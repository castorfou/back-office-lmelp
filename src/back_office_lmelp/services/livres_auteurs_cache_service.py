"""Service de cache pour les couples auteurs/livres (Issue #66 - Phase 1)."""

from datetime import datetime
from typing import Any

from bson import ObjectId

from .mongodb_service import mongodb_service


class LivresAuteursCacheService:
    """Service pour gérer le cache des couples auteurs/livres."""

    def __init__(self):
        """Initialise le service de cache."""
        self.mongodb_service = mongodb_service

    def create_cache_entry(
        self, avis_critique_id: ObjectId, book_data: dict[str, Any]
    ) -> ObjectId:
        """
        Crée une nouvelle entrée dans le cache livres-auteurs.

        Args:
            avis_critique_id: ID de l'avis critique source
            book_data: Données du livre extraites et vérifiées

        Returns:
            ObjectId de l'entrée créée

        Raises:
            ValueError: Si des champs obligatoires manquent
        """
        # Validation des champs obligatoires (système simplifié)
        required_fields = ["auteur", "titre", "episode_oid", "status"]
        for field in required_fields:
            if field not in book_data:
                raise ValueError(f"Champ obligatoire manquant: {field}")

        # Validation des statuts autorisés (4 statuts corrects selon spécification)
        allowed_statuses = ["not_found", "suggested", "verified", "mongo"]
        if book_data["status"] not in allowed_statuses:
            raise ValueError(
                f"Statut invalide: {book_data['status']}. Statuts autorisés: {allowed_statuses}"
            )

        # Préparer les données pour l'insertion
        now = datetime.now()

        # Système simplifié : champs essentiels seulement
        cache_entry = {
            "avis_critique_id": avis_critique_id,
            "episode_oid": book_data["episode_oid"],
            "auteur": book_data["auteur"],
            "titre": book_data["titre"],
            "editeur": book_data.get("editeur", ""),
            "programme": book_data.get("programme", False),
            "status": book_data["status"],  # UN SEUL statut unifié
            "created_at": now,
            "updated_at": now,
        }

        # Ajouter les suggestions SEULEMENT si fournies (avantage NoSQL)
        if "suggested_author" in book_data and book_data["suggested_author"]:
            cache_entry["suggested_author"] = book_data["suggested_author"]
        if "suggested_title" in book_data and book_data["suggested_title"]:
            cache_entry["suggested_title"] = book_data["suggested_title"]

        # Ajouter les enrichissements Babelio SEULEMENT si fournis (Issue #85)
        if "babelio_url" in book_data and book_data["babelio_url"]:
            cache_entry["babelio_url"] = book_data["babelio_url"]
        if "babelio_publisher" in book_data and book_data["babelio_publisher"]:
            cache_entry["babelio_publisher"] = book_data["babelio_publisher"]

        # Upsert dans la collection cache pour éviter les doublons
        cache_collection = self.mongodb_service.get_collection("livresauteurs_cache")

        # Filtre d'unicité : combinaison (avis_critique_id, auteur, titre)
        uniqueness_filter = {
            "avis_critique_id": avis_critique_id,
            "auteur": book_data["auteur"],
            "titre": book_data["titre"],
        }

        # Vérifier si une entrée existe déjà
        existing_entry = cache_collection.find_one(uniqueness_filter)

        if existing_entry:
            # Préserver seulement les champs de traitement (NoSQL simplifié)
            cache_entry.update(
                {
                    "created_at": existing_entry.get(
                        "created_at", cache_entry["created_at"]
                    ),
                }
            )

            # Préserver les champs de traitement s'ils existent
            if "author_id" in existing_entry:
                cache_entry["author_id"] = existing_entry["author_id"]
            if "book_id" in existing_entry:
                cache_entry["book_id"] = existing_entry["book_id"]
            if "processed_at" in existing_entry:
                cache_entry["processed_at"] = existing_entry["processed_at"]

            # Préserver le statut de traitement si déjà en base
            if existing_entry.get("status") == "mongo":
                cache_entry["status"] = "mongo"

            # Mettre à jour l'entrée existante
            result = cache_collection.replace_one(uniqueness_filter, cache_entry)
            return ObjectId(existing_entry["_id"])
        else:
            # Créer une nouvelle entrée
            result = cache_collection.replace_one(
                uniqueness_filter, cache_entry, upsert=True
            )
            if result.upserted_id is None:
                raise RuntimeError(
                    "Failed to create cache entry: no upserted_id returned"
                )
            return ObjectId(result.upserted_id)

    def get_books_by_avis_critique_id(
        self,
        avis_critique_id: ObjectId,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Récupère les livres du cache pour un avis critique donné.

        Args:
            avis_critique_id: ID de l'avis critique
            status: Filtre optionnel par statut unifié ('verified', 'suggested', 'not_found', 'processed')

        Returns:
            Liste des livres trouvés dans le cache
        """
        # Construire le filtre de base (convertir ObjectId en string pour compatibilité)
        avis_critique_id_str = str(avis_critique_id)
        query_filter = {"avis_critique_id": avis_critique_id_str}

        # Ajouter le filtre optionnel (système simplifié)
        if status is not None:
            query_filter["status"] = status

        # Exécuter la requête
        cache_collection = self.mongodb_service.get_collection("livresauteurs_cache")
        cursor = cache_collection.find(query_filter)

        # Convertir en liste et retourner
        return list(cursor)

    def get_books_by_episode_oid(
        self,
        episode_oid: str,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Récupère tous les livres en cache pour un episode_oid donné.

        Args:
            episode_oid: OID de l'épisode
            status: Filtre optionnel par statut

        Returns:
            Liste des livres trouvés en cache pour cet épisode
        """
        cache_collection = self.mongodb_service.get_collection("livresauteurs_cache")

        # Construire le filtre de base
        query_filter = {"episode_oid": episode_oid}

        # Ajouter filtre de statut si spécifié
        allowed_statuses = ["not_found", "suggested", "verified", "mongo"]
        if status and status in allowed_statuses:
            query_filter["status"] = status

        # Exécuter la requête
        cursor = cache_collection.find(query_filter)

        # Convertir en liste et retourner
        return list(cursor)

    def update_validation_status(
        self, cache_id: ObjectId, status: str, metadata: dict[str, Any]
    ) -> bool:
        """
        Met à jour le statut d'une entrée de cache (système simplifié).

        Args:
            cache_id: ID de l'entrée de cache
            status: Nouveau statut simplifié ('verified', 'suggested', 'not_found', 'processed')
            metadata: Métadonnées associées (IDs, etc.)

        Returns:
            True si mise à jour réussie, False sinon
        """
        now = datetime.now()

        # Préparer les champs à mettre à jour (système simplifié)
        update_fields = {
            "status": status,  # UN SEUL champ de statut
            "updated_at": now,
        }

        # Ajouter processed_at si le statut passe à 'mongo' (livre ajouté en base)
        if status == "mongo":
            update_fields["processed_at"] = now

        # Ajouter les métadonnées du dictionnaire metadata
        for key, value in metadata.items():
            update_fields[key] = value

        # Effectuer la mise à jour
        cache_collection = self.mongodb_service.get_collection("livresauteurs_cache")
        result = cache_collection.update_one({"_id": cache_id}, {"$set": update_fields})

        return bool(result.modified_count > 0)

    def mark_as_processed(
        self,
        cache_id: ObjectId,
        author_id: ObjectId,
        book_id: ObjectId,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """
        Marque une entrée comme traitée avec les références vers les collections finales.

        Args:
            cache_id: ID de l'entrée de cache
            author_id: ID de l'auteur créé dans la collection auteurs
            book_id: ID du livre créé dans la collection livres
            metadata: Métadonnées supplémentaires à persister (ex: babelio_publisher)

        Returns:
            True si mise à jour réussie, False sinon
        """
        update_metadata = {
            "author_id": author_id,
            "book_id": book_id,
        }

        # Ajouter les métadonnées supplémentaires si fournies (Issue #85: babelio_publisher)
        if metadata:
            update_metadata.update(metadata)
            # Issue #85: babelio_publisher reste SÉPARÉ de editeur
            # Les deux champs coexistent:
            # - editeur: valeur du markdown (ex: "POL")
            # - babelio_publisher: enrichissement Babelio (ex: "P.O.L.")
            # Le frontend affiche babelio_publisher s'il existe, sinon editeur

        return self.update_validation_status(cache_id, "mongo", update_metadata)

    def mark_summary_corrected(self, cache_id: ObjectId) -> bool:
        """
        Marque qu'une entrée a eu son summary corrigé dans avis_critiques (Issue #67).

        Args:
            cache_id: ID de l'entrée de cache

        Returns:
            True si mise à jour réussie, False sinon
        """
        try:
            cache_collection = self.mongodb_service.get_collection(
                "livresauteurs_cache"
            )
            result = cache_collection.update_one(
                {"_id": cache_id}, {"$set": {"summary_corrected": True}}
            )
            return bool(result.modified_count > 0 or result.matched_count > 0)
        except Exception as e:
            print(f"Erreur lors du marquage summary_corrected pour {cache_id}: {e}")
            return False

    def is_summary_corrected(self, cache_id: ObjectId) -> bool:
        """
        Vérifie si le summary a déjà été corrigé pour cette entrée.

        Args:
            cache_id: ID de l'entrée de cache

        Returns:
            True si summary_corrected=True, False sinon
        """
        try:
            cache_collection = self.mongodb_service.get_collection(
                "livresauteurs_cache"
            )
            entry = cache_collection.find_one({"_id": cache_id})
            if entry:
                return bool(entry.get("summary_corrected", False))
            return False
        except Exception as e:
            print(
                f"Erreur lors de la vérification summary_corrected pour {cache_id}: {e}"
            )
            return False

    def get_statistics_from_cache(self) -> dict[str, int]:
        """
        Récupère les statistiques optimisées depuis le cache (système simplifié).

        Returns:
            Dictionnaire des statistiques basées sur le nouveau système unifié
        """
        cache_collection = self.mongodb_service.get_collection("livresauteurs_cache")

        # Agrégation simplifiée : Compter par statut unifié
        status_pipeline = [{"$group": {"_id": "$status", "count": {"$sum": 1}}}]
        status_stats = list(cache_collection.aggregate(status_pipeline))

        # Construire les statistiques finales (nouveau système simplifié)
        stats = {
            "couples_en_base": 0,
            "couples_suggested_pas_en_base": 0,
            "couples_not_found_pas_en_base": 0,
        }

        # Traiter les statistiques par statut unifié
        for item in status_stats:
            status = item["_id"]
            count = item["count"]

            if status == "mongo":
                stats["couples_en_base"] = count
            elif status == "suggested":
                stats["couples_suggested_pas_en_base"] = count
            elif status == "not_found":
                stats["couples_not_found_pas_en_base"] = count

        # Compter les avis critiques analysés (nombre d'avis_critique_id distincts dans le cache)
        treated_avis_ids = cache_collection.distinct("avis_critique_id")
        stats["avis_critiques_analyses"] = len(treated_avis_ids)

        # Ajouter les épisodes non traités (réutilise le calcul ci-dessus)
        stats["episodes_non_traites"] = self._get_untreated_count_with_treated_ids(
            treated_avis_ids
        )

        return stats

    def get_untreated_avis_critiques_count(self) -> int:
        """
        Compte les avis critiques non encore traités (pas dans le cache).

        Returns:
            Nombre d'avis critiques non traités
        """
        # Compter le total d'avis critiques
        avis_collection = self.mongodb_service.get_collection("avis_critiques")
        total_avis = avis_collection.count_documents({})

        # Compter les avis critiques distincts dans le cache
        cache_collection = self.mongodb_service.get_collection("livresauteurs_cache")
        treated_avis_ids = cache_collection.distinct("avis_critique_id")
        treated_count = len(treated_avis_ids)

        return int(total_avis - treated_count)

    def _get_untreated_count_with_treated_ids(self, treated_avis_ids: list) -> int:
        """
        Compte les avis critiques non encore traités (optimisé avec IDs déjà calculés).

        Args:
            treated_avis_ids: Liste des avis_critique_id déjà traités

        Returns:
            Nombre d'avis critiques non traités
        """
        # Compter le total d'avis critiques
        avis_collection = self.mongodb_service.get_collection("avis_critiques")
        total_avis = avis_collection.count_documents({})

        # Utiliser la liste déjà calculée
        treated_count = len(treated_avis_ids)

        return int(total_avis - treated_count)

    def delete_cache_by_episode(self, episode_oid: str) -> int:
        """
        Supprime toutes les entrées de cache pour un épisode donné.

        Args:
            episode_oid: ID de l'épisode dont on veut supprimer le cache

        Returns:
            Nombre de documents supprimés
        """
        cache_collection = self.mongodb_service.get_collection("livresauteurs_cache")
        result = cache_collection.delete_many({"episode_oid": episode_oid})
        return int(result.deleted_count)


# Instance globale du service
livres_auteurs_cache_service = LivresAuteursCacheService()
