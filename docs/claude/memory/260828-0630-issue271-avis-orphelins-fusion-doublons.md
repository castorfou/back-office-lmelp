## Issue #271 — Avis orphelins après fusion de doublons de livres

### Contexte métier

L'export MongoDB → SQLite pour `lmelp-mobile` plantait avec `FOREIGN KEY constraint failed` sur la table `avis`. Cause racine : des documents `avis` référencent un `livre_oid` (String) qui ne correspond plus à aucun `livres._id` (ObjectId) — typiquement après une fusion de doublons de livres qui ne repointait jamais les avis existants.

### Ce qui a été implémenté

**Partie 1 — Fix préventif** (`src/back_office_lmelp/services/duplicate_books_service.py`) : `merge_duplicate_group()` a une nouvelle étape 9 qui repointe automatiquement `avis.livre_oid` (String) des livres doublons supprimés vers le livre primaire survivant, via `avis_collection.update_many({"livre_oid": {"$in": duplicate_ids_str}}, {"$set": {"livre_oid": str(primary_book["_id"])}})`. Le résultat de fusion expose désormais `avis_entries_updated`.

**Partie 2 — Visibilité dashboard** : nouveau service `src/back_office_lmelp/services/orphaned_avis_service.py` (`OrphanedAvisService`), route `GET /api/avis/orphaned/statistics`, nouvelle tuile "Avis orphelins" dans `frontend/src/views/Dashboard.vue` (pattern masquage à 0, Issue #212).

**Partie 3 — Page de nettoyage manuel** : route `GET /api/avis/orphaned` (liste avec contexte), réutilisation des routes existantes `PUT`/`DELETE /api/avis/{avis_id}` (déjà capables de modifier `livre_oid` ou supprimer). Nouveau composant `frontend/src/views/OrphanedAvis.vue`, route `/avis-orphelins`.

**Partie 3bis — Correctif post-incident** (voir ci-dessous) : `list_orphaned_avis()` (`src/back_office_lmelp/services/orphaned_avis_service.py:31-84`) détecte désormais, pour chaque avis orphelin, si un livre correspondant existe en base (matching par titre normalisé via `normalize_for_matching()`, méthode `_build_titre_index()`). Le résultat expose `suggested_livre_id` / `suggested_livre_titre`. Côté UI (`frontend/src/views/OrphanedAvis.vue`), le bouton "Supprimer" est masqué (`v-if="!avis.suggested_livre_id"`) quand une suggestion existe, remplacé par un bouton "Repointer vers ce livre" pré-rempli en un clic.

### Incident survenu pendant le test manuel (leçon importante)

Pendant le test manuel de la Partie 3, une suppression réelle d'un avis orphelin ("La Promesse", note 9, critique Olivia de Lamberterie) a été effectuée via l'UI alors que **le livre existait toujours en base** sous un autre `_id` (`69496a1cfcfa88e53d6abe3b`, toujours lié à l'émission via `livres.episodes`).

**Effet de bord** : `_count_emissions_with_problems()` (`src/back_office_lmelp/services/stats_service.py:421-512`) compare `livres_summary` (titres uniques extraits de `avis.livre_titre_extrait` pour l'émission) vs `livres_mongo_count` (compte de `livres` ayant cet épisode dans leur `episodes`). En supprimant l'avis, `livres_summary` est passé de 5 à 4 alors que `livres_mongo_count` restait à 5 → écart détecté → badge 🔴 "1 Émission avec problème" est apparu sur le Dashboard.

**Réparation** : l'avis a été réinséré manuellement en base (mêmes commentaire/note/critique) avec `livre_oid` repointé directement vers le livre survivant, restaurant `emissions_with_problems: 0`.

**Root cause du défaut de conception** : la page de nettoyage (Partie 3 initiale) présentait "Repointer" et "Supprimer" à égalité pour tous les avis orphelins, sans jamais vérifier si le cas était "livre déplacé" (le cas très majoritaire après une fusion de doublons — le livre existe encore) vs "livre vraiment disparu" (rare). Corrigé par la Partie 3bis.

**Règle à retenir pour l'avenir** : avant de proposer/exécuter une action destructive (`delete`) sur des données réelles pendant un test manuel, vérifier explicitement s'il existe une donnée de remplacement (ici : un livre correspondant par titre) et privilégier la correction (repointage) plutôt que la suppression quand c'est possible — l'UI elle-même doit porter cette distinction plutôt que de la laisser à la charge de l'utilisateur qui teste.

### Fichiers clés

- `src/back_office_lmelp/services/duplicate_books_service.py` — étape 9 de `merge_duplicate_group()`
- `src/back_office_lmelp/services/orphaned_avis_service.py` — nouveau service, `_orphaned_pipeline()`, `_build_titre_index()`, `get_orphaned_statistics()`, `list_orphaned_avis()`
- `src/back_office_lmelp/app.py` — routes `GET /api/avis/orphaned/statistics`, `GET /api/avis/orphaned` (placées avant `PUT/DELETE /api/avis/{avis_id}` pour respecter l'ordre FastAPI specific-before-parametric)
- `frontend/src/views/OrphanedAvis.vue` — page de nettoyage, pattern calqué sur `frontend/src/views/DuplicateBooks.vue`
- `frontend/src/views/Dashboard.vue` — tuile "Avis orphelins", `loadOrphanedAvisStatistics()`, `navigateToOrphanedAvis()`
- `src/back_office_lmelp/services/stats_service.py:421-512` — `_count_emissions_with_problems()`, logique du badge 🔴 à connaître pour tout futur travail touchant `avis` ou `livres.episodes`

### Pattern technique réutilisable

Pour toute jointure `avis.livre_oid` (String) → `livres._id` (ObjectId) dans une agrégation MongoDB, le pattern retenu dans ce repo est `$lookup` avec `let: {"livre_id": {"$toObjectId": "$livre_oid"}}` + `pipeline: [{"$match": {"$expr": {"$eq": ["$_id", "$$livre_id"]}}}]` — déjà utilisé dans `src/back_office_lmelp/services/mongodb_service.py:2739` (méthode `get_palmares`), repris tel quel dans `orphaned_avis_service.py:31-46`.

### Suivi GitHub

Specs et incident documentés en commentaires sur l'issue : https://github.com/castorfou/back-office-lmelp/issues/271#issuecomment-5441551099 et https://github.com/castorfou/back-office-lmelp/issues/271#issuecomment-5442852592
