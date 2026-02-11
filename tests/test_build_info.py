"""Tests pour l'utilitaire build_info (Issue #205)."""

import json
from unittest.mock import patch

from back_office_lmelp.utils.build_info import (
    GITHUB_REPO_URL,
    get_build_info,
    get_changelog,
)


class TestGetBuildInfo:
    """Tests pour get_build_info() avec chaîne de priorité."""

    def test_returns_dict_with_expected_keys(self):
        """Build info doit contenir toutes les clés attendues."""
        info = get_build_info()
        assert "commit_hash" in info
        assert "commit_short" in info
        assert "commit_date" in info
        assert "build_date" in info
        assert "commit_url" in info
        assert "environment" in info

    @patch("back_office_lmelp.utils.build_info._BUILD_INFO_FILE")
    def test_prefers_build_info_file_over_git(self, mock_path):
        """Doit préférer build_info.json quand disponible."""
        mock_path.exists.return_value = True
        mock_path.read_text.return_value = json.dumps(
            {
                "commit_hash": "abc1234567890def1234567890abcdef12345678",  # pragma: allowlist secret
                "commit_date": "2025-01-15 10:30:00 +0100",
                "build_date": "2025-01-15T11:00:00Z",
            }
        )
        info = get_build_info()
        assert info["environment"] == "docker"
        expected_hash = (
            "abc1234567890def1234567890abcdef12345678"  # pragma: allowlist secret
        )
        assert info["commit_hash"] == expected_hash
        assert info["commit_short"] == "abc1234"
        assert GITHUB_REPO_URL in info["commit_url"]

    @patch("back_office_lmelp.utils.build_info._BUILD_INFO_FILE")
    def test_returns_none_commit_url_when_hash_unknown(self, mock_path):
        """commit_url doit être None quand hash est unknown."""
        mock_path.exists.return_value = True
        mock_path.read_text.return_value = json.dumps(
            {
                "commit_hash": "unknown",
                "commit_date": "unknown",
                "build_date": "unknown",
            }
        )
        info = get_build_info()
        assert info["commit_url"] is None

    @patch(
        "back_office_lmelp.utils.build_info.subprocess.check_output",
        side_effect=Exception("git not found"),
    )
    @patch("back_office_lmelp.utils.build_info._BUILD_INFO_FILE")
    def test_returns_fallback_when_nothing_available(self, mock_path, mock_subprocess):
        """Doit retourner des valeurs 'unknown' en fallback."""
        mock_path.exists.return_value = False
        info = get_build_info()
        assert info["commit_hash"] == "unknown"
        assert info["commit_short"] == "unknown"
        assert info["environment"] == "unknown"
        assert info["commit_url"] is None

    @patch("back_office_lmelp.utils.build_info.subprocess.check_output")
    @patch("back_office_lmelp.utils.build_info._BUILD_INFO_FILE")
    def test_falls_back_to_git_when_no_file(self, mock_path, mock_subprocess):
        """Doit utiliser git quand build_info.json est absent."""
        mock_path.exists.return_value = False
        mock_subprocess.side_effect = [
            "def4567890123456789012345678901234567890\n",
            "2025-02-01 14:00:00 +0100\n",
        ]
        info = get_build_info()
        assert info["environment"] == "development"
        expected = (
            "def4567890123456789012345678901234567890"  # pragma: allowlist secret
        )
        assert info["commit_hash"] == expected
        assert info["commit_short"] == "def4567"


class TestGetChangelog:
    """Tests pour get_changelog()."""

    @patch("back_office_lmelp.utils.build_info._CHANGELOG_FILE")
    def test_reads_changelog_from_file(self, mock_path):
        """Doit lire le changelog depuis changelog.json."""
        entries = [
            {
                "hash": "abc1234",
                "date": "2025-01-15 10:30:00 +0100",
                "message": "feat: Add feature (#42)",
            },
            {
                "hash": "def5678",
                "date": "2025-01-10 08:00:00 +0100",
                "message": "fix: Bug fix (#41)",
            },
        ]
        mock_path.exists.return_value = True
        mock_path.read_text.return_value = json.dumps(entries)
        changelog = get_changelog()
        assert len(changelog) == 2
        assert changelog[0]["hash"] == "abc1234"
        assert "#42" in changelog[0]["message"]

    @patch(
        "back_office_lmelp.utils.build_info.subprocess.check_output",
        side_effect=Exception("git not found"),
    )
    @patch("back_office_lmelp.utils.build_info._CHANGELOG_FILE")
    def test_returns_empty_list_when_nothing_available(
        self, mock_path, mock_subprocess
    ):
        """Doit retourner une liste vide en fallback."""
        mock_path.exists.return_value = False
        changelog = get_changelog()
        assert changelog == []

    @patch("back_office_lmelp.utils.build_info.subprocess.check_output")
    @patch("back_office_lmelp.utils.build_info._CHANGELOG_FILE")
    def test_reads_changelog_from_git(self, mock_path, mock_subprocess):
        """Doit lire le changelog via git en dev."""
        mock_path.exists.return_value = False
        git_output = (
            "abc1234|2025-01-15 10:30:00 +0100|feat: Add feature (#42)\n"
            "def5678|2025-01-10 08:00:00 +0100|fix: Bug fix (#41)\n"
            "ghi9012|2025-01-05 12:00:00 +0100|chore: cleanup\n"
        )
        mock_subprocess.return_value = git_output
        changelog = get_changelog()
        # Seuls les commits avec #XXX sont gardés
        assert len(changelog) == 2
        assert changelog[0]["hash"] == "abc1234"
        assert changelog[1]["hash"] == "def5678"
