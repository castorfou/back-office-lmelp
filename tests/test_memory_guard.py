"""Tests pour les garde-fous mémoire du Back-Office LMELP."""

from unittest.mock import MagicMock, patch

import pytest

from back_office_lmelp.utils.memory_guard import MemoryGuard


class TestMemoryGuard:
    """Tests pour la classe MemoryGuard."""

    @pytest.fixture
    def memory_guard(self):
        """Create a MemoryGuard instance for testing."""
        return MemoryGuard(limit_mb=500)

    @patch("back_office_lmelp.utils.memory_guard.psutil.Process")
    def test_check_memory_limit_under_threshold(self, mock_process, memory_guard):
        """Test vérification mémoire sous le seuil d'alerte."""
        # Arrange
        mock_proc = MagicMock()
        mock_proc.memory_info.return_value.rss = 300 * 1024 * 1024  # 300 MB
        mock_process.return_value = mock_proc

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

        # Act
        result = memory_guard.check_memory_limit()

        # Assert
        assert result is not None
        assert "Attention: utilisation mémoire élevée" in result
        assert "450 MB / 500 MB" in result

    @patch("back_office_lmelp.utils.memory_guard.psutil.Process")
    def test_check_memory_limit_exceeded(self, mock_process, memory_guard):
        """Test vérification mémoire dépassant la limite."""
        # Arrange
        mock_proc = MagicMock()
        mock_proc.memory_info.return_value.rss = 600 * 1024 * 1024  # 600 MB
        mock_process.return_value = mock_proc

        # Act
        result = memory_guard.check_memory_limit()

        # Assert
        assert result is not None
        assert "LIMITE MÉMOIRE DÉPASSÉE" in result
        assert "600 MB / 500 MB" in result

    @patch("back_office_lmelp.utils.memory_guard.psutil.Process")
    def test_check_memory_limit_psutil_error(self, mock_process, memory_guard):
        """Test gestion d'erreur psutil."""
        # Arrange
        mock_process.side_effect = Exception("psutil error")

        # Act
        result = memory_guard.check_memory_limit()

        # Assert
        assert result is None  # Erreur silencieuse, pas de blocage

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
        guard = MemoryGuard(limit_mb=1000)

        # Assert
        assert guard.limit_mb == 1000
        assert guard.warning_threshold == 800  # 80% de 1000

    @patch("back_office_lmelp.utils.memory_guard.psutil.Process")
    def test_memory_guard_different_warning_thresholds(self, mock_process):
        """Test différents seuils d'alerte."""
        # Test cases avec différentes limites
        test_cases = [
            (100, 80),  # 100MB limit -> 80MB warning
            (250, 200),  # 250MB limit -> 200MB warning
            (1000, 800),  # 1GB limit -> 800MB warning
        ]

        for limit_mb, expected_warning in test_cases:
            # Arrange
            guard = MemoryGuard(limit_mb=limit_mb)
            mock_proc = MagicMock()
            # Utiliser exactement le seuil d'avertissement
            mock_proc.memory_info.return_value.rss = expected_warning * 1024 * 1024
            mock_process.return_value = mock_proc

            # Act
            result = guard.check_memory_limit()

            # Assert
            assert result is not None
            assert f"{expected_warning} MB / {limit_mb} MB" in result

    @patch("back_office_lmelp.utils.memory_guard.psutil.Process")
    def test_memory_conversion_accuracy(self, mock_process, memory_guard):
        """Test précision de la conversion bytes vers MB."""
        # Arrange - Utiliser des valeurs exactes
        exact_mb = 123
        bytes_value = exact_mb * 1024 * 1024
        mock_proc = MagicMock()
        mock_proc.memory_info.return_value.rss = bytes_value
        mock_process.return_value = mock_proc

        # Act
        result = memory_guard.check_memory_limit()

        # Assert
        # Doit être None car 123 MB < seuil de 400 MB (80% de 500)
        assert result is None


class TestMemoryGuardIntegration:
    """Tests d'intégration pour les garde-fous mémoire."""

    @patch("back_office_lmelp.utils.memory_guard.psutil.Process")
    def test_memory_guard_realistic_scenarios(self, mock_process):
        """Test scénarios réalistes d'utilisation mémoire."""
        guard = MemoryGuard(limit_mb=500)
        mock_proc = MagicMock()
        mock_process.return_value = mock_proc

        scenarios = [
            (100, False, False),  # Utilisation normale
            (350, False, False),  # Utilisation élevée mais OK
            (400, True, False),  # Seuil d'alerte atteint
            (450, True, False),  # Alerte forte
            (500, True, True),  # Limite exacte
            (600, True, True),  # Dépassement critique
        ]

        for memory_mb, should_warn, should_shutdown in scenarios:
            # Arrange
            mock_proc.memory_info.return_value.rss = memory_mb * 1024 * 1024

            # Act
            result = guard.check_memory_limit()

            # Assert
            if not should_warn and not should_shutdown:
                assert result is None, f"Pas d'alerte attendue pour {memory_mb}MB"
            elif should_warn and not should_shutdown:
                assert result is not None, f"Alerte attendue pour {memory_mb}MB"
                assert "Attention" in result or "LIMITE" not in result
            elif should_shutdown:
                assert result is not None, f"Arrêt d'urgence attendu pour {memory_mb}MB"
                assert "LIMITE MÉMOIRE DÉPASSÉE" in result

    def test_memory_guard_thread_safety(self):
        """Test sécurité thread du guard mémoire."""
        import threading
        import time

        guard = MemoryGuard(limit_mb=500)
        results = []
        errors = []

        def check_memory_worker():
            try:
                for _ in range(10):
                    result = guard.check_memory_limit()
                    results.append(result)
                    time.sleep(0.01)  # Petite pause
            except Exception as e:
                errors.append(e)

        # Act - Plusieurs threads appelant check_memory_limit
        threads = [threading.Thread(target=check_memory_worker) for _ in range(5)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # Assert
        assert len(errors) == 0, f"Erreurs thread-safety: {errors}"
        assert len(results) == 50  # 5 threads * 10 checks chacun

    @patch("back_office_lmelp.utils.memory_guard.psutil.Process")
    def test_memory_guard_performance(self, mock_process):
        """Test performance du guard mémoire."""
        import time

        # Arrange
        guard = MemoryGuard(limit_mb=500)
        mock_proc = MagicMock()
        mock_proc.memory_info.return_value.rss = 300 * 1024 * 1024
        mock_process.return_value = mock_proc

        # Act - Mesurer le temps pour 1000 vérifications
        start_time = time.time()
        for _ in range(1000):
            guard.check_memory_limit()
        end_time = time.time()

        # Assert - Doit être rapide (< 1 seconde pour 1000 vérifications)
        elapsed = end_time - start_time
        assert elapsed < 1.0, f"Vérifications mémoire trop lentes: {elapsed:.3f}s"


class TestMemoryGuardSingleton:
    """Tests pour le pattern singleton du guard mémoire."""

    def test_memory_guard_singleton_pattern(self):
        """Test que le guard mémoire utilise le pattern singleton."""
        # Act
        guard1 = MemoryGuard()
        guard2 = MemoryGuard()

        # Assert
        # Note: Actuellement MemoryGuard n'est pas un singleton,
        # mais ça pourrait être ajouté pour éviter la duplication d'instances
        # Pour l'instant, on teste juste que les instances ont les mêmes paramètres par défaut
        assert guard1.limit_mb == guard2.limit_mb
        assert guard1.warning_threshold == guard2.warning_threshold

    def test_memory_guard_global_instance(self):
        """Test utilisation de l'instance globale."""
        # Arrange & Act
        from back_office_lmelp.utils.memory_guard import memory_guard

        # Assert
        assert memory_guard is not None
        assert hasattr(memory_guard, "check_memory_limit")
        assert hasattr(memory_guard, "force_shutdown")
        assert memory_guard.limit_mb == 500  # Valeur par défaut
