import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import numpy as np
import csv
import re
import logging
import os
import glob
from pathlib import Path
import pytz

# Configure page settings to keep header menu visible
st.set_page_config(
    page_title="Sleep Data Analysis",
    page_icon="💤",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://docs.streamlit.io',
        'Report a bug': None,
        'About': 'A sleep data analysis application'
    }
)

# Add custom CSS to keep the header visible
st.markdown("""
<style>
    .stApp header {
        position: sticky;
        top: 0px;
        z-index: 999;
    }
</style>
""", unsafe_allow_html=True)

# Title
st.title("😴 Sleep Data Dashboard")

# Helper function to find the latest data file
def find_latest_data_file():
    """
    Find the latest 2025-only data file in the data folder based on naming convention.
    New format: YYYYMMDD_sleep-export[_2025only].csv
    Returns the path to the most recent file.
    """
    data_folder = Path("data")
    
    # Look for 2025-only files first (these are smaller and optimized)
    # New format: YYYYMMDD_sleep-export_2025only.csv
    pattern_2025_new = "*_sleep-export_2025only.csv"
    files_2025_new = list(data_folder.glob(pattern_2025_new))
    
    if files_2025_new:
        # Sort by date in filename (newest first) - extract YYYYMMDD from start of filename
        latest_file = max(files_2025_new, key=lambda x: x.name[:8])
        return str(latest_file)
    
    # Fallback to new format full dataset files
    # New format: YYYYMMDD_sleep-export.csv
    pattern_full_new = "*_sleep-export.csv"
    files_full_new = list(data_folder.glob(pattern_full_new))
    
    if files_full_new:
        # Filter out 2025only files (already checked above) and sort by date
        files_full_new = [f for f in files_full_new if "2025only" not in f.name]
        if files_full_new:
            latest_file = max(files_full_new, key=lambda x: x.name[:8])
            return str(latest_file)
    
    # Legacy format fallbacks (old naming convention)
    pattern_2025_old = "sleep-export_2025only_*.csv"
    files_2025_old = list(data_folder.glob(pattern_2025_old))
    
    if files_2025_old:
        latest_file = max(files_2025_old, key=lambda x: x.stat().st_mtime)
        return str(latest_file)
    
    pattern_full_old = "sleep-export_*.csv"
    files_full_old = list(data_folder.glob(pattern_full_old))
    
    if files_full_old:
        files_full_old = [f for f in files_full_old if "2025only" not in f.name]
        if files_full_old:
            latest_file = max(files_full_old, key=lambda x: x.stat().st_mtime)
            return str(latest_file)
    
    # Final fallback to old structure
    legacy_file = data_folder / "sleep-export.csv"
    if legacy_file.exists():
        return str(legacy_file)
    
    return None

def process_timezone_aware_dates(df, target_timezone='America/Chicago'):
    """
    Process date columns to be timezone-aware, converting all times to a target timezone.
    
    Args:
        df: DataFrame with 'Tz' column and date columns
        target_timezone: Target timezone to convert all dates to (default: 'America/Chicago')
    
    Returns:
        DataFrame with timezone-aware and converted date columns
    """
    if 'Tz' not in df.columns:
        st.warning("⚠️ No timezone information found in data. Times will be treated as naive datetimes.")
        return df
    
    date_columns = ['From', 'To', 'Sched']
    df_processed = df.copy()
    
    # Get the target timezone object
    try:
        target_tz = pytz.timezone(target_timezone)
    except Exception as e:
        st.warning(f"⚠️ Invalid target timezone '{target_timezone}'. Using UTC instead.")
        target_tz = pytz.UTC
        target_timezone = 'UTC'
    
    successful_conversions = 0
    total_conversions = 0
    
    for date_col in date_columns:
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

# Load data
@st.cache_data
def load_data(uploaded_file=None):
    # Determine data source
    if uploaded_file is not None:
        data_source = uploaded_file
        source_desc = "uploaded file"
    else:
        data_source = find_latest_data_file()
        if data_source is None:
            st.error("❌ No sleep data files found in the data folder!")
            st.write("Expected file patterns:")
            st.write("- `YYYYMMDD_sleep-export_2025only.csv` (preferred)")
            st.write("- `YYYYMMDD_sleep-export.csv` (full dataset)")
            st.write("- `sleep-export_2025only_YYYYMMDD.csv` (legacy)")
            st.write("- `sleep-export.csv` (legacy)")
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
        
        # Process the data structure - first get basic columns
        basic_cols = ['Id', 'Tz', 'From', 'To', 'Sched', 'Hours', 'Rating', 'Comment', 
                     'Framerate', 'Snore', 'Noise', 'Cycles', 'DeepSleep', 'LenAdjust', 'Geo']
        
        # Parse date columns - ensure handling 2025 dates correctly
        try:
            # Convert date columns using the specific format in this data
            date_format = '%d. %m. %Y %H:%M'
            for date_col in ['From', 'To', 'Sched']:
                if date_col in df.columns:
                    # Convert to datetime with specified format
                    df[date_col] = pd.to_datetime(df[date_col], format=date_format, errors='coerce')
                    
                    # Ensure all dates are in the correct year (some may have incorrect years)
                    # Filter out obvious incorrect years (< 2000 or > 2100)
                    mask = ((df[date_col].dt.year > 2000) & (df[date_col].dt.year < 2100))
                    df = df[mask]
        except Exception as e:
            st.warning(f"Error parsing date columns: {e}")
        
        # Process timezone-aware dates BEFORE filtering and numeric processing
        target_tz = st.session_state.get('target_timezone', 'America/Chicago')
        df = process_timezone_aware_dates(df, target_tz)
        
        # Handle numeric columns
        numeric_cols = ['Hours', 'Rating', 'Snore', 'Noise', 'Cycles', 'DeepSleep', 'LenAdjust']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Filter out days with zero records
        if 'Hours' in df.columns:
            df = df[df['Hours'] > 0]
        
        # If this is not already a 2025-only file, filter for 2025 data
        if 'From' in df.columns and pd.api.types.is_datetime64_any_dtype(df['From']):
            year_2025_count = len(df[df['From'].dt.year == 2025])
            total_count = len(df)
            
            if year_2025_count < total_count:
                st.session_state.notifications.append(f"📅 Filtering to 2025 data: {year_2025_count} records out of {total_count} total")
                df = df[df['From'].dt.year == 2025].copy()
        
        # Get event data - These are the columns with Event headers
        event_cols = [col for col in df.columns if 'Event' in str(col)]
        
        # Identify sleep movement data columns (time positions in format like "1:04", "2:35", etc.)
        time_pattern = r'^\d{1,2}:\d{2}$'
        movement_cols = [col for col in df.columns if pd.api.types.is_string_dtype(df[col]) and 
                         isinstance(col, str) and re.match(time_pattern, col)]
        
        # Log information about the data structure
        print(f"✅ Successfully loaded {len(df)} sleep records")
        print(f"📊 Found {len(movement_cols)} movement data columns and {len(event_cols)} event columns")
        
        return df
        
    except Exception as e:
        st.error(f"❌ Error processing data: {e}")
        st.write("**Troubleshooting tips:**")
        st.write("1. Check that the file is not corrupted")
        st.write("2. Ensure the file follows the expected CSV format")
        st.write("3. Try uploading the file manually using the sidebar")
        return pd.DataFrame()

# Load the data
try:
    # Check if we have an uploaded file in session state
    uploaded_file = st.session_state.get('uploaded_file', None)
    
    # Set default timezone for processing
    if 'target_timezone' not in st.session_state:
        st.session_state.target_timezone = 'America/Chicago'
    
    df = load_data(uploaded_file)
    
    if len(df) > 0:
        # Show data overview but collapsed by default
        with st.expander("📋 Data Overview", expanded=False):
            st.write(f"**Total records:** {len(df)}")
            
            # Show date range
            if 'From' in df.columns and pd.api.types.is_datetime64_any_dtype(df['From']):
                date_range = f"{df['From'].min().strftime('%Y-%m-%d')} to {df['From'].max().strftime('%Y-%m-%d')}"
                st.write(f"**Date range:** {date_range}")
            
            st.dataframe(df.head())
            st.write("**Data columns:**")
            st.write(df.columns.tolist())
            
            # Data summary
            st.write("**Data summary:**")
            st.write(df.describe())
            
            # Show file information
            if not uploaded_file:
                data_file = find_latest_data_file()
                if data_file:
                    file_info = Path(data_file)
                    file_size = file_info.stat().st_size / (1024 * 1024)  # MB
                    mod_time = datetime.fromtimestamp(file_info.stat().st_mtime)
                    st.write(f"**Source file:** {file_info.name}")
                    st.write(f"**File size:** {file_size:.1f} MB")
                    st.write(f"**Last modified:** {mod_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    if len(df) == 0:
        st.stop()  # Stop execution if no data loaded
        
    # Create dashboard layout with tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Sleep Duration", "Sleep Quality", "Sleep Patterns", "Notifications", "Troubleshooting"])
    
    with tab1:
        st.header("Sleep Duration Analysis")
        
        try:
            if 'From' not in df.columns or 'Hours' not in df.columns:
                st.error("Could not find required columns for sleep duration analysis")
            else:
                # Create a separate dataframe for plotting to avoid any PyArrow conversion issues
                plot_df = df[['From', 'To', 'Hours']].copy()
                
                # Filter for 2025 data only (should already be filtered but double-check)
                if pd.api.types.is_datetime64_any_dtype(plot_df['From']):
                    plot_df = plot_df[plot_df['From'].dt.year == 2025].copy()
                    
                    # Ensure we're only looking at legitimate tracked sleep (Hours > 0)
                    plot_df = plot_df[plot_df['Hours'] > 0].copy()
                    
                    if len(plot_df) > 0:
                        # Add a date-only column for aggregation using intelligent date assignment
                        def assign_sleep_date(row):
                            start_date = row['From'].date()
                            end_date = row['To'].date()
                            
                            # If sleep spans midnight (end date != start date), 
                            # assign to the wake-up date (when the sleep "completes")
                            if end_date != start_date:
                                return end_date
                            else:
                                return start_date
                        
                        plot_df['Date'] = plot_df.apply(assign_sleep_date, axis=1)
                        
                        # Sum all sleep periods per day (includes naps, multiple sessions)
                        daily_sleep = plot_df.groupby('Date')['Hours'].sum().reset_index()
                        daily_sleep['Date'] = pd.to_datetime(daily_sleep['Date'])
                        
                        # Store aggregation info for notifications tab
                        total_records = len(plot_df)
                        unique_dates = len(daily_sleep)
                        multi_session_days = total_records - unique_dates
                        cross_midnight_count = len(plot_df[plot_df['From'].dt.date != plot_df['To'].dt.date])
                        
                        # Store processing info in session state for notifications tab
                        st.session_state.processing_info = {
                            'total_records': total_records,
                            'unique_dates': unique_dates,
                            'multi_session_days': multi_session_days,
                            'cross_midnight_count': cross_midnight_count
                        }
                        
                        # Timeline Analysis
                        st.subheader("Sleep Duration Over Time")
                        
                        fig1 = px.bar(daily_sleep, x='Date', y='Hours', 
                                    title='Total Sleep Duration Per Day',
                                    labels={'Date': 'Date', 'Hours': 'Total Sleep Hours'})
                        
                        # Add a horizontal reference line at 8 hours
                        fig1.add_hline(y=8, line_dash="dash", line_color="green", 
                                     annotation_text="Ideal Sleep", 
                                     annotation_position="top right")
                        
                        # Set y-axis to show even hours with gridlines
                        max_hours = daily_sleep['Hours'].max()
                        y_max = 2 * (max_hours // 2) + 2  # Round up to next even number
                        
                        fig1.update_layout(
                            yaxis=dict(
                                tickmode='linear',
                                tick0=0,
                                dtick=2,  # Every 2 hours
                                range=[0, y_max],
                                gridcolor='lightgray',
                                griddash='dash'
                            )
                        )
                        
                        st.plotly_chart(fig1, use_container_width=True)
                        
                        # Sleep duration distribution
                        st.subheader("Sleep Duration Distribution")
                        
                        fig2 = px.histogram(daily_sleep, x='Hours', 
                                          nbins=20, 
                                          title='Distribution of Daily Total Sleep Duration',
                                          labels={'Hours': 'Total Sleep Hours', 'count': 'Frequency'})
                        
                        fig2.update_layout(bargap=0.2)
                        st.plotly_chart(fig2, use_container_width=True)
                        
                        # Days of the week analysis
                        st.subheader("Sleep by Day of Week")
                        
                        # Add day of week
                        daily_sleep['Day_of_Week'] = daily_sleep['Date'].dt.day_name()
                        
                        # Get all days and counts to show tracking frequency
                        day_counts = daily_sleep['Day_of_Week'].value_counts().reset_index()
                        day_counts.columns = ['Day_of_Week', 'Count']
                        
                        # Define the correct order for days of the week
                        day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                        
                        # Calculate average sleep per tracked day
                        day_avg = daily_sleep.groupby('Day_of_Week')['Hours'].mean().reset_index()
                        
                        # Ensure all days are in the correct order
                        day_avg['Day_of_Week'] = pd.Categorical(day_avg['Day_of_Week'], categories=day_order, ordered=True)
                        day_avg = day_avg.sort_values('Day_of_Week')
                        
                        # Same for counts
                        day_counts['Day_of_Week'] = pd.Categorical(day_counts['Day_of_Week'], categories=day_order, ordered=True)
                        day_counts = day_counts.sort_values('Day_of_Week')
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            fig3 = px.bar(day_avg, x='Day_of_Week', y='Hours',
                                         title='Average Sleep Duration by Day (Tracked Days Only)',
                                         labels={'Day_of_Week': 'Day', 'Hours': 'Average Sleep Hours'})
                            
                            fig3.update_layout(xaxis_title="Day of Week")
                            st.plotly_chart(fig3, use_container_width=True)
                        
                        with col2:
                            fig4 = px.bar(day_counts, x='Day_of_Week', y='Count',
                                         title='Number of Tracked Days by Day of Week',
                                         labels={'Day_of_Week': 'Day', 'Count': 'Number of Days Tracked'})
                            
                            fig4.update_layout(xaxis_title="Day of Week")
                            st.plotly_chart(fig4, use_container_width=True)
                        
                        # Display overall stats for tracked days
                        st.subheader("Overall Sleep Statistics (Tracked Days Only)")
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            avg_sleep = daily_sleep['Hours'].mean()
                            st.metric("Average Sleep", f"{avg_sleep:.1f} hours")
                        
                        with col2:
                            median_sleep = daily_sleep['Hours'].median()
                            st.metric("Median Sleep", f"{median_sleep:.1f} hours")
                        
                        with col3:
                            sleep_range = daily_sleep['Hours'].max() - daily_sleep['Hours'].min()
                            st.metric("Range", f"{sleep_range:.1f} hours")
                            
                        with col4:
                            st.metric("Days with Multiple Sleep Periods", f"{multi_session_days}")
                            
                        # Show details about multiple sleep days with better explanation
                        if multi_session_days > 0:
                            # Count number of records per day
                            sleep_count = plot_df.groupby('Date').size().reset_index(name='Count')
                            # Filter to days with multiple records
                            multi_days = sleep_count[sleep_count['Count'] > 1]
                            
                            if st.checkbox("Show details of days with multiple sleep records"):
                                st.write("**Days with multiple sleep records** (showing longest session used):")
                                details = plot_df[plot_df['Date'].isin(multi_days['Date'])].sort_values(['Date', 'Hours'], ascending=[True, False])
                                
                                # Add a column to mark which session was selected
                                details['Used'] = False
                                for date in multi_days['Date']:
                                    date_records = details[details['Date'] == date]
                                    if len(date_records) > 0:
                                        details.loc[date_records.index[0], 'Used'] = True
                                
                                # Display with formatting
                                display_details = details[['Date', 'From', 'Hours', 'Used']].copy()
                                display_details['From'] = display_details['From'].dt.strftime('%H:%M')
                                st.dataframe(
                                    display_details,
                                    column_config={
                                        "Date": "Date",
                                        "From": "Start Time", 
                                        "Hours": st.column_config.NumberColumn("Sleep Hours", format="%.2f"),
                                        "Used": st.column_config.CheckboxColumn("Used for Daily Total")
                                    }
                                )
                                
                                st.markdown("**Note**: All sleep sessions for a given day are **summed** to calculate that day's total sleep. "
                                          "This includes the main overnight sleep plus any naps, interruptions, or split-sleep sessions.")
                    else:
                        st.warning("No sleep data found for 2025. Please check your date format.")
                else:
                    st.error("Could not properly parse the date column 'From'. Please ensure it's in a standard date format.")
        except Exception as e:
            st.error(f"Error analyzing sleep duration: {str(e)}")
    
    with tab2:
        st.header("Sleep Quality Metrics")
        
        try:
            # For this data format, we have several quality metrics
            quality_metrics = ['DeepSleep', 'Cycles', 'Snore', 'Noise']
            available_metrics = [col for col in quality_metrics if col in df.columns]
            
            if available_metrics:
                # Make sure we're looking at 2025 data only
                plot_df = df[df['From'].dt.year == 2025].copy()
                
                if len(plot_df) > 0:
                    # Create a multi-select for which metrics to view
                    selected_metrics = st.multiselect(
                        "Select metrics to view:",
                        available_metrics,
                        default=available_metrics[:2]  # Default to first two available metrics
                    )
                    
                    col1, col2 = st.columns(2)
                    
                    # Show quality metrics over time
                    if selected_metrics and 'From' in plot_df.columns:
                        for i, metric in enumerate(selected_metrics):
                            # Alternate between columns for better layout
                            with col1 if i % 2 == 0 else col2:
                                # Create simplified dataframe for plotting just this metric
                                metric_df = plot_df[['From', metric]].copy()
                                
                                fig = px.line(metric_df, x='From', y=metric, 
                                             title=f'{metric} Over Time',
                                             labels={'From': 'Date'})
                                st.plotly_chart(fig, use_container_width=True)
                                
                                # Show distribution of this metric
                                fig2 = px.histogram(metric_df, x=metric, 
                                                  title=f'Distribution of {metric}',
                                                  labels={metric: metric})
                                fig2.update_layout(bargap=0.2)
                                st.plotly_chart(fig2, use_container_width=True)
                    
                    # Add correlation analysis
                    if len(selected_metrics) >= 2 and 'Hours' in df.columns:
                        st.subheader("Correlation Analysis")
                        
                        # Only select the columns we need for correlation
                        corr_metrics = selected_metrics + ['Hours'] 
                        corr_df = plot_df[corr_metrics].corr()
                        
                        # Create a heatmap of correlations
                        fig = px.imshow(corr_df, 
                                       text_auto=True, 
                                       color_continuous_scale='RdBu_r',
                                       title='Correlation Between Sleep Metrics')
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # Explain what positive/negative correlations mean
                        st.markdown("""
                        **Interpreting correlations:**
                        - Values close to 1 indicate strong positive correlation (when one increases, the other tends to increase)
                        - Values close to -1 indicate strong negative correlation (when one increases, the other tends to decrease)
                        - Values close to 0 indicate little or no correlation
                        """)
                else:
                    st.warning("No sleep data found for 2025. Please check your date format.")
            else:
                st.warning("No specific quality metrics found in the data.")
        except Exception as e:
            st.error(f"Error processing sleep quality data: {e}")
            st.write("Please check the data format and column names.")
    
    with tab3:
        st.header("Sleep Patterns")
        
        try:
            if 'From' in df.columns and 'To' in df.columns:
                # Make sure these are datetime and filter for 2025
                if pd.api.types.is_datetime64_any_dtype(df['From']) and pd.api.types.is_datetime64_any_dtype(df['To']):
                    # Create a filtered dataframe for 2025 only
                    plot_df = df[df['From'].dt.year == 2025].copy()
                    
                    if len(plot_df) > 0:
                        # Extract bedtime and wake time info
                        plot_df['bedtime'] = plot_df['From'].dt.hour + plot_df['From'].dt.minute/60
                        plot_df['waketime'] = plot_df['To'].dt.hour + plot_df['To'].dt.minute/60
                        
                        # Handle overnight sleep (when waketime is earlier than bedtime)
                        # We'll create two versions - one for calculations and one for display
                        plot_df['waketime_calc'] = plot_df['waketime'].copy()
                        plot_df.loc[plot_df['waketime_calc'] < plot_df['bedtime'], 'waketime_calc'] += 24
                        
                        # For display, let's keep wake time in 24hr format
                        # Set special labels for the axis to show it's the next day
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            # Bedtime distribution
                            fig1 = px.histogram(plot_df, x='bedtime', 
                                               nbins=24,
                                               title='Distribution of Bedtimes',
                                               labels={'bedtime': 'Hour of Day (24h format)'})
                            fig1.update_layout(bargap=0.2)
                            # Set x-axis range and ticks
                            fig1.update_xaxes(range=[0, 24], tickvals=list(range(0, 24, 2)))
                            st.plotly_chart(fig1, use_container_width=True)
                        
                        with col2:
                            # For wake time, separate into "same day" and "next day" for clarity
                            # Create a clear version showing when it's the next day
                            plot_df['is_next_day'] = plot_df['waketime'] < plot_df['bedtime']
                            next_day = plot_df[plot_df['is_next_day']].copy()
                            same_day = plot_df[~plot_df['is_next_day']].copy()
                            
                            # Plot both in same chart with different colors
                            fig2 = px.histogram(plot_df, x='waketime',
                                               nbins=24,
                                               title='Distribution of Wake Times',
                                               labels={'waketime': 'Hour of Day (24h format)'},
                                               color='is_next_day',
                                               color_discrete_map={True: 'orange', False: 'blue'},
                                               barmode='overlay')
                            
                            fig2.update_layout(bargap=0.2, 
                                             legend=dict(
                                                 title="Wake Time",
                                                 orientation="h",
                                                 yanchor="bottom",
                                                 y=1.02,
                                                 xanchor="center",
                                                 x=0.5
                                             ))
                            
                            # Update color legend labels
                            fig2.data[0].name = "Same Day"
                            if len(fig2.data) > 1:
                                fig2.data[1].name = "Next Day"
                                
                            # Set x-axis range and ticks for consistency
                            fig2.update_xaxes(range=[0, 24], tickvals=list(range(0, 24, 2)))
                            st.plotly_chart(fig2, use_container_width=True)
                        
                        # Sleep schedule consistency
                        st.subheader("Sleep Schedule Consistency")
                        
                        # Calculate day-to-day variations in bedtime and waketime
                        plot_df = plot_df.sort_values('From')
                        plot_df['next_bedtime'] = plot_df['bedtime'].shift(-1)
                        plot_df['bedtime_diff'] = abs(plot_df['next_bedtime'] - plot_df['bedtime'])
                        # Filter out differences greater than 12 hours (likely gaps in data)
                        df_filtered = plot_df[plot_df['bedtime_diff'] < 12]
                        
                        if not df_filtered.empty:
                            # Show consistency in bedtime
                            fig3 = px.histogram(df_filtered, x='bedtime_diff',
                                               title='Variation in Bedtimes (Day-to-Day)',
                                               labels={'bedtime_diff': 'Hours of Variation'})
                            st.plotly_chart(fig3, use_container_width=True)
                            
                            # Show average variation in bedtime
                            avg_variation = df_filtered['bedtime_diff'].mean()
                            st.metric("Average Bedtime Variation", f"{avg_variation:.2f} hours")
                            
                            if avg_variation < 0.5:
                                st.success("Your sleep schedule is very consistent (less than 30 minutes variation)!")
                            elif avg_variation < 1.0:
                                st.info("Your sleep schedule has moderate consistency (30-60 minutes variation).")
                            else:
                                st.warning(f"Your sleep schedule varies by {avg_variation:.1f} hours on average. More consistency may improve sleep quality.")
                    else:
                        st.warning("No sleep data found for 2025. Please check your date format.")
                else:
                    st.error("Could not properly parse the From/To date columns.")
            else:
                st.error("Could not find the required From/To columns for sleep timing analysis.")
            
            # Sleep phases analysis based on Event data
            if 'From' in df.columns:
                plot_df = df[df['From'].dt.year == 2025].copy()
                
                event_cols = [col for col in df.columns if 'Event' in str(col)]
                if event_cols and len(plot_df) > 0:
                    st.subheader("Sleep Phases")
                    st.write("This data includes sleep phase information in the Event columns. Looking for sleep phases...")
                    
                    # Analyze event data in the first row to see if we can extract sleep phases
                    if len(plot_df) > 0:
                        sample_row = plot_df.iloc[0]
                        event_data = []
                        for col in event_cols:
                            if pd.notna(sample_row[col]) and isinstance(sample_row[col], str):
                                if any(phase in sample_row[col] for phase in ['LIGHT', 'DEEP', 'REM', 'AWAKE']):
                                    event_data.append(sample_row[col])
                    
                        if event_data:
                            st.success(f"Found {len(event_data)} events with sleep phase information.")
                            st.write("First few events (shows sleep phases):")
                            st.write(event_data[:5])
                            st.info("A full analysis of sleep phases would require parsing the timestamp and phase type from each event, which requires more detailed processing.")
                        else:
                            st.warning("No sleep phase data found in the event columns.")
                    else:
                        st.warning("No rows found with event data.")
        except Exception as e:
            st.error(f"Error processing sleep pattern data: {e}")
            st.write("Please check the data format and column names.")

    with tab4:
        st.header("Notifications")
        
        try:
            # Display stored notifications
            if 'notifications' in st.session_state and st.session_state.notifications:
                st.subheader("Data Loading & Processing")
                for notification in st.session_state.notifications:
                    st.info(notification)
            
            # Display processing info
            if 'processing_info' in st.session_state:
                processing_info = st.session_state.processing_info
                st.subheader("Sleep Data Processing")
                st.info(f"📊 Sleep Data Processing: Summing all sleep periods per day\n"
                        f"- Total sleep records: {processing_info['total_records']}\n"
                        f"- Unique days: {processing_info['unique_dates']}\n"
                        f"- Days with multiple sessions: {processing_info['multi_session_days']}\n"
                        f"- Sleep periods crossing midnight: {processing_info['cross_midnight_count']}")
            
            if not ('notifications' in st.session_state and st.session_state.notifications) and not ('processing_info' in st.session_state):
                st.info("No notifications available. Please load data first.")
                
        except Exception as e:
            st.error(f"Error displaying notifications: {e}")

    with tab5:
        st.header("CSV Troubleshooting")
        st.info("If you're having problems loading your sleep data, try these steps:")
        
        st.subheader("Common CSV Issues")
        st.markdown("""
        1. **Inconsistent column count**: Your CSV file has varying numbers of columns across rows.
        2. **Special characters**: Commas, quotes, or newlines inside data fields causing parsing errors.
        3. **Encoding issues**: Non-standard text encoding causing character problems.
        """)
        
        st.subheader("How to Fix")
        st.markdown("""
        Try these approaches:
        
        1. **Open in Excel or Google Sheets**
            - Open your CSV file in a spreadsheet program
            - Save it back as CSV with proper formatting
            
        2. **Use the File Upload Option**
            - Use the file uploader in the sidebar to upload a fixed version
            
        3. **Clean with Python**
            - If you're comfortable with Python, try this code to clean your file:
        """)
        
        st.code("""
        import pandas as pd
        
        # Load with the most permissive settings
        df = pd.read_csv('data/sleep-export.csv', 
                         engine='python', 
                         sep=None, 
                         on_bad_lines='skip')
        
        # Save a cleaned version
        df.to_csv('data/sleep-export-fixed.csv', index=False)
        """, language="python")
        
        st.subheader("CSV Format Requirements")
        st.markdown("""
        For best results:
        - Each row should have the same number of columns
        - Fields with commas should be enclosed in quotes
        - Avoid special characters if possible
        """)
        
        st.success("If you've cleaned your data, upload the fixed file using the sidebar uploader.")

except Exception as e:
    st.error(f"Error loading sleep data: {e}")
    st.write("Please make sure the data file exists at 'data/sleep-export.csv' and is in the correct format.")

# Sidebar for filters and settings
with st.sidebar:
    st.header("📁 Data Source")
    
    # Show current data source
    current_file = find_latest_data_file()
    if current_file and 'uploaded_file' not in st.session_state:
        file_name = Path(current_file).name
        st.success(f"🎯 **Auto-selected:** {file_name}")
        
        # Show available files
        data_folder = Path("data")
        available_files = list(data_folder.glob("sleep-export*.csv"))
        if len(available_files) > 1:
            st.write("**Available data files:**")
            for file in sorted(available_files, key=lambda x: x.stat().st_mtime, reverse=True):
                is_current = str(file) == current_file
                icon = "🎯" if is_current else "📄"
                size_mb = file.stat().st_size / (1024 * 1024)
                mod_time = datetime.fromtimestamp(file.stat().st_mtime).strftime('%m/%d')
                st.write(f"{icon} {file.name} ({size_mb:.1f}MB, {mod_time})")
    
    # Add file uploader for alternative CSV files
    st.write("**Upload different file:**")
    uploaded_file = st.file_uploader("Choose sleep data CSV", type="csv", key="file_uploader")
    
    if uploaded_file is not None:
        st.success("✅ Using uploaded file")
        st.session_state['uploaded_file'] = uploaded_file
        st.rerun()  # Rerun the app to use the uploaded file
    elif 'uploaded_file' in st.session_state:
        if st.button("🔄 Switch back to auto-selected file"):
            del st.session_state['uploaded_file']
            st.rerun()
    
    st.markdown("---")
    st.header("⚙️ Settings")
    
    # Show data refresh options
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()
    
    try:
        if 'df' in locals() and len(df) > 0:
            st.markdown("### 📊 Data Info")
            st.write(f"**Records:** {len(df):,}")
            
            # Find date columns
            date_cols = [col for col in df.columns if pd.api.types.is_datetime64_any_dtype(df[col])]
            
            if date_cols:
                main_date_col = date_cols[0]
                min_date = df[main_date_col].min().date()
                max_date = df[main_date_col].max().date()
                total_days = (max_date - min_date).days + 1
                
                st.write(f"**Date range:** {min_date} to {max_date}")
                st.write(f"**Total days:** {total_days}")
                st.write(f"**Tracking rate:** {len(df)/total_days:.1%}")
                
    except:
        st.write("Data info will appear after successful load.")
    
    st.markdown("---")
    st.markdown("### 🌍 Timezone Settings")
    
    # Common timezone options
    common_timezones = [
        'America/Chicago',
        'America/New_York', 
        'America/Los_Angeles',
        'America/Denver',
        'America/Phoenix',
        'UTC',
        'Europe/London',
        'Europe/Paris',
        'Asia/Tokyo',
        'Australia/Sydney'
    ]
    
    # Check if data has timezone info
    if 'df' in locals() and len(df) > 0 and 'Tz' in df.columns:
        # Show current timezone distribution
        unique_timezones = df['Tz'].value_counts()
        if len(unique_timezones) > 0:
            st.write("**Timezones in your data:**")
            for tz, count in unique_timezones.head(3).items():
                st.write(f"• {tz}: {count} records")
        
        # Let user select target timezone
        current_tz = st.session_state.get('target_timezone', 'America/Chicago')
        try:
            current_index = common_timezones.index(current_tz)
        except ValueError:
            current_index = 0
            
        target_timezone = st.selectbox(
            "Display times in timezone:",
            options=common_timezones,
            index=current_index,
            help="All times will be converted to this timezone for analysis"
        )
        
        # Update session state if timezone changed
        if target_timezone != st.session_state.get('target_timezone'):
            st.session_state.target_timezone = target_timezone
            st.cache_data.clear()  # Clear cache to force reload with new timezone
            st.rerun()
        
        # Note about timezone processing
        st.info(f"🔄 All times displayed in **{target_timezone}**")
        
    else:
        st.write("⚠️ No timezone data found")
        st.write("Times will be treated as naive datetimes")
    
    st.markdown("---")
    st.markdown("### ℹ️ About")
    st.markdown("This dashboard analyzes your 2025 sleep data from Sleep as Android exports.")
    st.markdown("**Features:**")
    st.markdown("- 📊 Sleep duration tracking")
    st.markdown("- 🎯 Sleep quality metrics")  
    st.markdown("- 📅 Sleep pattern analysis")
    st.markdown("- 🔧 Data troubleshooting tools")
