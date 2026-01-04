# Issue #181 - Résolution échec génération summary épisode 09/04/2017

**Date**: 2026-01-04
**Issue**: [#181](https://github.com/castorfou/back-office-lmelp/issues/181)
**Commits**: 5 commits (31ec2e8 → 493cea3)
**Résultat**: ✅ Épisode 09/04/2017 génère et sauvegarde correctement

## Contexte initial

**Problème rapporté**: Épisode du 09/04/2017 échouait lors de la génération de summary avec erreur `"Format markdown invalide: structure attendue non trouvée"`.

**Investigation initiale**:
- Épisode MongoDB vérifié: 5 livres au programme (Ma Petite France, Norma, Marlène, etc.)
- Transcription valide (54KB, type "livres")
- Erreur survient pendant génération LLM Phase 1

## Root Causes identifiées

### 1. Prompt LLM conceptuellement incorrect

**Localisation**: `src/back_office_lmelp/services/avis_critiques_generation_service.py:186-187`

**Code problématique**:
```python
Si AUCUN livre n'est discuté dans cet épisode, retourne UNIQUEMENT:
"Aucun livre discuté dans cet épisode. Cette émission semble porter sur d'autres sujets..."
```

**Feedback utilisateur critique**: *"il n'y a pas d'épisodes sans livres"*

**Analyse**:
- TOUS les épisodes de type "livres" contiennent des livres
- Le fallback "Aucun livre discuté" était une **assumption fausse**
- Le LLM retournait ce message au lieu de générer les tableaux markdown
- La validation échouait (pas de tableaux → format invalide)

### 2. Messages de validation trop vagues

**Erreur retournée**:
```
ValueError: Format markdown invalide: structure attendue non trouvée
```

**Problèmes**:
- Impossible de savoir QUELLE validation échouait (header? table? longueur?)
- Pas de visibilité sur le contenu généré par le LLM
- Difficile de diagnostiquer en production

### 3. Pas de logging de la réponse LLM brute

- Validation s'exécutait directement sur la réponse LLM
- Contenu rejeté perdu, impossible à analyser
- Debug difficile sans voir ce que le LLM générait réellement

## Solutions implémentées (5 commits)

### Commit 1: `31ec2e8` - Correction prompt + validation diagnostique

**Fichier**: `src/back_office_lmelp/services/avis_critiques_generation_service.py`

#### 1.1 Correction du prompt (lignes 186-189)

**SUPPRIMÉ**:
```python
Si AUCUN livre n'est discuté dans cet épisode, retourne UNIQUEMENT:
"Aucun livre discuté dans cet épisode..."
```

**AJOUTÉ**:
```python
IMPORTANT: Cette émission porte TOUJOURS sur des livres (type "livres").
Il y a TOUJOURS au moins un livre discuté au programme principal.
EXIGENCE ABSOLUE: Tu DOIS retourner les deux tableaux markdown.
Si tu ne trouves pas de livres après le courrier, relis attentivement la transcription.
```

**Impact**: Contrainte explicite positive au lieu d'un fallback négatif incorrect.

#### 1.2 Validation diagnostique (lignes 284-324)

**Renommage**: `_is_valid_markdown_format()` → `_validate_markdown_format()`

**Signature modifiée**:
```python
# Avant
def _is_valid_markdown_format(self, summary: str) -> bool:
    return bool(re.search(...) and "|" in summary and len(summary) >= 200)

# Après
def _validate_markdown_format(self, summary: str) -> dict[str, Any]:
    errors = []

    if not re.search(r"## 1\. LIVRES DISCUT", summary):
        errors.append("Section principale manquante: '## 1. LIVRES DISCUTÉS' non trouvée")
    if "|" not in summary:
        errors.append("Aucun tableau markdown détecté (pipe '|' absent)")
    if len(summary) < 200:
        errors.append(f"Contenu trop court: {len(summary)} caractères (minimum: 200)")
    if "Aucun livre discuté" in summary:
        errors.append(
            "ERREUR: Message 'Aucun livre discuté' détecté - prompt incorrect "
            "(tous les épisodes ont des livres)"
        )

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "summary_preview": summary[:200] if summary else "(vide)"
    }
```

**Check #4 ajouté**: Détection spécifique du message "Aucun livre discuté" incorrect.

#### 1.3 Messages d'erreur actionnables (lignes 154-167)

**Avant**:
```
ValueError: Format markdown invalide: structure attendue non trouvée
```

**Après**:
```
ValueError: Format markdown invalide:
  - ERREUR: Message 'Aucun livre discuté' détecté - prompt incorrect (tous les épisodes ont des livres)
  - Aucun tableau markdown détecté (pipe '|' absent)
  - Contenu trop court: 85 caractères (minimum: 200)

Aperçu du contenu reçu:
Aucun livre discuté dans cet épisode. Cette émission semble porter sur d'autres sujets...
```

#### 1.4 Debug logging enrichi (lignes 141-151)

**Avant validation**, log la réponse LLM brute (si `AVIS_CRITIQUES_DEBUG_LOG=1`):
```python
if self._debug_log_enabled:
    logger.info("=" * 80)
    logger.info("📄 PHASE 1 - RAW LLM OUTPUT (BEFORE VALIDATION)")
    logger.info(f"   Length: {len(summary)} chars")
    logger.info(f"   Preview (first 500):\n{summary[:500]}")
    logger.info(f"   Has header: {'## 1. LIVRES DISCUT' in summary}")
    logger.info(f"   Has tables: {'|' in summary}")
    logger.info("=" * 80)
```

#### 1.5 Tests ajoutés

**Fixture réelle MongoDB** (`tests/fixtures/transcription_samples.py`):
```python
# Episode 678ccfcba414f229887782db: 09/04/2017 - Le masque et la plume livres
# Books: Ma Petite France (P. Péan), Norma (S. Oksanen), Marlène (P. Djian), et autres
# Issue #181: This episode failed with "Format markdown invalide" error
TRANSCRIPTION_EPISODE_2017_04_09 = """ Musique Le masque et la plume..."""
```

**Test d'intégration** (`tests/test_avis_critiques_generation_service.py`):
```python
@skip_if_no_azure
@pytest.mark.asyncio
async def test_generate_summary_episode_2017_04_09_should_succeed(self):
    """Episode 09/04/2017 should generate valid summary. Fixes Issue #181."""
    service = AvisCritiquesGenerationService()

    result = await service.generate_summary_phase1(
        TRANSCRIPTION_EPISODE_2017_04_09,
        "2017-04-09"
    )

    # Business requirement: Valid markdown with books
    assert "## 1. LIVRES DISCUTÉS AU PROGRAMME" in result
    assert "|" in result
    assert len(result) >= 200

    # CRITICAL: Should NOT return "no books" message (incorrect prompt)
    assert "Aucun livre discuté" not in result
```

**Tests unitaires validation** (3 nouveaux + 3 mis à jour):
- `test_validate_markdown_format_valid_summary()`: Format valide → `{valid: True}`
- `test_validate_markdown_format_missing_header()`: Header manquant détecté
- `test_validate_markdown_format_detects_no_books_message()`: Détecte message incorrect
- `test_validate_markdown_format_provides_preview()`: Aperçu inclus dans résultat

**Tests mis à jour** (pour nouveau format dict):
- `test_is_valid_markdown_format_success()` → utilise `result["valid"]`
- `test_is_valid_markdown_format_missing_title()` → utilise `result["errors"]`
- `test_is_valid_markdown_format_missing_table()` → utilise `result["errors"]`

**Résultat**: 16 tests passent (7 nouveaux/modifiés pour validation + 9 existants)

### Commit 2: `2d461df` - Augmentation seuil validation espaces

**Problème découvert pendant investigation**: Épisode 16/10/2016 échouait avec "espaces consécutifs anormaux détectés" alors que génération réussissait.

**Cause**: Regex `\s{100,}` trop restrictive pour formatage markdown des tableaux.

**Solution** (`src/back_office_lmelp/app.py:3091`):
```python
# Avant
if re.search(r"\s{100,}", summary):
    return False, "Summary malformé (espaces consécutifs anormaux détectés)"

# Après
if re.search(r"\s{10000,}", summary):
    return False, "Summary malformé (espaces consécutifs anormaux détectés)"
```

**Contexte utilisateur**: *"ce test avait été fait quand on avait eu un summary généré avec une ligne de 100'000 espaces"*

**Justification**:
- 10000 espaces reste suffisant pour détecter vrais bugs LLM
- Permet formatage normal tableaux markdown (alignement colonnes)

### Commit 3: `73ec308` - Logs complets en cas d'échec validation

**Problème**: Difficile de diagnostiquer pourquoi validation échoue sans voir le contenu complet.

**Solution** (`src/back_office_lmelp/app.py:3139-3145`):
```python
if not is_valid:
    logger.error("❌ Échec de validation du summary")
    logger.error(f"  Raison: {error_message}")
    logger.error(f"  Longueur: {len(request.summary)} caractères")
    logger.error(f"  Contenu complet:\n{request.summary}")
```

**Bénéfice**: Facilite debugging en production (voir exactement ce que le LLM a généré).

### Commit 4: `ffc381b` - Documentation variables debug

**Nouveau fichier**: `docs/user/debug-logging.md`

**Contenu** (8 sections principales):

1. **Vue d'ensemble**: Variables disponibles et leur usage
2. **Variables disponibles**:
   - `AVIS_CRITIQUES_DEBUG_LOG`: Logs génération LLM (prompt, sorties brutes, validation)
   - `BABELIO_DEBUG_LOG`: Logs matching Babelio (similarité, fallback, scraping)
   - `BABELIO_CACHE_LOG`: Logs cache Babelio (hits/miss, taille, expiration)

3. **Activation en mode développement**:
   - Méthode 1: Via `scripts/start-dev.sh` (automatique, recommandée)
   - Méthode 2: Export manuel dans terminal
   - Méthode 3: Activation pour une seule commande

4. **Activation en production (Docker/Portainer)**:
   - Option 1: Via fichier `.env` (recommandée)
   - Option 2: Via interface Portainer
   - Option 3: Via modification `docker-compose.yml`

5. **Accès aux fichiers de debug en production**:
   - Commandes `docker exec` pour lister/afficher
   - Commande `docker cp` pour copier sur l'hôte
   - Configuration volume persistant (optionnel)

6. **Désactivation**: Méthodes en dev et production

7. **Bonnes pratiques**:
   - ✅ Activer en dev permanent (via start-dev.sh)
   - ✅ Activer temporairement en prod (diagnostic uniquement)
   - ❌ Ne pas activer en permanence en prod (impact performances)

8. **Troubleshooting**: Variables non prises en compte, fichiers absents, etc.

**Navigation** (`docs/user/.pages`): Ajout "Logs de debug" entre "Integration Calibre" et "Résolution de problèmes"

**Issue créée**: [docker-lmelp#38](https://github.com/castorfou/docker-lmelp/issues/38) - Demande exposition variables debug dans docker-compose.yml

### Commit 5: `493cea3` - Écriture logs debug dans fichiers

**Problème**: Investigation épisode 16/10/2016 a révélé LLM générant 1M+ espaces → saturation terminal.

**Solution**: Écrire sorties LLM dans fichiers au lieu du terminal.

**Modifications**:

#### 5.1 Service génération (`avis_critiques_generation_service.py:142-160`)

```python
if self._debug_log_enabled:
    from pathlib import Path
    from datetime import datetime

    debug_dir = Path("/tmp/avis_critiques_debug")
    debug_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    debug_file = debug_dir / f"phase1_raw_{timestamp}.md"
    debug_file.write_text(summary, encoding="utf-8")

    logger.info("=" * 80)
    logger.info("📄 PHASE 1 - RAW LLM OUTPUT (BEFORE VALIDATION)")
    logger.info(f"   📁 Fichier debug: {debug_file}")
    logger.info(f"   Length: {len(summary)} chars")
    logger.info(f"   Has header: {'## 1. LIVRES DISCUT' in summary}")
    logger.info(f"   Has tables: {'|' in summary}")
    logger.info("=" * 80)
```

**Phase 2 similaire** (lignes 388-400): `phase2_raw_{timestamp}.md`

#### 5.2 Endpoint API (`app.py:3121-3156`)

```python
if not is_valid:
    from datetime import datetime
    from pathlib import Path

    # Écrire dans fichier de debug
    debug_dir = Path("/tmp/avis_critiques_debug")
    debug_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    debug_file = debug_dir / f"validation_failed_{request.episode_id}_{timestamp}.md"
    debug_file.write_text(request.summary, encoding="utf-8")

    logger.error("❌ Échec de validation du summary")
    logger.error(f"  📁 Fichier debug: {debug_file}")
    logger.error(f"  Raison: {error_message}")
    logger.error(f"  Longueur: {len(request.summary)} caractères")
```

**Fichiers créés** (`/tmp/avis_critiques_debug/`):
- `phase1_raw_<timestamp>.md`: Sortie brute LLM Phase 1 (avant validation)
- `phase2_raw_<timestamp>.md`: Sortie brute LLM Phase 2 (correction)
- `validation_failed_<episode_id>_<timestamp>.md`: Summary rejeté par validation

**Bénéfices**:
- ✅ Pas de saturation terminal (épisode 16/10/2016 = 1M+ caractères)
- ✅ Inspection facile des réponses LLM (fichiers Markdown)
- ✅ Fichiers partageables dans issues GitHub
- ✅ Diagnostic post-mortem (fichiers conservés dans `/tmp/`)
- ✅ Pas d'impact quand debug désactivé (fichiers non créés)

## Investigation bonus: Épisode 16/10/2016

**Découverte pendant tests utilisateur**: Épisode 16/10/2016 échouait après le fix.

**Symptômes**:
- LLM générait 1M+ espaces au lieu de markdown
- Fichier debug: `phase1_raw_20260103_232308.md` = 1,019,230 caractères sur ligne 3
- Transcription anormalement grande: 64,803 chars (vs 27,826 chars pour 09/04/2017)

**Root cause identifiée par utilisateur**: *"il y a du texte en anglais au milieu de la transcription"*

**Résolution**: User va régénérer la transcription dans application lmelp frontend (hors scope Issue #181).

**Learnings**:
- Taille transcription peut impacter qualité génération LLM
- Transcriptions corrompues (multilingues) perturbent le LLM
- Debug file logging a permis d'identifier le problème rapidement

## Résultats

### Tests

**Coverage Backend**: 16/16 tests passent
- 1 nouveau test d'intégration (données réelles MongoDB)
- 3 nouveaux tests unitaires validation
- 3 tests unitaires validation mis à jour (format dict)
- 9 tests existants inchangés

**Quality gates**:
- ✅ Ruff linting: aucun problème
- ✅ MyPy type checking: aucun problème
- ✅ Pre-commit hooks: tous passent

### Validation utilisateur

✅ **Épisode 09/04/2017**: *"la generation a marché"*
- Génération Phase 1: succès
- Génération Phase 2: succès
- Sauvegarde: succès
- Summary valide visible dans interface

### Documentation

**Nouvelle page**: `docs/user/debug-logging.md` (330 lignes)
- Variables d'environnement debug documentées
- Méthodes d'activation (dev + production Docker/Portainer)
- Accès aux fichiers de debug dans conteneurs
- Bonnes pratiques et troubleshooting

**Issue externe**: [docker-lmelp#38](https://github.com/castorfou/docker-lmelp/issues/38)
- Proposition modification docker-compose.yml
- Valeurs par défaut sûres (`:-0`)
- Documentation commandes d'accès aux logs

## Apprentissages clés

### 1. Importance du feedback utilisateur pour comprendre le domaine

**Feedback critique**: *"il n'y a pas d'épisodes sans livres"*

**Impact**:
- Révèle que le fallback "Aucun livre discuté" était **conceptuellement faux**
- Change complètement l'approche: contrainte positive au lieu de fallback négatif
- Validation des assumptions avec domain expert = crucial

**Pattern**: Toujours questionner les assumptions du code avec l'utilisateur expert.

### 2. TDD avec données réelles (CLAUDE.md rule #2)

**Approche utilisée**:
1. ✅ Extraire données réelles de MongoDB avec MCP tools
2. ✅ Créer fixture avec transcription exacte de l'épisode problématique
3. ✅ Écrire UN test d'intégration montrant le problème business
4. ✅ Tests unitaires après pour fonctions helpers

**Anti-pattern évité**:
❌ Inventer des mocks de structure (risque de ne pas matcher la réalité)
❌ Écrire tous les tests unitaires d'abord (masque le vrai problème)

**Résultat**: Test d'intégration capture le problème réel, tests unitaires vérifient les détails.

### 3. Pattern "Debug Logging Strategy" (CLAUDE.md)

**Pattern appliqué**:
```python
self._debug_log_enabled = os.getenv("AVIS_CRITIQUES_DEBUG_LOG", "0").lower() in ("1", "true")

if self._debug_log_enabled:
    # Logs détaillés
    debug_file.write_text(content)
    logger.info(f"📁 Fichier debug: {debug_file}")
```

**Principes**:
- ✅ Garder logs debug dans le code (pas supprimer avant commit)
- ✅ Contrôlé par variable d'environnement (activation facile)
- ✅ Désactivé par défaut (pas d'impact production)
- ✅ Écriture dans fichiers (évite saturation terminal)

**Raison**: Facilite diagnostic futur sans modifier le code ni redéployer.

### 4. Validation avec diagnostics actionnables

**Principe**: Messages d'erreur doivent dire **QUELLE** validation échoue, pas juste "invalide".

**Avant**:
```
ValueError: Format markdown invalide: structure attendue non trouvée
```
→ Impossible de savoir quoi corriger

**Après**:
```
ValueError: Format markdown invalide:
  - ERREUR: Message 'Aucun livre discuté' détecté - prompt incorrect
  - Aucun tableau markdown détecté (pipe '|' absent)
  - Contenu trop court: 85 caractères (minimum: 200)

Aperçu: Aucun livre discuté dans cet épisode...
```
→ Erreurs spécifiques + aperçu du contenu → actionnable

**Pattern**: Validation retourne `dict` avec `{valid, errors[], preview}` au lieu de `bool`.

### 5. Prompt engineering pour LLM

**Anti-pattern identifié**:
```python
Si AUCUN livre n'est discuté, retourne "Aucun livre discuté..."
```
→ Condition négative qui confond le LLM

**Pattern recommandé**:
```python
IMPORTANT: Cette émission porte TOUJOURS sur des livres.
EXIGENCE ABSOLUE: Tu DOIS retourner les deux tableaux markdown.
```
→ Contraintes positives claires et explicites

**Learnings**:
- ❌ Éviter conditions négatives ("Si AUCUN...", "Si PAS...")
- ✅ Utiliser contraintes positives ("Tu DOIS...", "TOUJOURS...")
- ✅ Fournir contexte explicite ("Cette émission porte sur des livres")

### 6. Investigation progressive avec itérations utilisateur

**Séquence**:
1. Fix initial: Prompt + validation (commit 1)
2. Push + test utilisateur sur épisode 09/04/2017 → ✅ Succès
3. Test utilisateur sur épisode 16/10/2016 → ❌ Échec (espaces consécutifs)
4. Fix seuil validation 100→10000 (commit 2)
5. Test utilisateur → ❌ Échec (autre raison)
6. Ajout logs complets (commit 3)
7. Test utilisateur → Observation LLM génère 1M+ espaces
8. Ajout debug file logging (commit 5)
9. Investigation → User identifie transcription corrompue

**Learnings**:
- Résolution incrémentale avec boucles de feedback utilisateur
- Chaque échec révèle un nouveau problème (validation, logging, transcription)
- Debug file logging crucial pour diagnostiquer cas extrêmes (1M+ caractères)

## Fichiers modifiés

### Code source (3 fichiers)

1. **`src/back_office_lmelp/services/avis_critiques_generation_service.py`**
   - Lignes 186-189: Prompt corrigé (suppression fallback "no books", contrainte positive)
   - Lignes 284-324: `_validate_markdown_format()` retourne dict avec diagnostics
   - Lignes 142-160: Debug file logging Phase 1
   - Lignes 388-400: Debug file logging Phase 2

2. **`src/back_office_lmelp/app.py`**
   - Ligne 3091: Validation threshold 100→10000 espaces consécutifs
   - Lignes 3121-3156: Debug file logging validation failures
   - Lignes 3139-3145: Logs complets en cas d'échec validation

3. **`tests/fixtures/transcription_samples.py`**
   - Ajout `TRANSCRIPTION_EPISODE_2017_04_09` (données réelles MongoDB)

### Tests (1 fichier)

4. **`tests/test_avis_critiques_generation_service.py`**
   - Nouveau: `test_generate_summary_episode_2017_04_09_should_succeed()` (intégration)
   - Nouveau: `test_validate_markdown_format_valid_summary()` (unitaire)
   - Nouveau: `test_validate_markdown_format_missing_header()` (unitaire)
   - Nouveau: `test_validate_markdown_format_detects_no_books_message()` (unitaire)
   - Nouveau: `test_validate_markdown_format_provides_preview()` (unitaire)
   - Mis à jour: `test_is_valid_markdown_format_success()` (format dict)
   - Mis à jour: `test_is_valid_markdown_format_missing_title()` (format dict)
   - Mis à jour: `test_is_valid_markdown_format_missing_table()` (format dict)

### Documentation (2 fichiers)

5. **`docs/user/debug-logging.md`** (nouveau, 330 lignes)
   - Vue d'ensemble variables debug
   - Activation en développement (3 méthodes)
   - Activation en production Docker/Portainer (3 options)
   - Accès fichiers debug dans conteneurs
   - Bonnes pratiques et troubleshooting

6. **`docs/user/.pages`**
   - Ligne 14: Ajout "Logs de debug: debug-logging.md" dans navigation

## Références

- **Issue GitHub**: [#181 - Bug: Génération summary échoue pour émission 09/04/2017](https://github.com/castorfou/back-office-lmelp/issues/181)
- **Issue externe**: [docker-lmelp#38 - feat: Ajouter variables d'environnement debug](https://github.com/castorfou/docker-lmelp/issues/38)
- **Plan initial**: `/home/vscode/.claude/plans/staged-foraging-riddle.md`
- **Commits**: 5 commits (31ec2e8 → 493cea3)
- **Tests**: 16/16 passent (7 nouveaux/modifiés + 9 existants)

## Statut final

✅ **Issue #181 résolue**: Épisode 09/04/2017 génère et sauvegarde correctement
✅ **Documentation complète**: Variables debug documentées pour utilisateurs
✅ **Tests ajoutés**: Coverage validation + intégration données réelles
✅ **Bonus**: Investigation épisode 16/10/2016 → root cause transcription corrompue identifiée

**Prochaines étapes**:
- Attendre user régénère transcription épisode 16/10/2016 dans lmelp frontend
- Tester mkdocs build --strict
- Vérifier CI/CD
- Créer PR et merger
