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
    DATE_COLUMNS, NUMERIC_COLUMNS, BASIC_COLUMNS, DEFAULT_TIMEZONE, ENABLE_GDRIVE_SYNC, ENABLE_DB
)

from src.gdrive_sync import authenticate_gdrive, find_latest_zip, download_zip, load_config
from src.db_manager import load_from_db, insert_new_data

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

def sync_from_gdrive():
    if not ENABLE_GDRIVE_SYNC:
        return None
    
    # Lazy import only if enabled
    from src.gdrive_sync import authenticate_gdrive, find_latest_zip, download_zip, load_config
    
    try:
        config = load_config()
        folder_id = config['gdrive']['folder_id']
        service = authenticate_gdrive()
        latest_zip_id = find_latest_zip(service, folder_id)
        if latest_zip_id:
            csv_path = download_zip(service, latest_zip_id)
            return csv_path
        return None
    except Exception as e:
        # Log error, but don't crash - fall back to local
        print(f"GDrive sync failed: {e}")
        return None

@st.cache_data
def load_data(uploaded_file=None, enable_gdrive_sync=ENABLE_GDRIVE_SYNC):
    """
    Load and process sleep data. Skip DB entirely if not enabled; load directly from CSV.
    """
    df = pd.DataFrame()  # Empty init
    source_desc = None
    
    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file, parse_dates=['From', 'To', 'Sched'])
        source_desc = "uploaded file"
    else:
        df = pd.read_csv(DEFAULT_CSV_PATH, parse_dates=['From', 'To', 'Sched'])
        source_desc = "default CSV file"
    
    if ENABLE_DB:
        # Lazy import only if enabled
        from src.db_manager import load_from_db, insert_new_data
        db_df = load_from_db()
        if not db_df.empty:
            df = db_df
            source_desc = "local SQLite database"
    
    # Apply processing
    df = process_data(df)
    
    if ENABLE_DB and len(df) > 0:
        insert_new_data(df)
    
    st.session_state.notifications.append(f"📊 Loaded data from {source_desc}")
    return df

def process_data(df):
    # Placeholder for any additional processing after loading
    return df 