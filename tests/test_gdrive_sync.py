"""
Tests for gdrive_sync.py
Requires mock setup for Google API.
"""

import unittest
from unittest.mock import patch, MagicMock
from src.gdrive_sync import authenticate_gdrive, find_latest_zip

class TestGDriveSync(unittest.TestCase):
    @patch('src.gdrive_sync.build')
    def test_authenticate_gdrive(self, mock_build):
        # Mock credentials and service
        mock_creds = MagicMock()
        mock_creds.valid = True
        with patch('src.gdrive_sync.pickle.load', return_value=mock_creds):
            service = authenticate_gdrive()
            self.assertIsNotNone(service)

if __name__ == '__main__':
    unittest.main() 