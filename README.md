# Sleep Data Dashboard

A Streamlit dashboard for visualizing and analyzing sleep data.

## Setup

1. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Make sure your sleep data is in the `data` folder as `sleep-export.csv`.

## Exporting raw data from SleepCloud, as recorded by Sleep as Android (manual method until API acccess is available)

1. Export from mobile app to Google Drive (it doesn't seem possible to export from SleepCloud website)
   Google Drive folder (manual backups): 
   https://drive.google.com/drive/u/0/folders/15kBAnQDMFdSud2WRF5VwtgCzKd1Jo6gA
2. Import from Google Drive to this app's "data" folder

## Running the Dashboard

To run the dashboard, execute:
```bash
streamlit run main.py
```

The application will start and open in your default web browser at `http://localhost:8501`.

## Features

- **Sleep Duration Analysis**: Track your sleep duration over time and view weekly averages.
- **Sleep Quality Metrics**: Analyze factors that affect your sleep quality.
- **Sleep Patterns**: Discover patterns in your sleep schedule and habits.

## Data Format

The dashboard expects sleep data in CSV format with relevant columns for:
- Dates/times of sleep
- Sleep duration
- Sleep quality metrics
- Any other sleep-related metrics

The dashboard will attempt to automatically detect and use relevant columns from your data. 