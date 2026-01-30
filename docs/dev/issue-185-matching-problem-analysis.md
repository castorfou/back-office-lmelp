# Issue #185 - Analyse du problème de matching

## Problème identifié

### Symptômes (Émission 09/03/2025)
- 9 livres dans MongoDB
- 10 avis extraits (1 de trop)
- "La Chaises" non matché (`livre_oid=None`)
- Badge 🟡 (unmatched)

### Cause racine

**Approche actuelle** : Matching **avis par avis** séquentiel (24 avis traités un par un)

```python
# ACTUEL: Traitement séquentiel des avis
for avis in avis_list:  # 24 avis
    livre_matched = match_book(avis, all_books)
    if livre_matched:
        avis["livre_oid"] = livre_matched["_id"]
        # ⚠️ Aucun mécanisme pour "réserver" le livre
```

**Conséquence** : Un livre peut être matché plusieurs fois par des avis différents

### Scénario réel reproduit

**Avis #12** : "Trésors Cachés" (2ème avis de 4)
- Titre extrait : "Trésors Cachés" (pluriel)
- Auteur extrait : "Pascal Quignard"
- **Phase 3** (accent-insensitive regex) : Match "La chaise" ❌
  - Regex tolère le "s" final
  - Aucune validation de cohérence auteur/éditeur en Phase 3
  - "La chaise" devient "claimed"

**Avis #23** : "La Chaises" (coup de cœur)
- Titre extrait : "La Chaises" (avec S)
- Auteur extrait : "Jean-Louis Aislin" (faute de frappe)
- **Résultat** : `livre_oid=None`
  - "La chaise" déjà matché par avis #12
  - Phase 1-3 échouent (titre + auteur différents)
  - Phase 4 (fuzzy) pas encore implémentée

## Tests documentant le problème

### Test complet : 24 avis réels
**Fichier** : `tests/test_avis_extraction_emission_20250309.py::test_should_match_all_24_avis_like_real_extraction`

**Résultat** :
```
'Trésors Cachés': 4 avis
  - 3 matchent "Trésor caché" (68e9192d066cb40c25d5d2d9) ✅
  - 1 matche "La chaise" (68e919cd066cb40c25d5d2e3) ❌

'La Chaises': 1 avis
  - livre_oid=None ❌
```

## Solutions proposées

### Solution 1 : Fix rapide - Validation cohérence en Phase 3

**Principe** : Ajouter validation auteur/éditeur en Phase 3

```python
def _match_phase3_accent_insensitive(avis, books):
    """Phase 3 avec validation de cohérence."""
    for book in books:
        if title_matches_accent_insensitive(avis["titre"], book["titre"]):
            # ✅ NOUVEAU: Valider cohérence auteur OU éditeur
            if (
                author_similar(avis["auteur"], book["auteur_nom"])
                or avis["editeur"] == book["editeur"]
            ):
                return book
    return None
```

**Avantages** :
- Fix rapide (1 fonction à modifier)
- Réduit les faux matches de Phase 3

**Inconvénients** :
- Ne résout pas le problème fondamental (matching avis par avis)
- Complexifie la logique de Phase 3

### Solution 2 : Refactoring - Matching livre par livre

**Principe** : Grouper les avis par livre avant le matching

```python
def resolve_entities_v2(avis_list, books, critiques):
    """Nouvelle approche: matching livre par livre."""

    # 1. Grouper les avis par (titre, auteur)
    grouped_avis = {}
    for avis in avis_list:
        key = (avis["livre_titre_extrait"], avis["auteur_nom_extrait"])
        if key not in grouped_avis:
            grouped_avis[key] = []
        grouped_avis[key].append(avis)

    # 2. Matcher chaque groupe de livres (pas chaque avis)
    livre_matches = {}  # (titre, auteur) → livre_oid
    for (titre, auteur), avis_group in grouped_avis.items():
        # Créer un avis "représentatif" du groupe
        repr_avis = {
            "livre_titre_extrait": titre,
            "auteur_nom_extrait": auteur,
            "editeur_extrait": avis_group[0]["editeur_extrait"],
        }
        # Matcher UNE SEULE FOIS
        matched_book = _match_book_multi_phase(repr_avis, books)
        if matched_book:
            livre_matches[(titre, auteur)] = str(matched_book["_id"])

    # 3. Propager le match à tous les avis du groupe
    resolved_avis = []
    for avis in avis_list:
        key = (avis["livre_titre_extrait"], avis["auteur_nom_extrait"])
        avis["livre_oid"] = livre_matches.get(key)
        # Matcher critique (indépendant du livre)
        avis["critique_oid"] = _match_critique(avis, critiques)
        resolved_avis.append(avis)

    return resolved_avis
```

**Avantages** :
- ✅ Un livre ne peut être matché qu'une seule fois
- ✅ Matching plus rapide (9 matchings au lieu de 24)
- ✅ Plus logique métier (on matche des livres, pas des avis)
- ✅ Simplifie la détection de problèmes

**Inconvénients** :
- Refactoring plus important
- Tests existants à adapter

### Solution 3 : Hybrid - Track claimed books

**Principe** : Garder l'approche actuelle + tracking des livres déjà matchés

```python
def resolve_entities_v1_fixed(avis_list, books, critiques):
    """Approche actuelle avec tracking."""
    claimed_books = set()  # Livres déjà matchés

    for avis in avis_list:
        # Filtrer les livres déjà "claimed"
        available_books = [b for b in books if str(b["_id"]) not in claimed_books]

        matched_book = _match_book_multi_phase(avis, available_books)
        if matched_book:
            livre_oid = str(matched_book["_id"])
            avis["livre_oid"] = livre_oid
            claimed_books.add(livre_oid)  # Marquer comme claimed
        else:
            avis["livre_oid"] = None

    return avis_list
```

**Avantages** :
- Fix simple (ajout d'un set)
- Garde l'approche actuelle

**Inconvénients** :
- Ne résout pas le problème si plusieurs avis du même livre sont dispersés
- Dépend de l'ordre de traitement

## Recommandation

**Solution 2** (Matching livre par livre) est la plus robuste et logique métier.

**Plan d'implémentation** :
1. Créer `resolve_entities_v2()` en parallèle de l'existant
2. Adapter les tests pour vérifier les deux versions
3. Valider que tous les tests passent avec v2
4. Remplacer v1 par v2
5. Nettoyer le code

## Impact sur les tests

### Tests à garder
- `test_should_extract_all_avis_from_real_summary_section1_and_section2` ✅
- `test_should_match_all_24_avis_like_real_extraction` ✅ (documente le problème)

### Tests à adapter après refactoring
- `test_should_resolve_all_9_books_from_real_emission` (9 avis → OK, mais logique changera)
- Tests unitaires de matching (phases 1-4)

## Prochaines étapes

1. ✅ Documenter le problème (ce fichier)
2. ⬜ Implémenter Solution 2 (`resolve_entities_v2`)
3. ⬜ Vérifier tous les tests passent
4. ⬜ Remplacer l'ancienne version
5. ⬜ Vérifier l'émission 09/03/2025 devient 🟢
