import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import numpy as np
import csv
import re
import logging

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

# Load data
@st.cache_data
def load_data(uploaded_file=None):
    # Determine data source
    data_source = uploaded_file if uploaded_file is not None else 'data/sleep-export.csv'
    source_desc = "uploaded file" if uploaded_file is not None else "default file"
    
    try:
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
        
        # Handle numeric columns
        numeric_cols = ['Hours', 'Rating', 'Snore', 'Noise', 'Cycles', 'DeepSleep', 'LenAdjust']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Filter out days with zero records
        if 'Hours' in df.columns:
            df = df[df['Hours'] > 0]
        
        # Get event data - These are the columns with Event headers
        event_cols = [col for col in df.columns if 'Event' in str(col)]
        
        # Identify sleep movement data columns (time positions in format like "1:04", "2:35", etc.)
        time_pattern = r'^\d{1,2}:\d{2}$'
        movement_cols = [col for col in df.columns if pd.api.types.is_string_dtype(df[col]) and 
                         isinstance(col, str) and re.match(time_pattern, col)]
        
        # Suppress this message in UI but log to console
        print(f"Found {len(movement_cols)} movement data columns and {len(event_cols)} event columns")
        
        return df
        
    except Exception as e:
        st.error(f"Error processing data: {e}")
        return pd.DataFrame()

# Load the data
try:
    # Check if we have an uploaded file in session state
    uploaded_file = st.session_state.get('uploaded_file', None)
    
    df = load_data(uploaded_file)
    
    # Suppress this message in UI
    # st.success("Sleep data loaded successfully!")
    
    # Show data overview but collapsed by default
    with st.expander("Data Overview", expanded=False):
        st.write(f"Total records: {len(df)}")
        st.dataframe(df.head())
        st.write("Data columns:")
        st.write(df.columns.tolist())
        
        # Data summary
        st.write("Data summary:")
        st.write(df.describe())
        
        # Add CSV structure debugging info
        st.subheader("CSV Structure Analysis")
        try:
            with open('data/sleep-export.csv', 'r') as f:
                sample_lines = [next(f) for _ in range(10)]
                
            line_counts = []
            for i, line in enumerate(sample_lines):
                if i == 0:  # Header line
                    continue
                fields = line.split(',')
                line_counts.append(len(fields))
            
            st.write("Field counts in first 10 lines:")
            st.write(line_counts)
            
            if len(set(line_counts)) > 1:
                st.warning("⚠️ Inconsistent field counts detected in the CSV file. This may indicate formatting issues.")
                
            if min(line_counts) < max(line_counts):
                st.info(f"Line with fewest fields has {min(line_counts)} fields.")
                st.info(f"Line with most fields has {max(line_counts)} fields.")
        except Exception as e:
            st.error(f"Error analyzing CSV structure: {e}")
    
    # Create dashboard layout with tabs
    tab1, tab2, tab3, tab4 = st.tabs(["Sleep Duration", "Sleep Quality", "Sleep Patterns", "Troubleshooting"])
    
    with tab1:
        st.header("Sleep Duration Analysis")
        st.info("This section analyzes how much you sleep and how it changes over time.")
        
        try:
            if 'From' not in df.columns or 'Hours' not in df.columns:
                st.error("Could not find required columns for sleep duration analysis")
            else:
                # Create a separate dataframe for plotting to avoid any PyArrow conversion issues
                plot_df = df[['From', 'Hours']].copy()
                
                # Filter for 2025 data only
                if pd.api.types.is_datetime64_any_dtype(plot_df['From']):
                    plot_df = plot_df[plot_df['From'].dt.year == 2025].copy()
                    
                    # Ensure we're only looking at legitimate tracked sleep (Hours > 0)
                    plot_df = plot_df[plot_df['Hours'] > 0].copy()
                    
                    if len(plot_df) > 0:
                        # Add a date-only column for aggregation
                        plot_df['Date'] = plot_df['From'].dt.date
                        
                        # Create an aggregated dataframe that sums all sleep periods per day
                        daily_sleep = plot_df.groupby('Date')['Hours'].sum().reset_index()
                        daily_sleep['Date'] = pd.to_datetime(daily_sleep['Date'])
                        
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
                            multi_sleep_days = len(plot_df) - len(daily_sleep)
                            st.metric("Days with Multiple Sleep Periods", f"{multi_sleep_days}")
                            
                        # Optionally show more details about multiple sleep days
                        if multi_sleep_days > 0:
                            # Count number of records per day
                            sleep_count = plot_df.groupby('Date').size().reset_index(name='Count')
                            # Filter to days with multiple records
                            multi_days = sleep_count[sleep_count['Count'] > 1]
                            
                            if st.checkbox("Show details of days with multiple sleep records"):
                                st.write("Days with multiple sleep records:")
                                details = plot_df[plot_df['Date'].isin(multi_days['Date'])].sort_values(['Date', 'From'])
                                st.dataframe(details[['Date', 'From', 'Hours']])
                    else:
                        st.warning("No sleep data found for 2025. Please check your date format.")
                else:
                    st.error("Could not properly parse the date column 'From'. Please ensure it's in a standard date format.")
        except Exception as e:
            st.error(f"Error analyzing sleep duration: {str(e)}")
    
    with tab2:
        st.header("Sleep Quality Metrics")
        st.info("This section shows metrics related to your sleep quality.")
        
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
        st.info("This section analyzes your sleep patterns and schedules.")
        
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
    st.header("Data Source")
    
    # Add file uploader for alternative CSV files
    st.write("Having trouble with the default data file? Upload a corrected CSV:")
    uploaded_file = st.file_uploader("Upload sleep data CSV", type="csv")
    
    if uploaded_file is not None:
        st.success("✅ File uploaded successfully")
        st.session_state['uploaded_file'] = uploaded_file
        st.rerun()  # Rerun the app to use the uploaded file
    
    st.markdown("---")
    st.header("Filters and Settings")
    st.write("Filter your sleep data by date range:")
    
    try:
        if 'df' in locals():
            # Find date columns
            date_cols = [col for col in df.columns if pd.api.types.is_datetime64_any_dtype(df[col])]
            
            if date_cols:
                main_date_col = date_cols[0]
                min_date = df[main_date_col].min().date()
                max_date = df[main_date_col].max().date()
                
                date_range = st.date_input(
                    "Select date range",
                    value=(min_date, max_date),
                    min_value=min_date,
                    max_value=max_date
                )
                
                st.write("Additional filters will be added based on your data structure.")
    except:
        st.write("Date filters will be available after data is loaded correctly.")
    
    st.markdown("---")
    st.markdown("### About")
    st.markdown("This dashboard visualizes your sleep data to help you understand your sleep patterns and quality.")
    st.markdown("Data source: sleep-export.csv")
