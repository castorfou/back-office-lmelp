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
- **Intégration Calibre** : Accès SQLite lecture seule (optionnel)
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

2. **Configuration MongoDB et Azure OpenAI** :
```bash
# Fichier .env
MONGODB_URL=mongodb://localhost:27017/masque_et_la_plume
API_HOST=0.0.0.0
API_PORT=8000

# Azure OpenAI (requis pour génération LLM d'avis critiques)
AZURE_OPENAI_API_KEY=your_key_here
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_VERSION=2025-03-01-preview
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o
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

Le backend et le frontend se synchronisent automatiquement via un fichier `.dev-ports.json` :

```bash
# Le backend écrit ses informations de port au démarrage
🚀 Démarrage du serveur sur 127.0.0.1:54323
📡 Port discovery file created: /workspaces/back-office-lmelp/.dev-ports.json

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
- 💾 **Auto-save** : Sauvegarde directe des corrections dans `titre` et `description`
- 🔄 **Gestion d'erreurs** : Retry automatique et messages explicites
- 📱 **Interface responsive** : Compatible mobile/desktop

#### Génération LLM d'Avis Critiques (2 phases)
- 🤖 **Génération automatique** : Résumés structurés depuis transcriptions Whisper
- 🔄 **Processus en 2 phases** :
  - **Phase 1 (Brut)** : Extraction informations depuis transcription (livres, critiques, coups de cœur)
  - **Phase 2 (Corrigé)** : Correction orthographique noms/titres via page RadioFrance
- 📋 **Interface 3 onglets** : Visualisation Phase 1 / Phase 2 / Différences côte à côte
- 📅 **Dates en français** : Format "dimanche 1 octobre 2017" (mapping manuel des mois)
- ✅ **Validation robuste** : 5 critères anti-malformations (sections manquantes, espaces excessifs, longueur)
- 🔄 **Régénération** : Bouton orange pour relancer génération si résumé vide
- 💾 **Sauvegarde sélective** : Bouton désactivé si résumé vide ou invalide
- ⚠️ **Alertes visuelles** : Warning explicite en cas de génération LLM incomplète
- 🎯 **Double validation** : Frontend (UX rapide) + Backend (sécurité HTTP 400)

#### Masquage des Épisodes
- 🚫 **Gestion de visibilité** : Masquer/afficher les épisodes sans les supprimer
- 📊 **Tableau complet** : Vue de tous les épisodes (masqués et visibles)
- ⏱️ **Tri par durée** : Colonnes triables (Titre, Durée, Date, Visibilité)
- 🔍 **Filtrage temps réel** : Recherche par titre ou date
- 👁️ **Toggle visuel** : Boutons avec icônes (👁️ visible / 🚫 masqué)
- 📈 **Impact statistiques** : Épisodes masqués exclus automatiquement des totaux
- 🎯 **Filtrage automatique** : Épisodes masqués cachés de toutes les vues publiques

#### Extraction Livres et Auteurs
- 📚 **Extraction automatique** : Parse les tableaux markdown des avis critiques
- 📋 **Interface tableau** : Colonnes triables (Auteur/Titre/Éditeur)
- 🔍 **Recherche temps réel** : Filtrage par auteur, titre ou éditeur
- 📊 **Deux sources** : "Livres discutés au programme" + "Coups de cœur des critiques"
- 🎯 **Vue par épisode** : Sélection d'épisodes avec avis critiques

#### Gestion des Collections
- 🏗️ **Architecture cache-first** : Collection `livresauteurs_cache` avec `LivresAuteursCacheService` TDD complet
- 📊 **Dashboard statistiques optimisé** : Vue globale avec "Avis critiques analysés", ordre intelligent des métriques
- 🤖 **Traitement automatique** : Auto-intégration des livres vérifiés par Babelio dans les collections MongoDB
- ✅ **Validation manuelle** : Interface dédiée pour corriger et valider les suggestions d'auteurs/livres
- 🔗 **Auto-remplissage Babelio** : Champ URL optionnel dans modales validation/ajout pour extraction automatique (titre, auteur, éditeur)
- ➕ **Ajout manuel** : Saisie directe des livres non trouvés avec leurs métadonnées complètes
- 🔗 **Gestion des références** : Liaison automatique entre épisodes, avis critiques, auteurs et livres
- 📚 **Collections MongoDB** : Création et maintenance des collections `auteurs` et `livres` avec références croisées
- 🎯 **Workflow complet** : De l'extraction des avis critiques jusqu'aux collections finales structurées

#### Intégration Babelio
- 🔗 **Liens automatiques** : Tous les livres et auteurs incluent leurs URLs Babelio quand disponibles
- 🎨 **Affichage visuel** : Icônes Babelio cliquables (80x80px) sur pages détail livre/auteur
- 🤖 **Migration automatique** : Système en 2 phases pour enrichir les URLs manquantes
  - Phase 1 : Livres sans URL → recherche et validation sur Babelio
  - Phase 2 : Auteurs sans URL → extraction depuis pages livres existantes
- 📊 **Interface gestion** : Page dédiée `/babelio-migration` avec suivi temps réel
- ⚠️ **Cas problématiques** : Collection MongoDB `babelio_problematic_cases` pour traitement manuel
- ✅ **Validation intelligente** : Normalisation texte automatique (ligatures œ→oe, ponctuation, casse)
- 🔄 **Stratégie de secours** : Recherche élargie si correspondance exacte échoue
- 🏢 **Éditeur enrichi** : Scraping automatique de l'éditeur depuis Babelio, stocké via collection `editeurs` dédiée
- 🔄 **Ré-extraction Babelio** : Bouton sur la page livre pour rafraîchir titre, auteur et éditeur depuis Babelio (auto-apply avec toast notification)
- 🤖 **Tolérance fautes** : Corrections orthographiques (ex: "Houllebeck" → "Michel Houellebecq")

##### Cache disque Babelio (diagnostic)

Pour améliorer les performances et réduire les requêtes vers Babelio, le backend utilise un cache disque optionnel (format fichier JSON par clé) avec TTL par défaut 24h.

  - Exportez la variable d'environnement `BABELIO_CACHE_LOG=1` avant de lancer `./scripts/start-dev.sh` pour activer des logs détaillés (INFO) montrant les hits/misses/écritures du cache.
  - Exemple :

```bash
export BABELIO_CACHE_LOG=1
./scripts/start-dev.sh
```

  - Le cache stocke les réponses Babelio pour le terme recherché et pour une clé normalisée (lowercase). Les clés sont conservatrices : les résultats de Babelio peuvent changer entre exécutions, donc le cache est principalement destiné à améliorer des charges de travail répétées en développement.
  - Les logs affichent des lignes comme :
    - `[BabelioCache] HIT (orig) key='...' items=... ts=...`
    - `[BabelioCache] MISS keys=(orig='...', norm='...')`
    - `[BabelioCache] WROTE keys=(orig='...', norm='...') items=...`

  - Les résultats externes (Babelio) évoluent : une entrée cache peut devenir obsolète. Ne pas considérer les réponses cacheées comme la vérité absolue.
  - Pour un comportement reproductible en test, videz le dossier `data/processed/babelio_cache` si nécessaire.
 Pour améliorer les performances et réduire les requêtes vers Babelio, le backend utilise un cache disque (format fichier JSON par clé) avec TTL par défaut 24h. Le cache est activé par défaut en développement.

 - Désactiver le cache :
   - Pour désactiver le cache au démarrage, exportez `BABELIO_CACHE_ENABLED=0` avant de lancer `./scripts/start-dev.sh`.



#### Moteur de Recherche Textuelle
- 🔍 **Recherche multi-collections** : Episodes, auteurs, livres, éditeurs
- 📚 **Collections dédiées** : Recherche directe dans `auteurs` et `livres` MongoDB
- 👤 **Enrichissement auteur** : Livres affichés avec format "Auteur - Titre"
- ⚡ **Temps réel** : Debouncing 300ms, minimum 3 caractères
- 🎯 **Extraction de contexte** : 10 mots avant/après le terme trouvé (épisodes)
- 🖍️ **Surlignage** : Mise en évidence des termes recherchés
- 📊 **Compteurs intelligents** : Format "📖 LIVRES (3/155)" (affichés/total)
- 🔤 **Recherche exacte** : Insensible à la casse, regex MongoDB sur tous les champs

#### Recherche Avancée
- 🎯 **Filtres par entité** : Recherche ciblée (épisodes, auteurs, livres, éditeurs)
- 📄 **Pagination complète** : Navigation par page avec sélecteur de limite (10/20/50/100)
- 📊 **Compteurs totaux** : Affichage du nombre total de résultats par catégorie
- ⚙️ **Sources unifiées** : Recherche éditeurs dans `editeurs.nom` + `livres.editeur` (dédupliqué)
- 🔍 **Interface dédiée** : Page `/search` avec filtres interactifs
- 📱 **Responsive** : Optimisée pour mobile et desktop

#### Intégration Calibre
- 📚 **Bibliothèque personnelle** : Accès à votre collection Calibre existante
- 🔍 **Recherche avec highlighting** : Termes de recherche surlignés en jaune
- 🏷️ **Filtres intelligents** : Tous / Lus / Non lus
- 📊 **Tri flexible** : Par date, titre ou auteur (A→Z / Z→A)
- ∞ **Infinite scroll** : Chargement progressif des livres
- 🔐 **Lecture seule** : Accès sécurisé sans modification de votre bibliothèque
- 🎯 **Bibliothèque virtuelle** : Support des tags pour filtrage (ex: afficher uniquement tag "guillaume")
- 📖 **Métadonnées complètes** : Auteurs, éditeur, ISBN, note, tags, colonnes personnalisées (#read, #paper, #text)

#### Corrections Calibre
- 🔗 **Matching MongoDB-Calibre** : Algorithme à 3 niveaux (exact, containment, validation auteur)
- 👤 **Corrections auteurs** : Détection des différences de noms d'auteurs entre MongoDB et Calibre
- 📖 **Corrections titres** : Identification des différences de titres après matching
- 🏷️ **Tags manquants** : Détection des tags `lmelp_` attendus mais absents dans Calibre
- 📋 **Copier-coller** : Bouton de copie des tags complets (virtual library + notable + lmelp_) pour Calibre
- 🔄 **Cache intelligent** : Cache de 5 minutes avec invalidation manuelle après corrections

#### Palmarès des livres
- 🏆 **Classement par note** : Livres classés par note moyenne décroissante (minimum 2 avis)
- 📖 **Intégration Calibre** : Statut de lecture et note Calibre pour chaque livre
- 🏷️ **Filtres interactifs** : Lus / Non lus / Dans Calibre (persistés dans localStorage)
- ∞ **Infinite scroll** : Chargement progressif par pages de 30
- 🔗 **Liens rapides** : Accès direct à la fiche livre, fiche auteur, Calibre et Anna's Archive

#### Pages de Détail Auteur et Livre
- 👤 **Page auteur** : `/auteur/:id` - Vue détaillée d'un auteur avec tous ses livres triés alphabétiquement
- 📖 **Page livre** : `/livre/:id` - Vue détaillée d'un livre avec liste des épisodes où il est mentionné, tags Calibre associés (dates d'émission, coups de coeur) et copie en un clic
- 🔗 **Navigation inter-pages** : Liens clickables depuis recherche simple/avancée vers pages détail
- 🎯 **Liens depuis biblio validation** : Auteurs et titres clickables dans la page `/livres-auteurs`
- 🔄 **Liens épisodes** : Navigation directe depuis un livre vers validation biblio avec épisode pré-sélectionné
- 📍 **URL parameters** : Support `/livres-auteurs?episode=<id>` pour sélection automatique

### API disponible

```bash
# Lister tous les épisodes
GET /api/episodes

# Détails d'un épisode
GET /api/episodes/{id}

# Mettre à jour la description corrigée
PUT /api/episodes/{id}

# Extraction livres et auteurs
GET /api/livres-auteurs           # Tous les livres extraits
GET /api/livres-auteurs?episode_oid={id}  # Livres d'un épisode
GET /api/episodes-with-reviews    # Episodes ayant des avis critiques

# Gestion des collections
GET /api/livres-auteurs/statistics           # Statistiques des collections
POST /api/livres-auteurs/auto-process-verified  # Traitement automatique des livres vérifiés
GET /api/livres-auteurs/books/{status}       # Livres par statut (verified/suggested/not_found)
POST /api/livres-auteurs/validate-suggestion # Validation manuelle d'une suggestion
POST /api/livres-auteurs/add-manual-book     # Ajout manuel d'un livre not_found
GET /api/authors                             # Tous les auteurs de la collection
GET /api/books                               # Tous les livres de la collection

# Vérification orthographique Babelio
POST /api/verify-babelio          # Vérifier auteurs/livres/éditeurs

# Génération LLM d'avis critiques (Issue #171)
GET /api/avis-critiques/episodes-sans-avis  # Episodes sans avis critiques
POST /api/avis-critiques/generate            # Génération 2 phases (phase1 + phase2)
POST /api/avis-critiques/save                # Sauvegarde avec validation (5 critères)
GET /api/avis-critiques/{episode_id}         # Récupérer avis existant

# Pages de détail (Issue #96)
GET /api/auteur/{id}              # Détails d'un auteur avec ses livres
GET /api/livre/{id}               # Détails d'un livre avec ses épisodes

# Recherche textuelle
GET /api/search?q={query}&limit={n}              # Recherche simple multi-collections
GET /api/advanced-search?q={query}&entities={...}&page={n}&limit={m}  # Recherche avec filtres et pagination

# Palmarès
GET /api/palmares                 # Classement des livres par note moyenne (pagination)

# Calibre (Issue #119)
GET /api/calibre/status           # Statut de l'intégration Calibre
GET /api/calibre/statistics       # Statistiques de la bibliothèque
GET /api/calibre/books            # Liste des livres (pagination, tri, filtres)
GET /api/calibre/matching         # Matching MongoDB-Calibre (3 niveaux)
GET /api/calibre/corrections      # Corrections à appliquer (auteurs, titres, tags)
POST /api/calibre/cache/invalidate  # Invalider le cache matching
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
  "titre": "Titre corrigé par le back-office", // ⭐ Version corrigée finale
  "titre_origin": "Titre original de l'épisode", // ⭐ Version originale sauvegardée
  "date": ISODate,
  "type": "livres|cinema|theatre",
  "description": "Description corrigée manuellement", // ⭐ Version corrigée finale
  "description_origin": "Description originale France Inter", // ⭐ Version originale sauvegardée
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

## 🐳 Déploiement Docker

L'application est packagée sous forme de conteneurs Docker pour un déploiement simplifié sur NAS Synology ou tout environnement Docker.

### Architecture de déploiement

```
Internet → Application Portal (HTTPS)
         ↓
    Frontend Container (nginx)
         ↓
    Backend Container (FastAPI)
         ↓
    MongoDB Container (existant)
```

### Images Docker disponibles

Les images sont automatiquement buildées via GitHub Actions et disponibles sur GitHub Container Registry :

- **Backend** : `ghcr.io/castorfou/lmelp-backend:latest`
- **Frontend** : `ghcr.io/castorfou/lmelp-frontend:latest`

Tags disponibles : `latest`, `v1.0.0`, `v1.1.0`, etc.

### Déploiement rapide

```bash
# Utiliser docker-compose
cd docker/deployment
docker compose up -d

# Accéder à l'application
http://localhost:8080
```

### Documentation complète

Pour un guide détaillé incluant :
- Configuration Portainer et webhook pour auto-déploiement
- Configuration reverse proxy Synology
- Procédures de mise à jour et rollback
- Tests et validation
- Troubleshooting

Consulter la [documentation de déploiement](https://castorfou.github.io/back-office-lmelp/deployment/docker-setup/).

### CI/CD Pipeline

Chaque push sur `main` ou tag `v*` déclenche automatiquement :

1. ✅ Tests (backend + frontend)
2. 🐳 Build des images Docker
3. 📦 Publish sur ghcr.io
4. 🚀 Déploiement automatique via webhook Portainer (optionnel)

Temps total : ~10-15 minutes de commit à production.

## 📋 Roadmap

### MVP 0 ✅ **TERMINÉ**
- ✅ Interface de base pour correction des descriptions
- ✅ Sauvegarde automatique en base MongoDB
- ✅ **Extraction Livres/Auteurs** : Interface tableau avec parsing markdown
- ✅ **Gestion des Collections** : Dashboard statistiques, traitement automatique, validation manuelle, ajout manuel
- ✅ **Vérification Babelio** : Correction orthographique automatique auteurs/livres
- ✅ **Recherche Textuelle** : Moteur de recherche multi-entités avec extraction de contexte
- ✅ **Génération LLM d'avis critiques** : 2 phases (extraction + correction), validation robuste, interface 3 onglets
- ✅ Tests complets validés (backend + frontend)
- ✅ CI/CD pipeline avec validation complète
- ✅ Architecture full-stack (FastAPI + Vue.js 3)
- ✅ Documentation MkDocs + GitHub Pages avec Material Design

### Versions futures
- 🔍 **Recherche avancée** : Filtres par date, type, recherche sémantique
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
