# Issue #119 - Intégration Calibre Phase 1

**Date**: 2024-11-28
**Branche**: `119-integrer-calibre-dans-back-office-lmelp`
**Statut**: Phase de planification et documentation complétée, implémentation en cours

## Contexte

Intégration de la bibliothèque personnelle Calibre dans back-office-lmelp pour permettre de croiser les lectures personnelles avec les critiques du Masque et la Plume.

## Vision globale (3 phases)

### Phase 1 (Issue #119) - Accès direct
- Traiter Calibre comme **seconde source de données** indépendante
- Interrogation directe de la base Calibre (pas de synchronisation MongoDB)
- Nouvelle page "Accès Calibre" dans l'interface
- Extension de la recherche avancée pour inclure Calibre
- **Activation conditionnelle**: Uniquement si `CALIBRE_LIBRARY_PATH` défini et accessible

### Phase 2 (future) - Synchronisation
- Rapatrier les données Calibre vers MongoDB
- Processus: Calibre → Nettoyage Babelio → MongoDB
- Synchronisation incrémentielle pour gérer l'évolution continue de Calibre
- Liaison livres MongoDB ↔ livres Calibre

### Phase 3 (future) - Analyse et comparaison
- Comparer notes personnelles vs notes critiques LMELP
- Statistiques de corrélation
- Recommandations basées sur le profil
- Visualisations graphiques

## Travail accompli

### 1. Documentation créée

#### Documentation utilisateur
**Fichier**: [docs/user/calibre-integration.md](../../user/calibre-integration.md)

Contenu:
- Vue d'ensemble de l'architecture (MongoDB + Calibre + Babelio)
- Description des 3 phases d'évolution
- Fonctionnalités disponibles (page Calibre, recherche avancée)
- Configuration et variables d'environnement
- Métadonnées Calibre utilisées (standard et personnalisées)
- Cas d'usage pratiques
- FAQ

#### Documentation développeur
**Fichier**: [docs/dev/calibre-integration.md](../calibre-integration.md)

Contenu détaillé:
- Architecture technique avec diagrammes
- API Calibre Python (`from calibre.library import db`)
- Métadonnées disponibles (champs standard et personnalisés `#`)
- Structure des fichiers backend/frontend
- Exemples de code complets:
  - Service Calibre avec activation conditionnelle
  - Modèles Pydantic
  - Routes FastAPI
  - Composants Vue.js
- Patterns de tests (backend et frontend)
- Configuration Docker
- Considérations de performance (cache, pagination)
- Sécurité (lecture seule, validation chemins)
- Roadmap technique

### 2. Script d'exploration

**Fichier**: [scripts/explore_calibre.py](../../../scripts/explore_calibre.py)

Script pour analyser la bibliothèque Calibre:
- Vérification de connexion
- Comptage des livres
- Listing des colonnes personnalisées
- Affichage des champs standards disponibles
- Exemples de livres avec métadonnées
- Statistiques (livres avec ISBN, notes, tags)
- Recommandations pour l'intégration

Usage:
```bash
python scripts/explore_calibre.py
# ou
python scripts/explore_calibre.py /chemin/vers/Calibre Library
```

### 3. Configuration environnement

#### Devcontainer
**Fichier modifié**: `.devcontainer/devcontainer.json`

Ajout du montage Calibre:
```json
"mounts": [
    // ... existing mounts
    "source=${localEnv:HOME}/Calibre Library,target=/calibre,type=bind,consistency=cached,readonly"
]
```

**Note importante**: Montage en **lecture seule** (`:ro`) pour éviter toute modification accidentelle.

#### Variables d'environnement

**Fichier**: `.env`
```bash
# Calibre (optionnel)
CALIBRE_LIBRARY_PATH=/calibre
```

**Fichier**: `docker/deployment/.env.template`
```bash
# ============================================================================
# CALIBRE (OPTIONNEL)
# ============================================================================

# Chemin vers la bibliothèque Calibre
# Laisser vide ou commenter pour désactiver l'intégration Calibre
# CALIBRE_LIBRARY_PATH=/calibre

# Note : Pour Docker, vous devez également monter le volume Calibre dans docker-compose.yml
# Exemple dans docker-compose.yml :
#   volumes:
#     - /chemin/vers/Calibre Library:/calibre:ro
```

## Architecture technique prévue

### Backend (Python/FastAPI)

```
src/back_office_lmelp/
├── services/
│   ├── calibre_service.py       # Nouveau service Calibre
│   └── mongodb_service.py       # Service existant
├── models/
│   └── calibre_models.py        # Modèles Pydantic Calibre
├── routers/
│   └── calibre_router.py        # Routes API Calibre
└── config.py                    # Config (ajout CALIBRE_LIBRARY_PATH)
```

**Endpoints API prévus**:
- `GET /api/calibre/status` - Statut de l'intégration
- `GET /api/calibre/books` - Liste des livres (paginé)
- `GET /api/calibre/books/{id}` - Détails d'un livre

### Frontend (Vue.js)

```
frontend/src/
├── views/
│   └── CalibreView.vue          # Nouvelle page Calibre
├── router/
│   └── index.ts                 # Ajout route /calibre
└── views/
    └── HomeView.vue             # Ajout fonction conditionnelle
```

**Colonnes à afficher**:
- Auteur
- Livre (titre)
- Lu (oui/non)
- Note
- Tags
- Date de lecture

### Métadonnées Calibre

**Champs standard utilisables**:
- `title`, `authors` (affichage/recherche)
- `isbn` (liaison MongoDB/Babelio)
- `rating` (comparaison critiques)
- `tags` (catégorisation)
- `publisher`, `pubdate` (métadonnées)
- `series`, `comments`

**Champs personnalisés** (préfixés `#`, dépendent de la config utilisateur):
- `#read` - Marqueur "Lu"
- `#date_read` - Date de lecture
- `#review` - Commentaire personnel

## Principes de conception importants

### 1. Activation conditionnelle
```python
class CalibreService:
    def __init__(self):
        self._available = False
        if settings.calibre_library_path:
            try:
                # Test connexion
                self._available = True
            except:
                self._available = False
```

### 2. Isolation des sources
- MongoDB et Calibre complètement indépendants
- L'indisponibilité de Calibre n'affecte pas MongoDB
- Frontend vérifie le statut avant d'afficher les fonctions Calibre

### 3. Lecture seule
- **AUCUNE** modification de la base Calibre
- Protection par montage volume en `:ro`
- Validation des chemins et permissions

### 4. Performance
- Cache applicatif (TTL 5min recommandé)
- Pagination pour grandes bibliothèques (>1000 livres)
- Lazy loading (chargement uniquement si nécessaire)

## Prochaines étapes (après rebuild devcontainer)

### 1. Exploration de la base Calibre réelle
```bash
python scripts/explore_calibre.py
```

Objectifs:
- Comprendre les colonnes personnalisées de l'utilisateur
- Vérifier le taux de livres avec ISBN
- Identifier les champs utilisables
- Adapter l'implémentation selon les données réelles

### 2. Implémentation backend (TDD)

**Tests à écrire en premier (RED)**:
```python
# tests/test_calibre_service.py
- test_calibre_service_available()
- test_calibre_service_not_available()
- test_get_all_books()
- test_get_book_by_id()
- test_custom_columns_detection()

# tests/test_calibre_router.py
- test_calibre_status_available()
- test_calibre_status_unavailable()
- test_get_books_when_unavailable()
- test_get_books_with_pagination()
```

**Puis implémentation (GREEN)**:
- Service Calibre avec context manager
- Routes FastAPI
- Modèles Pydantic

### 3. Implémentation frontend

**Tests frontend (Vitest)**:
```typescript
// CalibreView.spec.ts
- test affichage message indisponible
- test affichage liste livres
- test pagination
- test recherche/filtres
```

**Composants**:
- `CalibreView.vue` avec tableau paginé
- Ajout route dans routeur
- Affichage conditionnel dans `HomeView.vue`

### 4. Intégration recherche avancée

Extension de la recherche avancée pour inclure Calibre comme source optionnelle.

## Points d'attention

### Dépendances Python
Ajouter `calibre` au fichier `pyproject.toml`:
```toml
[project]
dependencies = [
    # ... existing
    "calibre>=6.0.0",
]
```

### Tests avec mocks
**CRITIQUE**: Créer mocks à partir de vraies réponses Calibre (pas d'invention).

Workflow:
1. Exécuter `explore_calibre.py` pour capturer vraie structure
2. Utiliser cette structure exacte dans les mocks
3. Éviter les tests qui passent avec données inventées mais échouent en prod (cf. Issue #96)

### Configuration Docker (pour production)

Fichier `docker-compose.yml` à modifier:
```yaml
services:
  backend:
    volumes:
      - /chemin/host/Calibre Library:/calibre:ro
    environment:
      - CALIBRE_LIBRARY_PATH=/calibre
```

## État de la todo list

### Complété ✅
1. Récupération détails issue #119
2. Création branche feature
3. Documentation vision (user + dev)
4. Configuration devcontainer et .env
5. Script d'exploration Calibre

### En cours 🔄
- Compréhension problème et spécifications (attente exploration réelle)

### À faire 📋
- Exécuter script exploration
- Recherche fichiers concernés codebase
- Implémentation TDD (tests + code)
- Itération tests/code
- Vérification checks (tests, lint, mypy)
- Validation utilisateur
- Mise à jour README/CLAUDE.md
- Mise à jour documentation
- Commit + push
- Vérification CI/CD
- Confirmation feature complète
- Pull request
- Retour sur main

## Commandes utiles

### Exploration Calibre
```bash
python scripts/explore_calibre.py
```

### Tests backend
```bash
PYTHONPATH=/workspaces/back-office-lmelp/src pytest tests/test_calibre* -v
```

### Tests frontend
```bash
cd /workspaces/back-office-lmelp/frontend && npm test -- CalibreView
```

### Linting
```bash
ruff check src/back_office_lmelp/services/calibre_service.py
mypy src/back_office_lmelp/services/calibre_service.py
```

## Ressources

- **Documentation utilisateur**: [docs/user/calibre-integration.md](../../user/calibre-integration.md)
- **Documentation développeur**: [docs/dev/calibre-integration.md](../calibre-integration.md)
- **Script exploration**: [scripts/explore_calibre.py](../../../scripts/explore_calibre.py)
- **Issue GitHub**: #119

## Notes importantes

1. **Rebuild devcontainer nécessaire** pour activer montage `/calibre`
2. **Chemin Calibre hôte**: `/home/guillaume/Calibre Library` → `/calibre` dans container
3. **Lecture seule obligatoire** pour sécurité
4. **Tests avec données réelles** avant mocks pour éviter erreurs production
5. **Phase 1 uniquement**: Pas de synchronisation MongoDB dans cette issue

---

**APRÈS REBUILD**: Exécuter `python scripts/explore_calibre.py` pour analyser la structure réelle avant de continuer l'implémentation.
