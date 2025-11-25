# SleepHQ Integration Implementation

## Overview

The ezshare_resmed tool has been enhanced to support automatic uploading of CPAP data files to SleepHQ via the SleepHQ API. This integration allows users to automatically sync data from their EZShare WiFi SD card and upload new files to SleepHQ for cloud storage and analysis.

## New Files

### sleephq_client.py
Handles all OAuth2 authentication and file upload functionality with SleepHQ API.

**Key Features:**
- OAuth2 password grant flow authentication
- Automatic token management with expiration handling
- Secure local token storage (with file permissions 0o600)
- Team ID retrieval and caching
- Batch file upload support
- Detailed error handling and logging

**Key Classes:**
- `SleepHQClient`: Main class for SleepHQ API interactions

**Key Methods:**
- `authenticate(username, password)`: Obtain OAuth2 access token
- `is_authenticated()`: Check token validity
- `upload_file(file_path)`: Upload single file
- `upload_files(file_paths)`: Batch upload multiple files

### upload_tracker.py
Tracks uploaded files to prevent duplicate uploads across multiple runs.

**Key Features:**
- JSON-based tracking file
- Prevents duplicate uploads
- Persists upload history
- Simple in-memory cache with file persistence

**Key Classes:**
- `UploadTracker`: Manages upload history

**Key Methods:**
- `mark_uploaded(file_path)`: Record file as uploaded
- `is_uploaded(file_path)`: Check if file was previously uploaded
- `get_uploaded_count()`: Get total upload count

## Modified Files

### ezshare_resmed.py

**Changes:**
1. **Imports**: Added `getpass`, `sleephq_client`, and `upload_tracker` imports
2. **Configuration Parsing**: Added SleepHQ config parsing from `[sleephq]` section
3. **CLI Arguments**: Added three new arguments:
   - `--upload-to-sleephq`: Enable SleepHQ upload
   - `--sleephq-client-id`: OAuth2 client ID
   - `--sleephq-client-secret`: OAuth2 client secret
4. **EZShare Class**: Added `downloaded_files` list attribute to track successfully downloaded files
5. **download_file() Method**: Added line to track successfully downloaded files
6. **Main Function**: 
   - Initialize SleepHQClient if upload enabled
   - Call `upload_to_sleephq()` after successful sync
   - New helper function `upload_to_sleephq()` handles:
     - File filtering (only EDF and data files)
     - Authentication prompting
     - Tracker-based duplicate prevention
     - Batch upload with error handling

### ezshare_resmed_example_config.ini

**Added Section:**
```ini
[sleephq]
enabled = False
client_id = your_sleephq_client_id
client_secret = your_sleephq_client_secret
```

### README.md

**Added Section:**
- Complete SleepHQ Integration documentation
- Prerequisites and setup instructions
- Configuration examples
- Usage walkthrough
- OAuth2 credential setup guidance
- Cron scheduling examples for Raspberry Pi
- Troubleshooting guide

## File Upload Behavior

When SleepHQ upload is enabled:

1. Data is downloaded from EZShare as normal
2. Successfully downloaded files are tracked in `downloaded_files` list
3. After download completes, files are filtered to include only:
   - `.edf` files (ResMed CPAP data)
   - `.csv` files (exported data)
   - `.txt` files (logs/reports)
4. Files already tracked in upload_tracker.json are skipped
5. Remaining files are uploaded via SleepHQ API
6. Successfully uploaded files are recorded in upload_tracker.json

## Authentication Flow

1. **First Run**: User prompted for SleepHQ username and password
2. **OAuth2 Exchange**: Credentials exchanged for access token
3. **Team ID Retrieval**: Primary team ID retrieved from API
4. **Token Storage**: Token and team ID stored locally at `~/.config/ezshare_resmed/sleephq_token.json`
5. **Subsequent Runs**: Stored token loaded automatically
6. **Token Expiration**: Handled gracefully with re-authentication prompt

## Error Handling

- Network failures: Logged and gracefully handled
- Authentication errors: User prompted to re-authenticate
- Upload failures: Recorded but don't stop overall process
- Invalid credentials: Caught during OAuth2 exchange
- Missing credentials: Skips upload with warning

## Security Considerations

1. **Token Storage**: Protected with 0o600 file permissions
2. **Credentials**: Never stored locally; only tokens
3. **Prompts**: Passwords entered via getpass (hidden input)
4. **HTTPS**: All API communication over HTTPS
5. **Scope Control**: OAuth2 scope limited to "read write delete"

## Raspberry Pi Setup

For scheduled automated uploads on Raspberry Pi:

```bash
# Install dependencies (if not already done)
pip install -r requirements.txt

# Set up cron job
crontab -e

# Add line for periodic syncs (example: every 6 hours)
0 */6 * * * /path/to/ezshare_resmed --upload-to-sleephq
```

With config file approach:
```bash
0 */6 * * * /path/to/ezshare_resmed --config /path/to/config.ini
```

## SleepHQ API Integration

- **Authentication Endpoint**: `https://sleephq.com/oauth/token`
- **Teams Endpoint**: `https://sleephq.com/api/v1/teams`
- **Upload Endpoint**: `POST https://sleephq.com/api/v1/teams/{team_id}/imports`
- **Grant Type**: OAuth2 password grant (per SleepHQ documentation)
- **Token Lifespan**: 2 hours (standard from API, handled with expiration logic)

Reference: https://sleephq.com/api-docs/index.html

## Testing Recommendations

1. Test authentication with valid/invalid credentials
2. Verify token caching across multiple runs
3. Confirm duplicate upload prevention
4. Test with actual CPAP data files
5. Verify error handling for network failures
6. Test on Raspberry Pi environment
7. Validate cron job execution

## Future Enhancements

- Token refresh token support (when SleepHQ API supports it)
- Keyring integration for secure credential storage
- More granular file filtering options
- Upload retry logic with backoff
- Progress indication for batch uploads
- Support for other CPAP device formats
