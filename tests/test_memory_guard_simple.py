"""Tests simplifiés pour les garde-fous mémoire."""

from unittest.mock import MagicMock, patch

import pytest

from back_office_lmelp.utils.memory_guard import MemoryGuard


class TestMemoryGuardSimple:
    """Tests pour la classe MemoryGuard réelle."""

    @pytest.fixture
    def memory_guard(self):
        """Create a MemoryGuard instance for testing."""
        return MemoryGuard(max_memory_mb=500)

    @patch("back_office_lmelp.utils.memory_guard.psutil.Process")
    def test_check_memory_limit_under_threshold(self, mock_process, memory_guard):
        """Test vérification mémoire sous le seuil d'alerte."""
        # Arrange
        mock_proc = MagicMock()
        mock_proc.memory_info.return_value.rss = 300 * 1024 * 1024  # 300 MB
        mock_process.return_value = mock_proc
        # Override the process instance
        memory_guard.process = mock_proc

        # Act
        result = memory_guard.check_memory_limit()

        # Assert
        assert result is None  # Pas d'alerte sous le seuil

    @patch("back_office_lmelp.utils.memory_guard.psutil.Process")
    def test_check_memory_limit_warning_threshold(self, mock_process, memory_guard):
        """Test vérification mémoire au seuil d'alerte (80%)."""
        # Arrange
        mock_proc = MagicMock()
        mock_proc.memory_info.return_value.rss = (
            450 * 1024 * 1024
        )  # 450 MB (90% de 500)
        mock_process.return_value = mock_proc
        # Override the process instance
        memory_guard.process = mock_proc

        # Act
        result = memory_guard.check_memory_limit()

        # Assert
        assert result is not None
        assert "AVERTISSEMENT MÉMOIRE" in result
        assert "450.0MB" in result

    @patch("back_office_lmelp.utils.memory_guard.psutil.Process")
    def test_check_memory_limit_exceeded(self, mock_process, memory_guard):
        """Test vérification mémoire dépassant la limite."""
        # Arrange
        mock_proc = MagicMock()
        mock_proc.memory_info.return_value.rss = 600 * 1024 * 1024  # 600 MB
        mock_process.return_value = mock_proc
        # Override the process instance
        memory_guard.process = mock_proc

        # Act
        result = memory_guard.check_memory_limit()

        # Assert
        assert result is not None
        assert "LIMITE MÉMOIRE DÉPASSÉE" in result
        assert "600.0MB" in result

    @patch("back_office_lmelp.utils.memory_guard.os._exit")
    def test_force_shutdown(self, mock_exit, memory_guard):
        """Test arrêt d'urgence forcé."""
        # Arrange
        error_message = "LIMITE MÉMOIRE DÉPASSÉE - ARRÊT D'URGENCE"

        # Act
        memory_guard.force_shutdown(error_message)

        # Assert
        mock_exit.assert_called_once_with(1)

    def test_memory_guard_custom_limit(self):
        """Test création avec limite personnalisée."""
        # Act
        guard = MemoryGuard(max_memory_mb=1000)

        # Assert
        assert guard.max_memory_bytes == 1000 * 1024 * 1024
        assert guard.warning_threshold == 800 * 1024 * 1024  # 80% de 1000MB

    @patch("back_office_lmelp.utils.memory_guard.psutil.Process")
    def test_get_memory_usage_mb(self, mock_process, memory_guard):
        """Test récupération usage mémoire en MB."""
        # Arrange
        mock_proc = MagicMock()
        mock_proc.memory_info.return_value.rss = 100 * 1024 * 1024  # 100 MB
        mock_process.return_value = mock_proc
        # Override the process instance
        memory_guard.process = mock_proc

        # Act
        result = memory_guard.get_memory_usage_mb()

        # Assert
        assert result == 100.0

    def test_memory_guard_global_instance(self):
        """Test utilisation de l'instance globale."""
        # Arrange & Act
        from back_office_lmelp.utils.memory_guard import memory_guard

        # Assert
        assert memory_guard is not None
        assert hasattr(memory_guard, "check_memory_limit")
        assert hasattr(memory_guard, "force_shutdown")
        assert memory_guard.max_memory_bytes == 500 * 1024 * 1024
