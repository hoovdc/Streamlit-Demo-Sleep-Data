"""
Configuration settings for the Sleep Data Dashboard
"""
import streamlit as st

# Page Configuration
def configure_page():
    """Configure Streamlit page settings"""
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

# Custom CSS
CUSTOM_CSS = """
<style>
    .stApp header {
        position: sticky;
        top: 0px;
        z-index: 999;
    }
    
    /* Zoom out the entire app to reduce oversized appearance */
    .stApp {
     /*   zoom: 0.95; */
    }
    
    /* Make content fill the window horizontally */
    .main .block-container {
        max-width: none !important;
        width: 100% !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }
    
    /* Ensure full width for charts and content */
    div[data-testid="stPlotlyChart"] {
        width: 100% !important;
    }
    
    /* Full width for dataframes */
    div[data-testid="stDataFrame"] {
        width: 100% !important;
    }
    
    /* Full width for metrics containers */
    div[data-testid="metric-container"] {
        width: 100% !important;
    }
    
    /* Reduce vertical spacing between components - More specific selectors */
    .main .block-container .element-container {
        margin-bottom: 0.02rem !important;
        margin-top: 0.02rem !important;
    }
    
    /* Target specific Streamlit components */
    div[data-testid="stMarkdownContainer"] {
        margin-bottom: 0.02rem !important;
    }
    
    div[data-testid="metric-container"] {
        margin-bottom: 0.02rem !important;
    }
    
    div[data-testid="stVerticalBlock"] > div {
        gap: 0.02rem !important;
    }
    
    /* Reduce spacing around headers */
    .main h1, .main h2, .main h3 {
        margin-top: 0.02rem !important;
        margin-bottom: 0.02rem !important;
    }
    
    /* Reduce spacing in columns */
    div[data-testid="column"] {
        padding-bottom: 0.02rem !important;
        padding-top: 0.02rem !important;
    }
    
    /* Reduce spacing between plotly charts */
    div[data-testid="stPlotlyChart"] {
        margin-bottom: 0.02rem !important;
    }
</style>
"""

def apply_custom_styling():
    """Apply custom CSS styling"""
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# Application Constants
APP_TITLE = "😴 Sleep Data Dashboard"

# Data Constants
DATA_FOLDER = "data"
DATE_FORMAT = '%d. %m. %Y %H:%M'
TARGET_YEAR = 2025

# File Patterns (in priority order)
FILE_PATTERNS = [
    "*_sleep-export_2025only.csv",      # YYYYMMDD_sleep-export_2025only.csv (preferred)
    "*_sleep-export.csv",               # YYYYMMDD_sleep-export.csv (full dataset)
    "sleep-export_2025only_*.csv",      # Legacy: sleep-export_2025only_YYYYMMDD.csv
    "sleep-export_*.csv",               # Legacy: sleep-export_YYYYMMDD.csv
    "sleep-export.csv"                  # Legacy: sleep-export.csv
]

# Column Names
BASIC_COLUMNS = ['Id', 'Tz', 'From', 'To', 'Sched', 'Hours', 'Rating', 'Comment', 
                 'Framerate', 'Snore', 'Noise', 'Cycles', 'DeepSleep', 'LenAdjust', 'Geo']

DATE_COLUMNS = ['From', 'To', 'Sched']
NUMERIC_COLUMNS = ['Hours', 'Rating', 'Snore', 'Noise', 'Cycles', 'DeepSleep', 'LenAdjust']
QUALITY_METRICS = ['DeepSleep', 'Cycles', 'Snore', 'Noise']

# Timezone Constants
DEFAULT_TIMEZONE = 'America/Chicago'
COMMON_TIMEZONES = [
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

# Chart Configuration
IDEAL_SLEEP_HOURS = 8
MAX_REASONABLE_DAILY_SLEEP = 12
CHART_HEIGHT = 400 

# Feature Flags
ENABLE_GDRIVE_SYNC = False  # Set to True to enable Google Drive sync
ENABLE_DB = False  # Set to True to enable local SQLite DB loading 