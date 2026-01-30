"""Tests pour les méthodes CRUD de la collection avis dans MongoDBService."""

from unittest.mock import MagicMock, patch

from bson import ObjectId


class TestMongoDBServiceAvisCRUD:
    """Tests pour les méthodes CRUD avis."""

    def setup_method(self):
        """Setup pour chaque test."""
        # Créer un mock de la collection avis
        self.mock_avis_collection = MagicMock()

        # Patcher le service MongoDB
        self.patcher = patch(
            "back_office_lmelp.services.mongodb_service.mongodb_service"
        )
        self.mock_service = self.patcher.start()
        self.mock_service.avis_collection = self.mock_avis_collection

    def teardown_method(self):
        """Teardown après chaque test."""
        self.patcher.stop()

    # ==========================================================================
    # Tests pour get_avis_by_emission
    # ==========================================================================

    def test_get_avis_by_emission_returns_avis(self):
        """Test récupération des avis par émission."""
        from back_office_lmelp.services.mongodb_service import MongoDBService

        service = MongoDBService()
        service.avis_collection = self.mock_avis_collection

        emission_oid = "emission_123"
        expected_avis = [
            {
                "_id": ObjectId(),
                "emission_oid": emission_oid,
                "livre_titre_extrait": "Mon livre",
                "note": 8,
            },
            {
                "_id": ObjectId(),
                "emission_oid": emission_oid,
                "livre_titre_extrait": "Autre livre",
                "note": 9,
            },
        ]
        self.mock_avis_collection.find.return_value = expected_avis

        result = service.get_avis_by_emission(emission_oid)

        assert len(result) == 2
        self.mock_avis_collection.find.assert_called_once_with(
            {"emission_oid": emission_oid}
        )

    def test_get_avis_by_emission_returns_empty_when_no_collection(self):
        """Test retourne liste vide si collection non initialisée."""
        from back_office_lmelp.services.mongodb_service import MongoDBService

        service = MongoDBService()
        service.avis_collection = None

        result = service.get_avis_by_emission("emission_123")

        assert result == []

    # ==========================================================================
    # Tests pour get_avis_by_critique
    # ==========================================================================

    def test_get_avis_by_critique_returns_avis(self):
        """Test récupération des avis par critique."""
        from back_office_lmelp.services.mongodb_service import MongoDBService

        service = MongoDBService()
        service.avis_collection = self.mock_avis_collection

        critique_oid = "critique_456"
        expected_avis = [
            {
                "_id": ObjectId(),
                "critique_oid": critique_oid,
                "note": 7,
            }
        ]
        self.mock_avis_collection.find.return_value = expected_avis

        result = service.get_avis_by_critique(critique_oid)

        assert len(result) == 1
        self.mock_avis_collection.find.assert_called_once_with(
            {"critique_oid": critique_oid}
        )

    # ==========================================================================
    # Tests pour get_avis_by_livre
    # ==========================================================================

    def test_get_avis_by_livre_returns_avis(self):
        """Test récupération des avis par livre."""
        from back_office_lmelp.services.mongodb_service import MongoDBService

        service = MongoDBService()
        service.avis_collection = self.mock_avis_collection

        livre_oid = "livre_789"
        expected_avis = [
            {
                "_id": ObjectId(),
                "livre_oid": livre_oid,
                "note": 10,
            }
        ]
        self.mock_avis_collection.find.return_value = expected_avis

        result = service.get_avis_by_livre(livre_oid)

        assert len(result) == 1
        self.mock_avis_collection.find.assert_called_once_with({"livre_oid": livre_oid})

    # ==========================================================================
    # Tests pour get_avis_by_id
    # ==========================================================================

    def test_get_avis_by_id_returns_avis(self):
        """Test récupération d'un avis par ID."""
        from back_office_lmelp.services.mongodb_service import MongoDBService

        service = MongoDBService()
        service.avis_collection = self.mock_avis_collection

        avis_id = str(ObjectId())
        expected_avis = {
            "_id": ObjectId(avis_id),
            "note": 8,
        }
        self.mock_avis_collection.find_one.return_value = expected_avis

        result = service.get_avis_by_id(avis_id)

        assert result is not None
        assert result["note"] == 8

    def test_get_avis_by_id_returns_none_when_not_found(self):
        """Test retourne None si avis non trouvé."""
        from back_office_lmelp.services.mongodb_service import MongoDBService

        service = MongoDBService()
        service.avis_collection = self.mock_avis_collection
        self.mock_avis_collection.find_one.return_value = None

        result = service.get_avis_by_id(str(ObjectId()))

        assert result is None

    def test_get_avis_by_id_returns_none_on_invalid_id(self):
        """Test retourne None si ID invalide."""
        from back_office_lmelp.services.mongodb_service import MongoDBService

        service = MongoDBService()
        service.avis_collection = self.mock_avis_collection

        result = service.get_avis_by_id("invalid_id")

        assert result is None

    # ==========================================================================
    # Tests pour save_avis_batch
    # ==========================================================================

    def test_save_avis_batch_inserts_avis(self):
        """Test sauvegarde batch d'avis."""
        from back_office_lmelp.services.mongodb_service import MongoDBService

        service = MongoDBService()
        service.avis_collection = self.mock_avis_collection

        avis_list = [
            {"emission_oid": "em1", "note": 8},
            {"emission_oid": "em1", "note": 9},
        ]

        mock_result = MagicMock()
        mock_result.inserted_ids = [ObjectId(), ObjectId()]
        self.mock_avis_collection.insert_many.return_value = mock_result

        result = service.save_avis_batch(avis_list)

        assert len(result) == 2
        self.mock_avis_collection.insert_many.assert_called_once()
        # Vérifier que les timestamps ont été ajoutés
        call_args = self.mock_avis_collection.insert_many.call_args[0][0]
        assert "created_at" in call_args[0]
        assert "updated_at" in call_args[0]

    def test_save_avis_batch_returns_empty_on_empty_list(self):
        """Test retourne liste vide si liste d'avis vide."""
        from back_office_lmelp.services.mongodb_service import MongoDBService

        service = MongoDBService()
        service.avis_collection = self.mock_avis_collection

        result = service.save_avis_batch([])

        assert result == []
        self.mock_avis_collection.insert_many.assert_not_called()

    def test_save_avis_batch_returns_empty_when_no_collection(self):
        """Test retourne liste vide si collection non initialisée."""
        from back_office_lmelp.services.mongodb_service import MongoDBService

        service = MongoDBService()
        service.avis_collection = None

        result = service.save_avis_batch([{"note": 8}])

        assert result == []

    # ==========================================================================
    # Tests pour delete_avis_by_emission
    # ==========================================================================

    def test_delete_avis_by_emission_deletes_all(self):
        """Test suppression de tous les avis d'une émission."""
        from back_office_lmelp.services.mongodb_service import MongoDBService

        service = MongoDBService()
        service.avis_collection = self.mock_avis_collection

        mock_result = MagicMock()
        mock_result.deleted_count = 5
        self.mock_avis_collection.delete_many.return_value = mock_result

        result = service.delete_avis_by_emission("emission_123")

        assert result == 5
        self.mock_avis_collection.delete_many.assert_called_once_with(
            {"emission_oid": "emission_123"}
        )

    def test_delete_avis_by_emission_returns_zero_when_no_collection(self):
        """Test retourne 0 si collection non initialisée."""
        from back_office_lmelp.services.mongodb_service import MongoDBService

        service = MongoDBService()
        service.avis_collection = None

        result = service.delete_avis_by_emission("emission_123")

        assert result == 0

    # ==========================================================================
    # Tests pour update_avis
    # ==========================================================================

    def test_update_avis_updates_fields(self):
        """Test mise à jour d'un avis."""
        from back_office_lmelp.services.mongodb_service import MongoDBService

        service = MongoDBService()
        service.avis_collection = self.mock_avis_collection

        avis_id = str(ObjectId())
        mock_result = MagicMock()
        mock_result.matched_count = 1
        self.mock_avis_collection.update_one.return_value = mock_result

        result = service.update_avis(avis_id, {"livre_oid": "livre_new"})

        assert result is True
        self.mock_avis_collection.update_one.assert_called_once()
        # Vérifier que updated_at a été ajouté
        call_args = self.mock_avis_collection.update_one.call_args[0]
        assert "updated_at" in call_args[1]["$set"]

    def test_update_avis_returns_false_when_not_found(self):
        """Test retourne False si avis non trouvé."""
        from back_office_lmelp.services.mongodb_service import MongoDBService

        service = MongoDBService()
        service.avis_collection = self.mock_avis_collection

        mock_result = MagicMock()
        mock_result.matched_count = 0
        self.mock_avis_collection.update_one.return_value = mock_result

        result = service.update_avis(str(ObjectId()), {"note": 10})

        assert result is False

    def test_update_avis_returns_false_on_invalid_id(self):
        """Test retourne False si ID invalide."""
        from back_office_lmelp.services.mongodb_service import MongoDBService

        service = MongoDBService()
        service.avis_collection = self.mock_avis_collection

        result = service.update_avis("invalid_id", {"note": 10})

        assert result is False

    # ==========================================================================
    # Tests pour delete_avis
    # ==========================================================================

    def test_delete_avis_deletes_single(self):
        """Test suppression d'un avis."""
        from back_office_lmelp.services.mongodb_service import MongoDBService

        service = MongoDBService()
        service.avis_collection = self.mock_avis_collection

        avis_id = str(ObjectId())
        mock_result = MagicMock()
        mock_result.deleted_count = 1
        self.mock_avis_collection.delete_one.return_value = mock_result

        result = service.delete_avis(avis_id)

        assert result is True

    def test_delete_avis_returns_false_when_not_found(self):
        """Test retourne False si avis non trouvé."""
        from back_office_lmelp.services.mongodb_service import MongoDBService

        service = MongoDBService()
        service.avis_collection = self.mock_avis_collection

        mock_result = MagicMock()
        mock_result.deleted_count = 0
        self.mock_avis_collection.delete_one.return_value = mock_result

        result = service.delete_avis(str(ObjectId()))

        assert result is False

    # ==========================================================================
    # Tests pour get_avis_stats
    # ==========================================================================

    def test_get_avis_stats_returns_statistics(self):
        """Test récupération des statistiques."""
        from back_office_lmelp.services.mongodb_service import MongoDBService

        service = MongoDBService()
        service.avis_collection = self.mock_avis_collection

        self.mock_avis_collection.count_documents.side_effect = [
            100,  # total
            5,  # unresolved_livre
            3,  # unresolved_critique
            2,  # missing_note
        ]
        self.mock_avis_collection.distinct.return_value = ["em1", "em2", "em3"]

        result = service.get_avis_stats()

        assert result["total"] == 100
        assert result["unresolved_livre"] == 5
        assert result["unresolved_critique"] == 3
        assert result["missing_note"] == 2
        assert result["emissions_with_avis"] == 3

    def test_get_avis_stats_returns_zeros_when_no_collection(self):
        """Test retourne zéros si collection non initialisée."""
        from back_office_lmelp.services.mongodb_service import MongoDBService

        service = MongoDBService()
        service.avis_collection = None

        result = service.get_avis_stats()

        assert result["total"] == 0
        assert result["unresolved_livre"] == 0
        assert result["unresolved_critique"] == 0
        assert result["missing_note"] == 0
        assert result["emissions_with_avis"] == 0

    # ==========================================================================
    # Tests pour count_avis_by_emission
    # ==========================================================================

    def test_count_avis_by_emission_returns_count(self):
        """Test comptage des avis par émission."""
        from back_office_lmelp.services.mongodb_service import MongoDBService

        service = MongoDBService()
        service.avis_collection = self.mock_avis_collection

        self.mock_avis_collection.count_documents.return_value = 8

        result = service.count_avis_by_emission("emission_123")

        assert result == 8
        self.mock_avis_collection.count_documents.assert_called_once_with(
            {"emission_oid": "emission_123"}
        )

    def test_count_avis_by_emission_returns_zero_when_no_collection(self):
        """Test retourne 0 si collection non initialisée."""
        from back_office_lmelp.services.mongodb_service import MongoDBService

        service = MongoDBService()
        service.avis_collection = None

        result = service.count_avis_by_emission("emission_123")

        assert result == 0
