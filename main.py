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
import warnings
# Suppress only the pandas FutureWarning triggered by Plotly when converting
# datetime Series to NumPy arrays. This keeps the console clean while leaving
# all other warnings visible.
warnings.filterwarnings(
    "ignore",
    message=r"The behavior of DatetimeProperties\.to_pydatetime is deprecated",
    category=FutureWarning,
)

# Import configuration and data loading
from src.config import configure_page, apply_custom_styling, APP_TITLE, DEFAULT_TIMEZONE, ENABLE_GDRIVE_SYNC
from src.data_loader import load_data, sync_from_gdrive, find_latest_data_file
from src.data_processor import get_duration_analysis_data, get_quality_analysis_data, get_patterns_analysis_data, get_data_overview_info, clear_processing_cache
from src.advanced_analytics import display_moving_variance_analysis, display_extreme_outliers, display_recording_frequency, display_day_of_week_variability, display_sleep_time_polar_plot, display_sleep_time_polar_plot_nap_view

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
    
    df, source_description = load_data(uploaded_file)
    
    if len(df) == 0:
        st.warning(f"No data loaded. Source description: {source_description}")
        st.stop()  # Stop execution if no data loaded
        
    # Create dashboard layout with tabs
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📈 Sleep Duration & Trends", 
        "🕐 Sleep Patterns & Timing",
        "🔬 Sleep Variance",
        "💤 Sleep Quality & Metrics", 
        "📋 Raw Data & Overview", 
        "🔔 Notifications & Processing"
    ])
    
    with tab1:
        
        try:
            if 'From' not in df.columns or 'Hours' not in df.columns:
                st.error("Could not find required columns for sleep duration analysis")
            else:
                # Use the centralized data processor
                plot_df, daily_sleep, processing_info = get_duration_analysis_data(df)
                
                if plot_df is not None and len(plot_df) > 0:
                    # Store processing info in session state for notifications tab
                    st.session_state.processing_info = processing_info
                    
                    # Timeline Analysis
                    fig1 = px.bar(daily_sleep, x='Date', y='Hours', 
                                title='Total Sleep Duration Per Day',
                                labels={'Date': 'Date', 'Hours': 'Total Sleep Hours'})
                    fig1.add_hline(y=8, line_dash="dash", line_color="green", 
                                    annotation_text="Ideal Sleep", 
                                    annotation_position="top right")
                    
                    # Add 10-day moving average overlay
                    if len(daily_sleep) >= 10:
                        daily_sleep_sorted = daily_sleep.sort_values('Date')
                        daily_sleep_sorted['Moving_Avg_10'] = daily_sleep_sorted['Hours'].rolling(window=10, min_periods=10).mean()
                        
                        # Add moving average line (only where we have enough data)
                        ma_data = daily_sleep_sorted.dropna(subset=['Moving_Avg_10'])
                        if len(ma_data) > 0:
                            fig1.add_scatter(
                                x=ma_data['Date'], 
                                y=ma_data['Moving_Avg_10'],
                                mode='lines',
                                name='10-Day Moving Average',
                                line=dict(color='orange', width=3),
                                hovertemplate='<b>10-Day Average</b><br>Date: %{x}<br>Hours: %{y:.1f}<extra></extra>'
                            )
                    
                    max_hours = daily_sleep['Hours'].max()
                    y_max = 2 * (max_hours // 2) + 2
                    fig1.update_layout(
                        yaxis=dict(tickmode='linear', tick0=0, dtick=2, range=[0, y_max], gridcolor='lightgray', griddash='dash'),
                        showlegend=True,
                        legend=dict(
                            orientation="h",
                            yanchor="top",
                            y=-0.22,
                            xanchor="center",
                            x=0.5
                        )
                    )
                    st.plotly_chart(fig1, use_container_width=True)
                    
                    # Sleep duration distribution
                    fig2 = px.histogram(daily_sleep, x='Hours', nbins=20, 
                                        title='Distribution of Daily Total Sleep Duration',
                                        labels={'Hours': 'Total Sleep Hours', 'count': 'Frequency'})
                    fig2.update_layout(
                        bargap=0.2,
                        xaxis=dict(tickmode='linear', tick0=0, dtick=0.5, tickformat='.1f'),
                        margin=dict(t=40, b=40, l=40, r=40)
                    )
                    st.plotly_chart(fig2, use_container_width=True)

                    # Overall Sleep Statistics
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

                    # Create columns for layout
                    col_quality1, col_quality2 = st.columns(2)

                    with col_quality1:
                        display_recording_frequency(daily_sleep, plot_df)
                    
                    with col_quality2:
                        multi_session_days = processing_info.get('multi_session_days', 0)
                        if multi_session_days > 0:
                            with st.expander(f"Multiple sessions: {multi_session_days} days"):
                                # Count number of records per day
                                sleep_count = plot_df.groupby('Date').size().reset_index(name='Count')
                                # Filter to days with multiple records
                                multi_days = sleep_count[sleep_count['Count'] > 1]
                                
                                st.write("**Days with multiple sleep records**:")
                                details = plot_df[plot_df['Date'].isin(multi_days['Date'])].sort_values(['Date', 'Hours'], ascending=[True, False])
                                
                                # Display with formatting
                                display_details = details[['Date', 'From', 'To', 'Hours']].copy()
                                display_details['From'] = display_details['From'].dt.strftime('%H:%M')
                                display_details['To'] = display_details['To'].dt.strftime('%H:%M')
                                st.dataframe(
                                    display_details,
                                    column_config={
                                        "Date": "Date",
                                        "From": "Start Time", 
                                        "To": "End Time",
                                        "Hours": st.column_config.NumberColumn("Sleep Hours", format="%.2f"),
                                    },
                                    use_container_width=True
                                )
                                st.markdown("**Note**: All sleep sessions for a given day are **summed** to calculate that day's total sleep.")
                        else:
                            st.info("No days with multiple sleep sessions detected.")

                else:
                    st.warning("No sleep data found for 2025. Please check your date format.")
        except Exception as e:
            st.error(f"Error analyzing sleep duration: {str(e)}")
    
    with tab2:
        
        try:
            # Use the centralized data processor
            plot_df, daily_sleep, processing_info = get_duration_analysis_data(df)
            patterns_df = get_patterns_analysis_data(df)
            
            if patterns_df is not None and len(patterns_df) > 0:
                
                # Bedtime and Wake Time Distributions
                col1, col2 = st.columns(2)
                with col1:
                    bedtime_hours = patterns_df['From'].dt.hour + patterns_df['From'].dt.minute / 60
                    fig_bedtime = px.histogram(x=bedtime_hours, nbins=24, title="Bedtime Distribution (24h)", labels={'x': 'Hour of Day'})
                    fig_bedtime.update_layout(
                        xaxis_title="Hour of Day (e.g., 23.5 = 11:30 PM)", 
                        yaxis_title="Frequency",
                        xaxis=dict(tickmode='linear', tick0=0, dtick=1),
                        margin=dict(t=40, b=40, l=40, r=40)
                    )
                    
                    # Add hour labels - simpler approach
                    fig_bedtime.update_traces(texttemplate='%{y}', textposition='outside')
                    
                    st.plotly_chart(fig_bedtime, use_container_width=True)

                with col2:
                    wake_time_hours = patterns_df['To'].dt.hour + patterns_df['To'].dt.minute / 60
                    fig_wake_time = px.histogram(x=wake_time_hours, nbins=24, title="Wake Time Distribution (24h)", labels={'x': 'Hour of Day'})
                    fig_wake_time.update_layout(
                        xaxis_title="Hour of Day (e.g., 7.5 = 7:30 AM)", 
                        yaxis_title="Frequency",
                        xaxis=dict(tickmode='linear', tick0=0, dtick=1),
                        margin=dict(t=40, b=40, l=40, r=40)
                    )
                    
                    # Add hour labels - simpler approach
                    fig_wake_time.update_traces(texttemplate='%{y}', textposition='outside')
                    
                    st.plotly_chart(fig_wake_time, use_container_width=True)

                # Sleep Schedule Consistency
                col_consistency1, col_consistency2 = st.columns([1, 2])
                with col_consistency1:
                    bedtime_std = patterns_df['bedtime'].std()
                    st.metric("Bedtime Standard Deviation", f"{bedtime_std:.2f} hours")
                with col_consistency2:
                    st.info("A lower standard deviation indicates a more consistent sleep schedule.")
                
                # Average Sleep by Day of Week & Tracking Frequency
                daily_sleep['Day_of_Week'] = daily_sleep['Date'].dt.day_name()
                day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                
                col_weekly1, col_weekly2 = st.columns(2)
                with col_weekly1:
                    day_avg = daily_sleep.groupby('Day_of_Week')['Hours'].mean().reindex(day_order).reset_index()
                    fig_day_avg = px.bar(day_avg, x='Day_of_Week', y='Hours', title='Average Sleep Duration by Day', labels={'Day_of_Week': 'Day', 'Hours': 'Average Sleep Hours'})
                    fig_day_avg.update_traces(text=[f"{val:.1f}h" for val in day_avg['Hours']], textposition='outside')
                    fig_day_avg.update_layout(margin=dict(t=40, b=40, l=40, r=40))
                    st.plotly_chart(fig_day_avg, use_container_width=True)
                    
                with col_weekly2:
                    day_counts = daily_sleep['Day_of_Week'].value_counts().reindex(day_order).reset_index()
                    day_counts.columns = ['Day_of_Week', 'Count']
                    fig_day_counts = px.bar(day_counts, x='Day_of_Week', y='Count', title='Number of Tracked Days by Day of Week', labels={'Day_of_Week': 'Day', 'Count': 'Number of Days Tracked'})
                    fig_day_counts.update_traces(text=[f"{val}" for val in day_counts['Count']], textposition='outside')
                    fig_day_counts.update_layout(margin=dict(t=40, b=40, l=40, r=40))
                    st.plotly_chart(fig_day_counts, use_container_width=True)

        except Exception as e:
            st.error(f"Error analyzing sleep patterns: {str(e)}")

    with tab3:
        
        try:
            # Use the centralized data processor for source data
            plot_df, daily_sleep, processing_info = get_duration_analysis_data(df)
            
            # Display analyses
            display_moving_variance_analysis(daily_sleep)
            display_day_of_week_variability(daily_sleep)
            
            st.markdown("---")
            
            nap_view = st.checkbox("Focus on Naps/Short Sleep (<4 hours)", value=False)
            if nap_view:
                display_sleep_time_polar_plot_nap_view(plot_df)
            else:
                display_sleep_time_polar_plot(plot_df)
            
        except Exception as e:
            st.error(f"Error in advanced analytics: {str(e)}")

    with tab4:
        
        try:
            quality_df, quality_metrics = get_quality_analysis_data(df)
            
            if quality_df is not None and len(quality_df) > 0:
                # Let user select metrics
                selected_metrics = st.multiselect(
                    'Select sleep quality metrics to display:',
                    options=quality_metrics,
                    default=quality_metrics[:2]  # Default to first two
                )
                
                if selected_metrics:
                    # Create line chart for selected metrics over time
                    fig_quality = px.line(quality_df, x='Date', y=selected_metrics,
                                          title='Sleep Quality Metrics Over Time',
                                          labels={'value': 'Metric Value', 'variable': 'Metric'})
                    st.plotly_chart(fig_quality, use_container_width=True)
                else:
                    st.info("Select one or more quality metrics to visualize.")
            else:
                st.warning("No quality data found.")
        except Exception as e:
            st.error(f"Error analyzing sleep quality: {str(e)}")
            
    with tab5:
        
        try:
            overview_info = get_data_overview_info(df)

            col1, col2 = st.columns(2)
            with col1:
                file_info = overview_info.get('file_info', {})
                st.json({
                    "File Name": file_info.get("name", "N/A"),
                    "File Size": f"{file_info.get('size_mb', 0):.1f} MB" if file_info.get('size_mb') else "N/A",
                    "Last Modified": file_info.get("last_modified", "N/A")
                })
            with col2:
                date_range = overview_info.get('date_range', {})
                st.json({
                    "Total Records": overview_info.get("total_records", "N/A"),
                    "Date Range": f"{date_range.get('start', 'N/A')} to {date_range.get('end', 'N/A')}" if date_range else "N/A",
                    "Timezone": st.session_state.get('target_timezone', 'N/A')
                })
            
            # Column information
            if 'columns' in overview_info:
                columns_df = pd.DataFrame({
                    'Column': overview_info['columns'],
                    'Type': [str(df[col].dtype) for col in overview_info['columns']]
                })
                st.dataframe(columns_df, use_container_width=True)

            st.dataframe(df.head(10))
            
            validation_results = st.session_state.get('validation_results', {})
            if validation_results:
                st.success("Data validation passed with the following checks:")
                st.json(validation_results)
            else:
                st.info("No data validation issues to report.")

        except Exception as e:
            st.error(f"Error displaying data overview: {str(e)}")

    with tab6:
        
        # Display file loading info
        file_info = st.session_state.get('file_info', {})
        if file_info:
            st.success(f"Successfully loaded data from `{file_info.get('file_name', 'N/A')}`.")
        
        # Display timezone processing info
        processing_info = st.session_state.get('processing_info', {})
        if processing_info:
            st.json(processing_info)
        else:
            st.info("No processing messages.")

        # Display any validation messages
        validation_results = st.session_state.get('validation_results', {})
        if validation_results:
            st.write("Data Validation results:")
            st.json(validation_results)
        else:
            st.info("No system notifications.")
            
except FileNotFoundError:
    st.error("No data file found. Please place a file in the `data` directory.")

# Sidebar for filters and settings
with st.sidebar:
    st.header("Controls")
    
    if ENABLE_GDRIVE_SYNC:
        if st.button("🔄 Sync from Google Drive"):
            sync_success = sync_from_gdrive()
            if sync_success:
                # Clear caches and rerun to reflect new data
                st.cache_data.clear()
                st.rerun()

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
    
    # Removed duplicate lower sync button to avoid confusion

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
