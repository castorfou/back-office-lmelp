"""Deux livres sur une même ligne d'un résumé (Issue #405).

Le LLM regroupe parfois deux livres recommandés par un même critique en une
seule ligne de coup de cœur (« Titre A / Titre B »). L'avis ne peut alors être
rattaché qu'à un des deux livres. La génération le signale dans ses
avertissements, sans bloquer l'enregistrement.
"""

from unittest.mock import AsyncMock, patch

import pytest

from back_office_lmelp.services.avis_critiques_generation_service import (
    AvisCritiquesGenerationService,
)


# Ligne réelle du résumé du 28 juin 2015
SUMMARY_WITH_MERGED_ROW = """## 1. LIVRES DISCUTÉS AU PROGRAMME du 28 juin 2015

|Auteur|Titre|Éditeur|Avis détaillés des critiques|Note moyenne|Nb critiques|Coup de cœur|Chef d'œuvre|
|---|---|---|---|---|---|---|---|
|Isabelle Autissier|Soudain, seuls|Stock|**Michel Crépu**: Livre sensationnel. Note: 8|8.0|1|||

## 2. COUPS DE CŒUR DES CRITIQUES du 28 juin 2015

|Auteur|Titre|Éditeur|Critique|Note|Commentaire|
|--------|-------|---------|----------|------|-------------|
|Eve Babitz|Jours tranquilles, brèves rencontres|Gallmeister|Nelly Kapriélian|8|Découverte.|
|Pierre Boncenne et Simon Leys|Le Parapluie de Simon Leys / Quand vous viendrez me voir aux antipodes|Philippe Rey|Michel Crépu|8|Essais et correspondance.|
"""


@pytest.mark.asyncio
async def test_generation_warns_when_two_books_share_a_row():
    service = AvisCritiquesGenerationService()

    with (
        patch.object(
            service,
            "generate_summary_phase1",
            AsyncMock(return_value=SUMMARY_WITH_MERGED_ROW),
        ),
        patch.object(
            service,
            "enhance_summary_phase2",
            AsyncMock(return_value=SUMMARY_WITH_MERGED_ROW),
        ),
    ):
        result = await service.generate_full_summary(
            "transcription", "2015-06-28", episode_page_url=None
        )

    merged = [w for w in result["warnings"] if "même ligne" in w]
    assert len(merged) == 1
    assert (
        "Le Parapluie de Simon Leys / Quand vous viendrez me voir aux antipodes"
        in merged[0]
    )


def test_find_merged_book_rows_flags_titles_joined_by_slash():
    from back_office_lmelp.services.avis_extraction_service import (
        AvisExtractionService,
    )

    summary = SUMMARY_WITH_MERGED_ROW.replace(
        "|Isabelle Autissier|Soudain, seuls|",
        "|Pierre Notte|La chanson de Madame Rosenfeld / J'ai tué Barbara|",
    ) + (
        "|Albert Camus et Maria Casarès|Correspondance|Gallimard|"
        "Olivia de Lamberterie|9|Lettres.|\n"
    )

    assert AvisExtractionService().find_merged_book_rows(summary) == [
        "La chanson de Madame Rosenfeld / J'ai tué Barbara",
        "Le Parapluie de Simon Leys / Quand vous viendrez me voir aux antipodes",
    ]


def test_phase1_prompt_states_one_book_per_row_for_coups_de_coeur():
    prompt = AvisCritiquesGenerationService()._get_phase1_prompt(
        "transcription", " du 28 juin 2015"
    )
    section2_rules = prompt.split("## 2. COUPS DE CŒUR DES CRITIQUES", 1)[1]

    assert "UN LIVRE = UNE LIGNE" in section2_rules
    assert '"Titre 1 / Titre 2"' in section2_rules
