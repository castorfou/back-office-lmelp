# Issue #214 — LivreDetail: Statut Calibre & Tag Delta

## Objectif

Sur la page de détail d'un livre (`LivreDetail.vue`), afficher le statut de la bibliothèque Calibre :
- Indicateur "Dans Calibre" (badge 📚)
- Statut de lecture ("✓ Lu" / "◯ Non lu") + note si lu
- Masquer l'icône Anna's Archive si le livre est déjà dans la bibliothèque
- Mettre en évidence les tags lmelp_ attendus qui ne sont pas encore dans Calibre (tag delta, couleur orange)
- Exclure le tag "guillaume" (virtual library) du delta display
- Bouton "Copier les tags" inclut les "notable tags" (`babelio`, `lu`, `onkindle`) déjà dans Calibre

## Architecture de la solution

### 1. Backend — `src/back_office_lmelp/services/calibre_matching_service.py`

Extension de `enrich_palmares_item()` pour ajouter `calibre_current_tags` :

```python
def enrich_palmares_item(self, item, calibre_index):
    calibre_book = calibre_index.get(norm_title)
    if calibre_book:
        item["calibre_in_library"] = True
        item["calibre_read"] = calibre_book.get("read")
        item["calibre_rating"] = calibre_book.get("rating") if calibre_book.get("read") else None
        item["calibre_current_tags"] = calibre_book.get("tags")  # ← ajouté issue #214
    else:
        item["calibre_in_library"] = False
        item["calibre_read"] = None
        item["calibre_rating"] = None
        item["calibre_current_tags"] = None  # ← ajouté issue #214
```

### 2. Backend — `src/back_office_lmelp/app.py`

Appel dans `get_livre_detail()` après récupération de `livre_data` :

```python
# Issue #214: Enrich with Calibre library status
try:
    calibre_index = calibre_matching_service.get_calibre_index()
    calibre_matching_service.enrich_palmares_item(livre_data, calibre_index)
except Exception:
    livre_data["calibre_in_library"] = False
    livre_data["calibre_read"] = None
    livre_data["calibre_rating"] = None
    livre_data["calibre_current_tags"] = None
```

### 3. Frontend — `frontend/src/views/LivreDetail.vue`

**Template — Anna's Archive conditionnel :**
```html
<a v-if="!livre.calibre_in_library" ...>  ← masqué si dans Calibre
```

**Template — Section statut Calibre :**
```html
<span v-if="livre.calibre_in_library" data-test="calibre-in-library">
  <span>📚</span>
  <span :class="livre.calibre_read ? 'read' : 'not-read'" data-test="calibre-read-badge">
    {{ livre.calibre_read ? '✓ Lu' : '◯ Non lu' }}
  </span>
  <span v-if="livre.calibre_read && livre.calibre_rating != null" data-test="calibre-rating">
    {{ livre.calibre_rating }}/10
  </span>
</span>
```

**Template — Tags avec delta :**
```html
<span
  v-for="tag in displayedCalibreTags"
  :class="['tag-badge', isTagMissingFromCalibre(tag) ? 'tag-missing' : 'tag-present']"
  :data-test="isTagMissingFromCalibre(tag) ? 'tag-missing' : 'tag-badge'"
>{{ tag }}</span>
```

**Computed `displayedCalibreTags` :**
```javascript
displayedCalibreTags() {
  if (!this.livre?.calibre_tags) return [];
  if (!this.livre.calibre_in_library) return this.livre.calibre_tags;
  // Quand dans Calibre, masquer "guillaume" (virtual library tag) du delta
  return this.livre.calibre_tags.filter((t) => t.startsWith('lmelp_'));
},
```

**Méthode `isTagMissingFromCalibre(tag)` :**
```javascript
isTagMissingFromCalibre(tag) {
  if (!this.livre?.calibre_in_library) return false;
  if (!this.livre?.calibre_current_tags) return false;
  return !this.livre.calibre_current_tags.includes(tag);
},
```

**Méthode `copyTags()` — inclusion des notable tags :**
```javascript
async copyTags() {
  const NOTABLE_TAGS = ['babelio', 'lu', 'onkindle'];
  let tagsToCopy = [...this.livre.calibre_tags];

  if (this.livre.calibre_in_library && this.livre.calibre_current_tags) {
    const notablePresent = NOTABLE_TAGS.filter((t) => this.livre.calibre_current_tags.includes(t));
    for (const notable of notablePresent) {
      if (!tagsToCopy.includes(notable)) {
        tagsToCopy.push(notable);
      }
    }
  }
  await navigator.clipboard.writeText(tagsToCopy.join(', '));
}
```

## Tests écrits

### Backend (`tests/test_livre_detail_calibre_enrichment.py`)
- `test_livre_detail_includes_calibre_in_library_true`
- `test_livre_detail_includes_calibre_in_library_false`
- `test_livre_detail_includes_calibre_read_and_rating`
- `test_livre_detail_includes_calibre_current_tags`
- `test_livre_detail_calibre_unavailable_fallback`
- `test_livre_detail_enrich_called_with_calibre_index`

### Frontend (`frontend/src/views/__tests__/LivreDetailCalibre.spec.js`)
- Shows / hides Calibre in-library badge
- Shows / hides Anna's Archive icon based on `calibre_in_library`
- Shows "Lu" / "Non lu" badge + rating
- Tag delta highlighting (orange = missing, purple = present)
- "guillaume" tag excluded from delta
- `copyTags()` includes notable tags (`babelio`, `lu`) already in Calibre
- `copyTags()` excludes notable tags NOT in Calibre
- `copyTags()` works normally when not in Calibre

## Piège découvert (Bug post-implémentation initiale)

**Symptôme** : Bouton "Copier les tags" ne copiait pas `babelio`, `lu`, `onkindle` déjà dans Calibre.

**Cause** : `copyTags()` ne copiait que `this.livre.calibre_tags` (tags MongoDB attendus), sans inclure les tags "notables" déjà présents dans Calibre (`calibre_current_tags`).

**Fix** : Ajout de la logique d'union avec les `NOTABLE_TAGS` intersectés avec `calibre_current_tags`.

**Note** : `NOTABLE_TAGS = ("babelio", "lu", "onkindle")` était déjà défini dans `calibre_matching_service.py` pour `get_corrections()` — même logique répliquée côté frontend.

## CSS ajouté

- `.calibre-status-section` — flex container pour badges
- `.calibre-read-badge.read` — fond vert clair, texte vert
- `.calibre-read-badge.not-read` — fond gris, texte gris
- `.calibre-rating` — fond bleu clair, texte bleu
- `.tag-missing` — fond orange clair, bordure dashed orange (tag attendu manquant dans Calibre)
- `.tag-present` — fond violet clair (tag attendu présent dans Calibre, remplace `.tag-badge`)

## Fallback gracieux

Si Calibre est indisponible (exception dans `get_calibre_index`), le endpoint retourne quand même 200 avec :
- `calibre_in_library = False`
- `calibre_read = None`
- `calibre_rating = None`
- `calibre_current_tags = None`
