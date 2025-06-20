"""
Data loading and file detection for the Sleep Data Dashboard
"""
import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import pytz

from .config import (
    DATA_FOLDER, FILE_PATTERNS, DATE_FORMAT, TARGET_YEAR, 
    DATE_COLUMNS, NUMERIC_COLUMNS, BASIC_COLUMNS, DEFAULT_TIMEZONE
)

def find_latest_data_file():
    """
    Find the latest 2025-only data file in the data folder based on naming convention.
    New format: YYYYMMDD_sleep-export[_2025only].csv
    Returns the path to the most recent file.
    """
    data_folder = Path(DATA_FOLDER)
    
    # Try each pattern in priority order
    for pattern in FILE_PATTERNS:
        files = list(data_folder.glob(pattern))
        if files:
            if pattern.startswith("*_sleep-export"):
                # New format - sort by date in filename (YYYYMMDD at start)
                latest_file = max(files, key=lambda x: x.name[:8])
            else:
                # Legacy format - sort by modification time
                latest_file = max(files, key=lambda x: x.stat().st_mtime)
            return str(latest_file)
    
    return None

def process_timezone_aware_dates(df, target_timezone=DEFAULT_TIMEZONE):
    """
    Process date columns to be timezone-aware, converting all times to a target timezone.
    
    Args:
        df: DataFrame with 'Tz' column and date columns
        target_timezone: Target timezone to convert all dates to
    
    Returns:
        DataFrame with timezone-aware and converted date columns
    """
    if 'Tz' not in df.columns:
        if 'notifications' not in st.session_state:
            st.session_state.notifications = []
        st.session_state.notifications.append("⚠️ No timezone information found in data. Times will be treated as naive datetimes.")
        return df
    
    df_processed = df.copy()
    
    # Get the target timezone object
    try:
        target_tz = pytz.timezone(target_timezone)
    except Exception as e:
        if 'notifications' not in st.session_state:
            st.session_state.notifications = []
        st.session_state.notifications.append(f"⚠️ Invalid target timezone '{target_timezone}'. Using UTC instead.")
        target_tz = pytz.UTC
        target_timezone = 'UTC'
    
    successful_conversions = 0
    total_conversions = 0
    
    for date_col in DATE_COLUMNS:
        if date_col in df_processed.columns:
            # Process each row's date with its corresponding timezone
            converted_dates = []
            
            for idx, row in df_processed.iterrows():
                total_conversions += 1
                try:
                    if pd.isna(row[date_col]) or pd.isna(row['Tz']):
                        converted_dates.append(row[date_col])
                        continue
                    
                    # Get the source timezone
                    source_tz_str = row['Tz']
                    source_tz = pytz.timezone(source_tz_str)
                    
                    # If the datetime is naive, localize it to the source timezone
                    dt = row[date_col]
                    if dt.tz is None:
                        # Localize to source timezone
                        dt_localized = source_tz.localize(dt)
                    else:
                        # Already timezone-aware, convert to source timezone if needed
                        dt_localized = dt.astimezone(source_tz)
                    
                    # Convert to target timezone
                    dt_converted = dt_localized.astimezone(target_tz)
                    converted_dates.append(dt_converted)
                    successful_conversions += 1
                    
                except Exception as e:
                    # If conversion fails, keep original value
                    converted_dates.append(row[date_col])
                    continue
            
            # Update the column with converted dates
            df_processed[date_col] = converted_dates
    
    # Store conversion statistics for notifications tab
    if total_conversions > 0:
        success_rate = (successful_conversions / total_conversions) * 100
        if 'notifications' not in st.session_state:
            st.session_state.notifications = []
        st.session_state.notifications.append(f"🌍 Timezone Processing Complete\n"
               f"- Converted {successful_conversions}/{total_conversions} timestamps ({success_rate:.1f}% success rate)\n"
               f"- All times now displayed in {target_timezone}\n"
               f"- Original timezones preserved in 'Tz' column for reference")
    
    return df_processed

def assign_sleep_date(row):
    """
    Assign a date to a sleep record using intelligent date assignment logic.
    
    Args:
        row: DataFrame row with 'From' and 'To' datetime columns
        
    Returns:
        date: The assigned date for this sleep period
    """
    start_date = row['From'].date()
    end_date = row['To'].date()
    
    # If sleep spans midnight, assign to wake-up date
    if end_date != start_date:
        return end_date
    else:
        return start_date

@st.cache_data
def load_data(uploaded_file=None):
    """
    Load and process sleep data from file or uploaded data.
    
    Args:
        uploaded_file: Optional uploaded file from Streamlit file_uploader
        
    Returns:
        DataFrame: Processed sleep data
    """
    # Determine data source
    if uploaded_file is not None:
        data_source = uploaded_file
        source_desc = "uploaded file"
    else:
        data_source = find_latest_data_file()
        if data_source is None:
            st.error("❌ No sleep data files found in the data folder!")
            st.write("Expected file patterns:")
            for pattern in FILE_PATTERNS:
                st.write(f"- `{pattern}`")
            return pd.DataFrame()
        
        source_desc = f"latest data file: {Path(data_source).name}"
    
    try:
        # Store loading notification for notifications tab
        if 'notifications' not in st.session_state:
            st.session_state.notifications = []
        st.session_state.notifications.append(f"📊 Loading data from {source_desc}")
        
        # Try loading with specific columns as we now know the format
        df = pd.read_csv(data_source, 
                        on_bad_lines='skip',
                        low_memory=False,
                        engine='c')
        
        # Parse date columns - ensure handling 2025 dates correctly
        try:
            # Convert date columns using the specific format in this data
            for date_col in DATE_COLUMNS:
                if date_col in df.columns:
                    # Convert to datetime with specified format
                    df[date_col] = pd.to_datetime(df[date_col], format=DATE_FORMAT, errors='coerce')
                    
                    # Ensure all dates are in the correct year (some may have incorrect years)
                    # Filter out obvious incorrect years (< 2000 or > 2100)
                    mask = ((df[date_col].dt.year > 2000) & (df[date_col].dt.year < 2100))
                    df = df[mask]
        except Exception as e:
            st.session_state.notifications.append(f"⚠️ Error parsing date columns: {e}")
        
        # Process timezone-aware dates BEFORE filtering and numeric processing
        target_tz = st.session_state.get('target_timezone', DEFAULT_TIMEZONE)
        df = process_timezone_aware_dates(df, target_tz)
        
        # Handle numeric columns
        for col in NUMERIC_COLUMNS:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Filter for target year and valid hours
        if 'From' in df.columns and 'Hours' in df.columns:
            df = df[df['From'].dt.year == TARGET_YEAR].copy()
            df = df[df['Hours'] > 0].copy()
            df = df.dropna(subset=['From', 'To', 'Hours'])
        
        # Count movement and event columns for reporting
        movement_cols = [col for col in df.columns if 'Movement' in str(col)]
        event_cols = [col for col in df.columns if 'Event' in str(col)]
        
        # Store success notification for notifications tab
        st.session_state.notifications.append(f"✅ Successfully loaded {len(df)} sleep records")
        if movement_cols or event_cols:
            st.session_state.notifications.append(f"📊 Found {len(movement_cols)} movement data columns and {len(event_cols)} event columns")
        
        return df
        
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame() 