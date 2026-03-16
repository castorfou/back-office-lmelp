"""Service autonome pour la consultation des statistiques du cache livres/auteurs."""

from typing import Any

from .livres_auteurs_cache_service import livres_auteurs_cache_service
from .mongodb_service import mongodb_service


class StatsService:
    """Service pour consulter les statistiques du système cache-first."""

    def __init__(self):
        """Initialise le service de statistiques."""
        self.cache_service = livres_auteurs_cache_service
        self.mongodb_service = mongodb_service

    def get_cache_statistics(self) -> dict[str, Any]:
        """
        Récupère les statistiques optimisées depuis le cache.

        Returns:
            Dictionnaire avec les statistiques complètes (incluant métriques Issue #124 et #128)
        """
        result = self.cache_service.get_statistics_from_cache()
        stats = dict(result) if result else {}

        # Issue #124: Ajouter métriques de complétude URL Babelio
        stats["books_without_url_babelio"] = self._count_books_without_url_babelio()
        stats["authors_without_url_babelio"] = self._count_authors_without_url_babelio()

        # Issue #128: Ajouter nouvelles métriques
        stats["last_episode_date"] = self._get_last_episode_date()
        stats["episodes_without_avis_critiques"] = (
            self._count_episodes_without_avis_critiques()
        )
        stats["avis_critiques_without_analysis"] = (
            self._count_avis_critiques_without_analysis()
        )

        # Issue #185: Ajouter métriques des badges d'émissions
        stats["emissions_sans_avis"] = self._count_emissions_sans_avis()
        stats["emissions_with_problems"] = self._count_emissions_with_problems()

        # Issue #238: Livres avec url_babelio mais sans url_cover
        stats["books_without_cover"] = self._count_books_without_cover()

        return stats

    def _count_books_without_url_babelio(self) -> int:
        """
        Compte les livres sans URL Babelio (Issue #124, #128).

        Compte uniquement les livres à traiter manuellement (sans url_babelio).
        Exclut les livres avec babelio_not_found: true car confirmés comme absents de Babelio.

        Returns:
            Nombre de livres sans lien Babelio (à traiter manuellement)
        """
        livres_collection = self.mongodb_service.get_collection("livres")
        count: int = livres_collection.count_documents(
            {
                "$and": [
                    {
                        "$or": [
                            {"url_babelio": None},
                            {"url_babelio": {"$exists": False}},
                        ]
                    },
                    {
                        "$or": [
                            {"babelio_not_found": {"$ne": True}},
                            {"babelio_not_found": {"$exists": False}},
                        ]
                    },
                ]
            }
        )
        return count

    def _count_authors_without_url_babelio(self) -> int:
        """
        Compte les auteurs sans URL Babelio (Issue #124, #128).

        Compte uniquement les auteurs à traiter manuellement (sans url_babelio).
        Exclut les auteurs avec babelio_not_found: true car confirmés comme absents de Babelio.

        Returns:
            Nombre d'auteurs sans lien Babelio (à traiter manuellement)
        """
        auteurs_collection = self.mongodb_service.get_collection("auteurs")
        count: int = auteurs_collection.count_documents(
            {
                "$and": [
                    {
                        "$or": [
                            {"url_babelio": None},
                            {"url_babelio": {"$exists": False}},
                        ]
                    },
                    {
                        "$or": [
                            {"babelio_not_found": {"$ne": True}},
                            {"babelio_not_found": {"$exists": False}},
                        ]
                    },
                ]
            }
        )
        return count

    def _get_last_episode_date(self) -> str | None:
        """
        Récupère la date du dernier épisode en base (Issue #128).

        Returns:
            Date de diffusion du dernier épisode (format ISO), ou None si aucun épisode
        """
        episodes_collection = self.mongodb_service.get_collection("episodes")
        last_episode = episodes_collection.find_one(
            sort=[("diffusion", -1)], projection={"diffusion": 1}
        )
        if last_episode and "diffusion" in last_episode:
            # Retourner la date au format ISO string
            diffusion = last_episode["diffusion"]
            if hasattr(diffusion, "isoformat"):
                return str(diffusion.isoformat())
            return str(diffusion)
        return None

    def _count_episodes_without_avis_critiques(self) -> int:
        """
        Compte les épisodes non masqués sans avis critiques extraits (Issue #128).

        Returns:
            Nombre d'épisodes où masked=False et n'ont pas d'avis critiques
        """
        episodes_collection = self.mongodb_service.get_collection("episodes")
        avis_critiques_collection = self.mongodb_service.get_collection(
            "avis_critiques"
        )

        # Compter les épisodes non masqués
        non_masked_count = episodes_collection.count_documents(
            {"$or": [{"masked": False}, {"masked": {"$exists": False}}]}
        )

        # FIX: Utiliser aggregation pour filtrer les avis dont l'épisode est masqué
        # Seuls les avis_critiques avec épisode non masqué doivent être comptés
        pipeline = [
            {
                "$lookup": {
                    "from": "episodes",
                    "let": {"episode_oid_str": "$episode_oid"},
                    "pipeline": [
                        {
                            "$match": {
                                "$expr": {
                                    "$eq": [{"$toString": "$_id"}, "$$episode_oid_str"]
                                }
                            }
                        }
                    ],
                    "as": "episode",
                }
            },
            {"$unwind": "$episode"},
            {
                "$match": {
                    "$or": [
                        {"episode.masked": {"$ne": True}},
                        {"episode.masked": {"$exists": False}},
                    ]
                }
            },
            {"$group": {"_id": "$episode_oid"}},
        ]

        episodes_with_avis_non_masques = list(
            avis_critiques_collection.aggregate(pipeline)
        )
        episodes_with_avis_count = len(episodes_with_avis_non_masques)

        # Retourner la différence
        return int(max(0, non_masked_count - episodes_with_avis_count))

    def _count_avis_critiques_without_analysis(self) -> int:
        """
        Compte les épisodes non masqués avec avis critiques mais sans analyse (Issue #128, #143, #148).

        Un épisode est considéré comme "avec avis critique" s'il existe au moins un document
        dans avis_critiques qui référence cet épisode.

        Un épisode est considéré comme "analysé" s'il existe au moins un document
        dans livresauteurs_cache qui référence cet épisode.

        Exclut les épisodes masqués (Issue #143).

        Returns:
            Nombre d'épisodes avec avis critiques mais sans analyse (épisodes non masqués uniquement)
        """
        episodes_collection = self.mongodb_service.get_collection("episodes")
        avis_critiques_collection = self.mongodb_service.get_collection(
            "avis_critiques"
        )
        cache_collection = self.mongodb_service.get_collection("livresauteurs_cache")

        # Récupérer les IDs des épisodes NON masqués
        non_masked_episodes = episodes_collection.find(
            {"$or": [{"masked": False}, {"masked": {"$exists": False}}]}, {"_id": 1}
        )
        non_masked_episode_ids = {ep["_id"] for ep in non_masked_episodes}

        # Récupérer les épisodes distincts qui ont des avis critiques
        # IMPORTANT (Issue #148): episode_oid est stocké comme STRING dans la base,
        # on doit le convertir en ObjectId pour matcher avec les IDs de episodes.find()
        from bson import ObjectId

        episodes_with_avis = {
            ObjectId(ep_id) if isinstance(ep_id, str) else ep_id
            for ep_id in avis_critiques_collection.distinct("episode_oid")
            if ep_id is not None
        }

        # Filtrer pour ne garder que les épisodes NON masqués
        episodes_with_avis_non_masked = episodes_with_avis & non_masked_episode_ids

        # Récupérer les épisodes distincts qui ont été analysés
        # IMPORTANT (Issue #148): episode_oid est stocké comme STRING dans la base,
        # on doit le convertir en ObjectId pour matcher avec les IDs de episodes.find()
        episodes_analyzed = {
            ObjectId(ep_id) if isinstance(ep_id, str) else ep_id
            for ep_id in cache_collection.distinct("episode_oid")
            if ep_id is not None
        }

        # Filtrer pour ne garder que les épisodes NON masqués
        episodes_analyzed_non_masked = episodes_analyzed & non_masked_episode_ids

        # Calculer la différence: épisodes avec avis mais non analysés
        count_with_avis = len(episodes_with_avis_non_masked)
        count_analyzed = len(episodes_analyzed_non_masked)

        return int(max(0, count_with_avis - count_analyzed))

    def get_detailed_breakdown(self) -> list[dict[str, Any]]:
        """
        Récupère une répartition détaillée par biblio_verification_status.

        Returns:
            Liste des groupes avec comptes et exemples de livres
        """
        cache_collection = self.mongodb_service.get_collection("livresauteurs_cache")

        pipeline = [
            {
                "$group": {
                    "_id": "$biblio_verification_status",
                    "count": {"$sum": 1},
                    "books": {"$push": {"auteur": "$auteur", "titre": "$titre"}},
                }
            }
        ]

        return list(cache_collection.aggregate(pipeline))

    def get_validation_status_breakdown(self) -> list[dict[str, Any]]:
        """
        Récupère la répartition par validation_status.

        Returns:
            Liste des statuts de validation avec comptes
        """
        cache_collection = self.mongodb_service.get_collection("livresauteurs_cache")

        pipeline = [{"$group": {"_id": "$validation_status", "count": {"$sum": 1}}}]

        return list(cache_collection.aggregate(pipeline))

    def get_recent_processed_books(self, limit: int = 5) -> list[dict[str, Any]]:
        """
        Récupère les livres récemment auto-traités.

        Args:
            limit: Nombre maximum de livres à retourner

        Returns:
            Liste des livres récemment traités
        """
        cache_collection = self.mongodb_service.get_collection("livresauteurs_cache")

        return list(
            cache_collection.find({"validation_status": "mongo"})
            .sort("processed_at", -1)
            .limit(limit)
        )

    def get_human_readable_summary(self) -> str:
        """
        Formate un résumé lisible des statistiques.

        Returns:
            Résumé formaté pour affichage console
        """
        stats = self.get_cache_statistics()

        total_en_attente = (
            stats.get("couples_suggested_pas_en_base", 0)
            + stats.get("couples_not_found_pas_en_base", 0)
            + stats.get("couples_pending", 0)
        )

        total_traites = (
            stats.get("couples_en_base", 0)
            + total_en_attente
            + stats.get("couples_rejected", 0)
        )

        summary = f"""📊 STATISTIQUES CACHE LIVRES/AUTEURS

🚀 Auto-traités (en base) : {stats.get("couples_en_base", 0)} (couples)
📚 Livres uniques         : {stats.get("livres_uniques", 0)}
⏳ En attente validation  : {total_en_attente}
   ├─ 💡 Suggestions      : {stats.get("couples_suggested_pas_en_base", 0)}
   ├─ ❌ Non trouvés      : {stats.get("couples_not_found_pas_en_base", 0)}
   └─ ⏸️  Pending         : {stats.get("couples_pending", 0)}
🗑️  Rejetés             : {stats.get("couples_rejected", 0)}
📺 Avis critiques analysés : {stats.get("avis_critiques_analyses", 0)}
📝 Épisodes non traités : {stats.get("episodes_non_traites", 0)}

Total livres traités : {total_traites}"""

        return summary

    def display_console_stats(self) -> None:
        """Affiche les statistiques complètes dans la console."""
        print(self.get_human_readable_summary())
        print()

        # Afficher la répartition détaillée
        print("🔍 RÉPARTITION DÉTAILLÉE PAR STATUT:")
        breakdown = self.get_detailed_breakdown()

        for group in breakdown:
            status = group["_id"] or "null"
            count = group["count"]
            books = group.get("books", [])

            status_emoji = {
                "verified": "✅",
                "suggested": "💡",
                "not_found": "❌",
                "pending": "⏸️",
                "null": "❓",
            }.get(status, "📄")

            print(f"  {status_emoji} {status}: {count} livre(s)")

            # Afficher quelques exemples
            for book in books[:3]:  # Max 3 exemples
                print(f"    - {book['auteur']} - {book['titre']}")

            if len(books) > 3:
                print(f"    ... et {len(books) - 3} autres")
            print()

        # Afficher les livres récemment traités
        print("🕒 RÉCEMMENT AUTO-TRAITÉS:")
        recent = self.get_recent_processed_books()

        if recent:
            for book in recent:
                processed_date = book.get("processed_at", "Date inconnue")
                print(f"  📚 {book['auteur']} - {book['titre']} ({processed_date})")
        else:
            print("  Aucun livre récemment traité")

    def _count_emissions_sans_avis(self) -> int:
        """
        Compte les émissions avec badge_status = "no_avis" (⚪).

        Ces émissions n'ont pas encore d'avis extraits.

        OPTIMIZED (Issue #194): Utilise pipeline d'aggregation MongoDB au lieu
        d'itérer sur N émissions avec N requêtes.

        Performance: 1 aggregation au lieu de ~1500 requêtes (pour 500 émissions).

        IMPORTANT: emissions._id est ObjectId, mais avis.emission_oid est String.
        Il faut convertir _id en String pour le $lookup (Issue #194 type mismatch).

        Returns:
            Nombre d'émissions sans avis extraits
        """
        emissions_collection = self.mongodb_service.get_collection("emissions")

        # Aggregation pipeline: compter les émissions avec 0 avis
        pipeline = [
            # Step 1: Convertir _id (ObjectId) en String pour le lookup
            {"$addFields": {"emission_id_str": {"$toString": "$_id"}}},
            # Step 2: Joindre les avis pour chaque émission
            # Note: avis.emission_oid est String, emissions._id est ObjectId
            {
                "$lookup": {
                    "from": "avis",
                    "localField": "emission_id_str",
                    "foreignField": "emission_oid",
                    "as": "avis_list",
                }
            },
            # Step 3: Ajouter un champ avis_count
            {"$addFields": {"avis_count": {"$size": "$avis_list"}}},
            # Step 4: Filtrer les émissions avec avis_count == 0 (condition no_avis)
            {"$match": {"avis_count": 0}},
            # Step 5: Compter
            {"$count": "total"},
        ]

        result = list(emissions_collection.aggregate(pipeline))
        return result[0]["total"] if result else 0

    def _count_emissions_with_problems(self) -> int:
        """
        Compte les émissions avec problèmes = badge rouge (🔴) + badge jaune (🟡).

        Rouge (count_mismatch): Écart de comptage OU note manquante
        Jaune (unmatched): Livres non matchés

        OPTIMIZED (Issue #194): Utilise batch fetching (2 requêtes) au lieu
        d'itérer sur N émissions avec N×3 requêtes.

        Performance: ~N+2 requêtes au lieu de ~1500 requêtes (pour 500 émissions).

        La logique de badge est préservée depuis _calculate_emission_badge_status
        (app.py:1058-1133) pour garantir la cohérence.

        Returns:
            Nombre total d'émissions avec problèmes (rouge + jaune)
        """
        emissions_collection = self.mongodb_service.get_collection("emissions")
        avis_collection = self.mongodb_service.get_collection("avis")
        livres_collection = self.mongodb_service.get_collection("livres")

        # Step 1: Récupérer toutes les émissions (requête unique)
        emissions = list(emissions_collection.find({}, {"_id": 1, "episode_id": 1}))

        # Step 2: Récupérer tous les avis d'un coup (requête unique)
        all_avis = list(
            avis_collection.find(
                {},
                {
                    "emission_oid": 1,
                    "livre_titre_extrait": 1,
                    "livre_oid": 1,
                    "note": 1,
                },
            )
        )

        # Step 3: Grouper les avis par emission_id en mémoire (O(N))
        avis_by_emission: dict[str, list[dict[str, Any]]] = {}
        for avis in all_avis:
            emission_id = avis.get("emission_oid")
            if emission_id:
                if emission_id not in avis_by_emission:
                    avis_by_emission[emission_id] = []
                avis_by_emission[emission_id].append(avis)

        # Step 4: Pour chaque émission, calculer le badge status (en mémoire, rapide)
        count = 0
        for emission in emissions:
            emission_id_str = str(emission["_id"])
            episode_id_str = str(emission["episode_id"])

            # Récupérer les avis pour cette émission
            emission_avis = avis_by_emission.get(emission_id_str, [])

            # Ignorer si pas d'avis (badge no_avis, pas un problème)
            if not emission_avis:
                continue

            # Calculer le badge status (même logique que _calculate_emission_badge_status)
            unique_titles: set[str] = set()
            unmatched_count = 0
            missing_notes_count = 0

            for avis in emission_avis:
                titre = avis.get("livre_titre_extrait", "")
                if titre:
                    unique_titles.add(titre)
                    if avis.get("livre_oid") is None:
                        unmatched_count += 1
                    if avis.get("note") is None:
                        missing_notes_count += 1

            livres_summary = len(unique_titles)

            # Compter les livres MongoDB pour cet épisode (requête indexée rapide)
            livres_mongo_count = livres_collection.count_documents(
                {"episodes": episode_id_str}
            )

            # Déterminer le badge status
            # 🔴 count_mismatch: écart de comptage OU note manquante
            # 🟡 unmatched: comptes égaux mais livre(s) non matché(s)
            if (
                livres_summary != livres_mongo_count
                or missing_notes_count > 0
                or unmatched_count > 0
            ):
                count += 1

        return count

    def _count_books_without_cover(self) -> int:
        """Compte les livres avec url_babelio mais sans url_cover (Issue #238)."""
        livres_collection = self.mongodb_service.get_collection("livres")
        return int(
            livres_collection.count_documents(
                {
                    "url_babelio": {"$exists": True, "$ne": None},
                    "$or": [
                        {"url_cover": {"$exists": False}},
                        {"url_cover": None},
                    ],
                }
            )
        )


# Instance globale pour utilisation directe
stats_service = StatsService()
