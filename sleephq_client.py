#!/usr/bin/env python3
"""
SleepHQ API client for uploading CPAP data files.

Handles OAuth2 authentication, token management, team ID retrieval, and file uploads.
"""

import hashlib
import json
import logging
import pathlib
import time
from typing import Optional

import requests

logger = logging.getLogger(__name__)

SLEEPHQ_BASE_URL = "https://sleephq.com"
OAUTH_ENDPOINT = f"{SLEEPHQ_BASE_URL}/oauth/token"
TEAMS_ENDPOINT = f"{SLEEPHQ_BASE_URL}/api/v1/teams"


class SleepHQClient:
    """
    Client for interacting with the SleepHQ API.
    
    Attributes:
        client_id (str): OAuth2 client ID
        client_secret (str): OAuth2 client secret
        username (str): SleepHQ username
        password (str): SleepHQ password
        token_file (pathlib.Path): Path to store access token
        access_token (str): Current access token
        token_expiry (float): Unix timestamp when token expires
        team_id (str): Team ID for API requests
        session (requests.Session): Session for HTTP requests
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        token_file: Optional[pathlib.Path] = None,
        verbose: bool = False,
    ):
        """
        Initialize SleepHQ client.

        Args:
            client_id: OAuth2 client ID
            client_secret: OAuth2 client secret
            token_file: Path to store access token (default: ~/.config/ezshare_resmed/sleephq_token.json)
            verbose: Enable verbose logging
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.username = None
        self.password = None
        self.access_token = None
        self.token_expiry = 0
        self.team_id = None
        
        if token_file is None:
            token_file = pathlib.Path("~/.config/ezshare_resmed/sleephq_token.json").expanduser()
        self.token_file = token_file
        
        self.session = requests.Session()
        self._load_token()

    def _load_token(self) -> None:
        """Load stored access token if it exists and is still valid."""
        if not self.token_file.exists():
            return
        
        try:
            with open(self.token_file, 'r') as f:
                token_data = json.load(f)
            
            self.access_token = token_data.get('access_token')
            self.token_expiry = token_data.get('expires_at', 0)
            self.team_id = token_data.get('team_id')
            
            # Check if token is still valid (with 60 second buffer)
            if time.time() >= self.token_expiry - 60:
                logger.debug("Stored token has expired")
                self.access_token = None
                self.token_expiry = 0
            else:
                logger.debug("Loaded valid stored token")
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to load token file: {e}")
            self.access_token = None
            self.token_expiry = 0

    def _save_token(self) -> None:
        """Save access token to file for future use."""
        self.token_file.parent.mkdir(parents=True, exist_ok=True)
        
        token_data = {
            'access_token': self.access_token,
            'expires_at': self.token_expiry,
            'team_id': self.team_id,
        }
        
        try:
            with open(self.token_file, 'w') as f:
                json.dump(token_data, f)
            # Set restrictive permissions for security
            self.token_file.chmod(0o600)
            logger.debug("Token saved to file")
        except IOError as e:
            logger.error(f"Failed to save token file: {e}")

    def authenticate(self, username: str, password: str) -> bool:
        """
        Authenticate with SleepHQ API using OAuth2 password grant flow.

        Args:
            username: SleepHQ username/email
            password: SleepHQ password

        Returns:
            bool: True if authentication successful, False otherwise
        """
        self.username = username
        self.password = password
        
        logger.debug("Authenticating with SleepHQ API")
        
        try:
            response = requests.post(
                OAUTH_ENDPOINT,
                data={
                    'client_id': self.client_id,
                    'client_secret': self.client_secret,
                    'grant_type': 'password',
                    'username': username,
                    'password': password,
                    'scope': 'read write delete',
                },
                timeout=10,
            )
            response.raise_for_status()
            
            token_data = response.json()
            self.access_token = token_data['access_token']
            # OAuth2 password grant doesn't provide refresh tokens, so we calculate expiry
            self.token_expiry = time.time() + token_data.get('expires_in', 7200)
            
            logger.info("Successfully authenticated with SleepHQ API")
            
            # Retrieve team ID
            if not self._get_team_id():
                logger.warning("Failed to retrieve team ID, but authentication successful")
                return False
            
            # Save token
            self._save_token()
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Authentication failed: {e}")
            return False

    def _get_team_id(self) -> bool:
        """
        Retrieve user's primary team ID from SleepHQ API.

        Returns:
            bool: True if team ID retrieved successfully, False otherwise
        """
        if not self.access_token:
            logger.error("No access token available to retrieve team ID")
            return False
        
        try:
            response = self.session.get(
                TEAMS_ENDPOINT,
                headers={'Authorization': f'Bearer {self.access_token}'},
                timeout=10,
            )
            response.raise_for_status()
            
            response_data = response.json()
            logger.debug(f"Teams API response: {response_data}")
            
            # Handle both wrapped {"data": [...]} and unwrapped [...] response formats
            if isinstance(response_data, dict):
                # API returns wrapped response like {"data": [...]}
                teams = response_data.get('data', [])
                if not teams:
                    # Try other common wrapper keys
                    teams = response_data.get('teams', [])
            elif isinstance(response_data, list):
                teams = response_data
            else:
                logger.error(f"Unexpected teams API response format: {type(response_data)}")
                return False
            
            if teams and len(teams) > 0:
                self.team_id = teams[0].get('id') or teams[0].get('team_id')
                if self.team_id:
                    logger.debug(f"Retrieved team ID: {self.team_id}")
                    return True
                else:
                    logger.error(f"Team found but no 'id' field. Team data: {teams[0]}")
                    return False
            else:
                logger.error(f"No teams returned from API. Full response: {response_data}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to retrieve team ID: {e}")
            return False

    def is_authenticated(self) -> bool:
        """
        Check if client has valid authentication.

        Returns:
            bool: True if access token exists and hasn't expired, False otherwise
        """
        if not self.access_token or not self.team_id:
            return False
        
        # Check if token expired (with 60 second buffer)
        if time.time() >= self.token_expiry - 60:
            return False
        
        return True

    def create_import(self) -> Optional[str]:
        """
        Create a new import to hold uploaded files.

        Returns:
            str: Import ID if creation successful, None otherwise
        """
        if not self.is_authenticated():
            logger.error("Not authenticated with SleepHQ API")
            return None
        
        try:
            import_url = f"{SLEEPHQ_BASE_URL}/api/v1/teams/{self.team_id}/imports"
            
            response = self.session.post(
                import_url,
                headers={'Authorization': f'Bearer {self.access_token}'},
                timeout=30,
            )
            response.raise_for_status()
            
            # Extract import ID from response
            response_data = response.json()
            logger.debug(f"Create import response: {response_data}")
            
            # Handle wrapped {"data": {...}} or direct response
            if isinstance(response_data, dict):
                import_data = response_data.get('data', response_data)
                import_id = import_data.get('id') or import_data.get('import_id')
            else:
                import_id = None
            
            if import_id:
                logger.info(f"Created new import with ID: {import_id}")
                return str(import_id)
            else:
                logger.warning(f"Created import but no ID in response: {response_data}")
                return None
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                logger.error("Authentication token expired or invalid")
                self.access_token = None
            else:
                logger.error(f"Failed to create import: {e}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to create import: {e}")
            return None

    def _calculate_content_hash(self, file_path: pathlib.Path, file_content: bytes) -> str:
        """
        Calculate the content hash for a file.

        The content_hash is an MD5 hash of the file's content and name joined together.
        For example, if the file's name is "file.txt" and content is "Hello, World!",
        the hash would be MD5("Hello, World!file.txt").

        Args:
            file_path: Path to the file (used for the name)
            file_content: The raw bytes of the file content

        Returns:
            str: The MD5 hash as a hexadecimal string
        """
        hash_input = file_content + file_path.name.encode('utf-8')
        return hashlib.md5(hash_input).hexdigest()

    def _get_relative_path(self, file_path: pathlib.Path, base_path: Optional[pathlib.Path]) -> str:
        """
        Get the relative path of a file from the SD card root.

        Args:
            file_path: Full path to the file
            base_path: Base path (SD card root) to calculate relative path from

        Returns:
            str: Relative path in SleepHQ format (e.g., "./" or "./DATALOG/20230924/")
        """
        if base_path is None:
            return "./"
        
        try:
            # Get the relative path from base to file's parent directory
            relative = file_path.parent.relative_to(base_path)
            if str(relative) == ".":
                return "./"
            else:
                # Ensure forward slashes and trailing slash
                return "./" + str(relative).replace("\\", "/") + "/"
        except ValueError:
            # file_path is not relative to base_path
            logger.warning(f"Could not determine relative path for {file_path}, using root")
            return "./"

    def add_file_to_import(
        self,
        import_id: str,
        file_path: pathlib.Path,
        base_path: Optional[pathlib.Path] = None,
    ) -> bool:
        """
        Add a file to an existing import.

        Args:
            import_id: The import ID to add the file to
            file_path: Path to the file to upload
            base_path: Base path (SD card root) to calculate relative path from

        Returns:
            bool: True if file was added successfully, False otherwise
        """
        if not self.is_authenticated():
            logger.error("Not authenticated with SleepHQ API")
            return False
        
        if not file_path.exists():
            logger.error(f"File does not exist: {file_path}")
            return False
        
        try:
            upload_url = f"{SLEEPHQ_BASE_URL}/api/v1/imports/{import_id}/files"
            
            # Read file content for hash calculation and upload
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            # Calculate required fields
            file_name = file_path.name
            relative_path = self._get_relative_path(file_path, base_path)
            content_hash = self._calculate_content_hash(file_path, file_content)
            
            logger.debug(f"Uploading {file_name}: path={relative_path}, hash={content_hash}")
            
            # Prepare multipart form data
            files = {
                'file': (file_name, file_content, 'application/octet-stream'),
            }
            data = {
                'name': file_name,
                'path': relative_path,
                'content_hash': content_hash,
            }
            
            response = self.session.post(
                upload_url,
                headers={'Authorization': f'Bearer {self.access_token}'},
                files=files,
                data=data,
                timeout=30,
            )
            response.raise_for_status()
            
            logger.debug(f"Added file {file_name} to import {import_id}")
            return True
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                logger.error("Authentication token expired or invalid")
                self.access_token = None
            else:
                logger.error(f"Failed to add file {file_path.name}: {e}")
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to add file {file_path.name}: {e}")
            return False

    def process_import(self, import_id: str) -> bool:
        """
        Trigger processing of an uploaded import.

        Args:
            import_id: The import ID to process

        Returns:
            bool: True if processing was triggered successfully, False otherwise
        """
        if not self.is_authenticated():
            logger.error("Not authenticated with SleepHQ API")
            return False
        
        try:
            process_url = f"{SLEEPHQ_BASE_URL}/api/v1/imports/{import_id}/process_files"
            
            response = self.session.post(
                process_url,
                headers={'Authorization': f'Bearer {self.access_token}'},
                timeout=30,
            )
            response.raise_for_status()
            
            logger.info(f"Successfully triggered processing for import ID: {import_id}")
            return True
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                logger.error("Authentication token expired or invalid")
                self.access_token = None
            else:
                logger.error(f"Process request failed for import {import_id}: {e}")
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Process request failed for import {import_id}: {e}")
            return False

    def upload_files(
        self,
        file_paths: list[pathlib.Path],
        base_path: Optional[pathlib.Path] = None,
        overwrite: bool = False,
        process: bool = True,
    ) -> tuple[int, int]:
        """
        Upload multiple CPAP data files to SleepHQ as a single import.

        This follows the proper SleepHQ API flow:
        1. Create a new import
        2. Add all files to that import
        3. Trigger processing of the import

        Args:
            file_paths: List of file paths to upload
            base_path: Base path (SD card root) to calculate relative paths from
            overwrite: Whether to overwrite existing data in SleepHQ (not currently used)
            process: Whether to trigger processing after all uploads complete

        Returns:
            tuple: (successful_count, failed_count)
        """
        if not file_paths:
            logger.warning("No files to upload")
            return 0, 0
        
        # Step 1: Create a new import
        import_id = self.create_import()
        if not import_id:
            logger.error("Failed to create import, aborting upload")
            return 0, len(file_paths)
        
        # Step 2: Add all files to the import
        successful = 0
        failed = 0
        
        for file_path in file_paths:
            if self.add_file_to_import(import_id, file_path, base_path=base_path):
                successful += 1
                logger.info(f"Added file to import: {file_path.name}")
            else:
                failed += 1
        
        logger.info(f"Upload complete: {successful} successful, {failed} failed (import ID: {import_id})")
        
        # Step 3: Process the import (even if some files failed, process what we have)
        if process and successful > 0:
            if self.process_import(import_id):
                logger.info(f"Processing triggered for import with {successful} file(s)")
            else:
                logger.error("Failed to trigger processing")
        
        return successful, failed
