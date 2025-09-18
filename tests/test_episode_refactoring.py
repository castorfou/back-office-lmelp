"""Tests pour le refactoring des corrections de titres et descriptions."""

from src.back_office_lmelp.models.episode import Episode


class TestEpisodeRefactoring:
    """Tests pour la nouvelle logique de gestion des corrections."""

    def test_episode_with_origin_fields(self):
        """Test qu'un épisode peut avoir des champs _origin."""
        data = {
            "_id": "123",
            "titre": "Titre corrigé",
            "titre_origin": "Titre original",
            "description": "Description corrigée",
            "description_origin": "Description originale",
            "date": None,
            "type": "livres",
        }

        episode = Episode(data)

        assert episode.titre == "Titre corrigé"
        assert episode.titre_origin == "Titre original"
        assert episode.description == "Description corrigée"
        assert episode.description_origin == "Description originale"

    def test_episode_to_dict_includes_origin_fields(self):
        """Test que to_dict inclut les champs _origin."""
        data = {
            "_id": "123",
            "titre": "Titre corrigé",
            "titre_origin": "Titre original",
            "description": "Description corrigée",
            "description_origin": "Description originale",
            "date": None,
            "type": "livres",
        }

        episode = Episode(data)
        result = episode.to_dict()

        assert result["titre"] == "Titre corrigé"
        assert result["titre_origin"] == "Titre original"
        assert result["description"] == "Description corrigée"
        assert result["description_origin"] == "Description originale"

    def test_episode_without_origin_fields(self):
        """Test qu'un épisode sans champs _origin fonctionne encore."""
        data = {
            "_id": "123",
            "titre": "Titre",
            "description": "Description",
            "date": None,
            "type": "livres",
        }

        episode = Episode(data)

        assert episode.titre == "Titre"
        assert episode.titre_origin is None
        assert episode.description == "Description"
        assert episode.description_origin is None

    def test_episode_to_summary_dict_uses_corrected_title(self):
        """Test que to_summary_dict utilise le titre corrigé (dans 'titre')."""
        data = {
            "_id": "123",
            "titre": "Titre corrigé",
            "titre_origin": "Titre original",
            "date": None,
            "type": "livres",
        }

        episode = Episode(data)
        result = episode.to_summary_dict()

        # Le titre dans le résumé doit être la version corrigée
        assert result["titre"] == "Titre corrigé"
        # L'ancien champ titre_corrige ne doit plus être utilisé
        assert "titre_corrige" not in result
