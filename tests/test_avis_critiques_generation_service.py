"""Tests pour le service de génération d'avis critiques en 2 phases LLM."""

import asyncio
import os
from unittest.mock import MagicMock, patch

import pytest

from back_office_lmelp.services.avis_critiques_generation_service import (
    AvisCritiquesGenerationService,
)
from tests.fixtures.transcription_samples import (
    EXPECTED_SUMMARY_PHASE1_SAMPLE_1,
    TRANSCRIPTION_SAMPLE_1,
)


# Skip tous les tests si Azure OpenAI n'est pas configuré (CI/CD)
skip_if_no_azure = pytest.mark.skipif(
    os.getenv("AZURE_ENDPOINT") is None,
    reason="Azure OpenAI non configuré (variables d'environnement manquantes)",
)


class TestGenerateSummaryPhase1:
    """Tests pour la génération Phase 1 (transcription → markdown)."""

    @skip_if_no_azure
    @pytest.mark.asyncio
    async def test_generate_summary_phase1_success(self):
        """Test Phase 1 génère markdown valide depuis transcription."""
        service = AvisCritiquesGenerationService()

        # Mock Azure OpenAI response
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content=EXPECTED_SUMMARY_PHASE1_SAMPLE_1))
        ]

        with patch.object(
            service.client.chat.completions, "create", return_value=mock_response
        ):
            result = await service.generate_summary_phase1(
                TRANSCRIPTION_SAMPLE_1, "2025-01-15"
            )

            # Validation structure
            assert "## 1. LIVRES DISCUTÉS AU PROGRAMME" in result
            assert (
                "## 2. COUPS DE CŒUR DES CRITIQUES" in result
                or "## 2. COUPS DE C" in result
            )
            assert "|" in result  # Markdown table

    @skip_if_no_azure
    @pytest.mark.asyncio
    async def test_generate_summary_phase1_invalid_format_raises(self):
        """Test Phase 1 raise ValueError si format markdown invalide."""
        service = AvisCritiquesGenerationService()

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="Texte invalide sans tableaux"))
        ]

        with (
            patch.object(
                service.client.chat.completions, "create", return_value=mock_response
            ),
            pytest.raises(ValueError, match="Format markdown invalide"),
        ):
            await service.generate_summary_phase1("transcription", "2025-01-15")

    @skip_if_no_azure
    @pytest.mark.asyncio
    async def test_generate_summary_phase1_empty_transcription_raises(self):
        """Test Phase 1 raise ValueError si transcription vide."""
        service = AvisCritiquesGenerationService()

        with pytest.raises(ValueError, match="Transcription vide"):
            await service.generate_summary_phase1("", "2025-01-15")

    @pytest.mark.asyncio
    async def test_generate_summary_phase1_no_client_raises(self):
        """Test Phase 1 raise ValueError si client non configuré."""
        service = AvisCritiquesGenerationService()
        service.client = None

        with pytest.raises(ValueError, match="Client Azure OpenAI non configuré"):
            await service.generate_summary_phase1("transcription", "2025-01-15")

    @skip_if_no_azure
    @pytest.mark.asyncio
    async def test_generate_summary_phase1_timeout_retries(self):
        """Test Phase 1 retry en cas de timeout."""
        service = AvisCritiquesGenerationService()

        # First call times out, second succeeds
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content=EXPECTED_SUMMARY_PHASE1_SAMPLE_1))
        ]

        # Mock asyncio.wait_for to raise TimeoutError on first call
        original_wait_for = asyncio.wait_for

        call_count = 0

        async def mock_wait_for(coro, timeout):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise TimeoutError("First call timed out")
            return await original_wait_for(coro, timeout=1)

        with (
            patch.object(
                service.client.chat.completions, "create", return_value=mock_response
            ),
            patch("asyncio.wait_for", side_effect=mock_wait_for),
        ):
            result = await service.generate_summary_phase1(
                TRANSCRIPTION_SAMPLE_1, "2025-01-15"
            )
            assert "## 1. LIVRES DISCUTÉS" in result
            assert call_count == 2  # Retry happened


class TestValidateMarkdownFormat:
    """Tests pour la validation du format markdown."""

    def test_is_valid_markdown_format_success(self):
        """Test validation réussit avec format valide."""
        service = AvisCritiquesGenerationService()

        valid_summary = """
## 1. LIVRES DISCUTÉS AU PROGRAMME

| Auteur | Titre | Éditeur | Avis | Note |
|--------|-------|---------|------|------|
| Test Author | Test Book | Test Publisher | **Critique 1**: Excellent livre (9/10) | 9.0 |
| Another Author | Another Book | Another Publisher | **Critique 2**: Bon livre (7/10) | 7.0 |

## 2. COUPS DE CŒUR

Aucun coup de cœur supplémentaire.
"""

        assert service._is_valid_markdown_format(valid_summary) is True

    def test_is_valid_markdown_format_missing_title(self):
        """Test validation échoue sans titre de section."""
        service = AvisCritiquesGenerationService()

        invalid_summary = """
Juste du texte sans titre de section.
"""

        assert service._is_valid_markdown_format(invalid_summary) is False

    def test_is_valid_markdown_format_missing_table(self):
        """Test validation échoue sans tableau markdown."""
        service = AvisCritiquesGenerationService()

        invalid_summary = """
## 1. LIVRES DISCUTÉS AU PROGRAMME

Pas de tableau ici.
"""

        assert service._is_valid_markdown_format(invalid_summary) is False

    def test_is_valid_markdown_format_too_short(self):
        """Test validation échoue si texte trop court."""
        service = AvisCritiquesGenerationService()

        short_summary = "## 1. | Test |"

        assert service._is_valid_markdown_format(short_summary) is False


class TestEnhanceSummaryPhase2:
    """Tests pour la Phase 2 (correction avec métadonnées)."""

    @skip_if_no_azure
    @pytest.mark.asyncio
    async def test_enhance_summary_phase2_applies_corrections(self):
        """Test Phase 2 corrige noms avec metadata."""
        service = AvisCritiquesGenerationService()

        summary_phase1 = """
## 1. LIVRES DISCUTÉS AU PROGRAMME

| Auteur | Titre | Éditeur | Avis détaillés des critiques | Note moyenne |
|--------|-------|---------|------------------------------|--------------|
| Auteur | Titre | Editeur | **Patricia Martine**: Excellent | 9.0 |
"""

        metadata = {
            "animateur": "Jérôme Garcin",
            "critiques": ["Patricia Martin", "Arnaud Viviant"],
            "date": "2025-01-15",
        }

        mock_response = MagicMock()
        corrected_summary = summary_phase1.replace(
            "Patricia Martine", "Patricia Martin"
        )
        mock_response.choices = [
            MagicMock(message=MagicMock(content=corrected_summary))
        ]

        with patch.object(
            service.client.chat.completions, "create", return_value=mock_response
        ):
            result = await service.enhance_summary_phase2(summary_phase1, metadata)

            assert "Patricia Martin" in result
            assert "Patricia Martine" not in result

    @skip_if_no_azure
    @pytest.mark.asyncio
    async def test_enhance_summary_phase2_fallback_on_error(self):
        """Test Phase 2 fallback vers Phase 1 si erreur."""
        service = AvisCritiquesGenerationService()

        summary_phase1 = "## 1. LIVRES DISCUTÉS\n\nTest summary"

        with patch.object(
            service.client.chat.completions,
            "create",
            side_effect=Exception("LLM error"),
        ):
            result = await service.enhance_summary_phase2(summary_phase1, {})

            # Should return original summary on error
            assert result == summary_phase1

    @pytest.mark.asyncio
    async def test_enhance_summary_phase2_skip_if_no_metadata(self):
        """Test Phase 2 skip si pas de métadonnées."""
        service = AvisCritiquesGenerationService()

        summary_phase1 = "## 1. LIVRES DISCUTÉS\n\nTest summary"

        result = await service.enhance_summary_phase2(summary_phase1, {})

        # Should return original without calling LLM
        assert result == summary_phase1

    @pytest.mark.asyncio
    async def test_enhance_summary_phase2_skip_if_no_client(self):
        """Test Phase 2 skip si client non configuré."""
        service = AvisCritiquesGenerationService()
        service.client = None

        summary_phase1 = "## 1. LIVRES DISCUTÉS\n\nTest summary"

        result = await service.enhance_summary_phase2(
            summary_phase1, {"critiques": ["Test"]}
        )

        # Should return original without calling LLM
        assert result == summary_phase1
