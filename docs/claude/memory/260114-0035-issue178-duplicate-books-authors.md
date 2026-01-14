# Détection et fusion des doublons de livres et auteurs (Issue #178)

**Date**: 2026-01-14
**Branche**: `178-detecter-et-fusionner-les-livres-en-doublon`
**Status**: Implémentation complète + documentation + corrections UX

## Résumé

Implémentation complète d'un système de détection et fusion des doublons pour les livres et auteurs, basé sur l'URL Babelio identique. La solution inclut backend (service + API), frontend (UI complète), tests exhaustifs, et documentation.

## Problème résolu

### Problème initial
- **Doublons de livres** : Plusieurs entrées pour le même livre (même URL Babelio) dues à des variations de titre/éditeur
- **Doublons d'auteurs** : Plusieurs entrées pour le même auteur (même URL Babelio) dues à des variations de nom
- **Impact** :
  - Fragmentation des données (episodes, avis_critiques répartis sur plusieurs entrées)
  - Statistiques faussées
  - Complexité de maintenance

### Solution implémentée
Système complet de détection et fusion avec :
- Détection automatique via aggregation MongoDB (groupement par `url_babelio`)
- Validation stricte (vérification `auteur_id` identique pour livres)
- Scraping Babelio pour données officielles lors de la fusion
- Interface utilisateur intuitive avec statistiques et fusion par lot
- Gestion séparée livres/auteurs avec fusion des auteurs en premier

## Architecture technique

### Backend - Service de gestion des doublons

**Fichier**: `src/back_office_lmelp/services/duplicate_books_service.py` (385 lignes)

**Classe principale**: `DuplicateBooksService`

#### Méthodes pour les livres

1. **`find_duplicate_groups_by_url()`** - Détection des doublons
   - Pipeline MongoDB aggregation avec `$group` par `url_babelio`
   - Retourne uniquement les groupes avec `count > 1`
   - Tri par taille décroissante (groupes les plus gros en premier)

2. **`validate_duplicate_group()`** - Validation avant fusion
   - **CRITICAL**: Vérifie que tous les livres ont le MÊME `auteur_id`
   - Rejette la fusion si `auteur_id` différent
   - Retourne données complètes pour la fusion

3. **`merge_duplicate_group()`** - Fusion d'un groupe
   - **Algorithme en 7 étapes** :
     1. Validation du groupe (auteur_id identique)
     2. Scraping Babelio pour titre et éditeur officiels
     3. Sélection livre primaire (plus ancien via `created_at`)
     4. Fusion episodes et avis_critiques (union + déduplication)
     5. Update livre primaire avec données Babelio + `$addToSet`
     6. Suppression des doublons
     7. Cascading update dans collection auteurs

4. **`get_duplicate_statistics()`** - Statistiques pour dashboard
   - `total_groups`: Nombre de groupes de doublons
   - `total_duplicates`: Somme de `(count - 1)` pour chaque groupe

#### Méthodes pour les auteurs

5. **`find_duplicate_authors_by_url()`** - Détection auteurs en doublon
6. **`merge_duplicate_authors()`** - Fusion auteurs
   - Scraping nom officiel depuis Babelio
   - Fusion array `livres`
   - Update références dans collection `livres` (change `auteur_id`)
7. **`get_duplicate_authors_statistics()`** - Stats auteurs

### Backend - Endpoints API

**Fichier**: `src/back_office_lmelp/app.py` (+93 lignes)

#### Endpoints livres
- `GET /api/books/duplicates/statistics` - Stats doublons livres
- `GET /api/books/duplicates/groups` - Liste groupes doublons livres
- `POST /api/books/duplicates/merge` - Fusion d'un groupe de livres

#### Endpoints auteurs
- `GET /api/authors/duplicates/statistics` - Stats doublons auteurs
- `GET /api/authors/duplicates/groups` - Liste groupes doublons auteurs
- `POST /api/authors/duplicates/merge` - Fusion d'un groupe d'auteurs

### Frontend - Interface utilisateur

**Fichier**: `frontend/src/views/DuplicateBooks.vue` (532 lignes)

#### Fonctionnalités principales

1. **Section statistiques**
   - Statistiques livres (groupes, total doublons)
   - Statistiques auteurs (groupes, total doublons)
   - Sous-sections avec emojis (📚 Livres, 👤 Auteurs)

2. **Affichage des doublons**
   - **Auteurs d'abord** puis livres (ordre logique pour fusion)
   - Cartes par groupe avec :
     - Noms/titres variantes
     - Lien vers Babelio
     - Bouton "Fusionner"
     - Résultat de fusion (succès/erreur)

3. **Fusion globale par lot**
   - Bouton "Tout fusionner (auteurs puis livres)"
   - Phase 1 : Fusion tous les auteurs
   - Rechargement des données après auteurs (mise à jour groupes livres)
   - Phase 2 : Fusion tous les livres (avec skip list)
   - Barre de progression temps réel
   - Délai 1s entre chaque fusion (rate limiting)

4. **États UX**
   - Loading, error, empty states
   - Affichage résultats fusion (episodes/avis fusionnés)
   - Messages d'erreur clairs (ex: "auteur_id mismatch")

### Frontend - Dashboard

**Fichier**: `frontend/src/views/Dashboard.vue` (modifications)

#### Ajout carte statistiques doublons
- **Compteur combiné** : Livres + Auteurs en doublon
- Computed property `totalDuplicatesCount()` :
  ```javascript
  totalDuplicatesCount() {
    if (this.duplicateBooksCount === null || this.duplicateAuthorsCount === null) {
      return null;  // Encore en chargement
    }
    return this.duplicateBooksCount + this.duplicateAuthorsCount;
  }
  ```
- **Chargement parallèle** avec `Promise.all()` (affichage simultané)
- Cliquable → Navigation vers `/duplicates`
- Tooltip explicatif

### Tests

#### Tests backend

**Fichier**: `tests/test_duplicate_books_service.py` (459 lignes)

**Approche TDD incrémentale** :

1. **Test intégration haut niveau** (`test_merge_should_union_episodes_and_avis`)
   - Business problem : Fusionner 2 livres avec episodes différents
   - Vérifications :
     - Livre primaire = le plus ancien
     - Episodes dédupliqués (ep1, ep2, ep3 → 3 uniques, pas 4)
     - Avis dédupliqués
     - Données Babelio utilisées (titre, éditeur officiels)
     - MongoDB `$addToSet` appelé

2. **Test validation critique** (`test_should_reject_different_auteur_ids`)
   - Vérifie rejet si `auteur_id` différent
   - Message d'erreur explicite

3. **Test intégration Babelio** (`test_should_use_babelio_official_data`)
   - Données officielles Babelio utilisées (pas données locales)

4. **Test détection** (`test_should_find_duplicate_groups_by_url`)
   - Aggregation MongoDB correcte
   - Groupes avec count > 1 uniquement

5. **Test statistiques** (`test_should_calculate_statistics`)
   - Calcul `total_groups` et `total_duplicates` correct

**Fixtures** :
- `mock_mongodb_service` : Mock collections MongoDB
- `mock_babelio_service` : Mock scraping Babelio
- `duplicate_books_service` : Instance service avec mocks

#### Tests frontend

**Fichier**: `frontend/src/views/__tests__/DuplicateBooks.spec.js` (339 lignes)

**Tests implémentés** :

1. `loads statistics and groups on mount` - Chargement initial 4 endpoints
2. `displays loading state while fetching data` - État chargement
3. `displays error message on fetch failure` - Gestion erreurs
4. `displays statistics card with correct values` - Affichage stats
5. `displays duplicate groups list` - Liste groupes
6. `toggles skip checkbox correctly` - Fonctionnalité skip
7. `merges a group successfully` - Fusion succès
8. `handles merge error correctly` - Gestion erreur fusion
9. `calculates batch progress percentage correctly` - Calcul progression
10. `displays empty state when no duplicates` - État vide
11. `disables merge button during processing` - Désactivation bouton

**Helper** : `mockAllEndpoints()` - Mock 4 endpoints API (books stats/groups, authors stats/groups)

## Patterns et apprentissages critiques

### 1. Chargement parallèle (Frontend)

**Problème** : Compteurs s'affichaient en 2 vagues (séquentiel)

```javascript
// ❌ MAUVAIS - Chargement séquentiel
async mounted() {
  await this.loadStatistics();
  await this.loadCollectionsStatistics();
  await this.loadDuplicateStatistics();
}

// ✅ CORRECT - Chargement parallèle
async mounted() {
  await Promise.all([
    this.loadStatistics(),
    this.loadCollectionsStatistics(),
    this.loadDuplicateStatistics()
  ]);
}
```

**Impact** : UX améliorée, affichage simultané de tous les compteurs.

### 2. Propriétés calculées avec null safety

```javascript
computed: {
  totalDuplicatesCount() {
    // Retourner null si composants encore en chargement
    if (this.duplicateBooksCount === null || this.duplicateAuthorsCount === null) {
      return null;
    }
    return this.duplicateBooksCount + this.duplicateAuthorsCount;
  }
}
```

**Pattern** : Évite d'afficher des sommes partielles incorrectes.

### 3. Ordre de fusion (auteurs puis livres)

**Logique métier** :
- Fusionner auteurs D'ABORD modifie les `auteur_id` dans collection livres
- Cela peut résoudre certains doublons de livres (même `auteur_id` après fusion)
- **Implémentation** : Rechargement données après fusion auteurs (`await this.loadData()`)

### 4. Pattern à 3 états (Frontend)

```vue
<div v-if="loading" class="loading">Chargement...</div>
<div v-if="error" class="alert alert-error">{{ error }}</div>
<div v-if="!loading && !error && data.length > 0"><!-- Données --></div>
<div v-if="!loading && !error && data.length === 0" class="empty-state">
  Aucune donnée 🎉
</div>
```

**Ordre priorité** : loading → error → data → empty

### 5. Validation stricte auteur_id (Backend)

**CRITICAL** : Rejeter fusion si `auteur_id` différent

```python
unique_auteur_ids = list(set(auteur_ids))
if len(unique_auteur_ids) > 1:
    return {
        "valid": False,
        "errors": [f"auteur_id mismatch: Expected {unique_auteur_ids[0]}, found {unique_auteur_ids[1]}"]
    }
```

**Raison** : Un livre ne peut avoir qu'un seul auteur dans le modèle actuel.

### 6. MongoDB $addToSet pour déduplication

```python
livres_collection.update_one(
    {"_id": primary_book["_id"]},
    {
        "$addToSet": {
            "episodes": {"$each": unique_episodes},
            "avis_critiques": {"$each": unique_avis}
        }
    }
)
```

**Avantage** : MongoDB déduplique automatiquement.

### 7. Cascading updates

**Étapes critiques** après suppression doublons :

1. **Collection auteurs** : Retirer références livres supprimés
   ```python
   auteurs_collection.update_one(
       {"_id": auteur_id},
       {"$pull": {"livres": {"$in": duplicate_ids_str}}}
   )
   ```

2. **Collection livres** : Mettre à jour `auteur_id` (fusion auteurs)
   ```python
   livres_collection.update_many(
       {"auteur_id": {"$in": duplicate_ids}},
       {"$set": {"auteur_id": primary_auteur["_id"]}}
   )
   ```

### 8. Rate limiting scraping Babelio

**Pattern** : Délai entre requêtes pour éviter ban

```javascript
for (let i = 0; i < items.length; i++) {
  await this.processItem(items[i]);
  await new Promise(resolve => setTimeout(resolve, 1000));  // 1s délai
}
```

## Documentation créée

### 1. Charte graphique Vue.js

**Fichier** : `docs/dev/vue-ui-patterns.md`

**Contenu** :
- Structure des composants Vue
- Cartes de statistiques (Dashboard vs pages détail)
- États de chargement/erreur/vide
- Boutons d'action et hiérarchie visuelle
- Indicateurs de progression
- Opérations par lot
- Palette de couleurs
- Chargement parallèle des données
- Design responsive

**Ajouté dans** :
- `docs/dev/.pages` (navigation MkDocs)
- `docs/dev/claude-ai-guide.md` (section Frontend UI/UX Patterns)
- `CLAUDE.md` (référence rapide)

### 2. Pattern axios URLs relatives

**Ajouté dans** : `CLAUDE.md`

```javascript
// ✅ CORRECT - URL relative
const response = await axios.get('/api/books/duplicates/statistics');

// ❌ MAUVAIS - URL absolue
const response = await axios.get('http://localhost:8000/api/...');
```

**Raison** : Proxy Vite redirige automatiquement `/api/*` vers backend.

### 3. Limitation co-auteurs

**Ajouté dans** : `CLAUDE.md`

**Modèle actuel** : Un seul `auteur_id` par livre

**Conséquences** :
- Livres avec co-auteurs non supportés correctement
- Fusion rejette si `auteur_id` différent
- Solution actuelle : Choisir un auteur principal

**Évolution future** : `auteur_ids: list[ObjectId]` (nécessite migration)

## Statistiques

### Code ajouté
- **Total** : 1819 lignes
- **Backend** : 843 lignes (service 385 + tests 459)
- **Frontend** : 871 lignes (vue 532 + tests 339)
- **API** : 93 lignes

### Fichiers créés
- `src/back_office_lmelp/services/duplicate_books_service.py`
- `tests/test_duplicate_books_service.py`
- `frontend/src/views/DuplicateBooks.vue`
- `frontend/src/views/__tests__/DuplicateBooks.spec.js`
- `docs/dev/vue-ui-patterns.md`

### Fichiers modifiés
- `src/back_office_lmelp/app.py` (endpoints API)
- `src/back_office_lmelp/services/babelio_service.py` (ajout `fetch_author_name_from_url`)
- `frontend/src/views/Dashboard.vue` (carte stats doublons)
- `frontend/src/router/index.js` (route `/duplicates`)
- `CLAUDE.md` (patterns Vue, axios, co-auteurs)
- `docs/dev/claude-ai-guide.md` (section Frontend UI/UX)
- `docs/dev/.pages` (navigation MkDocs)
- `.claude/settings.local.json` (accept mcp aggregate)

## Commits de la branche

1. **a00f660** - `accept mongo mcp aggregate`
   - Configuration MCP MongoDB

2. **f8043fa** - `feat(duplicates): Add duplicate books detection and merge service`
   - Service backend complet
   - Tests backend (5 classes de tests)

3. **3156486** - `feat(duplicates): Add API endpoints for duplicate books management`
   - 6 endpoints API (livres + auteurs)

4. **5cd3189** - `feat(duplicates): Add frontend UI for duplicate books management`
   - Vue complète avec fusion par lot
   - Navigation Dashboard → `/duplicates`

5. **3c8ddd7** - `test(duplicates): Add comprehensive tests for DuplicateBooks component`
   - 11 tests frontend Vitest

## Résultats tests

### Backend
- **5 classes de tests** : TestMergeDuplicateGroup, TestValidateDuplicateGroup, TestBabelioIntegration, TestFindDuplicateGroups, TestGetDuplicateStatistics
- **Tous les tests passent** ✅

### Frontend
- **11 tests Vitest** couvrant :
  - Chargement données
  - États UI (loading, error, empty)
  - Fusion individuelle et gestion erreurs
  - Progression batch
  - Interactions utilisateur
- **Tous les tests passent** ✅

## Modifications post-commits (session actuelle)

### 1. Suppression système d'historique

**Raison** : Complexité excessive pour bénéfice limité

**Modifié** :
- `duplicate_books_service.py` : Retrait insertions `merge_history`
- `app.py` : Simplification statistiques (retrait `merged_count`, `pending_count`)
- Tests backend/frontend : Mise à jour assertions

### 2. Amélioration UX Dashboard

**Problème** : Compteurs s'affichaient en 2 temps

**Solution** : `Promise.all()` dans `mounted()`

### 3. Documentation exhaustive

- Charte graphique Vue.js (nouveau document)
- Pattern axios URLs relatives
- Limitation co-auteurs modèle actuel

## Prochaines étapes (TODO)

1. ✅ Documenter charte graphique Vue
2. ✅ Documenter pattern axios
3. ✅ Documenter limitation co-auteurs
4. ✅ Appeler /stocke-memoire
5. ⏳ Mettre à jour documentation (/docs)
6. ⏳ Tester `mkdocs build --strict`
7. ⏳ Vérifier CI/CD avec `gh run view`
8. ⏳ Demander validation utilisateur
9. ⏳ Préparer et merger PR
10. ⏳ Retour sur main

## Learnings pour futures implémentations

### Architecture
- **Service layer** : Séparer logique métier (services) de l'API (endpoints)
- **TDD incrémental** : Test haut niveau → tests validation → implémentation
- **Cascading updates** : Penser aux collections liées lors des modifications

### Frontend
- **Chargement parallèle** : Toujours utiliser `Promise.all()` pour stats multiples
- **Null safety** : Computed properties doivent gérer états de chargement
- **Ordre logique** : Fusion auteurs avant livres (impact sur données)
- **Pattern 3 états** : loading → error → data → empty

### Tests
- **Mocks réalistes** : Utiliser vrais types MongoDB (datetime, ObjectId)
- **Business tests first** : Test problème métier avant tests unitaires
- **Helper functions** : Mutualiser mocks complexes (ex: `mockAllEndpoints`)

### Documentation
- **Progressive** : Documentation pendant implémentation (pas après)
- **Exemples concrets** : Code snippets avec cas réels du projet
- **Liens internes** : Backticks pour code source, markdown pour URLs externes
