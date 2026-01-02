"""Test pour vérifier que le champ 'editeur' n'est JAMAIS ajouté à avis_critiques (Issue #174).

Ce test vérifie la correction du bug où update_avis_critique() était appelé avec
un champ "editeur" lors de l'enrichissement Babelio, polluant ainsi la collection
avis_critiques avec un champ qui devrait uniquement exister dans la collection livres.

Root cause: app.py ligne 1379 (avant correction)
Endpoint testé: POST /api/set-validation-results
"""

from unittest.mock import patch

from bson import ObjectId
from fastapi.testclient import TestClient

from back_office_lmelp.app import app


def test_should_not_add_editeur_field_to_avis_critique_when_updating_summary():
    """GIVEN: Un livre avec babelio_publisher enrichi par Babelio
    WHEN: POST /api/set-validation-results met à jour le summary dans avis_critique
    THEN: Le champ "editeur" NE DOIT PAS être ajouté à la collection avis_critiques
    """
    client = TestClient(app)

    avis_critique_id = str(ObjectId())
    episode_oid = "507f1f77bcf86cd799439012"  # pragma: allowlist secret

    original_summary = """## 1. LIVRES DISCUTÉS

| Auteur | Titre | Éditeur |
|--------|-------|---------|
| Gilles Legardinier | Quelqu'un pour qui trembler | |
"""

    # Mock les services
    with (
        patch("back_office_lmelp.app.livres_auteurs_cache_service") as mock_cache,
        patch("back_office_lmelp.app.mongodb_service") as mock_mongodb,
        patch("back_office_lmelp.app.memory_guard") as mock_memory,
    ):
        # Setup mocks
        mock_memory.check_memory_limit.return_value = None
        mock_cache.create_cache_entry.return_value = ObjectId()

        mock_mongodb.create_author_if_not_exists.return_value = ObjectId()
        mock_mongodb.create_book_if_not_exists.return_value = ObjectId()
        mock_mongodb.get_avis_critique_by_id.return_value = {
            "_id": ObjectId(avis_critique_id),
            "summary": original_summary,
        }

        # Capturer les appels à update_avis_critique
        updated_data = {}

        def mock_update(avis_id, update_dict):
            updated_data.update(update_dict)
            return True

        mock_mongodb.update_avis_critique.side_effect = mock_update

        # Arrange: Créer une requête avec un livre enrichi par Babelio
        request_data = {
            "avis_critique_id": avis_critique_id,
            "episode_oid": episode_oid,
            "books": [
                {
                    "auteur": "Gilles Legardinier",
                    "titre": "Quelqu'un pour qui trembler",
                    "editeur": "",  # Éditeur vide (transcription Whisper)
                    "programme": True,
                    "validation_status": "verified",
                    "babelio_publisher": "Flammarion",  # ✅ Enrichi par Babelio
                }
            ],
        }

        # Act: Appeler l'endpoint
        response = client.post("/api/set-validation-results", json=request_data)

        # Assert: L'endpoint doit réussir
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Assert CRITIQUE: Vérifier que update_avis_critique() a été appelé
        assert mock_mongodb.update_avis_critique.called, (
            "update_avis_critique() doit être appelé pour mettre à jour le summary"
        )

        # ✅ Le summary DOIT être mis à jour (markdown corrigé)
        assert "summary" in updated_data, "Le summary doit être mis à jour"

        # 🔴 CRITIQUE: Le champ "editeur" NE DOIT PAS être présent (Issue #174)
        assert "editeur" not in updated_data, (
            "ERREUR: Le champ 'editeur' ne doit PAS être ajouté à avis_critiques. "
            "L'éditeur appartient à la collection 'livres', pas 'avis_critiques'."
        )


def test_should_not_add_editeur_even_when_original_publisher_differs():
    """GIVEN: Un livre où l'éditeur original diffère de babelio_publisher
    WHEN: POST /api/set-validation-results met à jour le summary (correction auto)
    THEN: Le champ "editeur" NE DOIT PAS être ajouté à avis_critiques
    """
    client = TestClient(app)

    avis_critique_id = str(ObjectId())
    episode_oid = "507f1f77bcf86cd799439012"  # pragma: allowlist secret

    original_summary = """## 1. LIVRES DISCUTÉS

| Auteur | Titre | Éditeur |
|--------|-------|---------|
| Hannah Assouline | Des visages et des mains | Hercher |
"""

    # Mock les services
    with (
        patch("back_office_lmelp.app.livres_auteurs_cache_service") as mock_cache,
        patch("back_office_lmelp.app.mongodb_service") as mock_mongodb,
        patch("back_office_lmelp.app.memory_guard") as mock_memory,
    ):
        mock_memory.check_memory_limit.return_value = None
        mock_cache.create_cache_entry.return_value = ObjectId()

        mock_mongodb.create_author_if_not_exists.return_value = ObjectId()
        mock_mongodb.create_book_if_not_exists.return_value = ObjectId()
        mock_mongodb.get_avis_critique_by_id.return_value = {
            "_id": ObjectId(avis_critique_id),
            "summary": original_summary,
        }

        # Capturer les appels à update_avis_critique
        updated_data = {}

        def mock_update(avis_id, update_dict):
            updated_data.update(update_dict)
            return True

        mock_mongodb.update_avis_critique.side_effect = mock_update

        # Arrange: Livre avec éditeur incorrect qui sera corrigé
        request_data = {
            "avis_critique_id": avis_critique_id,
            "episode_oid": episode_oid,
            "books": [
                {
                    "auteur": "Hannah Assouline",
                    "titre": "Des visages et des mains",
                    "editeur": "Hercher",  # ❌ Faute de transcription
                    "programme": True,
                    "validation_status": "verified",
                    "babelio_publisher": "Herscher",  # ✅ Correction Babelio
                }
            ],
        }

        # Act
        response = client.post("/api/set-validation-results", json=request_data)

        # Assert
        assert response.status_code == 200

        # Le summary doit être mis à jour (Hercher → Herscher dans markdown)
        assert "summary" in updated_data

        # CRITIQUE: "editeur" ne doit PAS être là (même si correction auto)
        assert "editeur" not in updated_data, (
            "ERREUR: Même lors d'une correction automatique, 'editeur' ne doit PAS "
            "être ajouté à avis_critiques. La correction est faite dans le markdown."
        )
