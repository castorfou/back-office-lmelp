# Base de données - Back-Office LMELP

## Vue d'ensemble

Le Back-Office LMELP utilise MongoDB comme base de données principale pour stocker les informations des épisodes de podcast.

## Configuration

### Connection
```python
# URL par défaut
MONGODB_URL = "mongodb://localhost:27017"

# Base de données
DATABASE_NAME = "lmelp"

# Collection principale
COLLECTION_NAME = "episodes"
```

### Service MongoDB

```python
class MongoDBService:
    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.database: Optional[AsyncIOMotorDatabase] = None
        self.collection: Optional[AsyncIOMotorCollection] = None
```

## Schéma des données

### Collection `episodes`

```json
{
  "_id": ObjectId("68a3911df8b628e552fdf11f"),
  "titre": "Les nouveaux livres de Simon Chevrier, Sylvain Tesson, Gaël Octavia (corrigé)",
  "titre_origin": "Les nouveaux livres de Simon Chevrier, Sylvain Tesson, Gaël Octavia, L...",
  "date": ISODate("2025-08-03T10:59:59.000Z"),
  "description": "durée : 00:51:36 - Le Masque et la Plume - par : Laurent Goumarre (description corrigée)",
  "description_origin": "durée : 00:51:36 - Le Masque et la Plume - par : Laurent Goumarre - Un...",
  "url": "https://proxycast.radiofrance.fr/e7ade132-cccd-4bcc-ba98-f620f9c4a0d0/...",
  "audio_rel_filename": "2025/14007-03.08.2025-ITEMA_2420925-2025F400TS0215-NET_MFI_28633905-6...",
  "transcription": " France Inter Le masque et la plume Un tour du monde sur des stacks, u...",
  "type": "livres",
  "duree": 3096
}
```

### Champs détaillés

| Champ | Type | Obligatoire | Description |
|-------|------|------------|-------------|
| `_id` | ObjectId | Oui | Identifiant unique MongoDB |
| `titre` | String | Oui | Titre de l'épisode (version corrigée si applicable) |
| `titre_origin` | String | Non | Titre original avant correction |
| `date` | Date | Oui | Date de diffusion |
| `description` | String | Oui | Description de l'épisode (version corrigée si applicable) |
| `description_origin` | String | Non | Description originale avant correction |
| `url` | String | Oui | URL de l'épisode audio |
| `audio_rel_filename` | String | Oui | Chemin relatif du fichier audio |
| `transcription` | String | Oui | Transcription de l'épisode |
| `type` | String | Oui | Type d'émission (livres, cinéma, etc.) |
| `duree` | Number | Oui | Durée en secondes |

### Types de données

```typescript
interface Episode {
  _id: ObjectId;
  titre: string;
  titre_origin?: string | null;
  date: Date;
  description: string;
  description_origin?: string | null;
  url: string;
  audio_rel_filename: string;
  transcription: string;
  type: string;
  duree: number;
}
```

## Opérations CRUD

### Create (Insertion)

```python
async def insert_episode(self, episode_data: dict) -> str:
    """Insère un nouvel épisode."""
    result = await self.collection.insert_one(episode_data)
    return str(result.inserted_id)
```

### Read (Lecture)

```python
# Tous les épisodes
async def get_all_episodes(self) -> list[dict]:
    """Récupère tous les épisodes."""
    cursor = self.collection.find({})
    return await cursor.to_list(length=None)

# Épisode par ID
async def get_episode_by_id(self, episode_id: str) -> Optional[dict]:
    """Récupère un épisode par son ID."""
    return await self.collection.find_one({"_id": ObjectId(episode_id)})
```

### Update (Mise à jour)

```python
# Nouvelle logique de correction des titres
async def update_episode_title_new(self, episode_id: str, titre_corrige: str) -> bool:
    """Met à jour le titre d'un épisode avec sauvegarde de l'original."""
    # Récupérer l'épisode existant
    existing_episode = await self.collection.find_one({"_id": ObjectId(episode_id)})
    if not existing_episode:
        return False

    # Préparer les données de mise à jour
    update_data = {"titre": titre_corrige}

    # Sauvegarder l'original seulement si pas déjà fait
    if "titre_origin" not in existing_episode or existing_episode["titre_origin"] is None:
        update_data["titre_origin"] = existing_episode.get("titre")

    result = await self.collection.update_one(
        {"_id": ObjectId(episode_id)},
        {"$set": update_data}
    )
    return result.modified_count > 0

# Nouvelle logique de correction des descriptions
async def update_episode_description_new(self, episode_id: str, description_corrigee: str) -> bool:
    """Met à jour la description d'un épisode avec sauvegarde de l'originale."""
    # Récupérer l'épisode existant
    existing_episode = await self.collection.find_one({"_id": ObjectId(episode_id)})
    if not existing_episode:
        return False

    # Préparer les données de mise à jour
    update_data = {"description": description_corrigee}

    # Sauvegarder l'original seulement si pas déjà fait
    if "description_origin" not in existing_episode or existing_episode["description_origin"] is None:
        update_data["description_origin"] = existing_episode.get("description")

    result = await self.collection.update_one(
        {"_id": ObjectId(episode_id)},
        {"$set": update_data}
    )
    return result.modified_count > 0
```

### Delete (Suppression)

```python
async def delete_episode(self, episode_id: str) -> bool:
    """Supprime un épisode."""
    result = await self.collection.delete_one({"_id": ObjectId(episode_id)})
    return result.deleted_count > 0
```

## Index recommandés

### Index existants

```javascript
// Index par défaut sur _id
{ "_id": 1 }
```

### Index à créer pour les performances

```javascript
// Index sur la date (tri chronologique)
db.episodes.createIndex({ "date": -1 })

// Index sur le type (filtrage par émission)
db.episodes.createIndex({ "type": 1 })

// Index composé pour recherche avancée
db.episodes.createIndex({
  "type": 1,
  "date": -1
})

// Index texte pour recherche full-text
db.episodes.createIndex({
  "titre": "text",
  "description": "text",
  "transcription": "text"
}, {
  "weights": {
    "titre": 10,
    "description": 5,
    "transcription": 1
  }
})
```

### Commandes d'indexation

```bash
# Se connecter à MongoDB
mongosh

# Utiliser la base lmelp
use lmelp

# Créer les index
db.episodes.createIndex({ "date": -1 })
db.episodes.createIndex({ "type": 1 })
db.episodes.createIndex({ "type": 1, "date": -1 })

# Vérifier les index
db.episodes.getIndexes()
```

## Requêtes courantes

### Statistiques de base

```javascript
// Nombre total d'épisodes
db.episodes.countDocuments()

// Répartition par type
db.episodes.aggregate([
  { $group: { _id: "$type", count: { $sum: 1 } } },
  { $sort: { count: -1 } }
])

// Épisodes avec titre corrigé
db.episodes.countDocuments({ "titre_origin": { $ne: null, $exists: true } })

// Épisodes avec description corrigée
db.episodes.countDocuments({ "description_origin": { $ne: null, $exists: true } })
```

### Recherche et filtrage

```javascript
// Épisodes récents (30 derniers jours)
db.episodes.find({
  "date": { $gte: new Date(Date.now() - 30*24*60*60*1000) }
}).sort({ "date": -1 })

// Épisodes par type
db.episodes.find({ "type": "livres" }).sort({ "date": -1 })

// Recherche textuelle
db.episodes.find({
  $text: { $search: "Simon Chevrier" }
})

// Épisodes longs (> 1 heure)
db.episodes.find({ "duree": { $gt: 3600 } })
```

### Agrégations avancées

```javascript
// Durée moyenne par type
db.episodes.aggregate([
  { $group: {
    _id: "$type",
    avgDuration: { $avg: "$duree" },
    count: { $sum: 1 }
  }},
  { $sort: { avgDuration: -1 } }
])

// Évolution temporelle des épisodes
db.episodes.aggregate([
  { $group: {
    _id: {
      year: { $year: "$date" },
      month: { $month: "$date" }
    },
    count: { $sum: 1 }
  }},
  { $sort: { "_id.year": 1, "_id.month": 1 } }
])
```

## Gestion de la connexion

### Cycle de vie

```python
class MongoDBService:
    async def connect(self):
        """Établit la connexion MongoDB."""
        try:
            self.client = AsyncIOMotorClient(MONGODB_URL)
            self.database = self.client[DATABASE_NAME]
            self.collection = self.database[COLLECTION_NAME]

            # Test de connexion
            await self.client.admin.command('ismaster')
            print("Connexion MongoDB établie")
        except Exception as e:
            print(f"Erreur connexion MongoDB: {e}")
            raise

    async def disconnect(self):
        """Ferme la connexion MongoDB."""
        if self.client:
            self.client.close()
            print("Connexion MongoDB fermée")
```

### Gestion d'erreurs

```python
async def get_episode_by_id(self, episode_id: str) -> Optional[dict]:
    try:
        return await self.collection.find_one({"_id": ObjectId(episode_id)})
    except InvalidId:
        print(f"ID MongoDB invalide: {episode_id}")
        return None
    except Exception as e:
        print(f"Erreur lecture épisode {episode_id}: {e}")
        raise
```

## Logique des corrections (Refactorisée)

### Nouvelle approche de stockage des corrections

Depuis la version refactorisée, le système de corrections utilise une nouvelle logique :

#### Principe
- **Champs principaux** : `titre` et `description` contiennent toujours les versions à afficher (originales ou corrigées)
- **Champs de sauvegarde** : `titre_origin` et `description_origin` conservent les versions originales seulement quand une correction est faite
- **Avantage** : Les autres applications (lmelp, moteur de recherche) utilisent automatiquement les versions corrigées sans modification

#### Comportement lors des corrections

```python
# Première correction d'un titre
# Avant : { "titre": "Titre original" }
# Après : {
#   "titre": "Titre corrigé",
#   "titre_origin": "Titre original"
# }

# Corrections suivantes
# Avant : { "titre": "Titre corrigé", "titre_origin": "Titre original" }
# Après : {
#   "titre": "Nouveau titre corrigé",
#   "titre_origin": "Titre original"  # <- Préservé
# }
```

#### Identification des épisodes corrigés

```javascript
// Épisodes avec titre corrigé
db.episodes.find({ "titre_origin": { $exists: true, $ne: null } })

// Épisodes avec description corrigée
db.episodes.find({ "description_origin": { $exists: true, $ne: null } })

// Statistiques des corrections
db.episodes.aggregate([
  {
    $group: {
      _id: null,
      total: { $sum: 1 },
      titres_corriges: {
        $sum: {
          $cond: [
            { $and: [{ $exists: ["$titre_origin"] }, { $ne: ["$titre_origin", null] }] },
            1, 0
          ]
        }
      },
      descriptions_corrigees: {
        $sum: {
          $cond: [
            { $and: [{ $exists: ["$description_origin"] }, { $ne: ["$description_origin", null] }] },
            1, 0
          ]
        }
      }
    }
  }
])
```

### Compatibilité ascendante

La nouvelle logique maintient la compatibilité avec les épisodes existants :
- Les épisodes sans corrections n'ont pas de champs `*_origin`
- Les anciens champs `titre_corrige` et `description_corrigee` sont dépréciés mais peuvent coexister temporairement
- Migration progressive possible sans interruption de service

## Migration des données

### Scripts de migration

```python
# Migration: Ajouter champ description_corrigee
async def migrate_add_description_corrigee():
    result = await collection.update_many(
        {"description_corrigee": {"$exists": False}},
        {"$set": {"description_corrigee": None}}
    )
    print(f"Migration: {result.modified_count} documents mis à jour")

# Migration: Normaliser les types
async def migrate_normalize_types():
    type_mapping = {
        "Livres": "livres",
        "Cinema": "cinema",
        "Musique": "musique"
    }

    for old_type, new_type in type_mapping.items():
        result = await collection.update_many(
            {"type": old_type},
            {"$set": {"type": new_type}}
        )
        print(f"Migration: {old_type} -> {new_type} ({result.modified_count} docs)")
```

### Sauvegarde et restauration

```bash
# Sauvegarde complète
mongodump --db lmelp --out ./backup/

# Restauration
mongorestore --db lmelp ./backup/lmelp/

# Export JSON
mongoexport --db lmelp --collection episodes --out episodes.json --pretty

# Import JSON
mongoimport --db lmelp --collection episodes --file episodes.json
```

## Performance et optimisation

### Monitoring

```javascript
// Statistiques de la collection
db.episodes.stats()

// Plans d'exécution des requêtes
db.episodes.find({ "type": "livres" }).explain("executionStats")

// Index utilization
db.episodes.aggregate([{ $indexStats: {} }])
```

### Optimisation des requêtes

```python
# Projection pour limiter les données
async def get_episodes_summary(self):
    """Récupère uniquement les champs essentiels."""
    cursor = self.collection.find(
        {},
        {"_id": 1, "titre": 1, "date": 1, "type": 1}
    )
    return await cursor.to_list(length=None)

# Pagination
async def get_episodes_paginated(self, page: int = 1, limit: int = 20):
    """Pagination des résultats."""
    skip = (page - 1) * limit
    cursor = self.collection.find({}).skip(skip).limit(limit)
    return await cursor.to_list(length=limit)
```

## Sécurité

### Authentification (à implémenter)

```python
# Configuration recommandée pour production
client = AsyncIOMotorClient(
    "mongodb://username:password@localhost:27017", # pragma: allowlist secret
    authSource="admin",
    authMechanism="SCRAM-SHA-256"
)
```

### Bonnes pratiques

1. **Validation des ObjectId** avant les requêtes
2. **Limitation des projections** pour réduire le trafic
3. **Index appropriés** pour toutes les requêtes fréquentes
4. **Monitoring des performances** avec `explain()`
5. **Sauvegarde régulière** des données critiques
6. **Gestion des types de données** : vérifier le type réel retourné par les opérations MongoDB (voir section Type Handling ci-dessous)

### Type Handling - distinct() vs find()

**IMPORTANT**: Les opérations MongoDB peuvent retourner des types différents selon la méthode utilisée.

#### Problème courant

```python
# ❌ ERREUR: Assumer que distinct() retourne le même type que find()
episode_ids_from_distinct = collection.distinct("episode_oid")  # Peut retourner strings!
episode_ids_from_find = {ep["_id"] for ep in episodes.find()}    # Retourne ObjectId

# Intersection vide si les types ne matchent pas
intersection = set(episode_ids_from_distinct) & episode_ids_from_find  # 0 éléments!
```

#### Solution

```python
# ✅ CORRECT: Conversion explicite basée sur inspection des données réelles
from bson import ObjectId

# Vérifier le type réel avec MCP tools ou inspection manuelle
# Exemple: mcp__MongoDB__aggregate pour voir le type retourné

episode_ids_from_distinct = {
    ObjectId(ep_id) if isinstance(ep_id, str) else ep_id
    for ep_id in collection.distinct("episode_oid")
    if ep_id is not None
}

episode_ids_from_find = {ep["_id"] for ep in episodes.find()}
intersection = episode_ids_from_distinct & episode_ids_from_find  # Fonctionne!
```

#### Recommandations

1. **Toujours inspecter les données réelles** avant d'implémenter des comparaisons ou set operations
2. **Utiliser les MCP MongoDB tools** pour vérifier les types retournés: `mcp__MongoDB__find`, `mcp__MongoDB__aggregate`
3. **Documenter les conversions** dans le code avec des commentaires explicites
4. **Créer des mocks de tests** basés sur les types réels, pas sur des suppositions

## Troubleshooting

### Problèmes courants

```python
# Connexion refusée
# Solution: Vérifier que MongoDB est démarré
systemctl status mongod

# ObjectId invalide
# Solution: Validation avant conversion
from bson import ObjectId
from bson.errors import InvalidId

try:
    oid = ObjectId(episode_id)
except InvalidId:
    raise HTTPException(status_code=400, detail="ID invalide")

# Collection vide
# Solution: Vérifier le nom de la collection et database
db.listCollections()
```

### Logs et debugging

```python
import logging

# Activer les logs MongoDB
logging.getLogger('motor').setLevel(logging.DEBUG)

# Logs des requêtes
async def get_episode_by_id(self, episode_id: str):
    logger.info(f"Recherche épisode ID: {episode_id}")
    result = await self.collection.find_one({"_id": ObjectId(episode_id)})
    logger.info(f"Résultat: {'trouvé' if result else 'non trouvé'}")
    return result
```
