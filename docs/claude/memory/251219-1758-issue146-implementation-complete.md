# Issue #146 - Regroupement cas problématiques Babelio (Implémentation complète)

**Date**: 2025-12-19
**Issue**: #146 - Regrouper les entrées livre + auteur dans les cas problématiques Babelio
**Status**: ✅ Implémentation complète + Bugs corrigés + Validé utilisateur
**Branche**: `146-liaison-babelio-traitement-manuel-de-couple-livre-auteur`

---

## Vue d'ensemble

### Problème initial
Dans l'interface de migration Babelio, lorsqu'un livre ET son auteur sont tous deux problématiques (pas trouvés sur Babelio), ils apparaissent comme **deux entrées séparées** dans la liste des cas à traiter manuellement.

**Exemple concret**:
- Livre "Romance" (Anne Goscinny) → Pas trouvé
- Auteur "Anne Goscinny" → Pas trouvé
→ Apparaissent comme 2 entrées distinctes dans l'interface

### Solution implémentée
**Groupement intelligent** : Détecter quand livre + auteur sont tous deux problématiques et les afficher comme **une seule entrée groupée** avec:
- Icônes distinctives (📚 + 👤)
- Actions adaptées (pas de bouton "Accepter suggestion")
- Traitement simultané des deux entités

---

## Architecture de la solution

### 1. Backend - Détection et groupement (`babelio_migration_service.py`)

#### Flux de traitement

```
get_problematic_cases()
  │
  ├─> Récupérer tous les cas (livres + auteurs)
  │
  ├─> Créer index des cas auteur par auteur_id
  │
  ├─> Pour chaque cas livre:
  │     │
  │     ├─> Vérifier si déjà résolu (babelio_not_found ou url_babelio)
  │     │
  │     ├─> Récupérer auteur_id depuis le document livre
  │     │
  │     ├─> Si auteur aussi problématique:
  │     │     └─> Créer cas groupé (type: "livre_auteur_groupe")
  │     │
  │     └─> Sinon:
  │           └─> Retourner cas livre normal
  │
  └─> Pour chaque cas auteur non groupé:
        └─> Retourner cas auteur normal
```

#### Nouvelles méthodes

**`_create_grouped_case(livre_case, auteur_case)`**:
```python
def _create_grouped_case(
    self, livre_case: dict[str, Any], auteur_case: dict[str, Any]
) -> dict[str, Any]:
    """Crée un cas groupé livre+auteur."""
    return {
        "type": "livre_auteur_groupe",
        "livre_id": livre_case.get("livre_id"),
        "auteur_id": auteur_case.get("auteur_id"),
        "titre_attendu": livre_case.get("titre_attendu"),
        "nom_auteur": auteur_case.get("nom_auteur"),
        "auteur": livre_case.get("auteur"),  # Pour compatibilité
        "raison": f"Livre et auteur non trouvés sur Babelio",
        "timestamp": livre_case.get("timestamp"),
        # ... autres champs
    }
```

**`_serialize_case(case)`**:
```python
def _serialize_case(self, case: dict[str, Any]) -> dict[str, Any]:
    """Sérialise un cas en convertissant ObjectId et datetime en strings."""
    serializable_case = {}
    for key, value in case.items():
        if isinstance(value, ObjectId):
            serializable_case[key] = str(value)
        elif isinstance(value, datetime):
            serializable_case[key] = value.isoformat()
        else:
            serializable_case[key] = value
    return serializable_case
```

#### Tri des résultats
Les cas sont triés par priorité:
1. Cas groupés (`livre_auteur_groupe`)
2. Cas livres seuls
3. Cas auteurs seuls

---

### 2. Frontend - Affichage adaptatif (`BabelioMigration.vue`)

#### Template conditionnel

**Affichage du header**:
```vue
<template v-if="cas.type === 'livre_auteur_groupe'">
  <h3>📚 {{ cas.titre_attendu }} + 👤 {{ cas.nom_auteur }}</h3>
  <span class="author grouped-label">Livre et auteur à traiter ensemble</span>
</template>
<template v-else-if="cas.type === 'auteur'">
  <h3>👤 {{ cas.nom_auteur }}</h3>
  <span class="author">{{ cas.nb_livres }} livre(s) lié(s)</span>
</template>
<template v-else>
  <h3>{{ cas.titre_attendu }}</h3>
  <span class="author">{{ cas.auteur }}</span>
</template>
```

#### Actions adaptées

**Pour cas groupés** :
- ✗ Pas sur Babelio
- ✏️ Entrer URL Babelio (du livre)

**Pour cas normaux** :
- ✓ Accepter suggestion (si URL disponible)
- ✗ Pas sur Babelio
- ✏️ Entrer URL Babelio

#### Logique de soumission URL

```javascript
const cas = this.urlPopupCase;

// Pour les cas groupés, toujours traiter comme un livre
// Le backend extraira l'auteur automatiquement
let itemType = 'livre';
let itemId = cas.livre_id;
let itemName = cas.titre_attendu;

// Pour les cas non groupés, utiliser la logique existante
if (cas.type !== 'livre_auteur_groupe') {
  itemType = cas.type || 'livre';
  itemId = cas.type === 'auteur' ? cas.auteur_id : cas.livre_id;
  itemName = cas.type === 'auteur' ? cas.nom_auteur : cas.titre_attendu;
}
```

#### Styles CSS

```css
.case-header .author.grouped-label {
  color: #6f42c1;  /* Violet pour les cas groupés */
  font-weight: 500;
  font-style: normal;
}

.grouped-note {
  display: block;
  margin-top: 8px;
  font-size: 0.9em;
  color: #6f42c1;
}
```

---

## Bugs découverts et corrigés pendant les tests

### Bug 1: Auteur réapparaît après traitement

**Symptôme**: Cas groupé traité → livre disparaît ✅, auteur réapparaît ❌

**Cause**: MongoDB `{"url_babelio": {"$exists": False}}` ne matche pas `url_babelio: null`

**Fix** (`babelio_migration_service.py:304-318`):
```python
result = auteurs_collection.update_one(
    {
        "_id": auteur_id,
        "$or": [
            {"url_babelio": {"$exists": False}},
            {"url_babelio": None},  # FIX: Matche aussi null
        ],
    },
    {
        "$set": {
            "url_babelio": babelio_author_url,
            "updated_at": datetime.now(UTC),
        }
    },
)
```

**Test**: `tests/test_grouped_case_acceptance.py`

---

### Bug 2: Champ `updated_at` non mis à jour

**Symptôme**: URL auteur mise à jour, mais `updated_at` reste à l'ancienne valeur

**Fix**: Ajout de `"updated_at": datetime.now(UTC)` dans le `$set`

**Test**: `tests/test_grouped_case_acceptance.py:102-108`

---

### Bug 3: Titre pollué par nom d'auteur

**Symptôme**: Titre "Romance" → "Romance - Anne Goscinny" après scraping

**Cause**: Babelio `og:title` contient `"Romance - Anne Goscinny - Babelio"`

**Fix** (`babelio_service.py:704-727`): Inversion des priorités
```python
# Priorité 1: h1 (contient juste le titre)
h1_tag = soup.find("h1")
if h1_tag:
    return " ".join(h1_tag.get_text().split())

# Priorité 2: og:title (fallback, peut contenir auteur)
og_title_tag = soup.find("meta", property="og:title")
if og_title_tag:
    content = og_title_tag.get("content")
    if content:
        return " ".join(content.replace(" - Babelio", "").split())
```

**Tests**: `tests/test_babelio_title_scraping.py` (nouveau fichier)

---

### Bug 4: Tests cassés par le groupement

**Symptôme**: 3 tests échouaient (assert 0 == 2)

**Cause**: Mocks sans champ `"type": "livre"`

**Fix** (`tests/test_babelio_migration_service.py`): Ajout du champ type dans tous les mocks

---

## Tests créés

### 1. `test_problematic_cases_grouping.py` (nouveau)

**Tests de groupement**:
- `test_get_problematic_cases_should_group_book_and_author_when_both_problematic()`
- `test_get_problematic_cases_should_not_group_when_only_book_is_problematic()`
- `test_get_problematic_cases_should_handle_mixed_cases()`

### 2. `test_grouped_case_acceptance.py` (nouveau)

**Test d'acceptation du cas groupé**:
- `test_accept_suggestion_should_remove_both_book_and_author_from_problematic_cases()`

Vérifie que:
- Le livre est supprimé de `problematic_cases`
- L'auteur est AUSSI supprimé
- Le champ `updated_at` est mis à jour

### 3. `test_babelio_title_scraping.py` (nouveau)

**Tests de scraping de titre**:
- `test_fetch_full_title_should_return_clean_title_without_author_name()`
- `test_fetch_full_title_should_handle_og_title_fallback_when_h1_missing()`

---

## Fichiers modifiés

### Backend
- `src/back_office_lmelp/services/babelio_migration_service.py` (+165 lignes)
  - Logique de groupement
  - Méthodes `_create_grouped_case()` et `_serialize_case()`
  - Fixes bugs MongoDB

- `src/back_office_lmelp/services/babelio_service.py` (+54 lignes)
  - Fix priorité sélecteurs scraping (h1 > og:title)

### Frontend
- `frontend/src/views/BabelioMigration.vue` (+137 lignes)
  - Template conditionnel par type
  - Actions adaptées
  - Styles CSS pour cas groupés

### Tests
- `tests/test_problematic_cases_grouping.py` (nouveau, 249 lignes)
- `tests/test_grouped_case_acceptance.py` (nouveau, 118 lignes)
- `tests/test_babelio_title_scraping.py` (nouveau, 103 lignes)
- `tests/test_babelio_migration_service.py` (+9 lignes, fixes)

**Total**: +281 lignes, -84 lignes

---

## Patterns et apprentissages

### 1. MongoDB - Null vs $exists

**Problème**: `{"field": {"$exists": False}}` ne matche pas `field: null`

**Solution systématique**:
```python
{
    "$or": [
        {"field": {"$exists": False}},
        {"field": None}
    ]
}
```

### 2. MongoDB - Timestamps systématiques

**Toujours** mettre à jour `updated_at` dans les `$set`:
```python
{
    "$set": {
        "data": new_value,
        "updated_at": datetime.now(UTC),  # Obligatoire
    }
}
```

### 3. Web Scraping - Sélecteurs fiables

**Priorité**:
1. Sélecteurs sémantiques simples (`<h1>`, `<title>`)
2. Meta tags génériques (`og:title`)

Les meta tags peuvent contenir des métadonnées enrichies pour les réseaux sociaux.

### 4. Testing - Mocks réalistes

**Toujours** baser les mocks sur des données MongoDB réelles:
1. Vérifier: `db.collection.findOne()`
2. Copier la structure exacte
3. Inclure tous les champs requis par la logique métier (`type`, etc.)

### 5. TDD Incrémental

**Workflow appliqué** pour chaque bug:
1. RED: Test qui échoue (message clair)
2. GREEN: Implémentation minimale
3. REFACTOR: (si nécessaire)

### 6. Frontend - Template conditionnel

**Pattern Vue.js** pour affichage multi-types:
```vue
<template v-if="item.type === 'type1'">...</template>
<template v-else-if="item.type === 'type2'">...</template>
<template v-else>...</template>
```

---

## Statistiques finales

- **Tests totaux**: 744 passed, 22 skipped ✅
- **Coverage**: 77%
- **Ruff**: ✅ OK
- **MyPy**: ✅ OK
- **Validation utilisateur**: "tout fonctionne" ✅

---

## Commandes clés

### Investigation HTML
```bash
python3 << 'EOF'
from bs4 import BeautifulSoup
# ... inspecter og:title vs h1
EOF
```

### Tests
```bash
# Tests spécifiques
PYTHONPATH=/workspaces/back-office-lmelp/src python -m pytest \
  tests/test_problematic_cases_grouping.py \
  tests/test_grouped_case_acceptance.py \
  tests/test_babelio_title_scraping.py -v

# Tous les tests
PYTHONPATH=/workspaces/back-office-lmelp/src python -m pytest tests/ -v
```

### Lint et typecheck
```bash
ruff check . --output-format=github
mypy src/
```

---

## Impact utilisateur

### Avant
- ❌ Livre + auteur = 2 entrées séparées
- ❌ Confusion sur le traitement à effectuer
- ❌ Risque d'oublier de traiter l'auteur
- ❌ Timestamps incorrects
- ❌ Titres pollués

### Après
- ✅ Livre + auteur = 1 entrée groupée claire
- ✅ Actions adaptées (pas de suggestion pour groupés)
- ✅ Traitement simultané garanti
- ✅ Timestamps à jour
- ✅ Titres propres

---

## Leçons clés

1. **MongoDB null handling**: Toujours tester `$exists: False` ET `null`
2. **Web scraping**: Ne jamais supposer, toujours vérifier contenu réel
3. **TDD**: Bugs en production = excellents tests de régression
4. **Mocks**: Structure exacte des données réelles obligatoire
5. **Timestamps**: Mettre à jour `updated_at` systématiquement
6. **Frontend conditionnel**: `v-if`/`v-else-if` pour types multiples

---

## Prochaines étapes

1. ✅ Tests validés
2. ✅ Validation utilisateur
3. ⏳ Commit et push
4. ⏳ Pull request
5. ⏳ CI/CD validation
6. ⏳ Merge vers main
