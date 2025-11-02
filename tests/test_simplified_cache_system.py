"""Tests TDD pour un système de cache simplifié."""

from unittest.mock import patch

import pytest
from bson import ObjectId

from back_office_lmelp.services.livres_auteurs_cache_service import (
    LivresAuteursCacheService,
)


class TestSimplifiedCacheSystem:
    """Tests TDD pour simplifier le système de cache."""

    def test_cache_entry_should_only_store_essential_fields(self):
        """Test TDD: Les entrées de cache ne doivent contenir que les champs essentiels."""
        avis_critique_id = ObjectId(
            "68c718a16e51b9428ab88066"  # pragma: allowlist secret
        )
        book_data = {
            "episode_oid": "68c707ad6e51b9428ab87e9e",  # pragma: allowlist secret
            "auteur": "Laurent Mauvignier",
            "titre": "La Maison Vide",
            "editeur": "Éditions de Minuit",
            "programme": True,
            "status": "verified",  # UN SEUL statut simplifié
        }

        with patch(
            "back_office_lmelp.services.livres_auteurs_cache_service.mongodb_service"
        ) as mock_mongodb:
            # Mock: aucune entrée existante
            mock_mongodb.get_collection.return_value.find_one.return_value = None
            mock_mongodb.get_collection.return_value.replace_one.return_value.upserted_id = ObjectId()

            # Act
            service = LivresAuteursCacheService()
            service.create_cache_entry(avis_critique_id, book_data)

            # Assert - Vérifier que seuls les champs essentiels sont sauvegardés
            replace_call = (
                mock_mongodb.get_collection.return_value.replace_one.call_args
            )
            saved_document = replace_call[0][1]  # Document sauvegardé

            # Champs OBLIGATOIRES
            assert saved_document["avis_critique_id"] == avis_critique_id
            assert (
                saved_document["episode_oid"]
                == "68c707ad6e51b9428ab87e9e"  # pragma: allowlist secret
            )
            assert saved_document["auteur"] == "Laurent Mauvignier"
            assert saved_document["titre"] == "La Maison Vide"
            assert saved_document["editeur"] == "Éditions de Minuit"
            assert saved_document["programme"]
            assert saved_document["status"] == "verified"
            assert "created_at" in saved_document
            assert "updated_at" in saved_document

            # Champs qui NE DOIVENT PAS exister (NoSQL advantage)
            assert "suggested_author" not in saved_document
            assert "suggested_title" not in saved_document
            assert "user_validated_author" not in saved_document
            assert "user_validated_title" not in saved_document
            assert "user_entered_author" not in saved_document
            assert "user_entered_title" not in saved_document
            assert "user_entered_publisher" not in saved_document
            assert "author_id" not in saved_document
            assert "book_id" not in saved_document
            assert "processed_at" not in saved_document

            # PLUS DE DOUBLE STATUT
            assert "biblio_verification_status" not in saved_document
            assert "validation_status" not in saved_document

    def test_cache_entry_should_add_suggestions_only_when_provided(self):
        """Test TDD: Les suggestions Babelio ne sont ajoutées que si fournies."""
        avis_critique_id = ObjectId(
            "68c718a16e51b9428ab88066"  # pragma: allowlist secret
        )
        book_data = {
            "episode_oid": "68c707ad6e51b9428ab87e9e",  # pragma: allowlist secret
            "auteur": "Alain Mabancou",  # Typo volontaire
            "titre": "Ramsès de Paris",
            "editeur": "Seuil",
            "programme": True,
            "status": "suggested",
            "suggested_author": "Alain Mabanckou",  # Suggestion fournie
            "suggested_title": "Rumeurs d'Amérique",  # Suggestion fournie
        }

        with patch(
            "back_office_lmelp.services.livres_auteurs_cache_service.mongodb_service"
        ) as mock_mongodb:
            mock_mongodb.get_collection.return_value.find_one.return_value = None
            mock_mongodb.get_collection.return_value.replace_one.return_value.upserted_id = ObjectId()

            # Act
            service = LivresAuteursCacheService()
            service.create_cache_entry(avis_critique_id, book_data)

            # Assert
            replace_call = (
                mock_mongodb.get_collection.return_value.replace_one.call_args
            )
            saved_document = replace_call[0][1]

            # Champs essentiels
            assert saved_document["status"] == "suggested"

            # Suggestions présentes SEULEMENT car fournies
            assert saved_document["suggested_author"] == "Alain Mabanckou"
            assert saved_document["suggested_title"] == "Rumeurs d'Amérique"

            # Autres champs optionnels n'existent pas
            assert "user_validated_author" not in saved_document
            assert "author_id" not in saved_document

    def test_cache_entry_should_store_babelio_enrichment_when_provided(self):
        """Test TDD (Issue #85): Les champs enrichis par Babelio sont sauvegardés si fournis.

        GIVEN: Un livre extrait avec enrichissement Babelio (confidence >= 0.90)
        WHEN: create_cache_entry() est appelé avec babelio_url et babelio_publisher
        THEN: Ces champs sont persistés dans le cache MongoDB
        """
        avis_critique_id = ObjectId(
            "68c718a16e51b9428ab88066"  # pragma: allowlist secret
        )
        book_data = {
            "episode_oid": "68c707ad6e51b9428ab87e9e",  # pragma: allowlist secret
            "auteur": "Carlos Gimenez",
            "titre": "Paracuellos, Intégrale",
            "editeur": "Fluide Glacial",
            "programme": False,
            "status": "verified",
            # ✅ Enrichissement Babelio (ajouté par extract_books_from_reviews)
            "babelio_url": "https://www.babelio.com/livres/Gimenez-Paracuellos-Integrale/112880",
            "babelio_publisher": "Audie-Fluide glacial",
        }

        with patch(
            "back_office_lmelp.services.livres_auteurs_cache_service.mongodb_service"
        ) as mock_mongodb:
            mock_mongodb.get_collection.return_value.find_one.return_value = None
            mock_mongodb.get_collection.return_value.replace_one.return_value.upserted_id = ObjectId()

            # Act
            service = LivresAuteursCacheService()
            service.create_cache_entry(avis_critique_id, book_data)

            # Assert - Vérifier que les enrichissements Babelio sont sauvegardés
            replace_call = (
                mock_mongodb.get_collection.return_value.replace_one.call_args
            )
            saved_document = replace_call[0][1]

            # Champs essentiels
            assert saved_document["auteur"] == "Carlos Gimenez"
            assert saved_document["titre"] == "Paracuellos, Intégrale"
            assert saved_document["status"] == "verified"

            # ✅ Enrichissements Babelio DOIVENT être présents (Issue #85)
            assert "babelio_url" in saved_document, (
                "babelio_url doit être sauvegardé si fourni"
            )
            assert (
                saved_document["babelio_url"]
                == "https://www.babelio.com/livres/Gimenez-Paracuellos-Integrale/112880"
            )
            assert "babelio_publisher" in saved_document, (
                "babelio_publisher doit être sauvegardé si fourni"
            )
            assert saved_document["babelio_publisher"] == "Audie-Fluide glacial"

    def test_cache_entry_should_not_store_babelio_enrichment_when_not_provided(self):
        """Test TDD (Issue #85): Les champs Babelio NE sont PAS sauvegardés si absents.

        GIVEN: Un livre extrait sans enrichissement Babelio (confidence < 0.90)
        WHEN: create_cache_entry() est appelé sans babelio_url ni babelio_publisher
        THEN: Ces champs ne sont PAS dans le document MongoDB (avantage NoSQL)
        """
        avis_critique_id = ObjectId(
            "68c718a16e51b9428ab88066"
        )  # pragma: allowlist secret
        book_data = {
            "episode_oid": "68c707ad6e51b9428ab87e9e",  # pragma: allowlist secret
            "auteur": "Auteur Inconnu",
            "titre": "Livre Rare",
            "editeur": "Petit Éditeur",
            "programme": False,
            "status": "not_found",
            # ❌ Pas d'enrichissement Babelio (confidence < 0.90)
        }

        with patch(
            "back_office_lmelp.services.livres_auteurs_cache_service.mongodb_service"
        ) as mock_mongodb:
            mock_mongodb.get_collection.return_value.find_one.return_value = None
            mock_mongodb.get_collection.return_value.replace_one.return_value.upserted_id = ObjectId()

            # Act
            service = LivresAuteursCacheService()
            service.create_cache_entry(avis_critique_id, book_data)

            # Assert - Vérifier que babelio_url et babelio_publisher N'existent PAS
            replace_call = (
                mock_mongodb.get_collection.return_value.replace_one.call_args
            )
            saved_document = replace_call[0][1]

            # Champs essentiels présents
            assert saved_document["auteur"] == "Auteur Inconnu"
            assert saved_document["status"] == "not_found"

            # ❌ Enrichissements Babelio ne doivent PAS exister (NoSQL advantage)
            assert "babelio_url" not in saved_document, (
                "babelio_url ne doit pas exister si non fourni"
            )
            assert "babelio_publisher" not in saved_document, (
                "babelio_publisher ne doit pas exister si non fourni"
            )

    def test_cache_entry_should_only_add_processing_fields_when_processed(self):
        """Test TDD: Les champs de traitement ne sont ajoutés qu'après traitement."""
        ObjectId("68c718a16e51b9428ab88066")  # pragma: allowlist secret

        cache_id = ObjectId("68d4c4859265d804e509db57")

        with patch(
            "back_office_lmelp.services.livres_auteurs_cache_service.mongodb_service"
        ) as mock_mongodb:
            # Mock le résultat de update_one
            mock_mongodb.get_collection.return_value.update_one.return_value.modified_count = 1

            # Act - Marquer comme traité
            service = LivresAuteursCacheService()
            author_id = ObjectId("67a79b615b03b52d8c51db29")
            book_id = ObjectId("68d3ed1fad794a968c14f921")

            service.mark_as_processed(cache_id, author_id, book_id)

            # Assert - Seulement les champs de traitement sont ajoutés
            update_call = mock_mongodb.get_collection.return_value.update_one.call_args
            update_fields = update_call[0][1]["$set"]

            assert update_fields["status"] == "mongo"  # Statut unifié
            assert update_fields["author_id"] == author_id
            assert update_fields["book_id"] == book_id
            assert "processed_at" in update_fields

            # Plus de validation_status séparé
            assert "validation_status" not in update_fields

    def test_simplified_status_values_should_be_clear(self):
        """Test TDD: Les valeurs de statut doivent être simples et claires."""
        # Statuts autorisés (SEULEMENT 4)
        allowed_statuses = ["not_found", "suggested", "verified", "mongo"]

        # Statuts INTERDITS (complexité supprimée)

        # Test avec chaque statut autorisé
        for status in allowed_statuses:
            book_data = {
                "episode_oid": "68c707ad6e51b9428ab87e9e",  # pragma: allowlist secret
                "auteur": "Test Author",
                "titre": "Test Title",
                "editeur": "Test Publisher",
                "programme": False,
                "status": status,
            }

            avis_critique_id = ObjectId(
                "68c718a16e51b9428ab88066"  # pragma: allowlist secret
            )

            with patch(
                "back_office_lmelp.services.livres_auteurs_cache_service.mongodb_service"
            ) as mock_mongodb:
                mock_mongodb.get_collection.return_value.find_one.return_value = None
                mock_mongodb.get_collection.return_value.replace_one.return_value.upserted_id = ObjectId()

                # Act
                service = LivresAuteursCacheService()
                service.create_cache_entry(avis_critique_id, book_data)

                # Assert - Statut accepté
                replace_call = (
                    mock_mongodb.get_collection.return_value.replace_one.call_args
                )
                saved_document = replace_call[0][1]
                assert saved_document["status"] == status

    def test_validation_should_reject_old_complex_statuses(self):
        """Test TDD: Le nouveau système doit rejeter les anciens statuts complexes."""
        avis_critique_id = ObjectId(
            "68c718a16e51b9428ab88066"  # pragma: allowlist secret
        )

        # Données avec ancien système (double statut)
        old_book_data = {
            "episode_oid": "68c707ad6e51b9428ab87e9e",  # pragma: allowlist secret
            "auteur": "Test Author",
            "titre": "Test Title",
            "editeur": "Test Publisher",
            "programme": False,
            "biblio_verification_status": "verified",  # Ancien système
            "validation_status": "pending",  # Ancien système
        }

        service = LivresAuteursCacheService()

        # Act & Assert - Doit lever une erreur
        with pytest.raises(ValueError, match="Champ obligatoire manquant: status"):
            service.create_cache_entry(avis_critique_id, old_book_data)
