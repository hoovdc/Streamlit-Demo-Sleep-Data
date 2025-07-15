"""
Data loading and file detection for the Sleep Data Dashboard
"""
import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import pytz

# Standard library imports
import csv  # Added for csv.Error

# Import configuration *early* so constants are in scope for helper defaults
from .config import (
    DATA_FOLDER,
    FILE_PATTERNS,
    DATE_FORMAT,
    TARGET_YEAR,
    DATE_COLUMNS,
    NUMERIC_COLUMNS,
    BASIC_COLUMNS,
    DEFAULT_TIMEZONE,
    ENABLE_GDRIVE_SYNC,
    ENABLE_DB,
)

# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------


def _coerce_datetime_columns(
    df: pd.DataFrame,
    *,
    date_columns: list | None = None,
) -> pd.DataFrame:
    """Ensure the specified date columns are datetime dtype.

    Lazy-imports the project constants so this function remains safe even if a
    hot-reload executes an outdated module copy where the constants have not
    yet been imported at *definition* time.
    """

    if date_columns is None:
        from .config import DATE_COLUMNS as _DATE_COLS  # local import to avoid circularity
        date_columns = _DATE_COLS

    for col in date_columns:
        if col in df.columns and not pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = pd.to_datetime(df[col], format=DATE_FORMAT, errors='coerce')
    return df


def _coerce_numeric_columns(
    df: pd.DataFrame,
    numeric_columns: list | None = None,
) -> pd.DataFrame:
    """Convert numeric columns to numeric dtype, coercing errors to NaN."""

    if numeric_columns is None:
        from .config import NUMERIC_COLUMNS as _NUM_COLS
        numeric_columns = _NUM_COLS

    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    return df

# All top-level imports of local src modules are removed to prevent circular dependencies.

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
    """
    Orchestrates the GDrive sync process.
    Authenticates, finds the latest zip, downloads and extracts the data,
    processes it, and inserts the new data into the database.
    Returns True on success, False on failure.
    """
    if not ENABLE_GDRIVE_SYNC:
        st.error("GDrive Sync is not enabled in the configuration.")
        return False
    
    # Lazy import dependencies only when the function is called
    from src.gdrive_sync import authenticate_gdrive, find_latest_zip, download_zip, load_config
    from src.db_manager import insert_new_data
    
    try:
        with st.spinner("Connecting to Google Drive..."):
            config = load_config()
            folder_id = config['gdrive']['folder_id']
            service = authenticate_gdrive()
        
        with st.spinner("Finding latest sleep data in Google Drive..."):
            latest_zip_id = find_latest_zip(service, folder_id)
        
        if latest_zip_id:
            with st.spinner("Downloading and processing new data..."):
                # download_zip now returns a DataFrame directly
                new_df = download_zip(service, latest_zip_id)
                
                if new_df is not None and not new_df.empty:
                    # Perform all data processing before inserting into DB
                    new_df.rename(columns={'Sleep Quality': 'Rating', 'Deep sleep': 'DeepSleep'}, inplace=True, errors='ignore')
                    
                    for col in DATE_COLUMNS:
                        new_df[col] = pd.to_datetime(new_df[col], format=DATE_FORMAT, errors='coerce')

                    # This is a simplified version of timezone processing for the sync.
                    # A more robust implementation could be added later if needed.
                    
                    # Filter for 2025+ data
                    new_df = new_df[new_df['From'].dt.year >= TARGET_YEAR]
                    
                    if not new_df.empty:
                        insert_new_data(new_df)
                        st.success("Google Drive sync complete! New data has been added.")
                        return True
                    else:
                        st.info("No new data for the target year found in the latest Google Drive export.")
                        return False
                else:
                    st.info("No data found in the latest Google Drive export.")
                    return False
        else:
            st.warning("No 'Sleep as Android Data.zip' file found in the specified Google Drive folder.")
            return False
            
    except Exception as e:
        st.error(f"GDrive sync failed: {str(e)}")
        return False

@st.cache_data
def load_data(uploaded_file=None):
    """
    Load sleep data from the local SQLite database if enabled,
    otherwise fall back to loading from the latest CSV file.
    Returns a DataFrame and a string describing the source.
    """
    df = pd.DataFrame()
    source_desc = "No data loaded."
    
    if ENABLE_DB:
        # Lazy import db_manager only when needed
        from src.db_manager import load_from_db, DB_PATH
        df = load_from_db()
        if not df.empty:
            source_desc = f"local SQLite database ({DB_PATH})"
    
    # If DB is disabled, or was enabled but returned no data, load from CSV
    if df.empty:
        if uploaded_file:
            try:
                df = pd.read_csv(uploaded_file, parse_dates=DATE_COLUMNS, dayfirst=True, date_format=DATE_FORMAT)
                source_desc = "uploaded file"
            except (ValueError, csv.Error) as e:
                st.error(f"Error parsing uploaded file: {e}. Please ensure it is a valid Sleep as Android CSV.")
                return pd.DataFrame(), "Error parsing file."
        else:
            latest_file = find_latest_data_file()
            if latest_file:
                df = pd.read_csv(latest_file, parse_dates=DATE_COLUMNS, dayfirst=True, date_format=DATE_FORMAT)
                source_desc = f"local file: {Path(latest_file).name}"
            else:
                st.error("No data files found in the 'data' folder. Please add a sleep-export CSV file.")
                return pd.DataFrame(), "No data files found."
    
    # Enforce correct dtypes
    df = _coerce_datetime_columns(df)
    df = _coerce_numeric_columns(df)

    # Centralize notification logic
    if 'notifications' not in st.session_state:
        st.session_state.notifications = []
    
    if df.empty:
        st.warning("Loaded data is empty. The dashboard may not display correctly.")
    else:
        st.session_state.notifications.append(f"📊 Successfully loaded data from: {source_desc}")

    return df, source_desc

# process_data function is removed as processing logic is now handled in other functions.
# The `process_timezone_aware_dates` function is complex and its full logic
# should be reviewed and integrated carefully post-sync.
# It is not directly called by the new load_data function for simplicity but is kept for reference. 