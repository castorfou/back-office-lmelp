"""Application FastAPI principale."""

import os
import socket
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, suppress
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel
from rapidfuzz import fuzz
from thefuzz import process

from .models.episode import Episode
from .services.babelio_cache_service import BabelioCacheService
from .services.babelio_service import babelio_service
from .services.books_extraction_service import books_extraction_service
from .services.collections_management_service import collections_management_service
from .services.fixture_updater import FixtureUpdaterService
from .services.livres_auteurs_cache_service import livres_auteurs_cache_service
from .services.mongodb_service import mongodb_service
from .services.radiofrance_service import RadioFranceService
from .services.stats_service import stats_service
from .utils.memory_guard import memory_guard
from .utils.port_discovery import PortDiscovery


class BabelioVerificationRequest(BaseModel):
    """Modèle pour les requêtes de vérification Babelio."""

    type: str  # "author", "book", ou "publisher"
    name: str | None = None  # Pour author ou publisher
    title: str | None = None  # Pour book
    author: str | None = None  # Auteur du livre (optionnel pour book)


class FuzzySearchRequest(BaseModel):
    """Modèle pour les requêtes de recherche fuzzy dans les épisodes."""

    episode_id: str
    query_title: str
    query_author: str | None = None


class CapturedCall(BaseModel):
    """Modèle pour un appel API capturé."""

    service: str  # 'babelioService' | 'fuzzySearchService'
    method: str  # 'verifyAuthor' | 'verifyBook' | 'searchEpisode'
    input: dict[str, Any]
    output: dict[str, Any]
    timestamp: int


class BookValidationResult(BaseModel):
    """Modèle pour un livre avec résultat de validation du frontend."""

    auteur: str
    titre: str
    editeur: str
    programme: bool
    validation_status: str  # 'verified' | 'suggested' | 'not_found'
    suggested_author: str | None = None
    suggested_title: str | None = None
    # Issue #85: Champs d'enrichissement Babelio automatique
    babelio_url: str | None = None
    babelio_publisher: str | None = None


class ValidationResultsRequest(BaseModel):
    """Modèle pour recevoir les résultats de validation du frontend."""

    episode_oid: str
    avis_critique_id: str
    books: list[BookValidationResult]


class FixtureUpdateRequest(BaseModel):
    """Modèle pour les requêtes de mise à jour de fixtures."""

    calls: list[CapturedCall]


# Nouveaux modèles pour l'Issue #66 - Gestion des collections auteurs/livres
class ValidateSuggestionRequest(BaseModel):
    """Modèle pour la validation d'une suggestion."""

    cache_id: str | None = None
    episode_oid: str
    avis_critique_id: str
    auteur: str
    titre: str
    editeur: str | None = None
    user_validated_author: str
    user_validated_title: str
    user_validated_publisher: str | None = None
    babelio_publisher: str | None = None  # Issue #85: Enrichissement Babelio
    babelio_url: str | None = None  # Issue #85: URL Babelio du livre


class AddManualBookRequest(BaseModel):
    """Modèle pour l'ajout manuel d'un livre."""

    id: str
    user_entered_author: str
    user_entered_title: str
    user_entered_publisher: str | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Gestion du cycle de vie de l'application."""
    try:
        # Démarrage
        if not mongodb_service.connect():
            raise Exception("Impossible de se connecter à MongoDB")
        print("Connexion MongoDB établie")

        # Attach a persistent disk cache for Babelio lookups so restarts benefit
        try:
            cache_enabled = os.environ.get("BABELIO_CACHE_ENABLED", "1").lower() in (
                "1",
                "true",
                "yes",
            )

            if cache_enabled:
                cache_dir = os.environ.get(
                    "BABELIO_CACHE_DIR",
                    os.path.join(os.getcwd(), "data", "processed", "babelio_cache"),
                )
                babelio_service.cache_service = BabelioCacheService(
                    cache_dir=cache_dir, ttl_hours=24
                )
                print(f"Babelio disk cache attached at {cache_dir}")
            else:
                print("Babelio disk cache disabled via BABELIO_CACHE_ENABLED")
        except Exception as e:
            print(f"Unable to attach Babelio disk cache: {e}")

        yield

    except Exception as e:
        print(f"Erreur dans le cycle de vie: {e}")
        raise
    finally:
        # Arrêt garanti même en cas d'erreur
        try:
            mongodb_service.disconnect()
            print("Connexion MongoDB fermée")
        except Exception as e:
            print(f"Erreur lors de la fermeture: {e}")


app = FastAPI(
    title="Back-office LMELP",
    description="Interface de gestion pour la base de données du Masque et la Plume",
    version="0.1.0",
    lifespan=lifespan,
)


# Configuration CORS pour le frontend
def get_cors_configuration():
    """Retourne la configuration CORS selon l'environnement."""
    env = os.getenv("ENVIRONMENT", "development")

    if env == "development":
        # En développement, autoriser toutes les origines pour faciliter l'accès mobile
        return {
            "allow_origins": ["*"],
            "allow_credentials": False,  # Must be False when allow_origins is "*"
            "allow_methods": ["*"],
            "allow_headers": ["*"],
        }
    else:
        # En production, être restrictif
        return {
            "allow_origins": [
                "http://localhost:3000",
                "http://localhost:5173",
            ],
            "allow_credentials": True,
            "allow_methods": ["*"],
            "allow_headers": ["*"],
        }


cors_config = get_cors_configuration()
app.add_middleware(CORSMiddleware, **cors_config)


@app.get("/")
async def root() -> dict[str, str]:
    """Point d'entrée de l'API."""
    return {"message": "Back-office LMELP API", "version": "0.1.0"}


@app.get("/api/episodes", response_model=list[dict[str, Any]])
async def get_episodes() -> list[dict[str, Any]]:
    """Récupère la liste de tous les épisodes."""
    # Vérification mémoire
    memory_check = memory_guard.check_memory_limit()
    if memory_check:
        if "LIMITE MÉMOIRE DÉPASSÉE" in memory_check:
            memory_guard.force_shutdown(memory_check)
        print(f"⚠️ {memory_check}")

    try:
        episodes_data = mongodb_service.get_all_episodes()
        episodes = [Episode(data).to_summary_dict() for data in episodes_data]
        return episodes
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}") from e


@app.get("/api/episodes/{episode_id}", response_model=dict[str, Any])
async def get_episode(episode_id: str) -> dict[str, Any]:
    """Récupère un épisode par son ID."""
    # Vérification mémoire
    memory_check = memory_guard.check_memory_limit()
    if memory_check:
        if "LIMITE MÉMOIRE DÉPASSÉE" in memory_check:
            memory_guard.force_shutdown(memory_check)
        print(f"⚠️ {memory_check}")

    try:
        episode_data = mongodb_service.get_episode_by_id(episode_id)
        if not episode_data:
            raise HTTPException(status_code=404, detail="Épisode non trouvé")

        episode = Episode(episode_data)
        return episode.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}") from e


@app.delete("/api/episodes/{episode_id}", response_model=dict[str, Any])
async def delete_episode(episode_id: str) -> dict[str, Any]:
    """Supprime un épisode et toutes ses données associées.

    Effectue une suppression en cascade :
    - Supprime les avis critiques liés
    - Retire les références de l'épisode des livres
    - Supprime l'épisode lui-même
    """
    # Vérification mémoire
    memory_check = memory_guard.check_memory_limit()
    if memory_check:
        if "LIMITE MÉMOIRE DÉPASSÉE" in memory_check:
            memory_guard.force_shutdown(memory_check)
        print(f"⚠️ {memory_check}")

    try:
        # Tenter de supprimer l'épisode
        success = mongodb_service.delete_episode(episode_id)

        if not success:
            raise HTTPException(status_code=404, detail="Episode not found")

        return {
            "success": True,
            "episode_id": episode_id,
            "message": f"Episode {episode_id} deleted successfully",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}") from e


@app.put("/api/episodes/{episode_id}")
async def update_episode_description(
    episode_id: str, request: Request
) -> dict[str, str]:
    """Met à jour la description corrigée d'un épisode."""
    # Vérification mémoire
    memory_check = memory_guard.check_memory_limit()
    if memory_check:
        if "LIMITE MÉMOIRE DÉPASSÉE" in memory_check:
            memory_guard.force_shutdown(memory_check)
        print(f"⚠️ {memory_check}")

    try:
        # Lire le body de la requête (text/plain)
        description_corrigee = (await request.body()).decode("utf-8")

        # Vérifier que l'épisode existe
        episode_data = mongodb_service.get_episode_by_id(episode_id)
        if not episode_data:
            raise HTTPException(status_code=404, detail="Épisode non trouvé")

        # Mettre à jour la description avec la nouvelle logique
        success = mongodb_service.update_episode_description_new(
            episode_id, description_corrigee
        )
        if not success:
            raise HTTPException(status_code=400, detail="Échec de la mise à jour")

        return {"message": "Description mise à jour avec succès"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}") from e


@app.put("/api/episodes/{episode_id}/title")
async def update_episode_title(episode_id: str, request: Request) -> dict[str, str]:
    """Met à jour le titre corrigé d'un épisode."""
    # Vérification mémoire
    memory_check = memory_guard.check_memory_limit()
    if memory_check:
        if "LIMITE MÉMOIRE DÉPASSÉE" in memory_check:
            memory_guard.force_shutdown(memory_check)
        print(f"⚠️ {memory_check}")

    try:
        # Lire le body de la requête (text/plain)
        titre_corrige = (await request.body()).decode("utf-8")

        # Vérifier que l'épisode existe
        episode_data = mongodb_service.get_episode_by_id(episode_id)
        if not episode_data:
            raise HTTPException(status_code=404, detail="Épisode non trouvé")

        # Mettre à jour le titre avec la nouvelle logique
        success = mongodb_service.update_episode_title_new(episode_id, titre_corrige)
        if not success:
            raise HTTPException(status_code=400, detail="Échec de la mise à jour")

        return {"message": "Titre mis à jour avec succès"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}") from e


@app.post("/api/episodes/{episode_id}/fetch-page-url")
async def fetch_episode_page_url(episode_id: str) -> dict[str, Any]:
    """Fetch l'URL de la page RadioFrance pour un épisode et la persiste en DB.

    Utilise RadioFranceService pour scraper RadioFrance et trouver l'URL de la page
    de l'épisode à partir de son titre. L'URL trouvée est ensuite persistée dans le
    champ episode_page_url de l'épisode.

    Args:
        episode_id: ID de l'épisode

    Returns:
        Dict avec episode_id, episode_page_url, et success

    Raises:
        404: Si l'épisode n'existe pas en DB ou si l'URL n'est pas trouvée sur RadioFrance
        500: En cas d'erreur serveur
    """
    # Vérification mémoire
    memory_check = memory_guard.check_memory_limit()
    if memory_check:
        if "LIMITE MÉMOIRE DÉPASSÉE" in memory_check:
            memory_guard.force_shutdown(memory_check)
        print(f"⚠️ {memory_check}")

    try:
        # Vérifier que l'épisode existe
        episode_data = mongodb_service.get_episode_by_id(episode_id)
        if not episode_data:
            raise HTTPException(status_code=404, detail="Épisode non trouvé")

        # Récupérer le titre de l'épisode
        episode_title = episode_data.get("titre", "")
        if not episode_title:
            raise HTTPException(status_code=400, detail="L'épisode n'a pas de titre")

        # Chercher l'URL de la page sur RadioFrance
        radiofrance_service = RadioFranceService()
        episode_page_url = await radiofrance_service.search_episode_page_url(
            episode_title
        )

        if not episode_page_url:
            raise HTTPException(
                status_code=404,
                detail=f"URL de la page non trouvée sur RadioFrance pour: {episode_title[:50]}...",
            )

        # Persister l'URL en base de données
        success = mongodb_service.update_episode(
            episode_id, {"episode_page_url": episode_page_url}
        )

        if not success:
            raise HTTPException(
                status_code=500, detail="Échec de la mise à jour de l'épisode en base"
            )

        return {
            "episode_id": episode_id,
            "episode_page_url": episode_page_url,
            "success": True,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}") from e


@app.get("/api/statistics", response_model=dict[str, Any])
async def get_statistics() -> dict[str, Any]:
    """Récupère les statistiques de l'application."""
    # Vérification mémoire
    memory_check = memory_guard.check_memory_limit()
    if memory_check:
        if "LIMITE MÉMOIRE DÉPASSÉE" in memory_check:
            memory_guard.force_shutdown(memory_check)
        print(f"⚠️ {memory_check}")

    try:
        stats_data = mongodb_service.get_statistics()

        # Transformer les clés pour correspondre au format frontend
        return {
            "totalEpisodes": stats_data["total_episodes"],
            "episodesWithCorrectedTitles": stats_data["episodes_with_corrected_titles"],
            "episodesWithCorrectedDescriptions": stats_data[
                "episodes_with_corrected_descriptions"
            ],
            "criticalReviews": stats_data["critical_reviews_count"],
            "lastUpdateDate": stats_data["last_update_date"],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}") from e


@app.get("/api/livres-auteurs", response_model=list[dict[str, Any]])
async def get_livres_auteurs(
    episode_oid: str, limit: int | None = None
) -> list[dict[str, Any]]:
    """Récupère la liste des livres/auteurs extraits des avis critiques via parsing des tableaux markdown (format simplifié : auteur/titre/éditeur)."""
    # Vérification mémoire
    memory_check = memory_guard.check_memory_limit()
    if memory_check:
        if "LIMITE MÉMOIRE DÉPASSÉE" in memory_check:
            memory_guard.force_shutdown(memory_check)
        print(f"⚠️ {memory_check}")

    # Validation de episode_oid
    if not episode_oid or not episode_oid.strip():
        raise HTTPException(
            status_code=422, detail="episode_oid is required and cannot be empty"
        )

    # Validation du format episode_oid (ObjectId MongoDB : 24 caractères hexadécimaux)
    if len(episode_oid) != 24 or not all(
        c in "0123456789abcdefABCDEF" for c in episode_oid
    ):
        raise HTTPException(
            status_code=422,
            detail="episode_oid must be a valid MongoDB ObjectId (24 hex characters)",
        )

    try:
        # Récupérer seulement les avis critiques de cet épisode (episode_oid obligatoire)
        avis_critiques = mongodb_service.get_critical_reviews_by_episode_oid(
            episode_oid
        )

        if not avis_critiques:
            return []

        # Phase 1: Vérifier le cache global pour cet episode_oid
        cached_books = livres_auteurs_cache_service.get_books_by_episode_oid(
            episode_oid
        )

        # Utiliser les données du cache ou initialiser une liste vide
        all_books = cached_books or []

        # Phase 1.5: Ramasse-miettes automatique pour livres mongo non corrigés (Issue #67 - Phase 2)
        try:
            cleanup_stats = collections_management_service.cleanup_uncorrected_summaries_for_episode(
                episode_oid
            )
            # Logger les stats pour suivre la progression du cleanup global
            if cleanup_stats["corrected"] > 0:
                print(
                    f"🧹 Cleanup épisode {episode_oid}: {cleanup_stats['corrected']} summaries corrigés"
                )
        except Exception as cleanup_error:
            # Ne pas bloquer l'affichage en cas d'erreur de cleanup
            print(f"⚠️ Erreur cleanup épisode {episode_oid}: {cleanup_error}")

        # Phase 2: Extraction si cache miss global
        if not cached_books:
            try:
                extracted_books = (
                    await books_extraction_service.extract_books_from_reviews(
                        avis_critiques
                    )
                )
                all_books.extend(extracted_books)

            except Exception as extraction_error:
                print(f"⚠️ Erreur extraction: {extraction_error}")
                # En cas d'erreur d'extraction, continuer avec les données du cache uniquement

        # Pas de filtrage - afficher tous les livres (système unifié)
        books_for_frontend = all_books

        # Formater pour l'affichage simplifié
        formatted_books = books_extraction_service.format_books_for_simplified_display(
            books_for_frontend
        )

        return formatted_books

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}") from e


@app.get("/api/episodes-with-reviews", response_model=list[dict[str, Any]])
async def get_episodes_with_reviews() -> list[dict[str, Any]]:
    """Récupère la liste des épisodes qui ont des avis critiques associés."""
    # Vérification mémoire
    memory_check = memory_guard.check_memory_limit()
    if memory_check:
        if "LIMITE MÉMOIRE DÉPASSÉE" in memory_check:
            memory_guard.force_shutdown(memory_check)
        print(f"⚠️ {memory_check}")

    try:
        # Récupérer tous les avis critiques pour obtenir les episode_oid uniques
        avis_critiques = mongodb_service.get_all_critical_reviews()

        # Extraire les episode_oid uniques
        unique_episode_oids = list(
            {avis["episode_oid"] for avis in avis_critiques if avis.get("episode_oid")}
        )

        # Récupérer les détails des épisodes correspondants avec avis_critique_id
        episodes_with_reviews = []
        for episode_oid in unique_episode_oids:
            episode_data = mongodb_service.get_episode_by_id(episode_oid)
            if episode_data:
                episode = Episode(episode_data)
                episode_dict = episode.to_summary_dict()

                # Ajouter l'avis_critique_id correspondant à cet épisode
                avis_critique = next(
                    (
                        avis
                        for avis in avis_critiques
                        if avis["episode_oid"] == episode_oid
                    ),
                    None,
                )
                if avis_critique:
                    episode_dict["avis_critique_id"] = str(avis_critique["_id"])

                # Ajouter le flag has_cached_books pour indiquer si l'épisode a déjà été affiché
                # (présence de livres dans livresauteurs_cache)
                cached_books = livres_auteurs_cache_service.get_books_by_episode_oid(
                    episode_oid
                )
                episode_dict["has_cached_books"] = len(cached_books) > 0

                # Ajouter le flag has_incomplete_books pour identifier les épisodes avec livres non validés
                # (au moins un livre avec status != 'mongo')
                has_incomplete = any(
                    book.get("status") != "mongo" for book in cached_books
                )
                episode_dict["has_incomplete_books"] = has_incomplete

                episodes_with_reviews.append(episode_dict)

        # Trier par date décroissante
        episodes_with_reviews.sort(key=lambda x: x.get("date", ""), reverse=True)

        return episodes_with_reviews

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}") from e


@app.post("/api/verify-babelio", response_model=dict[str, Any])
async def verify_babelio(request: BabelioVerificationRequest) -> dict[str, Any]:
    """Vérifie et corrige l'orthographe via le service Babelio."""
    # Vérification mémoire
    memory_check = memory_guard.check_memory_limit()
    if memory_check:
        if "LIMITE MÉMOIRE DÉPASSÉE" in memory_check:
            memory_guard.force_shutdown(memory_check)
        print(f"⚠️ {memory_check}")

    try:
        if request.type == "author":
            if not request.name:
                raise HTTPException(
                    status_code=400, detail="Le nom de l'auteur est requis"
                )
            result = await babelio_service.verify_author(request.name)

        elif request.type == "book":
            if not request.title:
                raise HTTPException(
                    status_code=400, detail="Le titre du livre est requis"
                )
            result = await babelio_service.verify_book(request.title, request.author)

        elif request.type == "publisher":
            if not request.name:
                raise HTTPException(
                    status_code=400, detail="Le nom de l'éditeur est requis"
                )
            result = await babelio_service.verify_publisher(request.name)

        else:
            raise HTTPException(
                status_code=400,
                detail="Type invalide. Doit être 'author', 'book' ou 'publisher'",
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}") from e


@app.post("/api/set-validation-results", response_model=dict[str, Any])
async def set_validation_results(request: ValidationResultsRequest) -> dict[str, Any]:
    """Reçoit les résultats de validation biblio du frontend et les stocke."""
    # Vérification mémoire
    memory_check = memory_guard.check_memory_limit()
    if memory_check:
        if "LIMITE MÉMOIRE DÉPASSÉE" in memory_check:
            memory_guard.force_shutdown(memory_check)
        print(f"⚠️ {memory_check}")

    try:
        books_processed = 0

        for book_result in request.books:
            # Convertir le statut de validation frontend vers statut cache unifié
            if book_result.validation_status == "verified":
                cache_status = "verified"
            elif book_result.validation_status == "suggestion":
                cache_status = "suggested"
            else:  # not_found
                cache_status = "not_found"

            # Préparer les données pour le cache
            book_data = {
                "episode_oid": request.episode_oid,
                "auteur": book_result.auteur,
                "titre": book_result.titre,
                "editeur": book_result.editeur,
                "programme": book_result.programme,
                "status": cache_status,
            }

            # Ajouter les suggestions si disponibles
            if book_result.suggested_author:
                book_data["suggested_author"] = book_result.suggested_author
            if book_result.suggested_title:
                book_data["suggested_title"] = book_result.suggested_title

            # Issue #85: Ajouter les enrichissements Babelio si disponibles
            if book_result.babelio_url:
                book_data["babelio_url"] = book_result.babelio_url
            if book_result.babelio_publisher:
                book_data["babelio_publisher"] = book_result.babelio_publisher

            # Créer l'entrée cache
            from bson import ObjectId

            avis_critique_id = ObjectId(request.avis_critique_id)
            cache_entry_id = livres_auteurs_cache_service.create_cache_entry(
                avis_critique_id, book_data
            )

            # Auto-processing pour les livres verified
            if cache_status == "verified":
                try:
                    # Utiliser le nom validé (suggested_author si disponible, sinon auteur original)
                    validated_author = (
                        book_result.suggested_author or book_result.auteur
                    )
                    validated_title = book_result.suggested_title or book_result.titre

                    # Créer auteur en base
                    author_id = mongodb_service.create_author_if_not_exists(
                        validated_author
                    )

                    # Créer livre en base
                    # Issue #85: Utiliser babelio_publisher si disponible (source plus fiable)
                    editeur_value = book_result.babelio_publisher or book_result.editeur
                    book_data_for_mongo = {
                        "titre": validated_title,
                        "auteur_id": author_id,
                        "editeur": editeur_value,
                        "episodes": [request.episode_oid],
                        "avis_critiques": [request.avis_critique_id],
                    }
                    book_id = mongodb_service.create_book_if_not_exists(
                        book_data_for_mongo
                    )

                    # Issue #85: Passer babelio_publisher en metadata pour écraser editeur dans le cache
                    # C'est la source la plus fiable (enrichissement Babelio)
                    cache_metadata = {}
                    if book_result.babelio_publisher:
                        cache_metadata["babelio_publisher"] = (
                            book_result.babelio_publisher
                        )

                    # Marquer comme traité (mongo) avec metadata pour override cache editeur
                    livres_auteurs_cache_service.mark_as_processed(
                        cache_entry_id, author_id, book_id, metadata=cache_metadata
                    )

                    # Issue #85: Mettre à jour l'avis_critique avec le nouvel éditeur enrichi par Babelio
                    # Mettre à jour le summary markdown pour remplacer l'ancien éditeur par le nouvel
                    if (
                        book_result.babelio_publisher
                        and book_result.babelio_publisher != book_result.editeur
                    ):
                        print(
                            f"📝 [Issue #85] Updating avis_critique {request.avis_critique_id} with Babelio publisher={book_result.babelio_publisher}"
                        )

                        # Récupérer l'avis critique actuel pour accéder au summary
                        avis_critique = mongodb_service.get_avis_critique_by_id(
                            request.avis_critique_id
                        )
                        if avis_critique:
                            # Importer la fonction pour mettre à jour le summary
                            from .utils.summary_updater import replace_book_in_summary

                            # Mettre à jour le summary markdown avec le nouvel éditeur
                            original_summary = avis_critique.get("summary", "")
                            updated_summary = replace_book_in_summary(
                                summary=original_summary,
                                original_author=book_result.auteur,
                                original_title=book_result.titre,
                                corrected_author=book_result.auteur,  # Pas de changement d'auteur
                                corrected_title=book_result.titre,  # Pas de changement de titre
                                original_publisher=book_result.editeur,
                                corrected_publisher=book_result.babelio_publisher,
                            )

                            # Mettre à jour l'avis_critique avec le summary et l'éditeur mis à jour
                            mongodb_service.update_avis_critique(
                                request.avis_critique_id,
                                {
                                    "summary": updated_summary,
                                    "editeur": book_result.babelio_publisher,
                                },
                            )
                            print("   ✅ Summary and editeur updated in avis_critique")

                except Exception as auto_processing_error:
                    # Ne pas faire échouer l'endpoint si l'auto-processing échoue
                    print(
                        f"⚠️ Erreur auto-processing pour {book_result.auteur}: {auto_processing_error}"
                    )

            books_processed += 1

        return {"success": True, "books_processed": books_processed}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}") from e


def extract_ngrams(text: str, n: int) -> list[str]:
    """
    Extrait des séquences de n mots consécutifs.

    Args:
        text: Le texte source
        n: Le nombre de mots par n-gram

    Returns:
        Liste des n-grams extraits

    Example:
        >>> extract_ngrams("L'invention de Tristan", 2)
        ["L'invention de", "de Tristan"]
    """
    words = text.split()
    if len(words) < n:
        return []
    return [" ".join(words[i : i + n]) for i in range(len(words) - n + 1)]


def smart_fuzzy_score(query: str, candidate: str) -> float:
    """
    Scorer intelligent qui pénalise les matches partiels trop courts.

    Problème avec ratio/WRatio : "Adrien" vs "Adrien Bosc" pour query "Adrien Bosque"
    - "Adrien" → score élevé (petit dénominateur)
    - "Adrien Bosc" → score plus bas (dénominateur plus grand)

    Solution : Utiliser token_sort_ratio ET pénaliser si le candidat est trop court
    par rapport à la query.
    """
    # Score de base avec token_sort_ratio (ignore l'ordre des mots)
    base_score: float = float(fuzz.token_sort_ratio(query, candidate))

    # Pénalité si le candidat est significativement plus court que la query
    query_len = len(query)
    candidate_len = len(candidate)

    # Si le candidat est < 60% de la longueur de la query, appliquer une pénalité
    if candidate_len < query_len * 0.6:
        # Pénalité proportionnelle à la différence de longueur
        length_ratio = candidate_len / query_len
        penalty = (1 - length_ratio) * 15  # Pénalité max 15 points
        return float(max(0, base_score - penalty))

    return float(base_score)


@app.post("/api/fuzzy-search-episode", response_model=dict[str, Any])
async def fuzzy_search_episode(request: FuzzySearchRequest) -> dict[str, Any]:
    """Recherche fuzzy dans le titre et description d'un épisode."""
    # Vérification mémoire
    memory_check = memory_guard.check_memory_limit()
    if memory_check:
        if "LIMITE MÉMOIRE DÉPASSÉE" in memory_check:
            memory_guard.force_shutdown(memory_check)
        print(f"⚠️ {memory_check}")

    try:
        # Récupérer l'épisode
        episode_data = mongodb_service.get_episode_by_id(request.episode_id)
        if not episode_data:
            raise HTTPException(status_code=404, detail="Épisode non trouvé")

        episode = Episode(episode_data)

        # Combiner titre et description pour la recherche
        full_text = f"{episode.titre} {episode.description}"

        # Nettoyer et diviser le texte en mots/segments
        import re

        # Extraire segments entre guillemets (priorité haute - titres potentiels)
        quoted_segments = re.findall(r'"([^"]+)"', full_text)

        # NOUVEAU : Extraire n-grams de différentes tailles (Issue #76)
        # Pour détecter les titres multi-mots comme "L'invention de Tristan"
        bigrams = extract_ngrams(full_text, 2)  # "L'invention de", "de Tristan"
        trigrams = extract_ngrams(full_text, 3)  # "L'invention de Tristan"
        quadrigrams = extract_ngrams(full_text, 4)  # "L'invention de Tristan Adrien"

        # Extraire mots individuels de plus de 3 caractères
        words = [word for word in full_text.split() if len(word) > 3]

        # Nettoyer les mots (enlever ponctuation)
        clean_words = [re.sub(r"[^\w\-\'àâäéèêëïîôöùûüÿç]", "", word) for word in words]
        clean_words = [word for word in clean_words if len(word) > 3]

        # Candidats par priorité : guillemets > 4-grams > 3-grams > 2-grams > mots
        # Filtrer n-grams trop courts pour éviter le bruit
        search_candidates = (
            quoted_segments
            + [ng for ng in quadrigrams if len(ng) > 10]  # Filtrer n-grams courts
            + [ng for ng in trigrams if len(ng) > 8]
            + [ng for ng in bigrams if len(ng) > 6]
            + clean_words
        )

        # Recherche fuzzy pour le titre
        # D'abord chercher dans les segments entre guillemets (priorité haute)
        quoted_matches = (
            process.extract(
                request.query_title, quoted_segments, scorer=smart_fuzzy_score, limit=5
            )
            if quoted_segments
            else []
        )

        # Puis chercher dans tous les candidats
        all_matches = process.extract(
            request.query_title, search_candidates, scorer=smart_fuzzy_score, limit=10
        )

        # Retourner TOUS les segments entre guillemets (potentiels titres) + bons matches généraux
        title_matches = []

        # Ajouter tous les segments entre guillemets avec marqueur 📖
        if quoted_matches:
            title_matches.extend(
                [("📖 " + match, score) for match, score in quoted_matches]
            )

        # Ajouter les autres bons matches généraux (seuil plus strict)
        title_matches.extend(
            [
                (match, score)
                for match, score in all_matches
                if score >= 60 and match not in [q[0] for q in quoted_matches]
            ]
        )

        # Recherche fuzzy pour l'auteur (si fourni)
        author_matches = []
        if request.query_author:
            author_matches_raw = process.extract(
                request.query_author,
                search_candidates,
                scorer=smart_fuzzy_score,
                limit=10,
            )
            # Filtrer manuellement par score
            author_matches = [
                (match, score) for match, score in author_matches_raw if score >= 75
            ]

        # Nettoyer la ponctuation en fin de chaîne pour tous les matches
        def clean_trailing_punctuation(text: str) -> str:
            """Nettoie la ponctuation en fin de chaîne (virgules, points, etc.)"""
            return text.rstrip(",.;:!? ")

        title_matches = [
            (clean_trailing_punctuation(match), score) for match, score in title_matches
        ]
        author_matches = [
            (clean_trailing_punctuation(match), score)
            for match, score in author_matches
        ]

        # Trier les résultats par score décroissant
        title_matches.sort(key=lambda x: x[1], reverse=True)
        author_matches.sort(key=lambda x: x[1], reverse=True)

        return {
            "episode_id": request.episode_id,
            "episode_title": episode.titre,
            "query_title": request.query_title,
            "query_author": request.query_author,
            "title_matches": title_matches,
            "author_matches": author_matches,
            "found_suggestions": len(title_matches) > 0 or len(author_matches) > 0,
            "debug_candidates": search_candidates[:10],  # Pour debug
            "debug_quoted_matches": quoted_matches[:3]
            if quoted_matches
            else [],  # Pour debug
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}") from e


@app.get("/api/search", response_model=dict[str, Any])
async def search_text(q: str, limit: int = 10) -> dict[str, Any]:
    """Recherche textuelle multi-entités avec support de recherche floue."""
    # Vérification mémoire
    memory_check = memory_guard.check_memory_limit()
    if memory_check:
        if "LIMITE MÉMOIRE DÉPASSÉE" in memory_check:
            memory_guard.force_shutdown(memory_check)
        print(f"⚠️ {memory_check}")

    # Validation des paramètres
    if len(q.strip()) < 3:
        raise HTTPException(
            status_code=400,
            detail="La recherche nécessite au moins 3 caractères minimum",
        )

    if limit < 1 or limit > 100:
        raise HTTPException(
            status_code=400, detail="La limite doit être entre 1 et 100"
        )

    try:
        # Recherche dans les épisodes
        episodes_search_result = mongodb_service.search_episodes(q, limit)
        episodes_list = episodes_search_result.get("episodes", [])
        episodes_total_count = episodes_search_result.get("total_count", 0)

        # Recherche dans les collections dédiées auteurs et livres
        auteurs_search_result = mongodb_service.search_auteurs(q, limit)
        auteurs_list = auteurs_search_result.get("auteurs", [])
        auteurs_total_count = auteurs_search_result.get("total_count", 0)

        livres_search_result = mongodb_service.search_livres(q, limit)
        livres_list = livres_search_result.get("livres", [])
        livres_total_count = livres_search_result.get("total_count", 0)

        # Recherche dans les avis critiques (pour éditeurs et backup)
        critical_reviews_results = (
            mongodb_service.search_critical_reviews_for_authors_books(q, limit)
        )

        # Structure de la réponse - utilise les collections dédiées en priorité
        response = {
            "query": q,
            "results": {
                "auteurs": auteurs_list,
                "auteurs_total_count": auteurs_total_count,
                "livres": livres_list,
                "livres_total_count": livres_total_count,
                "editeurs": critical_reviews_results["editeurs"],
                "episodes": [
                    {
                        "titre": episode.get("titre_corrige")
                        or episode.get("titre", ""),
                        "description": episode.get("description_corrigee")
                        or episode.get("description", ""),
                        "date": episode.get("date", ""),
                        "score": episode.get("score", 0),
                        "match_type": episode.get("match_type", "none"),
                        "search_context": episode.get("search_context", ""),
                        "_id": episode.get("_id", ""),
                    }
                    for episode in episodes_list
                ],
                "episodes_total_count": episodes_total_count,
            },
        }

        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}") from e


@app.get("/api/advanced-search", response_model=dict[str, Any])
async def advanced_search(
    q: str,
    entities: str | None = None,
    page: int = 1,
    limit: int = 20,
) -> dict[str, Any]:
    """
    Recherche avancée avec filtres par entités et pagination.

    Args:
        q: Terme de recherche (minimum 3 caractères)
        entities: Entités à rechercher (auteurs,livres,editeurs,episodes) séparées par virgule
                 Si None, recherche dans toutes les entités
        page: Numéro de page (commence à 1)
        limit: Nombre de résultats par page (max 100)

    Returns:
        Résultats de recherche avec pagination et compteurs totaux
    """
    # Vérification mémoire
    memory_check = memory_guard.check_memory_limit()
    if memory_check:
        if "LIMITE MÉMOIRE DÉPASSÉE" in memory_check:
            memory_guard.force_shutdown(memory_check)
        print(f"⚠️ {memory_check}")

    # Validation des paramètres
    if len(q.strip()) < 3:
        raise HTTPException(
            status_code=400,
            detail="La recherche nécessite au moins 3 caractères minimum",
        )

    if page < 1:
        raise HTTPException(status_code=400, detail="Le numéro de page doit être >= 1")

    if limit < 1 or limit > 100:
        raise HTTPException(
            status_code=400, detail="La limite doit être entre 1 et 100"
        )

    # Parser les entités demandées
    valid_entities = {"auteurs", "livres", "editeurs", "episodes"}
    requested_entities = valid_entities.copy()  # Par défaut, toutes les entités

    if entities:
        requested_entities = {
            entity.strip() for entity in entities.split(",") if entity.strip()
        }
        # Valider que les entités sont valides
        invalid_entities = requested_entities - valid_entities
        if invalid_entities:
            raise HTTPException(
                status_code=400,
                detail=f"Entité invalide: {', '.join(invalid_entities)}. "
                f"Entités valides: {', '.join(valid_entities)}",
            )

    try:
        # Calculer l'offset pour la pagination
        offset = (page - 1) * limit

        # Initialiser les résultats
        results: dict[str, Any] = {
            "auteurs": [],
            "auteurs_total_count": 0,
            "livres": [],
            "livres_total_count": 0,
            "editeurs": [],
            "editeurs_total_count": 0,
            "episodes": [],
            "episodes_total_count": 0,
        }

        # Rechercher dans les entités demandées avec offset et limit
        if "episodes" in requested_entities:
            episodes_search_result = mongodb_service.search_episodes(q, limit, offset)
            episodes_list = episodes_search_result.get("episodes", [])
            results["episodes"] = [
                {
                    "titre": episode.get("titre_corrige") or episode.get("titre", ""),
                    "description": episode.get("description_corrigee")
                    or episode.get("description", ""),
                    "date": episode.get("date", ""),
                    "score": episode.get("score", 0),
                    "match_type": episode.get("match_type", "none"),
                    "search_context": episode.get("search_context", ""),
                    "_id": episode.get("_id", ""),
                }
                for episode in episodes_list
            ]
            results["episodes_total_count"] = episodes_search_result.get(
                "total_count", 0
            )

        if "auteurs" in requested_entities:
            auteurs_search_result = mongodb_service.search_auteurs(q, limit, offset)
            results["auteurs"] = auteurs_search_result.get("auteurs", [])
            results["auteurs_total_count"] = auteurs_search_result.get("total_count", 0)

        if "livres" in requested_entities:
            livres_search_result = mongodb_service.search_livres(q, limit, offset)
            results["livres"] = livres_search_result.get("livres", [])
            results["livres_total_count"] = livres_search_result.get("total_count", 0)

        if "editeurs" in requested_entities:
            # Recherche dans la collection editeurs
            editeurs_search_result = mongodb_service.search_editeurs(q, limit, offset)
            results["editeurs"] = editeurs_search_result.get("editeurs", [])
            results["editeurs_total_count"] = editeurs_search_result.get(
                "total_count", 0
            )

        # Calculer le nombre total de pages (basé sur la plus grande collection)
        max_total = max(
            results["episodes_total_count"],
            results["auteurs_total_count"],
            results["livres_total_count"],
            results["editeurs_total_count"],
        )
        total_pages = (max_total + limit - 1) // limit if max_total > 0 else 1

        response = {
            "query": q,
            "results": results,
            "pagination": {"page": page, "limit": limit, "total_pages": total_pages},
        }

        return response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}") from e


@app.post("/api/update-fixtures", response_model=dict[str, Any])
async def update_fixtures(request: FixtureUpdateRequest) -> dict[str, Any]:
    """Met à jour les fixtures YAML avec les appels API capturés."""
    # Vérification mémoire
    memory_check = memory_guard.check_memory_limit()
    if memory_check:
        if "LIMITE MÉMOIRE DÉPASSÉE" in memory_check:
            memory_guard.force_shutdown(memory_check)
        print(f"⚠️ {memory_check}")

    try:
        updater = FixtureUpdaterService()
        result = updater.update_from_captured_calls(
            [call.model_dump() for call in request.calls]
        )

        return {
            "success": True,
            "updated_files": result.updated_files,
            "added_cases": result.added_cases,
            "updated_cases": result.updated_cases,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}") from e


# Nouveaux endpoints pour l'Issue #66 - Gestion des collections auteurs/livres


@app.get("/api/livres-auteurs/statistics", response_model=dict[str, Any])
async def get_livres_auteurs_statistics() -> dict[str, Any]:
    """Récupère les statistiques pour la page livres-auteurs."""
    # Vérification mémoire
    memory_check = memory_guard.check_memory_limit()
    if memory_check:
        if "LIMITE MÉMOIRE DÉPASSÉE" in memory_check:
            memory_guard.force_shutdown(memory_check)
        print(f"⚠️ {memory_check}")

    try:
        stats = collections_management_service.get_statistics()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}") from e


@app.post("/api/livres-auteurs/auto-process-verified", response_model=dict[str, Any])
async def auto_process_verified_books() -> dict[str, Any]:
    """Traite automatiquement les livres avec statut 'verified'."""
    # Vérification mémoire
    memory_check = memory_guard.check_memory_limit()
    if memory_check:
        if "LIMITE MÉMOIRE DÉPASSÉE" in memory_check:
            memory_guard.force_shutdown(memory_check)
        print(f"⚠️ {memory_check}")

    try:
        result = collections_management_service.auto_process_verified_books()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}") from e


@app.get("/api/livres-auteurs/books/{status}", response_model=list[dict[str, Any]])
async def get_books_by_validation_status(status: str) -> list[dict[str, Any]]:
    """Récupère les livres par statut de validation."""
    # Vérification mémoire
    memory_check = memory_guard.check_memory_limit()
    if memory_check:
        if "LIMITE MÉMOIRE DÉPASSÉE" in memory_check:
            memory_guard.force_shutdown(memory_check)
        print(f"⚠️ {memory_check}")

    try:
        books = collections_management_service.get_books_by_validation_status(status)
        return books
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}") from e


@app.post("/api/livres-auteurs/validate-suggestion", response_model=dict[str, Any])
async def validate_suggestion(request: ValidateSuggestionRequest) -> dict[str, Any]:
    """Valide manuellement une suggestion d'auteur/livre."""
    # Vérification mémoire
    memory_check = memory_guard.check_memory_limit()
    if memory_check:
        if "LIMITE MÉMOIRE DÉPASSÉE" in memory_check:
            memory_guard.force_shutdown(memory_check)
        print(f"⚠️ {memory_check}")

    try:
        result = collections_management_service.handle_book_validation(
            request.model_dump()
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}") from e


@app.delete(
    "/api/livres-auteurs/cache/episode/{episode_oid}", response_model=dict[str, Any]
)
async def delete_cache_by_episode(episode_oid: str) -> dict[str, Any]:
    """Supprime toutes les entrées de cache pour un épisode donné."""
    try:
        deleted_count = livres_auteurs_cache_service.delete_cache_by_episode(
            episode_oid
        )
        return {"deleted_count": deleted_count, "episode_oid": episode_oid}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}") from e


# Note: add_manual_book endpoint removed - functionality unified with validate_suggestion


@app.get("/api/authors", response_model=list[dict[str, Any]])
async def get_all_authors() -> list[dict[str, Any]]:
    """Récupère tous les auteurs de la collection."""
    # Vérification mémoire
    memory_check = memory_guard.check_memory_limit()
    if memory_check:
        if "LIMITE MÉMOIRE DÉPASSÉE" in memory_check:
            memory_guard.force_shutdown(memory_check)
        print(f"⚠️ {memory_check}")

    try:
        authors = collections_management_service.get_all_authors()
        return authors
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}") from e


@app.get("/api/books", response_model=list[dict[str, Any]])
async def get_all_books() -> list[dict[str, Any]]:
    """Récupère tous les livres de la collection."""
    # Vérification mémoire
    memory_check = memory_guard.check_memory_limit()
    if memory_check:
        if "LIMITE MÉMOIRE DÉPASSÉE" in memory_check:
            memory_guard.force_shutdown(memory_check)
        print(f"⚠️ {memory_check}")

    try:
        books = collections_management_service.get_all_books()
        return books
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}") from e


@app.get("/api/stats", response_model=dict[str, int])
async def get_cache_statistics() -> dict[str, int] | JSONResponse:
    """Récupère les statistiques de base du cache livres/auteurs."""
    try:
        return stats_service.get_cache_statistics()
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/stats/detailed", response_model=list[dict[str, Any]])
async def get_detailed_breakdown() -> list[dict[str, Any]] | JSONResponse:
    """Récupère la répartition détaillée par biblio_verification_status."""
    try:
        result = stats_service.get_detailed_breakdown()
        return list(result) if result else []
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/stats/recent", response_model=list[dict[str, Any]])
async def get_recent_processed_books(
    limit: int = 10,
) -> list[dict[str, Any]] | JSONResponse:
    """Récupère les livres récemment auto-traités."""
    try:
        result = stats_service.get_recent_processed_books(limit)
        return list(result) if result else []
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/stats/summary")
async def get_human_readable_summary() -> Response:
    """Récupère un résumé lisible des statistiques."""
    try:
        summary = stats_service.get_human_readable_summary()
        return Response(content=summary, media_type="text/plain; charset=utf-8")
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/stats/validation", response_model=list[dict[str, Any]])
async def get_validation_status_breakdown() -> list[dict[str, Any]] | JSONResponse:
    """Récupère la répartition par validation_status."""
    try:
        result = stats_service.get_validation_status_breakdown()
        return list(result) if result else []
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/openapi_reduced.json")
async def openapi_reduced() -> JSONResponse:
    """Retourne une version allégée de la spec OpenAPI (chemins, méthodes, summary, params, responses).

    Utile pour un client qui veut lister rapidement les endpoints et leurs usages sans charger
    toute la définition des schémas.
    """
    try:
        schema = app.openapi()

        reduced: dict[str, object] = {
            "openapi": schema.get("openapi"),
            "info": {
                "title": schema.get("info", {}).get("title"),
                "version": schema.get("info", {}).get("version"),
            },
            "paths": {},
        }

        for path, methods in (schema.get("paths") or {}).items():
            reduced_methods: dict[str, object] = {}
            for method, op in methods.items():
                params = []
                for p in op.get("parameters", []) if op.get("parameters") else []:
                    p_schema = p.get("schema", {})
                    params.append(
                        {
                            "name": p.get("name"),
                            "in": p.get("in"),
                            "required": p.get("required", False),
                            "type": p_schema.get("type"),
                        }
                    )

                responses = {
                    status: (resp.get("description") if isinstance(resp, dict) else "")
                    for status, resp in (op.get("responses") or {}).items()
                }

                reduced_methods[method] = {
                    "summary": op.get("summary"),
                    "description": op.get("description"),
                    "tags": op.get("tags", []),
                    "parameters": params,
                    "responses": responses,
                }

            paths_dict = reduced["paths"]
            assert isinstance(paths_dict, dict)
            paths_dict[path] = reduced_methods

        return JSONResponse(content=reduced)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


# Variables globales pour la gestion propre du serveur
_server_instance = None


def signal_handler(signum, frame):
    """Gestionnaire de signaux pour arrêt propre."""
    print(f"\n🛑 Signal {signum} reçu - Arrêt en cours...")

    # Arrêter le serveur proprement si disponible
    if _server_instance is not None:
        _server_instance.should_exit = True
        print("📡 Signal d'arrêt envoyé au serveur")

    # Forcer la fermeture des ressources
    with suppress(Exception):
        mongodb_service.disconnect()
        print("🔌 MongoDB déconnecté")

    # Nettoyer le fichier de découverte de port unifié
    with suppress(Exception):
        port_file = PortDiscovery.get_unified_port_file_path()
        PortDiscovery.cleanup_unified_port_file(port_file)
        print("🧹 Unified port discovery file cleaned up")


def find_free_port_or_default() -> int:
    """Find a free port using priority strategy.

    Priority order:
    1. Environment variable API_PORT if specified (current behavior)
    2. Default preferred port 54321 (try first)
    3. Fallback range 54322-54350 (scan for first available)

    Returns:
        Available port number

    Raises:
        ValueError: If environment variable contains invalid port number
        RuntimeError: If no available port is found in the range
    """
    # 1. Check environment variable first
    if "API_PORT" in os.environ:
        api_port_str = os.getenv("API_PORT")
        if api_port_str is None:
            # Should not happen since we checked the key exists, but satisfy mypy
            raise ValueError("API_PORT environment variable is None")
        try:
            return int(api_port_str)
        except (TypeError, ValueError) as e:
            raise ValueError(
                f"Invalid API_PORT environment variable: {api_port_str}"
            ) from e

    # Get the same host that will be used by the server
    host = os.getenv("API_HOST", "0.0.0.0")

    # 2. Try preferred default port 54321
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((host, 54321))
            return 54321
    except OSError:
        # Port 54321 is occupied, continue to fallback range
        pass

    # 3. Scan fallback range 54322-54350 (29 attempts)
    return PortDiscovery.find_available_port(
        start_port=54322, max_attempts=29, host=host
    )


def main():
    """Fonction principale pour démarrer le serveur."""
    global _server_instance

    import signal

    import uvicorn

    # Enregistrer les gestionnaires de signaux
    signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # Termination

    host = os.getenv("API_HOST", "0.0.0.0")
    port = find_free_port_or_default()

    # Determine if port was automatically selected
    port_auto_selected = "API_PORT" not in os.environ
    port_message = f"🚀 Démarrage du serveur sur {host}:{port}"
    if port_auto_selected:
        port_message += " (port automatiquement sélectionné)"

    print(port_message)
    print("🛡️ Garde-fou mémoire activé")

    # Create unified port discovery file for frontend
    port_file = PortDiscovery.get_unified_port_file_path()
    PortDiscovery.write_backend_info_to_unified_file(port_file, port, host)
    print(f"📡 Unified port discovery file created: {port_file}")

    try:
        # Créer la configuration uvicorn avec des paramètres pour un arrêt propre
        config = uvicorn.Config(
            app,
            host=host,
            port=port,
            access_log=False,
            server_header=False,
            date_header=False,
            lifespan="on",
            # Paramètres pour un arrêt plus propre
            timeout_keep_alive=5,
            timeout_graceful_shutdown=10,
        )

        # Créer le serveur et le garder en référence globale
        _server_instance = uvicorn.Server(config)

        # Démarrer le serveur
        _server_instance.run()

    except KeyboardInterrupt:
        print("\n⚠️ Interruption clavier détectée")
    except Exception as e:
        print(f"❌ Erreur serveur: {e}")
    finally:
        # Nettoyage final garanti
        print("🧹 Nettoyage final...")
        with suppress(Exception):
            mongodb_service.disconnect()
        with suppress(Exception):
            port_file = PortDiscovery.get_unified_port_file_path()
            PortDiscovery.cleanup_unified_port_file(port_file)
        print("✅ Arrêt complet")


if __name__ == "__main__":
    main()
