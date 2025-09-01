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
# Lancer le serveur de développement
PYTHONPATH=/workspaces/back-office-lmelp/src API_PORT=54322 python -m back_office_lmelp.app

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
