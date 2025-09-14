# Documentation API - Back-Office LMELP

## Base URL

**Découverte automatique de port** (depuis Issue #13) :

Le backend utilise maintenant une sélection automatique de port. Consultez les logs de démarrage ou le fichier `.backend-port.json` pour connaître le port utilisé.

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
# Remplacez [PORT] par le port affiché au démarrage du backend
curl -X GET "http://localhost:[PORT]/api/episodes/68a3911df8b628e552fdf11f"
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
# Remplacez [PORT] par le port affiché au démarrage du backend
curl -X PUT "http://localhost:[PORT]/api/episodes/68a3911df8b628e552fdf11f" \
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
# Remplacez [PORT] par le port affiché au démarrage du backend
curl -X PUT "http://localhost:[PORT]/api/episodes/68a3911df8b628e552fdf11f/title" \
  -H "Content-Type: text/plain" \
  -d "Nouveau titre corrigé et plus lisible"
```

#### Note importante

L'endpoint lit le body de la requête comme `text/plain` via :
```python
titre_corrige = (await request.body()).decode('utf-8')
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

# Lister les épisodes (remplacez [PORT])
curl -X GET "http://localhost:[PORT]/api/episodes"

# Récupérer un épisode
curl -X GET "http://localhost:[PORT]/api/episodes/68a3911df8b628e552fdf11f"

# Mettre à jour une description
curl -X PUT "http://localhost:[PORT]/api/episodes/68a3911df8b628e552fdf11f" \
  -H "Content-Type: text/plain" \
  -d "Description corrigée"

# Mettre à jour un titre
curl -X PUT "http://localhost:[PORT]/api/episodes/68a3911df8b628e552fdf11f/title" \
  -H "Content-Type: text/plain" \
  -d "Nouveau titre corrigé"
```

### Avec HTTPie

```bash
# Consultez les logs backend pour connaître le port (ex: 54324)

# Lister les épisodes
http GET localhost:[PORT]/api/episodes

# Récupérer un épisode
http GET localhost:[PORT]/api/episodes/68a3911df8b628e552fdf11f

# Mettre à jour une description
echo "Description corrigée" | http PUT localhost:[PORT]/api/episodes/68a3911df8b628e552fdf11f \
  Content-Type:text/plain

# Mettre à jour un titre
echo "Nouveau titre corrigé" | http PUT localhost:[PORT]/api/episodes/68a3911df8b628e552fdf11f/title \
  Content-Type:text/plain
```

### Documentation interactive

FastAPI génère automatiquement une documentation interactive :

- **Swagger UI** : http://localhost:[PORT]/docs
- **ReDoc** : http://localhost:[PORT]/redoc
- **OpenAPI Schema** : http://localhost:[PORT]/openapi.json

*Remplacez [PORT] par le port affiché au démarrage du backend*

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
http POST localhost:[PORT]/api/verify-babelio \
  type=author name="Michel Houellebecq"

# Vérifier un livre
http POST localhost:[PORT]/api/verify-babelio \
  type=book title="Le Petit Prince" author="Antoine de Saint-Exupéry"

# Vérifier un éditeur
http POST localhost:[PORT]/api/verify-babelio \
  type=publisher name="Gallimard"

# Test avec faute d'orthographe
http POST localhost:[PORT]/api/verify-babelio \
  type=author name="Houllebeck"
```

#### Fonctionnalités

- ✅ **Auteurs** : Vérification et correction excellent
- ✅ **Livres** : Vérification titre + auteur excellent
- ⚠️ **Éditeurs** : Fonctionnalité limitée (recherche dans auteurs)
- 🔄 **Rate limiting** : 1 requête/seconde respectueux de Babelio
- 🔄 **Tolérance aux fautes** : Corrections automatiques intelligentes

## Roadmap API

- [ ] Authentification JWT
- [ ] Pagination des résultats
- [ ] Filtrage et recherche d'épisodes
- [ ] Validation Pydantic stricte
- [ ] Rate limiting
- [ ] Versioning API (v1, v2)
- [ ] Endpoints de métadonnées (/health, /metrics)
- [x] **Intégration Babelio** ✅ COMPLETED
