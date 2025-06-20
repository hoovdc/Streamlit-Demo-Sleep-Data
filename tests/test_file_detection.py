#!/usr/bin/env python3
"""
Test script for file detection logic with new naming convention
"""

import os
from pathlib import Path
import glob

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

def test_file_detection():
    print("=== File Detection Test ===")
    
    # List all CSV files in data folder
    print("\n1. Available files in data folder:")
    data_folder = Path("data")
    for file in sorted(data_folder.glob("*.csv")):
        print(f"   - {file.name}")
    
    print("\n2. Files in data/old:")
    old_folder = data_folder / "old"
    if old_folder.exists():
        for file in sorted(old_folder.glob("*.csv")):
            print(f"   - {file.name}")
    
    # Test file detection
    print("\n3. File detection result:")
    latest_file = find_latest_data_file()
    if latest_file:
        print(f"   ✅ Latest file detected: {latest_file}")
        
        # Check file size
        file_path = Path(latest_file)
        if file_path.exists():
            size_mb = file_path.stat().st_size / (1024 * 1024)
            print(f"   📊 File size: {size_mb:.1f} MB")
        
    else:
        print("   ❌ No files detected")

if __name__ == "__main__":
    test_file_detection() 