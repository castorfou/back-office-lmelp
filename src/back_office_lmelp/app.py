"""Application FastAPI principale."""

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .models.episode import Episode
from .services.mongodb_service import mongodb_service


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Gestion du cycle de vie de l'application."""
    # Démarrage
    if not mongodb_service.connect():
        raise Exception("Impossible de se connecter à MongoDB")
    print("Connexion MongoDB établie")

    yield

    # Arrêt
    mongodb_service.disconnect()
    print("Connexion MongoDB fermée")


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
    try:
        episodes_data = mongodb_service.get_all_episodes()
        episodes = [Episode(data).to_summary_dict() for data in episodes_data]
        return episodes
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}") from e


@app.get("/api/episodes/{episode_id}", response_model=dict[str, Any])
async def get_episode(episode_id: str) -> dict[str, Any]:
    """Récupère un épisode par son ID."""
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
    episode_id: str, description_corrigee: str
) -> dict[str, str]:
    """Met à jour la description corrigée d'un épisode."""
    try:
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


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))

    uvicorn.run(app, host=host, port=port)
