# Intégration Calibre - Documentation technique

## Architecture

### Vue d'ensemble

L'intégration Calibre permet d'accéder à une bibliothèque Calibre comme source de données complémentaire à MongoDB. L'architecture suit un pattern de **multi-source data access** avec activation conditionnelle.

```
┌─────────────────────────────────────────────────────────┐
│                    FastAPI Backend                      │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────────┐         ┌──────────────────┐     │
│  │ MongoDB Service  │         │ Calibre Service  │     │
│  │                  │         │   (Optional)     │     │
│  │ • get_episodes() │         │ • get_books()    │     │
│  │ • get_books()    │         │ • get_metadata() │     │
│  │ • get_critics()  │         │ • is_available() │     │
│  └──────────────────┘         └──────────────────┘     │
│           │                            │                │
│           ▼                            ▼                │
│  ┌──────────────────┐         ┌──────────────────┐     │
│  │   motor/pymongo  │         │  calibre.library │     │
│  │    (MongoDB)     │         │      (Calibre)   │     │
│  └──────────────────┘         └──────────────────┘     │
│           │                            │                │
└───────────┼────────────────────────────┼────────────────┘
            │                            │
            ▼                            ▼
    ┌──────────────┐           ┌──────────────┐
    │   MongoDB    │           │ Calibre DB   │
    │   Database   │           │ metadata.db  │
    └──────────────┘           └──────────────┘
```

### Principe de conception

**Activation conditionnelle** : Le service Calibre n'est instancié que si :
1. Dossier `/calibre` détecté
2. Base Calibre (`metadata.db`) présente et lisible

**Isolation des sources** : Les services MongoDB et Calibre sont indépendants. L'indisponibilité de Calibre n'affecte pas MongoDB.

## Service de Matching MongoDB-Calibre

### Architecture

Le `CalibreMatchingService` (`src/back_office_lmelp/services/calibre_matching_service.py`) orchestre le rapprochement entre les livres MongoDB et Calibre. Il dépend de `CalibreService` et `MongoDBService`.

```
┌─────────────────────────────────────────────────────────┐
│              CalibreMatchingService                     │
│                                                         │
│  ┌──────────────────┐         ┌──────────────────┐     │
│  │ CalibreService   │         │ MongoDBService   │     │
│  │ .get_all_books_  │         │ .get_all_books() │     │
│  │  with_tags()     │         │ .get_all_authors()│    │
│  │                  │         │ .get_expected_    │     │
│  │                  │         │  calibre_tags()   │     │
│  └──────────────────┘         └──────────────────┘     │
│           │                            │                │
│           ▼                            ▼                │
│  ┌──────────────────────────────────────────────────┐  │
│  │         normalize_for_matching(text)              │  │
│  │         (text_utils.py)                           │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### Algorithme de matching (`match_all()`)

Trois niveaux appliqués séquentiellement :

1. **Tier 1 - Exact** : Les titres MongoDB et Calibre sont normalisés via `normalize_for_matching()` (minuscules, sans accents, ligatures converties, tirets et apostrophes normalisés). Les titres identiques après normalisation constituent un match exact.

2. **Tier 2 - Containment** : Pour les livres non matchés en Tier 1, on vérifie si le titre normalisé de l'un contient celui de l'autre (minimum 4 caractères pour le plus court, `MIN_CONTAINMENT_LENGTH`). Ceci gère les sous-titres, tomes et prix littéraires. Si un seul candidat est trouvé, l'auteur est validé.

3. **Tier 3 - Author validated** : Si le containment produit plusieurs candidats, la validation auteur départage les ambiguïtés. La comparaison d'auteurs (`_authors_match()`) est tolérante : normalisation des tokens de noms, gestion du format pipe Calibre (`Sarr| Mohamed Mbougar`), virgule (`Sarr, Mohamed`) et naturel MongoDB (`Mohamed Mbougar Sarr`). Un token significatif en commun (>1 caractère) suffit.

### Normalisation des auteurs (`_normalize_author_parts()`)

```python
# Formats supportés :
"Mohamed Mbougar Sarr"    → {"mohamed", "mbougar", "sarr"}
"Appanah| Nathacha"       → {"appanah", "nathacha"}
"Sarr, Mohamed Mbougar"   → {"sarr", "mohamed", "mbougar"}
"Kœnig| Gaspard"          → {"koenig", "gaspard"}  # ligature convertie
```

### Cache

Les données de matching (livres Calibre, livres MongoDB, auteurs) sont mises en cache en mémoire avec un TTL de 5 minutes (`_cache_ttl = 300`). Le cache est invalidable manuellement via `invalidate_cache()` (endpoint `POST /api/calibre/cache/invalidate`).

### Corrections (`get_corrections()`)

Retourne un dict avec 3 catégories + statistiques :

- `author_corrections` : Livres matchés dont les noms d'auteurs diffèrent (après normalisation)
- `title_corrections` : Livres matchés dont les titres diffèrent (matchés par containment ou author_validated)
- `missing_lmelp_tags` : Livres matchés dont les tags `lmelp_*` attendus (calculés par `MongoDBService.get_expected_calibre_tags()`) sont absents des tags Calibre actuels. Chaque entrée fournit un champ `all_tags_to_copy` avec l'ordre : `[virtual_library_tag]` + `[notable_tags]` + `[lmelp_*]`

### Enrichissement du palmarès

`enrich_palmares_item()` et `get_calibre_index()` remplacent l'ancien `_enrich_with_calibre()` de `app.py`. L'index Calibre est un dict `{titre_normalisé: calibre_book_data}` permettant un lookup O(1) par titre.

### Endpoints API

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/api/calibre/matching` | GET | Résultats complets du matching avec statistiques par tier |
| `/api/calibre/corrections` | GET | Corrections groupées (auteurs, titres, tags manquants) |
| `/api/calibre/cache/invalidate` | POST | Invalide le cache de 5 minutes |

**Placement des routes** : Ces routes sont définies AVANT `/api/calibre/books/{book_id}` pour éviter la capture par la route paramétrée.

## API Calibre Python

### Bibliothèque utilisée

```python
from calibre.library import db

# Connexion
library = db('/chemin/vers/Calibre Library')

# Requêtes
all_ids = library.all_book_ids()
metadata = library.get_metadata(book_id)

# Fermeture
library.close()
```

### Métadonnées disponibles

#### Champs standard

```python
metadata.title          # str : Titre du livre
metadata.authors        # List[str] : Liste des auteurs
metadata.isbn           # str : ISBN
metadata.publisher      # str : Éditeur
metadata.pubdate        # datetime : Date de publication
metadata.tags           # List[str] : Tags/catégories
metadata.series         # str : Série (si applicable)
metadata.series_index   # float : Numéro dans la série
metadata.rating         # int : Note (0-10, souvent 0-5 x2)
metadata.comments       # str : Résumé/description
```

#### Champs personnalisés

Les colonnes personnalisées sont préfixées par `#` :

```python
# Exemples courants
metadata.get('#read')       # Marqueur "Lu"
metadata.get('#date_read')  # Date de lecture
metadata.get('#review')     # Commentaire personnel
```

**Note** : Les noms de colonnes personnalisées varient selon la configuration Calibre de l'utilisateur.

### Gestion de la connexion

**Pattern recommandé** : Context manager

```python
class CalibreService:
    def __init__(self, library_path: str):
        self.library_path = library_path
        self._db = None

    def __enter__(self):
        self._db = db(self.library_path)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._db:
            self._db.close()

    def get_all_books(self):
        if not self._db:
            raise RuntimeError("Database not connected")
        return [self._db.get_metadata(bid) for bid in self._db.all_book_ids()]
```

## Implémentation Backend

### Structure des fichiers

```
src/back_office_lmelp/
├── services/
│   ├── calibre_service.py       # Service Calibre (nouveau)
│   └── mongodb_service.py       # Service MongoDB existant
├── models/
│   └── calibre_models.py        # Modèles Pydantic pour Calibre (nouveau)
├── routers/
│   └── calibre_router.py        # Routes API Calibre (nouveau)
└── config.py                    # Configuration (détection /calibre)
```

### Configuration

**Fichier `config.py`** :

```python
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Existing settings
    mongodb_url: str = "mongodb://localhost:27017"
    database_name: str = "masque_et_la_plume"

    # Nouvelle configuration Calibre
    @property
    def calibre_library_path(self) -> Optional[str]:
        # Retourne "/calibre" si présent
        ...

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
```

**Fichier `.env`** :

```bash
# MongoDB
MONGODB_URL=mongodb://localhost:27017
DATABASE_NAME=masque_et_la_plume
```

### Service Calibre

**Fichier `services/calibre_service.py`** :

```python
from typing import Optional, List
from calibre.library import db as calibre_db
from ..config import settings
import logging

logger = logging.getLogger(__name__)

class CalibreService:
    def __init__(self):
        self.library_path = settings.calibre_library_path
        self._db = None
        self._available = False
        self._check_availability()

    def _check_availability(self):
        """Vérifie si Calibre est accessible"""
        if not self.library_path:
            logger.warning("Calibre library not found at /calibre")
            return

        try:
            # Test de connexion
            test_db = calibre_db(self.library_path)
            test_db.close()
            self._available = True
            logger.info(f"Calibre integration: ENABLED at {self.library_path}")
        except Exception as e:
            logger.error(f"Calibre integration: DISABLED - {str(e)}")
            self._available = False

    def is_available(self) -> bool:
        """Retourne True si Calibre est disponible"""
        return self._available

    def get_all_books(self) -> List[dict]:
        """Récupère tous les livres de la bibliothèque"""
        if not self._available:
            return []

        try:
            with calibre_db(self.library_path) as db:
                books = []
                for book_id in db.all_book_ids():
                    metadata = db.get_metadata(book_id)
                    books.append({
                        "id": book_id,
                        "title": metadata.title,
                        "authors": metadata.authors,
                        "isbn": metadata.isbn,
                        "tags": metadata.tags,
                        "rating": metadata.rating,
                        "publisher": metadata.publisher,
                        "pubdate": metadata.pubdate.isoformat() if metadata.pubdate else None,
                    })
                return books
        except Exception as e:
            logger.error(f"Error fetching Calibre books: {str(e)}")
            return []

    def get_book_by_id(self, book_id: int) -> Optional[dict]:
        """Récupère un livre par son ID"""
        if not self._available:
            return None

        try:
            with calibre_db(self.library_path) as db:
                metadata = db.get_metadata(book_id)
                return {
                    "id": book_id,
                    "title": metadata.title,
                    "authors": metadata.authors,
                    "isbn": metadata.isbn,
                    "tags": metadata.tags,
                    "rating": metadata.rating,
                    "publisher": metadata.publisher,
                    "pubdate": metadata.pubdate.isoformat() if metadata.pubdate else None,
                    "comments": metadata.comments,
                }
        except Exception as e:
            logger.error(f"Error fetching Calibre book {book_id}: {str(e)}")
            return None

# Singleton
calibre_service = CalibreService()
```

### Modèles Pydantic

**Fichier `models/calibre_models.py`** :

```python
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class CalibreBook(BaseModel):
    id: int
    title: str
    authors: List[str]
    isbn: Optional[str] = None
    tags: List[str] = []
    rating: Optional[int] = None
    publisher: Optional[str] = None
    pubdate: Optional[str] = None  # ISO format
    comments: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": 42,
                "title": "Le Seigneur des Anneaux",
                "authors": ["J.R.R. Tolkien"],
                "isbn": "978-2-07-061332-8",
                "tags": ["Fantasy", "Classique"],
                "rating": 10,
                "publisher": "Gallimard",
                "pubdate": "1954-07-29",
            }
        }

class CalibreStatus(BaseModel):
    available: bool
    library_path: Optional[str] = None
    book_count: Optional[int] = None
    message: str
```

### Routes API

**Fichier `routers/calibre_router.py`** :

```python
from fastapi import APIRouter, HTTPException
from typing import List
from ..models.calibre_models import CalibreBook, CalibreStatus
from ..services.calibre_service import calibre_service

router = APIRouter(prefix="/api/calibre", tags=["calibre"])

@router.get("/status", response_model=CalibreStatus)
async def get_calibre_status():
    """Retourne le statut de l'intégration Calibre"""
    if calibre_service.is_available():
        books = calibre_service.get_all_books()
        return CalibreStatus(
            available=True,
            library_path=calibre_service.library_path,
            book_count=len(books),
            message="Calibre integration active"
        )
    else:
        return CalibreStatus(
            available=False,
            message="Calibre integration disabled (Library not found at /calibre)"
        )

@router.get("/books", response_model=List[CalibreBook])
async def get_all_calibre_books():
    """Récupère tous les livres de la bibliothèque Calibre"""
    if not calibre_service.is_available():
        raise HTTPException(status_code=503, detail="Calibre integration not available")

    books = calibre_service.get_all_books()
    return books

@router.get("/books/{book_id}", response_model=CalibreBook)
async def get_calibre_book(book_id: int):
    """Récupère un livre Calibre par son ID"""
    if not calibre_service.is_available():
        raise HTTPException(status_code=503, detail="Calibre integration not available")

    book = calibre_service.get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail=f"Book {book_id} not found")

    return book
```

**Enregistrement dans `app.py`** :

```python
from .routers import calibre_router

app.include_router(calibre_router.router)
```

## Implémentation Frontend

### Composant Vue.js

**Fichier `frontend/src/views/CalibreView.vue`** :

```vue
<template>
  <div class="calibre-view">
    <h1>Bibliothèque Calibre</h1>

    <div v-if="!calibreAvailable" class="alert alert-warning">
      L'intégration Calibre n'est pas disponible.
    </div>

    <div v-else>
      <p>{{ books.length }} livres dans votre bibliothèque</p>

      <table class="table">
        <thead>
          <tr>
            <th>Auteur</th>
            <th>Livre</th>
            <th>Lu</th>
            <th>Note</th>
            <th>Tags</th>
            <th>Date de lecture</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="book in books" :key="book.id">
            <td>{{ book.authors.join(', ') }}</td>
            <td>{{ book.title }}</td>
            <td>{{ book.read ? 'Oui' : 'Non' }}</td>
            <td>{{ book.rating || '-' }}</td>
            <td>{{ book.tags.join(', ') }}</td>
            <td>{{ book.date_read || '-' }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import axios from 'axios'

const calibreAvailable = ref(false)
const books = ref([])

onMounted(async () => {
  try {
    const statusRes = await axios.get('/api/calibre/status')
    calibreAvailable.value = statusRes.data.available

    if (calibreAvailable.value) {
      const booksRes = await axios.get('/api/calibre/books')
      books.value = booksRes.data
    }
  } catch (error) {
    console.error('Error fetching Calibre data:', error)
  }
})
</script>
```

### Ajout au routeur

**Fichier `frontend/src/router/index.ts`** :

```typescript
import CalibreView from '../views/CalibreView.vue'

const routes = [
  // ... routes existantes
  {
    path: '/calibre',
    name: 'calibre',
    component: CalibreView
  }
]
```

### Affichage conditionnel dans l'accueil

**Fichier `frontend/src/views/HomeView.vue`** :

```vue
<template>
  <!-- ... existing content -->

  <div class="functions">
    <!-- Existing functions -->

    <!-- Calibre function (conditional) -->
    <router-link
      v-if="calibreAvailable"
      to="/calibre"
      class="function-card">
      📚 Accès Calibre
    </router-link>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import axios from 'axios'

const calibreAvailable = ref(false)

onMounted(async () => {
  try {
    const res = await axios.get('/api/calibre/status')
    calibreAvailable.value = res.data.available
  } catch (error) {
    // Calibre not available, ignore
  }
})
</script>
```

## Tests

### Tests Backend

**Fichier `tests/test_calibre_service.py`** :

```python
import pytest
from unittest.mock import Mock, patch, MagicMock
from back_office_lmelp.services.calibre_service import CalibreService

@pytest.fixture
def mock_calibre_db():
    """Mock de la bibliothèque Calibre"""
    with patch('back_office_lmelp.services.calibre_service.calibre_db') as mock_db:
        # Mock metadata
        mock_metadata = Mock()
        mock_metadata.title = "Test Book"
        mock_metadata.authors = ["Test Author"]
        mock_metadata.isbn = "978-1234567890"
        mock_metadata.tags = ["Fiction"]
        mock_metadata.rating = 8
        mock_metadata.publisher = "Test Publisher"
        mock_metadata.pubdate = None

        # Mock database
        mock_instance = MagicMock()
        mock_instance.all_book_ids.return_value = [1, 2, 3]
        mock_instance.get_metadata.return_value = mock_metadata
        mock_db.return_value.__enter__.return_value = mock_instance
        mock_db.return_value.__exit__.return_value = None

        yield mock_db

def test_calibre_service_available(mock_calibre_db):
    """Test que le service détecte Calibre disponible"""
    with patch('back_office_lmelp.config.settings.calibre_library_path', '/fake/path'):
        service = CalibreService()
        assert service.is_available()

def test_calibre_service_not_available():
    """Test que le service détecte Calibre indisponible"""
    with patch('back_office_lmelp.config.settings.calibre_library_path', None):
        service = CalibreService()
        assert not service.is_available()

def test_get_all_books(mock_calibre_db):
    """Test récupération de tous les livres"""
    with patch('back_office_lmelp.config.settings.calibre_library_path', '/fake/path'):
        service = CalibreService()
        books = service.get_all_books()

        assert len(books) == 3
        assert books[0]['title'] == "Test Book"
        assert books[0]['authors'] == ["Test Author"]
```

**Fichier `tests/test_calibre_router.py`** :

```python
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from back_office_lmelp.app import app

client = TestClient(app)

def test_calibre_status_available():
    """Test endpoint status quand Calibre disponible"""
    with patch('back_office_lmelp.services.calibre_service.calibre_service.is_available', return_value=True):
        with patch('back_office_lmelp.services.calibre_service.calibre_service.get_all_books', return_value=[]):
            response = client.get("/api/calibre/status")
            assert response.status_code == 200
            data = response.json()
            assert data['available'] is True

def test_calibre_status_unavailable():
    """Test endpoint status quand Calibre indisponible"""
    with patch('back_office_lmelp.services.calibre_service.calibre_service.is_available', return_value=False):
        response = client.get("/api/calibre/status")
        assert response.status_code == 200
        data = response.json()
        assert data['available'] is False

def test_get_books_when_unavailable():
    """Test que /books retourne 503 si Calibre indisponible"""
    with patch('back_office_lmelp.services.calibre_service.calibre_service.is_available', return_value=False):
        response = client.get("/api/calibre/books")
        assert response.status_code == 503
```

### Tests Frontend

**Fichier `frontend/src/views/__tests__/CalibreView.spec.ts`** :

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import CalibreView from '../CalibreView.vue'
import axios from 'axios'

vi.mock('axios')

describe('CalibreView', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('shows unavailable message when Calibre not available', async () => {
    vi.mocked(axios.get).mockResolvedValueOnce({
      data: { available: false }
    })

    const wrapper = mount(CalibreView)
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toContain("L'intégration Calibre n'est pas disponible")
  })

  it('displays books when Calibre available', async () => {
    vi.mocked(axios.get)
      .mockResolvedValueOnce({ data: { available: true } })
      .mockResolvedValueOnce({
        data: [
          { id: 1, title: 'Book 1', authors: ['Author 1'], tags: [], rating: 8 }
        ]
      })

    const wrapper = mount(CalibreView)
    await wrapper.vm.$nextTick()
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toContain('Book 1')
    expect(wrapper.text()).toContain('Author 1')
  })
})
```

## Configuration Docker

### Dockerfile

Ajouter l'installation de Calibre :

```dockerfile
FROM python:3.11-slim

# ... existing setup

# Install Calibre library (not the GUI)
RUN pip install calibre

# ... rest of Dockerfile
```

### docker-compose.yml

```yaml
version: '3.8'

services:
  backend:
    build: .
    environment:
      - MONGODB_URL=mongodb://mongodb:27017
    volumes:
      - /home/guillaume/Calibre Library:/calibre:ro
    ports:
      - "54321:54321"

  frontend:
    # ... existing config

  mongodb:
    # ... existing config
```

**Important** : Le volume Calibre est monté en **read-only** (`:ro`) pour éviter toute modification accidentelle.

## Considérations de performance

### Cache applicatif

Pour éviter de requêter Calibre à chaque appel :

```python
from functools import lru_cache
from datetime import datetime, timedelta

class CalibreService:
    def __init__(self):
        # ... existing code
        self._cache = {}
        self._cache_expiry = {}
        self._cache_ttl = timedelta(minutes=5)

    def get_all_books(self) -> List[dict]:
        cache_key = "all_books"
        now = datetime.now()

        # Check cache
        if cache_key in self._cache and self._cache_expiry.get(cache_key, now) > now:
            return self._cache[cache_key]

        # Fetch from Calibre
        books = self._fetch_all_books()

        # Update cache
        self._cache[cache_key] = books
        self._cache_expiry[cache_key] = now + self._cache_ttl

        return books

    def _fetch_all_books(self) -> List[dict]:
        # ... actual Calibre query
```

### Pagination

Pour les grandes bibliothèques (>1000 livres) :

```python
@router.get("/books", response_model=List[CalibreBook])
async def get_all_calibre_books(
    skip: int = 0,
    limit: int = 100
):
    """Récupère les livres avec pagination"""
    if not calibre_service.is_available():
        raise HTTPException(status_code=503, detail="Calibre integration not available")

    books = calibre_service.get_all_books()
    return books[skip:skip+limit]
```

## Sécurité

### Validation des chemins

```python
import os
from pathlib import Path

def validate_calibre_path(path: str) -> bool:
    """Valide que le chemin Calibre est sûr"""
    try:
        # Résoudre le chemin absolu
        abs_path = Path(path).resolve()

        # Vérifier existence
        if not abs_path.exists():
            return False

        # Vérifier que c'est un dossier
        if not abs_path.is_dir():
            return False

        # Vérifier présence metadata.db
        metadata_file = abs_path / "metadata.db"
        if not metadata_file.exists():
            return False

        return True
    except Exception:
        return False
```

### Permissions

- **Lecture seule** : Ne jamais modifier la base Calibre
- **Isolation** : Calibre et MongoDB complètement séparés
- **Validation** : Vérifier tous les chemins et IDs

## Roadmap technique

### Phase 1 (Issue #119)
- [x] Service Calibre avec activation conditionnelle
- [x] Routes API basiques (/status, /books, /books/:id)
- [x] Composant Vue.js pour affichage
- [ ] Tests unitaires backend
- [ ] Tests unitaires frontend
- [ ] Documentation API (OpenAPI)

### Phase 2 (future)
- [ ] Service de synchronisation Calibre → MongoDB
- [ ] Détection des changements incrémentielle
- [ ] Intégration Babelio pour nettoyage
- [ ] Job périodique de synchronisation

### Phase 3 (future)
- [ ] API de comparaison notes personnelles vs critiques
- [ ] Endpoints statistiques
- [ ] Cache Redis pour performance
- [ ] Webhooks pour mise à jour temps réel

## Debugging

### Logs

Activer les logs détaillés :

```python
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('back_office_lmelp.services.calibre_service')
logger.setLevel(logging.DEBUG)
```

### CLI de test

Script utile pour tester Calibre en ligne de commande :

```python
# scripts/test_calibre.py
from calibre.library import db
import sys

if len(sys.argv) < 2:
    print("Usage: python test_calibre.py /path/to/library")
    sys.exit(1)

library_path = sys.argv[1]

try:
    library = db(library_path)
    print(f"✅ Connection successful to {library_path}")

    book_ids = library.all_book_ids()
    print(f"📚 Found {len(book_ids)} books")

    if book_ids:
        first_book = library.get_metadata(book_ids[0])
        print(f"📖 First book: {first_book.title} by {', '.join(first_book.authors)}")

    library.close()
except Exception as e:
    print(f"❌ Error: {str(e)}")
    sys.exit(1)
```

Usage :
```bash
python scripts/test_calibre.py "/home/guillaume/Calibre Library"
```

---

*Cette documentation technique complète la [documentation utilisateur](../user/calibre-integration.md) pour l'intégration Calibre.*
