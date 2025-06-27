"""
Advanced Sleep Analytics Module
Provides sophisticated analysis functions for sleep data patterns and trends
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

@st.cache_data
def calculate_moving_variance(daily_sleep, window_days=10):
    """
    Calculate 10-day moving variance analysis to track sleep consistency trends
    """
    if len(daily_sleep) < window_days:
        return None
    
    # Sort by date
    df_sorted = daily_sleep.sort_values('Date').copy()
    
    # Calculate rolling variance
    df_sorted['Moving_Variance'] = df_sorted['Hours'].rolling(window=window_days, min_periods=window_days).var()
    df_sorted['Moving_StdDev'] = df_sorted['Hours'].rolling(window=window_days, min_periods=window_days).std()
    df_sorted['Moving_Average'] = df_sorted['Hours'].rolling(window=window_days, min_periods=window_days).mean()
    
    # Remove rows without variance calculation
    df_variance = df_sorted.dropna(subset=['Moving_Variance']).copy()
    
    return df_variance

@st.cache_data
def detect_extreme_outliers(daily_sleep, plot_df, n_outliers=10):
    """
    Detect the 10 most unusual sleep periods with detailed analysis
    """
    if len(daily_sleep) == 0:
        return None, None
    
    # Calculate statistics for outlier detection
    mean_sleep = daily_sleep['Hours'].mean()
    std_sleep = daily_sleep['Hours'].std()
    
    # Calculate z-scores for daily totals
    daily_sleep = daily_sleep.copy()
    daily_sleep['Z_Score'] = abs((daily_sleep['Hours'] - mean_sleep) / std_sleep)
    daily_sleep['Deviation_Hours'] = abs(daily_sleep['Hours'] - mean_sleep)
    
    # Get top outliers by z-score
    top_outliers = daily_sleep.nlargest(n_outliers, 'Z_Score').copy()
    
    # Get detailed session information for these outlier days
    outlier_details = []
    for _, outlier_day in top_outliers.iterrows():
        date = outlier_day['Date']
        day_sessions = plot_df[plot_df['Date'] == date].copy()
        
        if len(day_sessions) > 0:
            # Sort by hours descending to show longest session first
            day_sessions = day_sessions.sort_values('Hours', ascending=False)
            
            outlier_info = {
                'Date': date,
                'Total_Hours': outlier_day['Hours'],
                'Z_Score': outlier_day['Z_Score'],
                'Deviation_Hours': outlier_day['Deviation_Hours'],
                'Session_Count': len(day_sessions),
                'Longest_Session': day_sessions.iloc[0]['Hours'] if len(day_sessions) > 0 else 0,
                'Sessions': day_sessions[['From', 'To', 'Hours']].to_dict('records'),
                'Day_of_Week': date.strftime('%A') if hasattr(date, 'strftime') else 'Unknown'
            }
            outlier_details.append(outlier_info)
    
    return top_outliers, outlier_details

@st.cache_data
def analyze_recording_frequency(daily_sleep, plot_df):
    """
    Analyze recording frequency and identify gaps in sleep data
    """
    if len(daily_sleep) == 0:
        return None
    
    # Get date range
    min_date = daily_sleep['Date'].min()
    max_date = daily_sleep['Date'].max()
    
    # Create complete date range
    date_range = pd.date_range(start=min_date, end=max_date, freq='D')
    complete_dates = pd.DataFrame({'Date': date_range})
    
    # Merge with actual data to find gaps
    merged = complete_dates.merge(daily_sleep[['Date', 'Hours']], on='Date', how='left')
    merged['Has_Data'] = merged['Hours'].notna()
    
    # Identify gaps
    gaps = merged[~merged['Has_Data']].copy()
    
    # Calculate gap statistics
    total_days = len(complete_dates)
    recorded_days = len(daily_sleep)
    missing_days = len(gaps)
    recording_rate = (recorded_days / total_days) * 100
    
    # Find consecutive gap periods
    gap_periods = []
    if len(gaps) > 0:
        gaps['Date_Diff'] = gaps['Date'].diff().dt.days
        gap_start = None
        
        for idx, row in gaps.iterrows():
            if gap_start is None or row['Date_Diff'] > 1:
                # Start of new gap period
                if gap_start is not None:
                    # End previous gap period
                    gap_periods.append({
                        'Start': gap_start,
                        'End': prev_date,
                        'Duration_Days': (prev_date - gap_start).days + 1
                    })
                gap_start = row['Date']
            prev_date = row['Date']
        
        # Don't forget the last gap period
        if gap_start is not None:
            gap_periods.append({
                'Start': gap_start,
                'End': prev_date,
                'Duration_Days': (prev_date - gap_start).days + 1
            })
    
    # Sessions per day analysis
    session_counts = plot_df.groupby('Date').size().reset_index(name='Session_Count')
    session_stats = session_counts['Session_Count'].describe()
    
    frequency_stats = {
        'total_days_in_range': total_days,
        'recorded_days': recorded_days,
        'missing_days': missing_days,
        'recording_rate_percent': recording_rate,
        'date_range': (min_date, max_date),
        'gap_periods': gap_periods,
        'session_stats': session_stats,
        'session_counts': session_counts
    }
    
    return frequency_stats

@st.cache_data
def calculate_day_of_week_variability(daily_sleep):
    """
    Calculate variability (in hours) per day of week
    """
    if len(daily_sleep) == 0:
        return None
    
    # Add day of week
    daily_sleep_copy = daily_sleep.copy()
    daily_sleep_copy['Day_of_Week'] = daily_sleep_copy['Date'].dt.day_name()
    
    # Define proper order
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    # Calculate statistics per day of week
    day_stats = daily_sleep_copy.groupby('Day_of_Week')['Hours'].agg([
        'count', 'mean', 'std', 'min', 'max', 'median'
    ]).reset_index()
    
    # Calculate additional variability metrics
    day_stats['Range'] = day_stats['max'] - day_stats['min']
    day_stats['Coefficient_of_Variation'] = (day_stats['std'] / day_stats['mean']) * 100
    
    # Ensure proper ordering
    day_stats['Day_of_Week'] = pd.Categorical(day_stats['Day_of_Week'], categories=day_order, ordered=True)
    day_stats = day_stats.sort_values('Day_of_Week')
    
    # Fill NaN values for days with only one data point
    day_stats['std'] = day_stats['std'].fillna(0)
    day_stats['Range'] = day_stats['Range'].fillna(0)
    day_stats['Coefficient_of_Variation'] = day_stats['Coefficient_of_Variation'].fillna(0)
    
    return day_stats

def display_moving_variance_analysis(daily_sleep):
    """Display 10-day moving variance analysis"""
    
    variance_data = calculate_moving_variance(daily_sleep)
    
    if variance_data is None or len(variance_data) == 0:
        st.warning("Not enough data for 10-day moving variance analysis (minimum 10 days required)")
        return
    
    # Create the variance trend chart
    fig = go.Figure()
    
    # Add variance line
    fig.add_trace(go.Scatter(
        x=variance_data['Date'],
        y=variance_data['Moving_Variance'],
        mode='lines',
        name='10-Day Variance',
        line=dict(color='orange', width=2)
    ))
    
    # Add average line for reference
    avg_variance = variance_data['Moving_Variance'].mean()
    fig.add_hline(y=avg_variance, line_dash="dash", line_color="red", 
                  annotation_text=f"Average Variance: {avg_variance:.2f}")
    
    fig.update_layout(
        title='Sleep Consistency Trends (10-Day Moving Variance)',
        xaxis_title='Date',
        yaxis_title='Variance (hours²)',
        hovermode='x unified'
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Display insights
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Average Variance", f"{avg_variance:.2f} hrs²")
    
    with col2:
        min_variance = variance_data['Moving_Variance'].min()
        st.metric("Most Consistent Period", f"{min_variance:.2f} hrs²")
    
    with col3:
        max_variance = variance_data['Moving_Variance'].max()
        st.metric("Least Consistent Period", f"{max_variance:.2f} hrs²")
    
    # Interpretation
    if avg_variance < 0.5:
        st.success("🎯 Excellent sleep consistency! Your sleep duration is very stable.")
    elif avg_variance < 1.0:
        st.info("👍 Good sleep consistency with moderate variation.")
    elif avg_variance < 2.0:
        st.warning("⚠️ Moderate sleep inconsistency. Consider establishing a more regular sleep schedule.")
    else:
        st.error("🚨 High sleep variability detected. This may impact sleep quality and health.")

def display_extreme_outliers(daily_sleep, plot_df):
    """Display extreme outliers analysis"""
    
    outliers, outlier_details = detect_extreme_outliers(daily_sleep, plot_df)
    
    if outliers is None or len(outlier_details) == 0:
        st.warning("No outliers detected or insufficient data")
        return
    
    st.write("**Top 10 most unusual sleep periods:**")
    
    # Display outliers in an expandable format
    for i, outlier in enumerate(outlier_details[:10], 1):
        date_str = outlier['Date'].strftime('%Y-%m-%d') if hasattr(outlier['Date'], 'strftime') else str(outlier['Date'])
        
        with st.expander(f"#{i}. {date_str} ({outlier['Day_of_Week']}) - {outlier['Total_Hours']:.1f} hours (Z-score: {outlier['Z_Score']:.1f})"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Total Sleep:** {outlier['Total_Hours']:.1f} hours")
                st.write(f"**Deviation from Average:** {outlier['Deviation_Hours']:.1f} hours")
                st.write(f"**Statistical Outlier Score:** {outlier['Z_Score']:.1f}")
                st.write(f"**Number of Sessions:** {outlier['Session_Count']}")
            
            with col2:
                st.write("**Sleep Sessions:**")
                for j, session in enumerate(outlier['Sessions'], 1):
                    from_time = session['From'].strftime('%H:%M') if hasattr(session['From'], 'strftime') else str(session['From'])
                    to_time = session['To'].strftime('%H:%M') if hasattr(session['To'], 'strftime') else str(session['To'])
                    st.write(f"Session {j}: {from_time} → {to_time} ({session['Hours']:.1f}h)")

def display_recording_frequency(daily_sleep, plot_df):
    """Display recording frequency analysis"""
    
    freq_stats = analyze_recording_frequency(daily_sleep, plot_df)
    
    if freq_stats is None:
        st.warning("No data available for frequency analysis")
        return
    
    # Display key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Days Tracked", f"{freq_stats['recorded_days']}")
    
    with col2:
        st.metric("Days in Range", f"{freq_stats['total_days_in_range']}")
    
    with col3:
        st.metric("Missing Days", f"{freq_stats['missing_days']}")
    
    with col4:
        st.metric("Recording Rate", f"{freq_stats['recording_rate_percent']:.1f}%")
    
    # Gap analysis
    if freq_stats['gap_periods']:
        st.write("**Data Gaps Identified:**")
        gap_df = pd.DataFrame(freq_stats['gap_periods'])
        gap_df['Start'] = gap_df['Start'].dt.strftime('%Y-%m-%d')
        gap_df['End'] = gap_df['End'].dt.strftime('%Y-%m-%d')
        st.dataframe(gap_df, column_config={
            "Start": "Gap Start",
            "End": "Gap End", 
            "Duration_Days": st.column_config.NumberColumn("Duration (Days)", format="%d")
        })
    else:
        st.success("✅ No data gaps detected - excellent recording consistency!")
    
    # Sessions per day analysis
    session_counts = freq_stats['session_counts']
    
    fig = px.histogram(session_counts, x='Session_Count',
                      title='Distribution of Sleep Sessions Per Day',
                      labels={'Session_Count': 'Number of Sessions', 'count': 'Number of Days'})
    st.plotly_chart(fig, use_container_width=True)
    
    # Session statistics
    session_stats = freq_stats['session_stats']
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Average Sessions/Day", f"{session_stats['mean']:.1f}")
    
    with col2:
        st.metric("Most Sessions in One Day", f"{int(session_stats['max'])}")
    
    with col3:
        multi_session_days = len(session_counts[session_counts['Session_Count'] > 1])
        st.metric("Days with Multiple Sessions", f"{multi_session_days}")

def display_day_of_week_variability(daily_sleep):
    """Display day of week variability analysis"""
    
    day_stats = calculate_day_of_week_variability(daily_sleep)
    
    if day_stats is None or len(day_stats) == 0:
        st.warning("No data available for day-of-week analysis")
        return
    
    # Create variability chart
    fig = px.bar(day_stats, x='Day_of_Week', y='std',
                title='Sleep Duration Variability by Day of Week',
                labels={'std': 'Standard Deviation (hours)', 'Day_of_Week': 'Day of Week'})
    
    # Add text annotations showing the exact values
    fig.update_traces(text=[f"{val:.1f}h" for val in day_stats['std']], textposition='outside')
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Display detailed statistics table
    st.write("**Detailed Variability Statistics:**")
    
    display_stats = day_stats.copy()
    display_stats = display_stats.round(1)
    
    st.dataframe(display_stats, column_config={
        "Day_of_Week": "Day",
        "count": st.column_config.NumberColumn("Days Tracked", format="%d"),
        "mean": st.column_config.NumberColumn("Average Sleep (hrs)", format="%.1f"),
        "std": st.column_config.NumberColumn("Variability (hrs)", format="%.1f"),
        "min": st.column_config.NumberColumn("Minimum (hrs)", format="%.1f"),
        "max": st.column_config.NumberColumn("Maximum (hrs)", format="%.1f"),
        "Range": st.column_config.NumberColumn("Range (hrs)", format="%.1f"),
        "Coefficient_of_Variation": st.column_config.NumberColumn("CV (%)", format="%.1f")
    })
    
    # Insights
    most_variable_day = day_stats.loc[day_stats['std'].idxmax(), 'Day_of_Week']
    most_consistent_day = day_stats.loc[day_stats['std'].idxmin(), 'Day_of_Week']
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.info(f"**Most Variable:** {most_variable_day} ({day_stats['std'].max():.1f}h variability)")
    
    with col2:
        st.success(f"**Most Consistent:** {most_consistent_day} ({day_stats['std'].min():.1f}h variability)")

def display_sleep_time_polar_plot(df):
    """Display 24-hour sleep distribution as a polar plot"""
    
    from .data_processor import get_sleep_time_distribution_data
    
    time_dist_data = get_sleep_time_distribution_data(df, interval_minutes=15)
    
    if time_dist_data is None or len(time_dist_data) == 0:
        st.warning("No data available for 24-hour sleep distribution analysis")
        return
    
    # Filter out time slots with no sleep (optional - can be removed for complete visualization)
    # time_dist_data = time_dist_data[time_dist_data['total_hours'] > 0]
    
    if len(time_dist_data) == 0:
        st.info("No sleep time distribution data to display")
        return
    
    # Create polar plot
    fig = go.Figure(go.Scatterpolar(
        r=time_dist_data['total_hours'],
        theta=time_dist_data['degrees'],
        mode='lines+markers',
        fill='toself',
        name='Sleep Hours',
        line=dict(color='rgba(135, 206, 250, 0.9)', width=2),  # Light blue line
        fillcolor='rgba(100, 149, 237, 0.4)',  # Cornflower blue fill
        marker=dict(size=4, color='rgba(135, 206, 250, 0.9)'),
        hovertemplate='<b>Time:</b> %{customdata}<br><b>Total Sleep:</b> %{r:.1f} hours<extra></extra>',
        customdata=time_dist_data['time_label']
    ))
    
    # Calculate max hours for radial axis range
    max_hours = time_dist_data['total_hours'].max() if len(time_dist_data) > 0 else 1
    radial_max = max(max_hours * 1.1, 1)  # Add 10% padding, minimum 1 hour
    
    # Create time labels for angular axis (every hour)
    hour_ticks = list(range(0, 360, 15))  # Every 15 degrees = every hour
    hour_labels = [f"{i//15:02d}:00" for i in hour_ticks]
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                title="Total Hours Slept",
                range=[0, radial_max],
                tickmode='linear',
                tick0=0,
                dtick=max(1, radial_max//5),  # About 5 tick marks
                title_font=dict(color='white'),
                tickfont=dict(color='white'),
                gridcolor='rgba(255, 255, 255, 0.3)'
            ),
            angularaxis=dict(
                tickmode='array',
                tickvals=hour_ticks,
                ticktext=hour_labels,
                direction='clockwise',
                rotation=90,  # Start at top (midnight)
                showgrid=True,
                gridcolor='rgba(255, 255, 255, 0.3)',
                gridwidth=1,
                tickfont=dict(color='white', size=12)
            ),
            bgcolor='#0E1117'
        ),
        showlegend=False,
        margin=dict(t=40, b=40, l=40, r=40),
        height=910,
        width=910,
        paper_bgcolor='#0E1117',
        plot_bgcolor='#0E1117'
    )
    
    st.plotly_chart(fig, use_container_width=False)
    
    # Additional insights (keeping only the nighttime/daytime distribution)
    time_dist_data = get_sleep_time_distribution_data(df, interval_minutes=15)
    if len(time_dist_data) > 0:
        total_sleep_hours = time_dist_data['total_hours'].sum()
        
        nighttime_hours = time_dist_data[
            (time_dist_data['time_slot'] >= 84) |  # 21:00 and later (84 * 15min = 1260min = 21:00)  
            (time_dist_data['time_slot'] <= 32)    # 08:00 and earlier (32 * 15min = 480min = 08:00)
        ]['total_hours'].sum()
        
        if total_sleep_hours > 0:
            nighttime_percentage = (nighttime_hours / total_sleep_hours) * 100
            st.info(f"**Sleep Distribution:** {nighttime_percentage:.1f}% nighttime (9PM-8AM), {100-nighttime_percentage:.1f}% daytime")

def display_sleep_time_polar_plot_nap_view(df):
    """Display 24-hour sleep distribution as a polar plot scaled for nap visibility (10am-7pm range)"""
    
    from .data_processor import get_sleep_time_distribution_data
    
    time_dist_data = get_sleep_time_distribution_data(df, interval_minutes=15)
    
    if time_dist_data is None or len(time_dist_data) == 0:
        st.warning("No data available for nap view analysis")
        return
    
    if len(time_dist_data) == 0:
        st.info("No sleep time distribution data to display for nap view")
        return
    
    # Calculate daytime range (10am to 7pm)
    # 10:00 AM = slot 40 (10 * 4 slots per hour)
    # 7:00 PM = slot 76 (19 * 4 slots per hour) 
    daytime_start_slot = 10 * 4  # 10am
    daytime_end_slot = 19 * 4    # 7pm
    
    # Find maximum sleep value in daytime range for scaling
    daytime_data = time_dist_data[
        (time_dist_data['time_slot'] >= daytime_start_slot) & 
        (time_dist_data['time_slot'] <= daytime_end_slot)
    ]
    
    if len(daytime_data) == 0 or daytime_data['total_hours'].max() == 0:
        st.info("No daytime sleep detected for nap view (10am-7pm range)")
        return
    
    daytime_max = daytime_data['total_hours'].max()
    radial_max = max(daytime_max * 1.2, 0.1)  # Add 20% padding, minimum 0.1 hour
    
    # Create polar plot with daytime scaling
    fig = go.Figure(go.Scatterpolar(
        r=time_dist_data['total_hours'],
        theta=time_dist_data['degrees'],
        mode='lines+markers',
        fill='toself',
        name='Sleep Hours',
        line=dict(color='rgba(255, 165, 0, 0.9)', width=2),  # Orange line for nap view
        fillcolor='rgba(255, 140, 0, 0.4)',  # Dark orange fill
        marker=dict(size=4, color='rgba(255, 165, 0, 0.9)'),
        hovertemplate='<b>Time:</b> %{customdata}<br><b>Total Sleep:</b> %{r:.1f} hours<extra></extra>',
        customdata=time_dist_data['time_label']
    ))
    
    # Create time labels for angular axis (every hour)
    hour_ticks = list(range(0, 360, 15))  # Every 15 degrees = every hour
    hour_labels = [f"{i//15:02d}:00" for i in hour_ticks]
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                title="Total Hours Slept",
                range=[0, radial_max],
                tickmode='linear',
                tick0=0,
                dtick=max(0.05, radial_max//5),  # Smaller tick intervals for nap scale
                title_font=dict(color='white'),
                tickfont=dict(color='white'),
                gridcolor='rgba(255, 255, 255, 0.3)'
            ),
            angularaxis=dict(
                tickmode='array',
                tickvals=hour_ticks,
                ticktext=hour_labels,
                direction='clockwise',
                rotation=90,  # Start at top (midnight)
                showgrid=True,
                gridcolor='rgba(255, 255, 255, 0.3)',
                gridwidth=1,
                tickfont=dict(color='white', size=12)
            ),
            bgcolor='#0E1117'
        ),
        showlegend=False,
        margin=dict(t=40, b=40, l=40, r=40),
        height=910,
        width=910,
        paper_bgcolor='#0E1117',
        plot_bgcolor='#0E1117'
    )
    
    st.plotly_chart(fig, use_container_width=False)
    
    # Display nap-specific insights
    total_daytime_hours = daytime_data['total_hours'].sum()
    if total_daytime_hours > 0:
        peak_nap_slot = daytime_data.loc[daytime_data['total_hours'].idxmax()]
        st.info(f"**Nap Insights:** Peak daytime sleep at {peak_nap_slot['time_label']} ({peak_nap_slot['total_hours']:.2f} hours). Total daytime sleep: {total_daytime_hours:.1f} hours") 