# Issue #402 — Bouton de transcription PGX bloqué pendant l'attente de PGX

## Problème
Sur la page Transcription PGX, le bouton « ▶️ Lancer la transcription des épisodes en attente »
restait désactivé (curseur sens interdit) alors que les 4 diagnostics PGX étaient au vert.

Cause : un cycle déclenché par Automatisch (`trigger="api"`) n'avait pas trouvé PGX et
attendait 1 h (`pgx_transcription_retry_interval_hours`) dans `_wait_for_reachable_with_retry()`.
Pendant toute cette attente `is_running` reste `True` (garde anti-chevauchement voulue,
Issue #309), donc le bouton (`disabled` si `is_running`) restait bloqué même après le retour
de PGX. Les diagnostics (`GET /api/pgx/diagnostics`) appellent la même `locate_pgx()` que le
runner : la différence venait seulement du moment (PGX rallumée après la tentative du runner).

## Solution (choix utilisateur : « Réessayer tout de suite »)

### Backend — `src/back_office_lmelp/utils/pgx_transcription_runner.py`
- `self._retry_now_event = asyncio.Event()` dans `_initialize()`.
- `_wait_for_next_attempt(seconds)` remplace l'`asyncio.sleep()` de la boucle de retry :
  `clear()` de l'événement, puis course `asyncio.sleep(seconds)` / `event.wait()` via
  `asyncio.wait(..., FIRST_COMPLETED)`, tâches annulées dans un `finally`. `asyncio.sleep`
  reste appelé : les tests existants qui le patchent restent valides.
- `request_retry_now()` : `{"status": "retrying"}` + `event.set()` si `retry_pending`, sinon
  `{"status": "no_pending_retry"}`. Si PGX reste introuvable, l'attente horaire reprend avec
  le même plafond (`retry_deadline` inchangé).
- **Demande ajoutée pendant l'issue** : `_append_new_pending_episodes()` est appelée en fin de
  chaque itération de la boucle `for index, episode_id in enumerate(self.episode_ids)`. Elle
  relit `stats_service.get_episodes_without_transcription()` et ajoute les ids absents de
  `self.episode_ids` ; l'itérateur de liste Python voit les ajouts en fin de liste. Un épisode
  déjà tenté (même en échec) n'est jamais rajouté → pas de boucle infinie. Exception attrapée
  et loggée. Log : « N épisode(s) ajouté(s) au cycle en cours ».

### API — `src/back_office_lmelp/app.py`
- `POST /api/pgx/transcription/retry-now` → `request_retry_now()`. **`async def` malgré
  l'absence d'`await`** : un endpoint `def` tourne dans le threadpool, et `asyncio.Event.set()`
  n'est pas thread-safe (il doit être appelé depuis la boucle d'événements). Exception assumée
  à la règle « pas d'await → def » de CLAUDE.md.
- Nouvel endpoint plutôt que modifier `/start` : le contrat Automatisch ne change pas.

### Frontend — `frontend/src/views/PgxTranscription.vue`
- Computed `startButtonDisabled` : `!pgxReady` → désactivé ; cycle en cours → actif seulement
  si `retry_pending` ; sinon désactivé sans épisode.
- Libellé « 🔁 Réessayer maintenant » quand `retry_pending`.
- `startPgxTranscription()` délègue à `retryPgxNow()` (POST retry-now + polling) si `retry_pending`.
- `checkPgxProgress()` démarre le polling dès que `is_running` est vrai : une page ouverte
  pendant un cycle se met à jour seule (avant : figée jusqu'au rechargement).

## Tests
- `tests/test_pgx_transcription_runner.py` :
  - fixture autouse `no_new_pending_episodes` qui patche `stats_service` du runner (sinon
    `_run()` interrogerait la vraie base en fin d'épisode) ; un test la repatche pour simuler
    un épisode arrivé.
  - `TestRetryNow` : vrai `asyncio.sleep` d'1 h non mocké, seul `request_retry_now()` peut
    débloquer → `asyncio.wait_for(task, timeout=2)`.
  - `TestEpisodesAddedDuringCycle` : épisode ajouté traité dans le même cycle, échec non retenté,
    erreur de relecture sans effet sur le cycle.
- `tests/test_pgx_endpoints.py` : `TestRetryNowPgxTranscription`.
- `frontend/src/views/__tests__/PgxTranscription.spec.js` : nouveau describe Issue #402.
  **Piège** : quand `is_running` est vrai au montage, le polling (`setInterval`) démarre ;
  `vi.runAllTimersAsync()` ne termine alors plus → utiliser `vi.advanceTimersByTimeAsync(0)`
  et `wrapper.unmount()` (test « bandeau retry » existant adapté).

## Vérification
- Playwright avec interception `page.route('**/api/pgx/...')` pour simuler `retry_pending`
  (PGX injoignable depuis le devcontainer) : bouton actif, `cursor: pointer`, clic → 1 appel
  `retry-now`. Route de la page : `/transcription-pgx`.
- Test réel prévu en prod par l'utilisateur (plusieurs émissions à transcrire).
