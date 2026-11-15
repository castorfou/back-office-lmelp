# Issue #358 — La vérité terrain suggérait le titre d'un autre livre de l'émission

Issue : https://github.com/castorfou/back-office-lmelp/issues/358
Issue complétée pendant ce travail : https://github.com/castorfou/back-office-lmelp/issues/352 (commentaire sur la phase « Enrichissement Babelio… » sans avancement)

## Problème

Page **Livres et Auteurs**, émission du 15/11/2026 (`episode_oid` `6af98629a3c9beafb9dcb702`) : « Valider avec Babelio » proposait `Pierric Bailly – Rouge Truite → Saint Lucky Luke`. *Saint Lucky Luke* est la BD de Jul & Achdé, un autre livre de la même émission. Le vrai livre est *Rouges Truites*.

Babelio n'avait rien trouvé. La suggestion venait de la vérité terrain (`POST /api/fuzzy-search-episode`) :
- le texte de l'émission ne contient pas le vrai titre ;
- les seuls candidats « titre » (préfixe `📖`, segments entre guillemets du titre/description) étaient les autres livres de l'émission (`Saint Lucky Luke` 35.71, `Le Fondateur` 33.33) et une URL ;
- l'auteur est trouvé à 100, donc `_hasDecentGroundTruthMatches()` abaisse le seuil titre à 35 → `Saint Lucky Luke` passe ;
- `_extractGroundTruthSuggestion()` gardait le meilleur score combiné, sans exclusion ni seuil ;
- `_validateGroundTruthSuggestion()`, branche « matches décents » → `status: suggestion`.

## Solution

Tout dans `frontend/src/services/BiblioValidationService.js`.

1. **Autres livres de l'émission exclus** : `validateBiblio()` appelle `_filterGroundTruthTitleCandidates(groundTruthResult, original, episodeTitles)` juste après `_searchEpisodeWithCapture()`. La liste vient de `_getExtractedBooks(episodeId)` (cache `_extractedBooksCache`, déjà rempli par la Phase 0). Comparaison via `_normalizeTitle()` (minuscules, `removeAccents`, ponctuation → espace). Le titre du livre validé lui-même est conservé. Filtre `title_matches` et `titleMatches`, sur une copie de la réponse.
2. **Entités HTML** : `_isValidTitleSuggestion()` rejette `/&[a-z]+;|&#\d+;/i`. Les URL l'étaient déjà (`http`, `.fr`, `.com`).
3. **Seuil minimal** dans `_extractGroundTruthSuggestion()` : un candidat est écarté si score fuzzy < `MIN_GROUND_TRUTH_TITLE_SCORE` (50) **et** similarité < `MIN_GROUND_TRUTH_TITLE_SIMILARITY` (0.25). Sans candidat, le titre est vide et `_arbitrateResults()` retombe déjà sur Babelio seul (`!groundTruthSuggestion.title`).
   - Rouge Truite / Saint Lucky Luke : 35.7 / 0.125 → rejeté
   - Colcause / Kolkhoze (fixture existante, doit rester une suggestion) : 38 / 0.375 → gardé
4. La Levenshtein normalisée, auparavant locale à `_extractGroundTruthSuggestion()`, est extraite en `_titleSimilarity(a, b)`.

## Piège rencontré : l'ordre des candidats compte

Première version : le seuil était dans le filtre commun, appliqué avant `_hasGood…`/`_hasDecentGroundTruthMatches()`. Le cas fixture « Sephora Pondi – Aval » a régressé (`festival` suggéré au lieu de `Avale`).

Raison : `_hasDecentGroundTruthMatches()` lit le **premier** candidat valide de la liste, pas le meilleur. Le backend (`app.py`, endpoint fuzzy-search-episode) liste d'abord les segments entre guillemets (`📖`), puis les fragments du texte (n-grams, mots, score ≥ 60). Retirer « Tressaillir » (45, faible et éloigné) promouvait le fragment `festival` (77) en tête, qui franchissait le seuil de 75.

Règle retenue : le filtre commun ne retire que ce qui ne peut **jamais** être le livre (autres livres de l'émission) ; un seuil de qualité s'applique au choix final, pas à la liste lue par les tests d'ordre.

## Tests

`frontend/tests/unit/BiblioValidationService.otherEpisodeBook.test.js` :
- cas réel de l'issue (réponse fuzzy réelle en fixture, livres de l'épisode, Babelio `not_found`) → `not_found`, pas de `Saint Lucky Luke` ;
- filtre : autre livre exclu malgré casse/accents, livre validé gardé, format camelCase, réponse non modifiée ;
- seuil : Rouge Truite → titre vide, Colcause → Kolkhoze ;
- entités HTML rejetées, `&` seul accepté.

Suite frontend complète verte (862 tests).

## Test manuel

L'émission du 15/11 n'existait pas en local. Copiée depuis la prod (lecture seule) : l'épisode et son `avis_critiques`, **sans** `livresauteurs_cache` (qui contenait déjà la mauvaise suggestion). Résultat confirmé par l'utilisateur : Rouge Truite sort en non trouvé.

- Mongo de prod : NAS `192.168.50.207`, port **27018** (accessible depuis le réseau maison). Le port 27017 du NAS est une ancienne instance figée (239 épisodes, dernier le 23/08/2026).

## Constat annexe (→ #352)

« Valider avec Babelio » a deux phases (`validateWithBabelio()`, `frontend/src/views/LivresAuteurs.vue`) :
1. « Enrichissement Babelio… » : un seul appel `getLivresAuteurs({ enrich_babelio: true })`, le backend interroge Babelio pour tous les livres (≥ 10 s entre requêtes) → plusieurs minutes sans avancement visible ;
2. « Validation i/n — titre » : boucle frontend avec progression.
Ajouté en commentaire de #352.

## Hors périmètre

Piste annexe de l'issue : variante de recherche Babelio (pluriel « Rouges Truites », mots seuls), coûte des requêtes en plus, à évaluer séparément.
