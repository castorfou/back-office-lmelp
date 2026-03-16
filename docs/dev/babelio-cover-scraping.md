# Scraping des couvertures Babelio (développeur)

Ce document décrit l'architecture et l'implémentation du système de récupération automatique des couvertures depuis Babelio.

## Architecture générale

Le scraping de couvertures ne peut pas se faire directement depuis le navigateur (CORS). La page Babelio est récupérée côté **backend** via `aiohttp`, à la demande du frontend.

```
Frontend (Vue) ──POST /api/babelio/extract-cover-url──▶ Backend (FastAPI)
                    { babelio_url, expected_title,                  │
                      babelio_cookies }                              │
                                                           aiohttp.GET babelio_url
                                                           (avec Cookie header)
                                                                     │
                                                           parse og:image + h1
                                                                     │
                                                           ◀── { cover_url | TITLE_MISMATCH }
```

## Endpoint backend : `/api/babelio/extract-cover-url`

**Méthode** : POST
**Service** : `BabelioService.fetch_cover_url_from_babelio_page()`
**Fichier** : `src/back_office_lmelp/services/babelio_service.py`

### Headers critiques pour passer la détection bot Babelio

```python
headers = {
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-User": "?1",
    "Accept-Encoding": "gzip, deflate",  # PAS de br (aiohttp ne supporte pas Brotli)
    "Cookie": babelio_cookies,           # Cookie transmis depuis le navigateur
}
```

**Important** : Ne pas ajouter `br` dans `Accept-Encoding`. aiohttp ne supporte pas Brotli et lèverait `Can not decode content-encoding: brotli`.

### Transmission du cookie Babelio

Le cookie Babelio est obtenu par le navigateur (qui a une IP non bloquée) et transmis au backend via le body du POST. Le backend le place dans le header `Cookie` de la requête aiohttp.

```python
# Dans app.py
class ExtractCoverUrlRequest(BaseModel):
    babelio_url: str
    expected_title: str | None = None
    babelio_cookies: str = ""

# Dans babelio_service.py
async with session.get(url, headers={..., "Cookie": babelio_cookies}) as response:
    html = await response.text()
```

## Détection de redirection (TITLE_MISMATCH)

Babelio redirige parfois une URL obsolète vers un livre différent. La fonction valide le titre `<h1>` de la page contre le titre attendu.

### Format de retour

- **Succès** : URL de la couverture (chaîne `og:image`)
- **Mismatch** : `TITLE_MISMATCH:<page_title>|<cover_url_found>`

Le `cover_url_found` est l'`og:image` trouvée sur la mauvaise page — proposée à l'utilisateur pour décision manuelle.

### Parsing dans app.py

```python
if result.startswith("TITLE_MISMATCH:"):
    rest = result[len("TITLE_MISMATCH:"):]
    parts = rest.split("|", 1)
    page_title = parts[0]
    cover_url_found = parts[1] if len(parts) > 1 else ""
```

## Normalisation pour la comparaison de titres

`normalize_for_cover_title_matching()` dans `src/back_office_lmelp/utils/text_utils.py` étend `normalize_for_matching()` avec :

- Suppression de ponctuation : `, . : ( ) « »`
- Tirets → espaces
- Re-collapse whitespace

Cas gérés : virgule absente, tiret vs espace, guillemets, espacement `:`, parenthèses vs `,`, ligatures œ/æ, accents.

La comparaison utilise **la containment** en plus de l'égalité : si l'un des deux titres normalisés est contenu dans l'autre, c'est un match (gère les sous-titres).

## Champs MongoDB sur la collection `livres`

| Champ | Type | Signification |
|-------|------|--------------|
| `url_cover` | String | URL de la couverture récupérée |
| `cover_mismatch_page_title` | String | Titre affiché sur la mauvaise page Babelio |
| `cover_mismatch_url_found` | String | URL cover trouvée sur la mauvaise page (suggestion) |

## Endpoints de gestion des couvertures

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/api/babelio-migration/covers/pending` | Livres avec `url_babelio` sans `url_cover` ni mismatch |
| POST | `/api/babelio-migration/covers/save` | Sauvegarde `url_cover` sur un livre |
| GET | `/api/babelio-migration/covers/mismatch` | Livres avec `cover_mismatch_page_title` |
| POST | `/api/babelio-migration/covers/save-mismatch` | Stocke mismatch + `cover_url_found` |
| POST | `/api/babelio-migration/covers/clear-mismatch` | Efface `cover_mismatch_page_title` (cas traité) |
| POST | `/api/babelio/extract-cover-url` | Proxy scraping (backend → Babelio) |

## Service BabelioMigrationService — méthodes couvertures

Fichier : `src/back_office_lmelp/services/babelio_migration_service.py`

- `save_cover_url(livre_id, url_cover)` — `$set {"url_cover": ...}`
- `get_books_pending_covers()` — livres avec `url_babelio`, sans `url_cover` et sans `cover_mismatch_page_title`
- `save_cover_mismatch(livre_id, page_title, cover_url_found=None)` — stocke le mismatch
- `get_cover_mismatch_cases()` — retourne `_id`, `titre`, `url_babelio`, `cover_mismatch_page_title`, `cover_mismatch_url_found`
- `clear_cover_mismatch(livre_id)` — `$unset cover_mismatch_page_title`

## Statistiques dans `get_migration_status()`

- `covers_total` = `migrated_count` (livres avec `url_babelio`)
- `covers_with_url` = livres avec `url_cover`
- `covers_mismatch_count` = livres avec `cover_mismatch_page_title`
- `covers_pending` = livres avec `url_babelio`, sans `url_cover` **et** sans `cover_mismatch_page_title`

## Mock aiohttp dans les tests

La session aiohttp est créée par requête (pas de session partagée). Patcher :

```python
with patch("back_office_lmelp.services.babelio_service.aiohttp.ClientSession", return_value=mock_session):
    result = await service.fetch_cover_url_from_babelio_page(url, expected_title="...")
```

## Voir aussi

- `src/back_office_lmelp/services/babelio_service.py` — `fetch_cover_url_from_babelio_page()`
- `src/back_office_lmelp/services/babelio_migration_service.py` — méthodes cover
- `src/back_office_lmelp/utils/text_utils.py` — `normalize_for_cover_title_matching()`
- `tests/test_babelio_cover_title_validation.py` — tests de validation de titre
- `tests/test_babelio_cover_service.py` — tests du service de scraping
- `tests/test_babelio_cover_endpoints.py` — tests des endpoints
