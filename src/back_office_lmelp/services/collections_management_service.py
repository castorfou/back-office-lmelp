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
            # Nettoyer les espaces parasites dans tous les champs texte
            # Ceci évite les problèmes de matching et doublons causés par les copier-coller
            text_fields = [
                "auteur",
                "titre",
                "editeur",
                "user_validated_author",
                "user_validated_title",
                "user_validated_publisher",
                "user_entered_author",
                "user_entered_title",
                "user_entered_publisher",
                "suggested_author",
                "suggested_title",
                "suggested_publisher",
            ]
            for field in text_fields:
                if field in book_data and isinstance(book_data[field], str):
                    book_data[field] = book_data[field].strip()

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

            # Déterminer l'éditeur en priorité décroissante
            # Issue #85: babelio_publisher ajouté entre user_validated et user_entered
            publisher = (
                book_data.get("user_validated_publisher")
                or book_data.get("babelio_publisher")  # Nouveau: enrichissement Babelio
                or book_data.get("user_entered_publisher")
                or book_data.get("suggested_publisher")
                or book_data.get("editeur", "")
            )

            book_info = {
                "titre": book_title,
                "auteur_id": author_id,
                "editeur": publisher,
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

                # Issue #67: Mise à jour du summary dans avis_critiques
                avis_critique_id = book_data.get("avis_critique_id")
                # Vérifier si le summary n'a pas déjà été corrigé (idempotence)
                if (
                    avis_critique_id
                    and not livres_auteurs_cache_service.is_summary_corrected(cache_id)
                ):
                    self._update_summary_with_correction(
                        avis_critique_id=avis_critique_id,
                        original_author=book_data.get("auteur", ""),
                        original_title=book_data.get("titre", ""),
                        corrected_author=author_name,
                        corrected_title=book_title,
                        cache_id=cache_id,
                    )

            return {
                "success": True,
                "author_id": str(author_id),
                "book_id": str(book_id),
            }

        except Exception as e:
            raise Exception(f"Erreur lors de la validation/ajout: {e}") from e

    def _update_summary_with_correction(
        self,
        avis_critique_id: str,
        original_author: str,
        original_title: str,
        corrected_author: str,
        corrected_title: str,
        cache_id: Any,
    ) -> None:
        """
        Met à jour le summary de l'avis critique avec les données corrigées (Issue #67).

        Args:
            avis_critique_id: ID de l'avis critique
            original_author: Auteur original (potentiellement erroné)
            original_title: Titre original (potentiellement erroné)
            corrected_author: Auteur corrigé
            corrected_title: Titre corrigé
            cache_id: ID de l'entrée dans le cache
        """
        from ..services.livres_auteurs_cache_service import (
            livres_auteurs_cache_service,
        )
        from ..utils.summary_updater import (
            replace_book_in_summary,
            should_update_summary,
        )

        try:
            # Vérifier s'il y a réellement une correction à faire
            if not should_update_summary(
                original_author, original_title, corrected_author, corrected_title
            ):
                # Pas de changement, marquer quand même comme corrigé pour éviter retraitement
                livres_auteurs_cache_service.mark_summary_corrected(cache_id)
                return

            # Récupérer l'avis critique
            avis_critique = self.mongodb_service.get_avis_critique_by_id(
                avis_critique_id
            )
            if not avis_critique:
                print(f"⚠️ Avis critique {avis_critique_id} non trouvé")
                return

            # Sauvegarder summary_origin si première correction
            updates: dict[str, Any] = {}
            if "summary_origin" not in avis_critique:
                updates["summary_origin"] = avis_critique.get("summary", "")

            # Remplacer le livre dans le summary
            original_summary = avis_critique.get("summary", "")
            updated_summary = replace_book_in_summary(
                summary=original_summary,
                original_author=original_author,
                original_title=original_title,
                corrected_author=corrected_author,
                corrected_title=corrected_title,
            )

            updates["summary"] = updated_summary

            # Mettre à jour l'avis critique
            if updates:
                self.mongodb_service.update_avis_critique(avis_critique_id, updates)

            # Marquer comme corrigé dans le cache
            livres_auteurs_cache_service.mark_summary_corrected(cache_id)

            print(f"✅ Summary mis à jour pour {corrected_author} - {corrected_title}")

        except Exception as e:
            print(f"❌ Erreur lors de la mise à jour du summary: {e}")
            # Propager l'erreur pour que le cleanup puisse la compter
            raise

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

    def cleanup_uncorrected_summaries_for_episode(
        self, episode_oid: str
    ) -> dict[str, int]:
        """
        Ramasse-miettes : corrige les summaries des livres mongo non traités.

        Cette méthode est appelée automatiquement lors de l'affichage de la page
        /livres-auteurs pour un épisode donné. Elle traite progressivement les
        livres déjà validés (status=mongo) qui n'ont pas encore eu leurs summaries
        corrigés (summary_corrected != true).

        Args:
            episode_oid: ID de l'épisode à traiter

        Returns:
            Statistiques du traitement:
            - total_books: Nombre total de livres mongo trouvés
            - already_corrected: Déjà traités (summary_corrected=true)
            - no_correction_needed: Pas de différence auteur/titre
            - corrected: Summaries mis à jour
            - errors: Erreurs rencontrées
        """
        from ..services.livres_auteurs_cache_service import (
            livres_auteurs_cache_service,
        )
        from ..utils.summary_updater import should_update_summary

        stats = {
            "total_books": 0,
            "already_corrected": 0,
            "no_correction_needed": 0,
            "corrected": 0,
            "errors": 0,
        }

        try:
            # 1. Récupérer tous les livres status=mongo pour cet épisode
            books = livres_auteurs_cache_service.get_books_by_episode_oid(
                episode_oid, status="mongo"
            )
            stats["total_books"] = len(books)

            # 2. Pour chaque livre
            for book in books:
                try:
                    # Skip si déjà traité (idempotence)
                    if livres_auteurs_cache_service.is_summary_corrected(book["_id"]):
                        stats["already_corrected"] += 1
                        continue

                    # Récupérer les valeurs originales et corrigées (depuis Phase 0)
                    original_author = book.get("auteur", "")
                    original_title = book.get("titre", "")
                    # Utiliser suggested_* (Phase 0 Babelio), PAS validated_*
                    corrected_author = book.get("suggested_author", original_author)
                    corrected_title = book.get("suggested_title", original_title)

                    # Skip si pas de correction nécessaire
                    if not should_update_summary(
                        original_author,
                        original_title,
                        corrected_author,
                        corrected_title,
                    ):
                        stats["no_correction_needed"] += 1
                        # Marquer quand même pour éviter de re-vérifier
                        livres_auteurs_cache_service.mark_summary_corrected(book["_id"])
                        continue

                    # 3. Corriger le summary (réutilise le code existant)
                    avis_critique_id = book.get("avis_critique_id")
                    if avis_critique_id:
                        self._update_summary_with_correction(
                            avis_critique_id=str(avis_critique_id),
                            original_author=original_author,
                            original_title=original_title,
                            corrected_author=corrected_author,
                            corrected_title=corrected_title,
                            cache_id=book["_id"],
                        )
                        stats["corrected"] += 1

                except Exception as e:
                    stats["errors"] += 1
                    print(f"Erreur cleanup pour livre {book.get('_id')}: {e}")
                    continue

            return stats

        except Exception as e:
            print(f"Erreur cleanup épisode {episode_oid}: {e}")
            return stats


# Instance globale du service
collections_management_service = CollectionsManagementService()
