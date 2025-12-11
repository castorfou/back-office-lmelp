"""Tests TDD pour le cas où tous les livres d'un auteur sont absents de Babelio.

Problème identifié:
- Auteur: Patrice Delbourg
- 1 livre lié: "La Cordillère des ondes" (not_found sur Babelio)
- Comportement incorrect: Marque l'auteur comme babelio_not_found=True
- Comportement attendu: Ajouter l'auteur aux cas problématiques (pas not_found)

Raison: Ce n'est pas parce que le livre n'est pas sur Babelio que l'auteur
n'existe pas. L'auteur peut avoir d'autres œuvres sur Babelio.
"""

from unittest.mock import MagicMock, patch

import pytest
from bson import ObjectId


class TestAuthorAllBooksNotFound:
    """Tests pour le traitement d'un auteur dont tous les livres sont absents de Babelio."""

    @pytest.mark.asyncio
    async def test_should_add_to_problematic_cases_not_mark_as_not_found(self):
        """Test TDD: Auteur avec livres not_found → cas problématique, PAS not_found.

        Scénario:
        - Auteur: Patrice Delbourg
        - 1 livre: "La Cordillère des ondes" (babelio_not_found=True)
        - Action: Traiter l'auteur
        - Attendu:
          * Auteur ajouté aux cas problématiques
          * Auteur NOT marqué babelio_not_found=True
          * Raison: "Tous les livres sont absents de Babelio"
        """
        # Arrange
        from scripts.migration_donnees.migrate_url_babelio import process_one_author

        auteur_id = ObjectId("68ec0533c9f430a13dcefe75")
        livre_id = ObjectId("6914a45f497dd3ad92041855")

        with patch(
            "scripts.migration_donnees.migrate_url_babelio.mongodb_service"
        ) as mock_mongodb:
            # Mock collections
            mock_auteurs = MagicMock()
            mock_livres = MagicMock()
            mock_problematic = MagicMock()

            collections = {
                "auteurs": mock_auteurs,
                "livres": mock_livres,
                "babelio_problematic_cases": mock_problematic,
            }

            def get_collection(name):
                return collections.get(name, MagicMock())

            mock_mongodb.get_collection.side_effect = get_collection

            # Mock auteur
            mock_auteurs.find_one.return_value = {
                "_id": auteur_id,
                "nom": "Patrice Delbourg",
            }

            # Mock livre: NOT_FOUND sur Babelio
            mock_livres.find.return_value = [
                {
                    "_id": livre_id,
                    "titre": "La Cordillère des ondes",
                    "babelio_not_found": True,  # Livre absent de Babelio
                }
            ]

            # Mock update results
            mock_auteurs.update_one.return_value = MagicMock(matched_count=0)
            mock_problematic.insert_one.return_value = MagicMock()

            # Act
            result = await process_one_author(
                author_data={
                    "auteur_id": auteur_id,
                    "nom": "Patrice Delbourg",
                    "livres": [
                        {
                            "livre_id": livre_id,
                            "titre": "La Cordillère des ondes",
                            "babelio_not_found": True,  # Important: passer ce champ
                        }
                    ],
                }
            )

            # Assert
            assert result["status"] == "error", (
                "Doit retourner status=error (cas problématique)"
            )
            assert result["auteur_updated"] is False, (
                "Auteur ne doit PAS être mis à jour"
            )

            # Vérifier qu'on N'a PAS marqué l'auteur comme not_found
            mock_auteurs.update_one.assert_not_called()

            # Vérifier qu'on A ajouté aux cas problématiques
            mock_problematic.insert_one.assert_called_once()

            call_args = mock_problematic.insert_one.call_args[0][0]
            assert call_args["auteur_id"] == str(auteur_id)
            assert call_args["nom_auteur"] == "Patrice Delbourg"
            assert "livres sont absents de Babelio" in call_args["raison"]

    @pytest.mark.asyncio
    async def test_should_not_search_babelio_when_all_books_not_found(self):
        """Test TDD: Ne pas chercher sur Babelio si tous les livres sont not_found.

        Optimisation: Inutile de chercher l'auteur sur Babelio si on sait déjà
        qu'aucun de ses livres n'y est.
        """
        # Arrange
        from scripts.migration_donnees.migrate_url_babelio import process_one_author

        auteur_id = ObjectId()
        livre_id = ObjectId()

        with (
            patch(
                "scripts.migration_donnees.migrate_url_babelio.mongodb_service"
            ) as mock_mongodb,
            patch(
                "scripts.migration_donnees.migrate_url_babelio.BabelioService"
            ) as mock_babelio_service_class,
        ):
            mock_babelio_instance = MagicMock()
            mock_babelio_service_class.return_value = mock_babelio_instance

            # Mock collections
            mock_auteurs = MagicMock()
            mock_livres = MagicMock()
            mock_problematic = MagicMock()

            collections = {
                "auteurs": mock_auteurs,
                "livres": mock_livres,
                "babelio_problematic_cases": mock_problematic,
            }

            def get_collection(name):
                return collections.get(name, MagicMock())

            mock_mongodb.get_collection.side_effect = get_collection

            mock_auteurs.find_one.return_value = {
                "_id": auteur_id,
                "nom": "Test Auteur",
            }

            # Tous les livres sont not_found
            mock_livres.find.return_value = [
                {"_id": livre_id, "titre": "Livre Test", "babelio_not_found": True}
            ]

            mock_auteurs.update_one.return_value = MagicMock(matched_count=0)
            mock_problematic.insert_one.return_value = MagicMock()

            # Act
            result = await process_one_author(
                author_data={
                    "auteur_id": auteur_id,
                    "nom": "Test Auteur",
                    "livres": [
                        {
                            "livre_id": livre_id,
                            "titre": "Livre Test",
                            "babelio_not_found": True,  # Tous les livres sont not_found
                        }
                    ],
                }
            )

            # Assert - Ne doit PAS chercher sur Babelio
            mock_babelio_instance.search_author_by_name.assert_not_called()
            assert result["status"] == "error"
            assert result["auteur_updated"] is False
