# Issue #224 — Bug: "Quatre jours" ne retourne pas l'émission du 07/12/2025

## Problème

La recherche "Quatre jours" retournait le livre mais pas l'émission du 07/12/2025.
La recherche "jours" (sous-mot) retournait bien l'émission.

## Root cause identifiée

`search_emissions()` dans `src/back_office_lmelp/services/mongodb_service.py` cherchait dans les champs **non-canoniques** de la collection `avis` :
- `livre_titre_extrait` — extrait LLM, peut différer du titre Babelio
- `auteur_nom_extrait` — extrait LLM
- `editeur_extrait` — extrait LLM

Pour ce livre, le LLM avait extrait **"4 jours sans ma mère"** (chiffre) dans `livre_titre_extrait`, alors que `livres.titre` (source Babelio canonique) est **"Quatre jours sans ma mère"** (lettres). La regex `Quatre jours` ne matchait donc pas `4 jours`.

## Sources de vérité canoniques (à respecter pour les futures implémentations)

| Données | Collection | Champ | Notes |
|---------|------------|-------|-------|
| Titre livre | `livres` | `titre` | Source Babelio |
| Éditeur | `livres` | `editeur` | Source Babelio |
| Nom auteur | `auteurs` | `nom` | Source Babelio |
| Commentaire critique | `avis` | `commentaire` | Source LLM (canonique pour les avis) |
| Lien livre→avis | `avis` | `livre_oid` | String → `livres._id` ObjectId |
| Lien émission→avis | `avis` | `emission_oid` | String → `emissions._id` ObjectId |

**Champs NON canoniques dans `avis`** (ne jamais utiliser pour recherche/matching) :
- `livre_titre_extrait`, `auteur_nom_extrait`, `editeur_extrait`

## Fix appliqué

Refactorisation complète de `search_emissions()` — algorithme en 3 passes parallèles avec union par `_id` :

```python
# Pass 1: avis dont le commentaire matche (direct, canonique)
avis.find({"commentaire": regex_query})

# Pass 2: livres dont titre/éditeur matche → avis liés via livre_oid
matching_livres = livres.find({"$or": [{"titre": regex_q}, {"editeur": regex_q}]})
livre_ids_str = [str(l["_id"]) for l in matching_livres]  # ObjectId → String
avis.find({"livre_oid": {"$in": livre_ids_str}})

# Pass 3: auteurs dont le nom matche → livres liés → avis liés
matching_auteurs = auteurs.find({"nom": regex_q})
for auteur in matching_auteurs:
    auteur_livres = livres.find({"auteur_id": auteur["_id"]})  # ObjectId → ObjectId (direct)
    avis.find({"livre_oid": {"$in": [str(l["_id"]) for l in auteur_livres]}})

# Union par avis._id pour déduplication
```

## Types MongoDB critiques (rappel MEMORY.md)

- `avis.livre_oid` → **String**
- `livres._id` → **ObjectId** → convertir avec `str(livre["_id"])`
- `livres.auteur_id` → **ObjectId** → pas de conversion pour `auteurs._id` (même type)
- `avis.emission_oid` → **String** → convertir avec `ObjectId(oid)` pour `emissions._id`

## Fichiers modifiés

- `src/back_office_lmelp/services/mongodb_service.py` — méthode `search_emissions()` (~lignes 1406–1605)
- `tests/test_api_search_emissions.py` — 4 nouveaux tests + adaptation des 7 tests existants

## Pattern de test adapté (multi-appels à find)

Avec la nouvelle implémentation, `avis_collection.find()` est appelé plusieurs fois.
**Ne plus utiliser `return_value` pour les mocks `avis_collection.find`** → utiliser `side_effect` :

```python
def avis_find_side_effect(query, *args, **kwargs):
    if "commentaire" in query:
        return [avis_doc]  # Pass 1: commentaire search
    if "livre_oid" in query:
        return [avis_doc]  # Pass 2/3: livre_oid filter
    return []

mock_avis_collection.find.side_effect = avis_find_side_effect
```

## Nouveaux tests ajoutés (classe `TestSearchEmissionsCanonicalSources`)

1. `test_search_by_canonical_titre_finds_emission_when_titre_extrait_differs` — reproduit exactement le bug #224
2. `test_search_by_canonical_auteur_nom_finds_emission` — vérifie la recherche via auteurs.nom
3. `test_search_livres_titre_is_queried_not_livre_titre_extrait` — vérifie que livres.find() est appelé avec "titre"
4. `test_search_auteurs_nom_is_queried_not_auteur_nom_extrait` — vérifie que auteurs.find() est appelé avec "nom"
