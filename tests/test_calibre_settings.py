import os
from unittest.mock import patch

from back_office_lmelp.settings import Settings


class TestCalibreSettings:
    @patch.dict(os.environ, {}, clear=True)
    @patch("os.path.isdir")
    @patch("os.path.isfile")
    def test_calibre_library_path_detection(self, mock_isfile, mock_isdir):
        # Case 1: /calibre exists and has metadata.db
        def isdir_side_effect(path):
            return path == "/calibre"

        def isfile_side_effect(path):
            return path == "/calibre/metadata.db"

        mock_isdir.side_effect = isdir_side_effect
        mock_isfile.side_effect = isfile_side_effect

        settings = Settings()
        assert settings.calibre_library_path == "/calibre"

        # Case 2: /calibre does not exist
        mock_isdir.side_effect = None
        mock_isdir.return_value = False

        settings = Settings()
        assert settings.calibre_library_path is None

    @patch.dict(os.environ, {}, clear=True)
    @patch("os.path.isdir")
    @patch("os.path.isfile")
    def test_calibre_library_path_no_db(self, mock_isfile, mock_isdir):
        # Case 3: /calibre exists but NO metadata.db
        def isdir_side_effect(path):
            return path == "/calibre"

        def isfile_side_effect(path):
            return False

        mock_isdir.side_effect = isdir_side_effect
        mock_isfile.side_effect = isfile_side_effect

        settings = Settings()
        assert settings.calibre_library_path is None
