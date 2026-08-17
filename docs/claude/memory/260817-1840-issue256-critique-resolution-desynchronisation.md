# Issue #256 — Critique mal détecté (désynchronisation de résolution de variante)

## Problème

Sur la page d'affichage d'une émission (`Emissions.vue` → `AvisTable.vue`), le critique
"Philippe Trétiack" apparaissait avec le badge ⚠️ "Critique non résolu" quand détecté sous
une variante orthographique ("Philippe Tretiak") dans le texte brut d'un avis. Pourtant, sur
la page "Identification des critiques" (`IdentificationCritiques.vue`), ce même nom était
déjà correctement résolu vers "Philippe Trétiack" (badge "Variante détectée").

## Cause racine

Deux mécanismes de matching nom/variante de critique indépendants existent dans le code :

1. `CritiquesExtractionService.find_matching_critique`
   (`src/back_office_lmelp/services/critiques_extraction_service.py:92-127`) — recalculé
   **à la volée** à chaque appel de `GET /api/episodes/{id}/critiques-detectes`, utilisé
   par la page Identification des critiques.
2. `AvisExtractionService._find_matching_critique`
   (`src/back_office_lmelp/services/avis_extraction_service.py:953-983`) — calculé **une
   seule fois** au moment de `POST /api/avis-critiques/save`, puis le `critique_oid`
   obtenu est figé définitivement dans le document `avis` en base MongoDB.

Quand une variante est ajoutée à un critique existant *après* la sauvegarde initiale des
avis (via `POST /api/critiques` ou `PUT /api/critiques/{id}/variantes`), les documents
`avis` déjà en base ne sont jamais re-matchés : `critique_oid` reste `null` pour toujours,
même si le nom est désormais reconnu comme variante. Les endpoints de lecture
(`GET /api/avis/by-emission/{emission_id}`, `GET /api/avis/by-livre/{livre_id}`)
relisaient ce `critique_oid` figé tel quel, sans jamais retenter le matching.

Important : les deux algorithmes de normalisation (basés sur `normalize_for_matching`)
sont cohérents entre eux — ce n'était pas un bug de logique de comparaison, uniquement un
problème de **fraîcheur des données lues** (deux sources de vérité désynchronisées).

## Correctif appliqué

Dans `src/back_office_lmelp/app.py`, ajout d'une fonction helper
`_resolve_critique_enrichment` (juste avant `get_avis_by_emission`, ~ligne 4646) qui,
quand `critique_oid` est absent mais `critique_nom_extrait` est renseigné, retente le
matching à la volée contre la liste courante des critiques/variantes en base (réutilise
`critiques_extraction_service.find_matching_critique`). Utilisée dans les deux endpoints
`GET /api/avis/by-emission/{emission_id}` et `GET /api/avis/by-livre/{livre_id}`, chacun
préchargeant `existing_critiques = list(critiques_collection.find({}))` une seule fois
avant la boucle d'enrichissement (pattern déjà utilisé ailleurs dans `app.py`, ex. lignes
3696, 3784, 4894).

**Décision de conception clé** : correctif en **lecture seule** (recalcul à chaque GET),
sans persistance/backfill du `critique_oid` retrouvé en base. Plus simple, aucun effet de
bord sur un endpoint GET, cohérent avec le modèle déjà utilisé par `critiques-detectes`.
Aucune modification frontend nécessaire : `AvisTable.vue` et `LivreDetail.vue`
consommaient déjà `avis.critique_oid`/`avis.critique_nom`, seule la donnée backend a changé.

## Tests ajoutés (TDD)

Dans `tests/test_api_avis_endpoints.py` :
- `TestGetAvisByEmission::test_get_avis_resolves_critique_via_variante_when_oid_missing`
- `TestGetAvisByLivre::test_get_avis_by_livre_resolves_critique_via_variante_when_oid_missing`

Les deux mockent `critiques_collection.find.return_value` avec un critique ayant une
variante correspondant à `critique_nom_extrait`, et vérifient que `critique_oid` et
`critique_nom` sont bien enrichis dans la réponse malgré un `critique_oid` initial à
`None`.

## Point d'attention pour du code futur similaire

Si un nouveau mécanisme de résolution d'entité (livre, auteur, éditeur...) est ajouté avec
un `_oid` calculé une seule fois puis persisté, vérifier systématiquement s'il existe déjà
un mécanisme de matching dynamique équivalent ailleurs dans le code (page
d'identification/validation) et s'assurer que les deux restent synchronisés, ou accepter
consciemment le compromis lecture-seule comme fait ici.

## Fichiers modifiés

- `src/back_office_lmelp/app.py` — ajout de `_resolve_critique_enrichment` et son usage
  dans `get_avis_by_emission` et `get_avis_by_livre`.
- `tests/test_api_avis_endpoints.py` — 2 nouveaux tests RED→GREEN.
