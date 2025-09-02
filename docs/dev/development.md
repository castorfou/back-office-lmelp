# Guide de développement

Ce guide détaille l'environnement de développement et les bonnes pratiques.

## Environnement de développement

### Prérequis
- **Python 3.11+** avec uv
- **Node.js 18+** avec npm
- **Docker** pour devcontainer (optionnel)
- **MongoDB** local ou distant

### Installation
```bash
# Cloner le projet
git clone https://github.com/castorfou/back-office-lmelp.git
cd back-office-lmelp

# Backend
uv sync --extra dev
pre-commit install

# Frontend
cd frontend && npm install
```

## Structure du projet

```
back-office-lmelp/
├── src/                    # Code Python backend
│   └── back_office_lmelp/  # Package principal
├── frontend/               # Application Vue.js
│   ├── src/               # Code source frontend
│   └── tests/             # Tests frontend
├── tests/                 # Tests backend
├── docs/                  # Documentation
└── pyproject.toml         # Configuration Python
```

## Développement

### Backend (FastAPI)
```bash
# Lancer le serveur de développement (sélection automatique de port)
PYTHONPATH=/workspaces/back-office-lmelp/src python -m back_office_lmelp.app

# Ou spécifier un port manuellement
API_PORT=54325 PYTHONPATH=/workspaces/back-office-lmelp/src python -m back_office_lmelp.app

# Tests
uv run pytest tests/ -v --cov=src

# Qualité de code
uv run ruff check .
uv run ruff format .
uv run mypy src/
```

### Frontend (Vue.js)
```bash
cd frontend

# Serveur de développement
npm run dev

# Tests
npm test
npm run test:coverage

# Build
npm run build
```

### Sélection automatique de port

Le backend implémente une sélection automatique de port pour éviter les conflits lors du développement.

#### Stratégie de priorité

1. **Variable d'environnement** : `API_PORT` si définie (comportement manuel)
2. **Port préféré** : 54321 (essai automatique)
3. **Plage de fallback** : 54322-54350 (scan séquentiel)
4. **Attribution OS** : En dernier recours si tous les ports sont occupés

#### Utilisation

```bash
# Démarrage automatique (recommandé)
python -m back_office_lmelp.app
# 🚀 Démarrage du serveur sur 0.0.0.0:54323 (port automatiquement sélectionné)

# Démarrage manuel (si besoin de port spécifique)
API_PORT=8000 python -m back_office_lmelp.app
# 🚀 Démarrage du serveur sur 0.0.0.0:8000
```

#### Avantages

- ✅ **Zero configuration** : `python -m back_office_lmelp.app` fonctionne toujours
- ✅ **Résistant aux conflits** : Gère les ports occupés gracieusement
- ✅ **Compatible** : Variable d'environnement `API_PORT` toujours supportée
- ✅ **Feedback clair** : Indication quand le port est sélectionné automatiquement

### Dynamic Port Discovery

Le système de découverte dynamique de port synchronise automatiquement les ports entre le backend FastAPI et le proxy Vite du frontend.

#### Fonctionnement

1. **Backend** : Au démarrage, écrit ses informations de port dans `.backend-port.json`
2. **Frontend** : Vite lit ce fichier au démarrage pour configurer le proxy automatiquement
3. **Nettoyage** : Le fichier est supprimé à l'arrêt du backend

#### Fichier de découverte (`/.backend-port.json`)

```json
{
  "port": 54323,
  "host": "localhost",
  "timestamp": 1640995200,
  "url": "http://localhost:54323"
}
```

#### Configuration

- **Sélection automatique** : Aucune configuration requise, port auto-découvert
- **Fallback frontend** : Port 54322 si le fichier est manquant ou obsolète (>30s)
- **Développement** : Permet de démarrer backend/frontend dans n'importe quel ordre

#### Tests

```bash
# Tests sélection automatique de port
PYTHONPATH=/workspaces/back-office-lmelp/src uv run pytest tests/test_automatic_port_selection.py -v

# Tests backend port discovery
PYTHONPATH=/workspaces/back-office-lmelp/src uv run pytest tests/test_dynamic_port_discovery.py -v

# Tests frontend port discovery
cd frontend && npm test -- --run tests/unit/PortDiscovery.test.js
```

## Qualité de code

### Pre-commit hooks
- **Formatage** : Ruff, Prettier
- **Linting** : Ruff, ESLint
- **Sécurité** : detect-secrets
- **Validation** : YAML, JSON, TOML

### Standards
- **Python** : PEP 8 avec Ruff
- **JavaScript** : Standard avec ESLint
- **Tests** : Couverture minimale 40%
- **Documentation** : Docstrings obligatoires

## CI/CD Pipeline

### Déclencheurs

Le pipeline CI/CD se déclenche automatiquement sur :
- **Tous les pushs** sur n'importe quelle branche (`branches: ['**']`)
- **Pull requests** vers `main`

Cette configuration offre un **feedback immédiat** sur chaque commit, permettant une détection précoce des régressions.

### Jobs exécutés

- ✅ **Tests backend** (Python 3.11 + 3.12)
- ✅ **Tests frontend** (Node.js 18)
- ✅ **Security scan** (detect-secrets)
- ✅ **Quality gate** (validation de tous les jobs)
- 🚀 **Déploiements** (uniquement sur `main`)

### Optimisations

- **Concurrence** : Isolation par branche (`cancel-in-progress: true`)
- **Cache** : Dependencies Python (uv) et Node.js (npm)
- **Déploiement conditionnel** : Staging/Production uniquement sur `main`
