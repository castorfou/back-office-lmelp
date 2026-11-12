"""GET /api/livres-auteurs n'interroge pas Babelio par défaut.

Ouvrir la page Livres et Auteurs sur un épisode sans cache déclenchait
l'extraction des livres, enrichie par un verify_book() Babelio par livre. Les
403 de Babelio se transformant en ban IP, cet enrichissement n'a lieu que sur
geste explicite (« Valider avec Babelio » → enrich_babelio=true).
"""

from unittest.mock import patch

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


def test_get_livres_auteurs_does_not_call_babelio_by_default():
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
        response = TestClient(app).get(f"/api/livres-auteurs?episode_oid={EPISODE_OID}")

    assert response.status_code == 200
    books = response.json()
    assert [(b["auteur"], b["titre"]) for b in books] == [
        ("Carlos Gimenez", "Paracuellos, Intégrale")
    ]
    mock_babelio_verify.assert_not_called()
