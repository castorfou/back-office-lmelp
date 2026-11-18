"""GET /api/livres-auteurs n'interroge jamais Babelio.

Les 403 de Babelio se transforment en ban IP : seule la validation Babelio,
livre par livre depuis la page (« Valider avec Babelio »), interroge Babelio.
L'extraction des livres d'un épisode sans cache n'est jamais enrichie, même
par un ancien paramètre enrich_babelio=true (Issue #352).
"""

from unittest.mock import patch

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from back_office_lmelp.app import app


EPISODE_OID = "68c707ad6e51b9428ab87e9e"  # pragma: allowlist secret

AVIS_CRITIQUES = [
    {
        "_id": ObjectId("68c718a16e51b9428ab88066"),  # pragma: allowlist secret
        "episode_oid": EPISODE_OID,
        "episode_title": "Test Episode",
        "episode_date": "01 jan. 2025",
        "summary": """## 1. LIVRES DISCUTÉS AU PROGRAMME

| Auteur | Titre | Éditeur |
|--------|-------|---------|
| Carlos Gimenez | Paracuellos, Intégrale | Audie-Fluide glacial |

## 2. COUPS DE CŒUR DES CRITIQUES

(Aucun)
""",
    }
]


@pytest.mark.parametrize("query", ["", "&enrich_babelio=true"])
def test_get_livres_auteurs_never_calls_babelio(query):
    with (
        patch(
            "back_office_lmelp.app.mongodb_service.get_critical_reviews_by_episode_oid",
            return_value=AVIS_CRITIQUES,
        ),
        patch(
            "back_office_lmelp.app.livres_auteurs_cache_service.get_books_by_episode_oid",
            return_value=[],
        ),
        patch(
            "back_office_lmelp.services.babelio_service.BabelioService.verify_book"
        ) as mock_babelio_verify,
        patch(
            "back_office_lmelp.app.collections_management_service.cleanup_uncorrected_summaries_for_episode",
            return_value={"corrected": 0, "skipped": 0},
        ),
    ):
        response = TestClient(app).get(
            f"/api/livres-auteurs?episode_oid={EPISODE_OID}{query}"
        )

    assert response.status_code == 200
    books = response.json()
    assert [(b["auteur"], b["titre"]) for b in books] == [
        ("Carlos Gimenez", "Paracuellos, Intégrale")
    ]
    mock_babelio_verify.assert_not_called()
