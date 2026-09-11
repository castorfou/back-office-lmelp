# Compteurs et Statistiques

## Vue d'ensemble

Cette page documente tous les compteurs affichés dans l'application et leurs règles de calcul.

## Page d'accueil (Dashboard)

### 1. Dernière mise à jour
**Valeur:** Date du dernier épisode en base
**Collection:** `episodes`
**Requête:**
```javascript
db.episodes.find().sort({diffusion: -1}).limit(1)
```
**Clic:** Ouvre la page interne de Monitoring RSS (`/rss-monitoring`).

### 2. Épisodes sans transcription
**Valeur:** Nombre d'épisodes non masqués sans transcription
**Collection:** `episodes`
**Formule:**
```
COUNT(episodes WHERE masked ≠ true AND transcription IN [null, ""])
```
**Requête MongoDB:**
```javascript
db.episodes.count({
  $and: [
    {$or: [{masked: {$ne: true}}, {masked: {$exists: false}}]},
    {$or: [{transcription: null}, {transcription: ""}, {transcription: {$exists: false}}]}
  ]
})
```
**Clic:** Ouvre la page transcription PGX (`/transcription-pgx`), où la transcription peut être lancée directement depuis ce back-office — voir `docs/user/transcription-pgx.md`.
**Note :** Cette métrique est intégrée au payload caché standard du dashboard (`/api/dashboard/stats`, cache 5 min), invalidé automatiquement à chaque écriture du champ `transcription` sur la collection `episodes`.

### 3. Épisodes sans avis critiques
**Valeur:** Nombre d'épisodes non masqués, avec transcription, sans avis critique
**Collections:** `episodes`, `avis_critiques`
**Formule:**
```
COUNT(episodes WHERE masked ≠ true AND transcription NOT IN [null, ""])
- COUNT(DISTINCT avis_critiques.episode_oid WHERE episode.masked ≠ true)
```
**Note importante:** Un épisode sans transcription est exclu de ce compteur — les avis critiques sont générés à partir de la transcription, donc un épisode qui n'en a pas encore ne peut logiquement pas en avoir (il est déjà signalé par la tuile "Épisodes sans transcription" ci-dessus).

**Requête MongoDB:**
```javascript
// Étape 1: Compter épisodes non masqués avec transcription
db.episodes.count({
  $and: [
    {$or: [{masked: false}, {masked: {$exists: false}}]},
    {transcription: {$nin: [null, ""]}}
  ]
})

// Étape 2: Compter avis dont l'épisode n'est pas masqué (via aggregation)
db.avis_critiques.aggregate([
  {
    $lookup: {
      from: "episodes",
      let: {episode_oid_str: "$episode_oid"},
      pipeline: [
        {
          $match: {
            $expr: {$eq: [{$toString: "$_id"}, "$$episode_oid_str"]}
          }
        }
      ],
      as: "episode"
    }
  },
  {$unwind: "$episode"},
  {
    $match: {
      $or: [
        {"episode.masked": {$ne: true}},
        {"episode.masked": {$exists: false}}
      ]
    }
  },
  {$group: {_id: "$episode_oid"}}
])

// Résultat: Étape1 - COUNT(Étape2)
```

**Note importante:** Le calcul utilise une aggregation avec `$lookup` pour filtrer les avis critiques dont l'épisode est masqué. Cela garantit que seuls les épisodes non masqués sont comptés.

### 4. Avis critiques sans analyse
**Valeur:** Épisodes avec avis critique mais sans extraction des livres
**Collections:** `avis_critiques`, `livresauteurs_cache`, `episodes`
**Formule:**
```
COUNT(DISTINCT avis_critiques.episode_oid WHERE episode.masked ≠ true)
- COUNT(DISTINCT livresauteurs_cache.episode_oid WHERE episode.masked ≠ true)
```

### 5. Livres suggérés
**Valeur:** Livres avec statut "suggested" dans le cache
**Collection:** `livresauteurs_cache`
**Requête:**
```javascript
db.livresauteurs_cache.count({
  "couples.status": "suggested"
})
```

### 6. Livres non trouvés
**Valeur:** Livres avec statut "not_found" dans le cache
**Collection:** `livresauteurs_cache`
**Requête:**
```javascript
db.livresauteurs_cache.count({
  "couples.status": "not_found"
})
```

### 7. Livres sans lien Babelio
**Valeur:** Livres sans URL Babelio et non marqués "not_found"
**Collection:** `livres`
**Requête:**
```javascript
db.livres.count({
  $and: [
    {$or: [{url_babelio: null}, {url_babelio: {$exists: false}}]},
    {$or: [{babelio_not_found: {$ne: true}}, {babelio_not_found: {$exists: false}}]}
  ]
})
```

### 8. Auteurs sans lien Babelio
**Valeur:** Auteurs sans URL Babelio et non marqués "not_found"
**Collection:** `auteurs`
**Requête:** Identique à "Livres sans lien Babelio"

### 9. Critiques manquants
**Valeur:** Épisodes avec noms de critiques non présents en base
**Collections:** `episodes`, `avis_critiques`, `critiques`
**Logique:**
1. Pour chaque épisode avec avis critique non masqué
2. Extraire les noms de critiques depuis le summary
3. Vérifier existence dans collection `critiques`
4. Compter les épisodes avec au moins 1 critique manquant

### 10. Épisodes sans émission
**Valeur:** Épisodes avec avis critique mais sans émission créée
**Collections:** `avis_critiques`, `emissions`, `episodes`
**Formule:**
```
COUNT(DISTINCT avis_critiques.episode_oid WHERE episode.masked ≠ true)
- COUNT(DISTINCT emissions.episode_id)
```

---

## Page Génération d'Avis Critiques

### Pastilles vertes (🟢)
**Signification:** Épisodes avec avis critique généré
**Requête:** `/api/episodes-with-summaries`
**Critères:**
- Épisode non masqué
- Présence dans collection `avis_critiques`

### Pastilles grises (⚪)
**Signification:** Épisodes SANS avis critique (avec transcription)
**Requête:** `/api/episodes-sans-avis-critiques`
**Critères:**
- Épisode non masqué
- Transcription disponible (non vide)
- Absence dans collection `avis_critiques`

**Total affiché:**
```
Nombre d'épisodes = Pastilles vertes + Pastilles grises
```

---

## Page Livres et Auteurs

### Pastilles vertes (🟢)
**Signification:** Livre au statut "mongo" (trouvé et stocké)
**Collection:** `livresauteurs_cache`
**Champ:** `couples[].status = "mongo"`

### Pastilles grises (⚪)
**Signification:** Épisode sans analyse
**Critères:** Pas d'entrée dans `livresauteurs_cache` pour cet épisode

### Pastilles oranges (🟠)
**Signification:** Livre suggéré par Babelio (à vérifier)
**Collection:** `livresauteurs_cache`
**Champ:** `couples[].status = "suggested"`

### Pastilles rouges (🔴)
**Signification:** Analyse incomplète
**Critères:** Certains livres de l'épisode ne sont pas au statut "mongo"

---

## Page Émissions

### Nombre d'émissions
**Valeur:** Nombre total d'émissions créées
**Collection:** `emissions`
**Requête:**
```javascript
db.emissions.count({})
```

**Relation 1:1:**
- 1 émission = 1 avis_critique (épisode non masqué)
- `emission.episode_id` → `episodes._id` (ObjectId)
- `emission.avis_critique_id` → `avis_critiques._id` (ObjectId)

---

## Collections MongoDB

### Champs clés

#### Collection `episodes`
- `_id`: ObjectId (identifiant unique)
- `masked`: Boolean (épisode caché)
- `transcription`: String (transcription texte)
- `diffusion`: Date

#### Collection `avis_critiques`
- `_id`: ObjectId
- `episode_oid`: String (référence à episodes._id)
- `summary`: String (avis critique généré)

#### Collection `livresauteurs_cache`
- `episode_oid`: String
- `couples[].status`: "mongo" | "suggested" | "not_found"

#### Collection `emissions`
- `episode_id`: ObjectId (référence à episodes._id)
- `avis_critique_id`: ObjectId (référence à avis_critiques._id)
- `date`: Date
