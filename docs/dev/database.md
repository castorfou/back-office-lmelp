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
  "titre": "Les nouveaux livres de Simon Chevrier, Sylvain Tesson, Gaël Octavia, L...",
  "date": ISODate("2025-08-03T10:59:59.000Z"),
  "description": "durée : 00:51:36 - Le Masque et la Plume - par : Laurent Goumarre - Un...",
  "description_corrigee": "durée : 00:51:36 - Le Masque et la Plume - par : Laurent Goumarre -\n...",
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
| `titre` | String | Oui | Titre de l'épisode |
| `date` | Date | Oui | Date de diffusion |
| `description` | String | Oui | Description originale |
| `description_corrigee` | String | Non | Description corrigée par l'utilisateur |
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
  date: Date;
  description: string;
  description_corrigee?: string | null;
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
async def update_episode_description(self, episode_id: str, description: str) -> bool:
    """Met à jour la description corrigée d'un épisode."""
    result = await self.collection.update_one(
        {"_id": ObjectId(episode_id)},
        {"$set": {"description_corrigee": description}}
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

// Épisodes avec description corrigée
db.episodes.countDocuments({ "description_corrigee": { $ne: null } })
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
