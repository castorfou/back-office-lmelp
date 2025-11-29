# Issue #119 - Calibre Integration: Docker Deployment & Search Highlighting

**Date**: 2025-11-29 20:52
**Issue**: [#119 - Intégrer Calibre dans back-office-lmelp](https://github.com/castorfou/back-office-lmelp/issues/119)
**Related Issue**: [docker-lmelp#27](https://github.com/castorfou/docker-lmelp/issues/27)
**Branch**: `119-integrer-calibre-dans-back-office-lmelp`

## Résumé

Cette session est la **Phase 2** de l'Issue #119 (voir aussi [251128-2219-issue119-calibre-integration-phase1.md](251128-2219-issue119-calibre-integration-phase1.md)).

Trois fonctionnalités majeures ajoutées :
1. **Search highlighting** - Surlignage jaune des termes de recherche dans l'interface Calibre
2. **Docker production deployment** - Configuration volume mounting pour production
3. **Virtual library tag support** - Filtrage par tag Calibre (ex: "guillaume")

## Phase 2 vs Phase 1

**Phase 1** (voir mémoire précédente) :
- Intégration backend complète (SQLite direct, models, service, endpoints)
- Interface frontend Vue.js avec infinite scroll
- Tests backend et frontend complets
- Documentation technique

**Phase 2** (cette session) :
- Feature enhancement: search highlighting
- Production readiness: Docker deployment
- Configuration: virtual library tag support
- Documentation: guide de déploiement production

## Fonctionnalités implémentées

### 1. Search Highlighting (Frontend)

**Problème** : L'utilisateur voulait surligner en jaune les termes de recherche dans les titres et auteurs, comme dans les autres fonctionnalités de recherche de l'app.

**Question utilisateur** : "quand je filtre, est-ce que je peux mettre en surligne jaune les motifs correspondants (comme dans la recherche)"

**Solution** : Réutilisation de l'utilitaire existant `highlightSearchTermAccentInsensitive` de `frontend/src/utils/textUtils.js`.

#### Implémentation TDD

**RED** : Tests écrits en premier dans `frontend/tests/unit/CalibreLibrary.test.js`

```javascript
it('should highlight search matches in book titles and authors', async () => {
  calibreService.getBooks.mockResolvedValue({
    total: 2,
    books: [
      { id: 1, title: 'Le Silence de la mer', authors: ['Vercors'] },
      { id: 2, title: 'La Peste', authors: ['Albert Camus'] }
    ]
  });

  wrapper = mount(CalibreLibrary, { global: { plugins: [router] } });
  await flushPromises();

  const searchInput = wrapper.find('[data-testid="search-input"]');
  await searchInput.setValue('silen');
  await wrapper.vm.$nextTick();

  const highlightedTitle = wrapper.vm.highlightText('Le Silence de la mer', 'silen');
  expect(highlightedTitle).toContain('<strong');
  expect(highlightedTitle).toContain('background: #fff3cd');
});

it('should not highlight if search text is less than 3 characters', async () => {
  // ... vérification que les termes < 3 chars ne sont pas surlignés
});
```

**GREEN** : Implémentation dans `frontend/src/views/CalibreLibrary.vue`

```javascript
// Import
import { highlightSearchTermAccentInsensitive } from '../utils/textUtils.js';

// Méthode
highlightText(text, searchTerm) {
  return highlightSearchTermAccentInsensitive(text, searchTerm || this.searchText);
}
```

```vue
<!-- Template avec v-html -->
<h3 class="book-title" v-html="highlightText(book.title, searchText)"></h3>
<p class="book-authors" v-html="highlightText(book.authors.join(', '), searchText)"></p>
```

**Résultat** : 18/18 tests passent

**Commit** : `feat(calibre): add search highlighting with yellow background`

### 2. Docker Production Deployment

**Problème** : Rendre Calibre accessible en production via Docker avec volume mounting de la bibliothèque Calibre existante sur l'hôte.

#### Apprentissage critique : Calibre NOT needed in Docker

**Erreur initiale** : J'ai essayé d'ajouter `calibre` au Dockerfile backend.

**Question utilisateur** : "pourquoi installerais-tu calibre ?"

**Correction** : Calibre n'a PAS besoin d'être installé dans le conteneur. Notre code utilise uniquement `sqlite3` (built-in Python) pour lire `metadata.db` directement.

**Fichier examiné** : `docker/build/backend/Dockerfile`
- ✅ Conservé tel quel (seulement `curl` pour healthcheck)
- ❌ PAS d'ajout de `apt-get install calibre`

#### Configuration simplifiée

**Question utilisateur** : "est-ce necessaire d'avoir CALIBRE_LIBRARY_PATH si ca vaut toujours /calibre ?"

**Leçon** : Éviter les variables redondantes. Solution :
- **Variable unique** : `CALIBRE_HOST_PATH` (chemin sur l'hôte)
- **Chemin conteneur fixe** : Toujours `/calibre` dans le conteneur
- **Montage read-only** : `:ro` pour sécurité

#### docker-compose.yml

```yaml
services:
  backend:
    environment:
      # Calibre integration (optionnel)
      # Si CALIBRE_HOST_PATH est défini dans .env, Calibre sera disponible à /calibre
      CALIBRE_LIBRARY_PATH: ${CALIBRE_HOST_PATH:+/calibre}
      CALIBRE_VIRTUAL_LIBRARY_TAG: ${CALIBRE_VIRTUAL_LIBRARY_TAG:-}

    # Volumes
    # Monter la bibliothèque Calibre si CALIBRE_LIBRARY_PATH est défini
    # Format : <chemin-hôte>:<chemin-conteneur>:ro
    # Exemple : /volume1/books/Calibre Library:/calibre:ro
    volumes:
      - ${CALIBRE_HOST_PATH:-/dev/null}:/calibre:ro
```

**Bash parameter expansion utilisée** :
- `${CALIBRE_HOST_PATH:+/calibre}` : Si `CALIBRE_HOST_PATH` défini → utilise `/calibre`, sinon vide
- `${CALIBRE_HOST_PATH:-/dev/null}` : Si `CALIBRE_HOST_PATH` vide → monte `/dev/null` (évite erreur de montage)
- `${CALIBRE_VIRTUAL_LIBRARY_TAG:-}` : Valeur par défaut vide si non défini

**Avantage** : Configuration optionnelle propre sans scripts de preprocessing.

#### .env.template

Ajout section Calibre complète avec exemples multi-plateformes :

```bash
# ============================================================================
# CALIBRE (OPTIONNEL)
# ============================================================================

# Chemin SUR L'HÔTE de votre bibliothèque Calibre
# Laisser vide ou commenter pour désactiver l'intégration Calibre
# Ce chemin sera monté en lecture seule dans le conteneur à /calibre

# Option 1 : NAS Synology
# CALIBRE_HOST_PATH=/volume1/books/Calibre Library

# Option 2 : Linux
# CALIBRE_HOST_PATH=/home/user/Calibre Library

# Option 3 : Mac
# CALIBRE_HOST_PATH=/Users/username/Calibre Library

# Option 4 : Windows (WSL2 ou Docker Desktop)
# CALIBRE_HOST_PATH=/mnt/c/Users/username/Calibre Library

# Tag de bibliothèque virtuelle Calibre (optionnel)
# Si votre bibliothèque Calibre utilise un tag pour filtrer les livres
# (ex: afficher uniquement les livres avec le tag "guillaume")
# CALIBRE_VIRTUAL_LIBRARY_TAG=guillaume

# EXEMPLE POUR ACTIVER CALIBRE :
# CALIBRE_HOST_PATH=/volume1/books/Calibre Library
# CALIBRE_VIRTUAL_LIBRARY_TAG=guillaume

# Notes :
# - Le volume est monté en lecture seule (:ro) pour éviter toute modification
# - Dans le conteneur, Calibre sera toujours disponible à /calibre
# - Aucune installation de Calibre n'est nécessaire (lecture directe de metadata.db via SQLite)
# - Le tag de bibliothèque virtuelle permet de filtrer les livres affichés
```

**Commit** : `feat(docker): add Calibre volume mounting for production deployment`

### 3. Virtual Library Tag Support

**Problème** : L'utilisateur a remarqué l'absence de documentation pour `CALIBRE_VIRTUAL_LIBRARY_TAG`.

**Question utilisateur** : "as-tu parle de CALIBRE_VIRTUAL_LIBRARY_TAG=guillaume dans .env.template ?"

**Correction** : Ajout de la variable dans :
- ✅ `.env.template` (voir ci-dessus)
- ✅ `docker-compose.yml` environment section
- ✅ `calibre-setup.md` documentation

**Usage** : Permet de filtrer les livres affichés par tag Calibre.
- Exemple : `CALIBRE_VIRTUAL_LIBRARY_TAG=guillaume` → affiche uniquement livres avec tag "guillaume"
- Si vide → affiche tous les livres de la bibliothèque

**Commit** : `feat(docker): add CALIBRE_VIRTUAL_LIBRARY_TAG environment variable`

## Documentation créée

### docs/deployment/calibre-setup.md (319 lignes)

Guide de configuration production **exhaustif** avec :

**Architecture** :
```
┌─────────────────────────────────────────────────────────────┐
│                    NAS Synology (ou PC)                     │
│                                                             │
│  ┌────────────────────────────────────────────────────┐   │
│  │  Bibliothèque Calibre (sur l'hôte)                 │   │
│  │  /volume1/books/Calibre Library/                   │   │
│  │    ├── metadata.db (SQLite)                        │   │
│  │    ├── metadata_db_prefs_backup.json               │   │
│  │    └── Author/                                     │   │
│  │         └── Book Title (ID)/                       │   │
│  │              ├── cover.jpg                         │   │
│  │              └── Book Title - Author.epub          │   │
│  └──────────────────┬─────────────────────────────────┘   │
│                     │ Montage volume Docker (:ro)          │
│                     ▼                                       │
│  ┌────────────────────────────────────────────────────┐   │
│  │  Backend Container (FastAPI)                        │   │
│  │  /calibre/ (lecture seule)                         │   │
│  │    ├── metadata.db ← Lecture directe via SQLite    │   │
│  │    └── ...                                         │   │
│  └────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

**Sections principales** :
1. **Vue d'ensemble** : Architecture et prérequis
2. **Configuration** : Setup multi-plateforme (NAS/Linux/Mac/Windows)
3. **Vérification** : Commandes pour tester montage volume, API, interface web
4. **Troubleshooting exhaustif** :
   - "Calibre non disponible" → vérifier CALIBRE_HOST_PATH
   - "Permission denied" → chmod +r
   - "No such file or directory" → vérifier chemin et volume mount
   - "Livres affichés: 0" → vérifier tag de bibliothèque virtuelle
5. **Fonctionnalités** : API REST et interface web
6. **Sécurité** : Montage read-only, accès concurrent SQLite
7. **Limitations** : Lecture seule, pas de couvertures, colonnes personnalisées limitées
8. **Désactivation** : Comment désactiver Calibre

### docs/deployment/.pages

Ajout de `Configuration Calibre: calibre-setup.md` dans navigation MkDocs :

```yaml
title: 🐳 Déploiement Docker
nav:
  - Architecture Docker: docker-setup.md
  - Configuration Calibre: calibre-setup.md  # ← NOUVEAU
  - Guide Portainer: portainer-guide.md
  - Guide de mise à jour: update-guide.md
  - Tests et validation: testing-guide.md
  - Troubleshooting: troubleshooting.md
```

## GitHub Issue créée

**Issue docker-lmelp#27** : "Intégrer la fonctionnalité Calibre depuis back-office-lmelp"

**Méthode** : Utilisation de `gh issue create` après correction de l'utilisateur.

**Erreur initiale** : J'ai tenté de chercher le repo docker-lmelp sur le filesystem.
**Correction utilisateur** : "non utilise gh pour cela"
**Solution** : Utilisation du GitHub CLI pour créer l'issue directement.

**Commande** :
```bash
gh issue create --repo castorfou/docker-lmelp \
  --title "Intégrer la fonctionnalité Calibre depuis back-office-lmelp" \
  --body "..." # Corps avec architecture, modifications nécessaires, références
```

**Contenu de l'issue** :
- Contexte de l'intégration (Issue #119)
- Modifications nécessaires pour docker-compose.yml et .env.template
- Documentation à créer
- Diagramme d'architecture
- Fonctionnalités disponibles
- Références vers documentation complète et commits

**URL** : https://github.com/castorfou/docker-lmelp/issues/27

## Tous les fichiers modifiés sur la branche

### Backend (src/)

1. **src/back_office_lmelp/settings.py** (nouveau)
   - Centralisation configuration app
   - Properties pour MongoDB et Calibre
   - `calibre_library_path` : chemin bibliothèque (optionnel)
   - `calibre_virtual_library_tag` : tag pour filtrage (optionnel)

2. **src/back_office_lmelp/models/calibre_models.py** (nouveau)
   - Modèles Pydantic pour données Calibre
   - `CalibreBook` : livre avec métadonnées complètes
   - `CalibreAuthor` : auteur
   - `CalibreBookList` : liste paginée
   - `CalibreStatistics` : stats bibliothèque
   - Support colonnes personnalisées (#read, #paper, #text)

3. **src/back_office_lmelp/services/calibre_service.py** (nouveau)
   - Service d'accès SQLite direct à metadata.db
   - Lecture seule (mode=ro)
   - Support bibliothèques virtuelles (filtre tag)
   - Méthodes : `get_books()`, `get_statistics()`, `is_available()`
   - Mapping colonnes personnalisées dynamique

4. **src/back_office_lmelp/app.py** (modifié)
   - Ajout endpoints Calibre : `/api/calibre/status`, `/api/calibre/statistics`, `/api/calibre/books`
   - Initialisation conditionnelle du service Calibre

### Frontend (frontend/)

5. **frontend/src/views/CalibreLibrary.vue** (nouveau)
   - Interface Vue.js pour affichage bibliothèque Calibre
   - Infinite scroll avec intersection observer
   - Recherche temps réel avec debounce
   - Filtres : Tous / Lus / Non lus
   - Tri : Derniers ajoutés, Titre A→Z/Z→A, Auteur A→Z/Z→A
   - **Highlighting** : Surlignage jaune des termes de recherche (Phase 2)

6. **frontend/src/router/index.js** (modifié)
   - Ajout route `/calibre` → CalibreLibrary.vue

7. **frontend/src/services/api.js** (modifié)
   - Ajout méthode `getCalibreBooks(params)` pour appeler API backend

8. **frontend/src/views/Dashboard.vue** (modifié)
   - Ajout tuile Calibre dans dashboard
   - Logo Calibre avec lien vers /calibre
   - Affichage conditionnel si Calibre disponible

9. **frontend/src/assets/calibre_logo.png** (nouveau)
   - Logo Calibre pour dashboard

### Tests

10. **frontend/tests/unit/CalibreLibrary.test.js** (nouveau)
    - 18 tests pour CalibreLibrary.vue
    - Tests : rendering, search, filters, sorting, infinite scroll, highlighting

11. **frontend/tests/unit/calibreService.test.js** (nouveau)
    - Tests pour service API Calibre

12. **tests/test_calibre_endpoints.py** (nouveau)
    - Tests endpoints FastAPI Calibre
    - Tests : status, statistics, books list avec filtres/tri

13. **tests/test_calibre_service.py** (nouveau)
    - Tests unitaires CalibreService
    - Mocking SQLite, tests disponibilité, get_books(), statistics()

### Docker

14. **docker/deployment/docker-compose.yml** (modifié)
    - Ajout volume mount : `${CALIBRE_HOST_PATH:-/dev/null}:/calibre:ro`
    - Ajout env vars : `CALIBRE_LIBRARY_PATH`, `CALIBRE_VIRTUAL_LIBRARY_TAG`

15. **docker/deployment/.env.template** (modifié)
    - Section Calibre complète avec exemples multi-plateformes
    - Documentation inline pour CALIBRE_HOST_PATH et CALIBRE_VIRTUAL_LIBRARY_TAG

16. **docker/build/backend/Dockerfile** (NON modifié)
    - ✅ Conservé tel quel (pas d'installation Calibre)
    - Utilise sqlite3 built-in Python

### DevContainer (développement)

17. **.devcontainer/devcontainer.json** (modifié)
    - Configuration pour développement avec Calibre

18. **.devcontainer/postCreateCommand.sh** (modifié)
    - Ajout fonction `install_calibre()` pour dev environment
    - Installation Calibre via apt pour développement local
    - Note : **PAS nécessaire en production** (SQLite suffit)

### Pre-commit et linting

19. **.pre-commit-config.yaml** (modifié)
    - Mise à jour hooks vers dernières versions
    - Ajout type stubs pour MyPy : `types-beautifulsoup4`

20. **.vscode/settings.json** (modifié)
    - Configuration VSCode pour auto-approval de commandes gh

### Documentation

21. **docs/deployment/calibre-setup.md** (nouveau, 319 lignes)
    - Guide de configuration production
    - Architecture, setup, vérification, troubleshooting, sécurité

22. **docs/deployment/.pages** (modifié)
    - Ajout entrée navigation "Configuration Calibre"

23. **docs/dev/calibre-integration.md** (nouveau)
    - Documentation technique intégration Calibre
    - Architecture multi-source, API Python Calibre, patterns

24. **docs/dev/calibre-db-schema.md** (nouveau)
    - Structure complète de metadata.db
    - Tables, relations, colonnes personnalisées

25. **docs/dev/start-dev-script.md** (nouveau)
    - Documentation script `scripts/start-dev.sh`
    - Auto-discovery ports, nettoyage stale data

26. **docs/dev/.pages** (modifié)
    - Ajout entrées : "Calibre", "Calibre db schema", "Script de démarrage"

27. **docs/user/calibre-integration.md** (nouveau)
    - Guide utilisateur pour Calibre
    - Vision multi-sources, phases évolutives (Phase 1 → 2 → 3)

28. **docs/user/.pages** (modifié)
    - Ajout entrée "Integration Calibre"

29. **docs/claude/memory/251128-2219-issue119-calibre-integration-phase1.md** (nouveau)
    - Mémoire Phase 1 de l'intégration Calibre

### Scripts et configuration

30. **scripts/start-dev.sh** (modifié)
    - Améliorations pour support Calibre en dev

31. **pyproject.toml** (modifié)
    - Ajout dependency Pydantic pour models

32. **requirements.lock** (modifié)
    - Lock file généré après ajout dépendances

33. **uv.lock** (modifié)
    - Lock file uv après ajout dépendances

## Points d'apprentissage critiques

### 1. Ne pas installer de dépendances inutiles

**Erreur initiale** : J'ai essayé d'installer Calibre dans le Dockerfile backend.
**Question utilisateur** : "pourquoi installerais-tu calibre ?"
**Leçon** : Toujours vérifier si une dépendance est vraiment nécessaire.
- ✅ SQLite built-in Python suffit pour lire metadata.db
- ❌ Installation Calibre inutile en production Docker

**Distinction** :
- **DevContainer** : Calibre installé via apt (pour exploration/debug en dev)
- **Production Docker** : Pas d'installation Calibre (SQLite suffit)

### 2. Simplification de configuration

**Question utilisateur** : "est-ce necessaire d'avoir CALIBRE_LIBRARY_PATH si ca vaut toujours /calibre ?"
**Leçon** : Éviter les variables de configuration redondantes.
- ✅ Une seule variable (`CALIBRE_HOST_PATH`) + chemin fixe dans conteneur (`/calibre`)
- ❌ Deux variables qui contiennent essentiellement la même information

### 3. Utilisation du GitHub CLI pour issues

**Demande utilisateur** : "est-ce que tu peux ajouter une issue dans le repo docker-lmelp..."
**Erreur initiale** : J'ai tenté de chercher le repo sur le filesystem.
**Correction utilisateur** : "non utilise gh pour cela"
**Leçon** : Utiliser `gh issue create` pour créer des issues GitHub directement via API.

**Commande type** :
```bash
gh issue create --repo owner/repo --title "..." --body "..."
```

### 4. Bash parameter expansion pour Docker

**Patterns utilisés** : `${VAR:+value}` et `${VAR:-default}`

**Applications** :
- `${CALIBRE_HOST_PATH:+/calibre}` : Si défini → `/calibre`, sinon vide
  - Permet de conditionner CALIBRE_LIBRARY_PATH sans script externe
- `${CALIBRE_HOST_PATH:-/dev/null}` : Si vide → `/dev/null`
  - Évite les erreurs de montage Docker quand variable non définie
- `${CALIBRE_VIRTUAL_LIBRARY_TAG:-}` : Défaut vide

**Avantage** : Configuration optionnelle propre dans docker-compose.yml sans preprocessing.

### 5. Réutilisation de code existant

**Pattern** : Avant d'implémenter une nouvelle feature, chercher si une fonction similaire existe.

**Exemple** : Pour le search highlighting, `highlightSearchTermAccentInsensitive` existait déjà dans `frontend/src/utils/textUtils.js`. Simple réutilisation au lieu de réinventer.

**Bénéfices** :
- ✅ Cohérence UX (même style de highlighting partout)
- ✅ Moins de code à maintenir
- ✅ Fonction déjà testée

### 6. TDD méthodologie

**Cycle appliqué** : RED → GREEN → REFACTOR

**Exemple concret** :
1. **RED** : Écrire tests pour highlighting (2 tests) → échouent
2. **GREEN** : Implémenter `highlightText()` méthode → tests passent
3. **REFACTOR** : Réutiliser fonction existante au lieu de dupliquer → tests passent toujours

**Résultat** : 18/18 tests frontend passent.

## Architecture globale Calibre

### Multi-source data access

```
┌──────────────────────────────────────────────────────────┐
│                    Back-Office LMELP                     │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  ┌────────────┐    ┌────────────┐    ┌────────────┐     │
│  │  MongoDB   │    │  Calibre   │    │  Babelio   │     │
│  │            │    │            │    │            │     │
│  │ • Episodes │    │ • Livres   │    │ • Méta-    │     │
│  │ • Livres   │    │ • Auteurs  │    │   données  │     │
│  │ • Critiques│    │ • Notes    │    │ • Nettoyage│     │
│  │            │    │ • Tags     │    │   données  │     │
│  └────────────┘    └────────────┘    └────────────┘     │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### Activation conditionnelle

Le service Calibre n'est instancié que si :
1. ✅ Variable `CALIBRE_LIBRARY_PATH` définie
2. ✅ Chemin accessible et valide
3. ✅ Base Calibre (`metadata.db`) présente et lisible

**Isolation** : L'indisponibilité de Calibre n'affecte pas MongoDB.

### Phases évolutives (vision long-terme)

**Phase 1** : Accès direct (✅ TERMINÉ)
- Interrogation directe metadata.db
- Interface séparée
- Pas de synchronisation

**Phase 2** : Docker deployment (✅ CETTE SESSION)
- Production readiness
- Search highlighting
- Virtual library support

**Phase 3** : Synchronisation MongoDB (future)
- Rapatriement données Calibre → MongoDB
- Nettoyage via Babelio
- Corrélation avec critiques LMELP

**Phase 4** : Analyse et comparaison (future)
- Vos notes vs critiques LMELP
- Statistiques de corrélation
- Recommandations

## Commits de la branche

```
9ac21fe feat(docker): add CALIBRE_VIRTUAL_LIBRARY_TAG environment variable
da25739 feat(docker): add Calibre volume mounting for production deployment
401d344 feat(calibre): add search highlighting with yellow background
467e83c feat(calibre): add Calibre library integration with infinite scroll and statistics
801b822 fix(calibre): configure MyPy to handle Pydantic models correctly
99ad8b8 sqlite service for calibre
e7ee700 feat(calibre): configure devcontainer to install Calibre system package
a061038 chore: update pre-commit hooks to latest versions
42258ee docs(calibre): add comprehensive Calibre integration documentation and setup
```

**Phase 2 commits** (cette session) :
- `401d344` - Search highlighting
- `da25739` - Docker volume mounting
- `9ac21fe` - Virtual library tag

## Références

- **Issue source** : castorfou/back-office-lmelp#119
- **Issue docker** : castorfou/docker-lmelp#27
- **Documentation production** : https://castorfou.github.io/back-office-lmelp/deployment/calibre-setup/
- **Mémoire Phase 1** : [251128-2219-issue119-calibre-integration-phase1.md](251128-2219-issue119-calibre-integration-phase1.md)

## Tests

**Frontend** : 18/18 tests passent
- CalibreLibrary.vue : rendering, search, filters, sorting, scroll, highlighting
- calibreService : API calls

**Backend** : Tests complets
- Endpoints FastAPI : status, statistics, books
- Service : availability, get_books(), statistics()

## Méthodologie

**TDD** : RED → GREEN → REFACTOR
**Documentation-first** : Guides production avant features
**Simplicity** : Réutilisation code existant, éviter dépendances inutiles
**Security** : Montage read-only, isolation sources de données
