# Issue #277 — Tuiles Bibliothèque Calibre cliquables vers la fiche livre LMELP

## Contexte

Sur la page Bibliothèque Calibre (`/calibre`), les ~568 tuiles de livres affichaient titre/auteurs/éditeur/note/tags mais n'étaient pas cliquables, même quand le livre correspondait à un livre du Masque et la Plume dans MongoDB. La page OnKindle (`/onkindle`) avait déjà ce comportement (titre cliquable uniquement), mais sur un volume beaucoup plus petit (~15 livres taggés `onkindle`).

## Implémentation

### Backend

- Nouvelle méthode `get_calibre_id_to_mongo_livre_id_map()` dans `src/back_office_lmelp/services/calibre_matching_service.py` — matching par titre normalisé exact (tier 1 uniquement, pas de validation auteur), retourne `{calibre_id: mongo_livre_id}` pour l'ensemble de la bibliothèque. Réutilise le cache 5 min déjà existant (`_get_data()`), donc pas de coût supplémentaire de scan pour ~568 livres.
- Refactor : extraction d'un helper privé `_build_mongo_by_norm_title()` partagé entre cette nouvelle méthode et `get_onkindle_books()` (qui dupliquait la même logique d'index par titre normalisé).
- Champ `mongo_livre_id: str | None` ajouté au modèle `CalibreBook` dans `src/back_office_lmelp/models/calibre_models.py`.
- Enrichissement fait au niveau de l'endpoint (`get_calibre_books()` dans `src/back_office_lmelp/app.py:834-844`), pas dans `calibre_service` — car `calibre_service` n'a pas de dépendance vers MongoDB, seul `calibre_matching_service` connaît les deux sources.

### Frontend

- `frontend/src/views/CalibreLibrary.vue` : la tuile `book-card` utilise `<component :is="book.mongo_livre_id ? 'router-link' : 'div'">` pour rendre toute la carte cliquable (pas seulement le titre, contrairement à OnKindle — décision utilisateur explicite) quand un matching existe, avec classe `.clickable` pour le curseur pointer.
- CSS : `.book-card` a maintenant `text-decoration: none; color: inherit; display: block;` pour neutraliser le style de lien par défaut du `<a>` rendu par `router-link`.

### Effet de bord découvert après vérification manuelle par l'utilisateur

Rendre les tuiles cliquables crée un nouvel usage : cliquer sur un livre puis faire "retour arrière" navigateur perdait l'état de la page (recherche, filtre lu/non lu, tri), car seul `searchText` était restauré depuis `$route.query.search` (pour les deep-links depuis Palmares), et rien n'était synchronisé en écriture.

**Fix** : synchronisation bidirectionnelle des 3 réglages (`searchText`, `readFilter`, `sortBy`) avec les query params de l'URL (`search`, `read`, `sort`), via une méthode `syncStateToUrl()` appelée par `setReadFilter()`, `setSortBy()`, et un `watch` sur `searchText`. Utilise `$router.replace()` (pas `push`) pour ne pas polluer l'historique à chaque frappe/clic — cohérent avec le pattern déjà en place dans `frontend/src/views/OnKindle.vue` (qui persiste son tri de la même façon).

## Points d'apprentissage

1. **Piège de test découvert** : le fichier de test `frontend/tests/unit/CalibreLibrary.test.js` montait le composant sans jamais naviguer le router de test vers `/calibre` (routes enregistrées mais `router.currentRoute` restait sur `/` non matché). Tant qu'aucun code n'appelait `$router.replace()`, ce décalage restait silencieux (juste un warning `[Vue Router warn]: No match found for location with path "/"`). Dès qu'on ajoute une navigation programmatique (ex: sync d'état vers l'URL), ce genre de router de test mal initialisé devient une erreur fatale (`Error: No match for ... while being at {path: "/"}`). **Fix** : toujours faire `await router.push('/calibre')` dans le `beforeEach` du test après avoir enregistré les routes, comme le fait déjà `OnKindle.spec.js`.

2. **Décision produit** : contrairement à OnKindle où seul le titre est cliquable, ici l'utilisateur a explicitement demandé que toute la tuile soit cliquable (meilleure zone de clic vu la densité de la grille de 568 cartes).

3. Le refactor d'extraction de `_build_mongo_by_norm_title()` illustre le principe DRY appliqué a posteriori : la seconde implémentation d'un même besoin (index de lookup par titre normalisé) a servi de déclencheur pour factoriser, plutôt que d'anticiper la factorisation dès la première implémentation (`get_onkindle_books`, issue #216).

## Fichiers modifiés

- `src/back_office_lmelp/services/calibre_matching_service.py` — nouvelle méthode + refactor
- `src/back_office_lmelp/models/calibre_models.py` — champ `mongo_livre_id`
- `src/back_office_lmelp/app.py` — enrichissement endpoint `/api/calibre/books`
- `frontend/src/views/CalibreLibrary.vue` — tuiles cliquables + persistance URL
- `tests/test_calibre_matching_service.py`, `tests/test_calibre_endpoints.py` — tests backend TDD
- `frontend/tests/unit/CalibreLibrary.test.js` — tests frontend TDD (tuiles cliquables + persistance état)

## Résultat

- Backend : tous les tests passent (les 8 échecs observés en suite complète sont pré-existants, liés au circuit breaker Babelio externe, sans rapport avec Calibre).
- Frontend : 692 tests passent (4 nouveaux ajoutés pour cette issue).
- Vérification manuelle par l'utilisateur en conditions réelles (568 livres, 203 matchés) : comportement confirmé correct, y compris la persistance d'état après retour arrière.
