# Issue #185 : Système complet d'extraction et matching des avis critiques

**Date** : 30 janvier 2026
**Branche** : `185-feat-extraire-des-avis-structures-des-summary-davis_critiques`
**Status** : En cours - 27 commits depuis main
**Commits** : c503df6 → 0a17ad0 (2 semaines de développement)

## Vue d'ensemble

Issue #185 implémente un système complet d'extraction d'avis critiques structurés depuis les summaries LLM markdown, avec résolution vers MongoDB via un algorithme de matching robuste en 4 phases. Comprend UI complète, badges de statut, auto-sélection, et enrichissements.

---

## Phase 1 : Infrastructure extraction et matching initial (c503df6 → 56588ed)

### Commit c503df6 : Foundation complète
**3667 lignes ajoutées** - Infrastructure initiale extraction et résolution

**Backend** :
- `src/back_office_lmelp/services/avis_extraction_service.py` (453 lignes)
  - Extraction Section 1 (programme) et Section 2 (coups de cœur)
  - Matching en 3 phases : exact, partiel, similarité
  - Résolution `livre_oid`, `critique_oid`, `auteur_oid`
- `src/back_office_lmelp/app.py` (380 lignes)
  - Endpoints `/api/avis-critiques/{episode_id}` et `/api/avis-critiques/{episode_id}/save`
- `src/back_office_lmelp/services/mongodb_service.py` (202 lignes)
  - CRUD complet pour collection `avis_critiques`
- `src/back_office_lmelp/models/avis.py` (93 lignes)
  - Modèle Pydantic pour validation

**Frontend** :
- `frontend/src/components/AvisTable.vue` (601 lignes)
  - Affichage tableau Section 1 (programme) et Section 2 (coups de cœur)
  - Distinction visuelle par section
- `frontend/src/views/Emissions.vue` (270 lignes)
  - Intégration workflow génération → extraction → sauvegarde
- `frontend/src/services/api.js` (55 lignes)
  - Méthodes API `getAvisCritiques()`, `saveAvisCritiques()`

**Tests** (1618 lignes) :
- `tests/test_avis_extraction_service.py` (598 lignes)
- `tests/test_api_avis_endpoints.py` (453 lignes)
- `tests/test_mongodb_service_avis.py` (414 lignes)
- `tests/fixtures/avis_summary_samples.py` (153 lignes)

### Commit 56588ed : Fuzzy matching initial
**184 lignes** - Ajout fuzzy matching pour livres non résolus

- `_fuzzy_match_remaining_books()` dans `avis_extraction_service.py:852-951`
- Matrice de similarité + assignment greedy
- Cas 1vs1 : association automatique

---

## Phase 2 : Statistiques, UI et Phase 4 (3db65e8 → d472a56)

### Commit 3db65e8 : Stats et UI améliorée
**293 lignes** - Affichage stats matching + colonnes UI

**Statistiques** :
- Compteurs par phase : `match_phase1`, `match_phase2`, `match_phase3`, `unmatched`
- Basé sur livres uniques (pas avis individuels)
- Endpoint retourne stats dans réponse API

**UI** :
- Colonnes Match Phase (Phase 1/2/3, badge couleur)
- Auteurs cliquables → navigation `/auteurs/{id}`
- Affichage stats sous tableau

### Commit f0bf727 : Persistance match_phase
**17 lignes** - Sauvegarde `match_phase` en base

- Ajout champ `match_phase` dans modèle `Avis`
- Permet stats après reload depuis MongoDB

### Commit 05d8c08 : Préservation titre extrait
**528 lignes** - Fix propagation matching

**Problème** : Tous les avis d'un même livre doivent recevoir le même `livre_oid`
**Solution** :
- Préserver `livre_titre_extrait` (ne pas le remplacer par titre MongoDB)
- Clé `(titre, auteur)` pour propagation correcte
- Tests frontend : `AvisTable.spec.js` (169 lignes)

### Commit d472a56 : Phase 4 fuzzy matching
**390 lignes** - Fuzzy matching quand `len(summary) == len(mongo)`

**Cas d'usage** : Dernier livre restant de chaque côté → association automatique
**Implémentation** :
- Phase 4 activée si même nombre de livres restants
- Matrice de similarité pour cas général
- Tests : `Emissions.matchingStats.test.js` (144 lignes)

---

## Phase 3 : Système de badges et refactoring (0639de3 → 0f226fd)

### Commit 0639de3 : Badges et auto-sélection
**1413 lignes** - Système complet de badges émission

**Badges** :
- 🟢 **perfect** : Tous les livres matchés, count égal
- 🟡 **unmatched** : Des livres sans match
- 🔴 **count_diff** : `livres_summary ≠ livres_mongo`
- ⚪ **no_summary** : Pas de summary généré

**Auto-sélection** :
- Priorité badges : no_summary > count_diff > unmatched > perfect
- `EpisodeDropdown.vue` : auto-sélection premier épisode par priorité
- Tests : `Emissions.spec.js` (455 lignes), `test_emission_badge_status.py` (173 lignes)

**UI** :
- Badges visuels dans dropdown épisodes
- Statistiques détaillées par badge dans Emissions.vue

### Commit 45b4771 : Stats dynamiques émissions
**458 lignes** - Calcul dynamique stats badges

**Problème** : Stats statiques obsolètes
**Solution** :
- `stats_service.py` : `get_emission_badge_statistics()` (69 lignes)
- Calcul à la volée depuis MongoDB
- Dashboard : affichage stats badges
- Tests : `test_emissions_badge_stats.py` (244 lignes)

### Commit 5537966 : Update tests stats
**6 lignes** - Mise à jour attentes tests stats service

### Commit 0f226fd : Refactoring livre-par-livre ⭐
**2449 lignes** - **REFACTORING MAJEUR** pour fix doublons matching

**Problème critique** :
- Matching avis-par-avis → un livre MongoDB pouvait être matché plusieurs fois
- Exemple : "Trésors Cachés" matchait "La chaise" par erreur avant que "La Chaises" puisse matcher

**Solution** :
1. **Nouvelle fonction publique** : `match_livres(livres_summary, livres_mongo)`
   - Extrait livres uniques depuis avis : `_extract_unique_books_from_avis()`
   - Matche livre par livre (garantit unicité MongoDB)
   - Retourne `dict[(titre, auteur)] = (livre_oid, phase)`

2. **Nouvelle fonction publique** : `resolve_avis(avis_list, livre_matches, critiques)`
   - Applique les matches aux avis individuels
   - Lookup simple par clé `(titre, auteur)`

3. **Refactoring** : `resolve_entities_with_stats()`
   - Appelle `match_livres()` puis `resolve_avis()`
   - Stats calculées sur livres uniques

**Tests exhaustifs** (classe `TestMatchingLivreParLivre`) :
- `test_should_extract_unique_books_from_avis()` : 24 avis → 9 livres uniques
- `test_should_match_livres_summary_to_mongo()` : Fix cas "Trésors Cachés" vs "La Chaises"
- `test_should_apply_matches_to_all_avis()` : Propagation `livre_oid` à tous avis du même livre
- `test_should_fix_emission_20250309_matching()` : Test intégration émission 09/03/2025

**Documentation** :
- `docs/dev/issue-185-matching-problem-analysis.md` (198 lignes) : analyse complète du problème

**Tests spécialisés** (1560 lignes) :
- `test_avis_extraction_emission_20250309.py` (764 lignes) : cas réel émission
- `test_avis_extraction_typos_section2.py` (292 lignes) : typos Section 2
- `test_avis_extraction_wrong_match_plural.py` (171 lignes) : singulier/pluriel
- `test_avis_extraction_comma_in_title.py` (162 lignes) : virgules dans titres

---

## Phase 4 : Enrichissements et icônes (b47ed32 → 554aeaa)

### Commit b47ed32 : Enrichissement éditeur
**175 lignes** - Ajout champ `editeur` depuis MongoDB

- `avis_extraction_service.py:669-678` : enrichissement dans `resolve_entities_with_stats()`
- Tests : `test_avis_editeur_enrichment.py` (171 lignes)

### Commit 80e86d9 : Migration enrichissement
**324 lignes** - Script migration pour avis existants

- `utils/migrate_enrich_avis_editeur.py` (102 lignes)
- Enrichit avis déjà sauvegardés avec `editeur` depuis MongoDB
- Tests : `test_avis_editeur_migration.py` (222 lignes)

### Commit 554aeaa : Icônes visuelles
**21 lignes** - Cercle bleu (programme) et cœur rouge (coups de cœur)

- `AvisTable.vue` : icônes selon `avis.section`

---

## Phase 5 : Amélioration prompts LLM (19ee1cf → 7fa59df)

### Commit 19ee1cf : Structure prompt Phase 1
**53 lignes** - Clarification prompt LLM

- Meilleure distinction Section 1 (programme) vs Section 2 (coups de cœur)
- Exemples enrichis
- `avis_critiques_generation_service.py`

### Commit 680e35f : Fallback orphan avis_critique_id (Issue #188)
**371 lignes** - Gestion cas dégradé

**Problème** : Émission référence `avis_critique_id` orphelin (document supprimé)
**Solution** :
- Fallback sur `get_emission_by_episode()` dans `mongodb_service.py`
- Tests : `test_api_emissions_endpoints.py` (317 lignes)

### Commit 7fa59df : Simplification règles Phase 1
**46 lignes** - Refactoring prompt pour clarté

- Suppression règles redondantes
- Focus sur règles essentielles

---

## Phase 6 : Gestion doublons et cache (f763fe9 → 808cae4)

### Commit f763fe9 : Update cache lors fusion (Issue #187)
**231 lignes** - Synchronisation cache après merge doublons

- `duplicate_books_service.py` : update `livresauteurs_cache` après fusion
- Remplace `book_id` des livres mergés
- Tests : `test_duplicate_books_service.py` (212 lignes)

### Commit db41c86 : Script fix orphan book_ids (Issue #187)
**331 lignes** - Outil admin pour réparer cache

- `scripts/fix_orphan_book_ids.py`
- Détecte et corrige `book_id` orphelins dans cache
- Utile après suppressions manuelles

### Commit 6863e3e : Auto-sélection par badge
**208 lignes** - Auto-sélection épisode par priorité

- `utils/episodeSelection.js` (48 lignes) : logique auto-sélection
- `GenerationAvisCritiques.vue`, `LivresAuteurs.vue` : utilisation
- Tests : `LivresAuteurs.autoSelect.test.js` (132 lignes)

### Commit 4b73dfe : Fix stats émissions
**111 lignes** - Utiliser `livres_mongo` depuis stats

**Problème** : `livres_mongo` basé sur cache length (incorrect)
**Solution** : Utiliser count depuis stats MongoDB
- Tests : `test_api_avis_endpoints.py` (108 lignes)

### Commit 808cae4 : Clear cache à la sauvegarde
**128 lignes** - Invalidation cache automatique

- Clear `livresauteurs_cache` lors save avis → force refresh
- Tests : `test_api_avis_critiques_endpoints.py` (114 lignes)

---

## Phase 7 : Validation et fixes extraction (47e55ff → 5a0e911)

### Commit 47e55ff : Validation LLM overflow
**23 lignes** - Retry sur space overflow

**Problème** : LLM génère parfois des milliers d'espaces
**Solution** :
- Détection `if " " * 100 in summary`
- Retry avec ValueError
- `avis_critiques_generation_service.py`

### Commit 5a0e911 : Fix header filter
**35 lignes** - Header filter trop agressif

**Problème** : Skip lignes contenant "Auteur" dans commentaires
**Solution** :
- Skip uniquement si `"Auteur" in line AND "Titre" in line AND "Éditeur" in line`
- `avis_extraction_service.py:156-160`
- Tests : `test_avis_extraction_service.py` (30 lignes)

### Commit 23d6803 : Règle un livre par ligne
**5 lignes** - Prompt : un livre par ligne tableau

- Force LLM à ne pas grouper plusieurs livres sur une ligne
- `avis_critiques_generation_service.py`

---

## Phase 8 : Règles non-duplication et noms composés (0c31135 → 0a17ad0)

### Commit 0c31135 : Règle non-duplication
**7 lignes** - Un livre en Section 1 ne doit PAS réapparaître en Section 2

**Problème** : "Lettres à Véra" dupliqué Section 1 ET Section 2
**Solution** :
- Règle prompt : livre programme déjà capturé → ne pas dupliquer en coups de cœur
- `avis_critiques_generation_service.py:323-340`

### Commit d63d562 : Extraction noms avec tirets
**33 lignes** - Fix extraction noms composés sans espaces

**Problème** : "Jean-Louisine", "Jean-Louis" filtrés (pas d'espace)
**Solution** :
- Condition `(" " in nom or "-" in nom)` au lieu de `" " in nom`
- `critiques_extraction_service.py:36`
- Tests : `test_critiques_extraction_service.py` (32 lignes)

### Commit 0a17ad0 : Affichage nom officiel critique
**69 lignes** - UI affiche nom officiel vs variant LLM

**Problème** : Affiche "Jean-Louis" au lieu de "Jean-Louis Ezine"
**Solution** :
- `{{ avis.critique_nom || avis.critique_nom_extrait }}`
- `AvisTable.vue:67,70,163,166`
- Tests : `AvisTable.spec.js` (65 lignes)

---

## Phase 9 : Matching partiel bidirectionnel (session actuelle - non committée)

### Problème identifié
Épisode 20/02/2022 : livre "L'Emprise, la France sous influence" (summary LLM) ne matchait pas avec "L'emprise" (MongoDB) car titre MongoDB tronqué (manque sous-titre). Matchait en Phase 3 au lieu de Phase 2.

### Solution implémentée (TDD)

**Test RED** : `test_emission_20220220_partial_title_matching()` dans `tests/test_avis_extraction_service.py`
- 10 livres summary, 10 livres MongoDB (données réelles après rechargement)
- Attendu : Phase 1=5, Phase 2=2, Phase 3=2, Sans match=1
- Test échouait : "L'Emprise" matchait Phase 3 au lieu de Phase 2

**Fix GREEN** : Modifié `_find_matching_livre_partial()` dans `src/back_office_lmelp/services/avis_extraction_service.py:722-757`

**AVANT** (matching unidirectionnel) :
```python
# Match partiel : le titre extrait est contenu dans le titre du livre
if normalized_titre in normalized_livre_titre:
    return str(livre.get("_id", ""))
```

**APRÈS** (matching bidirectionnel) :
```python
# Match partiel bidirectionnel :
# - Cas 1: le titre extrait est contenu dans le titre MongoDB
# - Cas 2: le titre MongoDB est contenu dans le titre extrait (titre tronqué)
if (normalized_titre in normalized_livre_titre
    or normalized_livre_titre in normalized_titre):
    return str(livre.get("_id", ""))
```

**Cas d'usage couverts** :
1. **Cas original** : "La sirène d'Hollywood" matche "Esther Williams, la sirène d'Hollywood. Mémoires" (titre summary contenu dans MongoDB)
2. **Nouveau cas** : "L'Emprise, la France sous influence" matche "L'emprise" (titre MongoDB tronqué contenu dans summary)

**Résultats** :
- ✅ Tous les 58 tests passent
- ✅ Couverture `avis_extraction_service.py` : 29% → 79%
- ✅ Le livre "L'Emprise" matche en Phase 2 (partiel) au lieu de Phase 3

---

## Cas analysés durant la session

### Épisode 13/11/2016
- Livre "Malraux" (ADPF) en MongoDB mais absent du summary
- **Diagnostic** : Livre orphelin. LLM n'a extrait que "Malraux et les poètes"

### Épisode 31/07/2016
- Livre "Il me semble désormais que Roger est en Italie" en MongoDB mais absent du summary
- **Diagnostic** : Même pattern, livre orphelin

### Épisode 28/09/2014
- 2 livres "Vies imaginaires" en MongoDB (Flammarion et Folio Classique)
- LLM n'a extrait que "Vies imaginaires. De Plutarque à Michon"
- **Diagnostic** : Livre orphelin (doublon légitime éditions différentes)

### Épisode 20/02/2022 (après rechargement)
- 10 livres summary, **12 livres MongoDB**
- **Doublons légitimes** (éditions différentes, URLs Babelio distinctes) :
  - "Regardez-nous danser" : 2 éditions À vue d'œil (URLs `/1853023` et `/1356498`)
  - "Dersou Ouzala" : 2 éditions (URLs `/892000` et `/110329`)
- **Diagnostic** : Système détection doublons fonctionne (ne détecte pas car URLs différentes). Ajout manuel erroné.

### Épisode 25/08/2019
- Summary : "Eden" de Dominique Sabolo → **PAS dans MongoDB** (cause "Sans match: 1")
- MongoDB : "Rouge impératrice" → **PAS dans summary** (livre orphelin)
- Typo : "Ce que je suis" (summary) vs "Ceux que je suis" (MongoDB) → matché Phase 3

---

## Bilan technique

### Statistiques globales
- **27 commits** sur 2 semaines
- **~12 000 lignes** ajoutées (backend + frontend + tests + docs)
- **58 tests** avis_extraction_service.py (100% pass)
- **Couverture** : avis_extraction_service.py 79%

### Fichiers principaux modifiés

**Backend** :
- `src/back_office_lmelp/services/avis_extraction_service.py` : Service extraction/matching (984 lignes)
- `src/back_office_lmelp/services/avis_critiques_generation_service.py` : Service génération LLM
- `src/back_office_lmelp/services/critiques_extraction_service.py` : Extraction noms critiques
- `src/back_office_lmelp/app.py` : Endpoints API avis_critiques
- `src/back_office_lmelp/services/mongodb_service.py` : CRUD avis_critiques
- `src/back_office_lmelp/services/stats_service.py` : Stats badges émissions

**Frontend** :
- `frontend/src/components/AvisTable.vue` : Composant affichage avis
- `frontend/src/components/EpisodeDropdown.vue` : Dropdown avec badges
- `frontend/src/views/Emissions.vue` : Page principale workflow
- `frontend/src/views/GenerationAvisCritiques.vue` : Page génération
- `frontend/src/views/LivresAuteurs.vue` : Page livres/auteurs
- `frontend/src/utils/episodeSelection.js` : Logique auto-sélection

**Tests** :
- `tests/test_avis_extraction_service.py` : Tests extraction/matching (1800+ lignes)
- `tests/test_api_avis_endpoints.py` : Tests API endpoints
- `tests/test_emissions_badge_stats.py` : Tests stats badges
- `tests/test_avis_editeur_enrichment.py` : Tests enrichissement éditeur
- Nombreux tests spécialisés (emission 20250309, typos, pluriels, etc.)

---

## Apprentissages clés

### 1. Matching livre-par-livre vs avis-par-avis
Le refactoring majeur (commit 0f226fd) a résolu un bug critique où un livre MongoDB pouvait être matché plusieurs fois. Le matching livre-par-livre garantit l'unicité.

### 2. Titres MongoDB tronqués
Les titres MongoDB peuvent être tronqués (sans sous-titre) alors que le LLM extrait le titre complet. Le matching bidirectionnel Phase 2 résout ce cas sans Phase 3.

### 3. Doublons légitimes
Des éditions différentes du même livre (grands caractères, éditeurs différents) existent sur Babelio avec URLs distinctes. Le système de détection ne doit pas les détecter.

### 4. Livres orphelins
Livres en MongoDB avec `episodes: ["id"]` mais absents du summary LLM :
- LLM a omis lors extraction
- Ajout manuel erroné
- Livre non discuté dans émission

### 5. Badges et auto-sélection
Système de priorité badges (no_summary > count_diff > unmatched > perfect) améliore workflow utilisateur en sélectionnant automatiquement épisodes nécessitant attention.

### 6. Validation LLM
LLM peut générer contenu malformé (space overflow, doublons). Validation côté backend + retry essentiels.

### 7. Noms composés français
Noms avec tirets sans espaces ("Jean-Louis", "Marie-Claire") doivent être extraits. Pattern `(" " in nom or "-" in nom)`.

### 8. Enrichissement progressif
Enrichir avis avec données MongoDB (`editeur`, `critique_nom`) améliore UX. Migration nécessaire pour données existantes.

---

## Prochaines étapes potentielles

1. **Analyse systématique** : Script pour analyser tous épisodes avec pastilles rouge/jaune
2. **Amélioration prompt LLM** : Réduire omissions de livres
3. **Page admin livres orphelins** : Interface pour gérer livres MongoDB non matchés
4. **Documentation éditions multiples** : Guider utilisateur sur cas légitimes
5. **Commit matching bidirectionnel** : Committer le fix actuel après validation

---

## Références

- **Issue GitHub** : #185
- **Issues liées** : #187 (cache duplicates), #188 (orphan avis_critique_id)
- **Branche** : `185-feat-extraire-des-avis-structures-des-summary-davis_critiques`
- **Commits** : 27 commits (c503df6 → 0a17ad0)
- **Documentation** : `docs/dev/issue-185-matching-problem-analysis.md`
- **Tests** : 58 tests avis_extraction_service.py (100% pass)
- **Couverture** : avis_extraction_service.py 79%
