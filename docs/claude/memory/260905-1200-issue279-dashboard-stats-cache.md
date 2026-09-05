# Issue #279 — Cache des tuiles "Informations générales" du dashboard

## Contexte

Le dashboard (page d'accueil) recalculait à chaque affichage les 14 tuiles de stats (2-3 secondes), via 6 appels HTTP distincts. Objectif : cache TTL, bouton d'actualisation forcée, invalidation automatique lors des écritures MongoDB pertinentes (génération avis critiques, extraction livres/auteurs, identification critiques, liaison Babelio, page Emissions).

## Décisions d'architecture (validées avec l'utilisateur avant implémentation)

1. **Cache unique global** plutôt que cache partiel : un seul nouvel endpoint agrégé `GET /api/dashboard/stats` remplace les 6 appels HTTP existants du dashboard (`/api/statistics`, `/api/livres-auteurs/statistics`, `/api/stats/critiques-manquants`, `/api/books|authors/duplicates/statistics`, `/api/avis/orphaned/statistics`), mis en cache dans son ensemble.
2. **Invalidation globale simple** (pas de granularité fine par tuile) : n'importe quelle écriture pertinente invalide tout le cache dashboard.

## Découverte clé : pas de couche d'abstraction d'écriture MongoDB

Exploration du code a montré qu'il n'existe **aucun point de passage centralisé** pour les écritures MongoDB dans ce backend : ~59 points d'écriture directs (`collection.update_one()`, `insert_one()`, etc.) dispersés dans 5 fichiers (`app.py`, `mongodb_service.py`, `babelio_migration_service.py`, `duplicate_books_service.py`, `livres_auteurs_cache_service.py`). `MongoDBService.get_collection()` retourne l'objet `Collection` pymongo brut — pas de wrapper.

**Solution retenue** : un `pymongo.monitoring.CommandListener` enregistré une seule fois sur le `MongoClient` (dans `mongodb_service.connect()`, via `event_listeners=[...]`). Il intercepte toute commande d'écriture (`insert`, `update`, `delete`, `findAndModify`, `bulkWrite`) sur les collections surveillées, quel que soit le point d'entrée applicatif qui a déclenché l'écriture — sans toucher aux ~59 call-sites existants. C'est LE point de centralisation technique disponible quand le code applicatif n'en a pas.

Implémentation : `src/back_office_lmelp/services/dashboard_stats_invalidation_listener.py` (`DashboardStatsInvalidationListener`, collections surveillées dans `DASHBOARD_WATCHED_COLLECTIONS`), branché dans `mongodb_service.py:connect()`.

## Implémentation

- `src/back_office_lmelp/services/dashboard_stats_cache_service.py` : `DashboardStatsCacheService`, cache in-memory TTL 300s, pattern repris de `CalibreMatchingService._get_data()` (dict + timestamp). Deux API : `get_stats(compute_fn)` (usage synchrone) et `get_cached()`/`set_cache()` (primitives, nécessaires pour un appelant `async` qui ne peut pas passer une coroutine comme `compute_fn` synchrone).
- `src/back_office_lmelp/app.py` : nouveaux endpoints `GET /api/dashboard/stats` (agrège via `_compute_dashboard_stats()`) et `POST /api/dashboard/stats/cache/invalidate` (pattern identique à `POST /api/calibre/cache/invalidate`, Issue #249).
- `frontend/src/views/Dashboard.vue` : `mounted()` ne fait plus que 2 appels (`loadDashboardStats()` + `loadVersionInfo()`) au lieu de 6 ; nouveau bouton "Actualiser" (pattern OnKindle) avec état `refreshing`.

## Piège rencontré : réécriture de `bytes | memoryview` par mypy

`_compute_dashboard_stats()` réutilise directement `get_critiques_manquants_count()` (qui retourne un `JSONResponse`) pour éviter de dupliquer sa logique complexe (boucle + extraction regex de critiques). Il faut parser `response.body` en JSON — mais `JSONResponse.body` est typé `bytes | memoryview`, et `json.loads()` n'accepte pas `memoryview`. Fix : `json.loads(bytes(response.body))`.

## Piège rencontré : subclasser `pymongo.monitoring.CommandListener`

pymongo n'a pas de stubs typés complets pour `CommandListener` → mypy erreur `Class cannot subclass "CommandListener" (has type "Any")`. Fix : `# type: ignore[misc]` sur la déclaration de classe (pattern accepté, pas de solution plus propre pour cette lib).

## Piège rencontré : réécriture de 25 tests frontend fortement couplés

`frontend/tests/integration/Dashboard.test.js` mockait individuellement `statisticsService.getStatistics()`, `livresAuteursService.getCollectionsStatistics()`, et 4 `axios.get` distincts. Passer à un seul `GET /api/dashboard/stats` a nécessité de réécrire l'intégralité du fichier de test (validé explicitement avec l'utilisateur avant de le faire, car risque de régression important sur ~25 tests). Le composant garde en interne les mêmes noms de `data()` (`statistics`, `collectionsStatistics`, etc.) — seule la **source** change, pas le template ni les `computed`.

## Validation

- 21 nouveaux tests backend + 25 tests frontend réécrits, tous GREEN.
- Suite complète backend (1500 passed) et frontend (695 passed) non régressées — 8 échecs backend préexistants (Babelio 403/circuit breaker) confirmés indépendants via `git stash`.
- Vérification visuelle Playwright MCP en conditions réelles : navigation, tuiles avec vraies données MongoDB, clic sur "Actualiser" déclenchant bien `POST invalidate` + `GET` recalculé (network requests confirmées).
- **Piège environnement** : lors du test manuel, un ancien process `start-dev.sh` orphelin (démarré dans une session précédente) squattait le port 5173, donnant l'impression que le endpoint n'existait pas (404) alors que le nouveau backend répondait correctement en direct. Toujours vérifier `ps aux | grep -E "vite|start-dev"` et tuer les process orphelins avant de conclure à un bug si le comportement observé contredit ce que le code montre.

## Découverte hors-sujet : bug bouton "Traiter" (Issue #282)

Pendant le test utilisateur, découverte d'un bug indépendant sur la page Livres et Auteurs : deux systèmes de statut incompatibles coexistent dans `livresauteurs_cache` (champ `status` vs `validation_status`/`biblio_verification_status` legacy), qui fait que le bouton "Traiter" de `auto_process_verified_books()` n'a jamais pu fonctionner car il interroge un champ jamais peuplé par le flux d'écriture actif. Diagnostiqué en détail et documenté dans une issue séparée plutôt que mélangé à cette PR — voir Issue #282.
