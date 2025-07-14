"""
Google Drive Sync Module
Handles authentication and sync operations for sleep data.
"""

import os
import pickle
import toml
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.errors import HttpError
import io
from zipfile import ZipFile
import pandas as pd

SECRETS_DIR = 'secrets'
CREDENTIALS_FILE = os.path.join(SECRETS_DIR, 'gdrive_credentials.json')
TOKEN_FILE = os.path.join(SECRETS_DIR, 'token.json')
CONFIG_FILE = os.path.join(SECRETS_DIR, 'config.toml')

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

def authenticate_gdrive():
    """
    Authenticate with Google Drive API and return the service object.
    Handles token refresh and initial authorization flow.
    """
    creds = None
    
    # Load existing token if available
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)
    
    # Refresh token if expired
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    elif not creds or not creds.valid:
        # Run authorization flow
        if os.path.exists(CREDENTIALS_FILE):
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
            # Save the credentials for next run
            with open(TOKEN_FILE, 'wb') as token:
                pickle.dump(creds, token)
        else:
            raise FileNotFoundError(f"Credentials file not found at {CREDENTIALS_FILE}")
    
    # Build and return the Drive service
    service = build('drive', 'v3', credentials=creds)
    return service

def load_config():
    """
    Load configuration from config.toml.
    Returns dict with config values.
    """
    if os.path.exists(CONFIG_FILE):
        return toml.load(CONFIG_FILE)
    else:
        raise FileNotFoundError(f"Config file not found at {CONFIG_FILE}") 

def find_latest_zip(service, folder_id):
    """
    Find the specific 'Sleep as Android Data.zip' file in the folder.
    Returns the file ID or None if not found.
    """
    try:
        query = f"'{folder_id}' in parents and name = 'Sleep as Android Data.zip' and trashed = false"
        results = service.files().list(
            q=query,
            fields="files(id, name, modifiedTime)"
        ).execute()
        
        files = results.get('files', [])
        if files:
            # Since name is exact, return the first (should be only one)
            return files[0]['id']
        return None
    except HttpError as e:
        raise RuntimeError(f"Error finding ZIP file: {e}")

def download_zip(service, file_id, local_path='data/temp/latest_sleep.zip'):
    """
    Download the ZIP file from Google Drive to local path.
    Returns the path to the downloaded ZIP and extracts CSV if present.
    """
    try:
        request = service.files().get_media(fileId=file_id)
        file_content = io.BytesIO()
        downloader = request.execute() if hasattr(request, 'execute') else request()  # Handle streaming if needed
        with open(local_path, 'wb') as f:
            f.write(downloader)
        
        # Extract CSV from ZIP
        with ZipFile(local_path, 'r') as zip_ref:
            csv_files = [f for f in zip_ref.namelist() if f.endswith('.csv')]
            if not csv_files:
                raise ValueError("No CSV found in ZIP")
            # Extract the first CSV (assuming one per ZIP)
            extracted_csv = zip_ref.extract(csv_files[0], path='data/temp/')
        
        return extracted_csv
    except HttpError as e:
        raise RuntimeError(f"Error downloading ZIP: {e}") 

def sync_gdrive():
    """
    Full sync orchestration: Auth, find/download/extract, process, insert to DB.
    Returns updated DataFrame from DB.
    """
    # Lazy imports inside function to avoid circular imports
    from src.data_loader import process_timezone_aware_dates, assign_sleep_date  # Use existing processing functions
    from src.db_manager import insert_new_data, load_from_db
    
    config = load_config()
    folder_id = config['gdrive']['folder_id']
    service = authenticate_gdrive()
    latest_zip_id = find_latest_zip(service, folder_id)
    if not latest_zip_id:
        raise ValueError("No ZIP files found in folder")
    
    csv_path = download_zip(service, latest_zip_id)
    new_df = pd.read_csv(csv_path)
    
    # Apply processing (reuse from data_loader)
    new_df = process_timezone_aware_dates(new_df)
    new_df['Date'] = new_df.apply(assign_sleep_date, axis=1)  # Example processing
    new_df = new_df[new_df['From'].dt.year >= 2025]  # Filter 2025+
    
    insert_new_data(new_df)
    
    # Clean up temp files
    os.remove(csv_path)
    
    return load_from_db() 