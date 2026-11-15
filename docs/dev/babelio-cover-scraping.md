# Scraping des couvertures Babelio (développeur)

Ce document décrit l'architecture et l'implémentation du système de récupération automatique des couvertures depuis Babelio.

## Architecture générale

Le scraping de couvertures ne peut pas se faire directement depuis le navigateur (CORS). La page Babelio est récupérée côté **backend**, par la passerelle unique `BabelioService._fetch_page()`, à la demande du frontend.

```
Frontend (Vue) ──POST /api/babelio/extract-cover-url──▶ Backend (FastAPI)
                    { babelio_url, expected_title }                 │
                                                           _fetch_page(babelio_url)
                                                           (cookie stocké côté serveur)
                                                                     │
                                                           parse og:image + h1
                                                                     │
                                                           ◀── { cover_url | TITLE_MISMATCH }
```

## Endpoint backend : `/api/babelio/extract-cover-url`

**Méthode** : POST
**Service** : `BabelioService.fetch_cover_url_from_babelio_page()`
**Fichier** : `src/back_office_lmelp/services/babelio_service.py`

### En-têtes et cookie

Les en-têtes de navigation Firefox (`Sec-Fetch-*`, `User-Agent` et `Accept-Language` du navigateur qui a fourni le cookie) sont construits par `BabelioService._get_page_headers()`, et la requête part par `_send()` (empreinte TLS/HTTP2 de Firefox via `curl_cffi`).

Le seul cookie envoyé est celui du serveur, enregistré par `POST /api/babelio/cookie` (panneau **🔑 Cookie Babelio**). La requête du frontend ne transporte aucun cookie : un cookie joint par le client échapperait au contrôle d'âge (`BABELIO_COOKIE_MAX_AGE_SEC`), et un vieux `jstsToken` provoque un 403, que Babelio transforme en ban IP.

```python
# Dans app.py
class ExtractCoverUrlRequest(BaseModel):
    babelio_url: str
    expected_title: str | None = None
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

## Mock dans les tests

Mocker le point de sortie HTTP unique `_send()`, qui renvoie une `BabelioResponse(status, body)` (corps encodé en `cp1252`, comme Babelio) :

```python
send = AsyncMock(return_value=BabelioResponse(status=200, body=html.encode("cp1252")))
with patch.object(service, "_send", send):
    result = await service.fetch_cover_url_from_babelio_page(url, expected_title="...")
```

## Voir aussi

- `src/back_office_lmelp/services/babelio_service.py` — `fetch_cover_url_from_babelio_page()`
- `src/back_office_lmelp/services/babelio_migration_service.py` — méthodes cover
- `src/back_office_lmelp/utils/text_utils.py` — `normalize_for_cover_title_matching()`
- `tests/test_babelio_cover_title_validation.py` — tests de validation de titre
- `tests/test_babelio_cover_service.py` — tests du service de scraping
- `tests/test_babelio_cover_endpoints.py` — tests des endpoints
