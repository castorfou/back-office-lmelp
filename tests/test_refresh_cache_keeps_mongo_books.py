"""« Relancer la validation » ne défait jamais un livre déjà en base (Issue #383).

Le rafraîchissement du cache d'un épisode garde les entrées `status: "mongo"`
et ne supprime que les autres. Les livres du résumé sans entrée de cache
reviennent au chargement suivant pour être revalidés.
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

from bson import ObjectId
from fastapi.testclient import TestClient

from back_office_lmelp.app import app


EPISODE_OID = "6865f9a1a1418e3d7c63d06b"  # pragma: allowlist secret
AVIS_CRITIQUE_ID = ObjectId("68668b3ba1418e3d7c63d0b6")  # pragma: allowlist secret
BOOK_ID = ObjectId("68a3a9b7c1d2e3f405060708")  # pragma: allowlist secret
AUTHOR_ID = ObjectId("68a3a9b7c1d2e3f405060709")  # pragma: allowlist secret
DOCTEUR_BOOK_ID = ObjectId("68a3a9b7c1d2e3f40506070a")  # pragma: allowlist secret
DOCTEUR_AUTHOR_ID = ObjectId("68a3a9b7c1d2e3f40506070b")  # pragma: allowlist secret

SUMMARY = """## 1. LIVRES DISCUTÉS AU PROGRAMME du 24 avril 2016

| Auteur | Titre | Éditeur | Avis détaillés des critiques | Note moyenne | Nb critiques | Coup de cœur | Chef d'œuvre |
|--------|-------|---------|------------------------------|--------------|-------------|-------------|-------------|
| Anne Révah | Docteur écoutez ! | Albin Michel | **Arnaud Viviant**: Passionnant. Note: 8 | 8.0 | 1 | | |
| Neige Sinno | La Realidad | P.O.L | **Elisabeth Philippe**: Exceptionnel. Note: 10 | 10.0 | 1 | | |

## 2. COUPS DE CŒUR DES CRITIQUES du 24 avril 2016

| Auteur | Titre | Éditeur | Critique | Note | Commentaire |
|--------|-------|---------|----------|------|-------------|
| Carl Friedrich von Rumohr | L'esprit de l'art culinaire | Les Belles Lettres | Arnaud Viviant | 9.0 | Savoureux |"""


def _avis_critique() -> dict:
    return {
        "_id": AVIS_CRITIQUE_ID,
        "episode_oid": EPISODE_OID,
        "episode_title": "Le Masque et la Plume",
        "episode_date": "24 avr. 2016",
        "summary": SUMMARY,
    }


def _mongo_entry(titre: str, auteur: str, **extra: object) -> dict:
    """Entrée de cache d'un livre en base, telle qu'écrite par handle_book_validation."""
    now = datetime(2026, 11, 20, 10, 0, 0)
    entry = {
        "_id": ObjectId(),
        "avis_critique_id": AVIS_CRITIQUE_ID,
        "episode_oid": EPISODE_OID,
        "auteur": auteur,
        "titre": titre,
        "editeur": "Albin Michel",
        "programme": True,
        "status": "mongo",
        "book_id": BOOK_ID,
        "author_id": AUTHOR_ID,
        "created_at": now,
        "updated_at": now,
    }
    entry.update(extra)
    return entry


class TestGetLivresAuteursCompletesPartialCache:
    """Le chargement complète un cache partiel avec les livres du résumé."""

    def setup_method(self):
        self.client = TestClient(app)

    def _get_books(self, cached_entries: list[dict]) -> list[dict]:
        with (
            patch("back_office_lmelp.app.memory_guard") as mock_memory_guard,
            patch(
                "back_office_lmelp.app.livres_auteurs_cache_service"
            ) as mock_cache_service,
            patch("back_office_lmelp.app.mongodb_service") as mock_mongodb,
            patch(
                "back_office_lmelp.app.collections_management_service"
            ) as mock_collections,
        ):
            mock_memory_guard.check_memory_limit.return_value = None
            mock_cache_service.get_books_by_episode_oid.return_value = cached_entries
            mock_mongodb.get_critical_reviews_by_episode_oid.return_value = [
                _avis_critique()
            ]
            mock_collections.cleanup_uncorrected_summaries_for_episode.return_value = {
                "corrected": 0
            }

            response = self.client.get(f"/api/livres-auteurs?episode_oid={EPISODE_OID}")

        assert response.status_code == 200
        books: list[dict] = response.json()
        return books

    def test_books_without_cache_entry_come_back_after_refresh(self):
        """Après rafraîchissement, seule l'entrée mongo reste : les autres livres
        du résumé doivent revenir, sans statut, pour être revalidés."""
        books = self._get_books(
            [
                _mongo_entry(
                    "Docteur écoutez !",
                    "Anne Révah",
                    suggested_title="Docteur, écoutez ! Pour soigner, il faut écouter",
                )
            ]
        )

        titres = sorted(book["titre"] for book in books)
        assert titres == [
            "Docteur écoutez !",
            "L'esprit de l'art culinaire",
            "La Realidad",
        ]
        by_titre = {book["titre"]: book for book in books}
        assert by_titre["Docteur écoutez !"]["status"] == "mongo"
        assert "status" not in by_titre["La Realidad"]
        assert "cache_id" not in by_titre["La Realidad"]

    def test_summary_corrected_to_suggested_title_is_not_duplicated(self):
        """Le ramasse-miettes réécrit le résumé avec le titre validé : ce titre
        correspond à l'entrée mongo et ne doit pas apparaître une 2e fois."""
        corrected = _avis_critique()
        corrected["summary"] = SUMMARY.replace(
            "Docteur écoutez !", "Docteur, écoutez ! Pour soigner, il faut écouter"
        )
        entry = _mongo_entry(
            "Docteur écoutez !",
            "Anne Révah",
            suggested_title="Docteur, écoutez ! Pour soigner, il faut écouter",
        )

        with (
            patch("back_office_lmelp.app.memory_guard") as mock_memory_guard,
            patch(
                "back_office_lmelp.app.livres_auteurs_cache_service"
            ) as mock_cache_service,
            patch("back_office_lmelp.app.mongodb_service") as mock_mongodb,
            patch(
                "back_office_lmelp.app.collections_management_service"
            ) as mock_collections,
        ):
            mock_memory_guard.check_memory_limit.return_value = None
            mock_cache_service.get_books_by_episode_oid.return_value = [entry]
            mock_mongodb.get_critical_reviews_by_episode_oid.return_value = [corrected]
            mock_collections.cleanup_uncorrected_summaries_for_episode.return_value = {
                "corrected": 0
            }
            response = self.client.get(f"/api/livres-auteurs?episode_oid={EPISODE_OID}")

        titres = sorted(book["titre"] for book in response.json())
        assert titres == [
            "Docteur écoutez !",
            "L'esprit de l'art culinaire",
            "La Realidad",
        ]

    def test_fully_cached_episode_returns_cache_only(self):
        """Épisode entièrement en cache : rien n'est ajouté."""
        books = self._get_books(
            [
                _mongo_entry("Docteur écoutez !", "Anne Révah"),
                _mongo_entry("La Realidad", "Neige Sinno"),
                _mongo_entry(
                    "L'esprit de l'art culinaire",
                    "Carl Friedrich von Rumohr",
                    programme=False,
                ),
            ]
        )

        assert len(books) == 3
        assert all(book["status"] == "mongo" for book in books)

    def test_complete_cache_with_title_variants_adds_nothing(self):
        """Cache aussi long que le résumé : un titre du résumé qui diffère de
        son entrée (« Peau d'ours » / « Peau d'ourse ») n'est pas un livre
        manquant. Cas réel : 11 épisodes sur 188 en base locale."""
        books = self._get_books(
            [
                _mongo_entry("Docteur, écoutez !", "Anne Revah"),
                _mongo_entry("La Réalidade", "Neige Sinault"),
                _mongo_entry(
                    "L'esprit de la cuisine",
                    "Carl Friedrich von Rumohr",
                    programme=False,
                ),
            ]
        )

        assert len(books) == 3
        assert all(book["status"] == "mongo" for book in books)


class TestRefreshEndpointKeepsMongoEntries:
    """DELETE /api/livres-auteurs/cache/episode/{oid} garde les livres en base."""

    def setup_method(self):
        self.client = TestClient(app)

    def test_refresh_deletes_only_unvalidated_entries(self):
        cache_collection = MagicMock()
        cache_collection.delete_many.return_value = MagicMock(deleted_count=2)

        with patch(
            "back_office_lmelp.services.livres_auteurs_cache_service."
            "livres_auteurs_cache_service.mongodb_service"
        ) as mock_mongodb:
            mock_mongodb.get_collection.return_value = cache_collection
            response = self.client.delete(
                f"/api/livres-auteurs/cache/episode/{EPISODE_OID}"
            )

        assert response.status_code == 200
        assert response.json()["deleted_count"] == 2
        cache_collection.delete_many.assert_called_once_with(
            {"episode_oid": EPISODE_OID, "status": {"$ne": "mongo"}}
        )


class TestBooksMissingFromCache:
    """Repère les livres du résumé qui n'ont pas d'entrée de cache."""

    def test_matches_cache_titre_suggested_and_validated_titles(self):
        from back_office_lmelp.services.books_extraction_service import (
            BooksExtractionService,
        )

        cached = [
            {"titre": "Docteur écoutez !", "suggested_title": "Docteur, écoutez !"},
            {"titre": "Tressaillir", "validated_title": "Tressaillir (poche)"},
        ]
        extracted = [
            {"titre": "docteur ecoutez !"},  # casse/accents de l'entrée
            {"titre": "Docteur, écoutez !"},  # titre corrigé dans le résumé
            {"titre": "Tressaillir (poche)"},  # titre validé à la main
            {"titre": "La Realidad"},  # absent du cache
        ]

        missing = BooksExtractionService.books_missing_from_cache(extracted, cached)

        assert missing == [{"titre": "La Realidad"}]


class TestExtractAvisMatchesBooksLinkedToEpisode:
    """POST /api/avis/extract matche un livre en base lié à l'épisode, même si
    son entrée de cache n'est plus en `mongo` (rafraîchissement, revalidation
    Babelio qui propose un autre titre)."""

    def setup_method(self):
        self.mock_mongodb = MagicMock()
        self.patcher = patch("back_office_lmelp.app.mongodb_service", self.mock_mongodb)
        self.patcher.start()
        self.client = TestClient(app)

    def teardown_method(self):
        self.patcher.stop()

    def test_livre_en_base_matche_malgre_entree_cache_suggested(self):
        emission_id = ObjectId()
        episode_id = ObjectId(EPISODE_OID)
        self.mock_mongodb.emissions_collection.find_one.return_value = {
            "_id": emission_id,
            "episode_id": episode_id,
            "avis_critique_id": AVIS_CRITIQUE_ID,
        }
        self.mock_mongodb.avis_critiques_collection.find_one.return_value = (
            _avis_critique()
        )
        # Aucune entrée `mongo` dans le cache (l'entrée est repassée en suggested)
        self.mock_mongodb.get_collection.return_value.find.return_value = []
        # Le livre existe en base et est lié à l'épisode
        livre_realidad = {
            "_id": BOOK_ID,
            "titre": "La Realidad",
            "auteur_id": AUTHOR_ID,
            "editeur": "P.O.L",
            "episodes": [EPISODE_OID],
        }
        livre_docteur = {
            "_id": DOCTEUR_BOOK_ID,
            "titre": "Docteur, écoutez ! Pour soigner, il faut écouter",
            "auteur_id": DOCTEUR_AUTHOR_ID,
            "editeur": "Albin Michel",
            "episodes": [EPISODE_OID],
        }
        self.mock_mongodb.livres_collection.find.return_value = [
            livre_realidad,
            livre_docteur,
        ]
        self.mock_mongodb.critiques_collection.find.return_value = []
        self.mock_mongodb.delete_avis_by_emission.return_value = 0
        self.mock_mongodb.save_avis_batch.side_effect = lambda docs: [
            str(ObjectId()) for _ in docs
        ]

        response = self.client.post(f"/api/avis/extract/{emission_id}")

        assert response.status_code == 200
        saved = self.mock_mongodb.save_avis_batch.call_args[0][0]
        realidad = [d for d in saved if d["livre_titre_extrait"] == "La Realidad"]
        assert realidad
        assert all(d["livre_oid"] == str(BOOK_ID) for d in realidad)
        docteur = [d for d in saved if d["livre_titre_extrait"] == "Docteur écoutez !"]
        assert docteur
        assert all(d["livre_oid"] == str(livre_docteur["_id"]) for d in docteur)
        self.mock_mongodb.livres_collection.find.assert_any_call(
            {"episodes": EPISODE_OID}
        )
