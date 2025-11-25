import logging
import getpass
import pathlib

logger = logging.getLogger('ezshare_resmed')

def upload_to_sleephq(ezshare, sleephq_client, verbose, force=False):
    """
    Uploads the entire SD card mirror directory to SleepHQ.

    SleepHQ expects the complete SD card contents for each import and will
    deduplicate the data during processing.

    Args:
        ezshare (EZShare): The EZShare object.
        sleephq_client (SleepHQClient): The SleepHQ client object.
        verbose (bool): If verbose output should be shown.
        force (bool): If True, upload even if no new files were downloaded.
    """
    # Only upload if new files were downloaded (unless force is set)
    if not force and not ezshare.downloaded_files:
        logger.info("No files downloaded in this sync, skipping SleepHQ upload")
        return
    
    # Authenticate if not already authenticated
    if not sleephq_client.is_authenticated():
        # Prompt for credentials
        print("\nSleepHQ authentication required")
        username = input("SleepHQ username/email: ").strip()
        password = getpass.getpass("SleepHQ password: ")
        
        if not sleephq_client.authenticate(username, password):
            logger.error("Failed to authenticate with SleepHQ")
            return
    
    # Collect ALL files from the SD card mirror directory
    # SleepHQ will deduplicate during processing
    # Skip only known system files that shouldn't be uploaded
    SKIP_FILES = {'JOURNAL.JNL', '.DS_Store', 'Thumbs.db'}
    
    files_to_upload = []
    for file_path in ezshare.path.rglob('*'):
        if not file_path.is_file():
            continue
        # Skip known system files
        if file_path.name in SKIP_FILES:
            continue
        # Skip hidden files (starting with .)
        if file_path.name.startswith('.'):
            continue
        files_to_upload.append(file_path)
    
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
    
    logger.info(f"SleepHQ upload complete: {successful} successful, {failed} failed")
