"""
Data processing pipeline for the Sleep Data Dashboard
Eliminates duplicate data processing across tabs by providing cached, pre-processed data views
"""
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

from .data_loader import assign_sleep_date
from .config import TARGET_YEAR, QUALITY_METRICS

@st.cache_data
def get_base_sleep_data(df):
    """
    Create the base filtered and processed sleep data used across all tabs.
    This eliminates duplicate filtering and processing.
    """
    if df is None or len(df) == 0:
        return pd.DataFrame()
    
    # Base filtering - used by all tabs
    base_df = df.copy()
    
    # Filter for target year (2025) if date column exists
    if 'From' in base_df.columns and pd.api.types.is_datetime64_any_dtype(base_df['From']):
        base_df = base_df[base_df['From'].dt.year == TARGET_YEAR].copy()
    
    # Filter for legitimate sleep periods (Hours > 0)
    if 'Hours' in base_df.columns:
        base_df = base_df[base_df['Hours'] > 0].copy()
    
    return base_df

@st.cache_data
def get_duration_analysis_data(df):
    """
    Prepare data specifically for sleep duration analysis tab.
    Returns processed data with date assignments and daily aggregations.
    """
    base_df = get_base_sleep_data(df)
    if len(base_df) == 0:
        return None, None, {}
    
    # Create plot dataframe with required columns
    plot_df = base_df[['From', 'To', 'Hours']].copy()
    
    # Add intelligent date assignment
    plot_df['Date'] = plot_df.apply(assign_sleep_date, axis=1)
    
    # Create daily sleep aggregation
    daily_sleep = plot_df.groupby('Date')['Hours'].sum().reset_index()
    daily_sleep['Date'] = pd.to_datetime(daily_sleep['Date'])
    
    # Calculate processing statistics
    total_records = len(plot_df)
    unique_dates = len(daily_sleep)
    multi_session_days = total_records - unique_dates
    cross_midnight_count = len(plot_df[plot_df['From'].dt.date != plot_df['To'].dt.date])
    
    processing_info = {
        'total_records': total_records,
        'unique_dates': unique_dates,
        'multi_session_days': multi_session_days,
        'cross_midnight_count': cross_midnight_count
    }
    
    return plot_df, daily_sleep, processing_info

@st.cache_data
def get_quality_analysis_data(df):
    """
    Prepare data specifically for sleep quality analysis tab.
    Returns base data with available quality metrics.
    """
    base_df = get_base_sleep_data(df)
    if len(base_df) == 0:
        return pd.DataFrame(), []
    
    # Find available quality metrics
    available_metrics = [col for col in QUALITY_METRICS if col in base_df.columns]
    
    return base_df, available_metrics

@st.cache_data
def get_patterns_analysis_data(df):
    """
    Prepare data specifically for sleep patterns analysis tab.
    Returns data with bedtime/waketime calculations.
    """
    base_df = get_base_sleep_data(df)
    if len(base_df) == 0:
        return pd.DataFrame()
    
    # Ensure we have the required columns
    if 'From' not in base_df.columns or 'To' not in base_df.columns:
        return pd.DataFrame()
    
    patterns_df = base_df.copy()
    
    # Extract bedtime and wake time info (as decimal hours)
    patterns_df['bedtime'] = patterns_df['From'].dt.hour + patterns_df['From'].dt.minute/60
    patterns_df['waketime'] = patterns_df['To'].dt.hour + patterns_df['To'].dt.minute/60
    
    # Handle cross-midnight wakeup times for visualization
    patterns_df['waketime_calc'] = patterns_df['waketime'].copy()
    patterns_df.loc[patterns_df['waketime_calc'] < patterns_df['bedtime'], 'waketime_calc'] += 24
    
    # Add day-of-week information
    patterns_df['day_of_week'] = patterns_df['From'].dt.day_name()
    
    # Add flags for analysis
    patterns_df['is_next_day'] = patterns_df['waketime'] < patterns_df['bedtime']
    
    return patterns_df

@st.cache_data
def get_data_overview_info(df, uploaded_file=None):
    """
    Prepare data for the Raw Data tab overview.
    Returns summary information about the dataset.
    """
    if df is None or len(df) == 0:
        return {}
    
    from pathlib import Path
    from .data_loader import find_latest_data_file
    
    overview_info = {
        'total_records': len(df),
        'columns': df.columns.tolist(),
        'data_summary': df.describe()
    }
    
    # Add date range if available
    if 'From' in df.columns and pd.api.types.is_datetime64_any_dtype(df['From']):
        overview_info['date_range'] = {
            'start': df['From'].min().strftime('%Y-%m-%d'),
            'end': df['From'].max().strftime('%Y-%m-%d')
        }
    
    # Add file information
    if not uploaded_file:
        data_file = find_latest_data_file()
        if data_file:
            file_info = Path(data_file)
            file_size = file_info.stat().st_size / (1024 * 1024)  # MB
            mod_time = datetime.fromtimestamp(file_info.stat().st_mtime)
            overview_info['file_info'] = {
                'name': file_info.name,
                'size_mb': file_size,
                'last_modified': mod_time.strftime('%Y-%m-%d %H:%M:%S')
            }
    
    return overview_info

def clear_processing_cache():
    """
    Clear all cached processing data.
    Useful when switching data sources or refreshing data.
    """
    # Clear the specific cache functions
    get_base_sleep_data.clear()
    get_duration_analysis_data.clear()
    get_quality_analysis_data.clear()
    get_patterns_analysis_data.clear()
    get_data_overview_info.clear()
    get_sleep_time_distribution_data.clear()

@st.cache_data
def get_sleep_time_distribution_data(df, interval_minutes=15):
    """
    Process sleep data into 24-hour time-of-day distribution for polar plot.
    
    Args:
        df: Raw sleep data DataFrame
        interval_minutes: Time interval in minutes (default 15)
    
    Returns:
        DataFrame with columns: 'time_slot', 'time_label', 'total_hours', 'degrees'
    """
    base_df = get_base_sleep_data(df)
    if len(base_df) == 0:
        return pd.DataFrame()
    
    # Ensure we have required columns
    if 'From' not in base_df.columns or 'To' not in base_df.columns:
        return pd.DataFrame()
    
    # Calculate number of slots in 24 hours
    slots_per_day = (24 * 60) // interval_minutes
    
    # Initialize array to accumulate sleep minutes per time slot
    sleep_minutes_per_slot = np.zeros(slots_per_day)
    
    # Process each sleep period
    for _, row in base_df.iterrows():
        start_time = row['From']
        end_time = row['To']
        
        if pd.isna(start_time) or pd.isna(end_time):
            continue
            
        # Create minute-by-minute range for this sleep period
        sleep_duration_minutes = int((end_time - start_time).total_seconds() / 60)
        
        for minute_offset in range(sleep_duration_minutes):
            current_moment = start_time + pd.Timedelta(minutes=minute_offset)
            
            # Calculate which time slot this minute belongs to (using time of day only)
            hour = current_moment.hour
            minute = current_moment.minute
            total_minutes_in_day = hour * 60 + minute
            slot_index = total_minutes_in_day // interval_minutes
            
            # Ensure slot_index is valid (handle edge case of exactly midnight)
            if slot_index >= slots_per_day:
                slot_index = 0
                
            # Add one minute to this slot
            sleep_minutes_per_slot[slot_index] += 1
    
    # Convert to hours and create result DataFrame
    sleep_hours_per_slot = sleep_minutes_per_slot / 60
    
    # Create time labels and other metadata
    time_data = []
    for i in range(slots_per_day):
        slot_start_minutes = i * interval_minutes
        hours = slot_start_minutes // 60
        minutes = slot_start_minutes % 60
        
        time_data.append({
            'time_slot': i,
            'time_label': f"{hours:02d}:{minutes:02d}",
            'total_hours': sleep_hours_per_slot[i],
            'degrees': (i * 360) / slots_per_day  # Convert to polar coordinates
        })
    
    return pd.DataFrame(time_data) 