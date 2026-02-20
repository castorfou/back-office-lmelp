# Génération LLM d'Avis Critiques - Architecture

## Vue d'ensemble

Le système de génération LLM transforme les transcriptions Whisper d'épisodes en résumés structurés des avis critiques. Le processus utilise Azure OpenAI (GPT-4o) et se déroule en deux phases distinctes pour garantir la qualité et la précision des informations.

**Architecture en 2 phases** :
- **Phase 1 (Extraction)** : Extrait les informations depuis la transcription Whisper
- **Phase 2 (Correction)** : Corrige l'orthographe des noms propres via le contenu de la page RadioFrance

**Optimisation parallèle** : Phase 1 et fetch URL RadioFrance s'exécutent simultanément avec `asyncio.gather()`.

## Service Principal

### `AvisCritiquesGenerationService`

**Fichier** : `src/back_office_lmelp/services/avis_critiques_generation_service.py`

**Singleton** : `avis_critiques_generation_service` (instance globale)

#### Configuration Azure OpenAI

```python
# Variables d'environnement requises
AZURE_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_API_KEY=your_key_here
AZURE_API_VERSION=2024-09-01-preview  # Défaut
AZURE_DEPLOYMENT_NAME=gpt-4o  # Défaut

# Debug logging (optionnel)
AVIS_CRITIQUES_DEBUG_LOG=1  # Active logs détaillés
```

Le client Azure OpenAI est initialisé dans `__init__()` avec validation des variables d'environnement.

#### Méthode principale : `generate_full_summary()`

```python
async def generate_full_summary(
    transcription: str,
    episode_date: str,
    episode_page_url: str | None,
    episode_id: str | None = None
) -> dict[str, Any]:
    """
    Orchestrateur complet du processus de génération.

    Returns:
        {
            "summary": str,  # Résumé final (Phase 2 corrigé)
            "summary_phase1": str,  # Résumé brut (backup)
            "metadata": dict,  # Métadonnées RadioFrance
            "corrections_applied": list[dict],  # Corrections détectées
            "warnings": list[str]  # Avertissements éventuels
        }
    """
```

**Workflow** :

1. **Exécution parallèle** (si URL non disponible) :
   ```python
   summary_phase1, fetched_url = await asyncio.gather(
       self.generate_summary_phase1(transcription, episode_date),
       fetch_episode_url()  # Recherche + mise à jour MongoDB
   )
   ```

2. **Extraction métadonnées** :
   ```python
   metadata = await radiofrance_service.extract_episode_metadata(episode_page_url)
   page_content = metadata.get("page_text", "")  # Contenu complet page
   ```

3. **Phase 2 - Correction** :
   ```python
   summary_phase2 = await self.enhance_summary_phase2(
       summary_phase1, metadata, page_content
   )
   ```

4. **Détection corrections** :
   ```python
   corrections_applied = self._detect_corrections(summary_phase1, summary_phase2)
   ```

### Phase 1 : Extraction depuis transcription

#### `generate_summary_phase1(transcription, episode_date)`

**Objectif** : Extraire informations structurées depuis transcription Whisper.

**Paramètres LLM** :
```python
model=self.deployment_name,  # gpt-4o
max_tokens=8000,
temperature=0.1,  # Faible pour consistance
timeout=120  # 2 minutes
```

**Retry logic** :
```python
max_retries = 1  # 2 tentatives au total
for attempt in range(max_retries + 1):
    try:
        response = await asyncio.wait_for(
            asyncio.to_thread(self.client.chat.completions.create, ...),
            timeout=120
        )
        return response.choices[0].message.content
    except TimeoutError:
        if attempt < max_retries:
            await asyncio.sleep(2)  # Attente avant retry
            continue
        raise
```

**Format de sortie attendu** :

```markdown
## 1. LIVRES DISCUTÉS AU PROGRAMME du DD mois YYYY

| Auteur | Titre | Éditeur | Avis détaillés des critiques | Note moyenne | Nb critiques | Coup de cœur | Chef d'œuvre |
|--------|-------|---------|------------------------------|--------------|-------------|-------------|-------------|
| ... | ... | ... | **Critique 1**: avis (note) <br>**Critique 2**: avis (note) | 8.5 | 3 | Critique 1 | - |

## 2. COUPS DE CŒUR DES CRITIQUES du DD mois YYYY

| Auteur | Titre | Éditeur | Critique | Note | Commentaire |
|--------|-------|---------|----------|------|-------------|
| ... | ... | ... | Critique 1 | 9.0 | ... |
```

**Validation format** :
```python
def _is_valid_markdown_format(summary: str) -> bool:
    # Vérifier présence titre section
    if not re.search(r"## 1\. LIVRES DISCUT", summary):
        return False

    # Vérifier présence tableaux markdown
    if "|" not in summary:
        return False

    # Longueur minimale
    return len(summary) >= 200
```

**Formatage dates en français** :

```python
mois_fr = {
    1: "janvier", 2: "février", 3: "mars", 4: "avril",
    5: "mai", 6: "juin", 7: "juillet", 8: "août",
    9: "septembre", 10: "octobre", 11: "novembre", 12: "décembre"
}

date_obj = datetime.strptime(episode_date, "%Y-%m-%d")
date_str = f" du {date_obj.day} {mois_fr[date_obj.month]} {date_obj.year}"
```

### Phase 2 : Correction orthographique

#### `enhance_summary_phase2(summary_phase1, episode_metadata, page_content)`

**Objectif** : Corriger noms propres (auteurs, critiques, titres) avec données RadioFrance.

**Paramètres LLM** :
```python
messages=[
    {"role": "system", "content": "Tu es un correcteur orthographique..."},
    {"role": "user", "content": prompt}
],
max_tokens=8000,
temperature=0.1,
timeout=60  # 1 minute
```

**Sources de correction** :

1. **Métadonnées RadioFrance** :
   ```python
   metadata = {
       "animateur": "Jérôme Garcin",
       "critiques": ["Elisabeth Philippe", "Frédéric Beigbeder", ...],
       "date": "2024-01-15",
       "page_text": "..."  # Contenu complet page HTML
   }
   ```

2. **Contenu page RadioFrance** (max 3000 premiers caractères) :
   - Section livres du programme : `« Titre », de Auteur (Éditeur)`
   - Section coups de cœur : `"Critique: Titre, de Auteur (Éditeur)"`

**Validation préservation structure** :

```python
# Phase 2 doit préserver format markdown Phase 1
if not self._is_valid_markdown_format(summary_phase2):
    logger.warning("Phase 2 a cassé la structure, fallback Phase 1")
    return summary_phase1
```

**Fallback automatique** :

La Phase 2 ne lève jamais d'exception. En cas d'erreur, elle retourne le résultat de Phase 1 :

```python
try:
    summary_phase2 = await self.enhance_summary_phase2(...)
    return summary_phase2
except Exception as e:
    logger.warning(f"Erreur Phase 2, fallback Phase 1: {e}")
    return summary_phase1
```

### Détection des corrections

#### `_detect_corrections(summary_phase1, summary_phase2)`

**Algorithme** : Comparaison ligne par ligne avec détection différences de mots.

```python
corrections = []
lines1 = summary_phase1.split("\n")
lines2 = summary_phase2.split("\n")

for i, (line1, line2) in enumerate(zip(lines1, lines2)):
    if line1 != line2:
        words1 = set(line1.split())
        words2 = set(line2.split())

        removed = words1 - words2
        added = words2 - words1

        if removed and added:
            corrections.append({
                "field": f"ligne {i + 1}",
                "before": " ".join(removed)[:50],
                "after": " ".join(added)[:50]
            })

return corrections[:10]  # Limiter à 10 affichées
```

## API Endpoints

### POST `/api/avis-critiques/generate`

**Objectif** : Générer le résumé d'avis critiques en 2 phases.

**Request Body** :
```json
{
  "episode_id": "507f1f77bcf86cd799439011"  // pragma: allowlist secret
}
```

**Response** :
```json
{
  "summary": "...",  // Résumé final (Phase 2)
  "summary_phase1": "...",  // Résumé brut (backup)
  "metadata": {
    "animateur": "Jérôme Garcin",
    "critiques": ["Elisabeth Philippe", ...],
    "date": "2024-01-15"
  },
  "corrections_applied": [
    {
      "field": "ligne 12",
      "before": "Houllebeck",
      "after": "Houellebecq"
    }
  ],
  "warnings": []
}
```

**Implémentation** (`app.py:2895-2982`) :

```python
@app.post("/api/avis-critiques/generate")
async def generate_avis_critiques(request: Request) -> JSONResponse:
    data = await request.json()
    episode_id = data.get("episode_id")

    # Validation épisode
    episode = mongodb_service.get_episode_by_id(episode_id)
    if not episode:
        raise HTTPException(status_code=404, detail="Épisode non trouvé")

    # Validation transcription
    if not episode.get("transcription_whisper"):
        raise HTTPException(status_code=400, detail="Transcription manquante")

    # Génération complète
    result = await avis_critiques_generation_service.generate_full_summary(
        transcription=episode["transcription_whisper"],
        episode_date=episode_date,
        episode_page_url=episode.get("episode_page_url"),
        episode_id=episode_id
    )

    return JSONResponse(content=result)
```

### POST `/api/avis-critiques/save`

**Objectif** : Sauvegarder le résumé généré dans MongoDB.

**Request Body** :
```json
{
  "episode_id": "507f1f77bcf86cd799439011",  // pragma: allowlist secret
  "summary": "## 1. LIVRES DISCUTÉS...",
  "summary_phase1": "...",
  "metadata": {
    "animateur": "...",
    "critiques": [...]
  }
}
```

**Validation backend** (5 critères) :

```python
def _validate_summary(summary: str) -> tuple[bool, str | None]:
    """Valide le résumé avant sauvegarde."""

    # 1. Non vide
    if not summary or not summary.strip():
        return False, "Le résumé est vide"

    # 2. Longueur raisonnable (< 50000 chars)
    if len(summary) > 50000:
        return False, "Le résumé est anormalement long (malformé)"

    # 3. Pas d'espaces excessifs (bug LLM)
    if re.search(r' {100,}', summary):
        return False, "Le résumé contient trop d'espaces consécutifs (malformé)"

    # 4. Section "LIVRES DISCUTÉS" présente
    if "LIVRES DISCUTÉS" not in summary:
        return False, "Section 'LIVRES DISCUTÉS' manquante"

    # 5. Section "COUPS DE CŒUR" présente
    if "COUPS DE CŒUR" not in summary:
        return False, "Section 'COUPS DE CŒUR' manquante"

    return True, None
```

**Implémentation** (`app.py:3017-3100`) :

```python
@app.post("/api/avis-critiques/save")
async def save_avis_critiques(request: Request) -> JSONResponse:
    data = await request.json()

    # Validation résumé
    is_valid, error_msg = _validate_summary(data["summary"])
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)

    # Nettoyage metadata (retirer page_text volumineux)
    metadata_clean = {
        k: v for k, v in data["metadata"].items()
        if k != "page_text"
    }

    avis_data = {
        "episode_oid": data["episode_id"],
        "episode_title": episode_title,
        "episode_date": episode_date,
        "summary": data["summary"],
        "summary_phase1": data["summary_phase1"],
        "summary_origin": "llm_generation_phase2",
        "metadata_source": metadata_clean,
        "updated_at": datetime.now(UTC)
    }

    # Insert ou Update
    existing = mongodb_service.avis_critiques_collection.find_one(
        {"episode_oid": data["episode_id"]}
    )

    if existing:
        mongodb_service.avis_critiques_collection.update_one(
            {"episode_oid": data["episode_id"]},
            {"$set": avis_data}
        )
        avis_id = str(existing["_id"])
    else:
        avis_data["created_at"] = datetime.now(UTC)
        result = mongodb_service.avis_critiques_collection.insert_one(avis_data)
        avis_id = str(result.inserted_id)

    return JSONResponse(content={"success": True, "avis_critique_id": avis_id})
```

### GET `/api/avis-critiques/episodes-sans-avis`

**Objectif** : Liste des épisodes éligibles pour génération LLM.

**Critères** :
- Episodes **non masqués** (`masque != true`)
- Avec **transcription disponible** (`transcription_whisper` non vide)
- Tri par date décroissante (plus récents d'abord)

**Response** :
```json
[
  {
    "id": "507f1f77bcf86cd799439011",  // pragma: allowlist secret
    "titre": "Les nouvelles pages du polar",
    "date": "2024-01-15T00:00:00",
    "has_avis_critiques": false
  }
]
```

### GET `/api/avis-critiques/{episode_id}`

**Objectif** : Récupérer le résumé existant d'un épisode.

**Response** (si existant) :
```json
{
  "episode_oid": "507f1f77bcf86cd799439011",  // pragma: allowlist secret
  "summary": "## 1. LIVRES DISCUTÉS...",
  "summary_phase1": "...",
  "metadata_source": {...}
}
```

**Response** (si non existant) : HTTP 404

## Structure MongoDB

### Collection `avis_critiques`

**Schéma** :

```javascript
{
  "_id": ObjectId,
  "episode_oid": String,  // Référence vers episodes._id (STRING, pas ObjectId)
  "episode_title": String,
  "episode_date": String,  // Format YYYY-MM-DD
  "summary": String,  // Résumé final (Phase 2)
  "summary_phase1": String,  // Résumé brut (backup)
  "summary_origin": String,  // "llm_generation_phase2"
  "metadata_source": {
    "animateur": String,
    "critiques": [String],
    "date": String
    // Note: "page_text" retiré pour économie stockage
  },
  "created_at": DateTime,
  "updated_at": DateTime
}
```

**Indexes** :
```javascript
{ "episode_oid": 1 }  // Unique, recherche rapide par épisode
```

## Gestion des erreurs

### Erreurs Azure OpenAI

**Timeout après retry** :
```python
# Phase 1: max_retries=1 (2 tentatives), timeout=120s
try:
    response = await asyncio.wait_for(..., timeout=120)
except TimeoutError:
    if attempt < max_retries:
        await asyncio.sleep(2)
        continue
    raise TimeoutError("Timeout génération Phase 1")
```

**Client non configuré** :
```python
if not self.client:
    raise ValueError("Client Azure OpenAI non configuré")
```

**Validation format échouée** :
```python
if not self._is_valid_markdown_format(summary):
    raise ValueError("Format markdown invalide")
```

### Erreurs API

**Episode non trouvé** : HTTP 404
```python
if not episode:
    raise HTTPException(status_code=404, detail="Épisode non trouvé")
```

**Transcription manquante** : HTTP 400
```python
if not episode.get("transcription_whisper"):
    raise HTTPException(status_code=400, detail="Transcription manquante")
```

**Validation résumé échouée** : HTTP 400
```python
is_valid, error_msg = _validate_summary(summary)
if not is_valid:
    raise HTTPException(status_code=400, detail=error_msg)
```

**Erreur interne** : HTTP 500
```python
except Exception as e:
    logger.error(f"Erreur génération: {e}")
    raise HTTPException(status_code=500, detail=str(e))
```

## Debug et logging

### Activation logs debug

```bash
export AVIS_CRITIQUES_DEBUG_LOG=1
```

**Logs additionnels** :
- Nombre de caractères générés par phase
- Extraits des résumés Phase 1 et Phase 2 (500 premiers chars)
- Comparaison détaillée Phase 1 vs Phase 2
- Tentatives de retry

**Exemple** :
```python
if self._debug_log_enabled:
    logger.info(f"Phase 1 réussie: {len(summary)} caractères générés")
    logger.info(f"📄 PHASE 1 OUTPUT (extrait):\n{summary[:500]}...")

    logger.info("=" * 80)
    logger.info("🔍 COMPARAISON PHASE 1 vs PHASE 2:")
    logger.info("📄 summary_phase1 (brut):")
    logger.info(summary_phase1[:500] + "...")
    logger.info("-" * 80)
    logger.info("📄 summary (phase2, corrigé):")
    logger.info(summary_phase2[:500] + "...")
    logger.info("=" * 80)
```

### Logs standards (toujours actifs)

```python
logger.info("✅ Phase 1 et Fetch URL terminés")
logger.info(f"🔍 Extraction métadonnées depuis: {episode_page_url}")
logger.info(f"✅ Métadonnées extraites: animateur={...}, critiques={...}")
logger.info(f"📄 Contenu page RadioFrance: {len(page_content)} caractères")
logger.info(f"📝 {len(corrections_applied)} correction(s) détectée(s)")
logger.info("✅ Phase 2 terminée")
```

## Tests

### Tests unitaires

**Fichier** : `tests/test_avis_critiques_generation_service.py`

**Skip conditionnel** (si Azure OpenAI non configuré) :
```python
skip_if_no_azure = pytest.mark.skipif(
    os.getenv("AZURE_ENDPOINT") is None,
    reason="Azure OpenAI non configuré (CI/CD)"
)

class TestAvisCritiquesGenerationService:
    @skip_if_no_azure
    async def test_generate_summary_phase1(self):
        # Test avec vraie API Azure OpenAI
        ...
```

**Coverage** :
- Phase 1 : génération, retry logic, validation format
- Phase 2 : correction, fallback, préservation structure
- `generate_full_summary()` : orchestration parallèle
- Validation : 5 critères de validation résumé
- Détection corrections

### Tests d'intégration

**Fichier** : `tests/test_api_avis_critiques.py`

**Mocking** :
```python
@pytest.fixture
def mock_generation_service(monkeypatch):
    """Mock du service de génération."""
    mock_result = {
        "summary": "## 1. LIVRES DISCUTÉS...",
        "summary_phase1": "...",
        "metadata": {...},
        "corrections_applied": [],
        "warnings": []
    }

    async def mock_generate(*args, **kwargs):
        return mock_result

    monkeypatch.setattr(
        avis_critiques_generation_service,
        "generate_full_summary",
        mock_generate
    )
```

**Coverage endpoints** :
- `POST /api/avis-critiques/generate`
- `POST /api/avis-critiques/save` avec validation
- `GET /api/avis-critiques/episodes-sans-avis`
- `GET /api/avis-critiques/{episode_id}`

## Optimisations

### Exécution parallèle

**Pattern `asyncio.gather()`** :

```python
# Lancer Phase 1 et fetch URL en PARALLÈLE
summary_phase1, fetched_url = await asyncio.gather(
    self.generate_summary_phase1(transcription, episode_date),
    fetch_episode_url()  # Recherche + update MongoDB
)
```

**Gain de temps** : ~10-15 secondes économisées par rapport à exécution séquentielle.

### Mise à jour MongoDB automatique

Si URL RadioFrance non présente dans l'épisode :

```python
async def fetch_episode_url():
    episode = mongodb_service.get_episode_by_id(episode_id)
    titre = episode.get("titre")
    date = episode.get("date")
    duree = episode.get("duree")  # Durée en secondes (optionnel)

    # Filtrage par durée minimale pour éviter les clips de livres individuels
    # RadioFrance publie deux types d'URLs par émission :
    # - Émission complète (~47 min) : URL souhaitée
    # - Clip livre individuel (~9 min) : à ignorer
    min_duration_seconds = None
    if duree and isinstance(duree, int) and duree > 0:
        min_duration_seconds = duree // 2  # 50% de la durée connue

    # Recherche via RadioFrance service avec filtre durée + date ±7j
    url = await radiofrance_service.search_episode_page_url(
        titre, date, min_duration_seconds=min_duration_seconds
    )

    if url:
        # Mise à jour MongoDB immédiate
        mongodb_service.episodes_collection.update_one(
            {"_id": ObjectId(episode_id)},
            {"$set": {"episode_page_url": url}}
        )

    return url
```

**Logique de sélection de l'URL** (méthode `search_episode_page_url`) :

RadioFrance peut publier plusieurs types d'URLs pour la même date de diffusion :
- **Émission complète** (ex: `le-masque-et-la-plume-du-dimanche-15-fevrier-2026-...`) : ~47 min
- **Clip livre individuel** (ex: `aqua-de-gaspard-koenig-...`) : ~9 min

Le service applique un double filtre sur chaque URL candidate :
1. **Date** : la date de la page RadioFrance doit être dans un intervalle de ±7 jours par rapport à la date de l'épisode (RadioFrance publie parfois 1-2 jours après diffusion)
2. **Durée** (si `min_duration_seconds` fourni) : la durée extraite de la page doit être ≥ `min_duration_seconds`

Structure JSON-LD RadioFrance (réelle) :
```json
{
  "@type": "RadioEpisode",
  "dateCreated": "2026-02-15T09:12:30.000Z",
  "mainEntity": {
    "@type": "AudioObject",
    "duration": "P0Y0M0DT0H47M40S"
  }
}
```

Note : la durée est dans `mainEntity.duration` (format ISO 8601 complet), et la date dans `dateCreated` (champ `RadioEpisode`).

### Nettoyage metadata

**Problème** : `page_text` peut contenir 10000+ caractères → stockage excessif.

**Solution** : Retirer `page_text` avant sauvegarde MongoDB.

```python
metadata_clean = {
    k: v for k, v in metadata.items()
    if k != "page_text"
}

avis_data = {
    ...
    "metadata_source": metadata_clean,  # Sans page_text
    ...
}
```

## Dépendances

### Services externes

**Requis** :
- `mongodb_service` : Accès collections `episodes`, `avis_critiques`
- `radiofrance_service` : Recherche URL + extraction métadonnées

**Import** :
```python
from .mongodb_service import mongodb_service
from .radiofrance_service import radiofrance_service
```

### Bibliothèques

```python
import asyncio  # Exécution parallèle
import openai  # Client Azure OpenAI
import re  # Validation format markdown
from datetime import datetime  # Timestamps, formatage dates
```

## Évolutions futures possibles

1. **Support multi-modèles** : Permettre sélection GPT-4o vs GPT-4-turbo via configuration
2. **Métriques de qualité** : Score de confiance par livre (basé sur consensus critiques)
3. **Export formats** : JSON structuré, CSV pour analyse statistique
4. **Cache résultats** : Éviter régénération si transcription inchangée
5. **Amélioration détection corrections** : Algorithme diff plus précis (Levenshtein distance)
6. **Retry intelligent** : Backoff exponentiel au lieu de délai fixe
7. **Streaming progressif** : Retourner résumé par chunks (Server-Sent Events)
8. **Validation syntaxe HTML** : Vérifier balances `<span>` pour notes colorées
