# Docker - Back-Office LMELP

Ce répertoire contient les fichiers Docker pour **back-office-lmelp**.

## Structure

```
docker/
├── build/              # Utilisé par CI/CD pour construire les images Docker
│   ├── backend/
│   │   └── Dockerfile  # Image backend (FastAPI + MongoDB)
│   └── frontend/
│       └── Dockerfile  # Image frontend (Vue.js + Vite)
│
└── deployment/         # Utilisé pour déployer les images (PC local ou NAS)
    ├── docker-compose.yml  # Configuration Docker Compose
    ├── .env.template       # Template de variables d'environnement
    └── README.md           # Guide de déploiement complet
```

## 🏗️ Build (CI/CD)

Le répertoire `build/` contient les Dockerfiles utilisés par GitHub Actions pour construire les images Docker.

**Fichier utilisé par :** `.github/workflows/docker-publish.yml`

**Images publiées :**
- Backend : `ghcr.io/castorfou/lmelp-backend:latest`
- Frontend : `ghcr.io/castorfou/lmelp-frontend:latest`

### Architecture multi-stage

Les Dockerfiles utilisent des builds multi-stage pour optimiser la taille des images finales.

## 🚀 Deployment (Utilisation)

Le répertoire `deployment/` contient les fichiers pour déployer back-office-lmelp sur votre environnement.

**👉 Pour déployer, consultez :** [deployment/README.md](deployment/README.md)

### Déploiement rapide

```bash
cd docker/deployment/
cp .env.template .env
# Éditer .env avec votre configuration MongoDB
docker compose up -d
```

**Accès** :
- Frontend : **http://localhost:8080**
- Backend API : **http://localhost:8000**
- Documentation API : **http://localhost:8000/docs**

## 📚 Documentation

- [Guide de déploiement complet](deployment/README.md)
- [Documentation Docker](../docs/deployment/docker-setup.md)
- [Images Docker GitHub Container Registry](https://github.com/castorfou/back-office-lmelp/pkgs/container/lmelp-backend)

## 🔧 Développement local

Pour le développement local, utilisez les commandes du projet principal :

```bash
# Backend
PYTHONPATH=/workspaces/back-office-lmelp/src python -m back_office_lmelp.app

# Frontend
cd frontend && npm run dev
```

Consultez [CLAUDE.md](../CLAUDE.md) pour les détails complets du développement.
