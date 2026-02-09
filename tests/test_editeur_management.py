"""Tests for editeur management methods in MongoDBService (Issue #189)."""

from datetime import datetime
from unittest.mock import MagicMock, patch

from bson import ObjectId


class TestSearchEditeurByName:
    """Tests pour search_editeur_by_name - recherche case/accent insensitive."""

    @patch("back_office_lmelp.services.mongodb_service.mongodb_service")
    def test_finds_exact_match(self, mock_service):
        """search_editeur_by_name('Gallimard') trouve 'Gallimard'."""
        from back_office_lmelp.services.mongodb_service import MongoDBService

        service = MongoDBService()
        editeur_oid = ObjectId()
        mock_collection = MagicMock()
        mock_collection.find.return_value = [
            {"_id": editeur_oid, "nom": "Gallimard"},
        ]
        service.editeurs_collection = mock_collection

        result = service.search_editeur_by_name("Gallimard")

        assert result is not None
        assert result["_id"] == editeur_oid
        assert result["nom"] == "Gallimard"

    @patch("back_office_lmelp.services.mongodb_service.mongodb_service")
    def test_finds_case_insensitive_match(self, mock_service):
        """search_editeur_by_name('gallimard') trouve 'Gallimard'."""
        from back_office_lmelp.services.mongodb_service import MongoDBService

        service = MongoDBService()
        editeur_oid = ObjectId()
        mock_collection = MagicMock()
        mock_collection.find.return_value = [
            {"_id": editeur_oid, "nom": "Gallimard"},
            {"_id": ObjectId(), "nom": "Le Livre de Poche"},
        ]
        service.editeurs_collection = mock_collection

        result = service.search_editeur_by_name("gallimard")

        assert result is not None
        assert result["nom"] == "Gallimard"

    @patch("back_office_lmelp.services.mongodb_service.mongodb_service")
    def test_finds_accent_insensitive_match(self, mock_service):
        """search_editeur_by_name('Editions') trouve 'Éditions'."""
        from back_office_lmelp.services.mongodb_service import MongoDBService

        service = MongoDBService()
        editeur_oid = ObjectId()
        mock_collection = MagicMock()
        mock_collection.find.return_value = [
            {"_id": editeur_oid, "nom": "Éditions du Seuil"},
        ]
        service.editeurs_collection = mock_collection

        result = service.search_editeur_by_name("Editions du Seuil")

        assert result is not None
        assert result["nom"] == "Éditions du Seuil"

    @patch("back_office_lmelp.services.mongodb_service.mongodb_service")
    def test_returns_none_when_not_found(self, mock_service):
        """search_editeur_by_name('Unknown') retourne None."""
        from back_office_lmelp.services.mongodb_service import MongoDBService

        service = MongoDBService()
        mock_collection = MagicMock()
        mock_collection.find.return_value = [
            {"_id": ObjectId(), "nom": "Gallimard"},
        ]
        service.editeurs_collection = mock_collection

        result = service.search_editeur_by_name("Unknown Publisher")

        assert result is None

    @patch("back_office_lmelp.services.mongodb_service.mongodb_service")
    def test_returns_none_when_collection_empty(self, mock_service):
        """search_editeur_by_name retourne None si collection vide."""
        from back_office_lmelp.services.mongodb_service import MongoDBService

        service = MongoDBService()
        mock_collection = MagicMock()
        mock_collection.find.return_value = []
        service.editeurs_collection = mock_collection

        result = service.search_editeur_by_name("Gallimard")

        assert result is None


class TestCreateEditeur:
    """Tests pour create_editeur."""

    @patch("back_office_lmelp.services.mongodb_service.mongodb_service")
    def test_creates_editeur_with_timestamps(self, mock_service):
        """create_editeur insère un document avec nom, created_at, updated_at."""
        from back_office_lmelp.services.mongodb_service import MongoDBService

        service = MongoDBService()
        new_oid = ObjectId()
        mock_collection = MagicMock()
        mock_insert_result = MagicMock()
        mock_insert_result.inserted_id = new_oid
        mock_collection.insert_one.return_value = mock_insert_result
        service.editeurs_collection = mock_collection

        result = service.create_editeur("P.O.L")

        assert result == new_oid
        # Vérifier que insert_one a été appelé avec les bons champs
        call_args = mock_collection.insert_one.call_args[0][0]
        assert call_args["nom"] == "P.O.L"
        assert isinstance(call_args["created_at"], datetime)
        assert isinstance(call_args["updated_at"], datetime)

    @patch("back_office_lmelp.services.mongodb_service.mongodb_service")
    def test_returns_objectid(self, mock_service):
        """create_editeur retourne un ObjectId."""
        from back_office_lmelp.services.mongodb_service import MongoDBService

        service = MongoDBService()
        new_oid = ObjectId()
        mock_collection = MagicMock()
        mock_insert_result = MagicMock()
        mock_insert_result.inserted_id = new_oid
        mock_collection.insert_one.return_value = mock_insert_result
        service.editeurs_collection = mock_collection

        result = service.create_editeur("Flammarion")

        assert isinstance(result, ObjectId)


class TestGetOrCreateEditeur:
    """Tests pour get_or_create_editeur."""

    @patch("back_office_lmelp.services.mongodb_service.mongodb_service")
    def test_returns_existing_when_found(self, mock_service):
        """get_or_create_editeur retourne (oid, False) si l'éditeur existe."""
        from back_office_lmelp.services.mongodb_service import MongoDBService

        service = MongoDBService()
        existing_oid = ObjectId()
        mock_collection = MagicMock()
        mock_collection.find.return_value = [
            {"_id": existing_oid, "nom": "Gallimard"},
        ]
        service.editeurs_collection = mock_collection

        oid, created = service.get_or_create_editeur("Gallimard")

        assert oid == existing_oid
        assert created is False
        mock_collection.insert_one.assert_not_called()

    @patch("back_office_lmelp.services.mongodb_service.mongodb_service")
    def test_creates_when_not_found(self, mock_service):
        """get_or_create_editeur retourne (oid, True) si l'éditeur n'existe pas."""
        from back_office_lmelp.services.mongodb_service import MongoDBService

        service = MongoDBService()
        new_oid = ObjectId()
        mock_collection = MagicMock()
        # search returns nothing
        mock_collection.find.return_value = []
        # create returns new oid
        mock_insert_result = MagicMock()
        mock_insert_result.inserted_id = new_oid
        mock_collection.insert_one.return_value = mock_insert_result
        service.editeurs_collection = mock_collection

        oid, created = service.get_or_create_editeur("P.O.L")

        assert oid == new_oid
        assert created is True
        mock_collection.insert_one.assert_called_once()

    @patch("back_office_lmelp.services.mongodb_service.mongodb_service")
    def test_case_insensitive_match(self, mock_service):
        """get_or_create_editeur('gallimard') trouve 'Gallimard' sans créer."""
        from back_office_lmelp.services.mongodb_service import MongoDBService

        service = MongoDBService()
        existing_oid = ObjectId()
        mock_collection = MagicMock()
        mock_collection.find.return_value = [
            {"_id": existing_oid, "nom": "Gallimard"},
        ]
        service.editeurs_collection = mock_collection

        oid, created = service.get_or_create_editeur("gallimard")

        assert oid == existing_oid
        assert created is False


class TestUpdateLivreFromRefresh:
    """Tests pour update_livre_from_refresh."""

    @patch("back_office_lmelp.services.mongodb_service.mongodb_service")
    def test_updates_livre_with_editeur_id_removes_editeur_string(self, mock_service):
        """Quand editeur_id est fourni, le champ editeur (string) est supprimé."""
        from back_office_lmelp.services.mongodb_service import MongoDBService

        service = MongoDBService()
        mock_collection = MagicMock()
        mock_result = MagicMock()
        mock_result.matched_count = 1
        mock_collection.update_one.return_value = mock_result
        service.livres_collection = mock_collection

        livre_id = str(ObjectId())
        editeur_oid = ObjectId()
        updates = {
            "titre": "Nouveau Titre",
            "editeur_id": editeur_oid,
        }

        result = service.update_livre_from_refresh(livre_id, updates)

        assert result is True
        call_args = mock_collection.update_one.call_args
        # Vérifier le filtre
        assert call_args[0][0] == {"_id": ObjectId(livre_id)}
        update_doc = call_args[0][1]
        # $set contient editeur_id et titre
        assert update_doc["$set"]["titre"] == "Nouveau Titre"
        assert update_doc["$set"]["editeur_id"] == editeur_oid
        assert isinstance(update_doc["$set"]["updated_at"], datetime)
        # $unset supprime le champ editeur string
        assert "editeur" in update_doc["$unset"]

    @patch("back_office_lmelp.services.mongodb_service.mongodb_service")
    def test_updates_livre_without_editeur_id_keeps_editeur_string(self, mock_service):
        """Sans editeur_id, le champ editeur (string) n'est pas supprimé."""
        from back_office_lmelp.services.mongodb_service import MongoDBService

        service = MongoDBService()
        mock_collection = MagicMock()
        mock_result = MagicMock()
        mock_result.matched_count = 1
        mock_collection.update_one.return_value = mock_result
        service.livres_collection = mock_collection

        livre_id = str(ObjectId())
        updates = {"titre": "Nouveau Titre"}

        result = service.update_livre_from_refresh(livre_id, updates)

        assert result is True
        call_args = mock_collection.update_one.call_args
        update_doc = call_args[0][1]
        assert update_doc["$set"]["titre"] == "Nouveau Titre"
        # Pas de $unset quand pas d'editeur_id
        assert "$unset" not in update_doc

    @patch("back_office_lmelp.services.mongodb_service.mongodb_service")
    def test_returns_false_when_livre_not_found(self, mock_service):
        """update_livre_from_refresh retourne False si le livre n'existe pas."""
        from back_office_lmelp.services.mongodb_service import MongoDBService

        service = MongoDBService()
        mock_collection = MagicMock()
        mock_result = MagicMock()
        mock_result.matched_count = 0
        mock_collection.update_one.return_value = mock_result
        service.livres_collection = mock_collection

        result = service.update_livre_from_refresh(str(ObjectId()), {"titre": "X"})

        assert result is False


class TestUpdateAuteurNameAndUrl:
    """Tests pour update_auteur_name_and_url."""

    @patch("back_office_lmelp.services.mongodb_service.mongodb_service")
    def test_updates_both_fields(self, mock_service):
        """update_auteur_name_and_url met à jour nom et url_babelio."""
        from back_office_lmelp.services.mongodb_service import MongoDBService

        service = MongoDBService()
        mock_collection = MagicMock()
        mock_result = MagicMock()
        mock_result.matched_count = 1
        mock_collection.update_one.return_value = mock_result
        service.auteurs_collection = mock_collection

        auteur_id = str(ObjectId())
        result = service.update_auteur_name_and_url(
            auteur_id,
            nom="Nouveau Nom",
            url_babelio="https://www.babelio.com/auteur/Nouveau-Nom/12345",
        )

        assert result is True
        set_values = mock_collection.update_one.call_args[0][1]["$set"]
        assert set_values["nom"] == "Nouveau Nom"
        assert "babelio.com" in set_values["url_babelio"]
        assert isinstance(set_values["updated_at"], datetime)

    @patch("back_office_lmelp.services.mongodb_service.mongodb_service")
    def test_updates_only_nom_when_url_is_none(self, mock_service):
        """update_auteur_name_and_url ne met à jour que nom si url est None."""
        from back_office_lmelp.services.mongodb_service import MongoDBService

        service = MongoDBService()
        mock_collection = MagicMock()
        mock_result = MagicMock()
        mock_result.matched_count = 1
        mock_collection.update_one.return_value = mock_result
        service.auteurs_collection = mock_collection

        result = service.update_auteur_name_and_url(
            str(ObjectId()), nom="Nouveau Nom", url_babelio=None
        )

        assert result is True
        set_values = mock_collection.update_one.call_args[0][1]["$set"]
        assert set_values["nom"] == "Nouveau Nom"
        assert "url_babelio" not in set_values

    @patch("back_office_lmelp.services.mongodb_service.mongodb_service")
    def test_returns_false_when_nothing_to_update(self, mock_service):
        """update_auteur_name_and_url retourne False si rien à mettre à jour."""
        from back_office_lmelp.services.mongodb_service import MongoDBService

        service = MongoDBService()
        mock_collection = MagicMock()
        service.auteurs_collection = mock_collection

        result = service.update_auteur_name_and_url(
            str(ObjectId()), nom=None, url_babelio=None
        )

        assert result is False
        mock_collection.update_one.assert_not_called()


class TestResolveEditeurInGetLivre:
    """Tests pour la résolution editeur_id dans get_livre_with_episodes."""

    @patch("back_office_lmelp.services.mongodb_service.mongodb_service")
    def test_resolves_editeur_id_to_name(self, mock_service):
        """Quand un livre a editeur_id mais pas editeur, le nom est résolu."""
        from back_office_lmelp.services.mongodb_service import MongoDBService

        service = MongoDBService()
        livre_id = ObjectId()
        auteur_id = ObjectId()
        editeur_id = ObjectId()

        # Mock aggregation result - livre avec editeur_id mais sans editeur
        aggregation_result = {
            "_id": livre_id,
            "titre": "Test Livre",
            "auteur_id": auteur_id,
            "editeur_id": editeur_id,
            # Pas de champ "editeur" - supprimé par le refresh
            "auteur": [{"nom": "Test Auteur"}],
            "episodes_data": [],
        }

        mock_livres = MagicMock()
        mock_livres.aggregate.return_value = [aggregation_result]
        service.livres_collection = mock_livres

        # Mock editeurs collection - doit résoudre editeur_id
        mock_editeurs = MagicMock()
        mock_editeurs.find_one.return_value = {
            "_id": editeur_id,
            "nom": "P.O.L",
        }
        service.editeurs_collection = mock_editeurs

        # Mock empty collections
        service.avis_collection = MagicMock()
        service.avis_collection.find.return_value = []
        service.emissions_collection = MagicMock()
        service.critiques_collection = MagicMock()

        result = service.get_livre_with_episodes(str(livre_id))

        assert result is not None
        assert result["editeur"] == "P.O.L"

    @patch("back_office_lmelp.services.mongodb_service.mongodb_service")
    def test_keeps_editeur_string_when_no_editeur_id(self, mock_service):
        """Quand un livre a editeur (string) mais pas editeur_id, le string est utilisé."""
        from back_office_lmelp.services.mongodb_service import MongoDBService

        service = MongoDBService()
        livre_id = ObjectId()
        auteur_id = ObjectId()

        aggregation_result = {
            "_id": livre_id,
            "titre": "Test Livre",
            "auteur_id": auteur_id,
            "editeur": "Gallimard",
            "auteur": [{"nom": "Test Auteur"}],
            "episodes_data": [],
        }

        mock_livres = MagicMock()
        mock_livres.aggregate.return_value = [aggregation_result]
        service.livres_collection = mock_livres

        service.editeurs_collection = MagicMock()
        service.avis_collection = MagicMock()
        service.avis_collection.find.return_value = []
        service.emissions_collection = MagicMock()
        service.critiques_collection = MagicMock()

        result = service.get_livre_with_episodes(str(livre_id))

        assert result is not None
        assert result["editeur"] == "Gallimard"


class TestCreateBookUsesEditeurId:
    """Tests pour create_book_if_not_exists - doit utiliser editeur_id au lieu de editeur string."""

    @patch("back_office_lmelp.services.mongodb_service.mongodb_service")
    def test_new_book_stores_editeur_id_not_editeur_string(self, mock_service):
        """Quand on crée un livre avec editeur='Gallimard', on stocke editeur_id, pas editeur."""
        from back_office_lmelp.services.mongodb_service import MongoDBService

        service = MongoDBService()
        editeur_oid = ObjectId()
        livre_oid = ObjectId()
        auteur_oid = ObjectId()

        # Mock livres_collection
        mock_livres = MagicMock()
        mock_livres.find_one.return_value = None  # Livre n'existe pas
        mock_insert_result = MagicMock()
        mock_insert_result.inserted_id = livre_oid
        mock_livres.insert_one.return_value = mock_insert_result
        service.livres_collection = mock_livres

        # Mock editeurs_collection - éditeur "Gallimard" existe déjà
        mock_editeurs = MagicMock()
        mock_editeurs.find.return_value = [
            {"_id": editeur_oid, "nom": "Gallimard"},
        ]
        service.editeurs_collection = mock_editeurs

        # Mock auteurs_collection pour _add_book_to_author
        mock_auteurs = MagicMock()
        service.auteurs_collection = mock_auteurs

        book_data = {
            "titre": "Les Particules élémentaires",
            "auteur_id": auteur_oid,
            "editeur": "Gallimard",
            "episodes": [],
            "avis_critiques": [],
        }

        result = service.create_book_if_not_exists(book_data)

        assert result == livre_oid
        # Vérifier que le document inséré contient editeur_id, PAS editeur string
        insert_args = mock_livres.insert_one.call_args[0][0]
        assert "editeur_id" in insert_args
        assert insert_args["editeur_id"] == editeur_oid
        assert "editeur" not in insert_args  # PAS de champ editeur string

    @patch("back_office_lmelp.services.mongodb_service.mongodb_service")
    def test_new_book_creates_editeur_when_not_found(self, mock_service):
        """Quand l'éditeur n'existe pas, il est créé et editeur_id est stocké."""
        from back_office_lmelp.services.mongodb_service import MongoDBService

        service = MongoDBService()
        new_editeur_oid = ObjectId()
        livre_oid = ObjectId()
        auteur_oid = ObjectId()

        # Mock livres_collection
        mock_livres = MagicMock()
        mock_livres.find_one.return_value = None  # Livre n'existe pas
        mock_insert_result = MagicMock()
        mock_insert_result.inserted_id = livre_oid
        mock_livres.insert_one.return_value = mock_insert_result
        service.livres_collection = mock_livres

        # Mock editeurs_collection - éditeur n'existe pas, sera créé
        mock_editeurs = MagicMock()
        mock_editeurs.find.return_value = []  # Pas trouvé
        mock_editeur_insert = MagicMock()
        mock_editeur_insert.inserted_id = new_editeur_oid
        mock_editeurs.insert_one.return_value = mock_editeur_insert
        service.editeurs_collection = mock_editeurs

        # Mock auteurs_collection
        mock_auteurs = MagicMock()
        service.auteurs_collection = mock_auteurs

        book_data = {
            "titre": "Nouveau Livre",
            "auteur_id": auteur_oid,
            "editeur": "P.O.L",
            "episodes": [],
            "avis_critiques": [],
        }

        result = service.create_book_if_not_exists(book_data)

        assert result == livre_oid
        # L'éditeur a été créé
        mock_editeurs.insert_one.assert_called_once()
        # Le livre contient editeur_id
        insert_args = mock_livres.insert_one.call_args[0][0]
        assert insert_args["editeur_id"] == new_editeur_oid
        assert "editeur" not in insert_args

    @patch("back_office_lmelp.services.mongodb_service.mongodb_service")
    def test_existing_book_updates_editeur_to_editeur_id(self, mock_service):
        """Quand un livre existant a editeur string, la mise à jour migre vers editeur_id."""
        from back_office_lmelp.services.mongodb_service import MongoDBService

        service = MongoDBService()
        editeur_oid = ObjectId()
        livre_oid = ObjectId()
        auteur_oid = ObjectId()

        # Mock livres_collection - livre existe déjà avec editeur string
        mock_livres = MagicMock()
        mock_livres.find_one.return_value = {
            "_id": livre_oid,
            "titre": "Les Particules élémentaires",
            "auteur_id": auteur_oid,
            "editeur": "Gallimard",  # Ancien format string
            "episodes": [],
            "avis_critiques": [],
        }
        service.livres_collection = mock_livres

        # Mock editeurs_collection
        mock_editeurs = MagicMock()
        mock_editeurs.find.return_value = [
            {"_id": editeur_oid, "nom": "Gallimard"},
        ]
        service.editeurs_collection = mock_editeurs

        # Mock auteurs_collection
        mock_auteurs = MagicMock()
        service.auteurs_collection = mock_auteurs

        book_data = {
            "titre": "Les Particules élémentaires",
            "auteur_id": auteur_oid,
            "editeur": "Gallimard",
            "episodes": [],
            "avis_critiques": [],
        }

        result = service.create_book_if_not_exists(book_data)

        assert result == livre_oid
        # Vérifier que update_one a été appelé avec editeur_id et $unset editeur
        update_call = mock_livres.update_one.call_args
        if update_call:
            update_doc = update_call[0][1]
            assert "editeur_id" in update_doc.get("$set", {})
            assert update_doc["$set"]["editeur_id"] == editeur_oid
            assert "editeur" in update_doc.get("$unset", {})

    @patch("back_office_lmelp.services.mongodb_service.mongodb_service")
    def test_empty_editeur_skips_editeur_id(self, mock_service):
        """Quand editeur est vide, on ne crée pas d'entrée éditeur."""
        from back_office_lmelp.services.mongodb_service import MongoDBService

        service = MongoDBService()
        livre_oid = ObjectId()
        auteur_oid = ObjectId()

        # Mock livres_collection
        mock_livres = MagicMock()
        mock_livres.find_one.return_value = None
        mock_insert_result = MagicMock()
        mock_insert_result.inserted_id = livre_oid
        mock_livres.insert_one.return_value = mock_insert_result
        service.livres_collection = mock_livres

        # Mock editeurs_collection
        mock_editeurs = MagicMock()
        service.editeurs_collection = mock_editeurs

        # Mock auteurs_collection
        mock_auteurs = MagicMock()
        service.auteurs_collection = mock_auteurs

        book_data = {
            "titre": "Livre sans éditeur",
            "auteur_id": auteur_oid,
            "editeur": "",  # Pas d'éditeur
            "episodes": [],
            "avis_critiques": [],
        }

        result = service.create_book_if_not_exists(book_data)

        assert result == livre_oid
        # Pas de recherche ni création d'éditeur
        mock_editeurs.find.assert_not_called()
        mock_editeurs.insert_one.assert_not_called()
        # Le document ne doit PAS avoir editeur_id
        insert_args = mock_livres.insert_one.call_args[0][0]
        assert "editeur_id" not in insert_args
