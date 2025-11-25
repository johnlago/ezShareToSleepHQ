import unittest
import tempfile
import shutil
import pathlib
import sys
import os
from unittest.mock import MagicMock, patch

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sleephq_uploader

class TestUploadLogic(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.ezshare_path = pathlib.Path(self.test_dir)
        
        # Create standard SD card structure
        self.settings_dir = self.ezshare_path / "SETTINGS"
        self.settings_dir.mkdir()
        (self.settings_dir / "settings.dat").touch()
        
        self.datalog_dir = self.ezshare_path / "DATALOG"
        self.datalog_dir.mkdir()
        
        # Old date folder
        self.date1_dir = self.datalog_dir / "20230101"
        self.date1_dir.mkdir()
        (self.date1_dir / "file1.edf").touch()
        
        # New date folder
        self.date2_dir = self.datalog_dir / "20230102"
        self.date2_dir.mkdir()
        (self.date2_dir / "file2.edf").touch()
        
        # Root files
        (self.ezshare_path / "STR.edf").touch()
        (self.ezshare_path / "Identification.crc").touch()
        (self.ezshare_path / "Identification.json").touch()
        (self.ezshare_path / "random.txt").touch() # Should be ignored if not in mandatory list

        self.ezshare_mock = MagicMock()
        self.ezshare_mock.path = self.ezshare_path
        self.ezshare_mock.downloaded_files = []

        self.sleephq_client_mock = MagicMock()
        self.sleephq_client_mock.upload_files.return_value = (1, 0)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_incremental_upload_selection(self):
        # Simulate that only file2.edf (in 20230102) was downloaded
        self.ezshare_mock.downloaded_files = [str(self.date2_dir / "file2.edf")]
        
        # Mock the upload_files method to capture what would be uploaded
        self.sleephq_client_mock.upload_files.return_value = (1, 0)
        
        sleephq_uploader.upload_to_sleephq(self.ezshare_mock, self.sleephq_client_mock, verbose=True)
        
        # Verify upload_files was called
        self.assertTrue(self.sleephq_client_mock.upload_files.called)
        
        # Get the list of files passed to upload_files
        args, _ = self.sleephq_client_mock.upload_files.call_args
        files_to_upload = args[0]
        file_names = [f.name for f in files_to_upload]
        
        # Mandatory files
        self.assertIn("STR.edf", file_names)
        self.assertIn("Identification.crc", file_names)
        self.assertIn("Identification.json", file_names)
        self.assertIn("settings.dat", file_names)
        
        # New data
        self.assertIn("file2.edf", file_names)
        
        # Old data (should NOT be included)
        self.assertNotIn("file1.edf", file_names)
        
        # Random root file (should NOT be included unless we change logic to include everything in root)
        # The requirement says: "1. STR.edf 2. Identification.crc 3. Identification.json"
        # It doesn't explicitly say "exclude others", but "must include...". 
        # However, the goal is to filter DATALOG.
        # Let's assume we only include specific root files + SETTINGS + active DATALOGs.
        self.assertNotIn("random.txt", file_names)

    def test_force_upload_includes_all(self):
        # Force = True should upload everything
        self.ezshare_mock.downloaded_files = [] # Even with no new files
        
        sleephq_uploader.upload_to_sleephq(self.ezshare_mock, self.sleephq_client_mock, verbose=True, force=True)
        
        args, _ = self.sleephq_client_mock.upload_files.call_args
        files_to_upload = args[0]
        file_names = [f.name for f in files_to_upload]
        
        self.assertIn("file1.edf", file_names)
        self.assertIn("file2.edf", file_names)
        self.assertIn("STR.edf", file_names)

if __name__ == '__main__':
    unittest.main()
