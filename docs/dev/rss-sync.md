# Synchronisation RSS Le Masque et la Plume (développeur)

Ce document décrit l'implémentation du service de synchronisation automatique du flux RSS de l'émission "Le Masque et la Plume" (France Inter).

## Vue d'ensemble

`RssSyncService` (`src/back_office_lmelp/services/rss_sync_service.py`) orchestre :

1. Téléchargement et parsing du flux RSS (`feedparser`, wrappé dans `asyncio.to_thread` car la bibliothèque est synchrone/bloquante).
2. Filtrage des entries candidates : dédup niveau 1 (date de publication postérieure au dernier épisode connu en base) + seuil de durée (`RSS_DUREE_MINI_MINUTES`, défaut 15 minutes).
3. Classification LLM (Azure OpenAI) du type d'épisode : `"livres"` | `"films"` | `"théâtre"` | `"inconnu"` (fail-safe si le client n'est pas configuré ou en cas d'ambiguïté — ne jamais télécharger un épisode ambigu par défaut).
4. Pour les épisodes `"livres"` uniquement : dédup niveau 2 (existence exacte titre+date) puis téléchargement du fichier audio (`aiohttp`, idempotent) et insertion MongoDB.
5. Notification ntfy.sh (optionnelle) en fin de traitement de chaque épisode : téléchargé ou détecté mais non retenu.
6. Persistance d'un document de trace dans la collection `rss_download_logs` pour chaque run complet.

## Déclenchement

Deux endpoints exposent la synchronisation :

- `POST /api/rss/sync` (body `{"trigger": "manual" | "api"}`, défaut `"api"`) — déclenche un run complet et retourne son résumé.
- `GET /api/rss/logs` et `GET /api/rss/logs/{log_id}` — consultent l'historique.

`trigger="manual"` correspond au bouton "🔄 Rafraîchir Episodes" de la page `/rss-monitoring`. `trigger="api"` correspond à un appel externe (ex: automatisation Automatisch/n8n déclenchée sur détection d'un nouvel épisode RSS) — voir la section correspondante dans le guide de déploiement `docker-lmelp`.

## Déduplication à deux niveaux

1. **Niveau 1 (filtrage RSS)** : `RssSyncService.filter_new_candidate_entries()` ne retient que les entries dont `entry.published` est postérieure à la date la plus récente entre `mongodb_service.get_last_episode_date()` (dernier épisode réellement inséré, consulté en temps réel dans `episodes`) et `mongodb_service.get_last_processed_episode_date()` (dernier épisode `"skipped_not_book"` déjà vu, via une agrégation sur `rss_download_logs`). Évite de retraiter tout le flux à chaque run.
2. **Niveau 2 (avant insertion)** : `mongodb_service.find_episode_by_titre_and_date()` vérifie l'existence exacte (titre, date) avant tout téléchargement/insertion.
3. **Niveau 3 (fichier audio)** : `download_audio()` vérifie que le fichier n'existe pas déjà sur disque avant de le télécharger (idempotence, même si un même épisode passait les deux niveaux précédents).

**Piège corrigé (détecté par test manuel)** : se baser uniquement sur `get_last_episode_date()` pour le niveau 1 est insuffisant, car cette méthode ne voit que les épisodes **réellement insérés** dans `episodes` — un épisode `"skipped_not_book"` (film, théâtre) n'y apparaît jamais. Sans `get_last_processed_episode_date()`, un tel épisode resterait indéfiniment un candidat re-classifié par le LLM et re-notifié via ntfy.sh à chaque run, tant qu'aucun nouvel épisode "livres" n'est inséré après lui dans le flux.

**Piège n°2 (effet de bord du fix précédent, détecté par test manuel)** : `get_last_processed_episode_date()` doit filtrer strictement sur `episodes.outcome == "skipped_not_book"` — **jamais** inclure les outcomes `"downloaded"`. Une première version incluait tous les outcomes, ce qui empêchait de retélécharger un épisode "livres" supprimé manuellement de `episodes` (test manuel, correction d'erreur) : `get_last_episode_date()` (temps réel sur `episodes`) le considère à nouveau absent, mais `get_last_processed_episode_date()` (historique figé sur `rss_download_logs`) se souvenait encore l'avoir "vu", bloquant tout retraitement. Seuls les épisodes jamais insérés (`"skipped_not_book"`) doivent rester bloqués indéfiniment ; un épisode inséré puis supprimé doit redevenir un candidat normal.

## Classification LLM

Contrairement au projet `lmelp` (frontoffice Streamlit, qui partage la même base MongoDB) qui utilise un modèle HuggingFace zero-shot local (`facebook/bart-large-mnli`), ce service réutilise le client Azure OpenAI déjà configuré ailleurs dans le repo (`AZURE_API_KEY`, `AZURE_ENDPOINT`, `AZURE_API_VERSION`, `AZURE_DEPLOYMENT_NAME`), sur le modèle exact de l'appel LLM de `radiofrance_service.py` (`asyncio.wait_for(asyncio.to_thread(...), timeout=30)`).

Si le client n'est pas configuré, `classify_episode_type()` retourne `"inconnu"` — l'épisode n'est ni téléchargé ni notifié comme "livres" par erreur.

## Structure des documents MongoDB

### Collection `episodes` (champs ajoutés, Issue #295)

Les champs `url` (URL audio source) et `audio_rel_filename` (chemin relatif `<année>/<basename(url)>`) existaient déjà dans certains documents de la collection (écrits historiquement par `lmelp`) mais n'étaient pas exposés par le modèle `Episode`. Ils sont maintenant lus et retournés par `Episode.to_dict()` — noms de champs réutilisés à l'identique, sans renommage.

`audio_rel_filename` est ensuite consommé par l'étape suivante de la chaîne de traitement (transcription automatisée PGX côté `lmelp`) — le format doit rester `<année>/<basename(url)>`, relatif à la racine du dossier audio, pour ne pas casser cette étape.

### Nouvelle collection `rss_download_logs`

Un document par run complet de synchronisation :

```python
{
    "started_at": datetime,
    "finished_at": datetime,
    "trigger": "manual" | "api",
    "status": "success" | "partial_error" | "error",
    "feed_url": str,
    "episodes": [
        {
            "titre": str,
            "date": datetime,
            "duree": int | None,
            "outcome": "downloaded" | "skipped_not_book" | "already_exists" | "skipped_too_short" | "error",
            "episode_id": str | None,
            "audio_downloaded": bool,
            "error_message": str | None,
        },
        ...
    ],
    "notification_sent": bool,
    "error_message": str | None,
}
```

## Piège pymongo : mutation de dict par `insert_one()`

**Bug réel corrigé** (non détecté par les tests mockés, uniquement lors d'un test manuel avec une vraie base MongoDB) : `pymongo.Collection.insert_one(doc)` **mute** le dict `doc` passé en argument en y injectant un `_id` (`ObjectId`). Si le même dict est ensuite retourné comme réponse HTTP (via FastAPI/Pydantic), la sérialisation JSON échoue avec `PydanticSerializationError: Unable to serialize unknown type: <class 'bson.objectid.ObjectId'>`.

`RssSyncService.sync()` passe donc une **copie défensive** (`dict(result)`) à `mongodb_service.insert_rss_download_log()`, jamais l'objet `result` retourné à l'appelant HTTP.

```python
# ❌ WRONG — mute result, qui est ensuite retourné à l'API
self.mongodb_service.insert_rss_download_log(result)
return result

# ✅ CORRECT — copie défensive avant l'insertion
self.mongodb_service.insert_rss_download_log(dict(result))
return result
```

Un test dédié (`tests/test_rss_sync_service.py::test_sync_result_is_json_serializable_after_mongo_insert`) reproduit fidèlement ce comportement pymongo via un mock avec `side_effect` qui mute l'argument reçu — un `MagicMock()` classique ne le fait pas par défaut, il faut le simuler explicitement.

## Configuration

Voir `docs/dev/environment-variables.md` pour le détail des variables `RSS_MASQUE_ET_LA_PLUME_URL`, `RSS_DUREE_MINI_MINUTES`, `AUDIO_STORAGE_PATH`, `NTFY_SERVER_URL`, `NTFY_TOPIC`, `RSS_DEBUG_LOG`.

## Voir aussi

- `src/back_office_lmelp/services/rss_sync_service.py`
- `src/back_office_lmelp/services/mongodb_service.py` (méthodes de dédup et de gestion des logs RSS)
- `frontend/src/views/RssMonitoring.vue`
- `docs/user/rss-monitoring.md` (documentation utilisateur)
