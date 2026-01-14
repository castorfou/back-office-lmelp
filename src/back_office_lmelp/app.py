"""Application FastAPI principale."""

# CRITIQUE (Issue #171): Charger .env AVANT tous les imports de services
# Les singletons lisent os.getenv() dans __init__() au moment de l'import
# Si load_dotenv() n'est pas appelé avant, toutes les variables sont vides
from dotenv import load_dotenv  # noqa: E402, I001

load_dotenv()

# ruff: noqa: E402
# Justification: load_dotenv() DOIT être appelé avant tous les imports de services
# car les singletons lisent les variables d'environnement dans __init__()
import logging  # noqa: I001

# Configure logging AVANT les imports pour voir les logs d'initialisation des services
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

import os
import re
import socket
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, suppress
from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel
from rapidfuzz import fuzz
from thefuzz import process

from .middleware import EnrichedLoggingMiddleware
from .models.critique import Critique
from .models.emission import Emission
from .models.episode import Episode
from .services.avis_critiques_generation_service import (
    avis_critiques_generation_service,
)
from .services.babelio_cache_service import BabelioCacheService
from .services.babelio_migration_service import BabelioMigrationService
from .services.babelio_service import babelio_service
from .services.books_extraction_service import books_extraction_service
from .services.calibre_service import calibre_service
from .services.collections_management_service import collections_management_service
from .services.critiques_extraction_service import critiques_extraction_service
from .services.duplicate_books_service import DuplicateBooksService
from .services.fixture_updater import FixtureUpdaterService
from .services.livres_auteurs_cache_service import livres_auteurs_cache_service
from .services.mongodb_service import mongodb_service
from .services.radiofrance_service import RadioFranceService
from .services.stats_service import stats_service
from .utils.memory_guard import memory_guard
from .utils.port_discovery import PortDiscovery


logger = logging.getLogger(__name__)


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


# Modèles pour la génération d'avis critiques (Issue #171)
class GenerateAvisCritiquesRequest(BaseModel):
    """Modèle pour la génération d'avis critiques."""

    episode_id: str


class GenerateAvisCritiquesResponse(BaseModel):
    """Modèle pour la réponse de génération d'avis critiques."""

    success: bool
    summary: str
    summary_phase1: str
    metadata: dict[str, Any]
    corrections_applied: list[dict[str, Any]]
    warnings: list[str]


class SaveAvisCritiquesRequest(BaseModel):
    """Modèle pour la sauvegarde d'avis critiques."""

    episode_id: str
    summary: str
    summary_phase1: str
    metadata: dict[str, Any]


# Nouveaux modèles pour la migration Babelio (Issue #124)
class AcceptSuggestionRequest(BaseModel):
    """Modèle pour accepter une suggestion Babelio."""

    livre_id: str
    babelio_url: str
    babelio_author_url: str | None = None
    corrected_title: str | None = None


class MarkNotFoundRequest(BaseModel):
    """Modèle pour marquer un livre ou auteur comme non trouvé sur Babelio."""

    item_id: str
    reason: str
    item_type: str = "livre"  # "livre" ou "auteur"


class CorrectTitleRequest(BaseModel):
    """Modèle pour corriger le titre d'un livre."""

    livre_id: str
    new_title: str


class RetryWithTitleRequest(BaseModel):
    """Modèle pour réessayer une recherche avec un nouveau titre."""

    livre_id: str
    new_title: str
    author: str | None = None


class UpdateFromBabelioUrlRequest(BaseModel):
    """Modèle pour mettre à jour depuis une URL Babelio manuelle."""

    item_id: str
    babelio_url: str
    item_type: str = "livre"  # "livre" ou "auteur"


class ExtractFromBabelioUrlRequest(BaseModel):
    """Modèle pour extraire les données depuis une URL Babelio (Issue #159)."""

    babelio_url: str


class MergeDuplicateGroupRequest(BaseModel):
    """Modèle pour fusionner un groupe de doublons (Issue #178)."""

    url_babelio: str
    book_ids: list[str]


class MergeBatchRequest(BaseModel):
    """Modèle pour fusionner en batch avec skip list (Issue #178)."""

    skip_list: list[str] = []


class MergeDuplicateAuthorsRequest(BaseModel):
    """Modèle pour fusionner un groupe d'auteurs en doublon (Issue #178)."""

    url_babelio: str
    auteur_ids: list[str]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Gestion du cycle de vie de l'application."""
    try:
        # Afficher les informations de démarrage (Issue #136)
        from .utils.startup_logging import log_startup_info

        log_startup_info()

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

# Initialize migration service (Issue #124)
babelio_migration_service = BabelioMigrationService(
    mongodb_service=mongodb_service,
    babelio_service=babelio_service,
)

# Initialize duplicate books service (Issue #178)
duplicate_books_service = DuplicateBooksService(
    mongodb_service=mongodb_service,
    babelio_service=babelio_service,
)

# Configure logging for enriched access logs (Issue #115)
access_logger = logging.getLogger("back_office_lmelp.access")
access_logger.setLevel(logging.INFO)
# Add console handler if not already present
if not access_logger.handlers:
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    access_logger.addHandler(console_handler)
    access_logger.propagate = False  # Éviter la duplication avec le logger root


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

# Add enriched logging middleware (Issue #115)
app.add_middleware(EnrichedLoggingMiddleware)


@app.get("/")
async def root() -> dict[str, str]:
    """Point d'entrée de l'API."""
    return {"message": "Back-office LMELP API", "version": "0.1.0"}


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint for Docker healthchecks (Issue #115).

    This endpoint is designed for automated monitoring and Docker healthchecks.
    It returns a simple status without database connectivity check to keep
    response time minimal and avoid polluting logs.
    """
    return {"status": "ok"}


@app.get("/debug/azure-config")
async def debug_azure_config() -> dict[str, Any]:
    """Debug endpoint pour vérifier la configuration Azure OpenAI (Issue #171).

    TEMPORAIRE - À supprimer après résolution du problème.
    """
    return {
        "env_vars": {
            "AZURE_ENDPOINT": os.getenv("AZURE_ENDPOINT", "NOT_SET"),
            "AZURE_API_KEY": (
                "***" + os.getenv("AZURE_API_KEY", "NOT_SET")[-4:]
                if os.getenv("AZURE_API_KEY")
                else "NOT_SET"
            ),
            "AZURE_API_VERSION": os.getenv("AZURE_API_VERSION", "NOT_SET"),
            "AZURE_DEPLOYMENT_NAME": os.getenv("AZURE_DEPLOYMENT_NAME", "NOT_SET"),
        },
        "service_instance": {
            "azure_endpoint": avis_critiques_generation_service.azure_endpoint
            or "None",
            "api_key_set": bool(avis_critiques_generation_service.api_key),
            "api_version": avis_critiques_generation_service.api_version or "None",
            "deployment_name": avis_critiques_generation_service.deployment_name
            or "None",
            "client_initialized": avis_critiques_generation_service.client is not None,
        },
    }


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


@app.get("/api/episodes/all", response_model=list[dict[str, Any]])
async def get_all_episodes_including_masked() -> list[dict[str, Any]]:
    """Récupère tous les épisodes y compris les masqués (Issue #107).

    Cette route est utilisée par la page de gestion des épisodes masqués.
    """
    # Vérification mémoire
    memory_check = memory_guard.check_memory_limit()
    if memory_check:
        if "LIMITE MÉMOIRE DÉPASSÉE" in memory_check:
            memory_guard.force_shutdown(memory_check)
        print(f"⚠️ {memory_check}")

    try:
        episodes_data = mongodb_service.get_all_episodes(include_masked=True)
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

        # Récupérer la date de l'épisode
        # CRITIQUE: MongoDB retourne datetime.datetime, PAS une chaîne ISO
        # Convertir en YYYY-MM-DD pour RadioFranceService
        episode_date_raw = episode_data.get("date", None)
        episode_date = None
        if episode_date_raw:
            # MongoDB retourne datetime.datetime → convertir en "YYYY-MM-DD"
            if isinstance(episode_date_raw, datetime):
                episode_date = episode_date_raw.strftime("%Y-%m-%d")
            else:
                # Fallback si string (ne devrait pas arriver avec vraie DB)
                date_str = str(episode_date_raw)
                episode_date = date_str.split("T")[0].split(" ")[0]

        # Chercher l'URL de la page sur RadioFrance
        radiofrance_service = RadioFranceService()
        episode_page_url = await radiofrance_service.search_episode_page_url(
            episode_title, episode_date
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


@app.patch("/api/episodes/{episode_id}/masked")
async def update_episode_masked(episode_id: str, request: Request) -> dict[str, Any]:
    """Met à jour le statut masked d'un épisode (Issue #107).

    Args:
        episode_id: ID de l'épisode
        request: Corps de la requête contenant {"masked": true/false}

    Returns:
        Dict avec message de succès
    """
    # Vérification mémoire
    memory_check = memory_guard.check_memory_limit()
    if memory_check:
        if "LIMITE MÉMOIRE DÉPASSÉE" in memory_check:
            memory_guard.force_shutdown(memory_check)
        print(f"⚠️ {memory_check}")

    try:
        # Lire le body de la requête
        body = await request.json()
        masked = body.get("masked")

        if masked is None:
            raise HTTPException(status_code=400, detail="Le champ 'masked' est requis")

        if not isinstance(masked, bool):
            raise HTTPException(
                status_code=400, detail="Le champ 'masked' doit être un booléen"
            )

        # Vérifier que l'épisode existe
        episode_data = mongodb_service.get_episode_by_id(episode_id)
        if not episode_data:
            raise HTTPException(status_code=404, detail="Épisode non trouvé")

        # Mettre à jour le statut
        success = mongodb_service.update_episode_masked_status(episode_id, masked)
        if not success:
            raise HTTPException(status_code=400, detail="Échec de la mise à jour")

        action = "masqué" if masked else "rendu visible"
        return {"message": f"Épisode {action} avec succès"}
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
            "maskedEpisodes": stats_data["masked_episodes_count"],
            "episodesWithCorrectedTitles": stats_data["episodes_with_corrected_titles"],
            "episodesWithCorrectedDescriptions": stats_data[
                "episodes_with_corrected_descriptions"
            ],
            "criticalReviews": stats_data["critical_reviews_count"],
            "lastUpdateDate": stats_data["last_update_date"],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}") from e


# ========== ENDPOINTS CALIBRE ==========


@app.get("/api/calibre/status")
async def get_calibre_status() -> dict[str, Any]:
    """Récupère le statut de l'intégration Calibre."""
    try:
        status = calibre_service.get_status()
        return status.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}") from e


@app.get("/api/calibre/books")
async def get_calibre_books(
    limit: int = 50,
    offset: int = 0,
    read_filter: bool | None = None,
    search: str | None = None,
) -> dict[str, Any]:
    """Récupère la liste des livres Calibre."""
    try:
        books_list = calibre_service.get_books(
            limit=limit, offset=offset, read_filter=read_filter, search=search
        )
        return books_list.model_dump()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}") from e


@app.get("/api/calibre/books/{book_id}")
async def get_calibre_book(book_id: int) -> dict[str, Any]:
    """Récupère les détails d'un livre Calibre."""
    try:
        book = calibre_service.get_book(book_id)
        if book is None:
            raise HTTPException(status_code=404, detail=f"Livre {book_id} non trouvé")
        return book.model_dump()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}") from e


@app.get("/api/calibre/authors")
async def get_calibre_authors(
    limit: int = 100, offset: int = 0
) -> list[dict[str, Any]]:
    """Récupère la liste des auteurs Calibre."""
    try:
        authors = calibre_service.get_authors(limit=limit, offset=offset)
        return [author.model_dump() for author in authors]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}") from e


@app.get("/api/calibre/statistics")
async def get_calibre_statistics() -> dict[str, Any]:
    """Récupère les statistiques de la bibliothèque Calibre."""
    try:
        stats = calibre_service.get_statistics()
        return stats.model_dump()
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


async def get_livres_from_collections(episode_oid: str) -> list[dict[str, Any]]:
    """Get books for episode from authoritative livres/auteurs collections.

    Uses livresauteurs_cache as intermediary to find which books have been
    validated and moved to livres/auteurs collections (status="mongo").
    Then fetches actual data from those authoritative collections.

    Args:
        episode_oid: Episode identifier (String type, 24 hex characters)

    Returns:
        List of books with author info from livres/auteurs collections

    Raises:
        HTTPException: If episode_oid format is invalid
    """
    from bson import ObjectId

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

    # Step 1: Get validated cache entries that link to livres/auteurs
    # Only get entries with status="mongo" (already moved to collections)
    cache_collection = mongodb_service.get_collection("livresauteurs_cache")
    validated_cache = list(
        cache_collection.find(
            {
                "episode_oid": episode_oid,
                "status": "mongo",
                "book_id": {"$exists": True},
                "author_id": {"$exists": True},
            }
        )
    )

    if not validated_cache:
        return []

    # Step 2: Extract unique book_ids
    livre_ids = [ObjectId(cache["book_id"]) for cache in validated_cache]

    # Step 3: Query livres collection for actual book data
    livres_dict = {}
    if mongodb_service.livres_collection is not None:
        for livre in mongodb_service.livres_collection.find(
            {"_id": {"$in": livre_ids}}
        ):
            livres_dict[livre["_id"]] = livre

    # Step 4: Query auteurs collection for author data
    auteur_ids = [
        livre.get("auteur_id")
        for livre in livres_dict.values()
        if livre.get("auteur_id")
    ]
    auteurs_dict = {}
    if mongodb_service.auteurs_collection is not None:
        for auteur in mongodb_service.auteurs_collection.find(
            {"_id": {"$in": auteur_ids}}
        ):
            auteurs_dict[auteur["_id"]] = auteur

    # Step 5: Build response using data from livres/auteurs (not cache!)
    books = []
    for livre_id in livre_ids:
        if livre_id not in livres_dict:
            continue  # Skip if livre not found

        livre = livres_dict[livre_id]
        auteur = auteurs_dict.get(livre.get("auteur_id"))

        books.append(
            {
                "_id": str(livre["_id"]),
                "livre_id": str(livre["_id"]),
                "titre": livre.get("titre", ""),  # From livres collection
                "auteur": auteur.get("nom", "")
                if auteur
                else "",  # From auteurs collection
                "auteur_id": str(livre.get("auteur_id", "")),
                "editeur": livre.get("editeur", ""),  # From livres collection
                "url_babelio": livre.get("url_babelio", ""),  # From livres collection
            }
        )

    return books


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

                # Issue #107: Filtrer les épisodes masqués
                if episode.masked:
                    continue

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


# ========== EMISSIONS ENDPOINTS (Issue #154) ==========


@app.get("/api/emissions", response_model=list[dict[str, Any]])
async def get_all_emissions() -> list[dict[str, Any]]:
    """
    Récupère toutes les émissions.
    Déclenche l'auto-conversion à chaque chargement pour convertir
    les nouveaux épisodes avec avis critiques.

    Returns:
        Liste des émissions avec données enrichies (episode, avis_critique)
    """
    # Vérification mémoire
    memory_check = memory_guard.check_memory_limit()
    if memory_check:
        if "LIMITE MÉMOIRE DÉPASSÉE" in memory_check:
            memory_guard.force_shutdown(memory_check)
        print(f"⚠️ {memory_check}")

    try:
        # Auto-conversion systématique à chaque chargement
        logger.info("Déclenchement auto-conversion des nouveaux épisodes")
        await auto_convert_episodes_to_emissions()

        # Récupérer toutes les émissions (y compris nouvellement créées)
        emissions = mongodb_service.get_all_emissions()

        # Enrichir avec données episode et avis_critique
        enriched_emissions = []
        for emission in emissions:
            episode_data = mongodb_service.get_episode_by_id(
                str(emission["episode_id"])
            )
            avis_data = mongodb_service.get_avis_critique_by_id(
                str(emission["avis_critique_id"])
            )

            emission_dict = Emission(emission).to_dict()
            emission_dict["episode"] = (
                Episode(episode_data).to_summary_dict() if episode_data else None
            )
            emission_dict["has_avis_critique"] = avis_data is not None

            enriched_emissions.append(emission_dict)

        return enriched_emissions

    except Exception as e:
        logger.error(f"Erreur get_all_emissions: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/api/emissions/auto-convert", response_model=dict[str, Any])
async def auto_convert_episodes_to_emissions() -> dict[str, Any]:
    """
    Convertit automatiquement tous les épisodes (avec avis critiques) en émissions.

    Logique :
    1. Récupérer tous les avis_critiques
    2. Pour chaque avis, créer une émission si elle n'existe pas déjà
    3. Détecter animateur_id en cherchant les critiques avec animateur=true

    Returns:
        Statistiques de conversion (created, skipped, errors)
    """
    # Vérification mémoire
    memory_check = memory_guard.check_memory_limit()
    if memory_check:
        if "LIMITE MÉMOIRE DÉPASSÉE" in memory_check:
            memory_guard.force_shutdown(memory_check)
        print(f"⚠️ {memory_check}")

    try:
        created_count = 0
        skipped_count = 0
        errors = []

        # 1. Récupérer tous les avis_critiques
        all_avis = mongodb_service.get_all_critical_reviews()

        for avis in all_avis:
            try:
                episode_oid = avis.get("episode_oid")
                if not episode_oid:
                    continue

                # 2. Vérifier si émission existe déjà
                existing = mongodb_service.get_emission_by_episode_id(episode_oid)
                if existing:
                    skipped_count += 1
                    continue

                # 3. Récupérer données épisode
                episode_data = mongodb_service.get_episode_by_id(episode_oid)
                if not episode_data:
                    errors.append(f"Épisode {episode_oid} non trouvé")
                    continue

                episode = Episode(episode_data)

                # 3b. Skip épisodes masqués
                if episode.masked:
                    skipped_count += 1
                    continue

                # 4. Détecter animateur_id
                critiques = mongodb_service.get_critiques_by_episode(episode_oid)
                animateur_id = None
                for critique in critiques:
                    if critique.get("animateur", False):
                        animateur_id = critique["id"]
                        break  # Prendre le premier animateur trouvé

                # 5. Créer émission
                emission_data = Emission.for_mongodb_insert(
                    {
                        "episode_id": episode_oid,
                        "avis_critique_id": str(avis["_id"]),
                        "date": episode.date,
                        "duree": episode.duree,
                        "animateur_id": animateur_id,
                        "avis_ids": [],  # Vide pour l'instant (future issue)
                    }
                )

                mongodb_service.create_emission(emission_data)
                created_count += 1

            except Exception as e:
                errors.append(f"Erreur pour avis {avis.get('_id')}: {str(e)}")

        return {
            "success": True,
            "created": created_count,
            "skipped": skipped_count,
            "total_processed": len(all_avis),
            "errors": errors,
        }

    except Exception as e:
        logger.error(f"Erreur auto_convert_episodes_to_emissions: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/api/emissions/by-date/{date_str}", response_model=dict[str, Any])
async def get_emission_by_date(date_str: str) -> dict[str, Any]:
    """
    Récupère une émission par sa date (format YYYYMMDD).

    Args:
        date_str: Date au format YYYYMMDD (ex: "20251212")

    Returns:
        Mêmes données que /api/emissions/{emission_id}/details
    """
    # Vérification mémoire
    memory_check = memory_guard.check_memory_limit()
    if memory_check:
        if "LIMITE MÉMOIRE DÉPASSÉE" in memory_check:
            memory_guard.force_shutdown(memory_check)
        print(f"⚠️ {memory_check}")

    # Valider format date YYYYMMDD
    if not re.match(r"^\d{8}$", date_str):
        raise HTTPException(
            status_code=400, detail="Format de date invalide. Attendu: YYYYMMDD"
        )

    try:
        # Convertir string YYYYMMDD en datetime
        year = int(date_str[:4])
        month = int(date_str[4:6])
        day = int(date_str[6:8])
        target_date_start = datetime(year, month, day)
        target_date_end = datetime(year, month, day, 23, 59, 59)

        # Chercher émission avec cette date (range query pour matcher le jour complet)
        if mongodb_service.emissions_collection is None:
            raise HTTPException(
                status_code=500, detail="Service MongoDB non disponible"
            )
        emission_data = mongodb_service.emissions_collection.find_one(
            {"date": {"$gte": target_date_start, "$lte": target_date_end}}
        )

        if not emission_data:
            raise HTTPException(
                status_code=404,
                detail=f"Aucune émission trouvée pour la date {date_str}",
            )

        emission_id_str = str(emission_data["_id"])

        # Réutiliser la logique de get_emission_details
        result = await get_emission_details(emission_id_str)
        return dict(result) if isinstance(result, dict) else result

    except HTTPException:
        raise
    except ValueError:
        raise HTTPException(status_code=400, detail="Date invalide") from None
    except Exception as e:
        logger.error(f"Erreur get_emission_by_date: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/api/emissions/{emission_id}/details", response_model=dict[str, Any])
async def get_emission_details(emission_id: str) -> dict[str, Any]:
    """
    Récupère les détails complets d'une émission.

    Args:
        emission_id: ID de l'émission (ObjectId string)

    Returns:
        Dictionnaire avec toutes les données (emission, episode, books, critiques, summary)
    """
    # Vérification mémoire
    memory_check = memory_guard.check_memory_limit()
    if memory_check:
        if "LIMITE MÉMOIRE DÉPASSÉE" in memory_check:
            memory_guard.force_shutdown(memory_check)
        print(f"⚠️ {memory_check}")

    # Valider format ObjectId
    if not re.match(r"^[0-9a-fA-F]{24}$", emission_id):
        raise HTTPException(status_code=400, detail="Format d'ID invalide")

    try:
        # 1. Récupérer émission
        if mongodb_service.emissions_collection is None:
            raise HTTPException(
                status_code=500, detail="Service MongoDB non disponible"
            )
        emission_data = mongodb_service.emissions_collection.find_one(
            {"_id": ObjectId(emission_id)}
        )
        if not emission_data:
            raise HTTPException(status_code=404, detail="Émission non trouvée")

        emission = Emission(emission_data)

        # 2. Récupérer épisode
        episode_data = mongodb_service.get_episode_by_id(emission.episode_id)
        if not episode_data:
            raise HTTPException(status_code=404, detail="Épisode associé non trouvé")

        episode = Episode(episode_data)

        # 3. Récupérer avis_critique
        avis_data = mongodb_service.get_avis_critique_by_id(emission.avis_critique_id)
        if not avis_data:
            raise HTTPException(
                status_code=404, detail="Avis critique associé non trouvé"
            )

        # 4. Récupérer livres depuis collections livres/auteurs (Issue #177)
        books = await get_livres_from_collections(episode_oid=str(emission.episode_id))

        # 5. Récupérer critiques de cet épisode
        critiques = mongodb_service.get_critiques_by_episode(emission.episode_id)

        # 6. Construire réponse
        return {
            "emission": emission.to_dict(),
            "episode": {
                "id": episode.id,
                "titre": episode.titre,
                "date": episode.date.isoformat() if episode.date else None,
                "description": episode.description,
                "duree": episode.duree,
                "episode_page_url": episode.episode_page_url,
            },
            "summary": avis_data.get("summary", ""),
            "books": books,
            "critiques": critiques,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur get_emission_details: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


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

                            # Mettre à jour l'avis_critique avec le summary mis à jour
                            mongodb_service.update_avis_critique(
                                request.avis_critique_id,
                                {
                                    "summary": updated_summary,
                                },
                            )
                            print("   ✅ Summary updated in avis_critique")

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
        quoted_segments_raw = re.findall(r'"([^"]+)"', full_text)
        # Issue #96: Nettoyer les sauts de ligne dans les segments extraits
        quoted_segments = [" ".join(seg.split()) for seg in quoted_segments_raw]

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

        # Recherche dans les éditeurs
        editeurs_search_result = mongodb_service.search_editeurs(q, limit)
        editeurs_list = editeurs_search_result.get("editeurs", [])

        # Structure de la réponse - utilise les collections dédiées en priorité
        response = {
            "query": q,
            "results": {
                "auteurs": auteurs_list,
                "auteurs_total_count": auteurs_total_count,
                "livres": livres_list,
                "livres_total_count": livres_total_count,
                "editeurs": editeurs_list,
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


# Nouveaux endpoints pour l'Issue #96 - Pages de visualisation Auteur et Livre


@app.get("/api/auteur/{auteur_id}", response_model=dict[str, Any])
async def get_auteur_detail(auteur_id: str) -> dict[str, Any]:
    """Récupère les détails d'un auteur avec la liste de ses livres (Issue #96 - Phase 1).

    Args:
        auteur_id: ID de l'auteur (MongoDB ObjectId)

    Returns:
        Dict avec auteur_id, nom, nombre_oeuvres, et livres triés alphabétiquement

    Raises:
        404: Si l'auteur n'existe pas
        400: Si l'ID est invalide
        500: En cas d'erreur serveur
    """
    # Vérification mémoire
    memory_check = memory_guard.check_memory_limit()
    if memory_check:
        if "LIMITE MÉMOIRE DÉPASSÉE" in memory_check:
            memory_guard.force_shutdown(memory_check)
        print(f"⚠️ {memory_check}")

    # Validation du format ObjectId
    if len(auteur_id) != 24:
        raise HTTPException(status_code=404, detail="Auteur non trouvé")

    try:
        from bson import ObjectId

        # Vérifier que c'est un ObjectId valide
        ObjectId(auteur_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail="Auteur non trouvé") from e

    try:
        auteur_data = mongodb_service.get_auteur_with_livres(auteur_id)
        if not auteur_data:
            raise HTTPException(status_code=404, detail="Auteur non trouvé")

        return auteur_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}") from e


@app.get("/api/livre/{livre_id}", response_model=dict[str, Any])
async def get_livre_detail(livre_id: str) -> dict[str, Any]:
    """Récupère les détails d'un livre avec la liste de ses épisodes (Issue #96 - Phase 2).

    Args:
        livre_id: ID du livre (MongoDB ObjectId)

    Returns:
        Dict avec livre_id, titre, auteur_id, auteur_nom, editeur, nombre_episodes,
        et episodes triés par date décroissante

    Raises:
        404: Si le livre n'existe pas
        500: En cas d'erreur serveur
    """
    # Vérification mémoire
    memory_check = memory_guard.check_memory_limit()
    if memory_check:
        if "LIMITE MÉMOIRE DÉPASSÉE" in memory_check:
            memory_guard.force_shutdown(memory_check)
        print(f"⚠️ {memory_check}")

    # Validation du format ObjectId
    if len(livre_id) != 24:
        raise HTTPException(status_code=404, detail="Livre non trouvé")

    try:
        from bson import ObjectId

        # Vérifier que c'est un ObjectId valide
        ObjectId(livre_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail="Livre non trouvé") from e

    try:
        livre_data = mongodb_service.get_livre_with_episodes(livre_id)
        if not livre_data:
            raise HTTPException(status_code=404, detail="Livre non trouvé")

        return livre_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}") from e


# Nouveaux endpoints pour l'Issue #66 - Gestion des collections auteurs/livres


@app.get("/api/livres-auteurs/statistics", response_model=dict[str, Any])
async def get_livres_auteurs_statistics() -> dict[str, Any]:
    """Récupère les statistiques pour la page livres-auteurs (Issue #124: includes Babelio metrics)."""
    # Vérification mémoire
    memory_check = memory_guard.check_memory_limit()
    if memory_check:
        if "LIMITE MÉMOIRE DÉPASSÉE" in memory_check:
            memory_guard.force_shutdown(memory_check)
        print(f"⚠️ {memory_check}")

    try:
        # Utiliser stats_service qui contient toutes les métriques, y compris Babelio (Issue #124)
        stats = stats_service.get_cache_statistics()
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


@app.get("/api/books/duplicates/statistics", response_model=dict[str, Any])
async def get_duplicate_books_statistics() -> dict[str, Any]:
    """Récupère les statistiques des doublons de livres (Issue #178)."""
    try:
        stats = await duplicate_books_service.get_duplicate_statistics()
        return stats
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des stats doublons: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}") from e


@app.get("/api/books/duplicates/groups", response_model=list[dict[str, Any]])
async def get_duplicate_books_groups() -> list[dict[str, Any]]:
    """Récupère tous les groupes de doublons de livres (Issue #178)."""
    try:
        groups = await duplicate_books_service.find_duplicate_groups_by_url()
        return groups
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des groupes doublons: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}") from e


@app.post("/api/books/duplicates/merge", response_model=dict[str, Any])
async def merge_duplicate_books_group(
    request: MergeDuplicateGroupRequest,
) -> dict[str, Any]:
    """Fusionne un groupe de doublons (Issue #178)."""
    try:
        result = await duplicate_books_service.merge_duplicate_group(
            url_babelio=request.url_babelio,
            book_ids=request.book_ids,
        )

        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])

        return {
            "status": "success",
            "message": "Groupe fusionné avec succès",
            "result": result,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la fusion du groupe: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}") from e


@app.post("/api/books/duplicates/merge/batch")
async def merge_duplicate_books_batch(request: MergeBatchRequest) -> Response:
    """Fusionne en batch tous les groupes de doublons (Issue #178)."""
    try:

        async def event_generator() -> AsyncGenerator[str, None]:
            """Générateur d'événements Server-Sent Events."""
            async for event in duplicate_books_service.merge_batch(
                skip_list=request.skip_list
            ):
                yield f"data: {event}\n\n"

        return Response(
            content=event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )
    except Exception as e:
        logger.error(f"Erreur lors du batch merge: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}") from e


# ========== DUPLICATE AUTHORS ENDPOINTS (Issue #178) ==========


@app.get("/api/authors/duplicates/statistics", response_model=dict[str, Any])
async def get_duplicate_authors_statistics() -> dict[str, Any]:
    """Récupère les statistiques des doublons d'auteurs (Issue #178)."""
    try:
        stats = await duplicate_books_service.get_duplicate_authors_statistics()
        return stats
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des stats doublons auteurs: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}") from e


@app.get("/api/authors/duplicates/groups", response_model=list[dict[str, Any]])
async def get_duplicate_authors_groups() -> list[dict[str, Any]]:
    """Récupère tous les groupes d'auteurs en doublon (Issue #178)."""
    try:
        groups = await duplicate_books_service.find_duplicate_authors_by_url()
        return groups
    except Exception as e:
        logger.error(
            f"Erreur lors de la récupération des groupes doublons auteurs: {e}"
        )
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}") from e


@app.post("/api/authors/duplicates/merge", response_model=dict[str, Any])
async def merge_duplicate_authors_group(
    request: MergeDuplicateAuthorsRequest,
) -> dict[str, Any]:
    """Fusionne un groupe d'auteurs en doublon (Issue #178)."""
    try:
        result = await duplicate_books_service.merge_duplicate_authors(
            url_babelio=request.url_babelio,
            auteur_ids=request.auteur_ids,
        )

        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])

        return {
            "status": "success",
            "message": "Groupe d'auteurs fusionné avec succès",
            "result": result,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la fusion du groupe d'auteurs: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}") from e


@app.get("/api/stats", response_model=dict[str, Any])
async def get_cache_statistics() -> dict[str, Any] | JSONResponse:
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


# Endpoints pour la migration Babelio (Issue #124)
@app.get("/api/babelio-migration/status")
async def get_migration_status() -> dict[str, Any]:
    """Récupère le statut de la migration Babelio."""
    return babelio_migration_service.get_migration_status()


@app.get("/api/babelio-migration/problematic-cases")
async def get_problematic_cases() -> list[dict[str, Any]]:
    """Récupère la liste des cas problématiques de la migration."""
    return babelio_migration_service.get_problematic_cases()


@app.post("/api/babelio-migration/accept-suggestion")
async def accept_suggestion(request: AcceptSuggestionRequest) -> JSONResponse:
    """Accepte la suggestion Babelio et met à jour MongoDB."""
    try:
        success = babelio_migration_service.accept_suggestion(
            livre_id=request.livre_id,
            babelio_url=request.babelio_url,
            babelio_author_url=request.babelio_author_url,
            corrected_title=request.corrected_title,
        )

        if success:
            return JSONResponse(
                status_code=200,
                content={
                    "status": "success",
                    "message": f"Suggestion acceptée pour livre {request.livre_id}",
                },
            )
        else:
            return JSONResponse(
                status_code=404,
                content={"status": "error", "message": "Livre non trouvé"},
            )
    except Exception as e:
        return JSONResponse(
            status_code=500, content={"status": "error", "message": str(e)}
        )


@app.post("/api/babelio-migration/mark-not-found")
async def mark_not_found(request: MarkNotFoundRequest) -> JSONResponse:
    """Marque un livre ou auteur comme non trouvé sur Babelio."""
    try:
        success = babelio_migration_service.mark_as_not_found(
            item_id=request.item_id,
            reason=request.reason,
            item_type=request.item_type,
        )

        if success:
            item_label = "Livre" if request.item_type == "livre" else "Auteur"
            return JSONResponse(
                status_code=200,
                content={
                    "status": "success",
                    "message": f"{item_label} {request.item_id} marqué comme not found",
                },
            )
        else:
            item_label = "Livre" if request.item_type == "livre" else "Auteur"
            return JSONResponse(
                status_code=404,
                content={"status": "error", "message": f"{item_label} non trouvé"},
            )
    except Exception as e:
        return JSONResponse(
            status_code=500, content={"status": "error", "message": str(e)}
        )


@app.post("/api/babelio-migration/update-from-url")
async def update_from_babelio_url(request: UpdateFromBabelioUrlRequest) -> JSONResponse:
    """Met à jour un livre/auteur depuis une URL Babelio manuelle."""
    try:
        result = await babelio_migration_service.update_from_babelio_url(
            item_id=request.item_id,
            babelio_url=request.babelio_url,
            item_type=request.item_type,
        )

        if result["success"]:
            item_label = "Livre" if request.item_type == "livre" else "Auteur"
            return JSONResponse(
                status_code=200,
                content={
                    "status": "success",
                    "message": f"{item_label} mis à jour depuis URL Babelio",
                    "data": result["scraped_data"],
                },
            )
        else:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "message": result.get("error", "Erreur inconnue"),
                },
            )
    except Exception as e:
        return JSONResponse(
            status_code=500, content={"status": "error", "message": str(e)}
        )


@app.post("/api/babelio-migration/correct-title")
async def correct_title(request: CorrectTitleRequest) -> JSONResponse:
    """Corrige le titre d'un livre et le retire des cas problématiques."""
    try:
        success = babelio_migration_service.correct_title(
            livre_id=request.livre_id,
            new_title=request.new_title,
        )

        if success:
            return JSONResponse(
                status_code=200,
                content={
                    "status": "success",
                    "message": f"Titre corrigé: '{request.new_title}'",
                },
            )
        else:
            return JSONResponse(
                status_code=404,
                content={"status": "error", "message": "Livre non trouvé"},
            )
    except Exception as e:
        return JSONResponse(
            status_code=500, content={"status": "error", "message": str(e)}
        )


@app.post("/api/babelio-migration/retry-with-title")
async def retry_with_title(request: RetryWithTitleRequest) -> dict[str, Any]:
    """Réessaie la recherche Babelio avec un nouveau titre."""
    return await babelio_migration_service.retry_with_new_title(
        livre_id=request.livre_id,
        new_title=request.new_title,
        author=request.author,
    )


@app.post("/api/babelio/extract-from-url")
async def extract_from_babelio_url(
    request: ExtractFromBabelioUrlRequest,
) -> JSONResponse:
    """Extrait les données depuis une URL Babelio sans mise à jour (Issue #159)."""
    try:
        # Scraper les données depuis l'URL Babelio
        scraped_data = await babelio_migration_service.extract_from_babelio_url(
            request.babelio_url
        )

        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "data": scraped_data,
            },
        )
    except ValueError as e:
        # Erreur de validation d'URL
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "message": str(e),
            },
        )
    except Exception as e:
        # Autres erreurs (scraping, réseau, etc.)
        logger.error(f"Error extracting from Babelio URL: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": str(e),
            },
        )


@app.post("/api/babelio-migration/start")
async def start_migration_process() -> JSONResponse:
    """Lance le processus de migration automatique des URL Babelio."""
    try:
        from .utils.migration_runner import migration_runner

        result = await migration_runner.start_migration()
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Error starting migration: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@app.get("/api/babelio-migration/progress")
async def get_migration_progress() -> JSONResponse:
    """Récupère la progression actuelle de la migration."""
    try:
        from .utils.migration_runner import migration_runner

        status = migration_runner.get_status()
        return JSONResponse(content=status)
    except Exception as e:
        logger.error(f"Error getting migration progress: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@app.get("/api/babelio-migration/logs")
async def get_migration_logs() -> JSONResponse:
    """Récupère tous les logs détaillés de la migration."""
    try:
        from .utils.migration_runner import migration_runner

        logs = migration_runner.get_detailed_logs()
        return JSONResponse(content={"logs": logs})
    except Exception as e:
        logger.error(f"Error getting migration logs: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@app.post("/api/babelio-migration/stop")
async def stop_migration_process() -> JSONResponse:
    """Arrête le processus de migration en cours."""
    try:
        from .utils.migration_runner import migration_runner

        result = await migration_runner.stop_migration()
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Error stopping migration: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


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


# ============================================================================
# ENDPOINTS CRITIQUES ET EMISSIONS (Issue #154)
# ============================================================================


@app.get("/api/episodes/{episode_id}/critiques-detectes")
async def get_detected_critiques(episode_id: str) -> JSONResponse:
    """
    Extrait les critiques détectés dans l'avis critique d'un épisode.

    Returns:
        Liste des critiques détectés avec leur statut de matching
    """
    try:
        if (
            mongodb_service.avis_critiques_collection is None
            or mongodb_service.critiques_collection is None
        ):
            raise HTTPException(
                status_code=500, detail="Service MongoDB non disponible"
            )

        # Récupérer l'avis critique pour cet épisode
        # Note: episode_oid est stocké en STRING dans MongoDB, pas en ObjectId
        avis_critique = mongodb_service.avis_critiques_collection.find_one(
            {"episode_oid": episode_id}
        )

        if not avis_critique:
            raise HTTPException(
                status_code=404, detail="Aucun avis critique trouvé pour cet épisode"
            )

        # Extraire les critiques depuis le summary
        summary = avis_critique.get("summary", "")
        detected_names = critiques_extraction_service.extract_critiques_from_summary(
            summary
        )

        # Récupérer tous les critiques existants
        existing_critiques = list(mongodb_service.critiques_collection.find({}))

        # Pour chaque nom détecté, chercher une correspondance
        results = []
        for detected_name in detected_names:
            match = critiques_extraction_service.find_matching_critique(
                detected_name, existing_critiques
            )

            if match:
                # Critique existant trouvé
                results.append(
                    {
                        "detected_name": detected_name,
                        "status": "existing",
                        "match_type": match["match_type"],
                        "matched_critique": match["nom"],
                    }
                )
            else:
                # Nouveau critique
                results.append(
                    {
                        "detected_name": detected_name,
                        "status": "new",
                        "match_type": None,
                        "matched_critique": None,
                    }
                )

        return JSONResponse(
            content={
                "episode_id": episode_id,
                "avis_critique_id": str(avis_critique["_id"]),
                "detected_critiques": results,
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de l'extraction des critiques: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/api/stats/critiques-manquants")
async def get_critiques_manquants_count() -> JSONResponse:
    """
    Compte le nombre d'épisodes avec des critiques manquants.

    Returns:
        {"count": nombre d'épisodes avec critiques manquants}
    """
    try:
        if (
            mongodb_service.episodes_collection is None
            or mongodb_service.avis_critiques_collection is None
            or mongodb_service.critiques_collection is None
        ):
            raise HTTPException(
                status_code=500, detail="Service MongoDB non disponible"
            )

        # Récupérer tous les episode_oid qui ont des avis critiques (strings)
        episode_ids_with_reviews = set(
            mongodb_service.avis_critiques_collection.distinct("episode_oid")
        )

        # Convertir les episode_oid en ObjectId pour récupérer les épisodes
        from bson import ObjectId

        episode_object_ids = [
            ObjectId(ep_id) for ep_id in episode_ids_with_reviews if ep_id
        ]

        # Récupérer les épisodes pour vérifier le statut masqué
        # Issue #107: Filtrer les épisodes masqués
        episodes_data = list(
            mongodb_service.episodes_collection.find(
                {"_id": {"$in": episode_object_ids}}
            )
        )

        # Compter combien d'épisodes ont au moins un critique "new" (manquant)
        episodes_with_missing_critiques = 0

        # Récupérer tous les critiques existants une seule fois
        existing_critiques = list(mongodb_service.critiques_collection.find({}))

        for episode_data in episodes_data:
            # Filtrer les épisodes masqués
            episode = Episode(episode_data)
            if episode.masked:
                continue

            episode_id = str(episode_data["_id"])

            # Récupérer l'avis critique
            avis_critique = mongodb_service.avis_critiques_collection.find_one(
                {"episode_oid": episode_id}
            )

            if not avis_critique:
                continue

            # Extraire les critiques détectés
            summary = avis_critique.get("summary", "")
            detected_names = (
                critiques_extraction_service.extract_critiques_from_summary(summary)
            )

            # Vérifier si au moins un critique est "new" (manquant)
            has_missing = False
            for detected_name in detected_names:
                match = critiques_extraction_service.find_matching_critique(
                    detected_name, existing_critiques
                )
                if not match:
                    # Ce critique est "new" (manquant)
                    has_missing = True
                    break

            if has_missing:
                episodes_with_missing_critiques += 1

        return JSONResponse(content={"count": episodes_with_missing_critiques})

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors du comptage des critiques manquants: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/api/episodes-with-avis-critiques")
async def get_episodes_with_avis_critiques() -> JSONResponse:
    """
    Récupère la liste des épisodes qui ont des avis critiques associés.

    Returns:
        Liste des épisodes avec avis critiques
    """
    try:
        if (
            mongodb_service.episodes_collection is None
            or mongodb_service.avis_critiques_collection is None
        ):
            raise HTTPException(
                status_code=500, detail="Service MongoDB non disponible"
            )

        from bson import ObjectId

        # Récupérer tous les episode_oid qui ont des avis critiques (ce sont des strings)
        episode_ids_with_reviews = set(
            mongodb_service.avis_critiques_collection.distinct("episode_oid")
        )

        # Convertir les strings en ObjectId pour la recherche dans episodes
        episode_object_ids = [
            ObjectId(ep_id) for ep_id in episode_ids_with_reviews if ep_id
        ]

        # Récupérer les épisodes correspondants
        episodes = list(
            mongodb_service.episodes_collection.find(
                {"_id": {"$in": episode_object_ids}}
            )
        )

        # Convertir en format JSON compatible avec EpisodeDropdown
        # (même structure que /api/episodes-with-reviews)
        episodes_json = []
        for episode_data in episodes:
            from back_office_lmelp.models.episode import Episode

            episode = Episode(episode_data)

            # Issue #107: Filtrer les épisodes masqués
            if episode.masked:
                continue

            # Utiliser to_summary_dict() pour cohérence avec /api/episodes-with-reviews
            episode_dict = episode.to_summary_dict()

            # Ajouter les flags pour les pastilles de couleur dans EpisodeDropdown
            episode_oid = str(episode_data["_id"])

            # Pour la page Identification Critiques, les pastilles reflètent UNIQUEMENT
            # le statut des critiques (pas des livres):
            # - 🟢 Vert: TOUS les critiques ont été créés
            # - ⚪ Gris: AUCUN critique n'a été créé
            # - 🔴 Rouge: CERTAINS critiques créés ET CERTAINS "new"
            num_new_critiques = 0
            num_existing_critiques = 0

            avis_critique = mongodb_service.avis_critiques_collection.find_one(
                {"episode_oid": episode_oid}
            )
            if (
                avis_critique
                and avis_critique.get("summary")
                and mongodb_service.critiques_collection is not None
            ):
                # Extraire les critiques détectés
                detected_critiques = (
                    critiques_extraction_service.extract_critiques_from_summary(
                        avis_critique["summary"]
                    )
                )
                if detected_critiques:
                    # Récupérer les critiques existants
                    existing_critiques = list(
                        mongodb_service.critiques_collection.find()
                    )
                    # Compter les critiques "new" vs existants
                    for detected_name in detected_critiques:
                        match = critiques_extraction_service.find_matching_critique(
                            detected_name, existing_critiques
                        )
                        if match:
                            num_existing_critiques += 1
                        else:
                            num_new_critiques += 1

            total_critiques = num_new_critiques + num_existing_critiques

            # Déterminer les flags selon la logique:
            # - Si aucun critique: gris (has_cached_books=False)
            # - Si tous créés: vert (has_cached_books=True, has_incomplete_books=False)
            # - Si certains créés et certains new: rouge (has_cached_books=True, has_incomplete_books=True)
            if total_critiques == 0:
                # Aucun critique détecté → Gris
                episode_dict["has_cached_books"] = False
                episode_dict["has_incomplete_books"] = False
            elif num_new_critiques == 0:
                # Tous les critiques ont été créés → Vert
                episode_dict["has_cached_books"] = True
                episode_dict["has_incomplete_books"] = False
            else:
                # Au moins un critique "new" → Rouge
                episode_dict["has_cached_books"] = True
                episode_dict["has_incomplete_books"] = True

            episodes_json.append(episode_dict)

        # Issue #154: Trier par date décroissante (le plus récent en premier)
        episodes_json.sort(key=lambda ep: ep.get("date") or "", reverse=True)

        return JSONResponse(content=episodes_json)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des épisodes: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/api/episodes-sans-avis-critiques")
async def get_episodes_sans_avis_critiques() -> JSONResponse:
    """
    Liste épisodes avec transcription mais sans avis critique.

    Returns:
        Liste des épisodes (id, titre, date, transcription_length, has_episode_page_url)
    """
    memory_check = memory_guard.check_memory_limit()
    if memory_check:
        if "LIMITE MÉMOIRE DÉPASSÉE" in memory_check:
            memory_guard.force_shutdown(memory_check)
        print(f"⚠️ {memory_check}")

    try:
        if (
            mongodb_service.episodes_collection is None
            or mongodb_service.avis_critiques_collection is None
        ):
            raise HTTPException(
                status_code=500, detail="Service MongoDB non disponible"
            )

        # 1. Get episode IDs that have avis_critiques
        avis_critiques = list(
            mongodb_service.avis_critiques_collection.find({}, {"episode_oid": 1})
        )
        episode_ids_with_avis = {avis["episode_oid"] for avis in avis_critiques}

        # 2. Find episodes with transcription but not in the set
        # Issue #107: Exclure les épisodes masqués
        episodes = list(
            mongodb_service.episodes_collection.find(
                {
                    "transcription": {"$exists": True, "$nin": [None, ""]},
                    "masked": {"$ne": True},  # Exclure les épisodes masqués
                    "_id": {
                        "$nin": [ObjectId(eid) for eid in episode_ids_with_avis if eid]
                    },
                },
                {"titre": 1, "date": 1, "transcription": 1, "episode_page_url": 1},
            ).sort([("date", -1)])
        )

        # 3. Format response
        result = []
        for ep in episodes:
            result.append(
                {
                    "id": str(ep["_id"]),
                    "titre": ep.get("titre", ""),
                    "date": ep.get("date").isoformat() if ep.get("date") else None,
                    "transcription_length": len(ep.get("transcription", "")),
                    "has_episode_page_url": bool(ep.get("episode_page_url")),
                    "episode_page_url": ep.get(
                        "episode_page_url"
                    ),  # Retourner l'URL elle-même
                }
            )

        return JSONResponse(content=result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur récupération épisodes sans avis: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/api/episodes-with-summaries")
async def get_episodes_with_summaries() -> JSONResponse:
    """
    Liste épisodes qui ont des avis critiques.

    Returns:
        Liste des épisodes avec summary (id, titre, date, transcription_length, has_episode_page_url, has_summary)
    """
    memory_check = memory_guard.check_memory_limit()
    if memory_check:
        if "LIMITE MÉMOIRE DÉPASSÉE" in memory_check:
            memory_guard.force_shutdown(memory_check)
        print(f"⚠️ {memory_check}")

    try:
        if (
            mongodb_service.episodes_collection is None
            or mongodb_service.avis_critiques_collection is None
        ):
            raise HTTPException(
                status_code=500, detail="Service MongoDB non disponible"
            )

        # 1. Get all episode IDs that have avis_critiques
        avis_critiques = list(
            mongodb_service.avis_critiques_collection.find({}, {"episode_oid": 1})
        )
        episode_ids_with_avis = {
            avis["episode_oid"] for avis in avis_critiques if avis.get("episode_oid")
        }

        if not episode_ids_with_avis:
            return JSONResponse(content=[])

        # 2. Convert string IDs to ObjectId and find episodes
        object_ids = [ObjectId(eid) for eid in episode_ids_with_avis if eid]

        episodes = list(
            mongodb_service.episodes_collection.find(
                {"_id": {"$in": object_ids}, "masked": {"$ne": True}},
                {"titre": 1, "date": 1, "transcription": 1, "episode_page_url": 1},
            ).sort([("date", -1)])
        )

        # 3. Format response
        result = []
        for ep in episodes:
            result.append(
                {
                    "id": str(ep["_id"]),
                    "titre": ep.get("titre", ""),
                    "date": ep.get("date").isoformat() if ep.get("date") else None,
                    "transcription_length": len(ep.get("transcription", "")),
                    "has_episode_page_url": bool(ep.get("episode_page_url")),
                    "episode_page_url": ep.get("episode_page_url"),
                    "has_summary": True,  # All episodes in this endpoint have summaries
                }
            )

        return JSONResponse(content=result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur récupération épisodes avec summaries: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/api/avis-critiques/by-episode/{episode_id}")
async def get_summary_by_episode(episode_id: str) -> JSONResponse:
    """
    Récupère le summary existant pour un épisode.

    Args:
        episode_id: ID de l'épisode

    Returns:
        summary, summary_phase1, metadata, created_at, updated_at

    Raises:
        404: Aucun avis critique trouvé pour cet épisode
    """
    memory_check = memory_guard.check_memory_limit()
    if memory_check:
        if "LIMITE MÉMOIRE DÉPASSÉE" in memory_check:
            memory_guard.force_shutdown(memory_check)
        print(f"⚠️ {memory_check}")

    try:
        if mongodb_service.avis_critiques_collection is None:
            raise HTTPException(
                status_code=500, detail="Service MongoDB non disponible"
            )

        avis = mongodb_service.avis_critiques_collection.find_one(
            {"episode_oid": episode_id}
        )

        if not avis:
            raise HTTPException(
                status_code=404,
                detail=f"Aucun avis critique trouvé pour l'épisode {episode_id}",
            )

        result = {
            "summary": avis.get("summary", ""),
            "summary_phase1": avis.get("summary_phase1", ""),
            "metadata": avis.get("metadata_source", {}),
            "created_at": (
                avis["created_at"].isoformat() if avis.get("created_at") else None
            ),
            "updated_at": (
                avis["updated_at"].isoformat() if avis.get("updated_at") else None
            ),
        }

        return JSONResponse(content=result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur récupération summary pour épisode {episode_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/api/avis-critiques/generate", response_model=GenerateAvisCritiquesResponse)
async def generate_avis_critiques(
    request: GenerateAvisCritiquesRequest,
) -> GenerateAvisCritiquesResponse:
    """
    Génère un avis critique en 2 phases LLM (Phase 1 + Phase 2 avec correction).

    Args:
        request: episode_id

    Returns:
        success, summary, summary_phase1, metadata, corrections_applied, warnings
    """
    memory_check = memory_guard.check_memory_limit()
    if memory_check:
        if "LIMITE MÉMOIRE DÉPASSÉE" in memory_check:
            memory_guard.force_shutdown(memory_check)
        print(f"⚠️ {memory_check}")

    try:
        if mongodb_service.episodes_collection is None:
            raise HTTPException(
                status_code=500, detail="Service MongoDB non disponible"
            )

        # 1. Fetch episode
        episode = mongodb_service.get_episode_by_id(request.episode_id)
        if not episode:
            raise HTTPException(status_code=404, detail="Épisode non trouvé")

        transcription = episode.get("transcription")
        if not transcription:
            raise HTTPException(status_code=400, detail="Épisode sans transcription")

        # 2. Extract date
        episode_date = episode.get("date")
        if isinstance(episode_date, datetime):
            episode_date_str = episode_date.strftime("%Y-%m-%d")
        else:
            episode_date_str = str(episode_date).split("T")[0] if episode_date else ""

        # 3. Get episode page URL for metadata extraction
        episode_page_url = episode.get("episode_page_url")

        # 4. Generate full summary (Phase 1 + Phase 2)
        # Le service attendra automatiquement si l'URL est en cours de fetch
        result = await avis_critiques_generation_service.generate_full_summary(
            transcription, episode_date_str, episode_page_url, request.episode_id
        )

        return GenerateAvisCritiquesResponse(
            success=True,
            summary=result["summary"],
            summary_phase1=result["summary_phase1"],
            metadata=result["metadata"],
            corrections_applied=result["corrections_applied"],
            warnings=result["warnings"],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur génération avis: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


def _validate_summary(summary: str) -> tuple[bool, str | None]:
    """
    Valide un summary d'avis critique pour détecter les générations échouées.

    Critères de validation:
    1. Summary non vide
    2. Summary pas trop long (>50000 caractères = signe de malformation)
    3. Pas d'espaces consécutifs anormaux (100+ espaces = bug LLM)
    4. Structure markdown attendue présente (section 1 "LIVRES DISCUTÉS")
    5. Section 2 "COUPS DE CŒUR DES CRITIQUES" présente (génération complète)

    Args:
        summary: Le summary à valider

    Returns:
        Tuple (is_valid, error_message)
    """
    if not summary or summary is None:
        return False, "Aucun summary fourni"

    summary_stripped = summary.strip()

    # 1. Vérifier que le summary n'est pas vide
    if len(summary_stripped) == 0:
        return False, "Summary vide"

    # 2. Vérifier que le summary n'est pas suspicieusement long (> 50000 caractères)
    # Signe d'un tableau markdown tronqué/malformé
    if len(summary_stripped) > 50000:
        return False, "Summary trop long (probablement malformé/tronqué)"

    # 3. Détecter les séquences d'espaces anormalement longues (bug LLM)
    # Rechercher 10000+ espaces consécutifs (signe de génération malformée)
    # Note: 100 était trop restrictif et bloquait le formatage des tableaux markdown
    import re

    if re.search(r"\s{10000,}", summary):
        return False, "Summary malformé (espaces consécutifs anormaux détectés)"

    # 4. Vérifier la présence de la structure markdown attendue
    if "## 1. LIVRES DISCUTÉS" not in summary:
        return False, 'Structure markdown manquante (pas de section "LIVRES DISCUTÉS")'

    # 5. Vérifier la présence de la section "COUPS DE CŒUR DES CRITIQUES"
    # Cette section est toujours présente dans les générations réussies
    # Son absence indique une génération incomplète
    if "2. COUPS DE CŒUR DES CRITIQUES" not in summary:
        return (
            False,
            'Génération incomplète (pas de section "2. COUPS DE CŒUR DES CRITIQUES")',
        )

    return True, None


@app.post("/api/avis-critiques/save")
async def save_avis_critiques(request: SaveAvisCritiquesRequest) -> JSONResponse:
    """
    Sauvegarde un avis critique généré dans MongoDB.

    Args:
        request: episode_id, summary, summary_phase1, metadata

    Returns:
        success, avis_critique_id
    """
    from datetime import datetime
    from pathlib import Path

    memory_check = memory_guard.check_memory_limit()
    if memory_check:
        if "LIMITE MÉMOIRE DÉPASSÉE" in memory_check:
            memory_guard.force_shutdown(memory_check)
        print(f"⚠️ {memory_check}")

    try:
        if mongodb_service.avis_critiques_collection is None:
            raise HTTPException(
                status_code=500, detail="Service MongoDB non disponible"
            )

        # VALIDATION: Vérifier que le summary est valide AVANT sauvegarde
        is_valid, error_message = _validate_summary(request.summary)
        if not is_valid:
            logger.warning(
                f"Tentative de sauvegarde d'un summary invalide pour épisode {request.episode_id}: {error_message}"
            )

            # Écrire le contenu dans un fichier pour diagnostic
            debug_dir = Path("/tmp/avis_critiques_debug")
            debug_dir.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            debug_file = (
                debug_dir / f"validation_failed_{request.episode_id}_{timestamp}.md"
            )
            debug_file.write_text(request.summary, encoding="utf-8")

            logger.error("=" * 80)
            logger.error("❌ VALIDATION ÉCHEC - SUMMARY INVALIDE")
            logger.error(f"Épisode: {request.episode_id}")
            logger.error(f"Erreur: {error_message}")
            logger.error(f"Longueur: {len(request.summary)} caractères")
            logger.error(f"📁 Fichier debug: {debug_file}")
            logger.error("=" * 80)

            raise HTTPException(
                status_code=400,
                detail=f"Summary invalide: {error_message}. Le résultat n'a pas été sauvegardé.",
            )

        # Récupérer les infos de l'épisode pour episode_title et episode_date
        episode = mongodb_service.get_episode_by_id(request.episode_id)
        if not episode:
            raise HTTPException(status_code=404, detail="Épisode non trouvé")

        episode_title = episode.get("titre", "")
        episode_date_obj = episode.get("date")
        if isinstance(episode_date_obj, datetime):
            episode_date = episode_date_obj.strftime("%Y-%m-%d")
        else:
            episode_date = (
                str(episode_date_obj).split("T")[0] if episode_date_obj else ""
            )

        # Vérifier si avis existe déjà
        existing = mongodb_service.avis_critiques_collection.find_one(
            {"episode_oid": request.episode_id}
        )

        # Nettoyer metadata pour ne pas stocker page_text (trop volumineux)
        metadata_clean = {k: v for k, v in request.metadata.items() if k != "page_text"}

        avis_data = {
            "episode_oid": request.episode_id,
            "episode_title": episode_title,
            "episode_date": episode_date,
            "summary": request.summary,
            "summary_phase1": request.summary_phase1,
            "summary_origin": "llm_generation_phase2",
            "metadata_source": metadata_clean,
            "updated_at": datetime.now(UTC),
        }

        if existing:
            # Update
            mongodb_service.avis_critiques_collection.update_one(
                {"episode_oid": request.episode_id}, {"$set": avis_data}
            )
            avis_id = str(existing["_id"])
            logger.info(f"Avis critique mis à jour: {avis_id}")
        else:
            # Insert
            avis_data["created_at"] = datetime.now(UTC)
            insert_result = mongodb_service.avis_critiques_collection.insert_one(
                avis_data
            )
            avis_id = str(insert_result.inserted_id)
            logger.info(f"Avis critique créé: {avis_id}")

        return JSONResponse(content={"success": True, "avis_critique_id": avis_id})

    except HTTPException:
        # Re-raise HTTPException telles quelles (400, 404, etc.)
        raise
    except Exception as e:
        logger.error(f"Erreur sauvegarde avis: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/api/critiques")
async def create_critique(request: Request) -> JSONResponse:
    """
    Crée un nouveau critique.

    Body: {
        "nom": "Prénom Nom",
        "variantes": ["Variante 1", "Variante 2"],  # Optionnel
        "animateur": false
    }
    """
    try:
        if mongodb_service.critiques_collection is None:
            raise HTTPException(
                status_code=500, detail="Service MongoDB non disponible"
            )

        data = await request.json()

        # Valider les données
        if not data.get("nom"):
            raise HTTPException(status_code=400, detail="Le champ 'nom' est requis")

        # Préparer les variantes (enlever les doublons et les vides)
        variantes = data.get("variantes", [])
        if variantes:
            # Enlever les doublons et les chaînes vides
            variantes = list({v.strip() for v in variantes if v and v.strip()})
            # Enlever la variante si elle est identique au nom
            variantes = [v for v in variantes if v != data["nom"]]

        # Vérifier si un critique avec ce nom existe déjà
        existing = mongodb_service.critiques_collection.find_one({"nom": data["nom"]})
        if existing:
            # Comportement: Au lieu de rejeter, ajouter les variantes au critique existant
            # (Issue #154: permettre d'ajouter des variantes via l'interface de création)
            existing_variantes = set(existing.get("variantes", []))
            new_variantes = existing_variantes.union(set(variantes))

            # Mettre à jour le critique avec les nouvelles variantes
            from datetime import datetime

            mongodb_service.critiques_collection.update_one(
                {"_id": existing["_id"]},
                {
                    "$set": {
                        "variantes": list(new_variantes),
                        "updated_at": datetime.now(),
                    }
                },
            )

            # Récupérer le critique mis à jour
            updated_critique = mongodb_service.critiques_collection.find_one(
                {"_id": existing["_id"]}
            )

            if not updated_critique:
                raise HTTPException(
                    status_code=500, detail="Erreur lors de la mise à jour du critique"
                )

            critique = Critique(updated_critique)

            return JSONResponse(
                content={
                    **critique.to_dict(),
                    "message": "Variantes ajoutées au critique existant",
                },
                status_code=200,
            )

        # Préparer les données pour MongoDB (nouveau critique)
        critique_data = Critique.for_mongodb_insert(
            {
                "nom": data["nom"],
                "variantes": variantes,
                "animateur": data.get("animateur", False),
            }
        )

        # Insérer dans MongoDB
        result = mongodb_service.critiques_collection.insert_one(critique_data)

        # Récupérer le critique créé
        created_critique = mongodb_service.critiques_collection.find_one(
            {"_id": result.inserted_id}
        )

        if not created_critique:
            raise HTTPException(
                status_code=500, detail="Erreur lors de la création du critique"
            )

        critique = Critique(created_critique)

        return JSONResponse(content=critique.to_dict(), status_code=201)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la création du critique: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.put("/api/critiques/{critique_id}/variantes")
async def add_variante(critique_id: str, request: Request) -> JSONResponse:
    """
    Ajoute une variante à un critique existant.

    Body: {
        "variante": "Nouvelle variante"
    }
    """
    try:
        from bson import ObjectId

        if mongodb_service.critiques_collection is None:
            raise HTTPException(
                status_code=500, detail="Service MongoDB non disponible"
            )

        data = await request.json()
        variante = data.get("variante")

        if not variante:
            raise HTTPException(
                status_code=400, detail="Le champ 'variante' est requis"
            )

        # Récupérer le critique
        critique_doc = mongodb_service.critiques_collection.find_one(
            {"_id": ObjectId(critique_id)}
        )

        if not critique_doc:
            raise HTTPException(status_code=404, detail="Critique non trouvé")

        critique = Critique(critique_doc)

        # Ajouter la variante
        critique.add_variante(variante)

        # Mettre à jour dans MongoDB
        result = mongodb_service.critiques_collection.update_one(
            {"_id": ObjectId(critique_id)},
            {
                "$set": {
                    "variantes": critique.variantes,
                    "updated_at": critique.updated_at,
                }
            },
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Critique non trouvé")

        return JSONResponse(content=critique.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de l'ajout de la variante: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/api/emissions")
async def create_emission(request: Request) -> JSONResponse:
    """
    Crée une nouvelle émission.

    Body: {
        "episode_id": "ObjectId",
        "avis_critique_id": "ObjectId",
        "animateur_id": "ObjectId" (optionnel)
    }
    """
    try:
        from bson import ObjectId

        if (
            mongodb_service.episodes_collection is None
            or mongodb_service.emissions_collection is None
        ):
            raise HTTPException(
                status_code=500, detail="Service MongoDB non disponible"
            )

        data = await request.json()

        # Valider les données
        if not data.get("episode_id") or not data.get("avis_critique_id"):
            raise HTTPException(
                status_code=400,
                detail="Les champs 'episode_id' et 'avis_critique_id' sont requis",
            )

        # Récupérer l'épisode pour copier date et durée
        episode = mongodb_service.episodes_collection.find_one(
            {"_id": ObjectId(data["episode_id"])}
        )

        if not episode:
            raise HTTPException(status_code=404, detail="Épisode non trouvé")

        # Préparer les données pour MongoDB
        emission_data = Emission.for_mongodb_insert(
            {
                "episode_id": ObjectId(data["episode_id"]),
                "avis_critique_id": ObjectId(data["avis_critique_id"]),
                "date": episode.get("date"),
                "duree": episode.get("duree"),
                "animateur_id": (
                    ObjectId(data["animateur_id"]) if data.get("animateur_id") else None
                ),
                "avis_ids": [],  # Sera rempli dans une future issue
            }
        )

        # Insérer dans MongoDB
        result = mongodb_service.emissions_collection.insert_one(emission_data)

        # Récupérer l'émission créée
        created_emission = mongodb_service.emissions_collection.find_one(
            {"_id": result.inserted_id}
        )

        if not created_emission:
            raise HTTPException(
                status_code=500, detail="Erreur lors de la création de l'émission"
            )

        emission = Emission(created_emission)

        return JSONResponse(content=emission.to_dict(), status_code=201)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la création de l'émission: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


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
