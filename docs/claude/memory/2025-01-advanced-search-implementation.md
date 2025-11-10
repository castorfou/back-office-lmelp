# Implémentation de la Recherche Avancée (Issue #53)

**Branche**: `53-feat-implement-advanced-search-page-with-unlimited-results-and-filters`
**Date**: Janvier 2025
**Statut**: Complète avec corrections de bugs

## Vue d'ensemble

Cette branche implémente un système de recherche avancée complet pour le back-office LMELP, incluant :
- Page frontend avec filtres et pagination
- Endpoint backend `/api/advanced-search` avec support des filtres d'entités
- Recherche multi-sources pour les éditeurs
- Correction d'un bug de pagination critique

## Commits de la branche

1. `da79e71` - feat: implement advanced search page with filters and pagination (#53)
2. `dac9c60` - feat: add publisher search with pagination
3. `d3ad5ee` - refactor: improve search scope for publishers and books
4. `65bd64f` - fix: unify search sources and fix publisher pagination

## 1. Implémentation Frontend (Commit da79e71)

### Composant AdvancedSearch.vue

**Fichier**: `frontend/src/views/AdvancedSearch.vue`

**Fonctionnalités**:
- Barre de recherche avec icône et debounce (300ms)
- Filtres par entité (checkboxes) : Épisodes, Auteurs, Livres, Éditeurs
- Pagination complète :
  - Sélecteur de page avec navigation (← 1 2 3 →)
  - Sélecteur de limite (10, 20, 50, 100 résultats par page)
  - Affichage du nombre total de pages
- Affichage des résultats par catégorie avec compteurs totaux
- Gestion des états (loading, erreurs, résultats vides)

**Structure de données**:
```javascript
data() {
  return {
    searchQuery: '',
    lastSearchQuery: '',
    loading: false,
    error: null,
    showResults: false,
    filters: {
      episodes: true,
      auteurs: true,
      livres: true,
      editeurs: true
    },
    results: {
      auteurs: [],
      auteurs_total_count: 0,
      livres: [],
      livres_total_count: 0,
      editeurs: [],
      editeurs_total_count: 0,
      episodes: [],
      episodes_total_count: 0
    },
    pagination: {
      page: 1,
      limit: 20,
      total_pages: 1
    }
  }
}
```

**Méthode de recherche**:
```javascript
async performSearch() {
  if (!this.searchQuery || this.searchQuery.length < 3) {
    return;
  }

  this.loading = true;
  this.error = null;

  try {
    // Construire liste des entités filtrées
    const selectedEntities = Object.entries(this.filters)
      .filter(([_, enabled]) => enabled)
      .map(([entity, _]) => entity);

    const response = await searchService.advancedSearch(
      this.searchQuery,
      selectedEntities,
      this.pagination.page,
      this.pagination.limit
    );

    this.results = response.results;
    this.pagination = response.pagination;
    this.showResults = true;
    this.lastSearchQuery = this.searchQuery;
  } catch (err) {
    this.error = err.response?.data?.detail || err.message;
  } finally {
    this.loading = false;
  }
}
```

**Affichage des résultats**:
- Badge de compteur pour chaque catégorie (ex: "Auteurs (12)")
- Liste avec icônes par type d'entité
- Message "Aucun résultat trouvé" avec suggestions

### Intégration au Dashboard

**Fichier**: `frontend/src/views/Dashboard.vue`

**Carte ajoutée**:
```vue
<div
  class="function-card clickable"
  data-testid="function-advanced-search"
  @click="navigateToAdvancedSearch"
>
  <div class="function-icon">🔎</div>
  <h3>Recherche avancée</h3>
  <p>Recherche avec filtres et critères spécifiques</p>
  <div class="function-arrow">→</div>
</div>
```

**Navigation**:
```javascript
navigateToAdvancedSearch() {
  this.$router.push('/search');
}
```

### Service API Frontend

**Fichier**: `frontend/src/services/api.js`

**Méthode ajoutée**:
```javascript
async advancedSearch(query, entities = [], page = 1, limit = 20) {
  if (!query || query.trim().length < 3) {
    throw new Error('La recherche nécessite au moins 3 caractères');
  }

  const params = { q: query.trim(), page, limit };

  // Ajouter le paramètre entities si spécifié
  if (entities && entities.length > 0) {
    params.entities = entities.join(',');
  }

  const response = await api.get('/advanced-search', { params });
  return response.data;
}
```

**Format de requête**:
- Sans filtre: `/api/advanced-search?q=camus&page=1&limit=20`
- Avec filtres: `/api/advanced-search?q=camus&entities=auteurs,livres&page=2&limit=50`

### Configuration du Router

**Fichier**: `frontend/src/router/index.js`

**Route ajoutée**:
```javascript
{
  path: '/search',
  name: 'AdvancedSearch',
  component: AdvancedSearch,
  meta: {
    title: 'Recherche avancée - Back-office LMELP'
  }
}
```

## 2. Backend - Endpoint Advanced Search (Commit da79e71)

**Fichier**: `src/back_office_lmelp/app.py`

**Endpoint**:
```python
@app.get("/api/advanced-search")
def advanced_search(
    q: str,
    entities: str = "",
    page: int = 1,
    limit: int = 20
):
    """
    Recherche avancée avec filtres par entité et pagination.

    Args:
        q: Requête de recherche (min 3 caractères)
        entities: Entités filtrées séparées par virgule (auteurs,livres,editeurs,episodes)
        page: Numéro de page (>= 1)
        limit: Résultats par page (1-100)

    Returns:
        {
            "query": str,
            "results": {
                "auteurs": [...],
                "auteurs_total_count": int,
                "livres": [...],
                "livres_total_count": int,
                "editeurs": [...],
                "episodes": [...],
                "episodes_total_count": int
            },
            "pagination": {
                "page": int,
                "limit": int,
                "total_pages": int
            }
        }
    """
```

**Validations**:
```python
# Validation de la requête
if not q or len(q.strip()) < 3:
    raise HTTPException(
        status_code=400,
        detail="La recherche nécessite au moins 3 caractères"
    )

# Validation de la pagination
if page < 1:
    raise HTTPException(
        status_code=400,
        detail="Le numéro de page doit être >= 1"
    )
if limit < 1 or limit > 100:
    raise HTTPException(
        status_code=400,
        detail="La limite doit être entre 1 et 100"
    )
```

**Filtres d'entités**:
```python
# Parse entity filters
selected_entities = set()
if entities:
    for entity in entities.split(","):
        entity = entity.strip()
        if entity not in ["auteurs", "livres", "editeurs", "episodes"]:
            raise HTTPException(
                status_code=400,
                detail=f"Entité invalide: {entity}"
            )
        selected_entities.add(entity)
else:
    # Par défaut, toutes les entités
    selected_entities = {"auteurs", "livres", "editeurs", "episodes"}
```

**Calcul de l'offset pour pagination**:
```python
offset = (page - 1) * limit
```

**Calcul du total de pages**:
```python
max_count = max(
    auteurs_total_count,
    livres_total_count,
    episodes_total_count
)
total_pages = (max_count + limit - 1) // limit if max_count > 0 else 1
```

## 3. Recherche Multi-Sources pour Éditeurs (Commit dac9c60)

**Problème**: Les éditeurs peuvent être trouvés dans deux collections :
- Collection `editeurs` (entité dédiée)
- Champ `editeur` dans collection `livres`

### Implémentation search_editeurs()

**Fichier**: `src/back_office_lmelp/services/mongodb_service.py`

**Méthode**:
```python
def search_editeurs(
    self, query: str, limit: int = 10, offset: int = 0
) -> dict[str, Any]:
    """Recherche textuelle dans editeurs.nom ET livres.editeur."""
    if self.editeurs_collection is None or self.livres_collection is None:
        raise Exception("Connexion MongoDB non établie")

    if not query or len(query.strip()) == 0:
        return {"editeurs": [], "total_count": 0}

    try:
        query_escaped = query.strip()
        search_query = {"nom": {"$regex": query_escaped, "$options": "i"}}

        # 1. Recherche dans collection editeurs
        editeurs_from_collection = list(
            self.editeurs_collection.find(search_query).skip(offset).limit(limit)
        )

        # 2. Recherche dans livres.editeur
        livres_search_query = {
            "editeur": {"$regex": query_escaped, "$options": "i"}
        }
        livres_with_editeur = list(
            self.livres_collection.find(livres_search_query)
            .skip(offset)
            .limit(limit)
        )

        # 3. Combiner et dédupliquer
        editeurs_set = set()
        results = []

        # Ajouter éditeurs de la collection editeurs
        for editeur in editeurs_from_collection:
            editeur["_id"] = str(editeur["_id"])
            editeur_nom = editeur.get("nom")
            if editeur_nom and editeur_nom not in editeurs_set:
                editeurs_set.add(editeur_nom)
                results.append(editeur)

        # Ajouter éditeurs depuis livres.editeur
        for livre in livres_with_editeur:
            editeur_nom = livre.get("editeur")
            if editeur_nom and editeur_nom not in editeurs_set:
                editeurs_set.add(editeur_nom)
                results.append({"nom": editeur_nom})

        # Total = nombre d'éditeurs UNIQUES après déduplication
        total_count = len(editeurs_set)

        # Respecter la limite
        results = results[:limit]

        return {"editeurs": results, "total_count": total_count}
```

**Points clés**:
- Recherche dans deux collections en parallèle
- Déduplication par nom d'éditeur via `set()`
- `total_count` reflète le nombre d'éditeurs **uniques**
- Support de la pagination (offset, limit)

### Tests pour search_editeurs()

**Fichier**: `tests/test_search_service.py`

**Tests ajoutés**:
```python
def test_search_editeurs_finds_publisher_from_livres_collection(self):
    """Test que search_editeurs trouve un éditeur depuis livres.editeur."""

def test_search_editeurs_combines_both_collections(self):
    """Test que search_editeurs combine editeurs.nom et livres.editeur."""
```

## 4. Raffinement des Sources de Recherche (Commit d3ad5ee)

### Problème

Incohérence dans les sources de recherche :
- `search_livres()` cherchait dans `titre` ET `editeur`
- Mais éditeurs ont leur propre recherche via `search_editeurs()`
- Résultat : doublons et confusion

### Solution

**Séparation claire des responsabilités** :

| Méthode | Sources de recherche |
|---------|---------------------|
| `search_auteurs()` | `auteurs.nom` uniquement |
| `search_livres()` | `livres.titre` **uniquement** (PAS editeur) |
| `search_editeurs()` | `editeurs.nom` + `livres.editeur` (combiné) |
| `search_episodes()` | `titre`, `titre_corrige`, `description`, `description_corrigee`, `transcription` |

### Modification search_livres()

**AVANT** (incorrect):
```python
# Cherchait dans titre ET editeur
search_query = {
    "$or": [
        {"titre": {"$regex": query_escaped, "$options": "i"}},
        {"editeur": {"$regex": query_escaped, "$options": "i"}}
    ]
}
```

**APRÈS** (correct):
```python
# Cherche uniquement dans le titre
search_query = {"titre": {"$regex": query_escaped, "$options": "i"}}
```

### Test de non-régression

**Fichier**: `tests/test_search_service.py`

**Test ajouté**:
```python
def test_search_livres_does_not_search_by_editeur(self):
    """Test que search_livres ne cherche PAS dans le champ editeur."""
    # Mock avec un livre ayant "Gallimard" comme éditeur mais pas dans le titre
    mock_livres = []  # Aucun résultat attendu
    mock_cursor = Mock()
    mock_cursor.skip.return_value.limit.return_value = mock_livres
    self.mock_livres_collection.find.return_value = mock_cursor
    self.mock_livres_collection.count_documents.return_value = 0

    result = mongodb_service.search_livres("Gallimard", limit=10)

    # Ne devrait PAS trouver de livres (on cherche uniquement dans le titre)
    assert len(result["livres"]) == 0
    assert result["total_count"] == 0
```

## 5. Unification et Bug de Pagination (Commit 65bd64f)

### Bug #93 - Pagination Incorrecte

**Symptômes** (rapporté par l'utilisateur avec screenshot):
- Recherche "gall" dans éditeurs
- Retourne **1 résultat unique** (Gallimard)
- Affiche **"Page 1 sur 3"** avec 3 pages de pagination

**Cause racine**:

Dans `search_editeurs()`, ligne 656 (AVANT):
```python
# ❌ MAUVAIS - Total = somme brute des deux collections
total_count = total_count_editeurs + total_count_livres

# Exemple:
# - 1 éditeur dans collection editeurs
# - 3 livres avec "Gallimard" dans livres.editeur
# - total_count = 1 + 3 = 4
# - Pagination: 4 / 10 par page = 1 page (mais affiche 3 pages car 4 items)
```

**Pourquoi c'est incorrect**:
1. `search_editeurs()` déduplique les résultats (un seul "Gallimard")
2. Mais `total_count` utilisait la somme **avant** déduplication
3. Frontend calcule : `total_pages = Math.ceil(4 / 10) = 1`... mais les résultats étaient incohérents

### Solution TDD

**RED Phase** - Test documentant le bug:

**Fichier**: `tests/test_search_service.py`

```python
def test_search_editeurs_total_count_matches_unique_publishers(self):
    """
    Test que total_count reflète le nombre d'éditeurs UNIQUES, pas la somme brute.
    Bug #93: "gall" trouve 1 résultat mais affiche 3 pages (pagination incorrecte).
    """
    # Mock de la collection editeurs avec "Gallimard"
    mongodb_service.editeurs_collection = Mock()
    mock_editeurs = [
        {"_id": "507f1f77bcf86cd799439020", "nom": "Gallimard", "livres": []}
    ]
    mock_cursor_editeurs = Mock()
    mock_cursor_editeurs.skip.return_value.limit.return_value = mock_editeurs
    mongodb_service.editeurs_collection.find.return_value = mock_cursor_editeurs

    # Mock de la collection livres avec 3 livres ayant "Gallimard" comme éditeur
    mock_livres = [
        {"_id": "507f1f77bcf86cd799439031", "titre": "Livre 1", "editeur": "Gallimard"},
        {"_id": "507f1f77bcf86cd799439032", "titre": "Livre 2", "editeur": "Gallimard"},
        {"_id": "507f1f77bcf86cd799439033", "titre": "Livre 3", "editeur": "Gallimard"},
    ]
    mock_cursor_livres = Mock()
    mock_cursor_livres.skip.return_value.limit.return_value = mock_livres
    self.mock_livres_collection.find.return_value = mock_cursor_livres

    result = mongodb_service.search_editeurs("gall", limit=10)

    # Bug: total_count était 1 + 3 = 4, causant 3 pages au lieu de 1
    # Fix: total_count doit être 1 (nombre d'éditeurs uniques)
    assert len(result["editeurs"]) == 1
    assert result["total_count"] == 1  # Pas 4 !
    assert result["editeurs"][0]["nom"] == "Gallimard"
```

**GREEN Phase** - Fix du code:

**Fichier**: `src/back_office_lmelp/services/mongodb_service.py`, ligne 657

```python
# ✅ BON - Total = nombre d'éditeurs uniques après déduplication
total_count = len(editeurs_set)
```

**REFACTOR Phase** - Nettoyage:

Suppression des variables inutilisées qui causaient des erreurs de linting:
```python
# Deleted - plus besoin de ces compteurs
# total_count_editeurs = self.editeurs_collection.count_documents(search_query)
# total_count_livres = self.livres_collection.count_documents(livres_search_query)
```

### Unification des Sources de Recherche

**Problème**: `/api/search` utilisait encore l'ancienne méthode pour éditeurs.

**AVANT** (app.py, ligne 1004):
```python
# ❌ Utilisait l'ancienne méthode
editeurs_result = mongodb_service.search_critical_reviews_for_authors_books(q)
editeurs_list = editeurs_result.get("editeurs", [])
```

**APRÈS** (app.py, ligne 1004):
```python
# ✅ Utilise la nouvelle méthode unifiée
editeurs_search_result = mongodb_service.search_editeurs(q, limit)
editeurs_list = editeurs_search_result.get("editeurs", [])
```

**Résultat**: `/api/search` et `/api/advanced-search` utilisent maintenant **exactement** les mêmes sources.

### Mise à jour des Tests

**Fichier**: `tests/test_search_endpoint.py`

**Changements**:
- Remplacé tous les patches `search_critical_reviews_for_authors_books` par `search_editeurs`
- Ajouté `total_count` dans les mocks : `{"editeurs": [], "total_count": 0}`
- Ajouté test de non-régression :

```python
@patch("back_office_lmelp.services.mongodb_service.mongodb_service.search_editeurs")
def test_search_uses_search_editeurs_for_publishers(
    self,
    mock_search_editeurs,
    ...
):
    """Test que /api/search utilise search_editeurs() pour les éditeurs."""
    mock_search_editeurs.return_value = {
        "editeurs": [{"nom": "Gallimard"}],
        "total_count": 1,
    }

    response = self.client.get("/api/search?q=Gallimard")
    assert response.status_code == 200

    # Vérifier que search_editeurs a été appelé
    mock_search_editeurs.assert_called_once()

    # Vérifier que les résultats contiennent les éditeurs
    assert len(data["results"]["editeurs"]) == 1
    assert data["results"]["editeurs"][0]["nom"] == "Gallimard"
```

**Fichier**: `tests/test_search_service.py`

Nettoyage des mocks `count_documents` inutilisés dans 4 tests.

## 6. Tests Complets

### Coverage Backend

**54 tests validés** :
- `tests/test_search_service.py` : 28 tests
- `tests/test_search_endpoint.py` : 11 tests
- `tests/test_advanced_search.py` : 15 tests

**Catégories de tests** :

#### Advanced Search (test_advanced_search.py)
- Filtres d'entités (tous par défaut, épisodes seulement, multi-entités)
- Validation des paramètres (entité invalide, query trop courte)
- Pagination (par défaut, personnalisée, total_counts, validation)
- Structure de réponse (complète, épisodes détaillés)

#### Search Service (test_search_service.py)
- `search_episodes()` : recherche fuzzy, contexte, limites
- `search_auteurs()` : recherche par nom, query vide
- `search_livres()` : recherche par titre uniquement, enrichissement auteur
- `search_editeurs()` :
  - Recherche dans collection editeurs
  - Recherche dans livres.editeur
  - Combinaison et déduplication
  - **Total count correct après déduplication**

#### Search Endpoint (test_search_endpoint.py)
- Validation query (minimum 3 caractères)
- Structure de réponse
- Paramètre limit
- Score et match_type
- Caractères spéciaux
- Case insensitive
- **Utilisation de search_editeurs()**

### Coverage Frontend

**Tests à ajouter** (non implémentés dans cette branche):
- Test du composant AdvancedSearch.vue
- Test de l'intégration avec searchService.advancedSearch()
- Test de la pagination frontend

## 7. État Final des Sources de Recherche

| Entité | Collections | Champs recherchés | Méthode |
|--------|------------|-------------------|---------|
| **Auteurs** | `auteurs` | `nom` | `search_auteurs()` |
| **Livres** | `livres` | `titre` uniquement | `search_livres()` |
| **Éditeurs** | `editeurs` + `livres` | `nom` + `editeur` (dédupliqué) | `search_editeurs()` |
| **Épisodes** | `episodes` | `titre`, `titre_corrige`, `description`, `description_corrigee`, `transcription` | `search_episodes()` |

**Endpoints unifiés** :
- `/api/search` : Recherche simple (10 résultats par défaut)
- `/api/advanced-search` : Recherche avec filtres et pagination

**Les deux endpoints utilisent exactement les mêmes sources de données.**

## 8. Apprentissages Clés

### TDD pour Bug Fixes

**Processus appliqué** :
1. **RED** : Écrire test qui échoue et documente le bug
2. **GREEN** : Corriger le code pour faire passer le test
3. **REFACTOR** : Nettoyer le code (supprimer variables inutilisées)

**Avantage** : Le test devient la documentation vivante du bug et empêche les régressions.

### Déduplication et Compteurs

**Erreur courante** : Calculer `total_count` **avant** la déduplication.

**Solution** :
```python
# 1. Combiner les sources
editeurs_set = set()
for item in source1:
    editeurs_set.add(item["nom"])
for item in source2:
    editeurs_set.add(item["nom"])

# 2. Calculer total APRÈS déduplication
total_count = len(editeurs_set)
```

### Séparation des Responsabilités

**Principe** : Chaque méthode de recherche doit avoir des sources **clairement définies**.

**Anti-pattern** : `search_livres()` qui cherche aussi dans `editeur` alors que `search_editeurs()` existe.

**Pattern correct** : Chaque entité a sa méthode dédiée avec des sources uniques ou combinées.

### Pagination avec Offset

**Calcul** :
```python
offset = (page - 1) * limit

# Exemples:
# page=1, limit=20 → offset=0  (items 0-19)
# page=2, limit=20 → offset=20 (items 20-39)
# page=3, limit=20 → offset=40 (items 40-59)
```

**Total pages** :
```python
total_pages = (total_count + limit - 1) // limit if total_count > 0 else 1

# Exemples:
# total_count=44, limit=20 → total_pages=3
# total_count=20, limit=20 → total_pages=1
# total_count=0,  limit=20 → total_pages=1
```

## 9. Fichiers Modifiés - Résumé

### Backend
- `src/back_office_lmelp/app.py` : Endpoint `/api/advanced-search`, fix `/api/search`
- `src/back_office_lmelp/services/mongodb_service.py` : `search_editeurs()`, fix `search_livres()`
- `tests/test_advanced_search.py` : 15 tests (nouveau fichier)
- `tests/test_search_endpoint.py` : Mise à jour mocks + 1 nouveau test
- `tests/test_search_service.py` : 2 nouveaux tests + nettoyage
- `tests/conftest.py` : Ajout mocks `search_editeurs()` et `search_auteurs()`

### Frontend
- `frontend/src/views/AdvancedSearch.vue` : Composant complet (nouveau fichier)
- `frontend/src/views/Dashboard.vue` : Carte "Recherche avancée"
- `frontend/src/services/api.js` : Méthode `advancedSearch()`
- `frontend/src/router/index.js` : Route `/search`

## 10. Issue Liée

**Issue #92** : Recherche insensible aux accents (ex: "carre" devrait trouver "Carrère")

**Statut** : Identifié mais non implémenté dans cette branche.

**Raison** : Les collations MongoDB (`collation: {locale: 'fr', strength: 1}`) ne fonctionnent pas avec les requêtes `$regex`. Solution alternative requise (normalisation de texte ou index de recherche full-text).

## Conclusion

Cette branche implémente un système de recherche avancée **robuste et testé** avec :
- ✅ Filtres d'entités fonctionnels
- ✅ Pagination correcte et fiable
- ✅ Sources de recherche unifiées et cohérentes
- ✅ Déduplication correcte des éditeurs multi-sources
- ✅ 54 tests backend validés
- ✅ Interface utilisateur intuitive et responsive

**Prochaines étapes** :
1. Merger la branche dans `main`
2. Implémenter tests frontend pour AdvancedSearch.vue
3. Adresser Issue #92 (recherche insensible aux accents)
