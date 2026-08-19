# Issue #263 — Matching critique échoue sur accents (Philippe Tretiak)

## Contexte

Suite à l'issue #256, le re-matching à la volée en lecture seule sur
`GET /api/avis/by-emission/...` corrigeait bien l'affichage web du critique
"Philippe Trétiack", mais 6 documents `avis` en base MongoDB gardaient
`critique_oid: null` de façon permanente : ce champ n'est jamais recalculé
après la sauvegarde initiale. Ajouter "Philippe Tretiak" comme variante et
ré-extraire l'épisode ne changeait rien au problème.

## Cause racine

Deux fonctions de normalisation coexistent dans le backend :

- `text_utils.normalize_for_matching()` (utilisée par
  `critiques_extraction_service.find_matching_critique()`, appelée par le
  re-matching à la volée dans `app.py`) : fait une décomposition Unicode NFD
  et retire les accents.
- `AvisExtractionService._normalize_for_matching()`
  (`src/back_office_lmelp/services/avis_extraction_service.py:681-695`,
  méthode privée locale à la classe) : fait uniquement
  `" ".join(text.lower().split())` — **aucun retrait d'accent**.

`_find_matching_critique()` (`avis_extraction_service.py:953-987`), appelée
lors de l'extraction initiale des avis via `resolve_avis()` →
`POST /api/avis/extract/{emission_id}`, utilisait la seconde fonction.
Résultat : "Philippe Tretiak" (nom extrait par l'IA depuis la transcription,
sans accent) ne matchait jamais "Philippe Trétiak" (variante stockée en
base, avec accent) — d'où l'écart entre affichage (corrigé par le
re-matching GET) et donnée persistée (jamais corrigée).

## Correctif

Scope volontairement **limité au matching des critiques** (décision
utilisateur, pour ne pas risquer de régression sur le matching
livres/auteurs qui utilise la même `_normalize_for_matching` locale mais est
hors scope de cette issue) :

- `avis_extraction_service.py` : import de
  `from ..utils.text_utils import normalize_for_matching`, et remplacement
  des 3 appels à `self._normalize_for_matching` par `normalize_for_matching`
  **uniquement dans `_find_matching_critique`** (`avis_extraction_service.py:969-987`).
  Les méthodes `_find_matching_livre_*` continuent d'utiliser la
  normalisation locale (casse/espaces uniquement), inchangées.

## Tests (TDD)

- RED puis GREEN : `test_resolve_matches_critique_ignoring_accents` dans
  `tests/test_avis_extraction_service.py` (classe `TestResolveEntities`),
  reproduit exactement le cas de l'issue ("Philippe Tretiak" extrait vs
  critique "Philippe Trétiack" avec variantes accentuées).
- Suite complète backend : 1454 passed, 25 skipped, 0 failed — aucune
  régression sur le matching de livres (non touché).

## Vérification en base (post ré-extraction utilisateur)

Connexion MongoDB `nas923:27018/masque_et_la_plume` (URL du `.env` du
projet — pas la connexion MCP `preconfigured`, qui pointe ailleurs). Après
que l'utilisateur a ré-extrait l'épisode dans l'interface avec le fix en
place, les 6 documents `avis` pour "Philippe Tretiak" ont bien
`critique_oid` renseigné avec l'ObjectId du critique "Philippe Trétiack"
(au lieu de `null` précédemment).

## Point d'attention pour le futur

Il existe donc **deux normalisations différentes utilisées pour le même
type de matching** (nom de critique) selon le chemin de code emprunté
(extraction initiale vs re-matching à la volée). Si un futur bug de
matching critique/livre apparaît côté extraction initiale, vérifier
en premier si `AvisExtractionService._normalize_for_matching` (locale,
casse/espaces uniquement) est en cause plutôt que
`text_utils.normalize_for_matching` (accents/ligatures/tirets, la version
"complète" documentée dans `CLAUDE.md` § "Text Normalization for Accent and
Typographic Insensitivity").

## Pas de nouvel endpoint de re-matching en masse

Décision utilisateur : pas de script/endpoint de recalcul en masse de
`critique_oid` pour les avis existants. Les documents historiques bugués se
corrigent par ré-extraction manuelle de l'épisode concerné dans l'interface.
