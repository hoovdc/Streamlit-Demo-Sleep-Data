# Sleep Data Dashboard

A Streamlit dashboard for visualizing and analyzing sleep data.

## Setup

1. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Make sure your sleep data is in the `data` folder as `sleep-export.csv`.

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