"""
Tests TDD pour la configuration par défaut des logs de cache Babelio.
Requirement: Par défaut, les logs de cache ne doivent PAS être activés.
L'utilisateur peut les activer explicitement avec BABELIO_CACHE_LOG=1.
"""

import os
from unittest.mock import patch

from back_office_lmelp.services.babelio_service import BabelioService


class TestBabelioCacheLogDefault:
    """Tests TDD pour le comportement par défaut des logs de cache."""

    def test_cache_logs_disabled_by_default_red_phase(self):
        """
        RED: Test que les logs de cache sont désactivés par défaut.
        Ce test DOIT ÉCHOUER initialement car la valeur par défaut actuelle est "1".
        """
        # S'assurer qu'aucune variable d'environnement n'est définie
        with patch.dict(os.environ, {}, clear=True):
            # Créer le service sans variable d'environnement
            service = BabelioService()

            # RED: Ce test doit ÉCHOUER car actuellement _cache_log_enabled=True par défaut
            assert service._cache_log_enabled is False, (
                "Les logs de cache doivent être désactivés par défaut "
                "(sans variable d'environnement)"
            )

    def test_cache_logs_can_be_enabled_explicitly(self):
        """
        GREEN: Test que les logs peuvent être activés explicitement.
        Ce test devrait PASSER même avec la logique actuelle.
        """
        # Activer explicitement les logs
        with patch.dict(os.environ, {"BABELIO_CACHE_LOG": "1"}):
            service = BabelioService()

            # Ce test doit passer : activation explicite fonctionne
            assert service._cache_log_enabled is True, (
                "Les logs doivent être activés quand BABELIO_CACHE_LOG=1"
            )

    def test_cache_logs_various_activation_values(self):
        """
        GREEN: Test des différentes valeurs d'activation.
        """
        test_cases = [
            ("1", True),
            ("true", True),
            ("TRUE", True),
            ("yes", True),
            ("YES", True),
            ("0", False),
            ("false", False),
            ("no", False),
            ("", False),
            ("anything_else", False),
        ]

        for env_value, expected in test_cases:
            with patch.dict(os.environ, {"BABELIO_CACHE_LOG": env_value}):
                service = BabelioService()
                assert service._cache_log_enabled is expected, (
                    f"BABELIO_CACHE_LOG='{env_value}' devrait donner {expected}"
                )

    def test_cache_logs_disabled_by_default_after_fix(self):
        """
        GREEN: Test après correction - logs désactivés par défaut.
        Ce test passera après avoir corrigé la valeur par défaut.
        """
        # S'assurer qu'aucune variable d'environnement n'est définie
        with patch.dict(os.environ, {}, clear=True):
            service = BabelioService()

            # GREEN: Après correction, ce test doit PASSER
            assert service._cache_log_enabled is False, (
                "Après correction : logs de cache désactivés par défaut"
            )
            assert hasattr(service, "_cache_log_enabled"), (
                "L'attribut _cache_log_enabled doit exister"
            )
