# Issue #238 — url_cover dans les livres + traitement couvertures Babelio

## Contexte

Ajout du champ `url_cover` sur les livres et d'une section dédiée dans `/babelio-migration` permettant de récupérer automatiquement les couvertures depuis Babelio, avec gestion des cas à traiter manuellement.

---

## Architecture générale

### Scraping couverture (backend proxy)

Le scraping ne peut PAS se faire depuis le navigateur (CORS). La page est récupérée côté backend via `aiohttp` dans `fetch_cover_url_from_babelio_page()` dans `src/back_office_lmelp/services/babelio_service.py`.

**Headers critiques pour passer le bot-detection Babelio :**
- `Sec-Fetch-Dest: document`, `Sec-Fetch-Mode: navigate`, `Sec-Fetch-Site: same-origin`, `Sec-Fetch-User: ?1`
- `Accept-Encoding: gzip, deflate` — **pas de `br`** (aiohttp ne supporte pas Brotli)
- Cookie Babelio transmis depuis le navigateur via `sessionStorage` → body POST → header `Cookie` aiohttp

**Session aiohttp créée par requête** (pas de session partagée) — timeout 10s/5s.

### Détection de redirection (TITLE_MISMATCH)

Babelio redirige parfois une URL obsolète vers un autre livre. On valide le `<h1>` de la page contre le titre attendu via `normalize_for_cover_title_matching()` dans `src/back_office_lmelp/utils/text_utils.py`.

**Format de retour en cas de mismatch :**
```
TITLE_MISMATCH:<page_title>|<cover_url_found>
```
La partie `cover_url_found` est l'`og:image` trouvée sur la mauvaise page — proposée à l'utilisateur pour décision manuelle.

**`normalize_for_cover_title_matching()`** étend `normalize_for_matching()` avec :
- Suppression ponctuation : `, . : ( ) « »`
- Tirets → espaces
- Re-collapse whitespace

Cas gérés : virgule absente, tiret vs espace, guillemets, espacement `:`, parenthèses vs `,`, ligatures œ/æ, accents.

---

## Champs MongoDB ajoutés sur `livres`

| Champ | Type | Signification |
|-------|------|--------------|
| `url_cover` | String | URL de la couverture récupérée |
| `cover_mismatch_page_title` | String | Titre affiché sur la mauvaise page Babelio |
| `cover_mismatch_url_found` | String | URL cover trouvée sur la mauvaise page (suggestion) |

---

## Endpoints API ajoutés

- `GET /api/babelio-migration/covers/pending` — livres avec `url_babelio` sans `url_cover` ni mismatch
- `POST /api/babelio-migration/covers/save` — sauvegarde `url_cover` sur un livre
- `GET /api/babelio-migration/covers/mismatch` — livres avec `cover_mismatch_page_title`
- `POST /api/babelio-migration/covers/save-mismatch` — stocke mismatch + `cover_url_found`
- `POST /api/babelio-migration/covers/clear-mismatch` — efface `cover_mismatch_page_title` (cas traité)
- `POST /api/babelio/extract-cover-url` — proxy scraping (backend → Babelio)

---

## Service : BabelioMigrationService

Nouvelles méthodes dans `src/back_office_lmelp/services/babelio_migration_service.py` :
- `save_cover_url(livre_id, url_cover)`
- `get_books_pending_covers()` — exclut les livres avec `cover_mismatch_page_title`
- `save_cover_mismatch(livre_id, page_title, cover_url_found=None)`
- `get_cover_mismatch_cases()` — retourne `_id`, `titre`, `url_babelio`, `cover_mismatch_page_title`, `cover_mismatch_url_found`
- `clear_cover_mismatch(livre_id)` — `$unset cover_mismatch_page_title`

Stats dans `get_migration_status()` :
- `covers_total` = `migrated_count` (livres avec `url_babelio`)
- `covers_with_url` = livres avec `url_cover`
- `covers_mismatch_count` = livres avec `cover_mismatch_page_title`
- `covers_pending` = livres avec `url_babelio`, sans `url_cover` **et** sans `cover_mismatch_page_title`

Stats dans `stats_service.py` :
- `books_without_cover` = livres avec `url_babelio` mais sans `url_cover`

---

## Frontend : BabelioMigration.vue

### Section Couvertures (après Livres + Auteurs)

Structure :
1. Stats grid (4 cartes) : Liés à Babelio / Liés avec succès / À traiter manuellement / En attente
2. Légende compacte (`covers-legend`) — même style que livres/auteurs
3. Section cookie Babelio (instructions DevTools, textarea, sessionStorage)
4. Bouton "Lancer la liaison des couvertures"
5. Progress panel (logs ⚠️/✅/❌)
6. **Section "À traiter manuellement"** avec champ URL pré-rempli + bouton Sauvegarder + Ignorer

### Migration automatique (`startCoverMigration`)

- Fetch `/api/babelio-migration/covers/pending`
- Pour chaque livre : POST `/api/babelio/extract-cover-url` avec `babelio_cookies` depuis `sessionStorage`
- Délai 5s entre requêtes
- Si `title_mismatch` → POST `covers/save-mismatch` avec `cover_url_found`
- Rechargement des données à la fin

### Cookie Babelio

- Stocké dans `sessionStorage` clé `babelio_cookies`
- Instructions : F12 → Réseau → recharger babelio.com → clic 1ère requête → Request Headers → Cookie → Copy Value
- Nécessaire car les IPs de serveur sont bloquées par Babelio sans cookie valide

### Légendes

Les légendes livres et auteurs sont maintenant en format compact (`covers-legend`) placées directement sous leurs stats respectives. L'ancienne `legend-section` (bloc séparé) a été supprimée.

### Scroll ancre #covers

- `scrollBehavior` dans `src/back_office_lmelp/../frontend/src/router/index.js` gère `to.hash` → `{ el: to.hash, behavior: 'smooth' }`
- Dans `BabelioMigration.vue` `loadData()` : après chargement, si `this.$route.hash` → `scrollIntoView` (pour navigation depuis Dashboard où la route est déjà active)

---

## Dashboard

Carte "Livres sans couverture" dans `frontend/src/views/Dashboard.vue` :
- Source : `collectionsStatistics.books_without_cover`
- Cachée si 0
- Navigation : `navigateToBabelioCovers()` → `/babelio-migration#covers`

---

## Points techniques importants

### Pas de brotli dans aiohttp
`Accept-Encoding: gzip, deflate` uniquement. Ajouter `br` provoque une erreur `Can not decode content-encoding: brotli`.

### TITLE_MISMATCH format pipe
Le sentinel `TITLE_MISMATCH:<title>|<cover_url>` utilise `|` comme séparateur. Parsing : `rest.split("|", 1)`. Si pas de `|` (vieux format) → `cover_url = ""`.

### covers_pending exclut les mismatches
`covers_pending` ne compte que les livres sans `url_cover` ET sans `cover_mismatch_page_title`. Les mismatches ont leur propre compteur.

### normalize_for_cover_title_matching vs normalize_for_matching
- `normalize_for_matching` : usage général (matching auteur/titre, tags Calibre)
- `normalize_for_cover_title_matching` : spécifique couvertures, supprime ponctuation et normalise tirets en espaces

---

## Tests

- `tests/test_babelio_cover_title_validation.py` — 10 tests sur `fetch_cover_url_from_babelio_page` (mismatch, accents, ponctuation, containment, format pipe)
- `tests/test_babelio_migration_service.py` — 10 tests dont save/get/clear cover mismatch
- `tests/test_text_utils.py` — 98 assertions sur `normalize_for_cover_title_matching`
- `tests/test_babelio_cover_endpoints.py` — endpoints cover (save, extract, mismatch response)
- `tests/test_babelio_cover_service.py` — scraping service (og:image, img CVT_, fallbacks)

**Mock aiohttp** : patcher `back_office_lmelp.services.babelio_service.aiohttp.ClientSession` (pas `service.session` — la session est créée par requête).

---

## Commits de la branche

- `5dadb1a` feat(#238): ajout initial url_cover + section Couvertures + proxy scraping
- `dfd05ee` délai 5s entre requêtes (réglage utilisateur)
- `047c07c` feat(#238): section "À traiter manuellement", TITLE_MISMATCH|cover_url, légendes compactes, scroll #covers
- `53f2036` feat(#238): tests unitaires normalize_for_cover_title_matching
