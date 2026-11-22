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

### 2. Remises à intégrer
**Valeur:** Nombre de remises livrées par [lmelp-pap](https://github.com/castorfou/lmelp-pap) (émissions anciennes, 1955-2016) pas encore intégrées comme épisodes
**Collections:** `pap_remises` (écrite par lmelp-pap, lue seulement par lmelp) et `episodes`
**Règle:** une remise est à intégrer quand elle a une fiche dans `pap_remises`, que son fichier audio `<dossier audio>/<audio_rel_filename>` est présent (dossier audio : `AUDIO_STORAGE_PATH`) **et** qu'aucun épisode ne porte son identifiant (`episodes.pap_remise_id`, épisodes masqués compris). C'est exactement la liste de la page [Remises pap](remises-pap.md). Les fichiers audio du dossier qui n'ont pas de fiche pap (épisodes du flux RSS) ne sont pas comptés.
**Clic:** ouvre la page [Remises pap](remises-pap.md) (`/remises-pap`).
**Mise à jour:** la valeur fait partie du cache du dashboard (5 min). Une intégration la fait baisser aussitôt (écriture dans `episodes`, qui vide le cache). Une nouvelle remise de pap apparaît à l'expiration du cache, ou tout de suite avec le bouton « Actualiser ».
**Fichier absent:** chaque fiche pas encore intégrée dont le fichier manque est écrite dans les logs de lmelp (`docker logs`) :
```
fiche pap <_id> : fichier absent dans <dossier audio>/<audio_rel_filename>
```
C'est le signe que le dossier audio n'est pas monté au même endroit pour les deux applications.

### 3. Épisodes sans transcription
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

### 4. Épisodes sans avis critiques
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

### 5. Avis critiques sans analyse
**Valeur:** Épisodes avec avis critique mais sans extraction des livres
**Collections:** `avis_critiques`, `livresauteurs_cache`, `episodes`
**Formule:**
```
COUNT(DISTINCT avis_critiques.episode_oid WHERE episode.masked ≠ true)
- COUNT(DISTINCT livresauteurs_cache.episode_oid WHERE episode.masked ≠ true)
```

### 6. Livres suggérés
**Valeur:** Livres avec statut "suggested" dans le cache
**Collection:** `livresauteurs_cache`
**Requête:**
```javascript
db.livresauteurs_cache.count({
  "couples.status": "suggested"
})
```

### 7. Livres non trouvés
**Valeur:** Livres avec statut "not_found" dans le cache
**Collection:** `livresauteurs_cache`
**Requête:**
```javascript
db.livresauteurs_cache.count({
  "couples.status": "not_found"
})
```

### 8. Livres sans lien Babelio
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

### 9. Auteurs sans lien Babelio
**Valeur:** Auteurs sans URL Babelio et non marqués "not_found"
**Collection:** `auteurs`
**Requête:** Identique à "Livres sans lien Babelio"

### 10. Critiques manquants
**Valeur:** Épisodes avec noms de critiques non présents en base
**Collections:** `episodes`, `avis_critiques`, `critiques`
**Logique:**
1. Pour chaque épisode avec avis critique non masqué
2. Extraire les noms de critiques depuis le summary
3. Vérifier existence dans collection `critiques`
4. Compter les épisodes avec au moins 1 critique manquant

### 11. Épisodes sans émission
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

#### Collection `pap_remises`
- `_id`: String (URL de l'enregistrement pap, pas un ObjectId)
- `audio_rel_filename`: String (`<année>/<fichier>`, relatif au dossier audio)
- `date`: Date (première diffusion, 00:00 UTC)
- `sha256`: String (empreinte hexadécimale du fichier audio)
- `date_remise`: Date (UTC)

Un épisode intégré depuis une remise porte `source: "pap"` et `pap_remise_id` (String, `_id` de la fiche).

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
