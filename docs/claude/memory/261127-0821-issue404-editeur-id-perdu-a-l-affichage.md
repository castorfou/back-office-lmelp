# Issue #404 — L'éditeur saisi à la validation est perdu à l'affichage

## Symptôme

Un livre validé dans « Livres et Auteurs » avec l'éditeur « Conférence » s'affichait
« Revue Conférence » sur la page Émissions (tableau « Coups de cœur »).

## Cause

L'écriture était correcte : le livre pointait bien vers l'éditeur « Conférence » via
`editeur_id`. Depuis #189, un livre créé ou rafraîchi porte `editeur_id` (réf. collection
`editeurs`) et **plus** de champ texte `editeur` (`$unset`). Plusieurs lectures ne
regardaient que `livre["editeur"]` :

- `GET /api/avis/by-emission` (`src/back_office_lmelp/app.py`) → `editeur: null` → l'UI
  retombait sur `editeur_extrait` (texte du résumé LLM).
- Le tableau « Coups de cœur » de `frontend/src/components/AvisTable.vue` affichait
  `avis.editeur_extrait` en dur (le tableau « Programme » faisait déjà
  `avis.editeur || avis.editeur_extrait`).
- `get_auteur_with_livres` (projection sans `editeur_id`), `search_livres`,
  `get_livres_from_collections` (`app.py`), `get_critique_detail` (utilisait
  `editeur_extrait` même pour un livre résolu), `search_emissions` pass 2 (recherche par
  éditeur limitée au champ texte).

En local : 216 livres sur 1764 n'ont que `editeur_id`, 1545 que `editeur` texte, 3 aucun.
Diagnostic : la première capture Playwright montrait encore l'extrait après la correction
de l'API, parce que la ligne de l'issue était un **coup de cœur** (autre tableau).

## Correction

- Helper unique `MongoDBService.fill_editeur_names(livres)`
  (`src/back_office_lmelp/services/mongodb_service.py`, à côté de
  `search_editeur_by_name`) : pose `livre["editeur"]` depuis `editeur_id` quand le champ
  texte est absent/vide ; le texte prime ; `editeur_id` accepté en ObjectId ou str ;
  **une seule** requête `find({"_id": {"$in": ...}}, {"nom": 1})` pour le lot ; silencieux
  si `editeurs_collection is None` ou rien à résoudre. Modifie en place.
- Appliqué à : avis by-emission, `get_auteur_with_livres` (projection passée en notation
  pointée `"livres._id": 1, ..., "livres.editeur_id": 1`), `search_livres`,
  `get_livres_from_collections`, `get_critique_detail` (éditeur du livre, fallback
  extrait), `get_livre_with_episodes` (remplace la résolution inline `find_one`).
- `search_emissions` pass 2 : `$or` étendu à `{"editeur_id": {"$in": ids}}` où `ids` =
  éditeurs dont le `nom` matche la regex.
- `AvisTable.vue` coups de cœur : `{{ avis.editeur || avis.editeur_extrait }}`.
- Non touchés volontairement : refresh livre (`app.py`, logique `editeur_needs_migration`),
  `search_critical_reviews_for_authors_books` (legacy `avis_critiques`),
  `migrate_enrich_avis_editeur.py`, `AvisExtractionService` (`resolved["editeur"]` jamais
  persisté — alimenté de fait via `get_livres_from_collections`).

## Tests

- `tests/test_fill_editeur_names.py` (nouveau) : tests du helper et de chaque lecture sur
  **mongomock** (vraie exécution des requêtes : un mock de `find()` ne verrait pas une
  confusion ObjectId/str dans le `$in`). Compte des requêtes via un `find` enveloppé.
- `tests/test_api_avis_endpoints.py` : test endpoint avec `mongodb_service` mocké, le vrai
  helper branché via `side_effect=lambda livres: MongoDBService.fill_editeur_names(mock, livres)`.
- `frontend/src/components/__tests__/AvisTable.spec.js` : éditeur officiel / fallback
  extrait pour les coups de cœur.
- Ajustements : `tests/test_api_search_emissions.py` (services construits par `__new__`
  → ajout `service.editeurs_collection = None`), `tests/test_editeur_management.py`
  (mock `find_one` → `find` en lot).

## Pièges rencontrés

- **mongomock ne gère pas la projection imbriquée** `{"livres": {"_id": 1, ...}}` dans un
  `$project` (il renvoie le dict de projection tel quel). La notation pointée
  `"livres._id": 1` est équivalente en MongoDB et supportée par mongomock.
- `mongomock` `insert_many([])` lève `TypeError: documents must be a non-empty list`.
- Un service construit par `MongoDBService.__new__` (sans `__init__`) n'a pas
  `editeurs_collection` : tout nouvel attribut lu dans une méthode casse ces tests.
- L'accès lecture à la Mongo de prod (NAS) depuis le devcontainer a été refusé par le
  classifieur de permissions : reproduire sur des données locales équivalentes
  (agrégation avis ⨝ livres à `editeur_id` dont le nom ≠ `editeur_extrait`).

## Vérification

API locale : émission du 26/08/2018, « Ça raconte Sarah » → `editeur: "Minuit"`
(extrait « Éditions de Minuit ») ; page Émissions (Playwright) et page Auteur affichent
« Minuit ». Validé par l'utilisateur.
