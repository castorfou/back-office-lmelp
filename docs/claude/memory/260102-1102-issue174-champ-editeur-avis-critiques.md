# Issue #174: Suppression du champ erroné 'editeur' dans collection avis_critiques

**Date**: 2026-01-02
**Branche**: `174-bug-champs-manquants-et-erronés-dans-collection-avis_critiques`
**Statut**: Résolu ✅

## Contexte

Le champ `editeur` était ajouté à tort dans la collection MongoDB `avis_critiques` lors de l'enrichissement Babelio sur la page `/livres-auteurs`. Ce champ appartient **uniquement** à la collection `livres`, pas à `avis_critiques`.

### Origine du bug

**Fichier**: `src/back_office_lmelp/app.py`
**Ligne**: 1379 (avant correction)
**Endpoint**: `POST /api/set-validation-results`

```python
# Code buggy (ligne 1375-1381)
mongodb_service.update_avis_critique(
    request.avis_critique_id,
    {
        "summary": updated_summary,
        "editeur": book_result.babelio_publisher,  # ❌ BUG
    },
)
```

### Flux d'apparition du bug

1. User génère un avis critique → OK (pas de champ editeur)
2. User va sur `/livres-auteurs` pour extraire les livres
3. Frontend appelle `POST /api/set-validation-results`
4. Si Babelio enrichit l'éditeur → Le code met à jour le summary (markdown) ✅
5. PUIS ajoute "editeur" dans `avis_critiques` ❌ (ligne 1379)

### Pourquoi c'est un problème

Le champ `editeur` appartient UNIQUEMENT à la collection `livres`, PAS à `avis_critiques`.

**Schema MongoDB correct**:
- Collection `avis_critiques`: `episode_oid`, `episode_title`, `episode_date`, `summary`, `summary_phase1`, `summary_origin`, `metadata_source`, `created_at`, `updated_at`
- Collection `livres`: `titre`, `auteur`, **`editeur`**, `url_babelio`, `episodes`, etc.

L'éditeur est déjà correctement stocké dans `livres` via `create_book_if_not_exists()` et visible dans le summary markdown de l'avis_critique.

## Solution implémentée

### 1. Correction du code backend (TDD)

#### Étape RED: Créer les tests qui échouent

**Nouveau fichier**: `tests/test_set_validation_results_no_editeur_in_avis_critique.py`

Deux tests critiques:
1. `test_should_not_add_editeur_field_to_avis_critique_when_updating_summary()` - Cas standard avec enrichissement Babelio
2. `test_should_not_add_editeur_even_when_original_publisher_differs()` - Cas avec correction automatique (Hercher → Herscher)

**Assertion critique**:
```python
assert "editeur" not in updated_data, (
    "ERREUR: Le champ 'editeur' ne doit PAS être ajouté à avis_critiques. "
    "L'éditeur appartient à la collection 'livres', pas 'avis_critiques'."
)
```

#### Étape GREEN: Corriger le code

**Fichier modifié**: `src/back_office_lmelp/app.py:1371-1381`

```diff
- # Mettre à jour l'avis_critique avec le summary et l'éditeur mis à jour
+ # Mettre à jour l'avis_critique avec le summary mis à jour
  mongodb_service.update_avis_critique(
      request.avis_critique_id,
      {
          "summary": updated_summary,
-         "editeur": book_result.babelio_publisher,
      },
  )
- print("   ✅ Summary and editeur updated in avis_critique")
+ print("   ✅ Summary updated in avis_critique")
```

#### Étape REFACTOR: Mise à jour d'un test obsolète

**Fichier modifié**: `tests/test_validation_results_api.py:263-340`

Le test `test_red_avis_critique_editeur_should_be_updated_with_babelio_publisher()` attendait le comportement buggy.

**Changements**:
- Inverser l'assertion: de "doit contenir editeur" à "NE DOIT PAS contenir editeur"
- Vérifier que le summary markdown contient l'éditeur enrichi
- Mettre à jour la docstring pour refléter le comportement correct

```diff
- assert "editeur" in update_dict, (
-     "editeur doit être dans l'update de avis_critique"
- )
+ assert "editeur" not in update_dict, (
+     "ERREUR: Le champ 'editeur' ne doit PAS être dans avis_critiques. "
+     "L'éditeur appartient à la collection 'livres', pas 'avis_critiques'."
+ )
```

### 2. Migration des données existantes

**Problème**: 117 documents `avis_critiques` contenaient déjà le champ `editeur` erroné.

**Script créé**: `src/back_office_lmelp/utils/migrate_remove_editeur_from_avis_critiques.py`

#### Point technique important: Connexion MongoDB dans un script standalone

**Problème rencontré**: Lorsqu'on exécute le script directement, `mongodb_service` n'est pas connecté.

**Solution**: S'inspirer du pattern dans `scripts/migration_donnees/migrate_url_babelio.py`:
1. Ajouter `src` au `sys.path` si nécessaire
2. Importer `mongodb_service` depuis `back_office_lmelp.services.mongodb_service`
3. **Appeler `mongodb_service.connect()` AVANT d'utiliser les collections**

```python
from back_office_lmelp.services.mongodb_service import mongodb_service

def remove_editeur_from_avis_critiques() -> None:
    # CRITIQUE: Établir la connexion MongoDB
    if not mongodb_service.connect():
        print("❌ Erreur: Impossible de se connecter à MongoDB")
        return

    collection = mongodb_service.avis_critiques_collection
    # ... reste du code
```

#### Opération MongoDB: $unset

L'opération MongoDB `$unset` est utilisée pour supprimer un champ:

```python
result = collection.update_many(
    {"editeur": {"$exists": True}},  # Filtre: documents avec le champ
    {"$unset": {"editeur": ""}}      # Action: supprimer le champ
)
```

**Avantages**:
- Opération atomique
- Safe (pas besoin d'arrêter le backend)
- Idempotente (peut être réexécutée sans danger)

#### Résultats de la migration

```
📊 117 avis_critiques contiennent le champ 'editeur'

📋 Exemples de documents affectés :
  1. Episode: Les nouvelles pages de Gaël Faye..., editeur: P.O.L.
  2. Episode: Rentrée littéraire avec Alice Zeniter..., editeur: Éditions des Équateurs
  3. Episode: Les romans de Kamel Daoud..., editeur: Gallimard

🔧 Suppression du champ 'editeur' dans 117 documents...
✅ 117 documents mis à jour
✅ Migration réussie : plus aucun champ 'editeur' dans avis_critiques
```

**Vérification post-migration**:
```bash
mcp__MongoDB__count --database "masque_et_la_plume" --collection "avis_critiques" --query '{"editeur": {"$exists": true}}'
# Result: Found 0 documents
```

## Fichiers modifiés

### Code de production
1. `src/back_office_lmelp/app.py:1371-1381` - Suppression de la ligne ajoutant `editeur` dans `avis_critiques`

### Tests
1. `tests/test_set_validation_results_no_editeur_in_avis_critique.py` - **Nouveau**: 2 tests TDD critiques
2. `tests/test_validation_results_api.py:263-340` - Mise à jour du test obsolète

### Migration
1. `src/back_office_lmelp/utils/migrate_remove_editeur_from_avis_critiques.py` - **Nouveau**: Script de nettoyage des données

## Vérifications effectuées

✅ Tests backend passent (pytest)
✅ Linting passe (ruff check)
✅ Type checking passe (mypy)
✅ Formatage correct (ruff format)
✅ Migration exécutée avec succès (117 documents nettoyés)
✅ Vérification MongoDB: 0 documents avec champ `editeur` dans `avis_critiques`

## Tests existants qui couvrent le fix

- `test_babelio_publisher_persistence.py` - Vérifie que `editeur` va dans `livres`, pas `avis_critiques`
- `test_summary_actually_updated_with_babelio_publisher.py` - Vérifie mise à jour du summary markdown
- `test_set_validation_results_summary_update.py` - Tests de l'endpoint de validation

## Apprentissages clés

### 1. Séparation des concerns MongoDB

**Principe**: Chaque collection a sa responsabilité.

- `livres`: Données bibliographiques (titre, auteur, **éditeur**, ISBN, etc.)
- `avis_critiques`: Avis critiques d'épisodes (summary, metadata, dates)
- `episodes`: Données épisodes (titre, date, URL, etc.)

**Anti-pattern**: Mélanger les données de différentes collections (ex: ajouter `editeur` dans `avis_critiques`).

**Bonne pratique**: L'information de l'éditeur enrichie par Babelio doit être:
- ✅ Stockée dans `livres` via `create_book_if_not_exists()`
- ✅ Visible dans le summary **markdown** de l'avis_critique
- ❌ JAMAIS ajoutée comme champ direct dans `avis_critiques`

### 2. Pattern de connexion MongoDB dans scripts standalone

**Problème**: `mongodb_service` est un singleton global mais non connecté par défaut.

**Solution** (pattern de `migrate_url_babelio.py`):
```python
# 1. Import du service
from back_office_lmelp.services.mongodb_service import mongodb_service

# 2. Connexion AVANT utilisation
if not mongodb_service.connect():
    print("❌ Erreur: Impossible de se connecter à MongoDB")
    return

# 3. Utilisation des collections
collection = mongodb_service.avis_critiques_collection
```

**CRITIQUE**: Ne jamais supposer que `mongodb_service` est déjà connecté dans un script standalone.

### 3. MongoDB $unset pour suppression de champs

**Opération**: Supprimer un champ de documents existants.

```python
collection.update_many(
    {"field": {"$exists": True}},  # Filtre
    {"$unset": {"field": ""}}      # Suppression
)
```

**Avantages**:
- Atomique et safe
- Idempotente
- Peut tourner avec backend actif

### 4. TDD pour corrections de bugs

**Pattern recommandé**:

1. **RED**: Écrire test qui vérifie comportement correct (échoue car bug existe)
2. **GREEN**: Corriger le code pour faire passer le test
3. **REFACTOR**: Mettre à jour tests obsolètes qui attendaient le comportement buggy

**Exemple ici**:
- Nouveau test: `test_should_not_add_editeur_field_to_avis_critique_when_updating_summary()` échoue ❌
- Fix: Supprimer ligne 1379 → test passe ✅
- Refactor: Inverser assertion dans `test_red_avis_critique_editeur_should_be_updated_with_babelio_publisher()`

### 5. Gestion des tests obsolètes

**Situation**: Un test attend le comportement buggy.

**Choix**:
- ❌ Supprimer le test (perte de coverage)
- ✅ **Inverser le test** pour vérifier le comportement correct

**Avantages**:
- Garde le coverage de l'endpoint
- Documente le changement de comportement
- Prévient les régressions futures

**Exemple**:
```python
# Avant (attendait le bug)
assert "editeur" in update_dict

# Après (vérifie le fix)
assert "editeur" not in update_dict, (
    "ERREUR: Le champ 'editeur' ne doit PAS être dans avis_critiques."
)
```

## Prévention des régressions futures

### Tests critiques ajoutés

1. **Cas standard** (`test_should_not_add_editeur_field_to_avis_critique_when_updating_summary`)
   - Livre avec `babelio_publisher` enrichi par Babelio
   - Vérifie que `editeur` n'est PAS ajouté à `avis_critiques`
   - Vérifie que `summary` est bien mis à jour

2. **Cas avec correction automatique** (`test_should_not_add_editeur_even_when_original_publisher_differs`)
   - Livre où éditeur original diffère de `babelio_publisher` (Hercher vs Herscher)
   - Vérifie que même lors d'une correction auto, `editeur` n'est PAS ajouté
   - Vérifie que la correction est faite dans le markdown

### Documentation inline

Les tests contiennent des docstrings explicites et des messages d'assertion clairs:

```python
assert "editeur" not in updated_data, (
    "ERREUR: Le champ 'editeur' ne doit PAS être ajouté à avis_critiques. "
    "L'éditeur appartient à la collection 'livres', pas 'avis_critiques'."
)
```

Cela facilite la compréhension future et prévient les régressions.

## Impact sur les autres features

### Features qui utilisent `avis_critiques`

- ✅ Génération d'avis critiques (Issue #171) - Pas d'impact
- ✅ Page Émissions (Issue #154) - Pas d'impact
- ✅ Dashboard stats - Pas d'impact

### Features qui utilisent l'éditeur

- ✅ Page `/livres-auteurs` - Éditeur toujours visible dans summary markdown
- ✅ Collection `livres` - Éditeur stocké correctement
- ✅ Enrichissement Babelio - Continue de fonctionner normalement

**Aucune régression** car:
1. Le champ `editeur` dans `avis_critiques` n'était jamais lu par le code
2. L'éditeur reste visible dans le summary (markdown)
3. L'éditeur est toujours stocké dans `livres`

## Commande de migration

Pour référence future, la commande complète de migration:

```bash
PYTHONPATH=/workspaces/back-office-lmelp/src python -m back_office_lmelp.utils.migrate_remove_editeur_from_avis_critiques
```

**Note**: Cette migration a déjà été exécutée avec succès le 2026-01-02.

## Références

- **Issue GitHub**: #174
- **Branche**: `174-bug-champs-manquants-et-erronés-dans-collection-avis_critiques`
- **Plan détaillé**: `.claude/plans/ticklish-mapping-petal.md`
- **Tests ajoutés**: `tests/test_set_validation_results_no_editeur_in_avis_critique.py`
- **Migration script**: `src/back_office_lmelp/utils/migrate_remove_editeur_from_avis_critiques.py`

## Prochaines étapes

1. Vérifier documentation utilisateur/développeur
2. Commit atomique des modifications
3. Vérifier build documentation (mkdocs)
4. Créer Pull Request
5. Merger après revue
