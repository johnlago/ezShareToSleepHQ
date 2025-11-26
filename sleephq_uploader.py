import logging
import getpass
import pathlib

logger = logging.getLogger('ezshare_resmed')

def upload_to_sleephq(ezshare, sleephq_client, verbose, force=False, username=None, password=None):
    """
    Uploads the entire SD card mirror directory to SleepHQ.

    SleepHQ expects the complete SD card structure for each import and will
    deduplicate the data during processing.

    Args:
        ezshare (EZShare): The EZShare object.
        sleephq_client (SleepHQClient): The SleepHQ client object.
        verbose (bool): If verbose output should be shown.
        force (bool): If True, upload even if no new files were downloaded.
        username (str, optional): SleepHQ username for non-interactive auth.
        password (str, optional): SleepHQ password for non-interactive auth.
    """
    # Only upload if new files were downloaded (unless force is set)
    if not force and not ezshare.downloaded_files:
        logger.info("No files downloaded in this sync, skipping SleepHQ upload")
        return
    
    # Authenticate if not already authenticated
    if not sleephq_client.is_authenticated():
        if username and password:
            logger.info("Authenticating with SleepHQ using provided credentials")
            if not sleephq_client.authenticate(username, password):
                logger.error("Failed to authenticate with SleepHQ using provided credentials")
                return
        else:
            # Prompt for credentials
            print("\nSleepHQ authentication required")
            username = input("SleepHQ username/email: ").strip()
            password = getpass.getpass("SleepHQ password: ")
            
            if not sleephq_client.authenticate(username, password):
                logger.error("❌ Failed to authenticate with SleepHQ")
                return
    
    # Collect files to upload based on incremental strategy
    # 1. Mandatory files (STR.edf, Identification.crc, Identification.json)
    # 2. SETTINGS/ folder contents
    # 3. DATALOG/ subfolders that have new data (or all if force=True)
    
    files_to_upload = []
    added_paths = set()

    def add_file(path):
        if path.is_file() and not path.name.startswith('.') and path not in added_paths:
            files_to_upload.append(path)
            added_paths.add(path)

    # 1. Mandatory Root Files
    MANDATORY_FILES = {'STR.edf', 'Identification.crc', 'Identification.json'}
    for filename in MANDATORY_FILES:
        f = ezshare.path / filename
        if f.exists():
            add_file(f)

    # 2. SETTINGS folder
    settings_dir = ezshare.path / 'SETTINGS'
    if settings_dir.exists():
        for f in settings_dir.rglob('*'):
            add_file(f)

    # 3. DATALOG folders
    # Identify "active" DATALOG folders from downloaded_files
    active_datalog_folders = set()
    if not force:
        for downloaded_file in ezshare.downloaded_files:
            path = pathlib.Path(downloaded_file)
            try:
                # Check if file is inside a DATALOG subfolder
                rel_path = path.relative_to(ezshare.path)
                parts = rel_path.parts
                if len(parts) >= 3 and parts[0] == 'DATALOG':
                    # parts[0] is DATALOG, parts[1] is the date folder
                    active_datalog_folders.add(parts[1])
            except ValueError:
                continue
    
    datalog_dir = ezshare.path / 'DATALOG'
    if datalog_dir.exists():
        for date_folder in datalog_dir.iterdir():
            if not date_folder.is_dir():
                continue
            
            # Include if force=True or if it's an active folder
            if force or date_folder.name in active_datalog_folders:
                for f in date_folder.rglob('*'):
                    add_file(f)
    
    if not files_to_upload:
        logger.info("No data files found in SD card directory")
        return
    
    # Upload files
    logger.info(f"Found {len(files_to_upload)} file(s) in {ezshare.path} to upload to SleepHQ")
    logger.debug(f"Files to upload: {[str(f) for f in files_to_upload[:10]]}{'...' if len(files_to_upload) > 10 else ''}")
    successful, failed = sleephq_client.upload_files(
        files_to_upload,
        base_path=ezshare.path,
        overwrite=force,
    )
    
    logger.info(f"✅ SleepHQ upload complete: {successful} successful, {failed} failed")
