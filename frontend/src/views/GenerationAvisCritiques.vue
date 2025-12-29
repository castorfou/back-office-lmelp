<template>
  <div class="generation-avis-critiques">
    <!-- Navigation -->
    <Navigation pageTitle="Génération d'Avis Critiques" />

    <main>
      <section v-if="error" class="alert alert-error">
        {{ error }}
      </section>

      <section class="episode-selection">
        <h2>1. Sélectionner un épisode</h2>

        <div v-if="loading" class="loading">
          Chargement des épisodes...
        </div>

        <select
          v-else
          v-model="selectedEpisodeId"
          class="episode-dropdown"
          :disabled="episodesSansAvis.length === 0"
        >
          <option value="">-- Sélectionner un épisode --</option>
          <option
            v-for="ep in episodesSansAvis"
            :key="ep.id"
            :value="ep.id"
          >
            {{ ep.titre }} ({{ formatDate(ep.date) }}) - {{ ep.transcription_length }} caractères
          </option>
        </select>

        <p v-if="episodesSansAvis.length === 0 && !loading" class="info">
          Aucun épisode sans avis critique trouvé.
        </p>

        <button
          @click="generateAvisCritiques"
          :disabled="!selectedEpisodeId || isGenerating"
          class="btn-primary"
        >
          {{ isGenerating ? 'Génération en cours...' : 'Générer' }}
        </button>
      </section>

      <section v-if="isGenerating" class="progress">
        <p>{{ currentPhase }}</p>
        <div class="spinner"></div>
      </section>

      <section v-if="generationResult" class="results">
        <h2>2. Résultats</h2>

        <!-- Alerte si summary vide -->
        <div v-if="isSummaryEmpty" class="alert alert-warning">
          ⚠️ La génération a échoué (summary vide). Cliquez sur "Régénérer" pour relancer.
        </div>

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

        <div v-show="activeTab === 'phase1'" class="markdown-preview">
          <div v-html="renderMarkdown(generationResult.summary_phase1)"></div>
        </div>

        <div v-show="activeTab === 'phase2'" class="markdown-preview">
          <div v-html="renderMarkdown(generationResult.summary)"></div>

          <div v-if="generationResult.corrections_applied && generationResult.corrections_applied.length" class="corrections">
            <h3>Corrections appliquées</h3>
            <ul>
              <li v-for="(corr, idx) in generationResult.corrections_applied" :key="idx">
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

        <div v-if="generationResult.warnings && generationResult.warnings.length" class="warnings alert">
          <h3>⚠️ Avertissements</h3>
          <ul>
            <li v-for="(warn, idx) in generationResult.warnings" :key="idx">{{ warn }}</li>
          </ul>
        </div>

        <div class="action-buttons">
          <button
            @click="generateAvisCritiques"
            :disabled="isGenerating"
            class="btn-regenerate"
          >
            {{ isGenerating ? 'Régénération...' : '🔄 Régénérer' }}
          </button>

          <button
            @click="saveAvisCritiques"
            :disabled="isSaving || isSummaryEmpty"
            class="btn-success"
          >
            {{ isSaving ? 'Sauvegarde...' : 'Sauvegarder dans MongoDB' }}
          </button>
        </div>
      </section>
    </main>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue';
import { avisCritiquesService, episodeService } from '@/services/api';
import { marked } from 'marked';
import Navigation from '@/components/Navigation.vue';
import DiffViewer from '@/components/DiffViewer.vue';

export default {
  name: 'GenerationAvisCritiques',
  components: {
    Navigation,
    DiffViewer
  },

  setup() {
    const episodesSansAvis = ref([]);
    const selectedEpisodeId = ref('');
    const loading = ref(false);
    const error = ref(null);
    const isGenerating = ref(false);
    const currentPhase = ref('');
    const generationResult = ref(null);
    const activeTab = ref('phase2');
    const isSaving = ref(false);

    // Computed: vérifie si summary est vide
    const isSummaryEmpty = computed(() => {
      if (!generationResult.value) return false;
      const summary = generationResult.value.summary || '';
      return summary.trim().length === 0;
    });

    // Fonction pour lancer fetch URL en parallèle (fire-and-forget)
    const fetchEpisodeUrlInParallel = (episodeId) => {
      const episode = episodesSansAvis.value.find(ep => ep.id === episodeId);

      // Skip si URL déjà présente
      if (!episode || episode.episode_page_url) {
        return;
      }

      // Lancer fetch en fire-and-forget (non-bloquant)
      episodeService.fetchEpisodePageUrl(episodeId)
        .then(result => {
          if (result && result.episode_page_url) {
            // Mettre à jour l'épisode dans la liste
            const episodeIndex = episodesSansAvis.value.findIndex(ep => ep.id === episodeId);
            if (episodeIndex !== -1) {
              episodesSansAvis.value[episodeIndex].episode_page_url = result.episode_page_url;
            }
          }
        })
        .catch(urlError => {
          console.warn('Impossible de récupérer l\'URL RadioFrance:', urlError);
          // Silent failure - ne pas bloquer la génération
        });
    };

    const loadEpisodesSansAvis = async () => {
      loading.value = true;
      error.value = null;

      try {
        episodesSansAvis.value = await avisCritiquesService.getEpisodesSansAvis();
      } catch (err) {
        console.error('Erreur chargement épisodes:', err);
        error.value = err.message || 'Erreur lors du chargement des épisodes';
      } finally {
        loading.value = false;
      }
    };

    const formatDate = (dateStr) => {
      if (!dateStr) return '';
      const date = new Date(dateStr);
      return date.toLocaleDateString('fr-FR');
    };

    const generateAvisCritiques = async () => {
      isGenerating.value = true;
      currentPhase.value = 'Génération en cours...';
      error.value = null;

      // Lancer fetch URL RadioFrance en parallèle (non-bloquant)
      fetchEpisodeUrlInParallel(selectedEpisodeId.value);

      try {
        const result = await avisCritiquesService.generateAvisCritiques({
          episode_id: selectedEpisodeId.value
        });

        generationResult.value = result;
        currentPhase.value = '';
      } catch (err) {
        console.error('Erreur génération:', err);
        error.value = err.message || 'Erreur lors de la génération';
      } finally {
        isGenerating.value = false;
      }
    };

    const renderMarkdown = (text) => {
      return marked(text);
    };

    const saveAvisCritiques = async () => {
      isSaving.value = true;
      error.value = null;

      try {
        await avisCritiquesService.saveAvisCritiques({
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
        activeTab.value = 'phase2';
      } catch (err) {
        console.error('Erreur sauvegarde:', err);
        error.value = err.message || 'Erreur lors de la sauvegarde';
      } finally {
        isSaving.value = false;
      }
    };

    onMounted(loadEpisodesSansAvis);

    return {
      episodesSansAvis,
      selectedEpisodeId,
      loading,
      error,
      formatDate,
      isGenerating,
      currentPhase,
      generationResult,
      generateAvisCritiques,
      renderMarkdown,
      activeTab,
      isSaving,
      isSummaryEmpty,
      saveAvisCritiques
    };
  }
};
</script>

<style scoped>
.generation-avis-critiques {
  min-height: 100vh;
  background-color: #f5f5f5;
}

main {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 1rem 2rem;
}

.episode-selection {
  background: white;
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.episode-selection h2 {
  font-size: 1.5rem;
  color: #333;
  margin-bottom: 1rem;
}

.episode-dropdown {
  width: 100%;
  padding: 0.75rem;
  font-size: 1rem;
  border: 1px solid #ddd;
  border-radius: 6px;
  background: white;
  cursor: pointer;
}

.episode-dropdown:disabled {
  background: #f5f5f5;
  cursor: not-allowed;
  color: #999;
}

.loading {
  padding: 1rem;
  color: #666;
  text-align: center;
}

.info {
  padding: 1rem;
  color: #666;
  background: #f9f9f9;
  border-radius: 6px;
  text-align: center;
}

.alert {
  padding: 1rem;
  border-radius: 6px;
  margin-bottom: 1rem;
}

.alert-error {
  background: #fee;
  color: #c00;
  border: 1px solid #fcc;
}

.alert-warning {
  background: #fff3cd;
  color: #856404;
  border: 1px solid #ffeaa7;
}

.btn-primary {
  background: #667eea;
  color: white;
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 1rem;
  margin-top: 1rem;
  font-weight: 500;
  transition: background 0.2s;
}

.btn-primary:hover:not(:disabled) {
  background: #5568d3;
}

.btn-primary:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.progress {
  background: white;
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  margin-top: 1.5rem;
  text-align: center;
}

.progress p {
  color: #666;
  margin-bottom: 1rem;
  font-size: 1rem;
}

.spinner {
  border: 4px solid #f3f3f3;
  border-top: 4px solid #667eea;
  border-radius: 50%;
  width: 40px;
  height: 40px;
  animation: spin 1s linear infinite;
  margin: 0 auto;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.results {
  background: white;
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  margin-top: 1.5rem;
}

.results h2 {
  font-size: 1.5rem;
  color: #333;
  margin-bottom: 1rem;
}

.markdown-preview {
  background: #f9f9f9;
  padding: 1.5rem;
  border: 1px solid #ddd;
  border-radius: 6px;
  overflow-x: auto;
}

.markdown-preview :deep(h2) {
  font-size: 1.3rem;
  color: #333;
  margin-top: 1.5rem;
  margin-bottom: 1rem;
}

.markdown-preview :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 1rem 0;
}

.markdown-preview :deep(th) {
  background: #f5f5f5;
  padding: 0.75rem;
  border: 1px solid #ddd;
  text-align: left;
  font-weight: 600;
}

.markdown-preview :deep(td) {
  padding: 0.75rem;
  border: 1px solid #ddd;
}

.markdown-preview :deep(tr:nth-child(even)) {
  background: #fafafa;
}

.tabs {
  display: flex;
  gap: 1rem;
  margin: 1rem 0;
}

.tabs button {
  padding: 0.75rem 1.5rem;
  border: none;
  background: #e0e0e0;
  cursor: pointer;
  border-radius: 6px;
  font-size: 0.95rem;
  transition: background 0.2s;
}

.tabs button:hover {
  background: #d0d0d0;
}

.tabs button.active {
  background: #667eea;
  color: white;
  font-weight: bold;
}

.corrections {
  background: #e8f5e9;
  padding: 1rem;
  margin-top: 1rem;
  border-radius: 6px;
  border-left: 4px solid #4caf50;
}

.corrections h3 {
  margin-top: 0;
  margin-bottom: 0.75rem;
  color: #2e7d32;
  font-size: 1.1rem;
}

.corrections ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.corrections li {
  padding: 0.5rem 0;
  border-bottom: 1px solid #c8e6c9;
}

.corrections li:last-child {
  border-bottom: none;
}

.corrections del {
  color: #d32f2f;
  text-decoration: line-through;
  background: #ffebee;
  padding: 2px 4px;
  border-radius: 3px;
}

.corrections ins {
  color: #388e3c;
  font-weight: bold;
  text-decoration: none;
  background: #e8f5e9;
  padding: 2px 4px;
  border-radius: 3px;
}

.warnings {
  background: #fff3e0;
  padding: 1rem;
  border-left: 4px solid #ff9800;
  margin-top: 1rem;
  border-radius: 6px;
}

.warnings h3 {
  margin-top: 0;
  margin-bottom: 0.75rem;
  color: #e65100;
  font-size: 1.1rem;
}

.warnings ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.warnings li {
  padding: 0.25rem 0;
  color: #e65100;
}

.btn-success {
  background: #4caf50;
  color: white;
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 1rem;
  margin-top: 1rem;
  font-weight: 500;
  transition: background 0.2s;
}

.btn-success:hover:not(:disabled) {
  background: #45a049;
}

.btn-success:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.btn-regenerate {
  background: #ff9800;
  color: white;
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 1rem;
  font-weight: 500;
  transition: background 0.2s;
}

.btn-regenerate:hover:not(:disabled) {
  background: #f57c00;
}

.btn-regenerate:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.action-buttons {
  display: flex;
  gap: 1rem;
  margin-top: 1rem;
  flex-wrap: wrap;
}

.diff-view {
  margin-top: 1rem;
}
</style>
