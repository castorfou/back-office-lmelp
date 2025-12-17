"""Tests pour les fonctions de logging de démarrage."""

from unittest.mock import patch

from back_office_lmelp.utils.startup_logging import (
    is_running_in_docker,
    mask_mongodb_url,
)


class TestMaskMongodbUrl:
    """Tests pour la fonction mask_mongodb_url."""

    def test_mask_password_in_standard_url(self):
        """Test masquage du mot de passe dans une URL MongoDB standard."""
        url = "mongodb://user:secretpassword@localhost:27017/mydb"  # pragma: allowlist secret
        expected = "mongodb://user:***@localhost:27017/mydb"
        assert mask_mongodb_url(url) == expected

    def test_mask_password_in_mongodb_srv_url(self):
        """Test masquage dans une URL mongodb+srv."""
        url = "mongodb+srv://admin:myP@ssw0rd!@cluster.mongodb.net/database"  # pragma: allowlist secret
        expected = "mongodb+srv://admin:***@cluster.mongodb.net/database"
        assert mask_mongodb_url(url) == expected

    def test_no_masking_when_no_password(self):
        """Test qu'aucun masquage n'est fait si pas de mot de passe."""
        url = "mongodb://localhost:27017/mydb"
        assert mask_mongodb_url(url) == url

    def test_special_characters_in_password(self):
        """Test masquage avec caractères spéciaux dans le mot de passe."""
        url = "mongodb://user:p@ss!w0rd#$%@host:27017/db"
        expected = "mongodb://user:***@host:27017/db"
        assert mask_mongodb_url(url) == expected

    def test_empty_string(self):
        """Test avec chaîne vide."""
        assert mask_mongodb_url("") == ""

    def test_invalid_url_format(self):
        """Test avec format d'URL invalide (retourne tel quel)."""
        url = "not-a-mongodb-url"
        assert mask_mongodb_url(url) == url


class TestIsRunningInDocker:
    """Tests pour la fonction is_running_in_docker."""

    def test_detect_docker_when_dockerenv_exists(self):
        """Test détection Docker quand /.dockerenv existe."""
        with patch("os.path.exists") as mock_exists:
            mock_exists.return_value = True
            assert is_running_in_docker() is True
            mock_exists.assert_called_once_with("/.dockerenv")

    def test_no_docker_when_dockerenv_missing(self):
        """Test pas de Docker quand /.dockerenv n'existe pas."""
        with patch("os.path.exists") as mock_exists:
            mock_exists.return_value = False
            assert is_running_in_docker() is False
            mock_exists.assert_called_once_with("/.dockerenv")
