"""Tests TDD (Issue #267): create_book_if_not_exists doit dédupliquer les
livres par titre normalisé (insensible casse/accents/apostrophes), pas par
égalité stricte.

Bug: lors d'une ré-extraction, Babelio peut renvoyer un titre à la casse
légèrement différente (ex: "L'affaire Alaska Sanders" vs "L'Affaire Alaska
Sanders"). Avec une comparaison stricte, find_one ne reconnaît pas le livre
existant et un doublon est créé (avec sa propre url_babelio, elle-même en
casse différente, ce qui empêche aussi la détection ultérieure des doublons).
"""

from unittest.mock import MagicMock

import pytest
from bson import ObjectId

from back_office_lmelp.services.mongodb_service import MongoDBService


class TestCreateBookCaseInsensitiveDedup:
    """Tests pour la déduplication insensible à la casse dans create_book_if_not_exists."""

    @pytest.fixture
    def mongodb_service(self):
        """Create a MongoDBService with mocked collections."""
        service = MongoDBService()
        service.livres_collection = MagicMock()
        service.auteurs_collection = MagicMock()
        mock_editeurs = MagicMock()
        mock_editeurs.find.return_value = []
        service.editeurs_collection = mock_editeurs
        return service

    def test_should_find_existing_book_when_title_differs_only_by_case(
        self, mongodb_service
    ):
        """
        TDD RED: Un livre existant "L'affaire Alaska Sanders" doit être retrouvé
        même si book_data contient "L'Affaire Alaska Sanders" (casse différente).

        Actuellement find_one fait une comparaison stricte -> ne trouve rien ->
        un nouveau livre est créé (insert_one appelé), ce qui est le bug.
        """
        existing_livre_id = ObjectId()
        existing_author_id = ObjectId()

        existing_book = {
            "_id": existing_livre_id,
            "titre": "L'affaire Alaska Sanders",
            "auteur_id": existing_author_id,
            "episodes": ["678ccedda414f22988778163"],  # pragma: allowlist secret
        }

        # Le find_one strict ne matche pas (casse différente) -> None
        # mais notre nouvelle implémentation doit quand même retrouver le livre
        # via une recherche/comparaison normalisée.
        mongodb_service.livres_collection.find_one.return_value = None
        mongodb_service.livres_collection.find.return_value = [existing_book]
        mongodb_service.livres_collection.update_one.return_value = MagicMock(
            modified_count=1
        )

        book_data = {
            "titre": "L'Affaire Alaska Sanders",  # casse différente
            "auteur_id": existing_author_id,
            "episodes": ["678ccedda414f22988778163"],  # pragma: allowlist secret
            "avis_critiques": [],
        }

        book_id = mongodb_service.create_book_if_not_exists(book_data)

        assert book_id == existing_livre_id, (
            "Le livre existant devrait être retrouvé malgré la casse différente "
            "du titre, au lieu de créer un doublon."
        )
        mongodb_service.livres_collection.insert_one.assert_not_called()
