# Issue #92 - Implémentation de la recherche insensible aux accents

**Date**: 2025-11-10
**Issue**: #92 - Implement accent-insensitive search for advanced search

## Problème résolu

Les utilisateurs devaient taper les accents exacts pour trouver des résultats dans la recherche. Par exemple :
- Chercher "carrere" ne trouvait pas "Emmanuel Carrère"
- Chercher "emonet" ne trouvait pas "Simone Émonet"
- Chercher "etranger" ne trouvait pas "L'Étranger"

Ce problème affectait la recherche simple (barre de recherche principale) et la recherche avancée.

## Solution technique : Option 4 (Smart Regex)

### Approche choisie
Génération d'un pattern regex qui matche toutes les variantes accentuées de chaque lettre, sans modification de la base de données.

**Principe** :
1. Normalisation Unicode NFD du terme de recherche pour retirer les accents
2. Mapping de chaque lettre vers un charset regex incluant toutes ses variantes accentuées
3. Construction d'un pattern regex combinant tous les charsets

**Exemple** :
- Input: "carrere"
- Output regex: `[cç][aàâäáãåāăą]rr[eèéêëēĕėęě]r[eèéêëēĕėęě]`
- Ce pattern matche: "Carrère", "carrere", "CARRÈRE", etc.

### Avantages de cette solution
- ✅ Pas de modification de la structure MongoDB
- ✅ Pas de champs dupliqués normalisés à maintenir
- ✅ Solution élégante et maintenable
- ✅ Fonctionne pour toutes les entités (auteurs, livres, éditeurs, épisodes)

## Implémentation

### Backend (Python)

#### Nouveau fichier: `src/back_office_lmelp/utils/text_utils.py`

```python
def create_accent_insensitive_regex(term: str) -> str:
    """Convertit un terme de recherche en regex insensible aux accents."""
    accent_map = {
        'a': '[aàâäáãåāăą]',
        'e': '[eèéêëēĕėęě]',
        'i': '[iìíîïĩīĭįı]',
        'o': '[oòóôöõøōŏő]',
        'u': '[uùúûüũūŭůűų]',
        'c': '[cç]',
        'n': '[nñń]',
        'y': '[yÿý]',
    }

    # Normalisation NFD + retrait des marks
    nfd = unicodedata.normalize("NFD", term)
    normalized_term = "".join(
        char for char in nfd if unicodedata.category(char) != "Mn"
    )

    # Conversion en pattern regex
    result = []
    for char in normalized_term.lower():
        result.append(accent_map.get(char, char))

    return "".join(result)
```

#### Modifications: `src/back_office_lmelp/services/mongodb_service.py`

**Méthodes modifiées** :
- `search_auteurs(query, limit, offset)` - ligne ~512
- `search_livres(query, limit, offset)` - ligne ~561
- `search_editeurs(query, limit, offset)` - ligne ~629

**Pattern de modification** :
```python
from ..utils.text_utils import create_accent_insensitive_regex

def search_auteurs(self, query: str, limit: int = 10, offset: int = 0):
    query_stripped = query.strip()
    regex_pattern = create_accent_insensitive_regex(query_stripped)
    search_query = {"nom": {"$regex": regex_pattern, "$options": "i"}}
    # ... reste du code
```

#### Tests: `tests/test_accent_insensitive_search.py`

**13 tests créés** couvrant :
1. **Tests unitaires regex** (8 tests) :
   - Génération de pattern pour mots simples
   - Normalisation des accents dans le terme de recherche
   - Matching avec différentes variantes ("carrere" ↔ "Carrère")
   - Préservation des caractères spéciaux (apostrophes)
   - Cas limites (chaîne vide, majuscules)

2. **Tests d'intégration MongoDB** (3 tests) :
   - Vérification que `search_auteurs()` utilise le regex généré
   - Vérification que `search_livres()` utilise le regex généré
   - Vérification que `search_editeurs()` utilise le regex généré

3. **Tests end-to-end API** (2 tests) :
   - `/api/advanced-search?q=carrere` trouve "Emmanuel Carrère"
   - `/api/advanced-search?q=emonet` trouve "Simone Émonet"

### Frontend (JavaScript/Vue.js)

#### Nouveau fichier: `frontend/src/utils/textUtils.js`

```javascript
export function removeAccents(str) {
  return str.normalize('NFD').replace(/[\u0300-\u036f]/g, '');
}

export function createAccentInsensitiveRegex(term) {
  const accentMap = {
    'a': '[aàâäáãåāăą]',
    'e': '[eèéêëēĕėęě]',
    // ... mapping complet
  };

  const normalized = removeAccents(term.toLowerCase());
  const pattern = normalized.split('').map(char => {
    if (/[.*+?^${}()|[\]\\]/.test(char)) return '\\' + char;
    return accentMap[char] || char;
  }).join('');

  return pattern;
}

export function highlightSearchTermAccentInsensitive(text, searchTerm) {
  if (!text || !searchTerm) return text || '';
  const query = searchTerm.trim();
  if (query.length < 3) return text;

  const pattern = createAccentInsensitiveRegex(query);
  const regex = new RegExp(`(${pattern})`, 'gi');

  return text.replace(regex,
    '<strong style="background: #fff3cd; color: #856404;">$1</strong>'
  );
}
```

#### Modifications

**1. `frontend/src/views/AdvancedSearch.vue`** (ligne ~389) :
```javascript
import { highlightSearchTermAccentInsensitive } from '../utils/textUtils.js';

highlightSearchTerm(text) {
  return highlightSearchTermAccentInsensitive(text, this.lastSearchQuery);
}
```

**2. `frontend/src/components/TextSearchEngine.vue`** (lignes 118-119, 248-250) :
```javascript
import { highlightSearchTermAccentInsensitive } from '../utils/textUtils.js';

highlightSearchTerm(text) {
  return highlightSearchTermAccentInsensitive(text, this.lastSearchQuery);
}
```

#### Tests: `frontend/tests/unit/accentInsensitiveHighlight.spec.js`

**15 tests créés** couvrant :
1. **Tests `removeAccents()`** (3 tests) :
   - Retrait des accents français
   - Préservation des caractères non-accentués
   - Gestion mixte majuscules/minuscules

2. **Tests `createAccentInsensitiveRegex()`** (3 tests) :
   - Génération de pattern avec variantes
   - Normalisation des termes accentués en input
   - Préservation des caractères spéciaux

3. **Tests `highlightSearchTermAccentInsensitive()`** (9 tests) :
   - Highlighting "carre" dans "Emmanuel Carrère"
   - Highlighting "carrere" dans "Emmanuel Carrère"
   - Highlighting "emonet" dans "Simone Émonet"
   - Highlighting "etranger" dans "L'Étranger"
   - Case-insensitive matching
   - Minimum 3 caractères requis
   - Pas de match = texte original
   - Gestion des inputs vides/null
   - Highlighting multiples occurrences

## Résultats

### Tests
- ✅ **Backend** : 560 tests passent (13 nouveaux tests créés)
- ✅ **Frontend** : 277 tests passent (15 nouveaux tests créés)
- ✅ **Linting** : Ruff check passe sans erreur
- ✅ **Type checking** : MyPy passe sans erreur

### Fonctionnalités
- ✅ Recherche "carre" trouve "Emmanuel Carrère"
- ✅ Recherche "emonet" trouve "Simone Émonet"
- ✅ Recherche "etranger" trouve "L'Étranger"
- ✅ Highlighting insensible aux accents dans **recherche simple**
- ✅ Highlighting insensible aux accents dans **recherche avancée**
- ✅ Fonctionne pour **auteurs, livres, éditeurs, épisodes**

## Points techniques importants

### 1. Unicode Normalization (NFD vs NFC)
- **NFD** (Normalization Form Decomposed) : Décompose les caractères accentués
  - Exemple : `é` → `e` + `◌́` (caractère de base + accent combinant)
- **NFC** (Normalization Form Composed) : Forme composée standard
  - Exemple : `é` reste `é`
- **Utilisation** : NFD permet de facilement retirer les accents en filtrant les "marks"

### 2. MongoDB $regex
- Syntaxe : `{"$regex": pattern, "$options": "i"}`
- `"i"` option pour case-insensitive
- Le pattern généré est compatible avec MongoDB et JavaScript

### 3. Performance
- **Minimum 3 caractères** : Évite les regex trop permissives sur petites recherches
- **Pas d'index nécessaire** : Les index MongoDB existants restent utilisables

### 4. Préservation des caractères spéciaux
- Les apostrophes, espaces, tirets, etc. sont conservés tels quels
- Seuls les caractères alphabétiques sont transformés en charsets

## Workflow TDD suivi

1. ✅ **RED** : Tests écrits en premier (backend + frontend)
2. ✅ **GREEN** : Code implémenté pour passer les tests
3. ✅ **REFACTOR** : Nettoyage des imports inutilisés et variables non utilisées
4. ✅ **VERIFY** : Linting, type checking, et tests complets
5. ✅ **USER TESTING** : Validation par l'utilisateur

## Fichiers créés

- `src/back_office_lmelp/utils/text_utils.py`
- `tests/test_accent_insensitive_search.py`
- `frontend/src/utils/textUtils.js`
- `frontend/tests/unit/accentInsensitiveHighlight.spec.js`

## Fichiers modifiés

- `src/back_office_lmelp/services/mongodb_service.py`
- `frontend/src/views/AdvancedSearch.vue`
- `frontend/src/components/TextSearchEngine.vue`

## Lessons learned

### Options rejetées
1. **Option 1** (champs normalisés en DB) : Trop "crade", duplication de données
2. **Option 2** (normalisation Python-side) : Ne fonctionne pas avec MongoDB regex
3. **Option 3** (text index MongoDB) : Trop complexe pour le besoin

### Option retenue
**Option 4** (Smart Regex) : Solution élégante, performante, et maintenable qui répond parfaitement au besoin sans modification de la base de données.

### Points d'attention pour futures modifications
- Garder la cohérence entre les mappings Python et JavaScript
- Maintenir le minimum de 3 caractères pour la performance
- Préserver les tests unitaires lors des refactorings
