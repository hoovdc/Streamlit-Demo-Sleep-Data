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

# Import configuration and data loading
from src.config import configure_page, apply_custom_styling, APP_TITLE, DEFAULT_TIMEZONE
from src.data_loader import find_latest_data_file, load_data
from src.data_processor import get_duration_analysis_data, get_quality_analysis_data, get_patterns_analysis_data, get_data_overview_info, clear_processing_cache
from src.advanced_analytics import display_moving_variance_analysis, display_extreme_outliers, display_recording_frequency, display_day_of_week_variability

# Configure page settings
configure_page()
apply_custom_styling()

# Title
st.title(APP_TITLE)

# Load the data
try:
    # Check if we have an uploaded file in session state
    uploaded_file = st.session_state.get('uploaded_file', None)
    
    # Set default timezone for processing
    if 'target_timezone' not in st.session_state:
        st.session_state.target_timezone = DEFAULT_TIMEZONE
    
    df = load_data(uploaded_file)
    
    if len(df) == 0:
        st.stop()  # Stop execution if no data loaded
        
    # Create dashboard layout with tabs
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["Sleep Duration", "Sleep Quality", "Sleep Patterns", "Raw Data", "Notifications", "Troubleshooting"])
    
    with tab1:
        st.header("Sleep Duration Analysis")
        
        try:
            if 'From' not in df.columns or 'Hours' not in df.columns:
                st.error("Could not find required columns for sleep duration analysis")
            else:
                # Use the centralized data processor - eliminates duplicate processing
                plot_df, daily_sleep, processing_info = get_duration_analysis_data(df)
                
                if plot_df is not None and len(plot_df) > 0:
                    # Store processing info in session state for notifications tab
                    st.session_state.processing_info = processing_info
                    
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
                    
                    # Configure x-axis to show centered numeric labels under each bar
                    fig2.update_layout(
                        bargap=0.2,
                        xaxis=dict(
                            tickmode='linear',
                            tick0=0,
                            dtick=0.5,  # Show tick every 0.5 hours
                            tickformat='.1f'  # Format as decimal with 1 place
                        )
                    )
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
                        multi_session_days = processing_info['multi_session_days']
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
                    
                    # Advanced Analytics Section - moved outside checkbox to always show
                    st.markdown("---")
                    st.header("🔬 Advanced Sleep Analytics")
                    
                    # Create tabs for different advanced analytics
                    analytics_tab1, analytics_tab2, analytics_tab3, analytics_tab4 = st.tabs([
                        "📈 Moving Variance", "🎯 Extreme Outliers", "📊 Recording Frequency", "📅 Day Variability"
                    ])
                    
                    with analytics_tab1:
                        display_moving_variance_analysis(daily_sleep)
                    
                    with analytics_tab2:
                        display_extreme_outliers(daily_sleep, plot_df)
                    
                    with analytics_tab3:
                        display_recording_frequency(daily_sleep, plot_df)
                    
                    with analytics_tab4:
                        display_day_of_week_variability(daily_sleep)
                        
                else:
                    st.warning("No sleep data found for 2025. Please check your date format.")
        except Exception as e:
            st.error(f"Error analyzing sleep duration: {str(e)}")
    
    with tab2:
        st.header("Sleep Quality Metrics")
        
        try:
            # Use the centralized data processor - eliminates duplicate processing
            plot_df, available_metrics = get_quality_analysis_data(df)
            
            if available_metrics and len(plot_df) > 0:
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
                if not available_metrics:
                    st.warning("No specific quality metrics found in the data.")
                else:
                    st.warning("No sleep data found for 2025. Please check your date format.")
        except Exception as e:
            st.error(f"Error processing sleep quality data: {e}")
            st.write("Please check the data format and column names.")
    
    with tab3:
        st.header("Sleep Patterns")
        
        try:
            # Use the centralized data processor - eliminates duplicate processing
            patterns_df = get_patterns_analysis_data(df)
            
            if len(patterns_df) > 0:
                # Bedtime patterns histogram
                st.subheader("Bedtime Distribution")
                
                fig1 = px.histogram(patterns_df, x='bedtime', 
                                               nbins=24,
                                               title='Distribution of Bedtimes',
                                   labels={'bedtime': 'Bedtime (24h format)', 'count': 'Frequency'})
                
                fig1.update_layout(bargap=0.2)
                st.plotly_chart(fig1, use_container_width=True)
                        
                # Wake time patterns histogram
                st.subheader("Wake Time Distribution")
                
                # Separate same-day and next-day wake times for clarity
                next_day = patterns_df[patterns_df['is_next_day']].copy()
                same_day = patterns_df[~patterns_df['is_next_day']].copy()
                
                if len(next_day) > 0:
                    st.write("**Next-day wake times** (most common - sleep crosses midnight):")
                    fig2 = px.histogram(next_day, x='waketime', 
                                       nbins=12, 
                                       title='Wake Time Distribution - Next Day Wake Times',
                                       labels={'waketime': 'Wake Time (24h format)', 'count': 'Frequency'})
                    fig2.update_layout(bargap=0.2)
                    st.plotly_chart(fig2, use_container_width=True)
                        
                if len(same_day) > 0:
                    st.write("**Same-day wake times** (unusual - naps or short sleeps):")
                    fig3 = px.histogram(same_day, x='waketime', 
                                       nbins=12, 
                                       title='Wake Time Distribution - Same Day Wake Times',
                                       labels={'waketime': 'Wake Time (24h format)', 'count': 'Frequency'})
                    fig3.update_layout(bargap=0.2)
                    st.plotly_chart(fig3, use_container_width=True)
                            
                # Sleep consistency analysis
                st.subheader("Sleep Consistency Analysis")
                
                # Calculate bedtime differences between consecutive nights
                patterns_df_sorted = patterns_df.sort_values('From')
                patterns_df_sorted['next_bedtime'] = patterns_df_sorted['bedtime'].shift(-1)
                patterns_df_sorted['bedtime_diff'] = abs(patterns_df_sorted['next_bedtime'] - patterns_df_sorted['bedtime'])
                
                # Filter out unreasonable differences (more than 12 hours suggests data issues)
                df_filtered = patterns_df_sorted[patterns_df_sorted['bedtime_diff'] < 12]
                
                if len(df_filtered) > 0:
                    fig4 = px.histogram(df_filtered, x='bedtime_diff', 
                                       nbins=20,
                                       title='Bedtime Consistency (Hours difference between consecutive nights)',
                                       labels={'bedtime_diff': 'Hours Difference in Bedtime', 'count': 'Frequency'})
                    
                    fig4.update_layout(bargap=0.2)
                    st.plotly_chart(fig4, use_container_width=True)
                    
                    # Statistics
                    avg_diff = df_filtered['bedtime_diff'].mean()
                    median_diff = df_filtered['bedtime_diff'].median()
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Average Bedtime Variation", f"{avg_diff:.1f} hours")
                    with col2:
                        st.metric("Median Bedtime Variation", f"{median_diff:.1f} hours")
                        
                    if avg_diff < 1:
                        st.success("🎯 Excellent bedtime consistency!")
                    elif avg_diff < 2:
                        st.info("👍 Good bedtime consistency")
                    else:
                        st.warning("⚠️ Consider establishing a more consistent bedtime routine")
                
                # Event data analysis removed to clean up the interface
            else:
                st.warning("No sleep pattern data available for analysis.")
        except Exception as e:
            st.error(f"Error processing sleep pattern data: {e}")
            st.write("Please check the data format and column names.")

    with tab4:
        st.header("Raw Data")
        
        # Use the centralized data processor - eliminates duplicate processing
        overview_info = get_data_overview_info(df, uploaded_file)
        
        if overview_info:
            st.write(f"**Total records:** {overview_info['total_records']}")
            
            # Show date range if available
            if 'date_range' in overview_info:
                date_range = f"{overview_info['date_range']['start']} to {overview_info['date_range']['end']}"
                st.write(f"**Date range:** {date_range}")
            
            st.dataframe(df.head())
            st.write("**Data columns:**")
            st.write(overview_info['columns'])
            
            # Data summary
            st.write("**Data summary:**")
            st.write(overview_info['data_summary'])
            
            # Show file information if available
            if 'file_info' in overview_info:
                file_info = overview_info['file_info']
                st.write(f"**Source file:** {file_info['name']}")
                st.write(f"**File size:** {file_info['size_mb']:.1f} MB")
                st.write(f"**Last modified:** {file_info['last_modified']}")
        else:
            st.write("No data available to display.")

    with tab5:
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

    with tab6:
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
