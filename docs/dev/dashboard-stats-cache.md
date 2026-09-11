# Cache des statistiques du dashboard

Ce document décrit le cache TTL des 14 tuiles "Informations générales" affichées sur la page d'accueil.

## Endpoint

`GET /api/dashboard/stats` agrège en un seul payload les statistiques auparavant servies par 6 endpoints distincts (`/api/statistics`, `/api/livres-auteurs/statistics`, `/api/stats/critiques-manquants`, `/api/books/duplicates/statistics`, `/api/authors/duplicates/statistics`, `/api/avis/orphaned/statistics`). Le résultat agrégé est mis en cache dans son ensemble par `DashboardStatsCacheService`.

Structure du payload :

```json
{
  "statistics": { "totalEpisodes": 181, "lastUpdateDate": "..." },
  "collections_statistics": { "episodes_sans_emission": 0, "emissions_sans_avis": 0, ... },
  "critiques_manquants_count": 0,
  "duplicate_books_count": 0,
  "duplicate_authors_count": 0,
  "orphaned_avis_count": 0
}
```

## Cache : TTL et invalidation manuelle

`DashboardStatsCacheService` (`src/back_office_lmelp/services/dashboard_stats_cache_service.py`) est un cache in-memory (dict + timestamp), TTL par défaut 300 secondes (5 minutes). Pattern repris de `CalibreMatchingService._get_data()` (Issue #199).

Le bouton "Actualiser" du dashboard suit le même mécanisme que celui de la page OnKindle (Issue #249) : `POST /api/dashboard/stats/cache/invalidate` vide le cache, suivi d'un nouveau `GET /api/dashboard/stats` qui recalcule.

## Invalidation automatique sur écriture MongoDB

Le backend n'a pas de couche d'abstraction commune pour les écritures MongoDB : les collections sont accédées directement (`mongodb_service.livres_collection.update_one(...)`) depuis des dizaines de points d'appel dans `app.py` et plusieurs services, sans passer par une méthode unique interceptable.

**Solution retenue** : un `pymongo.monitoring.CommandListener` (`DashboardStatsInvalidationListener`, `src/back_office_lmelp/services/dashboard_stats_invalidation_listener.py`), enregistré une seule fois sur le `MongoClient` dans `mongodb_service.connect()` :

```python
self.client = MongoClient(
    self.mongo_url,
    event_listeners=[
        DashboardStatsInvalidationListener(dashboard_stats_cache_service.invalidate_cache)
    ],
)
```

Le listener intercepte toute commande `insert`, `update`, `delete`, `findAndModify`, `bulkWrite` visant l'une des collections surveillées (`DASHBOARD_WATCHED_COLLECTIONS` : `livres`, `auteurs`, `avis_critiques`, `critiques`, `emissions`, `avis`, `livresauteurs_cache`, `episodes`) et invalide le cache dashboard, quel que soit le point du code applicatif à l'origine de l'écriture.

**Pourquoi ce choix** : ce backend a environ 59 points d'écriture MongoDB directs répartis sur 5 fichiers. Patcher individuellement chacun de ces sites serait fragile (risque d'oubli à chaque nouvelle fonctionnalité) et ne couvrirait pas le code ajouté ultérieurement. Le `CommandListener` se situe sous le driver pymongo lui-même : il intercepte toute écriture indépendamment de la façon dont le code applicatif a récupéré la collection.

## Piège mypy

`pymongo` ne fournit pas de stub typé pour `monitoring.CommandListener`, donc subclasser cette classe déclenche `Class cannot subclass "CommandListener" (has type "Any")`. Solution : `# type: ignore[misc]` sur la déclaration de la classe.

## Limite du `CommandListener` : métriques dont l'écriture source est externe

Le `CommandListener` ci-dessus n'intercepte que les écritures passant par le `MongoClient` de ce backend. Une métrique dont les données source sont écrites par une **application externe** (un autre process, un autre service) échappe totalement à ce mécanisme et resterait figée jusqu'à expiration du TTL (5 min) si elle était intégrée telle quelle au payload caché.

`episodes_without_transcription_count` (tuile "Épisodes sans transcription") en est un exemple : elle est intégrée au payload caché standard (`StatsService.get_cache_statistics()`) depuis que le pipeline de transcription PGX (Issue #302) écrit le champ `transcription` via ce même `MongoClient` — le listener l'observe donc nativement. Si une métrique future dépend d'une écriture réellement externe à ce backend, exposez-la via un endpoint dédié **non caché** plutôt que de l'ajouter au payload agrégé (voir `docs/dev/environment-variables.md` pour un exemple de service externe, ou tout futur cas similaire).

## Isolation par métrique dans `StatsService.get_cache_statistics()`

`get_cache_statistics()` calcule une dizaine de métriques indépendantes (une par tuile).
Sans isolation, une exception dans **une seule** d'entre elles (ex: collection MongoDB
temporairement inaccessible) fait échouer toute la fonction, qui fait échouer
`GET /api/livres-auteurs/statistics` (500), qui fait échouer `_compute_dashboard_stats()`
via `asyncio.gather()`, qui fait échouer tout `GET /api/dashboard/stats` (500) — cassant
les 14 tuiles pour une seule métrique en panne.

`get_cache_statistics()` enveloppe donc chaque calcul dans un helper `_safe(metric_name,
fn)` qui catch toute exception, la logue, et retourne `None` pour cette clé uniquement :

```python
def _safe(self, metric_name: str, fn: Callable[[], T]) -> T | None:
    try:
        return fn()
    except Exception as e:
        logger.error(f"Erreur lors du calcul de la métrique '{metric_name}': {e}")
        return None
```

**Contrepartie côté frontend** : le bloc `catch` de `Dashboard.vue::loadDashboardStats()`
(déclenché si `/api/dashboard/stats` échoue malgré tout, ex: erreur réseau complète) doit
lister explicitement **toutes** les clés lues par le template, à `null` — une clé absente
de cet objet de fallback laisse sa tuile bloquée indéfiniment sur le placeholder de
chargement (`'...'`), y compris après un rechargement réussi ultérieur qui écrase l'objet
en entier plutôt que de le fusionner (Issue #310 : `episodes_without_transcription_count`
avait été omise de ce fallback, la tuile restait alors bloquée sur `...` en production dès
qu'une seule requête avait échoué).

## Voir aussi

- `src/back_office_lmelp/services/dashboard_stats_cache_service.py`
- `src/back_office_lmelp/services/dashboard_stats_invalidation_listener.py`
- `src/back_office_lmelp/services/mongodb_service.py` (méthode `connect()`)
- `src/back_office_lmelp/services/stats_service.py` (méthode `_safe()`)
- `docs/dev/calibre-integration.md` (cache 5 min de `CalibreMatchingService`, pattern source)
