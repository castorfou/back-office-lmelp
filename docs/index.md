# Back-Office LMELP - Documentation

Bienvenue dans la documentation du Back-Office LMELP, une application web pour la gestion et l'édition des descriptions d'épisodes de podcast.

## Vue d'ensemble

Cette application permet de :
- Consulter la liste des épisodes de podcast
- Visualiser les descriptions originales et corrigées
- Modifier et sauvegarder les descriptions d'épisodes
- Bénéficier de garde-fous mémoire pour éviter les crashes

## Architecture

- **Backend** : FastAPI avec garde-fous mémoire intégrés
- **Frontend** : Vue.js avec surveillance mémoire automatique
- **Base de données** : MongoDB
- **Environnement** : Docker devcontainer avec uv

## Documentation

### 👨‍💻 Pour les développeurs (`docs/dev/`)

- **[README.md](dev/README.md)** : Vue d'ensemble technique du projet
- **[architecture.md](dev/architecture.md)** : Architecture système, composants et interactions
- **[api.md](dev/api.md)** : Documentation complète des endpoints API
- **[database.md](dev/database.md)** : Schéma MongoDB et modèles de données
- **[deployment.md](dev/deployment.md)** : Guide de déploiement et configuration
- **[development.md](dev/development.md)** : Setup développement et conventions de code
- **[security.md](dev/security.md)** : Garde-fous mémoire et gestion des erreurs

### 👤 Pour les utilisateurs (`docs/user/`)

- **[README.md](user/README.md)** : Guide de démarrage rapide
- **[interface.md](user/interface.md)** : Guide complet de l'interface utilisateur
- **[episodes.md](user/episodes.md)** : Gestion et édition des épisodes
- **[troubleshooting.md](user/troubleshooting.md)** : Résolution des problèmes courants

## Démarrage rapide

### Prérequis
- Docker et VS Code avec devcontainer
- Ou Python 3.11+ avec uv

### Lancement
```bash
# Backend (port 54321)
PYTHONPATH=/workspaces/back-office-lmelp/src python -m back_office_lmelp.app

# Frontend (port 5173)
cd frontend && npm run dev

# Documentation locale (port 8000)
uv run mkdocs serve
```

### Accès
- **Application** : http://localhost:5173
- **API Backend** : http://localhost:54322
- **Documentation API** : http://localhost:54322/docs
- **Documentation MkDocs** : http://localhost:8000 (local) | [GitHub Pages](https://castorfou.github.io/back-office-lmelp/) (production)

## Fonctionnalités principales

### 🛡️ Garde-fous mémoire
- **Backend** : Limite 500MB avec surveillance continue
- **Frontend** : Limite 100MB avec rechargement d'urgence
- **Alertes** : Avertissements à 80% de la limite
- **Protection** : Arrêt automatique si limite dépassée

### 📝 Gestion des épisodes
- Sélection d'épisodes via dropdown
- Affichage des métadonnées complètes
- Édition en temps réel des descriptions
- Sauvegarde automatique avec indicateur visuel

### 🧪 Tests complets
- **Suite de tests** : 38 tests validés (12 backend + 26 frontend)
- **CI/CD Pipeline** : GitHub Actions avec Python 3.11/3.12 + Node.js 18
- **Couverture backend** : 40% avec pytest + coverage
- **Tests frontend** : Vitest + @vue/test-utils (EpisodeSelector, EpisodeEditor, HomePage)

### 🔧 Qualité de code
- **Linting** : Ruff avec configuration optimisée
- **Type checking** : MyPy avec strictness progressive
- **Pre-commit hooks** : Formatage, sécurité, qualité automatiques
- **Documentation** : MkDocs + Material Design sur GitHub Pages

## Problèmes connus

- ~~**Port 54321 occupé** : ✅ **Résolu** (voir [issue #1](https://github.com/castorfou/back-office-lmelp/issues/1))~~
- **Configuration ports** : Refonte nécessaire pour découverte automatique (voir [issue #2](https://github.com/castorfou/back-office-lmelp/issues/2))
- **CI/CD sur branches** : Tests ne s'exécutent que sur main/develop (voir [issue #10](https://github.com/castorfou/back-office-lmelp/issues/10))

## Contribuer

1. Consultez la [documentation développeurs](dev/README.md)
2. Suivez les [conventions de développement](dev/development.md)
3. Implémentez les [tests unitaires](https://github.com/castorfou/back-office-lmelp/issues/4)

## Support

- **Issues** : [GitHub Issues](https://github.com/castorfou/back-office-lmelp/issues)
- **Documentation** : Cette documentation MkDocs
- **Code** : [Repository GitHub](https://github.com/castorfou/back-office-lmelp)
