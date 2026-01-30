"""Tests pour le calcul du badge_status des émissions."""

from unittest.mock import MagicMock, patch

from bson import ObjectId


class TestCalculateEmissionBadgeStatus:
    """Tests pour la fonction _calculate_emission_badge_status."""

    def setup_method(self):
        """Setup pour chaque test."""
        # Patcher mongodb_service avant d'importer app
        self.mock_mongodb = MagicMock()
        self.patcher = patch("back_office_lmelp.app.mongodb_service", self.mock_mongodb)
        self.patcher.start()

        # Importer après le patch
        from back_office_lmelp.app import _calculate_emission_badge_status

        self.calculate_badge = _calculate_emission_badge_status

    def teardown_method(self):
        """Teardown après chaque test."""
        self.patcher.stop()

    def test_count_mismatch_when_counts_differ(self):
        """Test 🔴 count_mismatch quand # livres summary ≠ # livres mongo."""
        emission_id = str(ObjectId())
        episode_id = str(ObjectId())

        # Mock avis collection avec 2 livres uniques dans le summary
        self.mock_mongodb.avis_collection = MagicMock()
        self.mock_mongodb.avis_collection.count_documents.return_value = 3
        self.mock_mongodb.avis_collection.find.return_value = [
            {
                "livre_titre_extrait": "Livre 1",
                "livre_oid": str(ObjectId()),
                "note": 8,
            },
            {
                "livre_titre_extrait": "Livre 2",
                "livre_oid": str(ObjectId()),
                "note": 7,
            },
            {
                "livre_titre_extrait": "Livre 2",  # Même livre, avis différent
                "livre_oid": str(ObjectId()),
                "note": 9,
            },
        ]

        # Mock livres collection avec 3 livres dans mongo
        self.mock_mongodb.livres_collection = MagicMock()
        self.mock_mongodb.livres_collection.count_documents.return_value = 3

        # EXECUTE
        result = self.calculate_badge(emission_id, episode_id, self.mock_mongodb)

        # ASSERT: Devrait être count_mismatch (2 summary vs 3 mongo)
        assert result == "count_mismatch"

    def test_count_mismatch_when_missing_note(self):
        """
        Test 🔴 count_mismatch quand au moins une note est None.

        Nouvelle règle : count_mismatch = écart de comptage OU note manquante
        """
        emission_id = str(ObjectId())
        episode_id = str(ObjectId())

        # Mock avis collection avec 2 livres, comptes égaux MAIS une note manquante
        self.mock_mongodb.avis_collection = MagicMock()
        self.mock_mongodb.avis_collection.count_documents.return_value = 2
        self.mock_mongodb.avis_collection.find.return_value = [
            {
                "livre_titre_extrait": "Livre 1",
                "livre_oid": str(ObjectId()),
                "note": 8,  # Note présente
            },
            {
                "livre_titre_extrait": "Livre 2",
                "livre_oid": str(ObjectId()),
                "note": None,  # ⚠️ Note manquante → devrait être 🔴
            },
        ]

        # Mock livres collection avec 2 livres (comptes égaux)
        self.mock_mongodb.livres_collection = MagicMock()
        self.mock_mongodb.livres_collection.count_documents.return_value = 2

        # EXECUTE
        result = self.calculate_badge(emission_id, episode_id, self.mock_mongodb)

        # ASSERT: Devrait être count_mismatch à cause de la note manquante
        assert result == "count_mismatch"

    def test_unmatched_when_counts_equal_but_livre_oid_null(self):
        """Test 🟡 unmatched quand comptes égaux mais livre non matché."""
        emission_id = str(ObjectId())
        episode_id = str(ObjectId())

        # Mock avis collection avec 2 livres, comptes égaux, un non matché, notes présentes
        self.mock_mongodb.avis_collection = MagicMock()
        self.mock_mongodb.avis_collection.count_documents.return_value = 2
        self.mock_mongodb.avis_collection.find.return_value = [
            {
                "livre_titre_extrait": "Livre 1",
                "livre_oid": str(ObjectId()),
                "note": 8,
            },
            {
                "livre_titre_extrait": "Livre 2",
                "livre_oid": None,  # Non matché
                "note": 7,  # Note présente
            },
        ]

        # Mock livres collection avec 2 livres
        self.mock_mongodb.livres_collection = MagicMock()
        self.mock_mongodb.livres_collection.count_documents.return_value = 2

        # EXECUTE
        result = self.calculate_badge(emission_id, episode_id, self.mock_mongodb)

        # ASSERT: Devrait être unmatched (pas count_mismatch car comptes égaux et notes présentes)
        assert result == "unmatched"

    def test_perfect_when_all_ok(self):
        """Test 🟢 perfect quand comptes égaux, tous matchés, toutes notes présentes."""
        emission_id = str(ObjectId())
        episode_id = str(ObjectId())

        # Mock avis collection avec 2 livres, tous matchés, toutes notes présentes
        self.mock_mongodb.avis_collection = MagicMock()
        self.mock_mongodb.avis_collection.count_documents.return_value = 2
        self.mock_mongodb.avis_collection.find.return_value = [
            {
                "livre_titre_extrait": "Livre 1",
                "livre_oid": str(ObjectId()),
                "note": 8,
            },
            {
                "livre_titre_extrait": "Livre 2",
                "livre_oid": str(ObjectId()),
                "note": 7,
            },
        ]

        # Mock livres collection avec 2 livres
        self.mock_mongodb.livres_collection = MagicMock()
        self.mock_mongodb.livres_collection.count_documents.return_value = 2

        # EXECUTE
        result = self.calculate_badge(emission_id, episode_id, self.mock_mongodb)

        # ASSERT: Devrait être perfect
        assert result == "perfect"

    def test_no_avis_when_no_extraction(self):
        """Test ⚪ no_avis quand avis pas encore extraits."""
        emission_id = str(ObjectId())
        episode_id = str(ObjectId())

        # Mock avis collection vide
        self.mock_mongodb.avis_collection = MagicMock()
        self.mock_mongodb.avis_collection.count_documents.return_value = 0

        # EXECUTE
        result = self.calculate_badge(emission_id, episode_id, self.mock_mongodb)

        # ASSERT: Devrait être no_avis
        assert result == "no_avis"
