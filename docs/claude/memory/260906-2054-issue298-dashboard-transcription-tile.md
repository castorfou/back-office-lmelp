# Issue #298 : tuile "Épisodes sans transcription" + lien RSS monitoring

## Contexte

Depuis #295, des fonctions de lmelp (l'appli Streamlit historique) sont progressivement déportées vers back-office-lmelp. Deux changements demandés sur le dashboard :

1. La tuile "Dernière mise à jour" pointait vers la homepage lmelp externe → doit pointer vers la page interne `/rss-monitoring`.
2. Ajouter une tuile "Épisodes sans transcription", cliquable vers lmelp (racine), car c'est encore là que se lance la transcription pgx.

## Vérification de la logique métier dans lmelp

Le repo `castorfou/lmelp` a été cloné temporairement (`gh repo clone`, supprimé après lecture) pour lire l'implémentation exacte de la tuile homepage "# missing transcriptions" (`ui/lmelp.py:184-191`, `Episodes.get_missing_transcriptions()` dans `nbs/mongo_episode.py:1149-1153`). Elle filtre `transcription` vide/null, combiné par défaut avec l'exclusion des épisodes masqués (`include_masked=False`). Confirmé sur données réelles (MCP MongoDB) : 4 épisodes avaient `transcription: null`, dont 3 masqués et 1 non masqué.

## Implémentation backend

`src/back_office_lmelp/services/stats_service.py` : nouvelle méthode `_count_episodes_without_transcription()` (même pattern que `_count_episodes_without_avis_critiques`, comptage direct `count_documents` sans agrégation nécessaire).

**Décision clé sur le cache** : contrairement aux autres statistiques du dashboard (agrégées dans `/api/dashboard/stats`, mises en cache 5 min via `dashboard_stats_cache_service`), cette métrique est exposée par un **endpoint dédié non caché** : `GET /api/episodes/without-transcription/count` (`app.py`, juste après `/api/dashboard/stats/cache/invalidate`). Raison : la transcription se lance depuis lmelp, une appli externe dont ce back-office ne peut observer aucune écriture pour invalider un cache automatiquement — contrairement au `DashboardStatsInvalidationListener` (pymongo `CommandListener`) qui fonctionne parce que les écritures passent par ce même MongoClient. Un cache figé pendant 5 min sur cette tuile spécifique aurait été trompeur juste après le lancement d'une transcription dans lmelp.

**Effet de bord découvert et corrigé** : un épisode sans transcription ne peut pas encore avoir d'avis critiques (générés à partir de la transcription) — il était donc compté à la fois dans "sans transcription" ET "sans avis critiques", gonflant artificiellement cette dernière métrique avec un épisode qui n'a rien à "traiter" tant que la transcription n'existe pas. Fix : `_count_episodes_without_avis_critiques()` filtre désormais aussi `transcription: {"$nin": [None, ""]}` sur le comptage des épisodes non masqués (`stats_service.py:130-159`).

## Implémentation frontend

`frontend/src/views/Dashboard.vue` :
- Tuile "Dernière mise à jour" : `<a href="lmelpFrontOfficeUrl">` externe → `<div @click="navigateToRssMonitoring">` interne (méthode déjà existante).
- Nouvelle tuile "Épisodes sans transcription" : `<a>` externe (`target="_blank"`) vers `lmelpFrontOfficeUrl`, `v-if` masquant si compte = 0.
- Donnée chargée séparément (`episodesWithoutTranscriptionCount`, méthode `loadEpisodesWithoutTranscriptionCount()`) appelée en parallèle dans `mounted()` via `Promise.all`, PAS via `collectionsStatistics` (qui vient du payload caché) — cohérent avec la décision de ne pas cacher cette métrique.

## Bug d'infrastructure découvert en cours de route (hors scope #298)

En testant visuellement via Playwright, `.dev-ports.json` a disparu deux fois alors que les process backend/frontend restaient actifs (orphelins, invisibles à `get-services-info.sh`). Diagnostic confirmé par test A/B : lancer `start-dev.sh` en arrière-plan simple (`&`) depuis l'outil Bash de Claude Code expose le script à un SIGHUP quand le shell parent se termine (fin de l'appel d'outil) — signal non trappé par le script (seul `SIGINT SIGTERM` le sont) — qui tue le script sans exécuter `cleanup()`, laissant les process qu'il a backgroundés orphelins. `nohup ./scripts/start-dev.sh & disown` corrige immédiatement le symptôme (testé, fichier persiste). Issue dédiée créée : #299 (fix proposé : trapper aussi SIGHUP, et ne supprimer `.dev-ports.json` dans `cleanup()` qu'après confirmation que les process sont bien morts). Voir [[precommit_vs_venv_tool_versions]] pour un autre exemple de piège d'environnement dev spécifique à ce repo.

## Tests ajoutés

- Backend : `tests/test_stats_service.py` (exclusion masqués pour `_count_episodes_without_transcription`, exclusion sans-transcription pour `_count_episodes_without_avis_critiques`), `tests/test_stats_endpoint.py` (nouvel endpoint dédié, cas succès + erreur 500).
- Frontend : `frontend/tests/integration/Dashboard.test.js` (navigation interne au clic sur "Dernière mise à jour", affichage/masquage de la nouvelle tuile selon le compte, mock du nouvel endpoint ajouté à tous les `axios.get.mockImplementation` du fichier).

## État à la fin de la session

Code implémenté et vérifié (1571 tests backend, 712 tests frontend, pre-commit vert, vérification visuelle Playwright), mais **pas encore committé** — la session s'est arrêtée avant l'étape commit/PR pour traiter la découverte du bug #299 en aparté.
