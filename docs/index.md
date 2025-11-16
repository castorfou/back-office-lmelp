# Back-Office LMELP - Documentation

Bienvenue dans la documentation du Back-Office LMELP, une application web pour la gestion et l'édition des descriptions d'épisodes de podcast.

## Vue d'ensemble

Cette application permet de :

- Consulter la liste des épisodes de podcast

- Visualiser/Modifier les titres/descriptions (on conserve les versions originales et modifiees) des episodes

- Corriger les auteurs / livres / edtiteurs issus des avis ctitiques

- Rechercher dans les auteurs, livres, editeurs et episodes


## Architecture

- **Backend** : FastAPI avec garde-fous mémoire intégrés
- **Frontend** : Vue.js avec surveillance mémoire automatique
- **Base de données** : MongoDB
- **Environnement** : Docker devcontainer avec uv pour le developpement, image docker pour le deploiement (pour installation PC ou Nas)

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
- **[advanced-search.md](user/advanced-search.md)** : Recherche avancée avec filtres et pagination
- **[troubleshooting.md](user/troubleshooting.md)** : Résolution des problèmes courants

## Démarrage rapide

### Prérequis
- Docker et VS Code avec devcontainer
- Ou Python 3.11+ avec uv

### Lancement

en mode developpement

```bash
# Lancement backend + frontend
./scripts/start-dev.sh

# Documentation locale (port 8000)
mkdocs serve
```

en mode image docker

voir instructions dans `docker/deployment/README.md`

### Accès developpemet
- **Application** : http://localhost:5173
- **API Backend** : http://localhost:54322
- **Documentation API** : http://localhost:54322/docs
- **Documentation MkDocs** : http://localhost:8000 (local) | [GitHub Pages](https://castorfou.github.io/back-office-lmelp/) (production)

### Acces image docker
- **Application** : http://localhost:8080

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
- **Suite de tests** :
- **CI/CD Pipeline** : GitHub Actions avec Python 3.11/3.12 + Node.js 18
- **Couverture backend** : 40% avec pytest + coverage
- **Tests frontend** : Vitest + @vue/test-utils (EpisodeSelector, EpisodeEditor, HomePage)

### 🔧 Qualité de code
- **Linting** : Ruff avec configuration optimisée
- **Type checking** : MyPy avec strictness progressive
- **Pre-commit hooks** : Formatage, sécurité, qualité automatiques
- **Documentation** : MkDocs + Material Design sur GitHub Pages

## Contribuer

1. Consultez la [documentation développeurs](dev/README.md)
2. Suivez les [conventions de développement](dev/development.md)
3. Implémentez les [tests unitaires](https://github.com/castorfou/back-office-lmelp/issues/4)

## Support

- **Issues** : [GitHub Issues](https://github.com/castorfou/back-office-lmelp/issues)
- **Documentation** : Cette documentation MkDocs
- **Code** : [Repository GitHub](https://github.com/castorfou/back-office-lmelp)
