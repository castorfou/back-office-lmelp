"""Application FastAPI principale."""

import os
import socket
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, suppress
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from thefuzz import process

from .models.episode import Episode
from .services.babelio_service import babelio_service
from .services.books_extraction_service import books_extraction_service
from .services.fixture_updater import FixtureUpdaterService
from .services.mongodb_service import mongodb_service
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


class FixtureUpdateRequest(BaseModel):
    """Modèle pour les requêtes de mise à jour de fixtures."""

    calls: list[CapturedCall]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Gestion du cycle de vie de l'application."""
    try:
        # Démarrage
        if not mongodb_service.connect():
            raise Exception("Impossible de se connecter à MongoDB")
        print("Connexion MongoDB établie")

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
    limit: int | None = None, episode_oid: str | None = None
) -> list[dict[str, Any]]:
    """Récupère la liste des livres/auteurs extraits des avis critiques via parsing des tableaux markdown (format simplifié : auteur/titre/éditeur)."""
    # Vérification mémoire
    memory_check = memory_guard.check_memory_limit()
    if memory_check:
        if "LIMITE MÉMOIRE DÉPASSÉE" in memory_check:
            memory_guard.force_shutdown(memory_check)
        print(f"⚠️ {memory_check}")

    try:
        # Récupérer les avis critiques selon les paramètres
        if episode_oid:
            # Récupérer seulement les avis critiques de cet épisode
            avis_critiques = mongodb_service.get_critical_reviews_by_episode_oid(
                episode_oid
            )
        else:
            # Récupérer tous les avis critiques
            avis_critiques = mongodb_service.get_all_critical_reviews(limit=limit)

        if not avis_critiques:
            return []

        # Extraire les informations bibliographiques via parsing markdown
        extracted_books = await books_extraction_service.extract_books_from_reviews(
            avis_critiques
        )

        # Formater pour l'affichage simplifié (auteur/titre/éditeur uniquement)
        formatted_books = books_extraction_service.format_books_for_simplified_display(
            extracted_books
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

        # Récupérer les détails des épisodes correspondants
        episodes_with_reviews = []
        for episode_oid in unique_episode_oids:
            episode_data = mongodb_service.get_episode_by_id(episode_oid)
            if episode_data:
                episode = Episode(episode_data)
                episodes_with_reviews.append(episode.to_summary_dict())

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

        # Extraire mots individuels de plus de 3 caractères
        words = [word for word in full_text.split() if len(word) > 3]

        # Nettoyer les mots (enlever ponctuation)
        clean_words = [re.sub(r"[^\w\-\'àâäéèêëïîôöùûüÿç]", "", word) for word in words]
        clean_words = [word for word in clean_words if len(word) > 3]

        # Prioriser les segments entre guillemets, puis les mots longs
        search_candidates = quoted_segments + clean_words

        # Recherche fuzzy pour le titre
        # D'abord chercher dans les segments entre guillemets (priorité haute)
        quoted_matches = (
            process.extract(request.query_title, quoted_segments, limit=5)
            if quoted_segments
            else []
        )

        # Puis chercher dans tous les candidats
        all_matches = process.extract(request.query_title, search_candidates, limit=10)

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
                request.query_author, search_candidates, limit=10
            )
            # Filtrer manuellement par score
            author_matches = [
                (match, score) for match, score in author_matches_raw if score >= 75
            ]

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

        # Recherche dans les avis critiques (auteurs, livres, éditeurs)
        critical_reviews_results = (
            mongodb_service.search_critical_reviews_for_authors_books(q, limit)
        )

        # Structure de la réponse
        response = {
            "query": q,
            "results": {
                "auteurs": critical_reviews_results["auteurs"],
                "livres": critical_reviews_results["livres"],
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
