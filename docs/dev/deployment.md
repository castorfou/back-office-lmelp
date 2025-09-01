# Déploiement

Cette section couvre les aspects de déploiement du back-office LMELP.

## Environnements

### Développement
- **Local** : Port 54322 (backend) + 5173 (frontend)
- **Docker** : Via devcontainer VS Code

### Production
- **Backend** : FastAPI avec uvicorn
- **Frontend** : Build statique via npm
- **Base de données** : MongoDB

## Configuration

### Variables d'environnement
```bash
# Backend
API_PORT=54322
PYTHONPATH=/workspaces/back-office-lmelp/src

# Base de données
MONGODB_URL=mongodb://localhost:27017
DATABASE_NAME=lmelp
```

### Commandes de déploiement
```bash
# Backend
uv run python -m back_office_lmelp.app

# Frontend
cd frontend && npm run build
```

## CI/CD

Le déploiement automatique est géré par GitHub Actions :
- **Tests** : Python 3.11/3.12 + Node.js 18
- **Qualité** : Ruff, MyPy, pre-commit
- **Sécurité** : Analyse des secrets et dépendances
