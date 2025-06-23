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
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📈 Sleep Duration & Trends", 
        "🔬 Sleep Variance",
        "💤 Sleep Quality & Metrics", 
        "🕐 Sleep Patterns & Timing",
        "📋 Raw Data & Overview", 
        "🔔 Notifications & Processing"
    ])
    
    with tab1:
        st.header("📈 Sleep Duration & Trends")
        
        try:
            if 'From' not in df.columns or 'Hours' not in df.columns:
                st.error("Could not find required columns for sleep duration analysis")
            else:
                # Use the centralized data processor
                plot_df, daily_sleep, processing_info = get_duration_analysis_data(df)
                
                if plot_df is not None and len(plot_df) > 0:
                    # Store processing info in session state for notifications tab
                    st.session_state.processing_info = processing_info
                    
                    # --- BASIC DURATION ANALYSIS ---
                    st.subheader("Basic Duration Analysis")
                    
                    # Timeline Analysis
                    st.markdown("#### Sleep Duration Over Time")
                    fig1 = px.bar(daily_sleep, x='Date', y='Hours', 
                                title='Total Sleep Duration Per Day',
                                labels={'Date': 'Date', 'Hours': 'Total Sleep Hours'})
                    fig1.add_hline(y=8, line_dash="dash", line_color="green", 
                                    annotation_text="Ideal Sleep", 
                                    annotation_position="top right")
                    max_hours = daily_sleep['Hours'].max()
                    y_max = 2 * (max_hours // 2) + 2
                    fig1.update_layout(
                        yaxis=dict(tickmode='linear', tick0=0, dtick=2, range=[0, y_max], gridcolor='lightgray', griddash='dash')
                    )
                    st.plotly_chart(fig1, use_container_width=True)
                    
                    # Sleep duration distribution
                    st.markdown("#### Sleep Duration Distribution")
                    fig2 = px.histogram(daily_sleep, x='Hours', nbins=20, 
                                        title='Distribution of Daily Total Sleep Duration',
                                        labels={'Hours': 'Total Sleep Hours', 'count': 'Frequency'})
                    fig2.update_layout(
                        bargap=0.2,
                        xaxis=dict(tickmode='linear', tick0=0, dtick=0.5, tickformat='.1f')
                    )
                    st.plotly_chart(fig2, use_container_width=True)

                    # Overall Sleep Statistics
                    st.markdown("#### Overall Sleep Statistics")
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

                    st.markdown("---")

                    # --- DATA QUALITY INSIGHTS ---
                    st.subheader("Data Quality Insights")

                    # Create columns for layout
                    col_quality1, col_quality2 = st.columns(2)

                    with col_quality1:
                        st.markdown("#### Recording Frequency Analysis")
                        display_recording_frequency(daily_sleep, plot_df)
                    
                    with col_quality2:
                        st.markdown("#### Multiple Sleep Sessions Details")
                        multi_session_days = processing_info.get('multi_session_days', 0)
                        if multi_session_days > 0:
                            with st.expander(f"View details for {multi_session_days} days with multiple sessions"):
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
        st.header("🔬 Sleep Variance")
        
        try:
            # This data is required for the variance analysis
            plot_df, daily_sleep, processing_info = get_duration_analysis_data(df)
            
            if daily_sleep is not None and len(daily_sleep) > 0:
                # Flat layout for variance analytics
                st.subheader("📅 Day-of-Week Variability")
                display_day_of_week_variability(daily_sleep)
                
                st.markdown("---")
                
                st.subheader("📈 10-Day Moving Variance")
                display_moving_variance_analysis(daily_sleep)
                
                st.markdown("---")

                st.subheader("🎯 Extreme Outliers")
                display_extreme_outliers(daily_sleep, plot_df)
            else:
                st.warning("No sleep data available for variance analysis.")
        except Exception as e:
            st.error(f"Error in 'Sleep Variance' tab: {str(e)}")

    with tab3:
        st.header("💤 Sleep Quality & Metrics")
        
        try:
            # Use the centralized data processor
            plot_df, available_metrics = get_quality_analysis_data(df)
            
            if available_metrics and len(plot_df) > 0:
                st.subheader("Quality Metrics Selection")
                selected_metrics = st.multiselect(
                    "Select metrics to view:",
                    available_metrics,
                    default=available_metrics[:2]
                )
                
                st.markdown("---")
                st.subheader("Quality Analysis Charts")
                
                col1, col2 = st.columns(2)
                
                if selected_metrics and 'From' in plot_df.columns:
                    # Quality Metrics Over Time
                    with col1:
                        st.markdown("#### Quality Metrics Over Time")
                        for metric in selected_metrics:
                            fig = px.line(plot_df, x='From', y=metric, title=f'{metric} Over Time', labels={'From': 'Date', 'value': metric})
                            st.plotly_chart(fig, use_container_width=True)

                    # Quality Distribution Histograms
                    with col2:
                        st.markdown("#### Quality Distribution Histograms")
                        for metric in selected_metrics:
                            fig = px.histogram(plot_df, x=metric, nbins=20, title=f'Distribution of {metric}')
                            st.plotly_chart(fig, use_container_width=True)

                    # Correlation Heatmap
                    st.markdown("#### Correlation Heatmap (Quality vs. Duration)")
                    
                    # Ensure 'Hours' is in the dataframe for correlation
                    if 'Hours' not in plot_df.columns:
                        st.warning("Skipping correlation: 'Hours' column not available.")
                    else:
                        correlation_metrics = selected_metrics + ['Hours']
                        if len(correlation_metrics) > 1:
                            correlation_matrix = plot_df[correlation_metrics].corr()
                            fig_heatmap = go.Figure(data=go.Heatmap(
                                z=correlation_matrix.values,
                                x=correlation_matrix.columns,
                                y=correlation_matrix.columns,
                                colorscale='Viridis',
                                text=correlation_matrix.values,
                                texttemplate="%{text:.2f}"
                            ))
                            fig_heatmap.update_layout(title='Correlation Between Selected Metrics and Sleep Duration')
                            st.plotly_chart(fig_heatmap, use_container_width=True)
                        else:
                            st.info("Select at least one metric to see correlation with sleep duration.")
                
                st.markdown("---")
                st.subheader("Quality Insights")
                with st.expander("Show Correlation Interpretations & Recommendations"):
                    st.markdown("""
                    - **Positive Correlation** (closer to +1.0): When one metric increases, the other tends to increase. For example, more 'Deep sleep' might correlate with higher 'Snoring' if you snore more during deep sleep phases.
                    - **Negative Correlation** (closer to -1.0): When one metric increases, the other tends to decrease. For example, higher 'Noise' levels might correlate with lower 'Deep sleep' duration.
                    - **No Correlation** (closer to 0.0): The metrics have no clear relationship.
                    
                    **Recommendations**: Look for strong negative correlations between quality metrics (like 'Deep sleep') and controllable factors (like 'Noise' or 'Snoring'). Addressing these might improve sleep quality.
                    """)
            else:
                st.info("No sleep quality data available (e.g., Deep sleep %, Cycles, Snoring).")
        
        except Exception as e:
            st.error(f"Error analyzing sleep quality: {str(e)}")
            
    with tab4:
        st.header("🕐 Sleep Patterns & Timing")
        
        try:
            plot_df, daily_sleep, pattern_info = get_patterns_analysis_data(df)
            
            if plot_df is not None and len(plot_df) > 0:
                st.subheader("Sleep Timing Analysis")
                
                # Bedtime and Wake Time Distributions
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("#### Bedtime Distribution")
                    bedtime_hours = plot_df['From'].dt.hour + plot_df['From'].dt.minute / 60
                    fig_bedtime = px.histogram(x=bedtime_hours, nbins=24, title="Bedtime Distribution (24h)", labels={'x': 'Hour of Day'})
                    fig_bedtime.update_layout(xaxis_title="Hour of Day (e.g., 23.5 = 11:30 PM)", yaxis_title="Frequency")
                    st.plotly_chart(fig_bedtime, use_container_width=True)

                with col2:
                    st.markdown("#### Wake Time Distribution")
                    wake_time_hours = plot_df['To'].dt.hour + plot_df['To'].dt.minute / 60
                    fig_wake_time = px.histogram(x=wake_time_hours, nbins=24, title="Wake Time Distribution (24h)", labels={'x': 'Hour of Day'})
                    fig_wake_time.update_layout(xaxis_title="Hour of Day (e.g., 7.5 = 7:30 AM)", yaxis_title="Frequency")
                    st.plotly_chart(fig_wake_time, use_container_width=True)

                # Sleep Schedule Consistency
                st.markdown("#### Sleep Consistency Analysis")
                if pattern_info:
                    st.metric("Bedtime Standard Deviation", f"{pattern_info['bedtime_std']:.2f} hours")
                    st.info("A lower standard deviation indicates a more consistent sleep schedule.")
                
                st.markdown("---")
                st.subheader("Weekly Patterns")
                
                # Average Sleep by Day of Week & Tracking Frequency
                daily_sleep['Day_of_Week'] = daily_sleep['Date'].dt.day_name()
                day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                
                col_weekly1, col_weekly2 = st.columns(2)
                with col_weekly1:
                    st.markdown("#### Average Sleep by Day of Week")
                    day_avg = daily_sleep.groupby('Day_of_Week')['Hours'].mean().reindex(day_order).reset_index()
                    fig_day_avg = px.bar(day_avg, x='Day_of_Week', y='Hours', title='Average Sleep Duration by Day', labels={'Day_of_Week': 'Day', 'Hours': 'Average Sleep Hours'})
                    st.plotly_chart(fig_day_avg, use_container_width=True)
                    
                with col_weekly2:
                    st.markdown("#### Tracking Frequency by Day of Week")
                    day_counts = daily_sleep['Day_of_Week'].value_counts().reindex(day_order).reset_index()
                    day_counts.columns = ['Day_of_Week', 'Count']
                    fig_day_counts = px.bar(day_counts, x='Day_of_Week', y='Count', title='Number of Tracked Days by Day of Week', labels={'Day_of_Week': 'Day', 'Count': 'Number of Days Tracked'})
                    st.plotly_chart(fig_day_counts, use_container_width=True)

                st.markdown("---")
                st.subheader("Pattern Insights")
                with st.expander("Show Consistency Recommendations & Scores"):
                    st.markdown(f"""
                    Your average bedtime consistency score is **{pattern_info['bedtime_std']:.2f} hours** (standard deviation).

                    - **Under 1 hour**: Very consistent schedule.
                    - **1 to 1.5 hours**: Fairly consistent, but with some variability.
                    - **Over 1.5 hours**: Inconsistent schedule, which can impact sleep quality.

                    **Recommendation**: Aim to go to bed and wake up around the same time each day, even on weekends, to stabilize your body's internal clock.
                    """)
            else:
                st.warning("Not enough data to analyze sleep patterns.")
        except Exception as e:
            st.error(f"Error analyzing sleep patterns: {str(e)}")

    with tab5:
        st.header("📋 Raw Data & Overview")
        
        try:
            file_info, data_stats, column_info = get_data_overview_info(df)

            st.subheader("Data Summary")
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("#### File Information & Stats")
                st.json({
                    "File Name": file_info.get("file_name", "N/A"),
                    "File Size": file_info.get("file_size", "N/A"),
                    "Last Modified": file_info.get("last_modified", "N/A")
                })
            with col2:
                st.markdown("#### Data Range & Record Count")
                st.json({
                    "Total Records": data_stats.get("total_records", "N/A"),
                    "Date Range": data_stats.get("date_range", "N/A"),
                    "Timezone": st.session_state.get('target_timezone', 'N/A')
                })
            
            st.markdown("#### Column Information")
            st.dataframe(column_info, use_container_width=True)

            st.subheader("Raw Data Preview")
            st.dataframe(df.head(10))
            
            st.subheader("Data Health Check")
            validation_results = st.session_state.get('validation_results', {})
            if validation_results:
                st.success("Data validation passed with the following checks:")
                st.json(validation_results)
            else:
                st.info("No data validation issues to report.")

        except Exception as e:
            st.error(f"Error displaying data overview: {str(e)}")

    with tab6:
        st.header("🔔 Notifications & Processing")
        
        # Display file loading info
        st.subheader("Data Loading")
        file_info = st.session_state.get('file_info', {})
        if file_info:
            st.success(f"Successfully loaded data from `{file_info.get('file_name', 'N/A')}`.")
        
        # Display timezone processing info
        st.subheader("Processing Information")
        processing_info = st.session_state.get('processing_info', {})
        if processing_info:
            st.json(processing_info)
        else:
            st.info("No processing messages.")

        # Display any validation messages
        st.subheader("System Notifications")
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
