"""
SQLite Database Manager for Sleep Data
Handles incremental storage and loading of sleep records.
"""

import sqlite3
import pandas as pd
from datetime import datetime

DB_PATH = 'data/sleep_data.db'
TABLE_NAME = 'sleep_records'

# Define schema based on common columns (expand as needed)
SCHEMA = """
CREATE TABLE IF NOT EXISTS sleep_records (
    Id TEXT PRIMARY KEY,
    Tz TEXT,
    "From" DATETIME,
    "To" DATETIME,
    Sched DATETIME,
    Hours REAL,
    Rating REAL,
    Comment TEXT,
    Framerate INTEGER,
    Snore REAL,
    Noise REAL,
    Cycles INTEGER,
    DeepSleep REAL,
    LenAdjust INTEGER,
    Geo TEXT
);
"""

def init_db(db_path=DB_PATH):
    """
    Initialize the SQLite database and create table if not exists.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.executescript(SCHEMA)
    conn.commit()
    conn.close()

def insert_new_data(df, db_path=DB_PATH):
    """
    Insert new data into DB, skipping duplicates based on Id.
    Filters for year 2025+.
    """
    init_db(db_path)  # Ensure DB and table exist before writing
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Filter df for 2025+
    df['From'] = pd.to_datetime(df['From'])
    df = df[df['From'].dt.year >= 2025]
    
    for _, row in df.iterrows():
        cursor.execute(f"""
            INSERT OR IGNORE INTO sleep_records 
            (Id, Tz, "From", "To", Sched, Hours, Rating, Comment, Framerate, Snore, Noise, Cycles, DeepSleep, LenAdjust, Geo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            row['Id'], row['Tz'], row['From'], row['To'], row['Sched'], row['Hours'], row['Rating'], 
            row['Comment'], row.get('Framerate'), row.get('Snore'), row.get('Noise'), row.get('Cycles'), 
            row.get('DeepSleep'), row.get('LenAdjust'), row.get('Geo')
        ))
    
    conn.commit()
    conn.close()

def load_from_db(db_path=DB_PATH):
    """
    Load all records from DB into DataFrame.
    """
    init_db(db_path)  # Ensure DB and table exist before reading
    conn = sqlite3.connect(db_path)
    query = 'SELECT * FROM sleep_records'
    df = pd.read_sql_query(query, conn, parse_dates=["From", "To", "Sched"])
    conn.close()
    return df 