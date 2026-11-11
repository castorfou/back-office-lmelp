# Issue #334 — Ajouter une émission absente du flux RSS depuis sa page radiofrance.fr

## Problème

L'émission du 21/07/2024 manquait dans lmelp (signalée par lmelp-pap). Le flux RSS
France Inter (`rss_14007.xml`) ne garde que ~52 épisodes récents, et
`RssSyncService.sync()` ignore tout ce qui précède le dernier épisode connu :
aucun chemin de code ne pouvait créer une émission ancienne.

## Piège découvert : l'URL audio de l'issue était une séquence

- L'URL donnée par l'issue (`14007-22.07.2024-ITEMA_23810148-…S0204-27.m4a`) dure
  **7 min 37 s** : ses tags MP4 la titrent « "Ni de lait, ni de laine"… Emmanuelle
  Salasc ». C'est une séquence sur un livre, pas l'émission.
- L'émission complète est le `contentUrl` du JSON-LD `RadioEpisode.mainEntity` de la
  page radiofrance.fr : `14007-21.07.2024-ITEMA_23808923-…S0203-27.m4a`, 46 min 49 s,
  68 Mo (durée INA). Signalé en commentaire sur l'issue (pour lmelp-pap).
- Leçon : une URL `ITEMA_…` n'est pas forcément l'émission ; le JSON-LD de la page
  fait foi, et la durée sert de garde-fou (≥ 1800 s).

## Solution (décidée en session « grilling »)

Page **Ajouter une émission** (`/ajout-emission`, ➕), rubrique du tableau de bord
*Podcast Masque Et La Plume*, entre *Monitoring Downloads* et *Transcriptions PGX*.

### Backend

- `src/back_office_lmelp/services/manual_episode_service.py` (nouveau) :
  - `ManualEpisodeError(message, status_code)` : 400 URL invalide, 409 doublon,
    422 séquence trop courte, 502 page/audio inaccessible.
  - `parse_radiofrance_episode_page(html)` : lit `RadioEpisode` (`name`,
    `description`, `dateCreated` brut, `mainEntity.duration`, `mainEntity.contentUrl`).
    Réutilise `radiofrance_service._parse_iso_duration`.
  - `add_from_radiofrance_page(url)` : URL `https://www.radiofrance.fr/franceinter/podcasts/le-masque-et-la-plume/…`
    → page → durée ≥ 1800 s → pas d'épisode le même jour UTC → `download_audio` →
    `insert_episode` → notification ntfy (préfixe « Ajout manuel ») →
    `pgx_transcription_runner.start_transcription(trigger="api")`. Un échec de
    lancement de transcription n'annule pas l'ajout (`transcription_status: "error"`).
  - Document : `type: "livres"`, `transcription: None`, `masked: False`,
    `episode_page_url`, `source: "radiofrance_page"`. Rien dans `rss_download_logs`.
- `POST /api/episodes/from-radiofrance-page` dans `src/back_office_lmelp/app.py`,
  synchrone ; erreur métier détectée par nom de classe (`type(e).__name__`, cf.
  CLAUDE.md sur les imports `src.` doublés).
- `MongoDBService.find_episode_on_same_day(date)` : plage `[jour 00:00 UTC, +1 j)`,
  car les dates coexistent en minuit (anciens épisodes) et heure de publication (RSS).
- `RssSyncService.download_audio` (partagé avec le RSS) : `raise_for_status=True`
  (avant, une page 404 aurait été enregistrée comme audio), streaming `iter_chunked`
  1 Mo, timeout total 600 s, écriture dans `<fichier>.part` puis `os.replace` (un
  fichier tronqué n'est jamais pris pour « déjà présent »).
- `utils/ntfy.py` : paramètre `prefix` (défaut « PGX », inchangé pour PGX).

### Frontend

- `frontend/src/views/AjoutEmission.vue` : champ URL + bouton ; résultat (titre, date,
  durée, statut de transcription) ; liens *Suivre la transcription* et *Génération
  Avis Critiques*. **Pas de lien `/emissions`** : une « émission » (collection
  `emissions`) n'est créée par `auto_convert_episodes_to_emissions` qu'après la
  génération des avis critiques ; la route attend en plus `AAAAMMJJ`.
- Carte dans `frontend/src/views/Dashboard.vue`, route dans `frontend/src/router/index.js`.

## Intégration au processus existant

Le processus de traitement d'un nouvel épisode est décrit dans lmelp-mobile
(`docs/user/mise_a_jour_episode.md`) : Automatisch → `/api/rss/sync` → ntfy →
`/api/pgx/transcription/start` (trigger api) → suite manuelle (Génération Avis
Critiques, Livres et Auteurs, …, Émissions). La page remplace l'étape RSS ; tout le
reste est identique. Issue de doc ouverte :
[castorfou/lmelp-mobile#175](https://github.com/castorfou/lmelp-mobile/issues/175).

## Tests

- Fixture réelle `tests/fixtures/radiofrance/episode_2024_07_21_full_episode.html`
  (JSON-LD capturé ; le titre réel contient une espace insécable avant « ? »).
- `tests/test_manual_episode_service.py`, `tests/test_manual_episode_endpoint.py`.
- `download_audio`, `fetch_page_html` et le préfixe ntfy testés contre un **vrai
  serveur HTTP local** (`aiohttp.test_utils.TestServer`) : 404, connexion coupée en
  cours de route (`request.transport.close()` après un `StreamResponse` partiel),
  streaming. Un mock de `response.read()` ne voyait aucun de ces cas.
- Frontend : `frontend/tests/AjoutEmission.test.js` ; la route est testée à part
  (`frontend/tests/unit/ajoutEmissionRoute.test.js`) car importer le routeur charge
  `services/api.js` (`axios.interceptors`), incompatible avec `vi.mock('axios')`.

## Pièges de session

- Le backend de `start-dev.sh` ne recharge pas le code : relancer après modification
  backend avant un test manuel (`check-backend-freshness.sh`).
- `git add -N .` marque aussi `.playwright-mcp/` et `.dev-ports.json` : cibler les
  fichiers, ou annuler avec `git reset -- <chemin>`.
- En dev, `.env` configure ntfy **et** PGX : un ajout réel notifie le téléphone et lance
  PGX sur tous les épisodes non transcrits de la base locale.
