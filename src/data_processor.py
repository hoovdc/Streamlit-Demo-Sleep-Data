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