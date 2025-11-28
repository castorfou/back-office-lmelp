# Issue #119 - Intégration Calibre Phase 1

**Date**: 2024-11-28
**Dernière mise à jour**: 2025-11-28 (session 2)
**Branche**: `119-integrer-calibre-dans-back-office-lmelp`
**Statut**: Configuration devcontainer en cours - En attente de rebuild

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

## Session 2 - Configuration installation Calibre (2025-11-28)

### Problème identifié
Lors de la tentative d'exécution du script `explore_calibre.py`, erreur :
```
ModuleNotFoundError: No module named 'calibre.library'
```

**Cause** : Le package PyPI `calibre` (v0.5.0) n'est **PAS** le vrai Calibre. C'est un package différent sans l'API `calibre.library`.

### Actions effectuées

#### 1. Modification script d'exploration ✅
**Fichier** : [scripts/explore_calibre.py](../../../scripts/explore_calibre.py)

Ajout du chargement automatique de `.env` :
```python
from dotenv import load_dotenv

def main():
    # Charger les variables d'environnement depuis .env
    dotenv_path = Path(__file__).parent.parent / ".env"
    if dotenv_path.exists():
        load_dotenv(dotenv_path)
        print(f"✅ Fichier .env chargé depuis {dotenv_path}\n")
```

#### 2. Configuration devcontainer pour installer Calibre ✅
**Fichier** : [.devcontainer/postCreateCommand.sh](../../../.devcontainer/postCreateCommand.sh)

Ajout de la fonction `install_calibre()` :
```bash
# Installation de Calibre
install_calibre() {
    echo "Installation de Calibre..."

    # Installer Calibre via apt
    sudo apt-get install -y -qq calibre

    # Vérifier l'installation
    if command -v calibre &> /dev/null; then
        echo "✅ Calibre installé ($(calibre --version | head -n1))"
    else
        echo "⚠️  Calibre non installé correctement"
    fi

    echo "Installation de Calibre terminée"
}
```

Ajout dans l'ordre d'exécution :
```bash
# Exécution des étapes
update_system
ensure_uv
install_calibre        # ← NOUVEAU
create_python_environment
setup_node
setup_git
```

#### 3. Suppression du faux package calibre ✅
```bash
uv remove calibre
```

Le package PyPI `calibre==0.5.0` a été supprimé de `pyproject.toml`.

### État actuel

**⏸️ EN ATTENTE DE REBUILD DEVCONTAINER**

Pour que Calibre soit installé, il faut reconstruire le devcontainer :
- Commande VS Code : **F1 → "Dev Containers: Rebuild Container"**
- Le script `postCreateCommand.sh` installera Calibre via `apt-get install calibre`

### Après le rebuild

Une fois le rebuild terminé, les étapes suivantes seront :

1. **Vérifier l'installation de Calibre** :
   ```bash
   calibre --version
   python -c "from calibre.library import db; print('✅ API Calibre accessible')"
   ```

2. **Exécuter le script d'exploration** :
   ```bash
   python scripts/explore_calibre.py
   ```

3. **Analyser la sortie** pour comprendre :
   - Structure de la bibliothèque Calibre réelle
   - Colonnes personnalisées disponibles
   - Taux de livres avec ISBN
   - Champs utilisables pour l'intégration

4. **Adapter l'implémentation** selon les données réelles découvertes

### Points importants pour la suite

#### Installation Calibre
- ✅ Calibre sera installé **au niveau système** via apt (pas via pip/uv)
- ✅ L'API Python de Calibre (`calibre.library.db`) sera accessible
- ✅ Pas besoin de dépendance dans `pyproject.toml`

#### Dépendances Python
Le vrai Calibre s'installe avec ses propres modules Python. Pas besoin de l'ajouter dans `pyproject.toml`.

## Session 3 - Exploration bibliothèque Calibre réelle (2025-11-28)

### Installation Calibre vérifiée ✅

Après rebuild du devcontainer :
- ✅ Calibre 5.12 installé au niveau système
- ✅ Répertoire `/calibre` monté correctement
- ✅ API Calibre accessible via `calibre-debug`

### Problème: Montage lecture seule

**Erreur** :
```
[Errno 30] Read-only file system: '/calibre/calibre_test_case_sensitivity.txt'
```

**Cause** : Calibre essaie d'écrire un fichier de test même en mode `read_only=True`.

**Solution** : Copier temporairement la bibliothèque vers `/tmp` pour l'exploration.

### Corrections du script explore_calibre.py

#### 1. Import conditionnel de dotenv ✅
```python
try:
    from dotenv import load_dotenv
    HAS_DOTENV = True
except ImportError:
    HAS_DOTENV = False
```

#### 2. Mode lecture seule ✅
```python
library = db(library_path, read_only=True)
```

#### 3. Utilisation correcte de l'API ✅
- Méthode : `library.all_ids()` au lieu de `library.all_book_ids()`
- Métadonnées : `library.get_metadata(book_id, index_is_id=True)` obligatoire

### Exploration réussie ✅

**Commande utilisée** :
```bash
cp -r /calibre /tmp/calibre_temp
CALIBRE_LIBRARY_PATH=/tmp/calibre_temp calibre-debug scripts/explore_calibre.py
```

### Résultats de l'exploration

#### Statistiques générales
- 📚 **943 livres** au total
- 📊 **36.6% avec ISBN** (345 livres)
- ⭐ **35.8% avec notes** (338 livres)
- 🏷️ **96.9% avec tags** (914 livres)
- 🏷️ **336 tags uniques**

#### Colonnes personnalisées (3)
1. **`#paper`** (bool) - Livre au format papier
2. **`#read`** (bool) - **Marqueur "Lu"** ✅
3. **`#text`** (comments) - **Commentaires personnels** (notes, date lecture, avis)

#### Tags utiles découverts
- **Tags personnels** : `camille`, `guillaume`, `lu`
- **Tags LMELP** : `lmelp_hubert_arthus`, `lmelp_olivia_de_lamberterie`, `lmelp_230514`
- **Thèmes** : `roman noir`, `angoisse`, `Historical`, etc.

#### Champs standards utilisables
- ✅ `title`, `authors` - Affichage et recherche
- ✅ `isbn` - Liaison MongoDB/Babelio (mais seulement 36.6%)
- ✅ `rating` - Comparaison avec critiques LMELP
- ✅ `tags` - Catégorisation riche (96.9% des livres)
- ✅ `publisher`, `pubdate` - Métadonnées enrichies
- ✅ `series`, `comments` - Informations complémentaires

### Points clés pour l'implémentation

#### 1. Gestion du faible taux d'ISBN (36.6%)
⚠️ **CRITIQUE** : Seulement 36.6% des livres ont un ISBN.

**Solution** : Implémenter un matching fuzzy Titre+Auteur pour lier avec MongoDB/Babelio.

#### 2. Accès à la base Calibre

**Problème** : Le montage lecture seule empêche l'API Calibre standard.

**Solutions possibles** :
1. **Copier la DB à la volée** (solution temporaire utilisée)
2. **Accès direct SQLite** (plus performant, bypass API Calibre)
3. **Montage lecture-écriture** avec permissions restreintes

**Recommandation** : Utiliser **accès direct SQLite** en production pour éviter les problèmes de permissions et améliorer les performances.

#### 3. Colonnes personnalisées parfaites pour le besoin

La colonne `#read` correspond exactement au besoin "Lu (oui/non)" de l'issue #119 !

La colonne `#text` peut contenir les notes, dates de lecture et avis personnels.

### Prochaines étapes

#### 1. Décision technique : Méthode d'accès à Calibre

Choisir entre :
- **Option A** : API Calibre via `calibre-debug` (authentique mais contraintes)
- **Option B** : Accès direct SQLite `metadata.db` (performant, lecture seule native)

**Recommandation** : **Option B (SQLite direct)** car :
- ✅ Lecture seule native
- ✅ Pas de problème de permissions
- ✅ Plus performant
- ✅ Structure DB Calibre bien documentée
- ❌ Moins "officiel" mais suffisant pour lecture seule

#### 2. Implémentation backend (TDD)

**Tests à écrire (RED)** :
```python
# tests/test_calibre_service.py
- test_calibre_service_available_when_env_set()
- test_calibre_service_unavailable_when_no_env()
- test_calibre_service_unavailable_when_path_invalid()
- test_get_all_books_with_pagination()
- test_get_book_by_id()
- test_get_books_filtered_by_read_status()
- test_get_custom_columns()
- test_isbn_matching()
- test_fuzzy_matching_title_author()

# tests/test_calibre_router.py
- test_calibre_status_available()
- test_calibre_status_unavailable()
- test_get_books_when_unavailable_returns_503()
- test_get_books_with_pagination()
- test_get_books_filtered_by_read()
```

#### 3. Structure backend à créer

```python
# src/back_office_lmelp/services/calibre_service.py
class CalibreService:
    def __init__(self):
        self._available = self._check_availability()

    def is_available(self) -> bool
    def get_all_books(self, limit, offset, read_filter) -> List[CalibreBook]
    def get_book(self, book_id) -> CalibreBook | None
    def get_custom_columns(self) -> Dict
    def count_books(self) -> int

# src/back_office_lmelp/models/calibre_models.py
class CalibreBook(BaseModel):
    id: int
    title: str
    authors: List[str]
    isbn: str | None
    rating: int | None
    tags: List[str]
    publisher: str | None
    pubdate: datetime | None
    series: str | None
    read: bool | None  # from #read column
    comments: str | None  # from #text column

# src/back_office_lmelp/routers/calibre_router.py
@router.get("/api/calibre/status")
@router.get("/api/calibre/books")
@router.get("/api/calibre/books/{id}")
```

## État de la todo list (session 3)

### Complété ✅
1. Récupération détails issue #119
2. Création branche feature
3. Documentation vision (user + dev)
4. Configuration devcontainer et .env
5. Script d'exploration Calibre
6. Modification script pour charger .env automatiquement
7. Configuration installation Calibre dans devcontainer
8. Suppression faux package calibre PyPI
9. **[NOUVEAU]** Rebuild devcontainer réussi
10. **[NOUVEAU]** Vérification installation Calibre
11. **[NOUVEAU]** Correction script explore_calibre.py (dotenv optionnel, read_only, index_is_id)
12. **[NOUVEAU]** Exploration complète bibliothèque Calibre réelle

### Prochaines étapes 📋
- **[DÉCISION]** Choisir méthode d'accès (API Calibre vs SQLite direct)
- Recherche fichiers concernés codebase
- Implémentation TDD backend (service + models + router)
- Implémentation frontend (CalibreView + route)
- Tests backend et frontend
- Vérification checks (tests, lint, mypy)
- Validation utilisateur
- Documentation mise à jour
- Commit + push + PR

---

## 🚀 PROCHAINE SESSION - Décision architecturale

**QUESTION CRITIQUE à décider** :

Méthode d'accès à la bibliothèque Calibre :
1. **API Calibre officielle** (`calibre-debug` + `from calibre.library import db`)
   - ✅ Authentique, supporté
   - ❌ Problèmes permissions lecture seule
   - ❌ Nécessite copie temporaire

2. **Accès direct SQLite** (`sqlite3` + `metadata.db`)
   - ✅ Lecture seule native
   - ✅ Plus performant
   - ✅ Pas de problème permissions
   - ❌ Moins "officiel"
   - ❌ Dépend de la structure interne Calibre

**Recommandation** : **Option 2 (SQLite direct)** pour simplicité et performance.

Une fois la décision prise, commencer l'implémentation TDD du backend.
