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

    def get_cache_statistics(self) -> dict[str, int]:
        """
        Récupère les statistiques optimisées depuis le cache.

        Returns:
            Dictionnaire avec les statistiques complètes
        """
        result = self.cache_service.get_statistics_from_cache()
        return dict(result) if result else {}

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


# Instance globale pour utilisation directe
stats_service = StatsService()
