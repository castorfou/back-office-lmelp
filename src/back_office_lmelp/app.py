"""Application FastAPI principale."""

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, suppress
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from .models.episode import Episode
from .services.mongodb_service import mongodb_service
from .utils.memory_guard import memory_guard
from .utils.port_discovery import PortDiscovery


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
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
    ],  # Vue.js dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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

        # Mettre à jour la description
        success = mongodb_service.update_episode_description(
            episode_id, description_corrigee
        )
        if not success:
            raise HTTPException(status_code=400, detail="Échec de la mise à jour")

        return {"message": "Description mise à jour avec succès"}
    except HTTPException:
        raise
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

    # Nettoyer le fichier de découverte de port
    with suppress(Exception):
        port_file = PortDiscovery.get_port_file_path()
        PortDiscovery.cleanup_port_file(port_file)
        print("🧹 Port discovery file cleaned up")


def main():
    """Fonction principale pour démarrer le serveur."""
    global _server_instance

    import signal

    import uvicorn

    # Enregistrer les gestionnaires de signaux
    signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # Termination

    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))

    print(f"🚀 Démarrage du serveur sur {host}:{port}")
    print("🛡️ Garde-fou mémoire activé")

    # Create port discovery file for frontend
    port_file = PortDiscovery.get_port_file_path()
    PortDiscovery.write_port_info(port, port_file, host)
    print(f"📡 Port discovery file created: {port_file}")

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
            port_file = PortDiscovery.get_port_file_path()
            PortDiscovery.cleanup_port_file(port_file)
        print("✅ Arrêt complet")


if __name__ == "__main__":
    main()
