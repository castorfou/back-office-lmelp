"""Tests pour les endpoints API emissions (Issue #154)."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bson import ObjectId


@pytest.fixture
def mock_emission():
    """Fixture pour une émission mock."""
    return {
        "_id": ObjectId("686bf5e18380ee925ae5e318"),  # pragma: allowlist secret
        "episode_id": ObjectId("686bf5e18380ee925ae5e319"),  # pragma: allowlist secret
        "avis_critique_id": ObjectId(
            "686c48b728b9e451c1cee31f"  # pragma: allowlist secret
        ),
        "date": datetime(2025, 7, 6),
        "duree": 1800,
        "animateur_id": ObjectId(
            "686c48b728b9e451c1cee320"  # pragma: allowlist secret
        ),
        "avis_ids": [],
        "created_at": datetime(2025, 1, 1),
        "updated_at": datetime(2025, 1, 1),
    }


@pytest.fixture
def mock_episode():
    """Fixture pour un épisode mock."""
    return {
        "_id": ObjectId("686bf5e18380ee925ae5e319"),  # pragma: allowlist secret
        "titre": "Épisode du 6 juillet 2025",
        "date": datetime(2025, 7, 6),
        "description": "Description de l'épisode",
        "duree": 1800,
        "type": "radio",
        "episode_page_url": "https://www.radiofrance.fr/franceinter/podcasts/le-masque-et-la-plume/...",
        "masked": False,
    }


class TestGetAllEmissions:
    """Tests pour GET /api/emissions."""

    def test_should_return_emissions_list(self, client, mock_emission, mock_episode):
        """Doit retourner la liste des émissions."""
        with patch("back_office_lmelp.app.mongodb_service") as mock_service:
            mock_service.get_all_emissions.return_value = [mock_emission]
            mock_service.get_episode_by_id.return_value = mock_episode
            mock_service.get_avis_critique_by_id.return_value = {
                "_id": mock_emission["avis_critique_id"]
            }

            response = client.get("/api/emissions")

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["id"] == str(mock_emission["_id"])
            assert data[0]["episode"]["titre"] == mock_episode["titre"]

    def test_should_trigger_auto_conversion_if_empty(self, client):
        """Doit déclencher l'auto-conversion si collection vide."""
        with (
            patch("back_office_lmelp.app.mongodb_service") as mock_service,
            patch(
                "back_office_lmelp.app.auto_convert_episodes_to_emissions"
            ) as mock_convert,
        ):
            # Premier appel retourne liste vide, deuxième après conversion retourne toujours vide
            mock_service.get_all_emissions.return_value = []
            mock_convert.return_value = AsyncMock()

            response = client.get("/api/emissions")

            assert response.status_code == 200
            # Vérifier que auto_convert a été appelé
            mock_convert.assert_called_once()


class TestGetEmissionDetails:
    """Tests pour GET /api/emissions/{emission_id}/details."""

    def test_should_return_404_if_emission_not_found(self, client):
        """Doit retourner 404 si émission non trouvée."""
        with patch("back_office_lmelp.app.mongodb_service") as mock_service:
            mock_service.emissions_collection.find_one.return_value = None

            response = client.get("/api/emissions/686bf5e18380ee925ae5e318/details")

            assert response.status_code == 404

    def test_should_validate_objectid_format(self, client):
        """Doit valider le format ObjectId."""
        response = client.get("/api/emissions/invalid-id/details")

        assert response.status_code == 400
        data = response.json()
        assert "Format d'ID invalide" in data["detail"]

    def test_should_return_emission_with_full_details(
        self, client, mock_emission, mock_episode
    ):
        """Doit retourner tous les détails de l'émission."""
        mock_avis = {
            "_id": mock_emission["avis_critique_id"],
            "summary": "## 1. LIVRES DISCUTÉS\n**Auteur Exemple**: Livre test",
        }
        mock_critiques = [{"id": "123", "nom": "Jérôme Garcin", "animateur": True}]

        # Setup mock data for collections
        book_id = ObjectId("68e2c3ba1391489c77ccdee2")  # pragma: allowlist secret
        author_id = ObjectId("68e2c3ba1391489c77ccdee1")  # pragma: allowlist secret

        mock_cache_entry = {
            "episode_oid": str(mock_emission["episode_id"]),
            "book_id": book_id,
            "author_id": author_id,
            "status": "mongo",
        }

        mock_livre = {
            "_id": book_id,
            "titre": "Livre test",
            "auteur_id": author_id,
            "editeur": "Éditeur test",
        }

        mock_auteur = {
            "_id": author_id,
            "nom": "Auteur Exemple",
        }

        with patch("back_office_lmelp.app.mongodb_service") as mock_service:
            mock_service.emissions_collection.find_one.return_value = mock_emission
            mock_service.get_episode_by_id.return_value = mock_episode
            mock_service.get_avis_critique_by_id.return_value = mock_avis
            mock_service.get_critiques_by_episode.return_value = mock_critiques

            # Mock cache collection
            mock_cache_collection = MagicMock()
            mock_cache_collection.find.return_value = iter([mock_cache_entry])

            # Mock livres collection
            mock_livres_collection = MagicMock()
            mock_livres_collection.find.return_value = iter([mock_livre])

            # Mock auteurs collection
            mock_auteurs_collection = MagicMock()
            mock_auteurs_collection.find.return_value = iter([mock_auteur])

            # Setup get_collection to return cache mock
            def get_collection_mock(collection_name):
                if collection_name == "livresauteurs_cache":
                    return mock_cache_collection
                return MagicMock()

            mock_service.get_collection.side_effect = get_collection_mock
            mock_service.livres_collection = mock_livres_collection
            mock_service.auteurs_collection = mock_auteurs_collection

            emission_id = str(mock_emission["_id"])
            response = client.get(f"/api/emissions/{emission_id}/details")

            assert response.status_code == 200
            data = response.json()

            assert "emission" in data
            assert "episode" in data
            assert "summary" in data
            assert "books" in data
            assert "critiques" in data
            assert data["episode"]["titre"] == mock_episode["titre"]
            assert len(data["books"]) == 1
            assert len(data["critiques"]) == 1

    def test_should_use_livres_auteurs_collections_not_cache(
        self, client, mock_emission, mock_episode
    ):
        """Issue #177: Doit utiliser les collections livres/auteurs, pas livresauteurs_cache.

        Test d'intégration qui démontre le problème business:
        - Le cache contient des valeurs CACHE_AUTHOR/CACHE_TITLE (fausses données)
        - Les collections contiennent les vraies données (Laurent Mauvignier, La Maison Vide)
        - La réponse API DOIT contenir les données des collections, PAS du cache
        """
        mock_avis = {
            "_id": mock_emission["avis_critique_id"],
            "summary": "## 1. LIVRES DISCUTÉS\n**Laurent Mauvignier**: La Maison Vide",
        }
        mock_critiques = [{"id": "123", "nom": "Jérôme Garcin", "animateur": True}]

        # Mock cache entries (WRONG VALUES - should NOT appear in response)
        book_id = ObjectId("68e2c3ba1391489c77ccdee2")  # pragma: allowlist secret
        author_id = ObjectId("68e2c3ba1391489c77ccdee1")  # pragma: allowlist secret
        mock_cache_entries = [
            {
                "_id": ObjectId("68e2c3babf26cd8dd9a0a334"),  # pragma: allowlist secret
                "episode_oid": str(mock_emission["episode_id"]),
                "book_id": book_id,
                "author_id": author_id,
                "status": "mongo",
                # Cache fields (WRONG VALUES - should NOT appear in response)
                "auteur": "CACHE_AUTHOR_NAME",
                "titre": "CACHE_BOOK_TITLE",
                "editeur": "CACHE_PUBLISHER",
            }
        ]

        # Mock authoritative collection data (CORRECT VALUES - should appear in response)
        mock_livre = {
            "_id": book_id,
            "titre": "La Maison Vide",  # Authoritative title
            "auteur_id": author_id,
            "editeur": "Éditions de Minuit",
            "url_babelio": "https://www.babelio.com/livres/Mauvignier-La-Maison-vide/1234",
        }

        mock_auteur = {
            "_id": author_id,
            "nom": "Laurent Mauvignier",  # Authoritative author name
            "url_babelio": "https://www.babelio.com/auteur/Laurent-Mauvignier/5678",
        }

        with patch("back_office_lmelp.app.mongodb_service") as mock_service:
            # Mock emissions/episode/avis/critiques (standard setup)
            mock_service.emissions_collection.find_one.return_value = mock_emission
            mock_service.get_episode_by_id.return_value = mock_episode
            mock_service.get_avis_critique_by_id.return_value = mock_avis
            mock_service.get_critiques_by_episode.return_value = mock_critiques

            # Mock cache collection query (returns cache entries)
            mock_cache_collection = MagicMock()
            mock_cache_collection.find.return_value = iter(mock_cache_entries)

            # Mock livres collection query (returns authoritative data)
            mock_livres_collection = MagicMock()
            mock_livres_collection.find.return_value = iter([mock_livre])

            # Mock auteurs collection query (returns authoritative data)
            mock_auteurs_collection = MagicMock()
            mock_auteurs_collection.find.return_value = iter([mock_auteur])

            # Setup get_collection to return appropriate mock based on collection name
            def get_collection_mock(collection_name):
                if collection_name == "livresauteurs_cache":
                    return mock_cache_collection
                return MagicMock()

            mock_service.get_collection.side_effect = get_collection_mock
            mock_service.livres_collection = mock_livres_collection
            mock_service.auteurs_collection = mock_auteurs_collection

            emission_id = str(mock_emission["_id"])
            response = client.get(f"/api/emissions/{emission_id}/details")

            assert response.status_code == 200
            data = response.json()

            # CRITICAL ASSERTION: Books must come from collections, NOT cache
            books = data["books"]
            assert len(books) == 1

            # Verify data comes from livres/auteurs collections
            assert books[0]["titre"] == "La Maison Vide"  # From livres.titre
            assert books[0]["auteur"] == "Laurent Mauvignier"  # From auteurs.nom
            assert books[0]["editeur"] == "Éditions de Minuit"  # From livres.editeur

            # MUST NOT contain cache values
            assert books[0]["titre"] != "CACHE_BOOK_TITLE"
            assert books[0]["auteur"] != "CACHE_AUTHOR_NAME"
            assert books[0]["editeur"] != "CACHE_PUBLISHER"


class TestGetEmissionByDate:
    """Tests pour GET /api/emissions/by-date/{YYYYMMDD}."""

    def test_should_validate_date_format(self, client):
        """Doit valider le format de date YYYYMMDD."""
        response = client.get("/api/emissions/by-date/invalid")

        assert response.status_code == 400
        data = response.json()
        assert "Format de date invalide" in data["detail"]

    def test_should_return_404_if_date_not_found(self, client):
        """Doit retourner 404 si aucune émission pour cette date."""
        with patch("back_office_lmelp.app.mongodb_service") as mock_service:
            mock_service.emissions_collection.find_one.return_value = None

            response = client.get("/api/emissions/by-date/20250101")

            assert response.status_code == 404
            data = response.json()
            assert "Aucune émission trouvée" in data["detail"]

    def test_should_return_emission_for_valid_date(
        self, client, mock_emission, mock_episode
    ):
        """Doit retourner l'émission pour une date valide."""
        mock_avis = {
            "_id": mock_emission["avis_critique_id"],
            "summary": "## 1. LIVRES DISCUTÉS\n**Auteur Exemple**: Livre test",
        }

        mock_books = [{"auteur": "Auteur Exemple", "titre": "Livre test"}]
        mock_critiques = [{"id": "123", "nom": "Jérôme Garcin", "animateur": True}]

        with (
            patch("back_office_lmelp.app.mongodb_service") as mock_service,
            patch("back_office_lmelp.app.get_livres_auteurs") as mock_books_endpoint,
        ):
            mock_service.emissions_collection.find_one.return_value = mock_emission
            mock_service.get_episode_by_id.return_value = mock_episode
            mock_service.get_avis_critique_by_id.return_value = mock_avis
            mock_service.get_critiques_by_episode.return_value = mock_critiques
            mock_books_endpoint.return_value = mock_books

            # Date format YYYYMMDD pour 2025-07-06
            response = client.get("/api/emissions/by-date/20250706")

            assert response.status_code == 200
            data = response.json()

            assert "emission" in data
            assert "episode" in data
            assert data["episode"]["titre"] == mock_episode["titre"]


class TestOrphanAvisCritiqueIdFallback:
    """Tests pour le fallback quand avis_critique_id est orphelin.

    Issue #188: Quand l'émission référence un avis_critique_id qui n'existe plus
    (par exemple si le frontend lmelp a régénéré le summary avec un nouvel ID),
    l'endpoint doit faire un fallback en cherchant l'avis_critique par episode_oid.

    Scénario réel:  # pragma: allowlist secret
        1. Emission pointe vers avis_critique_id = "692b6c7bba26dcb8c46d94dd"
        2. Frontend lmelp régénère le summary → nouvel ID (MongoDB ObjectId)
        3. L'ancien avis_critique est supprimé
        4. Appel GET /api/emissions/by-date/20230402 → 404 (avis non trouvé)

    Solution:
        Si get_avis_critique_by_id() retourne None, chercher par episode_oid.
    """

    def test_should_fallback_to_episode_oid_when_avis_critique_id_orphan(
        self, client, mock_emission, mock_episode
    ):
        """
        Test TDD RED: Doit chercher l'avis_critique par episode_oid si l'ID est orphelin.

        Scénario:  # pragma: allowlist secret
            - L'émission a avis_critique_id = "692b..." (orphelin, MongoDB ObjectId)
            - get_avis_critique_by_id() → None
            - L'avis_critique avec episode_oid existe
            - Le fallback doit trouver cet avis_critique et retourner 200
        """
        # Setup: L'avis_critique référencé n'existe plus (orphelin)
        orphan_avis_id = ObjectId("692b6c7bba26dcb8c46d94dd")
        new_avis_id = ObjectId("69779615253570b7be2be59b")

        # L'émission pointe vers l'ancien ID orphelin
        mock_emission_with_orphan = {
            **mock_emission,
            "avis_critique_id": orphan_avis_id,
        }

        # Le nouvel avis_critique (créé par frontend lmelp)
        new_avis_critique = {
            "_id": new_avis_id,
            "episode_oid": str(mock_episode["_id"]),
            "summary": "## 1. LIVRES DISCUTÉS\n**Auteur Exemple**: Livre test",
        }

        mock_critiques = [{"id": "123", "nom": "Jérôme Garcin", "animateur": True}]

        # Setup mock data for books
        book_id = ObjectId("68e2c3ba1391489c77ccdee2")
        author_id = ObjectId("68e2c3ba1391489c77ccdee1")

        mock_cache_entry = {
            "episode_oid": str(mock_episode["_id"]),
            "book_id": book_id,
            "author_id": author_id,
            "status": "mongo",
        }

        mock_livre = {
            "_id": book_id,
            "titre": "Livre test",
            "auteur_id": author_id,
            "editeur": "Éditeur test",
        }

        mock_auteur = {
            "_id": author_id,
            "nom": "Auteur Exemple",
        }

        with patch("back_office_lmelp.app.mongodb_service") as mock_service:
            mock_service.emissions_collection.find_one.return_value = (
                mock_emission_with_orphan
            )
            mock_service.get_episode_by_id.return_value = mock_episode

            # CRITICAL: get_avis_critique_by_id retourne None pour l'ID orphelin
            # mais retourne l'avis quand on cherche par episode_oid
            def mock_get_avis_critique_by_id(avis_id):
                if avis_id == str(orphan_avis_id):
                    return None  # ID orphelin → non trouvé
                return new_avis_critique

            mock_service.get_avis_critique_by_id.side_effect = (
                mock_get_avis_critique_by_id
            )

            # Mock pour la recherche par episode_oid (fallback via nouvelle méthode)
            mock_service.get_avis_critique_by_episode_oid.return_value = (
                new_avis_critique
            )

            mock_service.get_critiques_by_episode.return_value = mock_critiques

            # Mock cache and collections
            mock_cache_collection = MagicMock()
            mock_cache_collection.find.return_value = iter([mock_cache_entry])

            mock_livres_collection = MagicMock()
            mock_livres_collection.find.return_value = iter([mock_livre])

            mock_auteurs_collection = MagicMock()
            mock_auteurs_collection.find.return_value = iter([mock_auteur])

            def get_collection_mock(collection_name):
                if collection_name == "livresauteurs_cache":
                    return mock_cache_collection
                return MagicMock()

            mock_service.get_collection.side_effect = get_collection_mock
            mock_service.livres_collection = mock_livres_collection
            mock_service.auteurs_collection = mock_auteurs_collection

            emission_id = str(mock_emission_with_orphan["_id"])
            response = client.get(f"/api/emissions/{emission_id}/details")

            # CRITICAL: Doit retourner 200, pas 404
            assert response.status_code == 200, (
                f"Should return 200 with fallback, got {response.status_code}: "
                f"{response.json()}"
            )

            data = response.json()
            assert "summary" in data
            assert "## 1. LIVRES DISCUTÉS" in data["summary"]

    def test_should_fallback_to_episode_oid_via_by_date_endpoint(
        self, client, mock_emission, mock_episode
    ):
        """
        Test TDD RED: Le fallback doit aussi fonctionner via /api/emissions/by-date/.

        Même scénario que ci-dessus, mais via l'endpoint by-date.
        """
        orphan_avis_id = ObjectId("692b6c7bba26dcb8c46d94dd")
        new_avis_id = ObjectId("69779615253570b7be2be59b")

        mock_emission_with_orphan = {
            **mock_emission,
            "avis_critique_id": orphan_avis_id,
            "date": mock_episode["date"],  # 2025-07-06
        }

        new_avis_critique = {
            "_id": new_avis_id,
            "episode_oid": str(mock_episode["_id"]),
            "summary": "## 1. LIVRES DISCUTÉS\n**Auteur Exemple**: Livre test",
        }

        mock_critiques = [{"id": "123", "nom": "Jérôme Garcin", "animateur": True}]

        book_id = ObjectId("68e2c3ba1391489c77ccdee2")
        author_id = ObjectId("68e2c3ba1391489c77ccdee1")

        mock_cache_entry = {
            "episode_oid": str(mock_episode["_id"]),
            "book_id": book_id,
            "author_id": author_id,
            "status": "mongo",
        }

        mock_livre = {
            "_id": book_id,
            "titre": "Livre test",
            "auteur_id": author_id,
            "editeur": "Éditeur test",
        }

        mock_auteur = {
            "_id": author_id,
            "nom": "Auteur Exemple",
        }

        with patch("back_office_lmelp.app.mongodb_service") as mock_service:
            mock_service.emissions_collection.find_one.return_value = (
                mock_emission_with_orphan
            )
            mock_service.get_episode_by_id.return_value = mock_episode

            def mock_get_avis_critique_by_id(avis_id):
                if avis_id == str(orphan_avis_id):
                    return None
                return new_avis_critique

            mock_service.get_avis_critique_by_id.side_effect = (
                mock_get_avis_critique_by_id
            )
            mock_service.get_avis_critique_by_episode_oid.return_value = (
                new_avis_critique
            )

            mock_service.get_critiques_by_episode.return_value = mock_critiques

            mock_cache_collection = MagicMock()
            mock_cache_collection.find.return_value = iter([mock_cache_entry])

            mock_livres_collection = MagicMock()
            mock_livres_collection.find.return_value = iter([mock_livre])

            mock_auteurs_collection = MagicMock()
            mock_auteurs_collection.find.return_value = iter([mock_auteur])

            def get_collection_mock(collection_name):
                if collection_name == "livresauteurs_cache":
                    return mock_cache_collection
                return MagicMock()

            mock_service.get_collection.side_effect = get_collection_mock
            mock_service.livres_collection = mock_livres_collection
            mock_service.auteurs_collection = mock_auteurs_collection

            # Date format YYYYMMDD pour 2025-07-06
            response = client.get("/api/emissions/by-date/20250706")

            assert response.status_code == 200, (
                f"Should return 200 with fallback, got {response.status_code}: "
                f"{response.json()}"
            )

            data = response.json()
            assert "summary" in data
            assert "## 1. LIVRES DISCUTÉS" in data["summary"]

    def test_should_update_emission_avis_critique_id_after_fallback(
        self, client, mock_emission, mock_episode
    ):
        """
        Test TDD RED: Après fallback, doit mettre à jour l'émission avec le nouvel ID.

        Pour éviter de refaire le fallback à chaque appel, on met à jour
        emissions.avis_critique_id avec le nouvel ID trouvé.
        """
        orphan_avis_id = ObjectId("692b6c7bba26dcb8c46d94dd")
        new_avis_id = ObjectId("69779615253570b7be2be59b")

        mock_emission_with_orphan = {
            **mock_emission,
            "avis_critique_id": orphan_avis_id,
        }

        new_avis_critique = {
            "_id": new_avis_id,
            "episode_oid": str(mock_episode["_id"]),
            "summary": "## 1. LIVRES DISCUTÉS\n**Auteur**: Livre",
        }

        mock_critiques = []

        book_id = ObjectId("68e2c3ba1391489c77ccdee2")
        author_id = ObjectId("68e2c3ba1391489c77ccdee1")

        mock_cache_entry = {
            "episode_oid": str(mock_episode["_id"]),
            "book_id": book_id,
            "author_id": author_id,
            "status": "mongo",
        }

        mock_livre = {"_id": book_id, "titre": "Livre", "auteur_id": author_id}
        mock_auteur = {"_id": author_id, "nom": "Auteur"}

        with patch("back_office_lmelp.app.mongodb_service") as mock_service:
            mock_service.emissions_collection.find_one.return_value = (
                mock_emission_with_orphan
            )
            mock_service.get_episode_by_id.return_value = mock_episode

            def mock_get_avis_critique_by_id(avis_id):
                if avis_id == str(orphan_avis_id):
                    return None
                return new_avis_critique

            mock_service.get_avis_critique_by_id.side_effect = (
                mock_get_avis_critique_by_id
            )
            mock_service.get_avis_critique_by_episode_oid.return_value = (
                new_avis_critique
            )
            mock_service.get_critiques_by_episode.return_value = mock_critiques

            mock_cache_collection = MagicMock()
            mock_cache_collection.find.return_value = iter([mock_cache_entry])

            mock_livres_collection = MagicMock()
            mock_livres_collection.find.return_value = iter([mock_livre])

            mock_auteurs_collection = MagicMock()
            mock_auteurs_collection.find.return_value = iter([mock_auteur])

            def get_collection_mock(collection_name):
                if collection_name == "livresauteurs_cache":
                    return mock_cache_collection
                return MagicMock()

            mock_service.get_collection.side_effect = get_collection_mock
            mock_service.livres_collection = mock_livres_collection
            mock_service.auteurs_collection = mock_auteurs_collection

            emission_id = str(mock_emission_with_orphan["_id"])
            response = client.get(f"/api/emissions/{emission_id}/details")

            assert response.status_code == 200

            # CRITICAL: Vérifier que l'émission a été mise à jour
            mock_service.emissions_collection.update_one.assert_called_once()

            update_call = mock_service.emissions_collection.update_one.call_args
            filter_arg = update_call[0][0]
            update_arg = update_call[0][1]

            assert filter_arg["_id"] == mock_emission_with_orphan["_id"]
            assert "$set" in update_arg
            # Note: avis_critique_id est stocké comme string, pas ObjectId
            assert update_arg["$set"]["avis_critique_id"] == str(new_avis_id)


class TestAutoConvertEpisodes:
    """Tests pour POST /api/emissions/auto-convert."""

    def test_should_skip_masked_episodes(self, client):
        """Doit ignorer les épisodes masqués (masked=True)."""
        mock_avis = [
            {
                "_id": ObjectId("686c48b728b9e451c1cee31f"),  # pragma: allowlist secret
                "episode_oid": "686bf5e18380ee925ae5e319",  # pragma: allowlist secret
                "summary": "**Rebecca Manzoni**: Test",
            }
        ]

        # Épisode masqué
        mock_episode_masked = {
            "_id": ObjectId("686bf5e18380ee925ae5e319"),  # pragma: allowlist secret
            "titre": "Épisode masqué",
            "date": datetime(2025, 7, 6),
            "duree": 1800,
            "masked": True,  # MASQUÉ
        }

        with patch("back_office_lmelp.app.mongodb_service") as mock_service:
            mock_service.get_all_critical_reviews.return_value = mock_avis
            mock_service.get_emission_by_episode_id.return_value = None
            mock_service.get_episode_by_id.return_value = mock_episode_masked

            response = client.post("/api/emissions/auto-convert")

            assert response.status_code == 200
            data = response.json()
            assert data["created"] == 0  # Aucune émission créée
            assert data["skipped"] == 1  # Episode masqué skip

    def test_should_create_emission_from_avis(self, client, mock_episode):
        """Doit créer une émission depuis un avis critique."""
        mock_avis = [
            {
                "_id": ObjectId("686c48b728b9e451c1cee31f"),  # pragma: allowlist secret
                "episode_oid": str(mock_episode["_id"]),
                "summary": "**Rebecca Manzoni**: Test",
            }
        ]

        mock_critiques = [{"id": "123", "nom": "Rebecca Manzoni", "animateur": True}]

        with (
            patch("back_office_lmelp.app.mongodb_service") as mock_service,
            patch("back_office_lmelp.app.Emission") as mock_emission_class,
        ):
            mock_service.get_all_critical_reviews.return_value = mock_avis
            mock_service.get_emission_by_episode_id.return_value = (
                None  # Pas d'émission existante
            )
            mock_service.get_episode_by_id.return_value = mock_episode
            mock_service.get_critiques_by_episode.return_value = mock_critiques
            mock_service.create_emission.return_value = "new_emission_id"

            # Mock Emission.for_mongodb_insert
            mock_emission_class.for_mongodb_insert.return_value = {
                "episode_id": mock_episode["_id"],
                "avis_critique_id": ObjectId(
                    "686c48b728b9e451c1cee31f"  # pragma: allowlist secret
                ),
                "date": mock_episode["date"],
                "duree": mock_episode["duree"],
                "animateur_id": "123",
                "avis_ids": [],
            }

            # Mock Episode constructor to return mock_episode
            with patch("back_office_lmelp.app.Episode") as mock_episode_class:
                mock_episode_instance = MagicMock()
                mock_episode_instance.date = mock_episode["date"]
                mock_episode_instance.duree = mock_episode["duree"]
                mock_episode_instance.masked = mock_episode["masked"]  # False
                mock_episode_class.return_value = mock_episode_instance

                response = client.post("/api/emissions/auto-convert")

                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["created"] == 1
                assert data["skipped"] == 0
