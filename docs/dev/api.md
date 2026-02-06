# Documentation API - Back-Office LMELP

## FastAPI Best Practices

### Route Order - CRITICAL

**IMPORTANT**: In FastAPI, route definition order matters. Specific routes MUST be defined BEFORE parametric routes.

**❌ Wrong (causes bugs)**:
```python
@app.get("/api/episodes/{episode_id}")  # Parametric FIRST → WRONG
@app.get("/api/episodes/all")           # Specific AFTER → BUG
```

Calling `/api/episodes/all` will match the first route with `episode_id="all"`, causing a 404 error.

**✅ Correct**:
```python
@app.get("/api/episodes/all")           # Specific FIRST → CORRECT
@app.get("/api/episodes/{episode_id}")  # Parametric AFTER → CORRECT
```

### REST Idempotence with MongoDB

**IMPORTANT**: Use `matched_count` instead of `modified_count` for idempotent operations.

**❌ Wrong (non-idempotent)**:
```python
result = collection.update_one({"_id": id}, {"$set": {"field": value}})
return bool(result.modified_count > 0)  # Fails if already in desired state
```

**✅ Correct (idempotent)**:
```python
result = collection.update_one({"_id": id}, {"$set": {"field": value}})
return bool(result.matched_count > 0)  # Success if document exists
```

**Why**: `modified_count` is 0 when the document is already in the desired state. REST APIs should be idempotent: calling the same operation twice should succeed both times.

**See**: [Claude AI Development Guide - FastAPI Route Patterns](claude-ai-guide.md#fastapi-route-patterns) for detailed explanations and testing strategies.

---

## Base URL

**Découverte automatique de port** (depuis Issue #13) :

Le backend utilise maintenant une sélection automatique de port. Consultez les logs de démarrage ou le fichier `.dev-ports.json` pour connaître le port utilisé.

```bash
# Port découvert automatiquement, exemple :
http://localhost:54324/api

# Ports possibles :
# - Port préféré : 54321
# - Ports de fallback : 54322-54350
# - Attribution OS : port aléatoire si nécessaire
```

## Authentification

Aucune authentification requise pour l'instant (développement local).

## Endpoints

### GET /episodes

Récupère la liste de tous les épisodes.

#### Réponse

**200 OK**
```json
[
  {
    "id": "68a3911df8b628e552fdf11f", // pragma: allowlist secret // pragma: allowlist secret
    "titre": "Les nouveaux livres de Simon Chevrier, Sylvain Tesson, Gaël Octavia, L...",
    "date": "2025-08-03T10:59:59.000+00:00",
    "description": "durée : 00:51:36 - Le Masque et la Plume - par : Laurent Goumarre - Un...",
    "url": "https://proxycast.radiofrance.fr/e7ade132-cccd-4bcc-ba98-f620f9c4a0d0/...",
    "audio_rel_filename": "2025/14007-03.08.2025-ITEMA_2420925-2025F400TS0215-NET_MFI_28633905-6...",
    "transcription": " France Inter Le masque et la plume Un tour du monde sur des stacks, u...",
    "type": "livres",
    "duree": 3096,
    "description_corrigee": null
  }
]
```

**500 Internal Server Error**
```json
{
  "detail": "Erreur serveur: message d'erreur"
}
```

#### Garde-fous mémoire

L'endpoint vérifie la mémoire avant traitement :
- Limite : 500MB
- Seuil d'alerte : 400MB (80%)
- Action si dépassement : Arrêt d'urgence du serveur

---

### GET /episodes/{episode_id}

Récupère un épisode spécifique par son ID.

#### Paramètres

- `episode_id` (string, required) : ID MongoDB de l'épisode

#### Réponses

**200 OK**
```json
{
  "id": "68a3911df8b628e552fdf11f", // pragma: allowlist secret
  "titre": "Les nouveaux livres de Simon Chevrier, Sylvain Tesson, Gaël Octavia, L...",
  "date": "2025-08-03T10:59:59.000+00:00",
  "description": "durée : 00:51:36 - Le Masque et la Plume - par : Laurent Goumarre - Un...",
  "description_corrigee": "durée : 00:51:36 - Le Masque et la Plume - par : Laurent Goumarre -\n...",
  "titre_corrige": "Les nouveaux livres de Simon Chevrier, Sylvain Tesson et Gaël Octavia",
  "url": "https://proxycast.radiofrance.fr/e7ade132-cccd-4bcc-ba98-f620f9c4a0d0/...",
  "audio_rel_filename": "2025/14007-03.08.2025-ITEMA_2420925-2025F400TS0215-NET_MFI_28633905-6...",
  "transcription": " France Inter Le masque et la plume Un tour du monde sur des stacks, u...",
  "type": "livres",
  "duree": 3096
}
```

**404 Not Found**
```json
{
  "detail": "Épisode non trouvé"
}
```

**500 Internal Server Error**
```json
{
  "detail": "Erreur serveur: message d'erreur"
}
```

#### Exemple de requête

```bash
# Remplacez <PORT> par le port affiché au démarrage du backend
curl -X GET "http://localhost:<PORT>/api/episodes/68a3911df8b628e552fdf11f"
```

---

### PUT /episodes/{episode_id}

Met à jour la description corrigée d'un épisode.

#### Paramètres

- `episode_id` (string, required) : ID MongoDB de l'épisode

#### Body

**Content-Type: `text/plain`**

La nouvelle description corrigée en texte brut.

```
durée : 00:51:36 - Le Masque et la Plume - par : Laurent Goumarre -
Chronique littéraire et productrice chez France Inter,
littéraire, Hubert Artus : Journaliste et chroniqueur
Guillaume Gault
```

#### Réponses

**200 OK**
```json
{
  "message": "Description mise à jour avec succès"
}
```

**400 Bad Request**
```json
{
  "detail": "Échec de la mise à jour"
}
```

**404 Not Found**
```json
{
  "detail": "Épisode non trouvé"
}
```

**500 Internal Server Error**
```json
{
  "detail": "Erreur serveur: message d'erreur"
}
```

#### Exemple de requête

```bash
# Remplacez <PORT> par le port affiché au démarrage du backend
curl -X PUT "http://localhost:<PORT>/api/episodes/68a3911df8b628e552fdf11f" \
  -H "Content-Type: text/plain" \
  -d "Nouvelle description corrigée avec passages à la ligne"
```

#### Note importante

L'endpoint lit le body de la requête comme `text/plain` via :
```python
description_corrigee = (await request.body()).decode('utf-8')
```

---

### PUT /episodes/{episode_id}/title

Met à jour le titre corrigé d'un épisode.

#### Paramètres

- `episode_id` (string, required) : ID MongoDB de l'épisode

#### Body

**Content-Type: `text/plain`**

Le nouveau titre corrigé en texte brut.

```
Les nouveaux livres de Simon Chevrier, Sylvain Tesson et Gaël Octavia
```

#### Réponses

**200 OK**
```json
{
  "message": "Titre mis à jour avec succès"
}
```

**400 Bad Request**
```json
{
  "detail": "Échec de la mise à jour"
}
```

**404 Not Found**
```json
{
  "detail": "Épisode non trouvé"
}
```

**500 Internal Server Error**
```json
{
  "detail": "Erreur serveur: message d'erreur"
}
```

#### Exemple de requête

```bash
# Remplacez <PORT> par le port affiché au démarrage du backend
curl -X PUT "http://localhost:<PORT>/api/episodes/68a3911df8b628e552fdf11f/title" \
  -H "Content-Type: text/plain" \
  -d "Nouveau titre corrigé et plus lisible"
```

#### Note importante

L'endpoint lit le body de la requête comme `text/plain` via :
```python
titre_corrige = (await request.body()).decode('utf-8')
```

---

### DELETE /episodes/{episode_id}

Supprime un épisode et toutes ses données associées.

#### Paramètres

- `episode_id` (string, required) : ID MongoDB de l'épisode

#### Comportement

Cette opération effectue une suppression en cascade :
1. Supprime tous les avis critiques liés (`avis_critiques.episode_oid`)
2. Retire les références à l'épisode dans les livres (`livres.episodes`)
3. Supprime l'épisode lui-même

#### Réponses

**200 OK**
```json
{
  "success": true,
  "episode_id": "680c97e15a667de306e42042",
  "message": "Episode 680c97e15a667de306e42042 deleted successfully"
}
```

**404 Not Found**
```json
{
  "detail": "Episode not found"
}
```

**500 Internal Server Error**
```json
{
  "detail": "Erreur serveur: message d'erreur"
}
```

#### Exemple de requête

```bash
# Remplacez <PORT> par le port affiché au démarrage du backend
curl -X DELETE "http://localhost:<PORT>/api/episodes/680c97e15a667de306e42042"
```

#### Avertissements

⚠️ **ATTENTION** : Cette opération est irréversible !

- **Faites toujours une sauvegarde** avant de supprimer un épisode
- Les avis critiques liés seront supprimés définitivement
- Les références dans les livres seront retirées

#### Exemple d'utilisation avec MongoDB backup

```bash
# 1. Sauvegarder la base avant suppression
mongodump --db masque_et_la_plume --out /backup/$(date +%Y-%m-%d)

# 2. Supprimer l'épisode
curl -X DELETE "http://localhost:<PORT>/api/episodes/680c97e15a667de306e42042"

# 3. Vérifier la suppression
curl "http://localhost:<PORT>/api/episodes/680c97e15a667de306e42042"  # Devrait retourner 404
```

---

## Codes d'erreur

| Code | Signification | Description |
|------|---------------|-------------|
| 200  | OK           | Requête réussie |
| 400  | Bad Request  | Données invalides ou échec de l'opération |
| 404  | Not Found    | Ressource non trouvée |
| 500  | Internal Server Error | Erreur serveur interne |

## Garde-fous mémoire

Tous les endpoints intègrent une surveillance mémoire :

### Vérification
```python
memory_check = memory_guard.check_memory_limit()
if memory_check:
    if "LIMITE MÉMOIRE DÉPASSÉE" in memory_check:
        memory_guard.force_shutdown(memory_check)
    print(f"⚠️ {memory_check}")
```

### Seuils
- **Limite maximale** : 500MB
- **Seuil d'alerte** : 400MB (80%)
- **Action d'urgence** : Arrêt du processus

### Messages d'alerte
- `"Attention: utilisation mémoire élevée (XXX MB / 500 MB)"`
- `"LIMITE MÉMOIRE DÉPASSÉE - ARRÊT D'URGENCE (XXX MB / 500 MB)"`

## Modèle de données

### Episode

```python
class Episode:
    id: str
    titre: str
    date: datetime
    description: str
    description_corrigee: Optional[str]
    titre_corrige: Optional[str]
    url: str
    audio_rel_filename: str
    transcription: str
    type: str
    duree: int
```

### Mapping MongoDB

```python
def to_dict(self) -> dict[str, Any]:
    return {
        "id": str(self.data["_id"]),
        "titre": self.data.get("titre", ""),
        "date": self.data.get("date"),
        "description": self.data.get("description", ""),
        "description_corrigee": self.data.get("description_corrigee"),
        "titre_corrige": self.data.get("titre_corrige"),
        "url": self.data.get("url", ""),
        "audio_rel_filename": self.data.get("audio_rel_filename", ""),
        "transcription": self.data.get("transcription", ""),
        "type": self.data.get("type", ""),
        "duree": self.data.get("duree", 0),
    }
```

## Tests d'API

### Avec curl

```bash
# Consultez d'abord les logs backend pour connaître le port utilisé
# Exemple : "🚀 Démarrage du serveur sur 0.0.0.0:54324"

# Lister les épisodes (remplacez <PORT>)
curl -X GET "http://localhost:<PORT>/api/episodes"

# Récupérer un épisode
curl -X GET "http://localhost:<PORT>/api/episodes/68a3911df8b628e552fdf11f"

# Mettre à jour une description
curl -X PUT "http://localhost:<PORT>/api/episodes/68a3911df8b628e552fdf11f" \
  -H "Content-Type: text/plain" \
  -d "Description corrigée"

# Mettre à jour un titre
curl -X PUT "http://localhost:<PORT>/api/episodes/68a3911df8b628e552fdf11f/title" \
  -H "Content-Type: text/plain" \
  -d "Nouveau titre corrigé"
```

### Avec HTTPie

```bash
# Consultez les logs backend pour connaître le port (ex: 54324)

# Lister les épisodes
http GET localhost:<PORT>/api/episodes

# Récupérer un épisode
http GET localhost:<PORT>/api/episodes/68a3911df8b628e552fdf11f

# Mettre à jour une description
echo "Description corrigée" | http PUT localhost:<PORT>/api/episodes/68a3911df8b628e552fdf11f \
  Content-Type:text/plain

# Mettre à jour un titre
echo "Nouveau titre corrigé" | http PUT localhost:<PORT>/api/episodes/68a3911df8b628e552fdf11f/title \
  Content-Type:text/plain
```

### Documentation interactive

FastAPI génère automatiquement une documentation interactive :

- **Swagger UI** : http://localhost:<PORT>/docs
- **ReDoc** : http://localhost:<PORT>/redoc
- **OpenAPI Schema** : http://localhost:<PORT>/openapi.json

*Remplacez <PORT> par le port affiché au démarrage du backend*

## CORS Configuration

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Frontend dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Limitations connues

1. ~~**Port fixe** : Configuration hardcodée pour le frontend proxy~~ **✅ RÉSOLU (Issue #13)**
2. **Pas d'authentification** : Accès libre en développement
3. **Pas de pagination** : Tous les épisodes retournés d'un coup
4. **Pas de filtrage** : Impossible de filtrer les épisodes
5. **Pas de validation** : Schema validation basique

### POST /api/verify-babelio

**✨ NOUVEAU** - Vérification orthographique via Babelio.com

Vérifie et corrige l'orthographe des auteurs, livres et éditeurs.

#### Paramètres

**Request Body** (application/json)
```json
{
  "type": "author|book|publisher",
  "name": "string",      // Pour author ou publisher
  "title": "string",     // Pour book (requis)
  "author": "string"     // Pour book (optionnel)
}
```

#### Réponses

**200 OK - Auteur vérifié**
```json
{
  "status": "verified",
  "original": "Michel Houellebecq",
  "babelio_suggestion": "Michel Houellebecq",
  "confidence_score": 1.0,
  "babelio_data": {
    "id": "2180",
    "prenoms": "Michel",
    "nom": "Houellebecq",
    "ca_oeuvres": "38",
    "ca_membres": "30453",
    "type": "auteurs",
    "url": "/auteur/Michel-Houellebecq/2180"
  },
  "babelio_url": "https://www.babelio.com/auteur/Michel-Houellebecq/2180",
  "error_message": null
}
```

**200 OK - Auteur corrigé**
```json
{
  "status": "corrected",
  "original": "Houllebeck",
  "babelio_suggestion": "Michel Houellebecq",
  "confidence_score": 0.85,
  "babelio_data": {...},
  "babelio_url": "https://www.babelio.com/auteur/Michel-Houellebecq/2180",
  "error_message": null
}
```

**200 OK - Livre vérifié**
```json
{
  "status": "verified",
  "original_title": "Le Petit Prince",
  "babelio_suggestion_title": "Le Petit Prince",
  "original_author": "Antoine de Saint-Exupéry",
  "babelio_suggestion_author": "Antoine de Saint-Exupéry",
  "confidence_score": 1.0,
  "babelio_data": {
    "id_oeuvre": "36712",
    "titre": "Le Petit Prince",
    "nom": "Saint-Exupéry",
    "prenoms": "Antoine de",
    "ca_copies": "210108",
    "ca_note": "4.32",
    "type": "livres"
  },
  "babelio_url": "https://www.babelio.com/livres/Saint-Exupery-Le-Petit-Prince/36712",
  "error_message": null
}
```

**200 OK - Non trouvé**
```json
{
  "status": "not_found",
  "original": "Auteur Inexistant",
  "babelio_suggestion": null,
  "confidence_score": 0.0,
  "babelio_data": null,
  "babelio_url": null,
  "error_message": null
}
```

**400 Bad Request**
```json
{
  "detail": "Type invalide. Doit être 'author', 'book' ou 'publisher'"
}
```

**500 Internal Server Error**
```json
{
  "detail": "Erreur serveur: détails de l'erreur"
}
```

#### Exemples d'utilisation

```bash
# Vérifier un auteur
http POST localhost:<PORT>/api/verify-babelio \
  type=author name="Michel Houellebecq"

# Vérifier un livre
http POST localhost:<PORT>/api/verify-babelio \
  type=book title="Le Petit Prince" author="Antoine de Saint-Exupéry"

# Vérifier un éditeur
http POST localhost:<PORT>/api/verify-babelio \
  type=publisher name="Gallimard"

# Test avec faute d'orthographe
http POST localhost:<PORT>/api/verify-babelio \
  type=author name="Houllebeck"
```

#### Fonctionnalités

- ✅ **Auteurs** : Vérification et correction excellent
- ✅ **Livres** : Vérification titre + auteur excellent
- ⚠️ **Éditeurs** : Fonctionnalité limitée (recherche dans auteurs)
- 🔄 **Rate limiting** : 1 requête/seconde respectueux de Babelio
- 🔄 **Tolérance aux fautes** : Corrections automatiques intelligentes

---

## Collections Management API (Issue #66)

**✨ NOUVEAU** - Gestion automatisée des collections auteurs/livres MongoDB

### GET /api/livres-auteurs/statistics

Récupère les statistiques pour la page de gestion des collections.

#### Réponse

**200 OK**
```json
{
  "episodes_non_traites": 11,
  "couples_en_base": 128,
  "avis_critiques_analyses": 27,
  "couples_suggested_pas_en_base": 86,
  "couples_not_found_pas_en_base": 52
}
```

**500 Internal Server Error**
```json
{
  "detail": "Erreur serveur: message d'erreur"
}
```

---

### POST /api/livres-auteurs/auto-process-verified

Traite automatiquement tous les livres avec statut "verified" (validés par Babelio).

#### Réponse

**200 OK**
```json
{
  "processed_count": 15,
  "created_authors": 8,
  "created_books": 15,
  "updated_references": 25
}
```

#### Fonctionnalité

- Crée automatiquement les auteurs et livres validés par Babelio
- Évite les doublons en vérifiant l'existence avant création
- Maintient les références croisées entre collections

---

### GET /api/livres-auteurs/books/{status}

Récupère les livres par statut de validation.

#### Paramètres

- `status` (string, required) : Statut de validation (`verified`, `suggested`, `not_found`)

#### Réponse

**200 OK**
```json
[
  {
    "id": "64f1234567890abcdef12345",  // pragma: allowlist secret // pragma: allowlist secret
    "auteur": "Michel Houellebecq",
    "titre": "Les Particules élémentaires",
    "validation_status": "verified",
    "editeur": "Flammarion",
    "episode_id": "64f1234567890abcdef54321"
  }
]
```

---

### POST /api/livres-auteurs/validate-suggestion

Valide manuellement une suggestion d'auteur/livre avec corrections utilisateur.

#### Request Body

```json
{
  "id": "64f1234567890abcdef12345",  // pragma: allowlist secret  // pragma: allowlist secret
  "auteur": "Michel Houllebeck",
  "titre": "Les Particules élémentaires",
  "user_validated_author": "Michel Houellebecq",
  "user_validated_title": "Les Particules élémentaires",
  "editeur": "Flammarion"
}
```

#### Réponse

**200 OK**
```json
{
  "success": true,
  "author_id": "64f1234567890abcdef11111", // pragma: allowlist secret
  "book_id": "64f1234567890abcdef22222" // pragma: allowlist secret
}
```

---

### POST /api/livres-auteurs/add-manual-book

Ajoute manuellement un livre marqué comme "not_found" avec saisie utilisateur.

#### Request Body

```json
{
  "id": "64f1234567890abcdef12345",  // pragma: allowlist secret
  "user_entered_author": "Auteur Inconnu",
  "user_entered_title": "Livre Introuvable",
  "user_entered_publisher": "Éditeur Inconnu"
}
```

#### Réponse

**200 OK**
```json
{
  "success": true,
  "author_id": "64f1234567890abcdef11111", // pragma: allowlist secret
  "book_id": "64f1234567890abcdef22222" // pragma: allowlist secret
}
```

---

### GET /api/authors

Récupère tous les auteurs de la collection.

#### Réponse

**200 OK**
```json
[
  {
    "id": "64f1234567890abcdef11111",  // pragma: allowlist secret
    "nom": "Michel Houellebecq",
    "livres": ["64f1234567890abcdef22222"],  // pragma: allowlist secret
    "created_at": "2024-01-01T10:00:00Z",
    "updated_at": "2024-01-01T10:00:00Z"
  }
]
```

---

### GET /api/books

Récupère tous les livres de la collection.

#### Réponse

**200 OK**
```json
[
  {
    "id": "64f1234567890abcdef22222",  // pragma: allowlist secret
    "titre": "Les Particules élémentaires",
    "auteur_id": "64f1234567890abcdef11111",  // pragma: allowlist secret
    "editeur": "Flammarion",
    "episodes": ["64f1234567890abcdef33333"],  // pragma: allowlist secret
    "avis_critiques": [],
    "created_at": "2024-01-01T10:00:00Z",
    "updated_at": "2024-01-01T10:00:00Z"
  }
]
```

## Modèles de données Collections

### Author

```python
class Author:
    id: str
    nom: str
    livres: list[str]  # ObjectId references
    created_at: datetime
    updated_at: datetime
```

### Book

```python
class Book:
    id: str
    titre: str
    auteur_id: str  # ObjectId reference
    editeur: str
    episodes: list[str]  # ObjectId references
    avis_critiques: list[str]  # ObjectId references
    created_at: datetime
    updated_at: datetime
```

### Request Models

#### ValidateSuggestionRequest
```python
class ValidateSuggestionRequest:
    id: str
    auteur: str
    titre: str
    user_validated_author: Optional[str]
    user_validated_title: Optional[str]
    editeur: Optional[str]
```

#### AddManualBookRequest
```python
class AddManualBookRequest:
    id: str
    user_entered_author: str
    user_entered_title: str
    user_entered_publisher: Optional[str]
```

---

## Detail Pages API (Issue #96)

Endpoints pour récupérer les informations détaillées d'un auteur ou d'un livre avec leurs relations.

### GET /api/auteur/{auteur_id}

Récupère les détails d'un auteur avec tous ses livres.

#### Paramètres

- `auteur_id` (path, required): ObjectId MongoDB de l'auteur (24 caractères hexadécimaux)

#### Réponse

**200 OK**
```json
{
  "nom": "Albert Camus",
  "nombre_livres": 3,
  "livres": [
    {
      "_id": "68e2c3ba1391489c77ccdee2",  // pragma: allowlist secret
      "titre": "L'Étranger",
      "editeur": "Gallimard",
      "nombre_episodes": 2
    },
    {
      "_id": "68e2c3ba1391489c77ccdee3",  // pragma: allowlist secret
      "titre": "La Peste",
      "editeur": "Gallimard",
      "nombre_episodes": 1
    }
  ]
}
```

**Notes**:
- Les livres sont triés alphabétiquement par titre
- Utilise une agrégation MongoDB avec `$lookup` pour joindre les collections `auteurs` et `livres`

**400 Bad Request** - ID invalide
```json
{
  "detail": "auteur_id must be a valid MongoDB ObjectId (24 hex characters)"
}
```

**404 Not Found** - Auteur non trouvé
```json
{
  "detail": "Author not found"
}
```

### GET /api/livre/{livre_id}

Récupère les détails d'un livre avec tous les épisodes où il est mentionné.

#### Paramètres

- `livre_id` (path, required): ObjectId MongoDB du livre (24 caractères hexadécimaux)

#### Réponse

**200 OK**
```json
{
  "_id": "68e2c3ba1391489c77ccdee2",  // pragma: allowlist secret
  "titre": "L'Étranger",
  "auteur_nom": "Albert Camus",
  "auteur_id": "68e2c3ba1391489c77ccdee1",  // pragma: allowlist secret
  "editeur": "Gallimard",
  "nombre_episodes": 2,
  "episodes": [
    {
      "episode_id": "68c707ad6e51b9428ab87e9e",  // pragma: allowlist secret
      "titre": "Les nouvelles pages du polar",
      "date": "2025-01-12",
      "programme": true
    },
    {
      "episode_id": "68c707ad6e51b9428ab87e9f",  // pragma: allowlist secret
      "titre": "Spécial rentrée littéraire",
      "date": "2024-09-05",
      "programme": false
    }
  ]
}
```

**Notes**:
- Les épisodes incluent un flag `programme` indiquant si le livre était au programme (true) ou coup de cœur (false)
- Utilise une agrégation MongoDB avec `$lookup` pour joindre les collections

**400 Bad Request** - ID invalide
```json
{
  "detail": "livre_id must be a valid MongoDB ObjectId (24 hex characters)"
}
```

**404 Not Found** - Livre non trouvé
```json
{
  "detail": "Book not found"
}
```

### GET /api/critique/{critique_id}

Récupère les détails d'un critique avec statistiques, distribution des notes, coups de cœur et liste des œuvres critiquées.

#### Paramètres

- `critique_id` (path, required): ObjectId MongoDB du critique (24 caractères hexadécimaux)

#### Réponse

**200 OK**
```json
{
  "critique_id": "694eb58bffd25d11ce052759",  // pragma: allowlist secret
  "nom": "Arnaud Viviant",
  "animateur": false,
  "variantes": ["Arnaud Vivian"],
  "nombre_avis": 838,
  "note_moyenne": 6.8,
  "note_distribution": {
    "2": 31, "3": 72, "4": 72, "5": 66,
    "6": 75, "7": 80, "8": 188, "9": 223, "10": 31
  },
  "coups_de_coeur": [
    {
      "livre_oid": "6948458b4c7793c317f9f795",  // pragma: allowlist secret
      "livre_titre": "Combats de filles",
      "auteur_nom": "Rita Bullwinkel",
      "auteur_oid": "694845004c7793c317f9f700",  // pragma: allowlist secret
      "editeur": "La Croisée",
      "note": 9,
      "commentaire": "Très belle découverte",
      "section": "programme",
      "emission_date": "2026-01-18",
      "emission_oid": "694fea91e46eedc769bcd996"  // pragma: allowlist secret
    }
  ],
  "oeuvres": [
    {
      "livre_oid": "6948458b4c7793c317f9f795",  // pragma: allowlist secret
      "livre_titre": "Combats de filles",
      "auteur_nom": "Rita Bullwinkel",
      "auteur_oid": "694845004c7793c317f9f700",  // pragma: allowlist secret
      "editeur": "La Croisée",
      "note": 9,
      "commentaire": "Très belle découverte",
      "section": "programme",
      "emission_date": "2026-01-18",
      "emission_oid": "694fea91e46eedc769bcd996"  // pragma: allowlist secret
    }
  ]
}
```

**Notes**:
- Les coups de cœur sont les avis avec une note >= 9
- La distribution des notes utilise des clés string de "2" à "10"
- Les œuvres sont triées par date d'émission décroissante
- Batch-lookup des livres, auteurs et émissions pour enrichir chaque avis
- Types MongoDB : `critique_oid` dans `avis` est String, `critiques._id` est ObjectId

**404 Not Found** - Critique non trouvé
```json
{
  "detail": "Critique non trouvé"
}
```

---

## Search API

Moteur de recherche textuelle multi-collections avec support de pagination et filtres avancés.

### GET /api/search

Recherche textuelle simple dans les collections MongoDB (épisodes, auteurs, livres, éditeurs).

#### Paramètres

- `q` (string, required) : Terme de recherche (minimum 3 caractères)
- `limit` (int, optional) : Nombre maximum de résultats par catégorie (défaut: 10)

#### Réponse

**200 OK**
```json
{
  "query": "camus",
  "results": {
    "auteurs": [
      {
        "id": "64f1234567890abcdef11111",  // pragma: allowlist secret
        "nom": "Albert Camus",
        "livres": ["64f1234567890abcdef22222"]  // pragma: allowlist secret
      }
    ],
    "auteurs_total_count": 1,
    "livres": [
      {
        "id": "64f1234567890abcdef22222",  // pragma: allowlist secret
        "titre": "L'Étranger",
        "auteur_id": "64f1234567890abcdef11111",  // pragma: allowlist secret
        "auteur_nom": "Albert Camus",
        "editeur": "Gallimard",
        "episodes": []
      }
    ],
    "livres_total_count": 1,
    "editeurs": [
      {
        "id": "64f1234567890abcdef33333",  // pragma: allowlist secret
        "nom": "Gallimard"
      }
    ],
    "episodes": [
      {
        "id": "64f1234567890abcdef44444",  // pragma: allowlist secret
        "titre": "Épisode sur Camus",
        "date": "2025-08-03T10:59:59.000+00:00",
        "search_context": "...discussion sur Albert Camus et son œuvre majeure..."
      }
    ],
    "episodes_total_count": 15
  }
}
```

**400 Bad Request**
```json
{
  "detail": "Le paramètre 'q' est requis et doit contenir au moins 3 caractères"
}
```

#### Fonctionnalités

- ✅ **Recherche auteurs** : Regex case-insensitive sur `auteurs.nom`
- ✅ **Recherche livres** : Regex sur `livres.titre` et `livres.editeur`
- ✅ **Enrichissement auteur** : Livres incluent automatiquement `auteur_nom` via lookup
- ✅ **Recherche épisodes** : Regex sur titre/description/transcription avec extraction de contexte
- ✅ **Recherche éditeurs** : Via collection `avis_critiques`
- ✅ **Compteurs intelligents** : Affiche résultats limités + total réel

#### Exemples d'utilisation

```bash
# Recherche d'auteur
curl "http://localhost:<PORT>/api/search?q=camus&limit=10"

# Recherche de livre
curl "http://localhost:<PORT>/api/search?q=étranger"

# Recherche d'éditeur
curl "http://localhost:<PORT>/api/search?q=gallimard"

# Recherche dans épisodes
curl "http://localhost:<PORT>/api/search?q=littérature"
```

#### Notes techniques

**Fonctionnalités** :
- Moteur de recherche de base avec épisodes
- Extraction de contexte (10 mots avant/après)
- Surlignage frontend avec highlighting
- Recherche étendue aux collections dédiées `auteurs` et `livres`
- Enrichissement automatique avec noms d'auteurs
- Affichage format "auteur - titre" dans l'interface

---

### GET /api/advanced-search

Recherche avancée avec filtres par entité et pagination complète.

#### Paramètres

- `q` (string, required) : Terme de recherche (minimum 3 caractères)
- `entities` (string, optional) : Filtres séparés par virgules : `episodes,auteurs,livres,editeurs` (défaut: toutes)
- `page` (int, optional) : Numéro de page (défaut: 1)
- `limit` (int, optional) : Résultats par page (10, 20, 50, 100, défaut: 10)

#### Réponse

**200 OK**
```json
{
  "query": "camus",
  "filters": ["episodes", "auteurs", "livres", "editeurs"],
  "page": 1,
  "limit": 10,
  "results": {
    "auteurs": [
      {
        "id": "64f1234567890abcdef11111",  // pragma: allowlist secret
        "nom": "Albert Camus",
        "livres": ["64f1234567890abcdef22222"]  // pragma: allowlist secret
      }
    ],
    "auteurs_total_count": 1,
    "livres": [
      {
        "id": "64f1234567890abcdef22222",  // pragma: allowlist secret
        "titre": "L'Étranger",
        "auteur_id": "64f1234567890abcdef11111",  // pragma: allowlist secret
        "auteur_nom": "Albert Camus",
        "editeur": "Gallimard",
        "episodes": []
      }
    ],
    "livres_total_count": 2,
    "editeurs": [
      {
        "nom": "Gallimard"
      }
    ],
    "editeurs_total_count": 1,
    "episodes": [
      {
        "id": "64f1234567890abcdef44444",  // pragma: allowlist secret
        "titre": "Épisode sur Camus",
        "date": "2025-08-03T10:59:59.000+00:00",
        "search_context": "...discussion sur Albert Camus et son œuvre majeure..."
      }
    ],
    "episodes_total_count": 15
  }
}
```

**400 Bad Request**
```json
{
  "detail": "Le paramètre 'q' est requis et doit contenir au moins 3 caractères"
}
```

#### Fonctionnalités

- ✅ **Filtres par entité** : Recherche ciblée sur une ou plusieurs catégories
- ✅ **Pagination complète** : Navigation par page avec offset/limit
- ✅ **Compteurs totaux** : `*_total_count` indique le nombre total de résultats
- ✅ **Résultats limités** : Chaque catégorie respecte la limite par page
- ✅ **Sources unifiées** : Éditeurs recherchés dans `editeurs.nom` + `livres.editeur` (dédupliqués)
- ✅ **Recherche auteurs** : Regex case-insensitive sur `auteurs.nom`
- ✅ **Recherche livres** : Regex sur `livres.titre` uniquement (pas `editeur`)
- ✅ **Recherche éditeurs** : Multi-source avec déduplication automatique
- ✅ **Recherche épisodes** : Regex sur titre/description/transcription avec extraction de contexte
- ✅ **Enrichissement auteur** : Livres incluent automatiquement `auteur_nom` via lookup

#### Exemples d'utilisation

```bash
# Recherche tous types avec pagination
curl "http://localhost:<PORT>/api/advanced-search?q=camus&page=1&limit=10"

# Recherche uniquement auteurs et livres
curl "http://localhost:<PORT>/api/advanced-search?q=camus&entities=auteurs,livres"

# Recherche éditeurs avec limite élevée
curl "http://localhost:<PORT>/api/advanced-search?q=gallimard&entities=editeurs&limit=100"

# Recherche page 2 des épisodes
curl "http://localhost:<PORT>/api/advanced-search?q=littérature&entities=episodes&page=2&limit=20"
```

#### Notes techniques - Pagination des éditeurs

**Problème résolu** : Les éditeurs sont recherchés dans deux sources :
1. Collection `editeurs.nom`
2. Champ `livres.editeur`

**Déduplication** : Le compteur total reflète le nombre d'éditeurs **uniques** après déduplication :

```python
# Mauvais (ancien code) - causait pagination incorrecte
total_count = total_count_editeurs + total_count_livres
# Exemple : 1 + 3 = 4 → 3 pages affichées pour 1 résultat unique

# Correct (code actuel) - compte les uniques
total_count = len(editeurs_set)
# Exemple : 1 → 1 page affichée pour 1 résultat unique
```

**Impact sur pagination** :
- `editeurs_total_count` = nombre d'éditeurs uniques trouvés
- Évite les doublons si un éditeur existe dans les deux sources
- Pagination correcte basée sur les résultats réels affichés

---

## Palmares API

Endpoint pour récupérer le classement des livres par note moyenne décroissante, avec enrichissement Calibre.

### GET /api/palmares

Récupère la liste paginée des livres classés par note moyenne (minimum 2 avis).

#### Paramètres

- `page` (query, optional, default=1): Numéro de page
- `limit` (query, optional, default=30): Nombre d'éléments par page

#### Réponse

**200 OK**
```json
{
  "items": [
    {
      "livre_id": "6956ba2affd13096430f9cb9",
      "titre": "Le Lambeau",
      "auteur_id": "6950027a26f38eb0ca5aabed",
      "auteur_nom": "Philippe Lançon",
      "note_moyenne": 10.0,
      "nombre_avis": 4,
      "url_babelio": "https://www.babelio.com/...",
      "calibre_in_library": true,
      "calibre_read": true,
      "calibre_rating": 8
    }
  ],
  "total": 861,
  "page": 1,
  "limit": 30,
  "total_pages": 29
}
```

**Notes**:

- Pipeline MongoDB `$facet` pour pagination serveur avec comptage total en une seule requête
- Enrichissement Calibre via matching par titre normalisé (NFKD, case-insensitive)
- `calibre_rating` est `null` si le livre n'est pas lu (même s'il a une note dans Calibre)
- Si Calibre n'est pas disponible, les champs `calibre_*` sont `false`/`null`

---

## Roadmap API

- [ ] Authentification JWT
- [ ] Pagination des résultats
- [ ] Validation Pydantic stricte
- [ ] Rate limiting
- [ ] Versioning API (v1, v2)
- [ ] Endpoints de métadonnées (/health, /metrics)
- [x] **Intégration Babelio** ✅ COMPLETED
- [x] **Gestion Collections Auteurs/Livres** ✅ COMPLETED (Issue #66)
- [x] **Moteur de Recherche Multi-Collections** ✅ COMPLETED (Issues #49 + #68)
