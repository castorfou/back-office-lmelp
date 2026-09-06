# Issue #295 — Synchronisation RSS "Le Masque et la Plume" + téléchargement audio + monitoring

## Contexte métier

L'utilisateur a un workflow n8n/Automatisch hébergé sur son NAS qui scrute le flux RSS de l'émission "Le Masque et la Plume" (France Inter), détecte les nouveaux épisodes de plus de 15 minutes et envoie déjà une notification ntfy.sh. Auparavant, l'étape suivante ("ajouter l'épisode à la base de données lmelp") se faisait manuellement via le frontoffice Streamlit `lmelp` (projet séparé, clic sur "🔄 Rafraîchir Episodes"). Cette issue déporte cette étape dans `back-office-lmelp`, exposée via un endpoint API REST appelable par l'automatisation externe, avec une UI de monitoring dédiée.

Cette chaîne s'inscrit dans une automatisation progressive plus large : RSS → téléchargement audio (cette issue) → transcription PGX (future issue, manuelle aujourd'hui) → génération de résumé/avis critique (déjà automatisé dans `back-office-lmelp` via `avis_critiques_generation_service`).

## Découvertes clés

### Le champ `episode_page_url` n'existe pas dans `lmelp`
C'est un champ propre à `back-office-lmelp` (Issue #129), rempli aujourd'hui via un clic manuel sur `POST /api/episodes/{id}/fetch-page-url` qui scrape RadioFrance. Il sert ensuite à `avis_critiques_generation_service.generate_full_summary()` (`src/back_office_lmelp/app.py:4287-4292`) pour extraire des métadonnées. Décision utilisateur : ne PAS l'auto-remplir depuis le flux RSS pour cette issue (même si le lien direct existe dans `entry.links` type `text/html`) — garder le geste manuel existant, cohérent avec toute création d'épisode.

### La collection MongoDB `episodes` contenait déjà `url` et `audio_rel_filename`
Vérifié via `mcp__MongoDB__collection-schema` + `find` avant toute implémentation (règle CLAUDE.md) : ces deux champs existaient déjà en base (écrits historiquement par `lmelp`, qui partage la même base MongoDB) mais n'étaient pas exposés par le modèle `Episode` (`src/back_office_lmelp/models/episode.py`). Il fallait réutiliser exactement ces noms, pas en inventer de nouveaux.

### Bug réel détecté uniquement par le test manuel : `PydanticSerializationError` sur `ObjectId`
Les 75 tests automatisés (tous mockés) ne l'ont pas détecté. En conditions réelles, `pymongo.insert_one(log_data)` **mute** le dict passé en argument en y injectant `_id` (un `ObjectId`). Comme `RssSyncService.sync()` appelait `self.mongodb_service.insert_rss_download_log(result)` puis `return result` sur le **même objet**, le dict retourné à l'endpoint FastAPI se retrouvait avec un `_id: ObjectId(...)` non sérialisable en JSON → 500 sur `POST /api/rss/sync`. Fix : passer une **copie défensive** (`dict(result)`) à l'insertion Mongo, jamais l'objet retourné à l'appelant HTTP. Un test dédié reproduit fidèlement ce comportement pymongo via un mock avec `side_effect` qui mute `log_data` — voir `tests/test_rss_sync_service.py::test_sync_result_is_json_serializable_after_mongo_insert`.
**Leçon générale** : tout service qui construit un dict, le passe à `insert_one()`, puis retourne ce même dict à un appelant HTTP doit soit copier avant l'insertion, soit ne jamais réutiliser l'objet post-insertion. Les mocks `MagicMock()` classiques ne reproduisent pas cette mutation par défaut — il faut un `side_effect` explicite pour l'attraper.

### Piège environnement dev : proxy Vite figé sur un ancien backend
Un ancien process backend orphelin (démarré la veille, jamais arrêté) tournait en parallèle du nouveau lancé par `start-dev.sh`. `vite.config.js` lit `.dev-ports.json` pour sa cible de proxy `/api` **une seule fois, au démarrage du process Vite** (pas à chaque requête) — donc plusieurs générations de process vite orphelins (3 dans ce cas) peuvent chacune pointer vers un backend différent. Symptôme : `curl` direct sur le backend répond `200`, mais le même appel via le frontend (`/api/...`) renvoie `404`, alors que `.dev-ports.json` contient pourtant le bon port. Un nouvel endpoint fraîchement ajouté semble alors "ne pas exister" côté frontend. **Fix appliqué en documentation** : `CLAUDE.md` section "Development Scripts" — toujours vérifier via `get-services-info.sh` qu'aucune ancienne instance ne tourne, et l'arrêter (jamais `kill -9` à l'aveugle) avant `start-dev.sh`.

## Architecture implémentée

### Nouveau service `src/back_office_lmelp/services/rss_sync_service.py`
`RssSyncService` orchestre : `fetch_feed_entries()` (feedparser, wrappé `asyncio.to_thread` car bibliothèque bloquante) → `filter_new_candidate_entries()` (dédup niveau 1 : date de publication > dernier épisode connu en base, + seuil durée `RSS_DUREE_MINI_MINUTES=15`) → `classify_episode_type()` (Azure OpenAI, PAS le modèle HuggingFace zero-shot `facebook/bart-large-mnli` utilisé par `lmelp` — trop lourd, remplacé par un prompt sur le client Azure OpenAI déjà configuré ailleurs dans le repo, pattern copié de `radiofrance_service.py`) → dédup niveau 2 (`find_episode_by_titre_and_date`) → `download_audio()` (aiohttp async, idempotent, chemin `<AUDIO_STORAGE_PATH>/<année>/<basename(url)>`) → insertion MongoDB → `send_ntfy_notification()` (générique via `NTFY_SERVER_URL`/`NTFY_TOPIC`, no-op si absent) → persistance d'un log dans la nouvelle collection `rss_download_logs`.

Valeur exacte du champ `type` : `"livres"` (avec le "s", confirmé par la donnée réelle en base) — jamais `"livre"`. Classification ambiguë → `"inconnu"` explicite (fail-safe : ne jamais télécharger un épisode ambigu par défaut).

Titre de notification ntfy.sh enrichi avec la date de l'épisode au format `dd/mm/yy` (ex: `"Nouvel épisode Le Masque et la Plume téléchargé — 06/09/26"`) — demande explicite de l'utilisateur en cours de test manuel, pour distinguer les notifications d'un coup d'œil sur mobile.

### Nouvelle collection MongoDB `rss_download_logs`
Un document par run complet (`started_at`, `finished_at`, `trigger`: `"manual"`|`"api"`, `status`, `feed_url`, `episodes[]` avec `outcome` par épisode: `downloaded`|`skipped_not_book`|`already_exists`|`skipped_too_short`|`error`, `notification_sent`, `error_message`). Nouvelles méthodes dans `mongodb_service.py`: `find_episode_by_titre_and_date`, `get_last_episode_date`, `insert_rss_download_log`, `get_rss_download_logs`, `get_rss_download_log_by_id`.

### Nouveaux endpoints (`src/back_office_lmelp/app.py`)
`POST /api/rss/sync` (body `{"trigger": "manual"|"api"}`, défaut `"api"` — donc un appel Automatisch/n8n sans body fonctionne), `GET /api/rss/logs`, `GET /api/rss/logs/{log_id}`.

### Frontend
Nouvelle vue `frontend/src/views/RssMonitoring.vue` (gabarit copié de `BabelioControl.vue`) avec bouton de déclenchement manuel, historique horodaté, détail par épisode en expansion inline (préfixé par la date `dd/mm/yy` de chaque épisode). Nouvelle route `/rss-monitoring`, nouvelle section Dashboard "RSS Masque Et La Plume" avec tuile "Monitoring Downloads" (emoji `📡`, pas d'asset SVG dédié).

### Configuration (`src/back_office_lmelp/settings.py`)
Nouvelles propriétés : `rss_masque_et_la_plume_url` (défaut `https://radiofrance-podcast.net/podcast09/rss_14007.xml`), `rss_duree_mini_minutes` (défaut 15), `audio_storage_path` (défaut `<cwd>/data/audios` en dev, `/app/audios` en prod Docker), `ntfy_server_url`/`ntfy_topic` (None si absent), `rss_debug_log`.

## Décisions produit validées avec l'utilisateur

- Scope inclut le téléchargement physique du fichier audio, pas seulement l'entrée MongoDB.
- Déclenchement double : bouton UI manuel ET endpoint API pour automatisation externe.
- Le montage du volume Docker `AUDIO_PATH` sur le service `backend` (actuellement monté uniquement sur le service `lmelp` dans `docker-lmelp/docker-compose.yml`) est HORS scope de ce repo → documenté comme issue externe.
- `episode_page_url` reste vide à l'insertion RSS (geste manuel existant conservé, cf. découverte ci-dessus).

## Issues externes créées

- `castorfou/docker-lmelp#64` : montage du volume audio sur le service `backend` + nouvelles variables d'env (`AUDIO_STORAGE_PATH`, `RSS_MASQUE_ET_LA_PLUME_URL`, `RSS_DUREE_MINI_MINUTES`, `NTFY_SERVER_URL`, `NTFY_TOPIC`) + nouvelle section dans `docs/user/migration-nas.md` documentant comment configurer une action Automatisch "HTTP Request" (Method POST, URL `http://<nas>:<port>/api/rss/sync`, header `Content-Type: application/json`, body `{"trigger": "api"}`) pour déclencher la synchronisation automatiquement.
- `castorfou/lmelp-mobile` : à créer — mise à jour de la doc "mise à jour épisode" pour mentionner l'alternative automatisée à l'étape manuelle "Rafraîchir Episodes".

## Tests manuels réels effectués (au-delà des tests automatisés)

Avec un vrai flux RSS, un vrai appel Azure OpenAI, un vrai téléchargement audio (~68 Mo), une vraie insertion MongoDB et un vrai envoi ntfy.sh (topic de production de l'utilisateur) :
- Bouton "Rafraîchir Episodes" côté UI → fonctionne, affiche le résumé du run.
- Appel `POST /api/rss/sync` en direct via `curl` (simulant Automatisch) → fonctionne, `trigger: "api"` bien distingué de `"manual"` dans l'historique.
- Classification LLM réelle : un épisode livres (`"livres"`) correctement téléchargé, un épisode cinéma (`"films"`) correctement ignoré (`skipped_not_book`) dans le même run.
- Notification ntfy.sh réelle reçue avec le bon titre (incluant la date après le fix) pour les deux cas (téléchargé / non retenu).
- Fichier audio réellement présent sur disque au format `<année>/<basename(url)>`, supprimé après validation (ne pas laisser de gros fichiers de test dans le repo).

## Fichiers critiques

- `src/back_office_lmelp/services/rss_sync_service.py` (nouveau, cœur de la logique)
- `src/back_office_lmelp/services/mongodb_service.py:299-357` (méthodes dédup + logs RSS)
- `src/back_office_lmelp/app.py` (bloc "RSS Masque Et La Plume sync endpoints", après le bloc Babelio control)
- `src/back_office_lmelp/models/episode.py` (champs `url`, `audio_rel_filename` ajoutés)
- `src/back_office_lmelp/settings.py` (config RSS/audio/ntfy)
- `frontend/src/views/RssMonitoring.vue`, `frontend/src/views/Dashboard.vue`, `frontend/src/router/index.js`
- `.env.example` (nouveau fichier, n'existait pas avant dans ce repo)
- `CLAUDE.md` (nouvelle section sur la vérification des process avant `start-dev.sh`)
