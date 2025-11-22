"""Tests pour le refactoring de la logique de sauvegarde MongoDB."""

from unittest.mock import Mock

from bson import ObjectId

from src.back_office_lmelp.services.mongodb_service import MongoDBService


class TestMongoDBServiceRefactoring:
    """Tests pour la nouvelle logique de sauvegarde des corrections."""

    def setup_method(self):
        """Setup pour chaque test."""
        self.service = MongoDBService()
        self.mock_collection = Mock()
        self.service.episodes_collection = self.mock_collection
        self.test_episode_id = ObjectId("507f1f77bcf86cd799439011")

    def test_update_episode_title_new_logic(self):
        """Test que la nouvelle logique de mise à jour de titre fonctionne."""
        # Mock de l'épisode existant dans la base
        existing_episode = {
            "_id": self.test_episode_id,
            "titre": "Titre original",
            "description": "Description originale",
        }

        # Mock des appels MongoDB
        self.mock_collection.find_one.return_value = existing_episode
        self.mock_collection.update_one.return_value = Mock(modified_count=1)

        # Appel de la nouvelle méthode
        result = self.service.update_episode_title_new(
            str(self.test_episode_id), "Titre corrigé"
        )

        # Vérifications
        assert result is True

        # Vérifier que find_one a été appelé pour récupérer l'épisode existant
        self.mock_collection.find_one.assert_called_once()

        # Vérifier que update_one a été appelé avec la bonne logique
        update_call = self.mock_collection.update_one.call_args
        assert update_call[0][0] == {"_id": self.test_episode_id}

        update_data = update_call[0][1]["$set"]
        assert update_data["titre"] == "Titre corrigé"
        assert update_data["titre_origin"] == "Titre original"

    def test_update_episode_description_new_logic(self):
        """Test que la nouvelle logique de mise à jour de description fonctionne."""
        # Mock de l'épisode existant dans la base
        existing_episode = {
            "_id": self.test_episode_id,
            "titre": "Titre original",
            "description": "Description originale",
        }

        # Mock des appels MongoDB
        self.mock_collection.find_one.return_value = existing_episode
        self.mock_collection.update_one.return_value = Mock(modified_count=1)

        # Appel de la nouvelle méthode
        result = self.service.update_episode_description_new(
            str(self.test_episode_id), "Description corrigée"
        )

        # Vérifications
        assert result is True

        # Vérifier que find_one a été appelé pour récupérer l'épisode existant
        self.mock_collection.find_one.assert_called_once()

        # Vérifier que update_one a été appelé avec la bonne logique
        update_call = self.mock_collection.update_one.call_args
        assert update_call[0][0] == {"_id": self.test_episode_id}

        update_data = update_call[0][1]["$set"]
        assert update_data["description"] == "Description corrigée"
        assert update_data["description_origin"] == "Description originale"

    def test_update_episode_title_already_has_origin(self):
        """Test quand l'épisode a déjà un titre_origin (ne pas l'écraser)."""
        # Mock de l'épisode existant avec déjà un titre_origin
        existing_episode = {
            "_id": self.test_episode_id,
            "titre": "Titre déjà corrigé",
            "titre_origin": "Titre original préservé",
            "description": "Description",
        }

        # Mock des appels MongoDB
        self.mock_collection.find_one.return_value = existing_episode
        self.mock_collection.update_one.return_value = Mock(modified_count=1)

        # Appel de la nouvelle méthode
        result = self.service.update_episode_title_new(
            str(self.test_episode_id), "Nouveau titre corrigé"
        )

        # Vérifications
        assert result is True

        # Vérifier que update_one a été appelé
        update_call = self.mock_collection.update_one.call_args
        update_data = update_call[0][1]["$set"]

        # Le titre doit être mis à jour
        assert update_data["titre"] == "Nouveau titre corrigé"
        # Mais titre_origin ne doit PAS être écrasé
        assert "titre_origin" not in update_data

    def test_update_episode_description_already_has_origin(self):
        """Test quand l'épisode a déjà un description_origin (ne pas l'écraser)."""
        # Mock de l'épisode existant avec déjà un description_origin
        existing_episode = {
            "_id": self.test_episode_id,
            "titre": "Titre",
            "description": "Description déjà corrigée",
            "description_origin": "Description originale préservée",
        }

        # Mock des appels MongoDB
        self.mock_collection.find_one.return_value = existing_episode
        self.mock_collection.update_one.return_value = Mock(modified_count=1)

        # Appel de la nouvelle méthode
        result = self.service.update_episode_description_new(
            str(self.test_episode_id), "Nouvelle description corrigée"
        )

        # Vérifications
        assert result is True

        # Vérifier que update_one a été appelé
        update_call = self.mock_collection.update_one.call_args
        update_data = update_call[0][1]["$set"]

        # La description doit être mise à jour
        assert update_data["description"] == "Nouvelle description corrigée"
        # Mais description_origin ne doit PAS être écrasé
        assert "description_origin" not in update_data

    def test_update_episode_not_found(self):
        """Test quand l'épisode n'existe pas."""
        # Mock d'un épisode non trouvé
        self.mock_collection.find_one.return_value = None

        # Appel de la nouvelle méthode
        result = self.service.update_episode_title_new(
            str(self.test_episode_id), "Titre corrigé"
        )

        # Vérifications
        assert result is False

        # update_one ne doit pas être appelé
        self.mock_collection.update_one.assert_not_called()

    def test_statistics_with_new_logic(self):
        """Test que les statistiques utilisent la nouvelle logique."""
        # Mock des données pour les statistiques
        self.mock_collection.count_documents.side_effect = [
            100,  # total_episodes (visible)
            5,  # masked_episodes_count
            15,  # episodes avec titre_origin (donc corrigés)
            25,  # episodes avec description_origin (donc corrigées)
        ]

        # Mock pour avis critiques
        self.service.avis_critiques_collection = Mock()
        self.service.avis_critiques_collection.count_documents.return_value = 50

        # Mock pour aggregate (dernière date de mise à jour)
        self.mock_collection.aggregate.return_value = [{"date": "2025-09-15"}]

        # Mock pour find (récupération des épisodes masqués)
        self.mock_collection.find.return_value = []

        # Appel de la méthode
        result = self.service.get_statistics()

        # Vérifications
        assert result["total_episodes"] == 100
        assert result["masked_episodes_count"] == 5
        assert result["episodes_with_corrected_titles"] == 15
        assert result["episodes_with_corrected_descriptions"] == 25

        # Vérifier que les bonnes requêtes ont été appelées
        expected_calls = [
            {"masked": {"$ne": True}},  # total episodes (visible)
            {"masked": True},  # masked episodes
            {"titre_origin": {"$ne": None, "$exists": True}},  # titres corrigés
            {
                "description_origin": {"$ne": None, "$exists": True}
            },  # descriptions corrigées
        ]

        actual_calls = [
            call[0][0] for call in self.mock_collection.count_documents.call_args_list
        ]
        assert actual_calls == expected_calls
