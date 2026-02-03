# Issue #191 - Page détail critique (/critique/:id)

## Contexte

Création d'une page de détail pour les critiques, accessible depuis les liens déjà cliquables dans le composant AvisTable. La page affiche le profil d'un critique, la distribution de ses notes en barplot CSS, ses coups de coeur, et une liste filtrable de toutes ses oeuvres critiquées.

## Fichiers créés

- `frontend/src/views/CritiqueDetail.vue` : Composant Vue.js suivant le pattern 3 états (loading/error/data) identique à `AuteurDetail.vue` et `LivreDetail.vue`
- `frontend/tests/integration/CritiqueDetail.test.js` : 11 tests d'intégration (affichage, filtres, états, API)
- `tests/test_critique_detail.py` : 5 tests backend (endpoint, 404, validation ObjectId, avis vides, flag animateur)

## Fichiers modifiés

- `src/back_office_lmelp/services/mongodb_service.py` : Ajout méthode `get_critique_detail()` (~160 lignes) avec batch-lookup livres/auteurs/émissions
- `src/back_office_lmelp/app.py` : Ajout endpoint `GET /api/critique/{critique_id}` après les endpoints auteur/livre detail
- `frontend/src/router/index.js` : Ajout route `/critique/:id` en lazy-loading

## Points techniques importants

### Types MongoDB - Conversions critiques

- `avis.critique_oid` est **String** (pas ObjectId) : la requête utilise directement `critique_id` comme string
- `avis.livre_oid` est **String** mais `livres._id` est **ObjectId** : conversion explicite avec `ObjectId(livre_oid)` et `contextlib.suppress(Exception)`
- `avis.emission_oid` est **String** mais `emissions._id` est **ObjectId** : même pattern de conversion
- `emissions.date` peut être `datetime` ou `str` : vérification avec `isinstance(em_date, datetime)`

### Pattern batch-lookup

La méthode `get_critique_detail()` effectue un seul appel API qui agrège tout :
1. Trouve le critique dans `critiques_collection`
2. Récupère tous les avis avec `critique_oid == critique_id`
3. Batch-lookup des livres, auteurs, émissions en un seul `find({"$in": [...]})`
4. Calcule distribution des notes (clés "2" à "10"), note_moyenne, coups de coeur (note >= 9)
5. Retourne le tout en un seul JSON (~200KB max pour le critique le plus prolifique avec 838 avis)

### Barplot CSS-only

Distribution des notes implémentée sans bibliothèque de charts :
- 9 colonnes (notes 2 à 10) avec hauteur proportionnelle au max
- Utilise les mêmes classes de couleur que le reste de l'app (`note-excellent`, `note-good`, `note-average`, `note-poor`)
- Compteur affiché au-dessus de chaque barre

### Filtrage côté client

3 filtres combinables sur les oeuvres :
- Recherche texte avec `removeAccents` de `@/utils/textUtils` (insensible aux accents)
- Plage de notes : Excellent (9-10), Bon (7-8), Moyen (5-6), Faible (<5)
- Section : Programme, Coup de coeur

### Liens de navigation

Depuis la page critique :
- Titre du livre -> `/livre/{livre_oid}`
- Nom de l'auteur -> `/auteur/{auteur_oid}`
- Date d'émission -> `/emissions/{YYYYMMDD}`

## Pattern réutilisable

La page suit exactement le même pattern que `AuteurDetail.vue` et `LivreDetail.vue` :
- Navigation component en haut
- 3 états : loading spinner, error avec bouton retour, contenu
- Appel API relatif (`/api/critique/${id}`) pour bénéficier du proxy Vite
- Gestion erreur 404 spécifique
- Memory guard côté backend
- Validation ObjectId (24 caractères hex)

## Volumes de données

- 28 critiques dans la collection `critiques`
- 4055 avis au total dans la collection `avis`
- Max 838 avis par critique (filtrage côté client approprié)
- Distribution des notes entre 2 et 10
