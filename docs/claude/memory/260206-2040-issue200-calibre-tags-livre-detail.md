# Issue #200 - Tags Calibre sur la page livre

## Contexte

Ajout de l'affichage des tags Calibre sur la page de détail d'un livre. Les tags sont **calculés dynamiquement** (non stockés) à partir des données existantes dans MongoDB et Calibre.

## Convention des tags Calibre lmelp

- **`lmelp_yyMMdd`** : tag "programme" pour chaque émission où le livre a été discuté (toutes sections : programme ET coup de coeur)
- **`lmelp_prenom_nom`** : tag "critique" pour chaque critique ayant donné un coup de coeur au livre
- **`CALIBRE_VIRTUAL_LIBRARY_TAG`** (ex: "guillaume") : tag de la bibliothèque virtuelle, ajouté en premier si le livre est trouvé dans Calibre

Exemple : "La Deuxième Vie" de Sollers → `guillaume, lmelp_240324, lmelp_arnaud_viviant`

## Architecture

### Sources de données

Les tags sont construits à partir de 2 sources :

1. **Collection `avis` (MongoDB)** : contient `emission_oid`, `section` ("programme"/"coup_de_coeur"), `critique_nom_extrait`
2. **Calibre SQLite** : matching par titre normalisé via `_normalize_title()` + variable d'environnement `CALIBRE_VIRTUAL_LIBRARY_TAG`

### Backend

**`mongodb_service.py`** - Méthode `_build_calibre_tags()` :
- Parcourt tous les avis du livre
- Pour chaque avis : récupère la date d'émission → génère `lmelp_yyMMdd`
- Pour les coup de coeur : récupère le nom du critique → génère `lmelp_prenom_nom` (lowercase, espaces→underscores)
- Tri : dates chronologiques d'abord, puis critiques alphabétiques
- Utilise des `set()` pour dédupliquer (plusieurs avis sur même émission = un seul tag date)

**`app.py`** - Endpoint `/api/livre/{livre_id}` enrichi :
- Après récupération des données MongoDB, vérifie si Calibre est disponible
- Si oui, utilise `_build_calibre_index()` + `_normalize_title()` (réutilisation du pattern Palmarès)
- Si le livre est trouvé dans Calibre, insère `CALIBRE_VIRTUAL_LIBRARY_TAG` en position 0

### Frontend

**`LivreDetail.vue`** :
- Affichage des tags comme badges violets (`#f3e5f5`/`#7b1fa2`) en police monospace dans la section `.livre-stats`
- Bouton copie (📋) qui copie tous les tags séparés par virgules dans le presse-papier via `navigator.clipboard.writeText()`
- Feedback visuel : le bouton change en ✓ pendant 2 secondes après copie
- Graceful degradation : rien ne s'affiche si `calibre_tags` est absent ou vide

## Fichiers modifiés

- `src/back_office_lmelp/services/mongodb_service.py` : `_build_calibre_tags()` + intégration dans `get_livre_with_episodes()`
- `src/back_office_lmelp/app.py` : enrichissement Calibre dans l'endpoint `/api/livre/{livre_id}`
- `frontend/src/views/LivreDetail.vue` : template tags + `copyTags()` + CSS
- `tests/test_livre_detail_tags.py` : 12 tests backend (tag generation, sorting, Calibre enrichment)
- `frontend/tests/unit/livreDetailTags.spec.js` : 5 tests frontend (affichage, copie, états vides)

## Points techniques notables

- La collection `avis` (pas `avis_critiques`) est utilisée car elle contient le champ `section` et `critique_nom_extrait`
- `self.avis_collection = self.db.avis` dans `mongodb_service.py`
- Le mapping `emissions_by_id` est construit à partir de `emissions_by_episode` (déjà disponible dans `get_livre_with_episodes`)
- Le format date `strftime('%y%m%d')` produit correctement `240324` pour le 24 mars 2024
- Le tag critique utilise `.lower().replace(" ", "_")` pour convertir "Arnaud Viviant" → "arnaud_viviant"

## Réutilisation de patterns existants

- Pattern Calibre enrichment du Palmarès (`_normalize_title()`, `_build_calibre_index()`)
- Pattern clipboard du frontend (similaire aux autres boutons de copie dans l'app)
- Pattern test avec `MongoDBService.__new__()` pour tester des méthodes sans connexion MongoDB
