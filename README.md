# Back-office LMELP

Interface de gestion pour la base de données du projet [LMELP](https://github.com/castorfou/lmelp) (Le Masque et La Plume).

[![CI/CD Pipeline](https://github.com/castorfou/back-office-lmelp/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/castorfou/back-office-lmelp/actions/workflows/ci-cd.yml)
[![Documentation](https://img.shields.io/badge/docs-MkDocs-blue.svg)](https://castorfou.github.io/back-office-lmelp/)
[![codecov](https://codecov.io/gh/castorfou/back-office-lmelp/branch/main/graph/badge.svg)](https://codecov.io/gh/castorfou/back-office-lmelp)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Code style: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)

## 🎯 Objectif

Nettoyer et corriger les données des épisodes du Masque et la Plume, en particulier les descriptions générées automatiquement qui peuvent contenir des erreurs de transcription.

## 🏗️ Architecture

### Stack technique
- **Backend** : FastAPI + Python 3.11
- **Frontend** : Vue.js 3 + Vite
- **Base de données** : MongoDB (collection `masque_et_la_plume`)
- **Tests** : pytest (backend) + Vitest (frontend)

### Structure du projet

```
├── src/back_office_lmelp/          # Backend FastAPI
│   ├── app.py                      # Application principale
│   ├── services/                   # Services (MongoDB, etc.)
│   └── models/                     # Modèles de données
├── frontend/                       # Interface Vue.js
│   ├── src/components/            # Composants Vue
│   ├── tests/                     # Tests frontend
│   └── README.md                  # Doc frontend détaillée
├── docs/                          # Documentation projet
└── pyproject.toml                 # Configuration Python/uv
```

## 🚀 Installation

### Prérequis

- **Python 3.11+** avec [uv](https://docs.astral.sh/uv/) (gestionnaire de paquets)
- **Node.js 18+** pour le frontend
- **MongoDB** accessible (configuré dans `.env`)

### Configuration

1. **Cloner et installer le backend** :
```bash
git clone [URL_DU_REPO]
cd back-office-lmelp

# Ouvrir avec code
code .

# Open in container
> Dev Containers: Open in container
```

2. **Configuration MongoDB** :
```bash
# Fichier .env
MONGODB_URL=mongodb://localhost:27017/masque_et_la_plume
API_HOST=0.0.0.0
API_PORT=8000

# Azure OpenAI (pour fonctionnalités futures)
AZURE_OPENAI_API_KEY=your_key_here
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
```

## 🎮 Lancement

### Démarrage rapide

```bash
# lancement via script
./scripts/start-dev.sh
```

ou en demarrant separemment backend et frontend

```bash
# Terminal 1 : Backend FastAPI (découverte automatique de port)
python -m back_office_lmelp.app
# ➜ API disponible sur port automatiquement détecté (voir sortie console)

# Terminal 2 : Frontend Vue.js (découverte automatique du backend)
cd frontend && npm run dev
# ➜ Interface sur http://localhost:5173
```

### Système de découverte dynamique

Le backend et le frontend se synchronisent automatiquement via un fichier `.backend-port.json` :

```bash
# Le backend écrit ses informations de port au démarrage
🚀 Démarrage du serveur sur 127.0.0.1:54323
📡 Port discovery file created: /workspaces/back-office-lmelp/.backend-port.json

# Le frontend lit automatiquement ces informations
Using backend target from discovery file: http://127.0.0.1:54323
```

**Avantages :**
- ✅ **Zéro configuration** : pas de gestion manuelle des ports
- ✅ **Toujours fonctionnel** : évite les conflits de ports
- ✅ **Ordre flexible** : démarrez backend/frontend dans n'importe quel ordre
- ✅ **Fallback intelligent** : port 54322 par défaut si fichier manquant

### Vérification

- **API** : Voir l'URL dans la sortie console du backend pour la documentation Swagger
- **Frontend** : http://localhost:5173 (interface principale)
- **Documentation** : https://castorfou.github.io/back-office-lmelp/ (MkDocs)
- **Santé** : Tester l'endpoint `/api/episodes` avec l'URL affichée au démarrage

## 📖 Utilisation

### Interface utilisateur

1. **Sélectionner un épisode** dans la liste déroulante (217 épisodes disponibles)
2. **Visualiser/Modifier** titre ou description
3. **Sauvegarde automatique** après 2 secondes d'inactivité

### Fonctionnalités principales

#### Édition des épisodes
- ✅ **Tri automatique** : Épisodes par date décroissante
- ✏️ **Édition en temps réel** : Modification libre du texte
- 💾 **Auto-save** : Sauvegarde transparente dans `description_corrigee`, `titre_corrige`
- 🔄 **Gestion d'erreurs** : Retry automatique et messages explicites
- 📱 **Interface responsive** : Compatible mobile/desktop

#### Extraction Livres et Auteurs ⭐ **NOUVEAU**
- 📚 **Extraction automatique** : Parse les tableaux markdown des avis critiques
- 📋 **Interface tableau** : Colonnes triables (Auteur/Titre/Éditeur)
- 🔍 **Recherche temps réel** : Filtrage par auteur, titre ou éditeur
- 📊 **Deux sources** : "Livres discutés au programme" + "Coups de cœur des critiques"
- 🎯 **Vue par épisode** : Sélection d'épisodes avec avis critiques

### API disponible

```bash
# Lister tous les épisodes
GET /api/episodes

# Détails d'un épisode
GET /api/episodes/{id}

# Mettre à jour la description corrigée
PUT /api/episodes/{id}

# Extraction livres et auteurs ⭐ NOUVEAU
GET /api/livres-auteurs           # Tous les livres extraits
GET /api/livres-auteurs?episode_oid={id}  # Livres d'un épisode
GET /api/episodes-with-reviews    # Episodes ayant des avis critiques
```

**📚 Documentation complète** : https://castorfou.github.io/back-office-lmelp/

## 🧪 Tests

### Suite complète
```bash
# Lancer tous les tests (backend + frontend)
pytest tests/ -v && cd frontend && npm test -- --run
```

### Backend
```bash
# Tests Python avec couverture
pytest tests/ -v --cov=src --cov-report=term-missing

# Linting et formatage
ruff check . --output-format=github
ruff format .

# Type checking
mypy src/
```

### Frontend
```bash
cd frontend

# Tests unitaires et d'intégration (Vitest)
npm test -- --run

# Tests avec interface graphique
npm run test:ui

# Tests en mode watch
npm test -- --watch

# Tests avec couverture
npm test -- --coverage
```

## 🔧 Développement

### Avec VS Code + Devcontainer (Recommandé)

Si vous avez Docker et VS Code :

```bash
# 1. Authentifiez-vous à ghcr.io (si nécessaire)
# Créez un Personal Access Token : https://github.com/settings/tokens/new
# Permissions : read:packages
docker login ghcr.io -u VOTRE_USERNAME

# 2. Ouvrez dans VS Code
code .
# VS Code proposera "Reopen in Container"
```

### Ajout de fonctionnalités

1. **Backend** : Ajouter routes dans `src/back_office_lmelp/app.py`
2. **Frontend** : Créer composants dans `frontend/src/components/`
3. **Tests** : Couvrir les nouvelles fonctionnalités
4. **Documentation** : Mettre à jour les README

### Architecture des données

**Collection `episodes`** :
```javascript
{
  "_id": ObjectId,
  "titre": "Titre de l'épisode",
  "titre_corrige": "Titre du super épisode", // ⭐ Ajouté par le back-office
  "date": ISODate,
  "type": "livres|cinema|theatre",
  "description": "Description originale France Inter",
  "description_corrigee": "Description corrigée manuellement", // ⭐ Ajouté par le back-office
  "transcription": "Transcription Whisper (avec erreurs possibles)"
}
```

### Qualité du code

- **Python** : Ruff (linting + formatage), MyPy (types)
- **JavaScript** : Tests Vitest complets avec @vue/test-utils
- **Git** : Pre-commit hooks configurés (detect-secrets, formatage)
- **CI/CD** : Pipeline complet (Python 3.11/3.12 + Node.js 18)
- **Documentation** : MkDocs avec Material Design déployé sur GitHub Pages

### Tests détaillés

**Backend** :
- API endpoints FastAPI
- Services MongoDB (CRUD épisodes)
- Utilitaires (memory guard, etc.)

**Frontend** :
- **EpisodeSelector** : 7 tests (chargement, sélection, erreurs)
- **EpisodeEditor** : 12 tests (édition, sauvegarde, validation)
- **HomePage** : 7 tests d'intégration (flux complets)

## 📋 Roadmap

### MVP 0 ✅ **TERMINÉ**
- ✅ Interface de base pour correction des descriptions
- ✅ Sauvegarde automatique en base MongoDB
- ✅ **Extraction Livres/Auteurs** : Interface tableau avec parsing markdown
- ✅ Tests complets : 245 tests validés (161 backend + 84 frontend)
- ✅ CI/CD pipeline avec validation complète
- ✅ Architecture full-stack (FastAPI + Vue.js 3)
- ✅ Documentation MkDocs + GitHub Pages avec Material Design

### Versions futures
- 🤖 **IA** : Suggestions de corrections via Azure OpenAI
- 🔍 **Recherche** : Filtres avancés par date, type, contenu
- 📊 **Analytics** : Statistiques de correction et qualité
- 👥 **Multi-user** : Gestion des utilisateurs et permissions
- 📤 **Export** : Sauvegarde des données nettoyées

## 💡 Contexte projet

### Problématique LMELP

Le projet [LMELP](https://github.com/castorfou/lmelp) développe un système de recommandation littéraire basé sur l'affinité avec les critiques du Masque et la Plume.

**Hiérarchie de fiabilité des données** :
- **✅ FIABLES** : Titres et descriptions (source France Inter)
- **⚠️ SUSPECTES** : Transcriptions Whisper avec erreurs de noms propres
- **❌ DÉRIVÉES** : Données extraites des transcriptions erronées

### Stratégie de nettoyage

1. **Partir des transcriptions** légèrement erronées (noms d'auteurs incorrects)
2. **Extraire les entités** (auteurs, livres, éditeurs) avec les erreurs
3. **Corriger les entités** via interface back-office + IA
4. **Stocker proprement** dans de nouvelles collections MongoDB
5. **Optionnel** : Corriger les transcriptions a posteriori

## 🤝 Contribution

1. **Fork** le repository
2. **Créer** une branche feature (`git checkout -b feature/amazing-feature`)
3. **Tester** les modifications (`npm test` + `uv run pytest`)
4. **Commiter** (`git commit -m 'feat: add amazing feature'`)
5. **Push** (`git push origin feature/amazing-feature`)
6. **Créer** une Pull Request

### Conventions

- **Commits** : [Conventional Commits](https://conventionalcommits.org/)
- **Code** : Respecter les linters (Ruff, ESLint)
- **Tests** : Couverture > 80% obligatoire
- **Docs** : Mettre à jour les README si nécessaire

## 📄 Licence

MIT - Voir [LICENSE](LICENSE) pour plus de détails.

## 🔗 Liens utiles

- **📚 Documentation** : https://castorfou.github.io/back-office-lmelp/
- **Projet principal** : https://github.com/castorfou/lmelp
- **FastAPI** : https://fastapi.tiangolo.com/
- **Vue.js** : https://vuejs.org/
- **MongoDB** : https://docs.mongodb.com/
- **uv (Python)** : https://docs.astral.sh/uv/
- **MkDocs** : https://www.mkdocs.org/
