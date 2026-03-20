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

---

## Fix bonus — RadioFrance pagination dichotomique pour épisodes anciens

Commits dans la même branche : `0057e61` (fix) + `fe40af1` (suppression test timeout)

### Problème

Les épisodes anciens (ex : 2017) n'étaient pas trouvés par la recherche RadioFrance :
1. Le paramètre de recherche était `?search=` au lieu de `?q=` (mauvaise URL)
2. RadioFrance bloquait les requêtes sans `User-Agent` (filtrage anti-bot)
3. Le moteur `?q=` n'indexe pas les anciens épisodes → page vide sans erreur

### Solution — `src/back_office_lmelp/services/radiofrance_service.py`

**Corrections directes** :
- `?search=` → `?q=` dans la construction d'URL de recherche
- Ajout `User-Agent` Chrome dans `self.http_headers` appliqué à toutes les sessions `aiohttp`

**Fallback dichotomique** (nouvelle méthode `_search_chronological_pages`) :
- Quand `?q=` ne retourne rien, bascule sur pagination chronologique `?p=N`
- Recherche binaire : la date médiane d'une page oriente la dichotomie (max ~8 itérations pour 200 pages)
- Détection des pages "fallback RadioFrance" : pages invalides retournent les mêmes liens récents (signature détectable)
- Tolérance de date réduite à 3 jours (vs 7 avant) pour éviter les faux positifs
- Sélection du **meilleur candidat** (diff date minimal) au lieu du premier acceptable

**Méthodes ajoutées** :
- `_get_page_links_and_median_date(page)` : récupère liens + date médiane d'une page `?p=N`
- `_get_page_median_date(page)` : wrapper pour la dichotomie
- `_search_chronological_pages(title, date, min_duration)` : orchestre la recherche dichotomique

### Suppression test timeout — `tests/test_radiofrance_pagination.py`

`test_pagination_should_respect_timeout` supprimé : le timeout de 30s était trop court pour une recherche dichotomique réseau (~60-90s réels). Les vrais garde-fous sont dans le code : max 10 itérations, fenêtre finie → pas de risque de boucle infinie.

### Tests mis à jour — `tests/test_radiofrance_service.py`

Mocks mis à jour : `?search=` → `?q=` dans les URLs mockées.
