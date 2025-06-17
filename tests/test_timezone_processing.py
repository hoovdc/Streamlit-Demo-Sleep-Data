#!/usr/bin/env python3
"""
Test script for timezone processing functionality
"""

import sys
sys.path.append('..')  # Add parent directory to path

import pandas as pd
import pytz
from datetime import datetime

def test_timezone_processing():
    """Test the timezone processing function with sample data"""
    
    # Create sample data with different timezones
    sample_data = {
        'Tz': ['America/Chicago', 'America/Los_Angeles', 'America/New_York'],
        'From': [
            datetime(2025, 1, 15, 22, 30),  # 10:30 PM Chicago time
            datetime(2025, 1, 16, 23, 45),  # 11:45 PM LA time  
            datetime(2025, 1, 17, 7, 15)    # 7:15 AM NYC time
        ],
        'To': [
            datetime(2025, 1, 16, 6, 30),   # 6:30 AM Chicago time
            datetime(2025, 1, 17, 7, 30),   # 7:30 AM LA time
            datetime(2025, 1, 17, 15, 0)    # 3:00 PM NYC time
        ],
        'Hours': [8.0, 7.75, 7.75]
    }
    
    df = pd.DataFrame(sample_data)
    
    print("Original data:")
    print(df[['Tz', 'From', 'To']])
    print()
    
    # Import the timezone processing function
    try:
        from main import process_timezone_aware_dates
        
        # Test conversion to Chicago time
        print("Testing conversion to America/Chicago:")
        df_converted = process_timezone_aware_dates(df.copy(), 'America/Chicago')
        
        print("Converted data:")
        print(df_converted[['Tz', 'From', 'To']])
        print()
        
        # Verify the conversions are timezone-aware
        print("Timezone info:")
        for idx, row in df_converted.iterrows():
            from_tz = row['From'].tz if hasattr(row['From'], 'tz') else 'None'
            to_tz = row['To'].tz if hasattr(row['To'], 'tz') else 'None'
            print(f"Row {idx}: From TZ = {from_tz}, To TZ = {to_tz}")
        
        print("✅ Timezone processing test completed successfully!")
        
    except Exception as e:
        print(f"❌ Error testing timezone processing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_timezone_processing() 