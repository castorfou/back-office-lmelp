# Issue #216 — Page /onkindle : liste des livres Calibre avec tag "onkindle"

## Résumé

Création d'une nouvelle page `/onkindle` affichant les livres Calibre tagués `onkindle`, enrichis avec les données MongoDB (note moyenne, lien Babelio, liens vers les pages livre/auteur).

## Architecture

### Backend (3 nouvelles fonctions)

**`src/back_office_lmelp/services/mongodb_service.py`** — `get_notes_for_livres(livre_ids: list[str]) -> dict[str, float]`
- Agrégation sur la collection `avis` (PAS `avis_critiques` !)
- `livre_oid` est un **String** dans `avis`, donc les ids sont passés tels quels
- Retourne `{livre_id: note_moyenne}` pour enrichissement
- **Bug corrigé** : utilisation de `avis_collection` et non `avis_critiques_collection`

**`src/back_office_lmelp/services/calibre_matching_service.py`** — `get_onkindle_books() -> list[dict]`
- Réutilise `_get_data()` (cache TTL 300s) pour Calibre + MongoDB
- Filtre les livres Calibre avec `"onkindle" in book.get("tags", [])`
- Matching titre Calibre ↔ MongoDB via `normalize_for_matching()`
- Appelle `mongodb_service.get_notes_for_livres()` pour enrichir avec les notes
- Retourne liste triée par titre avec : `calibre_id`, `titre`, `auteurs`, `mongo_livre_id`, `auteur_id`, `note_moyenne`, `url_babelio`

**`src/back_office_lmelp/app.py`** — `GET /api/calibre/onkindle`
- Retourne 503 si Calibre non disponible
- Délègue à `calibre_matching_service.get_onkindle_books()`
- Retourne `{books: [...], total: N}`

### Frontend (5 fichiers modifiés/créés)

**`frontend/src/views/OnKindle.vue`** (nouveau)
- Table style Palmares (`palmares-table`, `palmares-row`)
- Colonnes : **Auteur** | **Titre** (bold) | **Note** | **Babelio** (icône SVG)
- Links style Emissions : `color: #0066cc`, auteur avant titre
- Tri par colonne avec indicateur ▲/▼/⇅, `sort-active` class
- Tri note : décroissant par défaut (meilleure note d'abord)
- **Persistance URL** : `?sort=auteur&dir=asc` via `created()` + `$router.replace()`
- **Tri accent-insensitif** : `localeCompare(str, 'fr', { sensitivity: 'base' })` — évite que "À" tombe en dernier
- Icône Babelio : `@/assets/babelio-symbol-liaison.svg` 24×24px

**`frontend/src/services/api.js`** — `calibreService.getOnKindleBooks()`

**`frontend/src/router/index.js`** — route `/onkindle`

**`frontend/src/views/Dashboard.vue`** — carte "OnKindle" → `/onkindle`

**`frontend/src/views/__tests__/OnKindle.spec.js`** (nouveau, 25 tests)

## Points TDD notables

### Bug : mauvaise collection MongoDB pour les notes
- `get_notes_for_livres()` initialement codée avec `avis_critiques_collection` (résumés LLM, pas de champ `note`)
- Corrigé vers `avis_collection` qui contient les vraies notes
- Test dédié : `test_uses_avis_collection_not_avis_critiques`

### Bug : tri insensible aux accents
- `.toLowerCase()` + opérateurs `<`/`>` JS → `À` (U+00C0) sort après `Z`
- Fix : `strA.localeCompare(strB, 'fr', { sensitivity: 'base' })`
- Test : `sorts accent titles correctly — À prendre before Zola`

### Persistance du tri via URL
- `sortBy()` doit être `async` pour `await this.$router.replace()`
- Tests URL : utiliser `await wrapper.vm.sortBy('auteur')` + `$nextTick()` (pas `trigger('click')` + `flushPromises`)

## Collections MongoDB importantes

| Collection | Champ note | Type livre_oid |
|---|---|---|
| `avis` | `note` (Number) | String |
| `avis_critiques` | aucun `note` | String |

## Tests backend (12 tests dans `tests/test_onkindle_endpoint.py`)
- Endpoint `/api/calibre/onkindle` : 200 avec books+total, 503 si Calibre absent
- `MongoDBService.get_notes_for_livres()` : dict par livre_id, gestion liste vide
- `CalibreMatchingService.get_onkindle_books()` : filtre onkindle, enrichissement MongoDB, retourne [] si Calibre absent
- Vérification `avis_collection.aggregate` appelé (pas `avis_critiques_collection`)
