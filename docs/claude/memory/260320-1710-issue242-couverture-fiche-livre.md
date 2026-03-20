# Issue #242 - Afficher la couverture dans la fiche livre

## Contexte

Ajout de l'affichage de la couverture Babelio dans la page de détail d'un livre (`LivreDetail`).
Le champ `url_cover` existait déjà en MongoDB (collection `livres`) mais n'était pas exposé par l'API ni affiché en frontend.

## Modifications effectuées

### Backend — `src/back_office_lmelp/services/mongodb_service.py`

Dans `get_livre_with_episodes()` :
- Ajout de `"url_cover": 1` dans la projection du pipeline d'agrégation MongoDB
- Ajout de `"url_cover": livre_data.get("url_cover")` dans le dict retourné

### Frontend — `frontend/src/views/LivreDetail.vue`

**Template** :
- Suppression du bloc `external-links` séparé (était à gauche)
- Ajout d'un bloc `livre-cover` en premier dans `livre-header-container` (couverture collée à gauche)
- Déplacement des icônes Babelio + Anna's Archive dans un nouveau conteneur `refresh-and-links` (colonne flex) positionné à droite dans `livre-title-row`, avec le bouton Ré-extraire en haut et les icônes en dessous

**CSS** :
- `.livre-header` : `padding: 0`, `overflow: hidden` (suppression de l'espace blanc autour de la couverture)
- `.livre-header-container` : `gap: 0`, `align-items: stretch` (couverture pleine hauteur)
- `.livre-cover` : `flex-shrink: 0`
- `.cover-image` : `width: 200px`, `height: 100%`, `object-fit: cover` (colle au bord, pleine hauteur)
- `.livre-info` : `padding: 2rem` (padding déplacé du header vers livre-info)
- `.refresh-and-links` : `margin-left: auto`, flex colonne, `align-items: flex-end`
- `.external-links` : icônes 32px (réduit depuis 80px)
- `.livre-title-row` : ajout `flex-wrap: wrap`

**Logique Anna's Archive** : conservée — masquée si `calibre_in_library = true` (Issue #214, comportement voulu)

### Tests backend — `tests/test_livre_detail_endpoint.py`

2 nouveaux tests dans `TestGetLivreDetail` :
- `test_get_livre_returns_url_cover_when_present` : vérifie que `url_cover` est retourné quand présent
- `test_get_livre_handles_missing_url_cover` : vérifie que `url_cover` est absent/None quand non défini

### Tests frontend — `frontend/src/views/__tests__/LivreDetail.spec.js`

Nouveau describe `LivreDetail - Couverture du livre (Issue #242)` avec 2 tests :
- `should display cover image when url_cover is present` : vérifie `[data-test="livre-cover"]` avec bon `src`
- `should not display cover image when url_cover is absent` : vérifie absence du `[data-test="livre-cover"]`

## Points saillants

- Le champ `url_cover` est optionnel : `v-if="livre.url_cover"` côté frontend, `livre_data.get("url_cover")` côté backend
- La couverture n'est affichée que si disponible (pas tous les livres ont une couverture Babelio)
- Le redesign du header supprime le padding global pour coller la couverture au bord gauche
- Les icônes externes (Babelio, Anna's Archive) ont été réduites (32px) et repositionnées sous le bouton Ré-extraire (colonne flex à droite)
