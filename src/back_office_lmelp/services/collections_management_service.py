"""Service de gestion automatique des collections auteurs/livres (Issue #66)."""

from typing import Any

from bson import ObjectId

from .livres_auteurs_cache_service import livres_auteurs_cache_service
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
            # Utiliser le cache pour les statistiques optimisées
            return livres_auteurs_cache_service.get_statistics_from_cache()
        except Exception as cache_error:
            # Fallback vers l'ancienne méthode en cas d'erreur de cache
            try:
                # Utiliser le système unifié pour compter les livres par statut
                verified_books = self.mongodb_service.get_books_by_validation_status(
                    "verified"
                )
                suggested_books = self.mongodb_service.get_books_by_validation_status(
                    "suggested"
                )
                not_found_books = self.mongodb_service.get_books_by_validation_status(
                    "not_found"
                )

                stats = {
                    "episodes_non_traites": self.mongodb_service.get_untreated_episodes_count(),
                    "couples_en_base": self.mongodb_service.get_books_in_collections_count(),
                    "couples_verified_pas_en_base": len(verified_books),
                    "couples_suggested_pas_en_base": len(suggested_books),
                    "couples_not_found_pas_en_base": len(not_found_books),
                }
                return stats
            except Exception as fallback_error:
                raise Exception(
                    f"Erreur lors de la récupération des statistiques (cache et fallback échoués): {cache_error}, {fallback_error}"
                ) from fallback_error

    def auto_process_verified_books(self) -> dict[str, Any]:
        """
        Traite automatiquement les livres avec statut 'verified'.

        Returns:
            Dictionnaire avec les résultats du traitement
        """
        try:
            # Utiliser le système unifié pour récupérer les livres verified
            verified_books = self.mongodb_service.get_books_by_validation_status(
                "verified"
            )

            processed_count = 0
            created_authors = 0
            created_books = 0
            updated_references = 0

            for book in verified_books:
                # Utiliser le nom validé (suggested_author si disponible, sinon auteur original)
                validated_author = book.get("suggested_author") or book["auteur"]
                validated_title = book.get("suggested_title") or book["titre"]

                # Créer l'auteur si il n'existe pas
                author_id = self.mongodb_service.create_author_if_not_exists(
                    validated_author
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
                    "titre": validated_title,
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

        DEPRECATED: Cette méthode redirige vers handle_book_validation pour la compatibilité.

        Args:
            book_data: Données du livre avec les corrections de l'utilisateur

        Returns:
            Dictionnaire avec les résultats de la validation
        """
        print(
            "⚠️ DEPRECATED: manually_validate_suggestion appelée - redirection vers handle_book_validation"
        )
        # Rediriger vers la méthode unifiée pour éviter la duplication de code
        return self.handle_book_validation(book_data)

    def handle_book_validation(self, book_data: dict[str, Any]) -> dict[str, Any]:
        """
        Méthode unifiée pour valider/ajouter un livre (suggested ou not_found).

        Cette méthode remplace manually_validate_suggestion et manually_add_not_found_book
        en utilisant la même logique pour les deux cas.

        Args:
            book_data: Données du livre avec les corrections/saisies de l'utilisateur
                      Peut contenir user_validated_* ou user_entered_* selon le cas

        Returns:
            Dictionnaire avec les résultats de la validation/ajout
        """
        try:
            # Déterminer le nom de l'auteur en priorité décroissante
            author_name = (
                book_data.get("user_validated_author")
                or book_data.get("user_entered_author")
                or book_data.get("suggested_author")
                or book_data["auteur"]
            )
            author_id = self.mongodb_service.create_author_if_not_exists(author_name)

            # Déterminer le titre du livre en priorité décroissante
            book_title = (
                book_data.get("user_validated_title")
                or book_data.get("user_entered_title")
                or book_data.get("suggested_title")
                or book_data["titre"]
            )
            book_info = {
                "titre": book_title,
                "auteur_id": author_id,
                "editeur": book_data.get("editeur", ""),
                "episodes": [book_data["episode_oid"]]
                if book_data.get("episode_oid")
                else [],
                "avis_critiques": [book_data["avis_critique_id"]]
                if book_data.get("avis_critique_id")
                else [],
            }
            book_id = self.mongodb_service.create_book_if_not_exists(book_info)

            # Mettre à jour le cache avec le statut "mongo" et les références si un cache_id existe
            from bson import ObjectId

            from ..services.livres_auteurs_cache_service import (
                livres_auteurs_cache_service,
            )

            cache_id_str = book_data.get("cache_id")

            # Si cache_id est manquant, essayer de le retrouver via episode_oid et author/title
            if not cache_id_str and book_data.get("episode_oid"):
                try:
                    # Récupérer les livres en cache pour cet épisode
                    cached_books = (
                        livres_auteurs_cache_service.get_books_by_episode_oid(
                            book_data["episode_oid"]
                        )
                    )

                    # Chercher le livre correspondant par auteur et titre
                    author_to_find = book_data.get("auteur", "")
                    title_to_find = book_data.get("titre", "")

                    for cached_book in cached_books:
                        if (
                            cached_book.get("auteur", "") == author_to_find
                            and cached_book.get("titre", "") == title_to_find
                        ):
                            cache_id_str = str(cached_book.get("_id", ""))
                            break
                except Exception as e:
                    # Log l'erreur mais continuer sans cache_id
                    print(f"Erreur lors de la recherche cache_id: {e}")

            if cache_id_str:
                cache_id = ObjectId(cache_id_str)

                # Préparer les métadonnées avec tous les champs nécessaires
                validation_metadata = {
                    "validated_author": author_name,
                    "validated_title": book_title,
                }

                # Préserver/définir les champs suggested_author/suggested_title
                # Pour suggested: utiliser les champs fournis par le frontend
                # Pour not_found: utiliser la saisie utilisateur comme suggested
                suggested_author = (
                    book_data.get("suggested_author")
                    or book_data.get("user_validated_author")
                    or book_data.get("user_entered_author")
                    or author_name
                )
                suggested_title = (
                    book_data.get("suggested_title")
                    or book_data.get("user_validated_title")
                    or book_data.get("user_entered_title")
                    or book_title
                )

                # IMPORTANT: TOUJOURS remplir les champs suggested (pas de condition if)
                # Cela garantit que tous les livres (suggested ET not_found) ont ces champs
                validation_metadata["suggested_author"] = suggested_author
                validation_metadata["suggested_title"] = suggested_title

                # Mettre à jour le statut de validation du livre original
                self.mongodb_service.update_book_validation(
                    cache_id_str,
                    "validated",
                    validation_metadata,
                )
                # Marquer comme traité dans le cache (statut mongo)
                livres_auteurs_cache_service.mark_as_processed(
                    cache_id, author_id, book_id
                )

            return {
                "success": True,
                "author_id": str(author_id),
                "book_id": str(book_id),
            }

        except Exception as e:
            raise Exception(f"Erreur lors de la validation/ajout: {e}") from e

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
