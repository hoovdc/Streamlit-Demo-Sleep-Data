# Sleep Data Dashboard

A Streamlit dashboard for visualizing and analyzing sleep data from Sleep as Android exports.

## 🚀 Quick Start

1. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Place your sleep data in the `data` folder using the supported naming convention (see below).

3. Run the dashboard:
   ```bash
   streamlit run main.py
   ```

The application will automatically open in your default web browser at `http://localhost:8501`.

## 📁 Data File Structure

The dashboard automatically finds and loads the most recent data file using this priority order:

### Preferred Format (2025-only data)
```
data/
├── 20250617_sleep-export_2025only.csv    # ← Latest 2025-only export (preferred)
├── 20250327_sleep-export_2025only.csv    # ← Older 2025-only export  
└── old/
    └── 20250327_sleep-export_2025only.csv
```

### Full Dataset Format
```
data/
├── 20250617_sleep-export.csv             # ← Latest full export
├── 20250327_sleep-export.csv             # ← Older full export
└── old/
    └── 20250327_sleep-export.csv
```

### Legacy Format (fallback)
```
data/
└── sleep-export.csv                      # ← Original format
```

## 📊 Exporting Data from Sleep as Android

### Manual Export Method
1. Open Sleep as Android app on your phone
2. Go to Settings → Services → Export data
3. Choose "Export to Google Drive" or "Export to file"
4. Save the exported file to your computer
5. Rename using the convention: `YYYYMMDD_sleep-export_2025only.csv`
6. Place in the `data/` folder of this project

### Automated Google Drive Method (Planned)
The app will eventually support:
1. Connecting to your Google Drive Sleep as Android backup folder
2. Automatically extracting the latest ZIP exports
3. Filtering to 2025-only data for optimal performance
4. Updating the dashboard with the newest data

**Google Drive Folders:**
- Manual backups: [Sleep as Android folder](https://drive.google.com/drive/u/0/folders/15kBAnQDMFdSud2WRF5VwtgCzKd1Jo6gA)
- Automated backups: [Sleep Cloud backup folder](https://drive.google.com/drive/u/0/folders/1oFWJdhD73s9wVDTVCexmj9LslWSqIKAB)

## ✨ Features

### 📊 Sleep Duration Analysis
- **Daily Sleep Tracking**: Bar chart showing total sleep hours per day
- **Sleep Distribution**: Histogram of sleep duration patterns
- **Weekly Patterns**: Average sleep by day of the week
- **Multi-Sleep Days**: Detection and analysis of days with multiple sleep periods
- **Sleep Statistics**: Average, median, range, and consistency metrics

### 🎯 Sleep Quality Metrics
- **Quality Indicators**: Deep sleep, cycles, snoring, and noise analysis
- **Trend Analysis**: Quality metrics tracked over time
- **Correlation Analysis**: Relationships between different sleep factors
- **Interactive Visualization**: Select which metrics to compare

### 📅 Sleep Pattern Analysis
- **Bedtime/Wake Time Distribution**: When you typically go to bed and wake up
- **Schedule Consistency**: Day-to-day variation in sleep timing
- **Sleep Phase Detection (experimental)**: Limited preview that lists phase events if present; full analysis planned
- **Pattern Recognition**: Identify trends in your sleep schedule

### 🌍 Timezone Support
- **Automatic Timezone Detection**: Reads timezone information from your data
- **Smart Conversion**: Converts all sleep times to your selected timezone
- **Multi-Timezone Support**: Handles travel and timezone changes automatically
- **Timezone Selection**: Choose your preferred display timezone from the sidebar

### 🔧 Troubleshooting Tools
- **Data Validation**: Automatic detection of common CSV issues
- **File Upload**: Manual file upload if automatic detection fails
- **Format Guidance**: Instructions for preparing data files
- **Error Diagnostics**: Clear error messages and solution suggestions

### 📢 Notification System
- **Centralized Notifications**: All system messages, warnings, and processing updates are contained within the "Notifications" tab for a clean, uncluttered main interface
- **Processing Updates**: Data loading progress, timezone conversion status, and data validation results
- **No Home Page Clutter**: The main dashboard remains focused on analysis and visualization

## 🛠️ Technical Details

### Sleep Record Aggregation Logic

The dashboard uses intelligent date assignment to prevent double-counting of sleep periods across dates:

#### **Date Assignment Rules**
1. **Sleep within same day** (e.g., nap from 2:00 PM to 4:00 PM on June 15)
   - → Assigned to **June 15** (start date)

2. **Sleep crossing midnight** (e.g., sleep from June 15 11:30 PM to June 16 7:00 AM)
   - → Assigned to **June 16** (wake-up date)

#### **Why This Logic?**
This prevents double-counting issues that could occur with naive start-date assignment:

**Problem Scenario (if using start date only):**
- Sleep 1: June 15 11:30 PM → June 16 7:00 AM = assigned to June 15
- Sleep 2: June 16 10:00 PM → June 17 6:00 AM = assigned to June 16  
- Sleep 3: June 16 11:45 PM → June 17 7:30 AM = assigned to June 16

This would incorrectly show multiple full night's sleep on June 16.

**Current Solution:**
```python
def assign_sleep_date(row):
    start_date = row['From'].date()
    end_date = row['To'].date()
    
    # If sleep spans midnight, assign to wake-up date
    if end_date != start_date:
        return end_date
    else:
        return start_date
```

#### **Daily Aggregation**
- All sleep periods assigned to the same date are **summed together**
- This includes: main sleep + naps + brief interruptions
- Each sleep period is counted exactly once
- Result: Total sleep hours per calendar day

#### **Multiple Sleep Sessions**
The dashboard properly handles:
- **Naps during the day**
- **Split sleep schedules** (e.g., biphasic sleep)
- **Brief interruptions** (when tracking restarts)
- **Tracking errors** (very short sessions)

All sessions for a given date are summed to show total daily sleep.

### Data Processing
- **Smart File Detection**: Automatically finds the latest data file
- **2025 Focus**: Filters data to current year for relevant analysis
- **Multiple Sleep Periods**: Properly handles naps and split sleep
- **Data Validation**: Ensures data quality and consistency

### Performance Optimizations
- **Cached Loading**: Data is cached for faster subsequent loads
- **2025-Only Files**: Preferred smaller files for better performance
- **Efficient Processing**: Optimized pandas operations for large datasets

### File Naming Convention
- `YYYYMMDD_sleep-export_2025only.csv` - 2025-only data (recommended)
- `YYYYMMDD_sleep-export.csv` - Full dataset
- `sleep-export_2025only_YYYYMMDD.csv` - Legacy format (still supported)
- `sleep-export.csv` - Legacy format

## 🐛 Troubleshooting

### Common Issues

**"No data files found"**
- Ensure files are in the `data/` folder
- Check file naming follows the convention above
- Verify CSV format is correct

**"Error parsing date columns"**
- Check that dates are in format: `DD. MM. YYYY HH:MM`
- Ensure no corrupt or missing date entries

**"CSV structure issues"**
- Export a fresh file from Sleep as Android
- Use the file upload feature for manual correction
- Check the Troubleshooting tab in the app

### File Size Optimization
For better performance:
1. Use 2025-only exports when possible
2. Place older/larger files in the `old/` subfolder
3. The app will automatically select the most recent optimized file

## 📈 Planned Features

1. **Automated Data Ingestion**: Direct Google Drive integration
2. **Component Modularization**: Break monolith into separate modules  
3. **Advanced Analytics**: Predictive sleep quality models
4. **Export Features**: PDF reports and data export options
5. **Mobile Responsiveness**: Better mobile viewing experience

## 🔗 Links

- [Sleep as Android Documentation](https://sleep.urbandroid.org/)
- [Streamlit Documentation](https://docs.streamlit.io/)
- [Plotly Documentation](https://plotly.com/python/) 