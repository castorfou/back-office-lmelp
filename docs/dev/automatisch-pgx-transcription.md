# Automatiser la transcription PGX via Automatisch

!!! note "Contenu à dupliquer dans `docker-lmelp`"
    Cette page documente la configuration Automatisch côté `back-office-lmelp`. Le
    guide de déploiement NAS (`docker-lmelp`, page `migration-nas.md`) présente déjà
    l'étape équivalente pour la synchronisation RSS ("Étape 10 : Automatiser la
    synchronisation RSS via Automatisch") — cette page suit la même structure et est
    destinée à être dupliquée à la suite de cette étape dans ce même guide.

Sur le modèle de la synchronisation RSS, la transcription PGX peut être déclenchée
automatiquement par Automatisch via l'endpoint `POST /api/pgx/transcription/start`.
Contrairement à `/api/rss/sync` (synchrone, faible volume), cet endpoint est
**fire-and-forget** : Automatisch appelle l'endpoint **une seule fois** (à sa
fréquence propre, par exemple une fois par jour), et le backend prend en charge
tout le reste — y compris un **retry automatique toutes les heures pendant 24h**
si PGX est éteinte au moment de l'appel (Issue #309). Pas besoin de programmer un
cron répété côté Automatisch.

## Configuration de l'étape Automatisch

Ajout d'une étape "HTTP Request" dans le workflow :

| Champ | Valeur |
|-------|--------|
| App | `HTTP Request` |
| Event | `Custom request` |
| Method | `POST` |
| URL | `http://192.168.50.207:8000/api/pgx/transcription/start` |
| Headers | `Content-Type: application/json` |
| Data (raw JSON) | `{"trigger": "api"}` |

!!! warning "Ne pas omettre `trigger: api`"
    Sans ce paramètre (ou avec `"trigger": "manual"`), le comportement reste celui
    du bouton UI : échec immédiat et définitif si PGX est injoignable, sans retry.

## Réponse attendue

Réponse immédiate (l'endpoint ne bloque jamais jusqu'à la fin du traitement, qui
peut durer de quelques minutes à plusieurs heures selon le nombre d'épisodes et la
disponibilité de PGX) :

```json
{"status": "started", "episode_count": 2}
```

Autres réponses possibles :

- `{"status": "nothing_to_do"}` — aucun épisode en attente de transcription,
  normal si tout est déjà à jour.
- `{"status": "already_running"}` — un cycle est déjà en cours (traitement actif,
  ou retry en attente d'une prochaine tentative horaire) — évite les doublons si
  Automatisch se redéclenche pendant qu'un cycle précédent tourne encore.

## Suivre le résultat

Le déclenchement étant asynchrone, consultez l'historique pour connaître l'issue
réelle du cycle :

```bash
curl http://192.168.50.207:8000/api/pgx/logs | jq
```

Chaque document représente un cycle complet (du déclenchement au succès ou à
l'abandon) :

```json
{
  "_id": "...",
  "started_at": "...",
  "finished_at": "...",
  "trigger": "api",
  "status": "success",
  "episode_ids": ["..."],
  "episodes": [
    {"episode_id": "...", "titre": "...", "success": true, "error": null}
  ],
  "retry_attempts": [],
  "notification_sent": true,
  "error_message": null
}
```

`status` peut valoir :

- `success` — tous les épisodes traités avec succès.
- `partial_error` — au moins un épisode a échoué, cycle terminé quand même.
- `error` — erreur inattendue ayant interrompu tout le pipeline.
- `pgx_unreachable_abandoned` — PGX est restée injoignable au-delà du délai
  maximal de retry (24h par défaut) ; `episodes` est vide dans ce cas, mais
  `episode_ids` conserve la liste des épisodes qui attendaient d'être traités, et
  `retry_attempts` détaille chaque tentative horaire.

L'historique complet (y compris les cycles déclenchés manuellement depuis
`/transcription-pgx`) est aussi consultable dans le back-office, section
"📋 Historique des transcriptions" de cette page.

## Notifications ntfy.sh

Si `NTFY_SERVER_URL`/`NTFY_TOPIC` sont configurés (mêmes variables que pour RSS), des
notifications sont envoyées automatiquement, sans action supplémentaire côté
Automatisch — même logique que la synchronisation RSS : **une notification par
épisode**, pas de résumé groupé en fin de cycle :

- **Par épisode transcrit avec succès** — "Transcription PGX terminée — {date}" /
  titre de l'épisode.
- **Par épisode en échec** (ex: timeout scp) — "Échec transcription PGX — {date}" /
  titre + erreur.
- **Dès le premier échec de joignabilité** déclenchant le retry — une seule fois,
  pour savoir qu'il faut allumer PGX, sans attendre 24h en silence.

Aucune notification n'est envoyée à chaque tentative de retry individuelle
au-delà de la première (pas de bruit répété toutes les heures), ni de synthèse
groupée en fin de cycle.

## À retenir

- Cette étape Automatisch peut remplacer ou compléter le bouton
  "▶️ Lancer la transcription" du back-office `/transcription-pgx`.
- Le retry (jusqu'à 24 tentatives par défaut, une par heure) est entièrement géré
  côté backend — Automatisch n'a pas besoin de relancer l'appel tant que le cycle
  précédent n'est pas terminé.
- Les délais de retry sont configurables via `PGX_TRANSCRIPTION_RETRY_INTERVAL_HOURS`
  (défaut `1`) et `PGX_TRANSCRIPTION_RETRY_MAX_HOURS` (défaut `24`) — voir
  `docs/dev/environment-variables.md`.
- Un appel Automatisch pendant qu'un cycle est déjà en cours (traitement actif ou
  retry en attente) renvoie simplement `{"status": "already_running"}` — sans
  effet indésirable, sans doublon.

## Voir aussi

- `docs/dev/pgx-transcription.md` — architecture complète du pipeline PGX.
- `docs/user/transcription-pgx.md` — documentation utilisateur (page
  `/transcription-pgx`, historique, retry).
- `docs/dev/rss-sync.md` — pattern `trigger: "manual" | "api"` d'origine (Issue #295).
