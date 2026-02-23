# Issue #226 — Doublon critique Éric Neuhoff (fix accent matching)

## Problème
Deux entrées critiques pour le même critique :
- `"Eric Neuhoff"` (sans accent sur É) → 18 avis
- `"Éric Neuhoff"` (avec accent) → 6 avis

Root cause : `CritiquesExtractionService.normalize_critique_name()` faisait uniquement
`.lower()` + strip whitespace, sans supprimer les accents.
→ `"eric neuhoff" != "éric neuhoff"` → nouvelle entrée créée au lieu de matcher l'existante.

## Fix appliqué

### 1. `src/back_office_lmelp/services/critiques_extraction_service.py`
Remplacement de `normalize_critique_name()` :
```python
# Avant (bug)
def normalize_critique_name(self, name: str) -> str:
    normalized = re.sub(r"\s+", " ", name.strip())
    return normalized.lower()

# Après (fix)
from back_office_lmelp.utils.text_utils import normalize_for_matching

def normalize_critique_name(self, name: str) -> str:
    return normalize_for_matching(name)  # accents, ligatures, tirets, apostrophes
```

### 2. `tests/test_critiques_extraction_service.py`
Test TDD ajouté : `test_find_matching_critique_accent_insensitive`
→ vérifie que "Eric Neuhoff" matche "Éric Neuhoff"

### 3. `scripts/merge_critique_doublon_eric_neuhoff.py`
Script one-shot de migration (déjà exécuté) :
- Migré 18 avis de `"Eric Neuhoff"` (695433bc...) → `"Éric Neuhoff"` (695679b0...)
- Supprimé le doublon `"Eric Neuhoff"` de la collection `critiques`
- `avis.critique_oid` est de type **String** (pas ObjectId) → comparaison directe

## Corrections bonus (données MongoDB)
10 avis avec `critique_oid: null` corrigés manuellement :
- `"Jean-Louis"` (5) → Jean-Louis Ezine (`694f1daa...`)
- `"Olivia"` (4) → Olivia de Lamberterie (`694f1d9a...`)
- `"Antoine"` (1) → Patricia Martin (`694eb742...`) — transcription LLM bugguée

## Patterns à retenir
- **Toujours utiliser `normalize_for_matching()`** pour comparer des noms de critiques
- `avis.critique_oid` = String (pas ObjectId) — vérification via `db.avis.find({"critique_oid": str_id})`
- Les summaries LLM peuvent contenir des noms partiels ("Jean-Louis", "Olivia", "Antoine")
  → identifier par déduction (les autres critiques de l'épisode sont connus)

## Autres doublons potentiels détectés (futures issues)
- `"Nelly Kaprielian"` (24 avis, 694f1c88...) vs `"Nelly Kapriélian"` (275 avis, 694f1d6a...)
- `"Nicolas Destiendorf"` (12) vs `"Nicolas Destiendorv"` (6) — variante OCR/LLM
