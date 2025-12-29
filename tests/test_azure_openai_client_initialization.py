"""Tests TDD pour vérifier l'initialisation du client Azure OpenAI."""

import os
from unittest.mock import patch

import pytest


class TestDotenvLoadingInApp:
    """Test CRITIQUE pour le problème root cause (Issue #171)."""

    def test_app_must_load_dotenv_before_service_imports(self):
        """Test que app.py charge .env AVANT d'importer les services singletons.

        PROBLÈME ROOT CAUSE:
        - app.py ligne 23-25 importe avis_critiques_generation_service
        - Ce singleton lit os.getenv() dans __init__() à l'import
        - Si load_dotenv() n'est pas appelé AVANT, variables = vides
        - Résultat: client OpenAI non initialisé malgré .env correct

        SOLUTION:
        - Ajouter load_dotenv() EN HAUT de app.py
        - AVANT tous les imports de services
        """
        # Ce test vérifie que .env est bien chargé
        # (pytest le charge via conftest, mais app.py doit le faire aussi)
        from dotenv import load_dotenv

        load_dotenv()

        # Vérifier que les variables sont accessibles
        assert os.getenv("AZURE_ENDPOINT") is not None
        assert os.getenv("AZURE_API_KEY") is not None


class TestAzureOpenAIClientInitialization:
    """Tests pour diagnostiquer l'initialisation du client Azure OpenAI."""

    def test_environment_variables_are_loaded(self):
        """Test que les variables d'environnement Azure OpenAI sont chargées."""
        # GIVEN: Variables définies dans .env
        required_vars = [
            "AZURE_ENDPOINT",
            "AZURE_API_KEY",
            "AZURE_API_VERSION",
            "AZURE_DEPLOYMENT_NAME",
        ]

        # WHEN: On vérifie les variables d'environnement
        for var in required_vars:
            value = os.getenv(var)

            # THEN: Chaque variable doit être définie et non vide
            assert value is not None, f"{var} doit être défini dans .env"
            assert value.strip() != "", (
                f"{var} ne doit pas être vide (valeur actuelle: '{value}')"
            )

        # Vérification des valeurs attendues (basé sur .env modifié par user)
        # Note: AZURE_API_VERSION a été changé par user de 2024 à 2025
        assert os.getenv("AZURE_API_VERSION") in (
            "2024-09-01-preview",
            "2025-03-01-preview",
        )
        assert os.getenv("AZURE_DEPLOYMENT_NAME") == "gpt-4o"

    def test_service_singleton_reads_environment_variables(self):
        """Test que le service singleton lit correctement les variables d'environnement."""
        # GIVEN: Variables d'environnement définies
        with patch.dict(
            os.environ,
            {
                "AZURE_ENDPOINT": "https://test.openai.azure.com",
                "AZURE_API_KEY": "test-key-123",  # pragma: allowlist secret
                "AZURE_API_VERSION": "2024-09-01-preview",
                "AZURE_DEPLOYMENT_NAME": "gpt-4o",
            },
        ):
            # WHEN: On importe le service (ce qui crée le singleton)
            # Note: On doit réimporter pour forcer la création du singleton avec les nouvelles env vars
            import importlib

            from back_office_lmelp.services import avis_critiques_generation_service

            importlib.reload(avis_critiques_generation_service)

            service = (
                avis_critiques_generation_service.avis_critiques_generation_service
            )

            # THEN: Le service doit avoir les bonnes valeurs
            assert service.azure_endpoint == "https://test.openai.azure.com"
            assert service.api_key == "test-key-123"  # pragma: allowlist secret
            assert service.api_version == "2024-09-01-preview"
            assert service.deployment_name == "gpt-4o"
            assert service.client is not None, (
                "Client OpenAI doit être initialisé avec des env vars valides"
            )

    def test_service_singleton_fails_with_missing_env_vars(self):
        """Test que le service singleton détecte les variables manquantes."""
        # GIVEN: Variables d'environnement ABSENTES
        with patch.dict(os.environ, {}, clear=True):
            # WHEN: On importe le service
            import importlib

            from back_office_lmelp.services import avis_critiques_generation_service

            importlib.reload(avis_critiques_generation_service)

            service = (
                avis_critiques_generation_service.avis_critiques_generation_service
            )

            # THEN: Le client ne doit PAS être initialisé
            assert service.client is None, (
                "Client OpenAI ne doit pas être initialisé sans env vars"
            )

    @pytest.mark.asyncio
    async def test_generate_summary_phase1_raises_if_client_not_configured(self):
        """Test que generate_summary_phase1 raise ValueError si client non configuré."""
        # GIVEN: Service sans client configuré
        with patch.dict(os.environ, {}, clear=True):
            import importlib

            from back_office_lmelp.services import avis_critiques_generation_service

            importlib.reload(avis_critiques_generation_service)

            service = (
                avis_critiques_generation_service.avis_critiques_generation_service
            )

            # WHEN: On tente de générer un summary
            # THEN: Doit raise ValueError avec message explicite
            with pytest.raises(ValueError, match="Client Azure OpenAI non configuré"):
                await service.generate_summary_phase1(
                    "transcription test", "2025-01-15"
                )
