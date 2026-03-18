"""Service de recommandations de livres par collaborative filtering.

Algorithme SVD (Surprise) entraîné sur la matrice critique×livre issue des
avis du Masque & la Plume, avec injection des notes personnelles Calibre.

Score hybride : 0.7 × svd_predict(Moi, livre) + 0.3 × masque_moyenne(livre)

Décisions architecturales (spike #235) :
- SVD : n_factors=20, n_epochs=50, lr_all=0.01, reg_all=0.1
- Filtre : livres notés par ≥ 2 critiques Masque
- Filtre : critiques avec ≥ 10 avis dans la base
- Calcul temps réel à chaque requête (pas de cache en V1)
- Scoring hybride pour corriger les artefacts SVD pur

Issue #222
"""

import logging
from typing import Any

import pandas as pd
from bson import ObjectId
from surprise import SVD, Dataset, Reader

from ..utils.text_utils import normalize_for_matching


logger = logging.getLogger(__name__)

# Hyperparamètres SVD validés par le spike #235
SVD_PARAMS = {
    "n_factors": 20,
    "n_epochs": 50,
    "lr_all": 0.01,
    "reg_all": 0.1,
    "random_state": 42,  # Reproductibilité des scores entre appels successifs
}

# Identifiant utilisateur injecté dans le dataset SVD
USER_ID = "Moi"

# Poids du scoring hybride
HYBRID_WEIGHT_SVD = 0.7
HYBRID_WEIGHT_MASQUE = 0.3

# Filtres
MIN_AVIS_PER_CRITIQUE = 10  # Critiques avec < 10 avis exclus
MIN_CRITIQUES_PER_LIVRE = 2  # Livres notés par < 2 critiques exclus


class RecommendationService:
    """Service de recommandations par collaborative filtering SVD."""

    def __init__(
        self,
        calibre_service: Any,
        mongodb_service: Any,
    ) -> None:
        self._calibre_service = calibre_service
        self._mongodb_service = mongodb_service

    # ------------------------------------------------------------------
    # Méthodes publiques
    # ------------------------------------------------------------------

    def get_recommendations(self, top_n: int = 20) -> list[dict[str, Any]]:
        """Calcule les recommandations de livres pour l'utilisateur.

        Pipeline temps réel :
        1. Charger avis MongoDB + notes Calibre
        2. Filtrer critiques avec < MIN_AVIS_PER_CRITIQUE avis
        3. Entraîner SVD Surprise
        4. Calculer score hybride pour chaque livre non vu
        5. Enrichir avec titres et auteurs depuis MongoDB
        6. Retourner top-N triés par score décroissant

        Returns:
            Liste de dicts avec rank, livre_id, titre, auteur_id, auteur_nom,
            score_hybride, svd_predict, masque_mean, masque_count.
        """
        # 1. Charger les notes Calibre de l'utilisateur
        calibre_notes = self._load_calibre_notes()
        if not calibre_notes:
            logger.info("Aucune note Calibre disponible — recommandations vides")
            return []

        # 2. Charger les avis MongoDB (matrice critique × livre)
        avis_data = self._load_avis_mongodb()
        if not avis_data:
            logger.info("Aucun avis MongoDB disponible — recommandations vides")
            return []

        # 3. Filtrer les critiques avec peu d'avis
        active_critiques = self._filter_active_critiques(
            avis_data, min_avis=MIN_AVIS_PER_CRITIQUE
        )

        avis_filtered = [a for a in avis_data if a["critique_oid"] in active_critiques]

        # 4. Matcher les livres Calibre avec les livres MongoDB
        # pour identifier les livre_oid déjà vus par l'utilisateur
        livre_oids_seen = self._match_calibre_to_livre_oids(calibre_notes)

        # 5. Injecter les notes Calibre dans le dataset
        calibre_rows = [
            {"critique_oid": USER_ID, "livre_oid": oid, "note": note}
            for oid, note in livre_oids_seen.items()
        ]

        # 6. Calculer les moyennes Masque par livre (avant injection Calibre)
        masque_means = self._compute_masque_means(avis_filtered)

        # 7. Entraîner le modèle SVD
        all_rows = avis_filtered + calibre_rows
        if not all_rows:
            return []

        algo = self._train_svd(all_rows)

        # 8. Identifier les livres candidats (non vus, ≥ MIN_CRITIQUES_PER_LIVRE critiques)
        candidates = {
            livre_oid: stats
            for livre_oid, stats in masque_means.items()
            if livre_oid not in livre_oids_seen
            and stats["count"] >= MIN_CRITIQUES_PER_LIVRE
        }

        if not candidates:
            logger.info("Aucun livre candidat pour les recommandations")
            return []

        # 9. Calculer les scores hybrides
        scored = []
        for livre_oid, stats in candidates.items():
            svd_pred = algo.predict(USER_ID, livre_oid).est
            masque_mean = stats["mean"]
            hybrid = self._compute_hybrid_score(svd_pred, masque_mean)
            scored.append(
                {
                    "livre_oid": livre_oid,
                    "svd_predict": round(svd_pred, 3),
                    "masque_mean": round(masque_mean, 2),
                    "masque_count": stats["count"],
                    "score_hybride": round(hybrid, 3),
                }
            )

        # 10. Trier par score décroissant et limiter à top_n
        scored.sort(key=lambda x: x["score_hybride"], reverse=True)
        top = scored[:top_n]

        # 11. Enrichir avec titres et auteurs depuis MongoDB
        enriched = self._enrich_with_livre_auteur(top)

        return enriched

    # ------------------------------------------------------------------
    # Méthodes privées — chargement des données
    # ------------------------------------------------------------------

    def _load_calibre_notes(self) -> dict[str, float]:
        """Charge les notes Calibre de l'utilisateur.

        Returns:
            Dict {titre_normalise: note_sur_10}
        """
        if not self._calibre_service._available:
            return {}

        try:
            books = self._calibre_service.get_all_books_with_tags()
        except Exception:
            logger.exception("Erreur lors du chargement des livres Calibre")
            return {}

        notes: dict[str, float] = {}
        for book in books:
            rating = book.get("rating")
            if not rating or rating == 0:
                continue
            # Calibre stocke les ratings 2-10 par pas de 2 (2=1★, 4=2★, ..., 10=5★)
            # Ces valeurs sont directement sur l'échelle 1-10, pas de conversion nécessaire
            note = float(rating)
            titre_norm = normalize_for_matching(book.get("title", ""))
            if titre_norm:
                notes[titre_norm] = note

        return notes

    def _load_avis_mongodb(self) -> list[dict[str, Any]]:
        """Charge les avis notés depuis la collection MongoDB `avis`.

        Returns:
            Liste de dicts {critique_oid: str, livre_oid: str, note: int}
        """
        if self._mongodb_service.avis_collection is None:
            return []

        pipeline: list[dict[str, Any]] = [
            {
                "$match": {
                    "livre_oid": {"$ne": None},
                    "note": {"$ne": None},
                    "critique_oid": {"$ne": None},
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "critique_oid": 1,
                    "livre_oid": 1,
                    "note": 1,
                }
            },
        ]

        try:
            return list(self._mongodb_service.avis_collection.aggregate(pipeline))
        except Exception:
            logger.exception("Erreur lors du chargement des avis MongoDB")
            return []

    def _match_calibre_to_livre_oids(
        self, calibre_notes: dict[str, float]
    ) -> dict[str, float]:
        """Matche les titres Calibre avec les livre_oid MongoDB.

        Utilise la normalisation de titres pour un matching insensible aux
        accents, ligatures et caractères typographiques.

        Returns:
            Dict {livre_oid: note_sur_10} — livres déjà notés par l'utilisateur
        """
        if self._mongodb_service.livres_collection is None:
            return {}

        try:
            livres = list(
                self._mongodb_service.livres_collection.find({}, {"_id": 1, "titre": 1})
            )
        except Exception:
            logger.exception("Erreur lors du chargement des livres MongoDB")
            return {}

        matched: dict[str, float] = {}
        for livre in livres:
            titre_norm = normalize_for_matching(livre.get("titre", ""))
            if titre_norm in calibre_notes:
                livre_oid = str(livre["_id"])
                matched[livre_oid] = calibre_notes[titre_norm]

        return matched

    # ------------------------------------------------------------------
    # Méthodes privées — algorithme
    # ------------------------------------------------------------------

    def _filter_active_critiques(
        self, avis_data: list[dict[str, Any]], min_avis: int = MIN_AVIS_PER_CRITIQUE
    ) -> set[str]:
        """Retourne l'ensemble des critique_oid avec au moins min_avis avis.

        Args:
            avis_data: Liste de dicts avec critique_oid, livre_oid, note
            min_avis: Nombre minimum d'avis pour être inclus

        Returns:
            Ensemble des critique_oid actifs
        """
        counts: dict[str, int] = {}
        for avis in avis_data:
            critique_oid = avis["critique_oid"]
            counts[critique_oid] = counts.get(critique_oid, 0) + 1

        return {oid for oid, count in counts.items() if count >= min_avis}

    def _compute_masque_means(
        self, avis_data: list[dict[str, Any]]
    ) -> dict[str, dict[str, Any]]:
        """Calcule les moyennes de notes Masque par livre.

        Args:
            avis_data: Liste de dicts avec critique_oid, livre_oid, note

        Returns:
            Dict {livre_oid: {"mean": float, "count": int}}
        """
        sums: dict[str, float] = {}
        counts: dict[str, int] = {}
        for avis in avis_data:
            oid = avis["livre_oid"]
            sums[oid] = sums.get(oid, 0.0) + float(avis["note"])
            counts[oid] = counts.get(oid, 0) + 1

        return {
            oid: {"mean": sums[oid] / counts[oid], "count": counts[oid]} for oid in sums
        }

    def _compute_hybrid_score(self, svd_predict: float, masque_mean: float) -> float:
        """Calcule le score hybride SVD + moyenne Masque.

        Args:
            svd_predict: Prédiction SVD sur l'échelle 1-10
            masque_mean: Moyenne des notes Masque sur l'échelle 1-10

        Returns:
            Score hybride : 0.7 × svd_predict + 0.3 × masque_mean
        """
        return HYBRID_WEIGHT_SVD * svd_predict + HYBRID_WEIGHT_MASQUE * masque_mean

    def _train_svd(self, rows: list[dict[str, Any]]) -> SVD:
        """Entraîne le modèle SVD Surprise sur le dataset.

        Args:
            rows: Liste de dicts {critique_oid, livre_oid, note}
                  (inclut les notes de l'utilisateur Calibre)

        Returns:
            Modèle SVD entraîné
        """
        df = pd.DataFrame(rows, columns=["critique_oid", "livre_oid", "note"])
        df = df.rename(
            columns={"critique_oid": "user", "livre_oid": "item", "note": "rating"}
        )

        reader = Reader(rating_scale=(1, 10))
        data = Dataset.load_from_df(df[["user", "item", "rating"]], reader)
        trainset = data.build_full_trainset()

        algo = SVD(**SVD_PARAMS)
        algo.fit(trainset)

        logger.info(
            "SVD entraîné sur %d avis (%d utilisateurs, %d livres)",
            trainset.n_ratings,
            trainset.n_users,
            trainset.n_items,
        )
        return algo

    # ------------------------------------------------------------------
    # Enrichissement avec données MongoDB
    # ------------------------------------------------------------------

    def _enrich_with_livre_auteur(
        self, scored: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Enrichit les recommandations avec titres et auteurs depuis MongoDB.

        Args:
            scored: Liste triée de dicts avec livre_oid, score_hybride, etc.

        Returns:
            Liste de dicts enrichis avec rank, titre, auteur_id, auteur_nom
        """
        if not scored:
            return []

        livre_oids = [item["livre_oid"] for item in scored]

        # Charger les livres
        try:
            object_ids = [ObjectId(oid) for oid in livre_oids]
        except Exception:
            logger.exception("Erreur de conversion des livre_oid en ObjectId")
            return []

        try:
            livres_docs = list(
                self._mongodb_service.livres_collection.find(
                    {"_id": {"$in": object_ids}},
                    {"titre": 1, "auteur_id": 1},
                )
            )
        except Exception:
            logger.exception("Erreur lors du chargement des livres pour enrichissement")
            return []

        # Index livre_oid → données livre
        livres_index: dict[str, dict[str, Any]] = {
            str(doc["_id"]): doc for doc in livres_docs
        }

        # Charger les auteurs
        auteur_ids = list(
            {
                doc["auteur_id"]
                for doc in livres_docs
                if "auteur_id" in doc and doc["auteur_id"] is not None
            }
        )

        auteurs_index: dict[str, str] = {}
        if auteur_ids:
            try:
                auteurs_docs = list(
                    self._mongodb_service.auteurs_collection.find(
                        {"_id": {"$in": auteur_ids}},
                        {"nom": 1},
                    )
                )
                auteurs_index = {
                    str(doc["_id"]): doc.get("nom", "") for doc in auteurs_docs
                }
            except Exception:
                logger.exception("Erreur lors du chargement des auteurs")

        # Assembler le résultat final
        result = []
        rank = 1
        for item in scored:
            oid = item["livre_oid"]
            livre = livres_index.get(oid, {})
            auteur_id_obj = livre.get("auteur_id")
            auteur_id_str = str(auteur_id_obj) if auteur_id_obj else ""
            auteur_nom = auteurs_index.get(auteur_id_str, "")

            result.append(
                {
                    "rank": rank,
                    "livre_id": oid,
                    "titre": livre.get("titre", ""),
                    "auteur_id": auteur_id_str,
                    "auteur_nom": auteur_nom,
                    "score_hybride": item["score_hybride"],
                    "svd_predict": item["svd_predict"],
                    "masque_mean": item["masque_mean"],
                    "masque_count": item["masque_count"],
                }
            )
            rank += 1

        return result
