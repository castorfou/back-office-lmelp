# Issue #161 - Validation Format Markdown pour Extraction de Livres

**Date**: 2025-12-23
**Type**: Bug Fix + Amélioration défensive
**Contexte**: Prévention des échecs silencieux lors de l'extraction de livres

## 🎯 Problème Initial

L'extraction de livres échouait **silencieusement** pour l'épisode du 11/04/2021, retournant une liste vide `[]` avec HTTP 200 (succès) alors que l'avis critique contenait 9 livres.

### Cause Racine

Les regex dans `src/back_office_lmelp/services/books_extraction_service.py` ne matchaient pas le format markdown réel:

**Attendu par le code**:
```markdown
## 1. LIVRES DISCUTÉS AU PROGRAMME
## 2. COUPS DE CŒUR DES CRITIQUES
```

**Présent dans la base** (épisode 11/04/2021):
```markdown
## 1. LIVRES DU PROGRAMME PRINCIPAL
## 2. COUPS DE CŒUR PERSONNELS
```

Résultat: `re.search()` retournait `None`, aucun livre extrait, aucune erreur loguée.

## ✅ Solution Implémentée

### 1. Validation Préalable du Format Markdown

Nouvelle méthode `_validate_markdown_format()` dans `src/back_office_lmelp/services/books_extraction_service.py:169-205`:

```python
def _validate_markdown_format(self, summary: str) -> dict[str, Any]:
    """Valide que le markdown contient les sections attendues."""
    import re

    missing_sections = []

    # Vérifier section obligatoire #1
    if not re.search(r"## 1\. LIVRES DISCUTÉS AU PROGRAMME", summary):
        missing_sections.append("Section '## 1. LIVRES DISCUTÉS AU PROGRAMME' manquante")

    # Vérifier section obligatoire #2
    if not re.search(r"## 2\. COUPS DE CŒUR DES CRITIQUES", summary):
        missing_sections.append("Section '## 2. COUPS DE CŒUR DES CRITIQUES' manquante")

    return {
        "valid": len(missing_sections) == 0,
        "missing_sections": missing_sections,
        "help_url": "/avis_critiques"
    }
```

### 2. Propagation de l'Erreur

Modification de `extract_books_from_reviews()` dans `src/back_office_lmelp/services/books_extraction_service.py:71-77`:

```python
except ValueError as e:
    # Propager les erreurs de validation de format markdown
    # pour que l'utilisateur puisse corriger le problème
    if "Format markdown invalide" in str(e):
        raise
    # Autres ValueError, continuer
    continue
```

**Avant**: Exception silencieuse → retourne `[]`
**Après**: ValueError explicite propagée jusqu'au frontend

### 3. Message d'Erreur Actionnable

`src/back_office_lmelp/services/books_extraction_service.py:111-115`:

```python
raise ValueError(
    f"Format markdown invalide pour l'épisode {episode_oid}. "
    f"Sections manquantes: {', '.join(validation['missing_sections'])}. "
    f"Régénérez le résumé via {validation['help_url']}"
)
```

Message exemple:
```
ValueError: Format markdown invalide pour l'épisode 678ccf10a414f229887781b7.
Sections manquantes: Section '## 1. LIVRES DISCUTÉS AU PROGRAMME' manquante,
Section '## 2. COUPS DE CŒUR DES CRITIQUES' manquante.
Régénérez le résumé via /avis_critiques
```

## 🧪 Tests TDD Implémentés

### Tests de validation

Fichier `tests/test_books_extraction_service.py:491-566`:

1. **test_validate_markdown_format_detects_invalid_headers** (lignes 491-513)
   - Détecte format invalide avec les deux sections incorrectes
   - Vérifie le message d'aide avec lien `/avis_critiques`

2. **test_validate_markdown_format_accepts_valid_headers** (lignes 515-534)
   - Valide le bon format markdown
   - Retourne `valid: True`

3. **test_extract_books_raises_error_on_invalid_markdown_format** (lignes 536-566)
   - Vérifie que l'extraction lève une ValueError explicite
   - Teste la propagation de l'erreur

### Mise à jour des fixtures existantes

**Fichiers modifiés**:
- `tests/test_books_extraction_service.py`: Ajout section "## 2. COUPS DE CŒUR DES CRITIQUES" vide dans les mocks (lignes 31-35, 279-283)
- `tests/test_babelio_cache_enrichment.py`: Idem pour 4 fixtures (lignes 34-37, 100-103, 164-167, 263-266)

**Raison**: Les deux sections markdown sont **obligatoires** (pas optionnelles comme initialement pensé).

## 📊 Impact

### Avant
- Échec silencieux (retourne `[]` avec HTTP 200)
- Utilisateur ne sait pas pourquoi aucun livre n'est trouvé
- Impossible de diagnostiquer le problème

### Après
- Erreur explicite avec message actionnable
- Lien direct vers l'outil de régénération (`/avis_critiques`)
- Fail-fast: détection précoce du problème

## 🔑 Apprentissages Clés

### 1. Fail-Fast vs Silent Failure

**Principe**: Mieux vaut échouer bruyamment que silencieusement.

**Application**:
- Valider les prérequis avant traitement
- Propager les erreurs critiques (ne pas les avaler)
- Messages d'erreur avec solution concrète

### 2. Validation des Formats de Données

Quand on parse des données externes (markdown, JSON, etc.):
1. **Valider le format AVANT le parsing**
2. **Retourner des erreurs explicites** si format invalide
3. **Indiquer comment corriger** (lien vers outil, doc, etc.)

### 3. TDD pour Cas d'Erreur

**Pattern utilisé**:
1. Écrire test avec format invalide (RED)
2. Implémenter validation qui détecte le problème (GREEN)
3. Vérifier que l'erreur est bien propagée (REFACTOR)

**Ne pas oublier**: Les tests d'erreur sont aussi importants que les tests de succès.

### 4. Mocks Basés sur Données Réelles

**Erreur initiale**: Les mocks de tests n'avaient qu'une seule section markdown.

**Correction**: Tous les mocks ont maintenant les deux sections (même vides) pour refléter le format réel attendu.

**Leçon**: Toujours baser les mocks sur la structure réelle des données, pas sur des suppositions.

## 🔧 Fichiers Modifiés

### Code Source
- `src/back_office_lmelp/services/books_extraction_service.py:169-205`: Nouvelle méthode `_validate_markdown_format()`
- `src/back_office_lmelp/services/books_extraction_service.py:71-77`: Propagation ValueError
- `src/back_office_lmelp/services/books_extraction_service.py:108-115`: Validation avant extraction

### Tests
- `tests/test_books_extraction_service.py`: 3 nouveaux tests + mise à jour 2 fixtures
- `tests/test_babelio_cache_enrichment.py`: Mise à jour 4 fixtures

## 📈 Métriques

- **Tests ajoutés**: 3 (validation format)
- **Tests mis à jour**: 6 (fixtures corrigées)
- **Coverage**: 92% pour `books_extraction_service.py` (+8%)
- **Tous les tests passent**: ✅ 722/722

## 🚀 Utilisation

### Pour les Utilisateurs

Si vous voyez cette erreur:
```
Format markdown invalide pour l'épisode XXX.
Régénérez le résumé via /avis_critiques
```

**Solution**:
1. Aller sur l'URL `/avis_critiques` (front-office)
2. Régénérer le résumé pour cet épisode
3. Les livres seront alors correctement extraits

### Pour les Développeurs

Toute modification du format markdown des résumés doit:
1. Mettre à jour les regex dans `_validate_markdown_format()`
2. Ajouter des tests avec l'ancien ET le nouveau format
3. Documenter le changement dans les release notes

## 🔗 Références

- **Issue GitHub**: #161
- **Épisode problématique**: 11/04/2021 (ID: `678ccf10a414f229887781b7`)
- **Issue liée**: #160 (race condition frontend qui a permis de détecter ce bug)

## 💡 Principe de Design

**"Make wrong states unrepresentable"**

Au lieu de permettre un état invalide (format incorrect → extraction silencieuse → liste vide), on rend cet état **impossible** en validant le format dès le début et en échouant explicitement si invalide.

Ce pattern est applicable partout où on consomme des données externes dont le format peut varier.
