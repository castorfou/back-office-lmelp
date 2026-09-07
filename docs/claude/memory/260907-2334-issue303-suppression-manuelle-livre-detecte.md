# Issue #303 — Suppression manuelle d'une entrée détectée (Livres et Auteurs)

## Contexte

Le LLM extrait parfois un livre mentionné en passant dans un épisode (pas au programme, juste cité par un critique à propos d'un autre livre du même auteur) comme s'il s'agissait d'un livre à part entière détecté. Cas concret rapporté : épisode du 6/9/26, 11 livres détectés au lieu de 10 attendus (5 programme + 5 coups de cœur) — un critique évoquait "Mais que fait ce sang sur le pull de Jennifer ?" de Lucie Rico (POL) et a mentionné en aparté un précédent livre de la même autrice, "Un autre pareil", que l'extraction du résumé a fait remonter comme une œuvre détectée à part entière.

Deux pistes étaient possibles : renforcer le prompt d'extraction du résumé (traité séparément), ou ajouter un filet de sécurité manuel permettant à l'utilisateur de supprimer une détection erronée. C'est cette seconde piste qui a été implémentée ici.

## Décision de conception

- Le bouton "🗑️ Supprimer" n'apparaît que pour les entrées de cache dont `status !== 'mongo'` (`verified`, `corrected`, `not_found`) — c'est-à-dire pas encore validées/créées dans les collections `livres`/`auteurs`. La suppression cascade d'un livre déjà créé en base est explicitement **hors scope** de cette issue (risque de casser des références dans `episodes`/`avis_critiques`).
- Confirmation via un **modal dédié** (`data-testid="delete-confirm-modal"`), suivant exactement le pattern déjà en place dans `frontend/src/views/LivresAuteurs.vue` pour les modaux de validation et d'ajout manuel (`modal-overlay`/`modal-content`/`modal-actions`), plutôt qu'un `window.confirm()` natif — pour rester visuellement cohérent avec le reste de cette page spécifique.

## Implémentation (TDD, 4 cycles : service backend → endpoint → service API frontend → composant)

**Backend** :
- `src/back_office_lmelp/services/livres_auteurs_cache_service.py` — nouvelle méthode `delete_cache_entry(cache_id: ObjectId) -> bool`, suit exactement le pattern de `delete_cache_by_episode()` déjà présent (`cache_collection.delete_one({"_id": cache_id})`, retour basé sur `result.deleted_count > 0`).
- `src/back_office_lmelp/app.py` — nouvel endpoint `DELETE /api/livres-auteurs/cache/{cache_id}`, placé juste après `DELETE /api/livres-auteurs/cache/episode/{episode_oid}` existant (suppression de tout le cache d'un épisode). Validation manuelle du format ObjectId (24 caractères hex) avant conversion, retourne 404 si format invalide ou entrée non trouvée, 200 `{"deleted": true, "cache_id": ...}` sinon.

**Frontend** :
- `frontend/src/services/api.js` — `livresAuteursService.deleteCacheEntry(cacheId)`, wrapper trivial calqué sur `deleteCacheByEpisode`/`deleteAvis`.
- `frontend/src/views/LivresAuteurs.vue` — bouton `data-testid="delete-cache-entry-btn"` ajouté dans le même bloc `<template v-if="book.status !== 'mongo'">` qui contient déjà les boutons "✅ Traiter"/"🔍 Valider"/"➕ Ajouter" ; nouveau modal de confirmation (`showDeleteConfirmModal`, `bookToDelete` dans `data()`) avec les méthodes `confirmDeleteCacheEntry(book)`, `cancelDeleteCacheEntry()`, `deleteCacheEntry()` (celle-ci appelle le service puis `loadBooksForEpisode()` pour rafraîchir la liste).

## Point technique vérifié avant implémentation

Le champ `book.cache_id` (string d'ObjectId) est construit côté backend dans `src/back_office_lmelp/services/books_extraction_service.py:489` (`simplified_book["cache_id"] = str(book["_id"])`) et déjà consommé ailleurs dans `LivresAuteurs.vue` (Issue #282, bouton "Traiter"). Pas de nouveau champ à introduire — vérifier ce genre de champ existant avant d'en inventer un nouveau pour une future feature similaire sur cette page.

## Tests ajoutés

- `tests/test_livres_auteurs_cache_service_get_by_status.py` — classe `TestDeleteCacheEntry` (2 tests : suppression trouvée/non trouvée), même style de mock que les tests voisins (`@patch("back_office_lmelp.services.livres_auteurs_cache_service.mongodb_service")`).
- `tests/test_livres_auteurs_endpoint.py` — 3 tests dans `TestLivresAuteursCacheEndpoint` (succès, non trouvé → 404, format invalide → 404 sans appeler le service).
- `frontend/tests/integration/LivresAuteurs.test.js` — nouvelle section `describe` avec 6 tests (affichage conditionnel du bouton selon `status`, ouverture du modal, confirmation → appel API + rechargement, annulation → pas d'appel, gestion d'erreur API).

Aucune régression : suite backend complète 1580 passed, suite frontend complète 718 passed après implémentation.

Vérification manuelle faite en conditions réelles sur l'épisode `6a9d98080653c80b881510be` (le cas concret "Un autre pareil" / Lucie Rico existait toujours en cache avec `status: "not_found"` au moment du test) — bouton visible et fonctionnel confirmé par l'utilisateur via le navigateur.

## Fichiers modifiés

- `src/back_office_lmelp/services/livres_auteurs_cache_service.py`
- `src/back_office_lmelp/app.py`
- `frontend/src/services/api.js`
- `frontend/src/views/LivresAuteurs.vue`
- `tests/test_livres_auteurs_cache_service_get_by_status.py`
- `tests/test_livres_auteurs_endpoint.py`
- `frontend/tests/integration/LivresAuteurs.test.js`
