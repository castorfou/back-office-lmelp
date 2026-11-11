# Ajout d'une émission hors flux RSS (développeur)

Ce document décrit l'ajout d'une émission à partir de sa page radiofrance.fr, pour les
émissions trop anciennes pour le flux RSS (voir `docs/dev/rss-sync.md`).

## Vue d'ensemble

`ManualEpisodeService.add_from_radiofrance_page(url)`
(`src/back_office_lmelp/services/manual_episode_service.py`) enchaîne :

1. **Contrôle de l'URL** : `https://www.radiofrance.fr/franceinter/podcasts/le-masque-et-la-plume/<page>`.
2. **Lecture de la page** (`fetch_page_html`, en-têtes de `RadioFranceService`).
3. **Lecture du JSON-LD** `RadioEpisode` (`parse_radiofrance_episode_page`) :

    | Champ JSON-LD | Champ `episodes` |
    |---------------|------------------|
    | `name` | `titre` |
    | `description` | `description` |
    | `dateCreated` (gardée telle quelle, UTC) | `date` |
    | `mainEntity.duration` (`P0Y0M0DT0H46M49S`) | `duree` (secondes) |
    | `mainEntity.contentUrl` | `url` (audio complet) |

4. **Contrôles avant téléchargement** :
    - durée ≥ `MIN_FULL_EPISODE_SECONDS` (1800 s), sinon c'est une séquence ;
    - aucun épisode le même jour UTC (`MongoDBService.find_episode_on_same_day`), quel
      que soit son titre ou son heure.
5. **Téléchargement** via `RssSyncService.download_audio` (même stockage que le RSS :
   `<AUDIO_STORAGE_PATH>/<année>/<basename(url)>`).
6. **Insertion** dans `episodes`, uniquement une fois l'audio complet sur disque.
7. **Suite identique au parcours RSS + Automatisch** :
    - notification ntfy (`utils/ntfy.py`, préfixe « Ajout manuel ») ;
    - `pgx_transcription_runner.start_transcription(trigger="api")`, avec réessai horaire
      si PGX est injoignable (voir `docs/dev/pgx-transcription.md`). Un échec de ce
      lancement n'annule pas l'ajout : `transcription_status` vaut alors `"error"`.

Aucun document n'est écrit dans `rss_download_logs` : cette collection décrit les runs
RSS et alimente la déduplication du flux.

## Document inséré

```python
{
    "titre": str,
    "date": datetime,          # dateCreated de la page, UTC
    "description": str,
    "url": str,                # mainEntity.contentUrl
    "audio_rel_filename": str, # "<année>/<basename(url)>"
    "transcription": None,
    "type": "livres",          # pas de classification LLM : la page est choisie à la main
    "duree": int,
    "masked": False,
    "episode_page_url": str,
    "source": "radiofrance_page",
}
```

`source` distingue ces épisodes de ceux du flux RSS, qui n'ont pas ce champ.

## Endpoint

`POST /api/episodes/from-radiofrance-page`, body `{"url": "<page radiofrance.fr>"}`.
Synchrone : la réponse arrive une fois l'audio téléchargé et l'épisode inséré.

```json
{
  "episode_id": "…",
  "titre": "…",
  "date": "2024-07-21",
  "duree": 2809,
  "episode_page_url": "…",
  "audio_rel_filename": "2024/14007-21.07.2024-ITEMA_23808923-2024F4007S0203-27.m4a",
  "transcription_status": "started"
}
```

| Statut | Cause (`ManualEpisodeError.status_code`) |
|--------|-------------------------------------------|
| 400 | URL hors des pages Le Masque et la Plume, ou page sans `RadioEpisode` exploitable |
| 409 | Épisode existant le même jour |
| 422 | Audio de moins de 1800 s (séquence) |
| 502 | Page ou audio inaccessible |

En production, nginx coupe `/api/` à 120 s. Une émission complète (~70 Mo) se télécharge
bien en dessous. En cas de `504`, relancer suffit : l'audio présent sur disque est
réutilisé et le contrôle de doublon bloque une seconde insertion.

## Téléchargement de l'audio

`RssSyncService.download_audio` :

- vérifie le statut HTTP (`raise_for_status=True`) ;
- lit par morceaux de 1 Mo (`iter_chunked`), timeout total de 600 s ;
- écrit dans `<fichier>.part`, renommé (`os.replace`) une fois complet ; le `.part` est
  supprimé en cas d'échec. Un fichier final présent est donc toujours complet, ce qui
  rend sûr le saut des fichiers déjà téléchargés.

## Séquence ou émission

Sur radiofrance.fr, une émission complète dure ~47 min ; une séquence consacrée à un livre
dure ~8 à 10 min et a sa propre URL audio `ITEMA_…`, très proche de celle de l'émission.
Le `contentUrl` du JSON-LD de la page de l'émission est la seule source fiable, et la
durée minimale de 1800 s écarte une page de séquence collée par erreur.

## Frontend

- `frontend/src/views/AjoutEmission.vue` (route `/ajout-emission`)
- Tuile dans la section *Podcast Masque Et La Plume* de `frontend/src/views/Dashboard.vue`

Le résultat ne propose pas de lien vers `/emissions/<date>` : une émission (collection
`emissions`) n'existe qu'après la génération des avis critiques
(`auto_convert_episodes_to_emissions`).

## Tests

- `tests/test_manual_episode_service.py` : fixture réelle
  `tests/fixtures/radiofrance/episode_2024_07_21_full_episode.html` (JSON-LD capturé sur
  radiofrance.fr) ; `fetch_page_html` testé contre un serveur HTTP local.
- `tests/test_manual_episode_endpoint.py` : codes HTTP de l'endpoint.
- `tests/test_rss_sync_service.py::TestDownloadAudio` : téléchargement contre un serveur
  local (`aiohttp.test_utils.TestServer`) : 404, connexion coupée en cours de route,
  nouvel essai.
- `frontend/tests/AjoutEmission.test.js`, `frontend/tests/unit/ajoutEmissionRoute.test.js`.

## Voir aussi

- `docs/user/ajout-emission.md` (documentation utilisateur)
- `docs/dev/rss-sync.md`
- `docs/dev/pgx-transcription.md`
