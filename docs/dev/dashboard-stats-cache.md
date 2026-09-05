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

## Voir aussi

- `src/back_office_lmelp/services/dashboard_stats_cache_service.py`
- `src/back_office_lmelp/services/dashboard_stats_invalidation_listener.py`
- `src/back_office_lmelp/services/mongodb_service.py` (méthode `connect()`)
- `docs/dev/calibre-integration.md` (cache 5 min de `CalibreMatchingService`, pattern source)
