# Transcription PGX (développeur)

Ce document décrit l'implémentation du pipeline de transcription automatisée via la
station GPU dédiée PGX (Issue #302, portage depuis `castorfou/lmelp`, `nbs/pgx.py`).

## Vue d'ensemble

Deux modules collaborent :

- **`src/back_office_lmelp/services/pgx_service.py`** — fonctions I/O pures (SSH/SCP),
  sans état ni dépendance MongoDB. Portage quasi 1:1 du module `pgx.py` de lmelp, adapté
  en asyncio (`asyncio.create_subprocess_exec` au lieu de `subprocess.run`,
  `asyncio.open_connection` au lieu de `socket` bloquant) — voir la section
  "Subprocess Calls to External System Tools" dans `CLAUDE.md` pour la justification.
- **`src/back_office_lmelp/utils/pgx_transcription_runner.py`** — singleton
  `PgxTranscriptionRunner` qui orchestre le traitement de la file d'épisodes et
  l'écriture MongoDB, calqué sur `MigrationRunner`
  (`src/back_office_lmelp/utils/migration_runner.py`, pattern
  singleton + `asyncio.create_task` + polling GET, déjà utilisé pour la migration
  Babelio).

## Pipeline par épisode

Pour chaque épisode de la file (traités **séquentiellement**, une seule machine PGX) :

1. **Cache local** : si `<audio>.txt` existe déjà à côté du fichier audio local
   (`settings.audio_storage_path`), lire son contenu directement — aucun appel réseau.
   Reproduit `set_transcription()` de lmelp.
2. Sinon, pipeline réseau complet :
   - Vérification de joignabilité PGX (**lazy** : une seule fois pour toute la file, au
     premier épisode qui en a réellement besoin — pas en amont de la boucle, sinon un
     run entièrement servi par le cache local échouerait inutilement si PGX est
     injoignable).
   - Envoi du fichier audio par `scp` (`send_audio_to_pgx`, qui crée d'abord le
     répertoire distant `<remote_audio_root>/<année>/` via `ssh mkdir -p` — `scp` ne
     crée pas les répertoires manquants).
   - Attente de la transcription générée par le watcher PGX
     (`wait_for_pgx_transcription`, poll SSH `test -f`, timeout
     `PGX_TRANSCRIPTION_TIMEOUT_S`).
   - Rapatriement du fichier de transcription par `scp`
     (`fetch_transcription_from_pgx`), écrit en local à `<audio>.txt` (alimente le
     cache pour un run futur).
3. Écriture du champ `episodes.transcription` en base MongoDB, via
   `mongodb_service.episodes_collection` — passe donc par le `MongoClient` de ce
   backend, observé nativement par `DashboardStatsInvalidationListener` (voir
   `docs/dev/dashboard-stats-cache.md`).

Un échec (`PgxError`) sur un épisode n'interrompt **pas** le traitement des suivants de
la file — sauf l'échec de joignabilité initial (avant tout épisode traité), qui arrête
toute la file immédiatement (un nouvel essai réseau par épisode ne résoudrait rien tant
que PGX reste éteinte).

## Diagnostics

`run_pgx_diagnostics()` (`pgx_service.py`) exécute une checklist en cascade — chaque
étape court-circuite les suivantes si elle échoue :

1. **Joignabilité** (`wait_for_pgx_reachable`, poll TCP port 22).
2. **Authentification SSH** (`_check_ssh_auth`, connexion SSH réelle testée, pas
   seulement le port ouvert — le message d'échec inclut le `stderr` réel de la tentative,
   jamais un message générique statique, pour distinguer permissions de clé, clé absente
   d'`authorized_keys`, etc.).
3. **Répertoire audio distant** existe.
4. **Répertoire transcriptions distant** existe.

`get_pgx_config_missing_vars()` doit être vérifié **avant** tout appel à
`run_pgx_diagnostics()` — `wait_for_pgx_reachable()` lève sinon une erreur non catchée
si `host` est `None`. C'est ce que fait l'endpoint `GET /api/pgx/diagnostics`.

## Endpoints

- `GET /api/pgx/diagnostics` — checklist ci-dessus. Retourne `{"diagnostics": [],
  "missing_vars": [...]}` sans appel réseau si la config est incomplète.
- `GET /api/pgx/episodes-without-transcription` — liste (id/titre/date) des épisodes non
  masqués sans transcription, via `stats_service.get_episodes_without_transcription()`
  (même filtre Mongo que le compteur caché `episodes_without_transcription_count`, mais
  `find()` au lieu de `count_documents()`).
- `POST /api/pgx/transcription/start` — sans paramètre, traite **toute** la file
  courante des épisodes en attente (décision produit : une action déclenche tout le
  backlog plutôt qu'un sélecteur par épisode). Retourne `{"status": "already_running" |
  "nothing_to_do" | "started", "episode_count": N}`.
- `GET /api/pgx/transcription/progress` — statut consommé par polling (2s côté
  frontend), même pattern que `GET /api/babelio-migration/progress`.

Pas d'endpoint `stop` (décision explicite, cohérent avec lmelp qui n'en avait pas non
plus — un pipeline SSH en cours n'est pas trivialement interruptible proprement).

## Logs — en mémoire uniquement, pas de persistance MongoDB

Contrairement à `rss_download_logs` (un document par run RSS, historique consultable
même après redémarrage), les logs PGX (`PgxTranscriptionRunner.logs`) vivent uniquement
en mémoire dans le singleton : perdus au redémarrage du backend, et **réinitialisés à
chaque nouveau `start_transcription()`** (`self.logs = []`). Décision assumée : pas
d'accumulation indéfinie d'un historique de transcriptions, contrairement à RSS où le
faible volume (0-1 run/semaine) rend la persistance sans risque.

Chaque ligne est horodatée (`_log()`, préfixe `dd/mm/yy HH:MM:SS`) — date incluse, pas
seulement l'heure, un run de plusieurs épisodes pouvant s'étaler sur des dizaines de
minutes voire chevaucher minuit.

## Piège réel rencontré : `datetime` non JSON-sérialisable

**Bug trouvé lors du test en conditions réelles** (pas par les tests mockés, dont les
mocks utilisaient initialement une string pour `date` au lieu d'un vrai `datetime`) :
`stats_service.get_episodes_without_transcription()` retournait le champ `date` tel quel
(objet `datetime` MongoDB) → `JSONResponse` de FastAPI levait `"Object of type datetime
is not JSON serializable"` sur `GET /api/pgx/episodes-without-transcription`. Fix :
conversion `.isoformat()` explicite si `isinstance(date_value, datetime)`.

```python
# ❌ WRONG — passthrough du datetime MongoDB, non sérialisable
"date": episode.get("date"),

# ✅ CORRECT — conversion ISO explicite
date_value = episode.get("date")
"date": date_value.isoformat() if isinstance(date_value, datetime) else date_value,
```

Cf. la règle CLAUDE.md "MongoDB DateTime vs String Handling" — ici, le piège se
cachait dans un mock de test qui contredisait cette règle plutôt que dans le code de
production lui-même, d'où sa découverte tardive.

## Cache dashboard

`episodes_without_transcription_count` fait partie du payload caché standard
(`StatsService.get_cache_statistics()`, consommé par `GET /api/dashboard/stats`). Voir
`docs/dev/dashboard-stats-cache.md` pour le mécanisme d'invalidation automatique — plus
besoin d'endpoint dédié non caché ni de logique de comparaison de compteur, contrairement
à l'implémentation initiale de la tuile (Issue #298), car l'écriture du champ
`transcription` passe désormais nativement par le `MongoClient` de ce backend.

## Configuration

Voir `docs/dev/environment-variables.md` pour le détail des variables `PGX_HOST`,
`PGX_USER`, `PGX_SSH_KEY_PATH`, `PGX_REMOTE_AUDIO_ROOT`,
`PGX_REMOTE_TRANSCRIPTION_ROOT`, `PGX_TRANSCRIPTION_TIMEOUT_S`, `PGX_POLL_INTERVAL_S`.

## Tests

Tous les tests mockent `asyncio.create_subprocess_exec`/`asyncio.open_connection` —
aucun accès réseau réel :

- `tests/test_pgx_service.py` — fonctions pures et pipeline SSH/SCP mockées.
- `tests/test_pgx_transcription_runner.py` — orchestration de la file (singleton,
  `already_running`/`nothing_to_do`, cascade d'échecs, cache local).
- `tests/test_pgx_endpoints.py` — endpoints FastAPI (mocks du service/runner).

Le pipeline complet a aussi été validé en conditions réelles (vraie station PGX, base
MongoDB locale de test — voir `docs/dev/blocage_ip.md` pour le mécanisme de base locale
séparée de la prod), sur 2 épisodes réels : envoi scp, attente (~3-4 min chacun),
rapatriement, écriture Mongo, puis re-test confirmant le cache local (traitement
quasi instantané sans appel réseau).

## Voir aussi

- `src/back_office_lmelp/services/pgx_service.py`
- `src/back_office_lmelp/utils/pgx_transcription_runner.py`
- `src/back_office_lmelp/utils/migration_runner.py` (pattern singleton + polling source)
- `frontend/src/views/PgxTranscription.vue` (page dédiée `/transcription-pgx`)
- `docs/user/transcription-pgx.md` (documentation utilisateur)
- `docs/dev/rss-sync.md` — `audio_rel_filename` (format `<année>/<basename(url)>`,
  écrit par `RssSyncService.download_audio()`) est le champ consommé par ce pipeline
  pour localiser le fichier audio local de chaque épisode.
