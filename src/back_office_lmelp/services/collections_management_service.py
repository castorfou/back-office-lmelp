"""Service de gestion automatique des collections auteurs/livres (Issue #66)."""

from typing import Any

from bson import ObjectId

from .mongodb_service import mongodb_service


class CollectionsManagementService:
    """Service pour gérer automatiquement les collections auteurs et livres."""

    def __init__(self):
        """Initialise le service de gestion des collections."""
        self.mongodb_service = mongodb_service

    def get_statistics(self) -> dict[str, int]:
        """
        Récupère les statistiques pour la page livres-auteurs.

        Returns:
            Dictionnaire contenant les statistiques des collections
        """
        try:
            # Récupérer les livres verified pas en base
            verified_books_not_in_collections = (
                self.mongodb_service.get_verified_books_not_in_collections()
            )

            # Convertir en nombre si c'est une liste
            if isinstance(verified_books_not_in_collections, list):
                verified_count = len(verified_books_not_in_collections)
            else:
                verified_count = verified_books_not_in_collections

            stats = {
                "episodes_non_traites": self.mongodb_service.get_untreated_episodes_count(),
                "couples_en_base": self.mongodb_service.get_books_in_collections_count(),
                "couples_verified_pas_en_base": verified_count,
                "couples_suggested_pas_en_base": self.mongodb_service.get_suggested_books_not_in_collections(),
                "couples_not_found_pas_en_base": self.mongodb_service.get_not_found_books_not_in_collections(),
            }
            return stats
        except Exception as e:
            raise Exception(
                f"Erreur lors de la récupération des statistiques: {e}"
            ) from e

    def auto_process_verified_books(self) -> dict[str, Any]:
        """
        Traite automatiquement les livres avec statut 'verified'.

        Returns:
            Dictionnaire avec les résultats du traitement
        """
        try:
            verified_books = (
                self.mongodb_service.get_verified_books_not_in_collections()
            )

            processed_count = 0
            created_authors = 0
            created_books = 0
            updated_references = 0

            for book in verified_books:
                # Créer l'auteur si il n'existe pas
                author_id = self.mongodb_service.create_author_if_not_exists(
                    book["auteur"]
                )
                if author_id:
                    created_authors += 1

                # Récupérer l'avis critique correspondant à l'épisode
                critical_review = (
                    self.mongodb_service.get_critical_review_by_episode_oid(
                        book["episode_oid"]
                    )
                )
                avis_critiques_ids = []
                if critical_review:
                    avis_critiques_ids = [critical_review["_id"]]

                # Créer le livre si il n'existe pas
                book_data = {
                    "titre": book["titre"],
                    "auteur_id": author_id,
                    "editeur": book.get("editeur", ""),
                    "episodes": [ObjectId(book["episode_oid"])],
                    "avis_critiques": avis_critiques_ids,
                }
                book_id = self.mongodb_service.create_book_if_not_exists(book_data)
                if book_id:
                    created_books += 1

                # Mettre à jour les références
                # TODO: Ajouter la logique de mise à jour des références entre collections
                updated_references += 1

                processed_count += 1

            return {
                "processed_count": processed_count,
                "created_authors": created_authors,
                "created_books": created_books,
                "updated_references": updated_references,
            }

        except Exception as e:
            raise Exception(f"Erreur lors du traitement automatique: {e}") from e

    def get_books_by_validation_status(self, status: str) -> list[dict[str, Any]]:
        """
        Récupère les livres par statut de validation.

        Args:
            status: Statut de validation ('verified', 'suggested', 'not_found')

        Returns:
            Liste des livres avec le statut demandé
        """
        try:
            result = self.mongodb_service.get_books_by_validation_status(status)
            return list(result)
        except Exception as e:
            raise Exception(
                f"Erreur lors de la récupération des livres par statut: {e}"
            ) from e

    def manually_validate_suggestion(self, book_data: dict[str, Any]) -> dict[str, Any]:
        """
        Valide manuellement une suggestion d'auteur/livre.

        Args:
            book_data: Données du livre avec les corrections de l'utilisateur

        Returns:
            Dictionnaire avec les résultats de la validation
        """
        try:
            # Créer l'auteur avec le nom validé par l'utilisateur
            author_name = book_data.get("user_validated_author") or book_data["auteur"]
            author_id = self.mongodb_service.create_author_if_not_exists(author_name)

            # Créer le livre avec le titre validé par l'utilisateur
            book_title = book_data.get("user_validated_title") or book_data["titre"]
            book_info = {
                "titre": book_title,
                "auteur_id": author_id,
                "editeur": book_data.get("editeur", ""),
                "episodes": [],
                "avis_critiques": [],
            }
            book_id = self.mongodb_service.create_book_if_not_exists(book_info)

            # Mettre à jour le statut de validation du livre original
            self.mongodb_service.update_book_validation(
                book_data["id"],
                "validated",
                {"validated_author": author_name, "validated_title": book_title},
            )

            return {
                "success": True,
                "author_id": str(author_id),
                "book_id": str(book_id),
            }

        except Exception as e:
            raise Exception(f"Erreur lors de la validation manuelle: {e}") from e

    def manually_add_not_found_book(self, book_data: dict[str, Any]) -> dict[str, Any]:
        """
        Ajoute manuellement un livre marqué comme 'not_found'.

        Args:
            book_data: Données du livre saisies par l'utilisateur

        Returns:
            Dictionnaire avec les résultats de l'ajout
        """
        try:
            # Créer l'auteur avec le nom saisi par l'utilisateur
            author_name = book_data["user_entered_author"]
            author_id = self.mongodb_service.create_author_if_not_exists(author_name)

            # Créer le livre avec les données saisies par l'utilisateur
            book_info = {
                "titre": book_data["user_entered_title"],
                "auteur_id": author_id,
                "editeur": book_data.get("user_entered_publisher", ""),
                "episodes": [],
                "avis_critiques": [],
            }
            book_id = self.mongodb_service.create_book_if_not_exists(book_info)

            # Mettre à jour le statut de validation du livre original
            self.mongodb_service.update_book_validation(
                book_data["id"],
                "manually_added",
                {
                    "manual_author": author_name,
                    "manual_title": book_data["user_entered_title"],
                    "manual_publisher": book_data.get("user_entered_publisher", ""),
                },
            )

            return {
                "success": True,
                "author_id": str(author_id),
                "book_id": str(book_id),
            }

        except Exception as e:
            raise Exception(f"Erreur lors de l'ajout manuel: {e}") from e

    def get_all_authors(self) -> list[dict[str, Any]]:
        """
        Récupère tous les auteurs de la collection.

        Returns:
            Liste de tous les auteurs
        """
        try:
            result = self.mongodb_service.get_all_authors()
            return list(result)
        except Exception as e:
            raise Exception(f"Erreur lors de la récupération des auteurs: {e}") from e

    def get_all_books(self) -> list[dict[str, Any]]:
        """
        Récupère tous les livres de la collection.

        Returns:
            Liste de tous les livres
        """
        try:
            result = self.mongodb_service.get_all_books()
            return list(result)
        except Exception as e:
            raise Exception(f"Erreur lors de la récupération des livres: {e}") from e


# Instance globale du service
collections_management_service = CollectionsManagementService()
