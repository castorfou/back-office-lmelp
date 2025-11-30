# Issue #88 - Titres tronqués Babelio

**Date**: 2025-11-30
**Commit**: `5dad5db` - fix(Issue #88): afficher titre complet dans modal de validation

## Problème résolu

Les titres Babelio tronqués (se terminant par "...") n'étaient pas remplacés par le titre complet dans le modal de validation. Par exemple, "Le Chemin continue : Biographie de Georges Lambric..." au lieu de "Le Chemin continue : Biographie de Georges Lambrichs".

### Symptômes
- Section "Suggestions Babelio" : affichait le titre complet ✅
- Section "Validation finale (modifiable)" : affichait le titre tronqué ❌

## Causes identifiées

### 1. Backend - Enrichissement incomplet
**Fichier**: `src/back_office_lmelp/services/books_extraction_service.py`

La méthode `_enrich_books_with_babelio()` ajoutait `babelio_url` et `babelio_publisher` lors de l'enrichissement automatique (confidence >= 0.90), mais **oubliait** d'ajouter `suggested_title` et `suggested_author`.

### 2. Frontend - Ordre de priorité incorrect
**Fichier**: `frontend/src/views/LivresAuteurs.vue`

La méthode `validateSuggestion()` utilisait le mauvais ordre de priorité pour pré-remplir le formulaire :

```javascript
// ❌ AVANT (bug)
title: book.suggested_title || suggestion?.title || book.titre
```

Cela utilisait `book.suggested_title` en premier, qui n'existait pas avant le fix backend. Puis en fallback, utilisait `book.titre` (titre original du markdown, potentiellement tronqué).

## Solutions implémentées

### Backend (lignes 341-351)

```python
# ✅ FIX Issue #88: Enrichir suggested_title et suggested_author
# Ces champs sont ESSENTIELS pour que le frontend affiche le titre complet
# dans le modal de validation (LivresAuteurs.vue:validateSuggestion)
if verification.get("babelio_suggestion_title"):
    enriched_book["suggested_title"] = verification["babelio_suggestion_title"]
if verification.get("babelio_suggestion_author"):
    enriched_book["suggested_author"] = verification["babelio_suggestion_author"]
```

### Frontend (lignes 1115-1116)

```javascript
// ✅ APRÈS (fix)
// Issue #88: Utiliser suggestion en PRIORITÉ (même source que l'affichage "Suggestions Babelio")
this.validationForm = {
  author: suggestion?.author || book.suggested_author || book.auteur,
  title: suggestion?.title || book.suggested_title || book.titre,
  publisher: book.editeur || ''
};
```

**Logique de priorité corrigée**:
1. `suggestion?.title` - Provient de `validationSuggestions` (même source que l'affichage "Suggestions Babelio")
2. `book.suggested_title` - Enrichissement backend (nouveau champ ajouté)
3. `book.titre` - Fallback sur titre original du markdown

## Leçons apprises sur les tests

### Test E2E créé mais inutile
Un test E2E (`test_e2e_modal_title_enrichment.py`) a été créé pour :
- Créer un avis_critique dans MongoDB
- Appeler l'API `/api/livres-auteurs`
- Vérifier que `suggested_title` est dans la réponse

**Problème** : Ce test passait GREEN mais ne détectait pas le bug du modal !
- ✅ Teste que l'API retourne `suggested_title`
- ❌ **Ne teste PAS** que le modal utilise correctement ce champ

### Comment le bug a vraiment été trouvé
1. 🖼️ **Screenshot** de l'utilisateur montrant le modal
2. 👁️ **Observation visuelle** : "Suggestions Babelio" OK, mais "Validation finale" KO
3. 🤔 **Question clé** de l'utilisateur : "pourquoi ne pas mettre dans la zone editable la suggestion qu'on affiche a l'ecran ?"

### Apprentissage
Pour tester le comportement du modal, il faudrait un **test unitaire Vue** :

```javascript
test('validateSuggestion should prioritize suggestion.title', () => {
  const wrapper = mount(LivresAuteurs)

  const book = {
    auteur: 'Arnaud Villanova',
    titre: 'Le chemin continu',  // Original tronqué
    suggested_title: 'Backend titre',
  }

  wrapper.vm.validationSuggestions.set('key', {
    title: 'Le Chemin continue : Biographie de Georges Lambrichs'  // Prioritaire
  })

  wrapper.vm.validateSuggestion(book)

  // THEN: Le formulaire doit utiliser suggestion.title
  expect(wrapper.vm.validationForm.title).toBe(
    'Le Chemin continue : Biographie de Georges Lambrichs'
  )
})
```

**Conclusion** : Un test E2E backend ne peut pas détecter un bug frontend de logique UI. Les tests unitaires Vue auraient été plus appropriés.

## Correction manuelle MongoDB

3 livres avec titres tronqués existaient déjà dans la base (créés avant le fix). Correction manuelle via script Python `scripts/fix_truncated_titles.py` :

1. **Caroline du Saint**
   - ❌ "Un Déni français - Enquête sur l'élevage industrie..."
   - ✅ "Un Déni français : Enquête sur l'élevage industriel"

2. **Elise Goldberg**
   - ❌ "Tout le monde n'a pas la chance d'aimer la carpe f..."
   - ✅ "Tout le monde n'a pas la chance d'aimer la carpe farcie"

3. **Stefan Zweig**
   - ❌ "Découverte inopinée d'un vrai métier - La vieille ..."
   - ✅ "Découverte inopinée d'un vrai métier - La vieille dette"

Vérification post-correction :
```bash
# Plus aucun livre avec titre tronqué
mcp__MongoDB__count --collection livres --query '{"titre": {"$regex": "\\.\\.\\.$"}}'
# Result: 0 documents
```

## Fichiers modifiés

- `src/back_office_lmelp/services/books_extraction_service.py` (lignes 341-351)
- `frontend/src/views/LivresAuteurs.vue` (lignes 1112-1118)
- `scripts/fix_truncated_titles.py` (nouveau, temporaire)

## Tests

- Tests backend : 614 passed ✅
- Tests frontend : 340 passed ✅
- Test E2E supprimé (inutile)
