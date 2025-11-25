#!/usr/bin/env python3
"""
Upload tracking for SleepHQ API.

Maintains a JSON file of uploaded files to prevent duplicate uploads.
"""

import json
import logging
import pathlib
from typing import Optional

logger = logging.getLogger(__name__)


class UploadTracker:
    """
    Tracks uploaded files to prevent duplicate uploads.
    
    Attributes:
        tracker_file (pathlib.Path): Path to JSON file storing upload records
        uploads (dict): Dictionary of uploaded files {file_path: timestamp}
    """

    def __init__(self, tracker_file: Optional[pathlib.Path] = None):
        """
        Initialize upload tracker.

        Args:
            tracker_file: Path to tracker JSON file (default: ~/.config/ezshare_resmed/upload_tracker.json)
        """
        if tracker_file is None:
            tracker_file = pathlib.Path("~/.config/ezshare_resmed/upload_tracker.json").expanduser()
        
        self.tracker_file = tracker_file
        self.uploads = {}
        self._load_tracker()

    def _load_tracker(self) -> None:
        """Load upload tracker from file if it exists."""
        if not self.tracker_file.exists():
            logger.debug(f"No existing tracker file at {self.tracker_file}")
            return
        
        try:
            with open(self.tracker_file, 'r') as f:
                self.uploads = json.load(f)
            logger.debug(f"Loaded upload tracker with {len(self.uploads)} entries")
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to load tracker file: {e}")
            self.uploads = {}

    def _save_tracker(self) -> None:
        """Save upload tracker to file."""
        self.tracker_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(self.tracker_file, 'w') as f:
                json.dump(self.uploads, f, indent=2)
            # Set restrictive permissions for security
            self.tracker_file.chmod(0o600)
            logger.debug("Upload tracker saved")
        except IOError as e:
            logger.error(f"Failed to save tracker file: {e}")

    def mark_uploaded(self, file_path: pathlib.Path) -> None:
        """
        Mark a file as uploaded.

        Args:
            file_path: Path to the uploaded file
        """
        # Use absolute path and string as key for consistency
        key = str(file_path.resolve())
        self.uploads[key] = {
            'uploaded_at': json.dumps(str(pathlib.Path(file_path).stat().st_mtime)),
            'filename': file_path.name,
        }
        self._save_tracker()
        logger.debug(f"Marked as uploaded: {file_path.name}")

    def is_uploaded(self, file_path: pathlib.Path) -> bool:
        """
        Check if a file has been uploaded previously.

        Args:
            file_path: Path to check

        Returns:
            bool: True if file was previously uploaded, False otherwise
        """
        key = str(file_path.resolve())
        return key in self.uploads

    def get_uploaded_count(self) -> int:
        """Get total number of tracked uploads."""
        return len(self.uploads)

    def clear_tracker(self) -> None:
        """Clear all upload tracking records."""
        self.uploads = {}
        self._save_tracker()
        logger.info("Upload tracker cleared")

    def remove_file(self, file_path: pathlib.Path) -> None:
        """
        Remove a file from the upload tracker.

        Args:
            file_path: Path to remove from tracking
        """
        key = str(file_path.resolve())
        if key in self.uploads:
            del self.uploads[key]
            self._save_tracker()
            logger.debug(f"Removed from tracker: {file_path.name}")
