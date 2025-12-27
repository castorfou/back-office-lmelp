# Plan d'Implémentation : Génération d'Avis Critiques en 2 Phases LLM

> **📍 Emplacement** : `/workspaces/back-office-lmelp/.claude/plans/generation-avis-critiques-2phases.md`
> **🔄 Historique** : Plan créé le 2025-12-27, basé sur analyse du code lmelp frontend
> **🎯 Issue GitHub** : [#171 - Implémenter génération d'avis critiques en 2 phases LLM](https://github.com/castorfou/back-office-lmelp/issues/171)

---

## 📋 Vue d'Ensemble

**Objectif** : Créer un système complet de génération d'avis critiques en 2 phases LLM dans back-office-lmelp, remplaçant le système actuel (lmelp frontend).

**Phases** :
- **Phase 1** : Génération initiale depuis la transcription de l'épisode (Azure OpenAI GPT-4)
- **Phase 2** : Correction guidée par les métadonnées RadioFrance (noms des critiques, animateur)

**Déclenchement** : Nouvelle page `/generation-avis-critiques` accessible via le bloc Dashboard "Épisodes sans avis critiques"

**Stockage** :
- `summary` : Version finale (Phase 2 corrigée)
- `summary_phase1` : Backup Phase 1 (traçabilité)
- `summary_origin` : `"llm_generation_phase2"` (nouveau marqueur)

---

## 🎯 Spécifications Fonctionnelles

### Fonctionnalités Principales

1. **Liste des épisodes sans avis critiques**
   - Afficher les épisodes avec transcription mais sans avis critique
   - Tri par date décroissante
   - Affichage : titre, date, longueur transcription

2. **Génération 2 phases**
   - Phase 1 : LLM génère summary depuis transcription (tableaux markdown)
   - Phase 2 : LLM corrige noms (auteurs, critiques, animateur, éditeurs) avec métadonnées RadioFrance
   - Indicateur de progression pour l'utilisateur

3. **Comparaison des résultats**
   - Onglets : Phase 1 | Phase 2 | Différences
   - Liste des corrections appliquées
   - Avertissements si problèmes détectés

4. **Sauvegarde**
   - Bouton "Sauvegarder dans MongoDB"
   - Stockage dans `avis_critiques` collection
   - Retrait de l'épisode de la liste après sauvegarde

---

## 🏗️ Architecture Technique

### 1. Backend - Services Layer

#### **NOUVEAU FICHIER** : `/src/back_office_lmelp/services/avis_critiques_generation_service.py`

**Classe** : `AvisCritiquesGenerationService`

**Méthodes** :

```python
async def generate_summary_phase1(
    self,
    transcription: str,
    episode_date: str
) -> str:
    """
    Phase 1 : Génère summary depuis transcription.

    - Utilise Azure OpenAI GPT-4 (config de books_extraction_service)
    - Prompt : Extraire livres + avis en 2 tableaux markdown
    - Validation : Format markdown (regex pour vérifier structure)
    - Timeout : 120s avec 1 retry

    Returns:
        Markdown string avec structure:
        ## 1. LIVRES DISCUTÉS AU PROGRAMME
        | Auteur | Titre | Éditeur | Avis détaillés ... |

        ## 2. COUPS DE CŒUR DES CRITIQUES
        | Auteur | Titre | Éditeur | Critique | Note ... |
    """

async def enhance_summary_phase2(
    self,
    summary_phase1: str,
    episode_metadata: dict
) -> str:
    """
    Phase 2 : Corrige noms avec métadonnées RadioFrance.

    - Input metadata : {animateur, critiques, date, image_url}
    - Extrait critiques du summary_phase1 (critiques_extraction_service)
    - Match avec collection critiques (variantes)
    - Prompt LLM : Corriger noms propres sans changer structure
    - Validation : Vérifier structure markdown préservée

    Returns:
        Summary corrigé (même format markdown)
    """

async def generate_full_summary(
    self,
    episode_id: str
) -> dict:
    """
    Orchestrateur : Phase 1 + Phase 2.

    Workflow:
    1. Fetch episode avec transcription depuis MongoDB
    2. Lancer Phase 1 (génération)
    3. Fetch métadonnées RadioFrance (radiofrance_service)
    4. Lancer Phase 2 (correction)
    5. Tracker les corrections appliquées

    Returns:
        {
            "summary": str,  # Final (Phase 2)
            "summary_phase1": str,  # Backup
            "metadata": dict,  # RadioFrance metadata
            "corrections_applied": [
                {"field": "critique", "before": "...", "after": "..."}
            ],
            "warnings": ["..."]  # Si problèmes détectés
        }

    Gestion erreurs:
    - Phase 2 échoue → Utiliser Phase 1 comme summary final
    - Phase 1 échoue → Raise exception (pas de sauvegarde partielle)
    - Metadata extraction échoue → Skip Phase 2
    """
```

**Configuration Azure OpenAI** : Réutiliser variables d'environnement existantes

```python
# Déjà défini dans books_extraction_service
AZURE_OPENAI_ENDPOINT
AZURE_OPENAI_API_KEY
AZURE_OPENAI_API_VERSION
AZURE_OPENAI_DEPLOYMENT_NAME
```

#### **MODIFICATION** : `/src/back_office_lmelp/services/radiofrance_service.py`

**Nouvelles méthodes** :

```python
async def extract_episode_metadata(
    self,
    episode_url: str
) -> dict:
    """
    Scrape métadonnées depuis page RadioFrance épisode.

    Stratégie extraction:
    1. Fetch HTML avec aiohttp
    2. Parse JSON-LD (PodcastEpisode @type)
    3. Extraire:
       - author[0].name → animateur
       - datePublished → date
       - image → image_url
       - description → description
    4. Parser titre pour critiques (pattern "avec Nom1, Nom2...")

    Returns:
        {
            "animateur": "Jérôme Garcin",
            "critiques": ["Patricia Martin", "Arnaud Viviant"],
            "date": "2025-01-15",
            "image_url": "https://cdn.radiofrance.fr/...",
            "description": "Au programme..."
        }

    Fallback: Si JSON-LD absent, parser HTML (BeautifulSoup)
    """

def _parse_critics_from_title(self, title: str) -> list[str]:
    """
    Extrait noms critiques du titre épisode.

    Patterns RadioFrance:
    - "... avec Nom1, Nom2, Nom3"
    - "... par Nom1, Nom2"

    Returns:
        ["Nom1 Complet", "Nom2 Complet"]

    Post-traitement:
    - Normaliser whitespace
    - Matcher avec collection critiques (via critiques_extraction_service)
    """
```

---

### 2. Backend - API Layer

#### **MODIFICATION** : `/src/back_office_lmelp/app.py`

**Nouveaux endpoints** :

```python
@app.get("/api/episodes-sans-avis-critiques")
async def get_episodes_sans_avis_critiques() -> JSONResponse:
    """
    Liste épisodes avec transcription mais sans avis critique.

    Query MongoDB:
    - episodes.transcription: {$exists: true, $ne: null}
    - episodes._id: {$nin: [episode_oids from avis_critiques]}

    Sort: date DESC
    Limit: 100

    Returns:
        [
            {
                "id": str,
                "titre": str,
                "date": ISO string,
                "transcription_length": int,
                "has_episode_page_url": bool
            }
        ]
    """

@app.post("/api/avis-critiques/generate")
async def generate_avis_critiques(
    request: GenerateAvisCritiquesRequest
) -> GenerateAvisCritiquesResponse:
    """
    Génère avis critique (2 phases LLM).

    Body: {"episode_id": "..."}

    Process:
    1. Fetch episode
    2. generate_full_summary() du service
    3. Retourner résultat (PAS de sauvegarde auto)

    Returns:
        {
            "success": true,
            "summary": "...",
            "summary_phase1": "...",
            "metadata": {...},
            "corrections_applied": [...],
            "warnings": [...]
        }

    Timeout: 180s (3 minutes)
    """

@app.post("/api/avis-critiques/save")
async def save_avis_critiques(
    episode_id: str,
    summary: str,
    summary_phase1: str,
    metadata: dict
) -> JSONResponse:
    """
    Sauvegarde résultat génération dans MongoDB.

    Updates/inserts avis_critiques:
    - episode_oid: episode_id (string)
    - summary: summary (version finale Phase 2)
    - summary_phase1: summary_phase1 (backup)
    - summary_origin: "llm_generation_phase2"
    - metadata_source: metadata (RadioFrance)
    - created_at / updated_at

    Returns:
        {"success": true, "avis_critique_id": "..."}
    """
```

**Pydantic Models** :

```python
class GenerateAvisCritiquesRequest(BaseModel):
    episode_id: str

class GenerateAvisCritiquesResponse(BaseModel):
    success: bool
    summary: str
    summary_phase1: str
    metadata: dict
    corrections_applied: list[dict]
    warnings: list[str]
```

**⚠️ Route Order** : Placer `/api/episodes-sans-avis-critiques` AVANT `/api/episodes/{id}` (spécifique avant paramétrique)

---

### 3. Frontend - Vue.js

#### **NOUVEAU FICHIER** : `/frontend/src/views/GenerationAvisCritiques.vue`

**Structure** :

```vue
<template>
  <div class="generation-avis-critiques">
    <header class="page-header">
      <h1>Génération d'Avis Critiques</h1>
      <p>Génération automatique 2 phases LLM</p>
    </header>

    <main>
      <!-- 1. Sélection épisode -->
      <section class="episode-selection">
        <h2>1. Sélectionner un épisode</h2>
        <EpisodeDropdown
          v-model="selectedEpisodeId"
          :episodes="episodesSansAvis"
        />

        <!-- Détails épisode (accordéon transcription) -->
        <details v-if="selectedEpisode" class="episode-info">
          <summary>Voir la transcription ({{ selectedEpisode.transcription_length }} caractères)</summary>
          <pre>{{ selectedEpisode.transcription }}</pre>
        </details>
      </section>

      <!-- 2. Bouton génération -->
      <button
        @click="generateAvisCritiques"
        :disabled="!selectedEpisodeId || isGenerating"
        class="btn-primary"
      >
        {{ isGenerating ? 'Génération en cours...' : 'Générer' }}
      </button>

      <!-- Indicateur progression -->
      <div v-if="isGenerating" class="progress">
        <p>{{ currentPhase }}</p>
        <div class="spinner"></div>
      </div>

      <!-- 3. Résultats -->
      <section v-if="generationResult" class="results">
        <h2>2. Résultats</h2>

        <!-- Onglets comparaison -->
        <div class="tabs">
          <button
            @click="activeTab = 'phase1'"
            :class="{ active: activeTab === 'phase1' }"
          >
            Phase 1 (Brut)
          </button>
          <button
            @click="activeTab = 'phase2'"
            :class="{ active: activeTab === 'phase2' }"
          >
            Phase 2 (Corrigé) ✅
          </button>
          <button
            @click="activeTab = 'diff'"
            :class="{ active: activeTab === 'diff' }"
          >
            Différences
          </button>
        </div>

        <!-- Affichage markdown -->
        <div v-show="activeTab === 'phase1'" class="markdown-preview">
          <div v-html="renderMarkdown(generationResult.summary_phase1)"></div>
        </div>

        <div v-show="activeTab === 'phase2'" class="markdown-preview">
          <div v-html="renderMarkdown(generationResult.summary)"></div>

          <!-- Corrections appliquées -->
          <div v-if="generationResult.corrections_applied.length" class="corrections">
            <h3>Corrections appliquées</h3>
            <ul>
              <li v-for="corr in generationResult.corrections_applied" :key="corr.field">
                <strong>{{ corr.field }}:</strong>
                <del>{{ corr.before }}</del> → <ins>{{ corr.after }}</ins>
              </li>
            </ul>
          </div>
        </div>

        <div v-show="activeTab === 'diff'" class="diff-view">
          <DiffViewer
            :original="generationResult.summary_phase1"
            :modified="generationResult.summary"
          />
        </div>

        <!-- Avertissements -->
        <div v-if="generationResult.warnings.length" class="warnings alert">
          <h3>⚠️ Avertissements</h3>
          <ul>
            <li v-for="warn in generationResult.warnings" :key="warn">{{ warn }}</li>
          </ul>
        </div>

        <!-- Bouton sauvegarde -->
        <button
          @click="saveAvisCritiques"
          :disabled="isSaving"
          class="btn-success"
        >
          {{ isSaving ? 'Sauvegarde...' : 'Sauvegarder dans MongoDB' }}
        </button>
      </section>
    </main>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue';
import axios from 'axios';
import { marked } from 'marked';  // npm install marked
import EpisodeDropdown from '@/components/EpisodeDropdown.vue';
import DiffViewer from '@/components/DiffViewer.vue';

export default {
  name: 'GenerationAvisCritiques',
  components: { EpisodeDropdown, DiffViewer },

  setup() {
    const episodesSansAvis = ref([]);
    const selectedEpisodeId = ref('');
    const isGenerating = ref(false);
    const isSaving = ref(false);
    const currentPhase = ref('');
    const generationResult = ref(null);
    const activeTab = ref('phase2');
    const error = ref(null);

    const selectedEpisode = computed(() =>
      episodesSansAvis.value.find(ep => ep.id === selectedEpisodeId.value)
    );

    const loadEpisodesSansAvis = async () => {
      try {
        const { data } = await axios.get('/api/episodes-sans-avis-critiques');
        episodesSansAvis.value = data;
      } catch (err) {
        error.value = 'Erreur chargement épisodes';
        console.error(err);
      }
    };

    const generateAvisCritiques = async () => {
      isGenerating.value = true;
      currentPhase.value = 'Phase 1: Génération depuis transcription...';

      try {
        const { data } = await axios.post('/api/avis-critiques/generate', {
          episode_id: selectedEpisodeId.value
        }, { timeout: 180000 });  // 3 min

        generationResult.value = data;
        activeTab.value = 'phase2';
        currentPhase.value = '';
      } catch (err) {
        error.value = `Erreur génération: ${err.message}`;
        console.error(err);
      } finally {
        isGenerating.value = false;
      }
    };

    const saveAvisCritiques = async () => {
      isSaving.value = true;

      try {
        await axios.post('/api/avis-critiques/save', {
          episode_id: selectedEpisodeId.value,
          summary: generationResult.value.summary,
          summary_phase1: generationResult.value.summary_phase1,
          metadata: generationResult.value.metadata
        });

        alert('✅ Avis critique sauvegardé !');

        // Recharger liste + reset
        await loadEpisodesSansAvis();
        selectedEpisodeId.value = '';
        generationResult.value = null;
      } catch (err) {
        error.value = `Erreur sauvegarde: ${err.message}`;
        console.error(err);
      } finally {
        isSaving.value = false;
      }
    };

    const renderMarkdown = (text) => marked(text);

    onMounted(loadEpisodesSansAvis);

    return {
      episodesSansAvis,
      selectedEpisodeId,
      selectedEpisode,
      isGenerating,
      isSaving,
      currentPhase,
      generationResult,
      activeTab,
      error,
      generateAvisCritiques,
      saveAvisCritiques,
      renderMarkdown
    };
  }
};
</script>

<style scoped>
/* Pattern Dashboard.vue */
.generation-avis-critiques { padding: 2rem; max-width: 1200px; margin: 0 auto; }
.episode-info { background: #f5f5f5; padding: 1rem; border-radius: 8px; margin-top: 1rem; }
.tabs { display: flex; gap: 1rem; margin: 1rem 0; }
.tabs button { padding: 0.75rem 1.5rem; border: none; background: #e0e0e0; cursor: pointer; }
.tabs button.active { background: #667eea; color: white; }
.markdown-preview { background: white; padding: 1.5rem; border: 1px solid #ddd; border-radius: 8px; }
.corrections { background: #e8f5e9; padding: 1rem; margin-top: 1rem; border-radius: 6px; }
.corrections del { color: #d32f2f; }
.corrections ins { color: #388e3c; font-weight: bold; text-decoration: none; }
.warnings { background: #fff3e0; padding: 1rem; border-left: 4px solid #ff9800; }
.spinner { border: 4px solid #f3f3f3; border-top: 4px solid #667eea; border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
```

**Dépendances NPM** :
- `marked` : Rendering markdown → HTML
- `diff` : Composant DiffViewer (optionnel, simplifier avec CSS si besoin)

#### **NOUVEAU COMPOSANT** : `/frontend/src/components/DiffViewer.vue`

**Version simplifiée** (sans lib externe) :

```vue
<template>
  <div class="diff-viewer">
    <div class="diff-column">
      <h4>Phase 1 (Original)</h4>
      <pre>{{ original }}</pre>
    </div>
    <div class="diff-column">
      <h4>Phase 2 (Corrigé)</h4>
      <pre>{{ modified }}</pre>
    </div>
  </div>
</template>

<script>
export default {
  name: 'DiffViewer',
  props: {
    original: { type: String, required: true },
    modified: { type: String, required: true }
  }
};
</script>

<style scoped>
.diff-viewer { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
.diff-column { background: #f9f9f9; padding: 1rem; border-radius: 6px; }
.diff-column pre { overflow-x: auto; font-size: 0.85rem; }
</style>
```

#### **MODIFICATION** : `/frontend/src/router/index.js`

```javascript
import GenerationAvisCritiques from '../views/GenerationAvisCritiques.vue';

const routes = [
  // ... routes existantes
  {
    path: '/generation-avis-critiques',
    name: 'GenerationAvisCritiques',
    component: GenerationAvisCritiques,
    meta: {
      title: 'Génération Avis Critiques - Back-office LMELP'
    }
  }
];
```

#### **MODIFICATION** : `/frontend/src/views/Dashboard.vue`

**Changements** :

1. **Statistique "Épisodes sans avis critiques"** : Déjà présent (ligne 26-28), modifier pour navigation

```vue
<!-- Ligne 26-28 : Changer de lien externe vers navigation interne -->
<div
  class="stat-card clickable-stat"
  @click="navigateToGenerationAvis"
>
  <div class="stat-value">
    {{ (collectionsStatistics && collectionsStatistics.episodes_without_avis_critiques != null)
       ? collectionsStatistics.episodes_without_avis_critiques
       : '...'
    }}
  </div>
  <div class="stat-label">Épisodes sans avis critiques</div>
</div>
```

2. **Nouvelle carte fonction** (dans la grille functions-grid après ligne 80) :

```vue
<div
  class="function-card clickable"
  @click="navigateToGenerationAvis"
>
  <div class="function-icon">🤖</div>
  <h3>Génération Avis Critiques (LLM)</h3>
  <p>Génération automatique 2 phases depuis transcriptions</p>
  <div class="function-arrow">→</div>
</div>
```

3. **Méthode navigation** (dans `<script>` methods) :

```javascript
methods: {
  // ... méthodes existantes

  navigateToGenerationAvis() {
    this.$router.push('/generation-avis-critiques');
  }
}
```

---

### 4. Tests

#### **NOUVEAU FICHIER** : `/tests/test_avis_critiques_generation_service.py`

**Tests unitaires clés** :

```python
@pytest.mark.asyncio
async def test_generate_summary_phase1_success(mock_transcription):
    """Test Phase 1 génère markdown valide depuis transcription."""
    service = AvisCritiquesGenerationService()

    # Mock Azure OpenAI
    with patch.object(service.azure_client.chat.completions, 'create'):
        result = await service.generate_summary_phase1(
            mock_transcription,
            "2025-01-15"
        )

        assert "## 1. LIVRES DISCUTÉS AU PROGRAMME" in result
        assert "## 2. COUPS DE CŒUR DES CRITIQUES" in result

@pytest.mark.asyncio
async def test_generate_summary_phase1_invalid_format_raises():
    """Test Phase 1 raise ValueError si format invalide."""
    # Mock LLM retournant format cassé
    # Assert raises ValueError

@pytest.mark.asyncio
async def test_enhance_summary_phase2_applies_corrections():
    """Test Phase 2 corrige noms avec metadata."""
    # Mock Phase 1 avec typo: "Patricia Martine"
    # Mock metadata: {"critiques": ["Patricia Martin"]}
    # Assert correction appliquée

@pytest.mark.asyncio
async def test_generate_full_summary_orchestration():
    """Test orchestration complète Phase 1 + Phase 2."""
    # Mock episode fetch
    # Mock radiofrance_service.extract_episode_metadata
    # Mock Phase 1 et Phase 2
    # Assert result structure
```

**Fixtures** : Réutiliser `/tests/fixtures/avis_critique_summary_samples.py` pour markdown valide

#### **NOUVEAU FICHIER** : `/tests/test_radiofrance_metadata_extraction.py`

```python
@pytest.mark.asyncio
async def test_extract_episode_metadata_from_json_ld():
    """Test extraction metadata depuis JSON-LD RadioFrance."""
    # Mock HTML avec JSON-LD PodcastEpisode
    # Assert extraction: animateur, date, image_url

def test_parse_critics_from_title_standard_pattern():
    """Test parsing noms critiques depuis titre."""
    title = "... avec Patricia Martin, Arnaud Viviant"
    critics = service._parse_critics_from_title(title)

    assert "Patricia Martin" in critics
    assert "Arnaud Viviant" in critics
```

#### **NOUVEAU FICHIER** : `/frontend/src/views/__tests__/GenerationAvisCritiques.spec.js`

```javascript
describe('GenerationAvisCritiques.vue', () => {
  it('loads episodes on mount', async () => {
    axios.get.mockResolvedValueOnce({ data: mockEpisodes });

    const wrapper = mount(GenerationAvisCritiques);
    await wrapper.vm.$nextTick();

    expect(axios.get).toHaveBeenCalledWith('/api/episodes-sans-avis-critiques');
    expect(wrapper.vm.episodesSansAvis).toEqual(mockEpisodes);
  });

  it('generates critical review on button click', async () => {
    // Mock axios.post response
    // Trigger button click
    // Assert generationResult populated
  });
});
```

---

## 📦 Schéma MongoDB

### Collection `avis_critiques`

**Nouveaux champs** :

```javascript
{
  _id: ObjectId,
  episode_oid: String,  // Existing
  summary: String,  // UPDATED: Final (Phase 2 ou fallback Phase 1)
  summary_phase1: String,  // NEW: Backup Phase 1
  summary_origin: String,  // UPDATED: "llm_generation_phase2" | "lmelp_frontend"
  metadata_source: Object,  // NEW: RadioFrance metadata used
  // {
  //   "animateur": "Jérôme Garcin",
  //   "critiques": ["Patricia Martin", ...],
  //   "date": "2025-01-15",
  //   "image_url": "https://..."
  // }
  created_at: Date,
  updated_at: Date
}
```

**Migration** : ❌ Pas de migration nécessaire
- Nouveaux champs optionnels (backward compatible)
- Anciennes entrées conservent `summary_origin: "lmelp_frontend"`
- Nouvelles générations : `summary_origin: "llm_generation_phase2"`

---

## 🔧 Configuration

### Variables d'Environnement

**Déjà configurées** (réutilisation books_extraction_service) :

```bash
AZURE_OPENAI_ENDPOINT=https://...
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_API_VERSION=2024-02-01
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4
```

**Optionnelles** (debug) :

```bash
AVIS_CRITIQUES_DEBUG_LOG=1  # Logs détaillés génération
```

### Dépendances

**Backend** : Déjà installées ✅
- `openai` (Azure OpenAI SDK)
- `beautifulsoup4` (parsing HTML)
- `aiohttp` (HTTP async)

**Frontend** : À installer

```bash
cd frontend
npm install marked  # Markdown rendering
```

---

## 🎨 Prompts LLM

### Phase 1 : Génération Initiale

**Source** : Prompt extrait de `/tmp/lmelp-repo/ui/pages/4_avis_critiques.py` (lignes 874-982)

**Prompt complet** (fonction `generate_critique_summary`) :

```python
# Variables à interpoler :
# - {transcription} : Texte complet de la transcription
# - {date_str} : Format " du DD mois YYYY" (ex: " du 22 juin 2025")

prompt = f"""
Tu es un expert en critique littéraire qui analyse la transcription de l'émission "Le Masque et la Plume" sur France Inter.

⚠️ ATTENTION IMPORTANTE:
L'émission commence souvent par une section "courrier de la semaine" où l'animateur lit des réactions d'auditeurs sur des livres d'émissions PRÉCÉDENTES.
CES LIVRES DU COURRIER NE FONT PAS PARTIE DU PROGRAMME DE CETTE ÉMISSION.
Tu dois IGNORER complètement cette section du courrier.

Les livres du programme principal sont introduits APRÈS le courrier, généralement après des phrases comme:
- "Et on commence avec..."
- "Pour commencer ce soir..."
- "Parlons maintenant de..."
- "Le premier livre de ce soir..."

IMPORTANT: Si après avoir ignoré le courrier de la semaine, cette transcription ne contient PAS de discussions sur des livres, réponds simplement:
"Aucun livre discuté dans cet épisode. Cette émission semble porter sur d'autres sujets (cinéma, théâtre, musique)."

Voici la transcription:
{{transcription}}

CONSIGNE PRINCIPALE:
Identifie TOUS les livres discutés AU PROGRAMME DE CETTE ÉMISSION (pas ceux du courrier) et crée 2 tableaux détaillés et complets:

1. **LIVRES DU PROGRAMME PRINCIPAL**: Tous les livres qui font l'objet d'une discussion approfondie entre plusieurs critiques
2. **COUPS DE CŒUR PERSONNELS**: UNIQUEMENT les livres mentionnés rapidement par un critique comme recommandation personnelle (différents du programme principal)

⚠️ CONSIGNE CRUCIALE: NE RETOURNE QUE LES DEUX TABLEAUX, SANS AUCUNE PHRASE D'EXPLICATION, SANS COMMENTAIRE, SANS PHRASE INTRODUCTIVE. COMMENCE DIRECTEMENT PAR "## 1. LIVRES DISCUTÉS AU PROGRAMME" et termine par le dernier tableau.

---

## 1. LIVRES DISCUTÉS AU PROGRAMME{{date_str}}

Format de tableau markdown OBLIGATOIRE avec HTML pour les couleurs:

| Auteur | Titre | Éditeur | Avis détaillés des critiques | Note moyenne | Nb critiques | Coup de cœur | Chef d'œuvre |
|--------|-------|---------|------------------------------|--------------|-------------|-------------|-------------|
| [Nom auteur] | [Titre livre] | [Éditeur] | **[Nom COMPLET critique 1]**: [avis détaillé et note] <br>**[Nom COMPLET critique 2]**: [avis détaillé et note] <br>**[Nom COMPLET critique 3]**: [avis détaillé et note] | [Note colorée] | [Nombre] | [Noms si note ≥9] | [Noms si note=10] |

⚠️ IMPORTANT: CLASSE LES LIVRES PAR NOTE DÉCROISSANTE (meilleure note d'abord, pire note en dernier).

RÈGLES DE NOTATION STRICTES:
- Note 1-2: Livres détestés, "purges", "ennuyeux", "raté"
- Note 3-4: Livres décevants, "pas terrible", "problématique"
- Note 5-6: Livres moyens, "correct sans plus", "mitigé"
- Note 7-8: Bons livres, "plaisant", "réussi", "bien écrit"
- Note 9: Excellents livres, "formidable", "remarquable", "coup de cœur"
- Note 10: Chefs-d'œuvre, "génial", "exceptionnel", "chef-d'œuvre"

COULEURS HTML OBLIGATOIRES pour la Note moyenne:
- 9.0-10.0: <span style="background-color: #00C851; color: white; padding: 2px 6px; border-radius: 3px; font-weight: bold;">X.X</span>
- 8.0-8.9: <span style="background-color: #4CAF50; color: white; padding: 2px 6px; border-radius: 3px; font-weight: bold;">X.X</span>
- 7.0-7.9: <span style="background-color: #8BC34A; color: white; padding: 2px 6px; border-radius: 3px; font-weight: bold;">X.X</span>
- 6.0-6.9: <span style="background-color: #CDDC39; color: black; padding: 2px 6px; border-radius: 3px; font-weight: bold;">X.X</span>
- 5.0-5.9: <span style="background-color: #FFEB3B; color: black; padding: 2px 6px; border-radius: 3px; font-weight: bold;">X.X</span>
- 4.0-4.9: <span style="background-color: #FF9800; color: white; padding: 2px 6px; border-radius: 3px; font-weight: bold;">X.X</span>
- 3.0-3.9: <span style="background-color: #FF5722; color: white; padding: 2px 6px; border-radius: 3px; font-weight: bold;">X.X</span>
- 1.0-2.9: <span style="background-color: #F44336; color: white; padding: 2px 6px; border-radius: 3px; font-weight: bold;">X.X</span>

INSTRUCTIONS DÉTAILLÉES POUR EXTRAIRE TOUS LES AVIS:
1. Identifie TOUS les critiques qui parlent de chaque livre: Jérôme Garcin, Elisabeth Philippe, Frédéric Beigbeder, Michel Crépu, Arnaud Viviant, Judith Perrignon, Xavier Leherpeur, Patricia Martin, etc.
2. Pour chaque critique, capture son NOM COMPLET (Prénom + Nom)
3. Cite leurs avis EXACTS avec leurs mots-clés d'appréciation
4. Attribue une note individuelle basée sur leur vocabulaire (entre 1 et 10)
5. Calcule la moyenne arithmétique précise (ex: 7.3, 8.7)
6. Identifie les "coups de cœur" (critiques très enthousiastes, note ≥9)
7. **CLASSE OBLIGATOIREMENT PAR NOTE DÉCROISSANTE** (meilleure note d'abord)

⚠️ RAPPEL: Ignore complètement les livres mentionnés dans le "courrier de la semaine" au début de l'émission.

---

## 2. COUPS DE CŒUR DES CRITIQUES{{date_str}}

⚠️ ATTENTION: Ce tableau contient UNIQUEMENT les livres/ouvrages mentionnés rapidement par les critiques comme recommandations personnelles supplémentaires (souvent en fin d'émission avec "mon coup de cœur", "je recommande", etc.).
Ce sont des ouvrages DIFFÉRENTS de ceux discutés au programme principal ci-dessus.
INCLUT TOUS TYPES D'OUVRAGES : romans, essais, BD, guides, biographies, etc.

Format de tableau pour ces recommandations personnelles:

| Auteur | Titre | Éditeur | Critique | Note | Commentaire |
|--------|-------|---------|----------|------|-------------|
| [Nom] | [Titre] | [Éditeur] | [Nom COMPLET critique] | [Note colorée] | [Raison du coup de cœur] |

⚠️ IMPORTANT:
- CLASSE LES COUPS DE CŒUR PAR NOTE DÉCROISSANTE AUSSI
- N'INCLUS QUE les livres mentionnés comme recommandations PERSONNELLES, PAS ceux du programme principal
- CHERCHE SPÉCIALEMENT en fin de transcription les sections "coups de cœur", "conseils de lecture", "recommandations"

EXIGENCES QUALITÉ:
- Noms COMPLETS de TOUS les critiques (Prénom + Nom)
- Citations exactes des avis les plus marquants
- Éditeurs mentionnés quand disponibles
- Tableaux markdown parfaitement formatés
- Couleurs HTML correctement appliquées
- **CLASSEMENT OBLIGATOIRE PAR NOTE DÉCROISSANTE**
- Capture de TOUS les avis individuels (pas seulement Elisabeth Philippe)
- **RECHERCHE ACTIVE des coups de cœur en fin de transcription** : cherche "coups de cœur", "conseil de lecture", "je recommande", "mon choix"

⚠️ SPÉCIAL COUPS DE CŒUR: Les critiques mentionnent souvent leurs recommandations personnelles vers la fin de l'émission. SCRUTE ATTENTIVEMENT la fin de la transcription pour ne pas les manquer !

⚠️ FORMAT DE RÉPONSE: Retourne UNIQUEMENT les 2 tableaux markdown avec leurs titres. N'ajoute AUCUNE explication, phrase introductive, ou commentaire sur la méthode de génération. Commence directement par "## 1. LIVRES DISCUTÉS AU PROGRAMME" et termine par le dernier tableau.

RAPPEL FINAL:
- IGNORE les livres du courrier de la semaine
- NE RETOURNE AUCUN TEXTE EXPLICATIF AVANT OU APRÈS LES TABLEAUX
- AUCUNE PHRASE COMME "voici l'analyse" ou "en résumé"
- COMMENCE IMMÉDIATEMENT PAR LE PREMIER TITRE DE TABLEAU

Sois EXHAUSTIF et PRÉCIS. Capture TOUS les livres DU PROGRAMME, TOUS les critiques, et TOUS les avis individuels.
"""
```

**Paramètres Azure OpenAI** (lignes 990-994) :
```python
response = model.complete(
    prompt,
    max_tokens=8000,  # Augmenté pour épisodes longs
    temperature=0.1,  # Réduire créativité pour cohérence
)
```

**Post-traitement** : Le code lmelp applique aussi `post_process_and_sort_summary()` (lignes 647-786) pour :
- Supprimer phrases explicatives du LLM
- Ajouter date aux titres si absente
- Trier tableaux par note décroissante
- Nettoyer lignes vides multiples

**Validation anti-troncature** : Fonction `is_summary_truncated()` (lignes 50-98) bloque la sauvegarde si :
- Longueur < 200 caractères
- Se termine par `**`, `→`, `...`
- Pas de titre `## 1.`
- Dernière ligne de tableau incomplète

### Phase 2 : Correction Guidée

```
System:
Tu es un correcteur orthographique pour émission littéraire.
Corrige UNIQUEMENT les noms propres (auteurs, critiques, animateur, éditeurs).
PRÉSERVE structure markdown et avis/notes.

User:
Résumé initial:
{summary_phase1}

Métadonnées officielles RadioFrance:
- Animateur: {animateur}
- Critiques présents: {', '.join(critiques)}
- Date: {date}

Corrige les noms propres en préservant EXACTEMENT la structure markdown.
Retourne UNIQUEMENT le résumé corrigé, sans commentaire.
```

---

## 📊 Workflow Utilisateur

1. **Dashboard** → Clic sur "Épisodes sans avis critiques" (ou nouvelle carte fonction)
2. **Page Génération** → Dropdown liste épisodes
3. **Sélection épisode** → Affichage transcription (accordéon)
4. **Clic "Générer"** → Spinner + phase indicator (1.5-2 min)
5. **Résultats** → Onglets Phase 1 | Phase 2 | Diff
6. **Review** → Vérifier corrections appliquées + warnings
7. **Clic "Sauvegarder"** → Insertion MongoDB + retrait liste

---

## ⚠️ Points d'Attention

### Gestion Erreurs

**Timeout LLM** :
- Phase 1 : 120s timeout → 1 retry → Fail si échec
- Phase 2 : 60s timeout → Fallback sur Phase 1 si échec

**Format Markdown Invalide** :
- Validation regex : `## 1\. LIVRES DISCUTÉS` + `## 2\. COUPS DE CŒUR`
- Si invalid Phase 1 → Raise ValueError (user fix transcription)
- Si invalid Phase 2 → Fallback Phase 1

**Métadonnées RadioFrance Absentes** :
- Si `episode_page_url` vide → Skip Phase 2, utiliser Phase 1 directement
- Si scraping échoue → Warning + Skip Phase 2

### Performance

**Latence attendue** :
- Phase 1 : ~60s
- Metadata extraction : ~3s (en parallèle)
- Phase 2 : ~30s
- **Total** : ~90s (bien sous timeout 3 min)

**Optimisation** : Lancer metadata extraction pendant Phase 1 (gain 3s)

---

## ✅ Critères de Succès

### Fonctionnel
- [ ] Phase 1 génère markdown valide depuis transcription
- [ ] Phase 2 corrige noms (critiques, auteur, éditeur, animateur)
- [ ] UI affiche comparaison 3 onglets (Phase 1 | Phase 2 | Diff)
- [ ] Sauvegarde MongoDB avec champs `summary`, `summary_phase1`, `metadata_source`
- [ ] Dashboard affiche count épisodes sans avis
- [ ] Navigation Dashboard → Page génération

### Qualité
- [ ] Tests coverage >85% (services backend)
- [ ] Tests frontend (Vitest) pour composant génération
- [ ] Validation format markdown (regex)
- [ ] Gestion erreurs graceful (fallback Phase 2 → Phase 1)
- [ ] Pre-commit hooks passent (ruff, mypy, tests)

### UX
- [ ] Indicateur progression (spinner + phase actuelle)
- [ ] Affichage corrections appliquées (del/ins)
- [ ] Warnings visibles si problèmes
- [ ] Timeout 3 min suffisant (95th percentile <180s)

---

## 📂 Fichiers à Créer/Modifier

### Créer (7 fichiers)

1. `/src/back_office_lmelp/services/avis_critiques_generation_service.py` - Service génération 2 phases
2. `/frontend/src/views/GenerationAvisCritiques.vue` - Page UI principale
3. `/frontend/src/components/DiffViewer.vue` - Composant comparaison
4. `/tests/test_avis_critiques_generation_service.py` - Tests unitaires service
5. `/tests/test_radiofrance_metadata_extraction.py` - Tests extraction metadata
6. `/frontend/src/views/__tests__/GenerationAvisCritiques.spec.js` - Tests frontend
7. `/tests/fixtures/transcription_samples.py` - Fixtures transcriptions réelles

### Modifier (4 fichiers)

1. `/src/back_office_lmelp/services/radiofrance_service.py` - Ajout `extract_episode_metadata()` + `_parse_critics_from_title()`
2. `/src/back_office_lmelp/app.py` - 3 nouveaux endpoints API
3. `/frontend/src/router/index.js` - Route `/generation-avis-critiques`
4. `/frontend/src/views/Dashboard.vue` - Navigation vers génération + nouvelle carte fonction

---

## 🚀 Ordre d'Implémentation Recommandé

### Phase A - Backend Services (TDD)

1. **Fixtures** : Créer `transcription_samples.py` avec vraies transcriptions
2. **Tests RadioFrance** : `test_radiofrance_metadata_extraction.py`
3. **RadioFrance Service** : Implémenter `extract_episode_metadata()`
4. **Tests Génération** : `test_avis_critiques_generation_service.py`
5. **Service Génération** : Implémenter Phase 1 + Phase 2

### Phase B - API Layer

6. **Pydantic Models** : Définir request/response dans `app.py`
7. **Endpoints** : Implémenter 3 endpoints (`episodes-sans-avis`, `generate`, `save`)
8. **Tests API** : Intégration avec services mockés

### Phase C - Frontend

9. **Composant Diff** : `DiffViewer.vue` (simple 2-column layout)
10. **Page Génération** : `GenerationAvisCritiques.vue`
11. **Router** : Ajouter route
12. **Dashboard** : Modifier navigation
13. **Tests Frontend** : `GenerationAvisCritiques.spec.js`

### Phase D - Validation

14. **Test end-to-end** : Génération complète sur vrai épisode
15. **Pre-commit hooks** : Vérifier tous les checks passent
16. **Documentation** : Mettre à jour README si nécessaire

---

## 📝 Notes Importantes

1. **Prompt Phase 1** : Attendre le prompt exact de l'utilisateur (depuis lmelp frontend) pour garantir cohérence
2. **Backward Compatibility** : Aucune migration DB nécessaire, nouveaux champs optionnels
3. **Réutilisation Code** : Pattern de `books_extraction_service` pour Azure OpenAI config
4. **TDD Obligatoire** : Suivre CLAUDE.md (tests avant implémentation)
5. **Format Markdown** : Validation stricte (regex) pour éviter parsing errors downstream
