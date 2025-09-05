# Documentation Développeurs - Back-Office LMELP

## Vue d'ensemble technique

Le Back-Office LMELP est une application web full-stack pour la gestion d'épisodes de podcast avec des fonctionnalités avancées de protection mémoire.

## Architecture

```
┌─────────────────┐    HTTP/JSON    ┌──────────────────┐    MongoDB    ┌─────────────┐
│   Frontend      │◄───────────────►│    Backend       │◄─────────────►│   Database  │
│   Vue.js        │                 │    FastAPI       │               │   MongoDB   │
│   Port 5173     │                 │ Port Auto-sélect │               │   Port 27017│
└─────────────────┘                 └──────────────────┘               └─────────────┘
         │                                   │
         ▼                                   ▼
┌─────────────────┐                 ┌──────────────────┐
│ Memory Guard    │                 │  Memory Guard    │
│ 100MB limit     │                 │  500MB limit     │
└─────────────────┘                 └──────────────────┘
```

## Stack technique

### Backend
- **FastAPI** : API REST moderne avec documentation automatique
- **MongoDB** : Base de données NoSQL pour stockage des épisodes
- **psutil** : Surveillance mémoire système
- **uvicorn** : Serveur ASGI haute performance

### Frontend
- **Vue.js 3** : Framework progressif avec Composition API
- **Axios** : Client HTTP pour communication API
- **Vite** : Build tool et dev server
- **Vitest** : Framework de tests avec @vue/test-utils

### Outils de développement
- **uv** : Gestionnaire de dépendances Python rapide
- **Ruff** : Linter et formatter Python
- **MyPy** : Type checker Python
- **Pre-commit** : Hooks de qualité de code
- **CI/CD** : Pipeline GitHub Actions (Python 3.11/3.12 + Node.js 18)

## Structure du projet

```
back-office-lmelp/
├── src/back_office_lmelp/          # Code backend Python
│   ├── models/                     # Modèles de données
│   ├── services/                   # Services métier
│   ├── utils/                      # Utilitaires (memory guard)
│   └── app.py                      # Application FastAPI
├── frontend/                       # Code frontend Vue.js
│   ├── src/
│   │   ├── components/            # Composants Vue
│   │   ├── services/              # Services API
│   │   └── utils/                 # Utilitaires frontend
│   └── tests/                     # Tests frontend (26 tests Vitest)
│       ├── unit/                  # Tests unitaires (EpisodeSelector, EpisodeEditor)
│       └── integration/           # Tests d'intégration (HomePage)
├── docs/                          # Documentation
│   ├── dev/                       # Documentation développeurs
│   └── user/                      # Documentation utilisateurs
└── tests/                         # Tests backend (12 tests pytest)
```

## Démarrage développement

### Prérequis
```bash
# Vérifier Python 3.11+
python --version

# Installer uv
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Installation
```bash
# Cloner le repository
git clone https://github.com/castorfou/back-office-lmelp.git
cd back-office-lmelp

# Installer dépendances Python
uv sync --extra dev

# Installer pre-commit hooks
pre-commit install

# Installer dépendances frontend
cd frontend
npm install
```

### Lancement développement

**Terminal 1 - Backend :**
```bash
# Démarrer MongoDB (si local)
mongod

# Démarrer l'API (sélection automatique de port)
python -m back_office_lmelp.app

# Ou spécifier un port si nécessaire
API_PORT=54322 python -m back_office_lmelp.app
```

**Terminal 2 - Frontend :**
```bash
cd frontend
npm run dev
```

**Accès :**
- Application : http://localhost:5173
- API Backend : Consultez les logs pour le port (ex: http://localhost:54324)
- API Docs : http://localhost:[PORT]/docs (remplacez [PORT])

## Commandes de développement

### Code quality
```bash
# Linting
ruff check .

# Formatting
ruff format .

# Type checking
mypy src/

# Pre-commit (tous les hooks)
pre-commit run --all-files
```

### Tests
```bash
# Suite complète (backend + frontend)
pytest tests/ -v && cd frontend && npm test -- --run

# Tests backend
pytest tests/ -v --cov=src --cov-report=term-missing

# Tests frontend
cd frontend
npm test -- --run
npm run test:ui  # Interface graphique
npm test -- --coverage  # Avec couverture
```

## Variables d'environnement

### Backend
- `API_PORT` : Port du serveur FastAPI (défaut: sélection automatique 54321-54350)
- `MONGODB_URL` : URL de connexion MongoDB (défaut: mongodb://localhost:27017)
- `MEMORY_LIMIT_MB` : Limite mémoire backend (défaut: 500)

### Frontend
- `VITE_API_BASE_URL` : URL de base de l'API
- `VITE_MEMORY_LIMIT_MB` : Limite mémoire frontend (défaut: 100)

## Conventions de code

### Python (Backend)
- **Style** : Ruff + Black compatible (ligne 88 caractères)
- **Types** : Annotations obligatoires avec MyPy
- **Imports** : Triés avec Ruff
- **Docstrings** : Style Google

### JavaScript (Frontend)
- **Style** : Prettier + ESLint
- **Vue** : Composition API + script setup
- **Nommage** : camelCase JS, kebab-case templates

### Git
- **Commits** : Conventional commits (feat:, fix:, docs:)
- **Branches** : feature/, bugfix/, hotfix/
- **PRs** : Template avec checklist

## Ressources

- [Architecture détaillée](architecture.md)
- [Documentation API](api.md)
- [Découverte automatique de port](port-discovery.md)
- [Schéma base de données](database.md)
- [Guide déploiement](deployment.md)
- [Sécurité et garde-fous](security.md)
