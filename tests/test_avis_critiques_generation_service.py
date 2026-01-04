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
    TRANSCRIPTION_EPISODE_2017_04_09,
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

    @skip_if_no_azure
    @pytest.mark.asyncio
    async def test_generate_summary_episode_2017_04_09_should_succeed(self):
        """
        Integration test: Episode 09/04/2017 should generate valid summary.

        This episode has 5 books discussed (Ma Petite France, Norma, Marlène, etc.).
        LLM should NOT return 'Aucun livre discuté' message.
        Fixes Issue #181.
        """
        service = AvisCritiquesGenerationService()

        result = await service.generate_summary_phase1(
            TRANSCRIPTION_EPISODE_2017_04_09, "2017-04-09"
        )

        # Business requirement: Valid markdown with books
        assert "## 1. LIVRES DISCUTÉS AU PROGRAMME" in result
        assert "|" in result  # Has markdown tables
        assert len(result) >= 200

        # CRITICAL: Should NOT return "no books" message (incorrect prompt)
        assert "Aucun livre discuté" not in result


class TestValidateMarkdownFormat:
    """Tests pour la validation du format markdown."""

    def test_validate_markdown_format_valid_summary(self):
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

        result = service._validate_markdown_format(valid_summary)

        assert result["valid"] is True
        assert len(result["errors"]) == 0
        assert "summary_preview" in result

    def test_validate_markdown_format_missing_header(self):
        """Test validation détecte header manquant."""
        service = AvisCritiquesGenerationService()

        invalid_summary = "Juste du texte sans titre de section."

        result = service._validate_markdown_format(invalid_summary)

        assert result["valid"] is False
        assert "Section principale manquante" in result["errors"][0]
        assert len(result["summary_preview"]) > 0

    def test_validate_markdown_format_missing_table(self):
        """Test validation détecte tableau manquant."""
        service = AvisCritiquesGenerationService()

        invalid_summary = """
## 1. LIVRES DISCUTÉS AU PROGRAMME

Pas de tableau ici.
"""

        result = service._validate_markdown_format(invalid_summary)

        assert result["valid"] is False
        assert any("tableau markdown" in err for err in result["errors"])

    def test_validate_markdown_format_too_short(self):
        """Test validation détecte contenu trop court."""
        service = AvisCritiquesGenerationService()

        short_summary = "## 1. | Test |"

        result = service._validate_markdown_format(short_summary)

        assert result["valid"] is False
        assert any("trop court" in err for err in result["errors"])

    def test_validate_markdown_format_detects_no_books_message(self):
        """Test validation rejette le message 'no books' incorrect."""
        service = AvisCritiquesGenerationService()

        no_books_message = "Aucun livre discuté dans cet épisode."

        result = service._validate_markdown_format(no_books_message)

        assert result["valid"] is False
        assert any("Aucun livre discuté" in err for err in result["errors"])

    def test_validate_markdown_format_provides_preview(self):
        """Test validation inclut preview dans résultats."""
        service = AvisCritiquesGenerationService()

        result = service._validate_markdown_format("Short")

        assert "summary_preview" in result
        assert len(result["summary_preview"]) > 0


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
