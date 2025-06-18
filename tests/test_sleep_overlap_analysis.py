#!/usr/bin/env python3
"""
Sleep Record Overlap Analysis Test Script

This script analyzes sleep data to detect and resolve questions about:
1. Temporal overlaps between sleep records
2. Date assignment logic validation
3. Aggregation accuracy verification
4. Multiple sleep session analysis

Usage:
    python tests/test_sleep_overlap_analysis.py
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import sys
import os

# Add the parent directory to the path so we can import from main.py
sys.path.append(str(Path(__file__).parent.parent))

def find_latest_data_file():
    """Find the latest data file (copied from main.py)"""
    data_dir = Path("data")
    if not data_dir.exists():
        return None
    
    # Priority order for file patterns
    patterns = [
        "????????_sleep-export_2025only.csv",  # YYYYMMDD_sleep-export_2025only.csv
        "????????_sleep-export.csv",           # YYYYMMDD_sleep-export.csv
        "sleep-export_2025only_????????.csv", # sleep-export_2025only_YYYYMMDD.csv (legacy)
        "sleep-export_????????.csv",          # sleep-export_YYYYMMDD.csv (legacy)
        "sleep-export.csv"                    # sleep-export.csv (legacy)
    ]
    
    for pattern in patterns:
        files = list(data_dir.glob(pattern))
        if files:
            # Sort by filename (which includes date) and return the latest
            latest_file = sorted(files, key=lambda x: x.name, reverse=True)[0]
            return str(latest_file)
    
    return None

def load_and_parse_data():
    """Load and parse sleep data"""
    data_file = find_latest_data_file()
    if not data_file:
        print("❌ No data file found!")
        return None
    
    print(f"📊 Loading data from: {Path(data_file).name}")
    
    # Load the data
    df = pd.read_csv(data_file, on_bad_lines='skip', low_memory=False, engine='c')
    
    # Parse date columns
    date_format = '%d. %m. %Y %H:%M'
    for date_col in ['From', 'To', 'Sched']:
        if date_col in df.columns:
            df[date_col] = pd.to_datetime(df[date_col], format=date_format, errors='coerce')
    
    # Filter for 2025 and valid hours
    if 'From' in df.columns and 'Hours' in df.columns:
        df = df[df['From'].dt.year == 2025].copy()
        # Convert Hours to numeric first, then filter
        df['Hours'] = pd.to_numeric(df['Hours'], errors='coerce')
        df = df[df['Hours'] > 0].copy()
        df = df.dropna(subset=['From', 'To', 'Hours'])
    
    print(f"✅ Loaded {len(df)} valid sleep records for 2025")
    return df

def assign_sleep_date(row):
    """Date assignment logic (copied from main.py)"""
    start_date = row['From'].date()
    end_date = row['To'].date()
    
    # If sleep spans midnight, assign to wake-up date
    if end_date != start_date:
        return end_date
    else:
        return start_date

def check_temporal_overlaps(df):
    """Check for temporal overlaps between sleep records"""
    print("\n🔍 ANALYZING TEMPORAL OVERLAPS")
    print("=" * 50)
    
    overlaps = []
    df_sorted = df.sort_values('From').reset_index(drop=True)
    
    for i in range(len(df_sorted) - 1):
        current = df_sorted.iloc[i]
        next_record = df_sorted.iloc[i + 1]
        
        # Check if current sleep ends after next sleep starts
        if current['To'] > next_record['From']:
            overlap_duration = current['To'] - next_record['From']
            overlaps.append({
                'record_1_idx': i,
                'record_2_idx': i + 1,
                'record_1_from': current['From'],
                'record_1_to': current['To'],
                'record_1_hours': current['Hours'],
                'record_2_from': next_record['From'],
                'record_2_to': next_record['To'],
                'record_2_hours': next_record['Hours'],
                'overlap_duration': overlap_duration,
                'overlap_hours': overlap_duration.total_seconds() / 3600
            })
    
    if overlaps:
        print(f"⚠️  Found {len(overlaps)} temporal overlaps!")
        print("\nOverlap Details:")
        for i, overlap in enumerate(overlaps[:5]):  # Show first 5
            print(f"\nOverlap {i+1}:")
            print(f"  Record 1: {overlap['record_1_from']} → {overlap['record_1_to']} ({overlap['record_1_hours']:.2f}h)")
            print(f"  Record 2: {overlap['record_2_from']} → {overlap['record_2_to']} ({overlap['record_2_hours']:.2f}h)")
            print(f"  Overlap:  {overlap['overlap_hours']:.2f} hours")
        
        if len(overlaps) > 5:
            print(f"\n... and {len(overlaps) - 5} more overlaps")
            
        # Analyze overlap patterns
        overlap_hours = [o['overlap_hours'] for o in overlaps]
        print(f"\nOverlap Statistics:")
        print(f"  Average overlap: {np.mean(overlap_hours):.2f} hours")
        print(f"  Maximum overlap: {np.max(overlap_hours):.2f} hours")
        print(f"  Minimum overlap: {np.min(overlap_hours):.2f} hours")
        
    else:
        print("✅ No temporal overlaps found - all sleep records are sequential!")
    
    return overlaps

def analyze_date_assignment(df):
    """Analyze the date assignment logic"""
    print("\n📅 ANALYZING DATE ASSIGNMENT LOGIC")
    print("=" * 50)
    
    # Apply date assignment
    df['assigned_date'] = df.apply(assign_sleep_date, axis=1)
    df['start_date'] = df['From'].dt.date
    df['end_date'] = df['To'].dt.date
    df['crosses_midnight'] = df['start_date'] != df['end_date']
    
    # Statistics
    total_records = len(df)
    crosses_midnight = df['crosses_midnight'].sum()
    same_day = total_records - crosses_midnight
    
    print(f"Sleep Records by Type:")
    print(f"  Same-day sleep:     {same_day:3d} records ({same_day/total_records*100:.1f}%)")
    print(f"  Cross-midnight:     {crosses_midnight:3d} records ({crosses_midnight/total_records*100:.1f}%)")
    print(f"  Total:              {total_records:3d} records")
    
    # Check assignment logic
    print(f"\nDate Assignment Verification:")
    same_day_correct = df[~df['crosses_midnight']]['assigned_date'].equals(df[~df['crosses_midnight']]['start_date'])
    cross_midnight_correct = df[df['crosses_midnight']]['assigned_date'].equals(df[df['crosses_midnight']]['end_date'])
    
    print(f"  Same-day assigned to start date: {'✅' if same_day_correct else '❌'}")
    print(f"  Cross-midnight assigned to end date: {'✅' if cross_midnight_correct else '❌'}")
    
    # Show examples
    if crosses_midnight > 0:
        print(f"\nCross-Midnight Examples:")
        examples = df[df['crosses_midnight']].head(3)
        for _, row in examples.iterrows():
            print(f"  {row['From'].strftime('%Y-%m-%d %H:%M')} → {row['To'].strftime('%Y-%m-%d %H:%M')} "
                  f"= assigned to {row['assigned_date']}")
    
    return df

def analyze_daily_aggregation(df):
    """Analyze daily aggregation and look for suspicious totals"""
    print("\n📊 ANALYZING DAILY AGGREGATION")
    print("=" * 50)
    
    # Group by assigned date
    daily_totals = df.groupby('assigned_date').agg({
        'Hours': ['sum', 'count', 'mean', 'max'],
        'From': 'min',
        'To': 'max'
    }).round(2)
    
    # Flatten column names
    daily_totals.columns = ['total_hours', 'session_count', 'avg_session', 'max_session', 'earliest_start', 'latest_end']
    daily_totals = daily_totals.reset_index()
    
    # Find suspicious days
    suspicious_days = daily_totals[daily_totals['total_hours'] > 12]  # More than 12 hours
    multi_session_days = daily_totals[daily_totals['session_count'] > 1]
    
    print(f"Daily Sleep Summary:")
    print(f"  Total days tracked:           {len(daily_totals)}")
    print(f"  Days with multiple sessions:  {len(multi_session_days)}")
    print(f"  Days with >12 hours sleep:    {len(suspicious_days)}")
    print(f"  Average daily sleep:          {daily_totals['total_hours'].mean():.2f} hours")
    print(f"  Maximum daily sleep:          {daily_totals['total_hours'].max():.2f} hours")
    print(f"  Minimum daily sleep:          {daily_totals['total_hours'].min():.2f} hours")
    
    # Show suspicious days
    if len(suspicious_days) > 0:
        print(f"\n⚠️  Days with >12 hours sleep:")
        for _, day in suspicious_days.head(5).iterrows():
            print(f"  {day['assigned_date']}: {day['total_hours']:.2f}h "
                  f"({day['session_count']} sessions, max: {day['max_session']:.2f}h)")
    
    # Show multi-session days
    if len(multi_session_days) > 0:
        print(f"\n📋 Days with multiple sleep sessions (first 5):")
        for _, day in multi_session_days.head(5).iterrows():
            print(f"  {day['assigned_date']}: {day['total_hours']:.2f}h total "
                  f"({day['session_count']} sessions, avg: {day['avg_session']:.2f}h)")
    
    return daily_totals

def detailed_multi_session_analysis(df):
    """Detailed analysis of multi-session days"""
    print("\n🔬 DETAILED MULTI-SESSION ANALYSIS")
    print("=" * 50)
    
    # Group by date and analyze each day with multiple sessions
    multi_session_dates = df.groupby('assigned_date').size()
    multi_session_dates = multi_session_dates[multi_session_dates > 1].index
    
    if len(multi_session_dates) == 0:
        print("✅ No multi-session days found")
        return
    
    print(f"Analyzing {len(multi_session_dates)} days with multiple sessions...\n")
    
    for date in list(multi_session_dates)[:3]:  # Show first 3 days
        day_data = df[df['assigned_date'] == date].sort_values('From')
        
        print(f"📅 {date} ({len(day_data)} sessions, {day_data['Hours'].sum():.2f}h total):")
        
        for i, (_, session) in enumerate(day_data.iterrows(), 1):
            duration_str = f"{session['From'].strftime('%H:%M')} → {session['To'].strftime('%H:%M')}"
            if session['From'].date() != session['To'].date():
                duration_str += " (+1 day)"
            
            print(f"  Session {i}: {duration_str} = {session['Hours']:.2f}h")
        
        # Check for gaps between sessions
        if len(day_data) > 1:
            print("  Gaps between sessions:")
            for i in range(len(day_data) - 1):
                current_end = day_data.iloc[i]['To']
                next_start = day_data.iloc[i + 1]['From']
                gap = next_start - current_end
                gap_hours = gap.total_seconds() / 3600
                print(f"    Gap {i+1}-{i+2}: {gap_hours:.2f} hours")
        
        print()

def main():
    """Main analysis function"""
    print("🔍 SLEEP RECORD OVERLAP ANALYSIS")
    print("=" * 60)
    print("This script analyzes sleep data for:")
    print("1. Temporal overlaps between records")
    print("2. Date assignment logic validation")  
    print("3. Daily aggregation accuracy")
    print("4. Multi-session day analysis")
    print("=" * 60)
    
    # Load data
    df = load_and_parse_data()
    if df is None or len(df) == 0:
        print("❌ No valid data to analyze")
        return
    
    # Run analyses
    overlaps = check_temporal_overlaps(df)
    df_with_dates = analyze_date_assignment(df)
    daily_totals = analyze_daily_aggregation(df_with_dates)
    detailed_multi_session_analysis(df_with_dates)
    
    # Final summary
    print("\n📋 FINAL SUMMARY")
    print("=" * 50)
    print(f"✅ Analyzed {len(df)} sleep records")
    print(f"📊 Found {len(daily_totals)} unique days")
    print(f"⚠️  Temporal overlaps: {len(overlaps)}")
    print(f"🌙 Cross-midnight sleep: {df_with_dates['crosses_midnight'].sum()}")
    print(f"📅 Multi-session days: {len(daily_totals[daily_totals['session_count'] > 1])}")
    print(f"⏰ Suspicious high totals (>12h): {len(daily_totals[daily_totals['total_hours'] > 12])}")
    
    if len(overlaps) == 0:
        print("\n✅ CONCLUSION: No temporal overlaps found!")
        print("   The date assignment logic should work correctly.")
    else:
        print(f"\n⚠️  CONCLUSION: Found {len(overlaps)} overlaps that need investigation.")
        print("   This could explain unrealistic daily totals.")

if __name__ == "__main__":
    main() 