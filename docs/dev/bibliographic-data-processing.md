# Traitement des données bibliographiques

## Vue d'ensemble

Le système de gestion bibliographique traite les données des livres et auteurs à travers plusieurs étapes de validation et de correction automatique.

---

## Propagation des corrections dans les résumés

### Architecture

Le système maintient la cohérence entre les données bibliographiques validées (base MongoDB) et les résumés affichés (`avis_critiques.summary`).

#### Mise à jour immédiate lors de validation

Lors de la validation manuelle d'un livre, le résumé est automatiquement corrigé :

```python
# collections_management_service.py

def _update_summary_with_correction(self, cache_id: str, book_data: dict) -> None:
    """Mise à jour du résumé avec les corrections bibliographiques."""

    # Récupération de l'avis critique
    avis_critique = self.mongodb_service.get_avis_critique_by_id(
        book_data.get("avis_critique_id")
    )

    # Détection des corrections
    original_author = book_data.get("auteur", "")
    corrected_author = book_data.get("user_validated_author", original_author)
    original_title = book_data.get("titre", "")
    corrected_title = book_data.get("user_validated_title", original_title)

    # Application si différence détectée
    if original_author != corrected_author or original_title != corrected_title:
        updated_summary = summary_updater.update_summary(
            original_summary=avis_critique["summary"],
            original_author=original_author,
            corrected_author=corrected_author,
            original_title=original_title,
            corrected_title=corrected_title
        )

        self.mongodb_service.update_avis_critique(
            avis_critique_id,
            {"summary": updated_summary}
        )
```

#### Garbage collector automatique

Au chargement d'un épisode, les résumés existants sont automatiquement nettoyés :

```python
def _cleanup_existing_summaries(self, episode_oid: str) -> None:
    """
    Nettoie les résumés pour les livres déjà validés.
    Utilise les données Babelio (Phase 0) comme référence.
    """

    cached_books = livres_auteurs_cache_service.get_books_by_episode_oid(episode_oid)

    for book in cached_books:
        # Vérification idempotence
        if livres_auteurs_cache_service.is_summary_corrected(book["_id"]):
            continue

        # Comparaison stricte OCR vs Babelio
        original_author = book.get("auteur", "")
        corrected_author = book.get("suggested_author", original_author)
        original_title = book.get("titre", "")
        corrected_title = book.get("suggested_title", original_title)

        # Application de la correction si nécessaire
        if original_author != corrected_author or original_title != corrected_title:
            self._update_summary_with_correction(str(book["_id"]), book)

        livres_auteurs_cache_service.mark_summary_corrected(book["_id"])
```

### Gestion de l'idempotence

Flag `summary_corrected` dans `livresauteurs_cache` :

```python
# livres_auteurs_cache_service.py

def is_summary_corrected(self, cache_id: str) -> bool:
    """Vérifie si le résumé a déjà été corrigé."""
    book = self.cache_collection.find_one({"_id": ObjectId(cache_id)})
    return book.get("summary_corrected", False) if book else False

def mark_summary_corrected(self, cache_id: str) -> bool:
    """Marque le résumé comme corrigé."""
    result = self.cache_collection.update_one(
        {"_id": ObjectId(cache_id)},
        {"$set": {"summary_corrected": True}}
    )
    return result.modified_count > 0
```

### Tests

- `tests/test_avis_critique_summary_correction.py` - Validation manuelle
- `tests/test_summary_cleanup_on_page_load.py` - Garbage collector
- `tests/test_garbage_collector_cleanup.py` - Tests avec données réelles

---

## Nettoyage automatique des champs texte

### Fonctionnement

Tous les champs bibliographiques sont automatiquement nettoyés lors de la validation pour éliminer les espaces parasites (début/fin).

```python
# collections_management_service.py

def handle_book_validation(self, book_data: dict[str, Any]) -> dict[str, Any]:
    """Traitement unifié avec nettoyage automatique des champs."""

    # Trim automatique de tous les champs texte
    text_fields = [
        "auteur", "titre", "editeur",
        "user_validated_author", "user_validated_title", "user_validated_publisher",
        "user_entered_author", "user_entered_title",
        "suggested_author", "suggested_title",
    ]

    for field in text_fields:
        if field in book_data and isinstance(book_data[field], str):
            book_data[field] = book_data[field].strip()

    # Suite du traitement...
```

### Champs traités

| Catégorie | Champs | Origine |
|-----------|--------|---------|
| Données OCR | `auteur`, `titre`, `editeur` | Extraction PDF |
| Validation manuelle | `user_validated_*` | Interface utilisateur |
| Saisie manuelle | `user_entered_*` | Interface utilisateur |
| Suggestions | `suggested_*` | Phase 0 Babelio |

### Comportement

- **Suppression** : Espaces en début et fin uniquement (`.strip()`)
- **Préservation** : Espaces internes conservés
  - `"Jean-Pierre Martin"` → Inchangé
  - `"Le livre de la jungle"` → Inchangé
  - `"  Albert Camus  "` → `"Albert Camus"`

### Bénéfices

- Évite les doublons en base
- Améliore le matching Babelio
- Garantit la cohérence des données

### Tests

`tests/test_input_trimming.py` - 6 tests couvrant tous les cas

---

## Identification des épisodes traités

### Vue d'ensemble

Les épisodes déjà traités (avec livres en cache) sont identifiés visuellement dans l'interface par un préfixe `*`.

### Backend : Flag has_cached_books

L'endpoint `/api/episodes-with-reviews` enrichit chaque épisode :

```python
# app.py

# Pour chaque épisode
episode_dict = episode.to_summary_dict()

# Vérification cache
cached_books = livres_auteurs_cache_service.get_books_by_episode_oid(episode_oid)
episode_dict["has_cached_books"] = len(cached_books) > 0
```

**Réponse API** :
```json
{
  "id": "507f...",
  "date": "2025-01-12",
  "titre": "Les nouvelles pages du polar",
  "has_cached_books": true
}
```

### Frontend : Affichage visuel

La fonction `formatEpisodeOption()` ajoute le préfixe :

```javascript
// LivresAuteurs.vue

formatEpisodeOption(episode) {
  const date = new Date(episode.date).toLocaleDateString('fr-FR');
  const title = episode.titre_corrige || episode.titre;
  const prefix = episode.has_cached_books ? '* ' : '';
  return `${prefix}${date} - ${title}`;
}
```

**Rendu** :
```
* 12/01/2025 - Les nouvelles pages du polar    ← Déjà traité
  05/01/2025 - Littérature contemporaine        ← Nouveau
```

### Logique de détection

Un épisode est marqué comme traité si au moins une entrée existe dans `livresauteurs_cache` avec l'`episode_oid` correspondant.

### Tests

- Backend : `tests/test_episodes_with_cached_books_flag.py` - 3 tests
- Frontend : `frontend/tests/unit/formatEpisodeOption.spec.js` - 5 tests

---

## Configuration du cache navigateur (développement)

### Headers HTTP no-cache

En mode développement, le serveur Vite envoie des headers pour désactiver le cache :

```javascript
// vite.config.js

export default defineConfig({
  server: {
    headers: {
      'Cache-Control': 'no-store, no-cache, must-revalidate',
      'Pragma': 'no-cache',
      'Expires': '0'
    }
  }
})
```

### Impact

| Header | Effet |
|--------|-------|
| `Cache-Control` | Force revalidation systématique |
| `Pragma` | Compatibilité anciens navigateurs |
| `Expires` | Marque contenu comme expiré |

### Scope

- **Mode développement** (`npm run dev`) : Headers actifs
- **Mode production** (`npm run build`) : Cache normal (performances)

### Bénéfices

- Plus besoin de Ctrl+F5 après redémarrage backend/frontend
- Rechargement normal (F5) suffit
- Impact négligeable sur performance en développement

---

## Références techniques

- [Summary Garbage Collector](./summary-garbage-collector.md) - Détails du ramasse-miette
- [Testing Patterns](./testing-patterns-advanced-mocking.md) - Patterns de test
