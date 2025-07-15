# Google Drive Sync Integration Plan

## 🚨 **CRITICAL SECURITY ISSUE - TOP PRIORITY**

**SECURITY VULNERABILITY DISCOVERED**: Personal Google Drive folder IDs were publicly exposed. They have now been **removed**:
- Manual backups folder ID: `YOUR_FOLDER_ID_HERE`
- Automated backups folder ID: `YOUR_FOLDER_ID_HERE`

**IMMEDIATE ACTION REQUIRED**:
1. **Remove hardcoded folder IDs** from `docs/README.md`
2. **Replace with placeholder text** (e.g., `YOUR_FOLDER_ID_HERE`)
3. **Review Google Drive folder permissions** - these IDs may give unauthorized access
4. **Consider rotating/changing folder IDs** if sensitive data is exposed

**WHY THIS IS CRITICAL**: These folder IDs are personal identifiers that could allow unauthorized access to your Google Drive folders. This violates the security principle established in this plan where all secrets should be in the `secrets/` folder.

---

## Current Status of Implementation
As of the latest efforts, all five phases have been implemented with code additions to `src/gdrive_sync.py`, `src/db_manager.py`, `src/data_loader.py`, `main.py`, and tests. Feature flags (ENABLE_GDRIVE_SYNC and ENABLE_DB) added to `src/config.py` and integrated into `data_loader.py` and `main.py` to allow disabling sync and DB for stability. DB reading temporarily disabled to revert to CSV loading due to persistent SQL errors. Changes committed to new 'gdrive-sync-buggy' branch, pushed to GitHub; fixed future-dated commit issue for heatmap visibility. Key achievements:
- Authentication and config loading from `secrets/`.
- File detection refined for 'Sleep as Android Data.zip'.
- Download and extraction logic.
- DB schema and operations (with fixes for reserved keywords).
- Sidebar sync button.

However, errors have been encountered during runtime:
- **Circular Imports**: Resolved via lazy imports, but some persisted initially.
- **Import Errors**: Functions not found, addressed by correcting sources.
- **SQLite Syntax Error**: Fixed by quoting reserved column names like "From" and "To".
- **Streamlit Cache Errors**: Related to caching failures, possibly triggered by the above issues.
- Persistent DB errors led to full disable via flags.

No further code changes are being made until reviewed. The plan below has been updated with phase status.

This document outlines a detailed, phased plan for implementing a modular Google Drive sync feature. The goal is to automatically fetch sleep data from ZIP files containing CSVs in a specified Google Drive folder, extract and process new data (2025+ only), and store it incrementally in a local SQLite database. This will integrate with the existing app structure without disrupting current functionality.

The implementation will be modular, adding a new module (e.g., `src/gdrive_sync.py`) that can be called from `data_loader.py`. Secrets (e.g., Google API credentials, folder IDs) will be stored in a new `secrets/` folder, excluded via `.gitignore`.

## Key Requirements
- **Modular Design**: Separate concerns (auth, file handling, data processing, DB ops) into functions/classes.
- **Data Flow**: Download ZIP from Drive → Extract CSV → Parse/filter 2025+ data → Merge new records into local SQLite DB → App loads from DB instead of CSV.
- **Scope**: Only process data where 'From' year >= 2025.
- **Security**: Use `secrets/` for sensitive info (e.g., `secrets/gdrive_credentials.json`, `secrets/config.toml` for folder ID). Add `secrets/` to `.gitignore`.
- **Dependencies**: Add `google-api-python-client`, `google-auth-httplib2`, `google-auth-oauthlib`, and `sqlite3` (built-in) to `requirements.txt`.
- **Error Handling**: Graceful failures, logging, and user notifications via Streamlit session state.
- **Integration**: Trigger sync optionally (e.g., button in sidebar) or on app start if configured.

## Phased Implementation Plan

### Phase 1: Setup and Authentication
**Status**: Completed. Authentication works, but tested standalone due to import issues.
**Goal**: Establish secure Google Drive API access.
- Create `secrets/` folder and add to `.gitignore`.
- Generate Google API credentials (OAuth client ID) via Google Cloud Console (instructions in README.md update).
- Store credentials in `secrets/gdrive_credentials.json`.
- Store config (e.g., Drive folder ID) in `secrets/config.toml` (use `toml` library to read).
- In `src/gdrive_sync.py`, implement authentication using `google-auth-oauthlib` and `google-api-python-client`:
  - Function: `authenticate_gdrive()` → Returns authorized Drive service object.
  - Handle token refresh and store token in `secrets/token.json`.
- Test: Standalone script to list files in the target folder.

**Milestones**:
- New files: `secrets/.gitignore` (empty), `secrets/config.toml` template.
- Update `requirements.txt` with Google libs.

### Phase 2: File Detection and Download
**Status**: Completed. Detection updated for specific ZIP name.
**Goal**: Identify and download the latest ZIP file from Drive.
- Function: `find_latest_zip(service, folder_id)` → Queries Drive API for ZIP files in the folder, sorts by modified time, returns file ID of the latest.
- Function: `download_zip(service, file_id, local_path)` → Downloads the ZIP to a temp location (e.g., `data/temp/`).
- Extract CSV from ZIP using `zipfile` module.
- Handle errors: If no ZIP found, fall back to existing local data; notify user.

**Milestones**:
- Test downloading and extracting a sample ZIP.
- Ensure only processes ZIPs with CSVs matching the sleep export format.

### Phase 3: Data Processing and Filtering
**Status**: Partially complete. Processing logic moved inside functions, but `process_new_data` needs definition.
**Goal**: Parse extracted CSV and filter for 2025+ data.
- Reuse/extend `src/data_loader.py` functions for parsing CSV (e.g., date parsing, timezone handling).
- Function: `process_new_data(csv_path)` → Loads CSV into Pandas DF, filters rows where `df['From'].dt.year >= 2025`, applies existing processing (e.g., numeric conversions).
- Compare with existing DB data to identify truly new records (e.g., by unique 'Id' if available, or timestamp).

**Milestones**:
- Output: Filtered DF of new 2025+ data ready for DB insertion.

### Phase 4: Local SQLite Database Integration
**Status**: Completed, but schema has syntax error due to reserved keyword 'From'.
**Goal**: Store and manage data incrementally in SQLite.
- Create `src/db_manager.py` for DB operations.
- Initialize DB: Schema with tables mirroring CSV structure (e.g., 'sleep_records' with columns like Id, From, To, Hours, etc.).
- Function: `init_db(db_path='data/sleep_data.db')` → Creates DB if not exists.
- Function: `insert_new_data(db_path, new_df)` → Inserts new records, avoids duplicates (e.g., UPSERT on unique key).
- Function: `load_from_db(db_path, year=2025)` → Queries DB for data >= year, returns DF for app use.
- Update `data_loader.py` to prefer loading from DB if available, falling back to CSV.

**Milestones**:
- Test incremental inserts: Simulate adding new data without duplicating old records.
- Ensure DB is lightweight (SQLite is file-based, no server needed).

### Phase 5: App Integration and Testing
**Status**: Completed and refined. A single **🔄 Sync from Google Drive** button now exists in the sidebar; duplicate controls removed. Unit tests pass.
**Goal**: Seamlessly integrate into the dashboard.
- Add sync button in sidebar (e.g., "Sync from Google Drive") that calls `sync_gdrive()` in `src/gdrive_sync.py`.
- This function orchestrates: Auth → Find/Download/Extract → Process → Insert to DB → Clear caches → Rerun app.
- Update `main.py` to load data from DB via `db_manager`.
- Edge Cases: Handle no internet, invalid secrets, empty ZIPs, data conflicts.
- Testing: Unit tests in `tests/test_gdrive_sync.py` for each function; integration test for full sync flow.

**Milestones**:
- Update README.md with setup instructions (e.g., how to get API credentials).
- Ensure no disruption to existing CSV-based loading (e.g., config flag to enable GDrive).

## Risks and Mitigations
- **API Limits**: Google Drive has quotas; mitigate with caching and infrequent syncs (e.g., once per run).
- **Data Privacy**: All processing local; no uploads.
- **Dependencies**: Pin versions in `requirements.txt`.
- **Complexity**: Keep modular—each phase testable independently.

## Timeline Estimate
- Phase 1-2: 1-2 days (setup heavy).
- Phase 3-4: 2-3 days (core logic).
- Phase 5: 1-2 days (integration).
- Total: 1 week, assuming review after each phase.

This plan maintains the project's modular structure and focuses on root causes (e.g., manual exports) by automating sync. Review and provide feedback before proceeding!

## Revised Next Steps
Considering the errors and current disables:
1. **Re-enable and Test DB**: After confirming SQL fixes, set ENABLE_DB=True and test loading/inserts with sample CSV.
2. **Resolve Any Remaining Imports**: Ensure no circular dependencies remain.
3. **Integrate and Test Sync**: Enable flags, test full flow with mock data.
4. **Merge Branch**: Once stable, merge 'gdrive-sync-buggy' to main.
5. **Update Docs**: Finalize README with flag instructions.
6. **Clear Caches**: Run `streamlit cache clear` post-fixes.

Proceed only after user review. Timeline: 1-2 days for fixes.
