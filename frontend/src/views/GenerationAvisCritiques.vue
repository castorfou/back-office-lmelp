<template>
  <div class="generation-avis-critiques">
    <!-- Navigation -->
    <Navigation pageTitle="Génération d'Avis Critiques" />

    <main>
      <section v-if="error" class="alert alert-error">
        {{ error }}
      </section>

      <section class="episode-selection">
        <div v-if="loading" class="loading">
          Chargement des épisodes...
        </div>

        <div v-else-if="allEpisodes.length === 0" class="info">
          Aucun épisode trouvé.
        </div>

        <div v-else>
          <label for="episode-dropdown" class="form-label">
            Choisir un épisode ({{ allEpisodes.length || 0 }} disponibles)
          </label>

          <div class="episode-select-wrapper">
          <button
            class="nav-episode-btn prev-btn"
            @click.prevent="selectPreviousEpisode"
            :disabled="!hasPreviousEpisode || isGenerating"
            aria-label="Épisode précédent"
          >
            ◀️ Précédent
          </button>

          <EpisodeDropdown
            v-model="selectedEpisodeId"
            :episodes="allEpisodes"
            @update:modelValue="onEpisodeChange"
            :disabled="isGenerating"
          />

          <button
            class="nav-episode-btn next-btn"
            @click.prevent="selectNextEpisode"
            :disabled="!hasNextEpisode || isGenerating"
            aria-label="Épisode suivant"
          >
            Suivant ▶️
          </button>
        </div>

        <!-- Bouton Générer OU Régénérer -->
        <div v-if="selectedEpisodeId" class="action-buttons-top">
          <button
            v-if="!episodeHasSummary"
            @click="generateAvisCritiques"
            :disabled="isGenerating"
            class="btn-primary"
          >
            {{ isGenerating ? 'Génération...' : '🚀 Générer le summary' }}
          </button>

          <button
            v-else
            @click="generateAvisCritiques"
            :disabled="isGenerating"
            class="btn-regenerate"
          >
            {{ isGenerating ? 'Régénération...' : '🔄 Régénérer' }}
          </button>
        </div>
        </div>
      </section>

      <!-- Progress pendant génération -->
      <section v-if="isGenerating" class="progress">
        <p>{{ currentPhase }}</p>
        <div class="spinner"></div>
      </section>

      <!-- Résultats -->
      <section v-if="generationResult && !isGenerating" class="results">
        <!-- Alerte si summary vide -->
        <div v-if="isSummaryEmpty" class="alert alert-warning">
          ⚠️ La génération a échoué (summary vide). Cliquez sur "Régénérer" pour relancer.
        </div>

        <!-- Afficher directement le summary Phase 2 (corrigé) -->
        <div class="markdown-preview">
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

        <div v-if="generationResult.warnings && generationResult.warnings.length" class="warnings alert">
          <h3>⚠️ Avertissements</h3>
          <ul>
            <li v-for="(warn, idx) in generationResult.warnings" :key="idx">{{ warn }}</li>
          </ul>
        </div>
      </section>
    </main>
  </div>
</template>

<script>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue';
import { avisCritiquesService, episodeService } from '@/services/api';
import { marked } from 'marked';
import Navigation from '@/components/Navigation.vue';
import DiffViewer from '@/components/DiffViewer.vue';
import EpisodeDropdown from '@/components/EpisodeDropdown.vue';

export default {
  name: 'GenerationAvisCritiques',
  components: {
    Navigation,
    DiffViewer,
    EpisodeDropdown
  },

  setup() {
    // State
    const allEpisodes = ref([]);  // TOUS les épisodes (avec ET sans summary)
    const selectedEpisodeId = ref('');
    const loading = ref(false);
    const error = ref(null);
    const isGenerating = ref(false);
    const currentPhase = ref('');
    const generationResult = ref(null);
    const navLock = ref(false);  // Prévenir navigation pendant génération

    // Computed properties
    const currentEpisodeIndex = computed(() => {
      if (!allEpisodes.value || !selectedEpisodeId.value) return -1;
      return allEpisodes.value.findIndex(ep => String(ep.id) === String(selectedEpisodeId.value));
    });

    const hasPreviousEpisode = computed(() => {
      return currentEpisodeIndex.value >= 0 &&
             currentEpisodeIndex.value < (allEpisodes.value.length - 1);
    });

    const hasNextEpisode = computed(() => {
      return currentEpisodeIndex.value > 0;
    });

    const selectedEpisode = computed(() => {
      if (!selectedEpisodeId.value || !allEpisodes.value) return null;
      return allEpisodes.value.find(ep => String(ep.id) === String(selectedEpisodeId.value));
    });

    const episodeHasSummary = computed(() => {
      return selectedEpisode.value?.has_summary === true;
    });

    const isSummaryEmpty = computed(() => {
      if (!generationResult.value) return false;
      const summary = generationResult.value.summary || '';
      return summary.trim().length === 0;
    });

    // Load all episodes (with and without summaries)
    const loadAllEpisodes = async () => {
      loading.value = true;
      error.value = null;

      try {
        // Charger en parallèle les épisodes avec et sans summary
        const [withSummaries, withoutSummaries] = await Promise.all([
          avisCritiquesService.getEpisodesWithSummaries(),
          avisCritiquesService.getEpisodesSansAvis()
        ]);

        // Marquer ceux avec summary
        const episodesWithFlag = withSummaries.map(ep => ({...ep, has_summary: true}));
        const episodesWithoutFlag = withoutSummaries.map(ep => ({...ep, has_summary: false}));

        // Fusionner et trier par date DESC (plus récent en premier)
        allEpisodes.value = [...episodesWithFlag, ...episodesWithoutFlag]
          .sort((a, b) => new Date(b.date) - new Date(a.date));

        // Présélection: épisode le plus récent SANS summary
        const firstWithoutSummary = allEpisodes.value.find(ep => !ep.has_summary);
        if (firstWithoutSummary) {
          selectedEpisodeId.value = firstWithoutSummary.id;
          await onEpisodeChange();
        }

      } catch (err) {
        console.error('Erreur chargement épisodes:', err);
        error.value = err.message || 'Erreur lors du chargement des épisodes';
      } finally {
        loading.value = false;
      }
    };

    // Handle episode change
    const onEpisodeChange = async () => {
      if (!selectedEpisodeId.value) {
        generationResult.value = null;
        return;
      }

      // Si l'épisode a un summary existant, le charger
      if (episodeHasSummary.value) {
        loading.value = true;
        try {
          const existingSummary = await avisCritiquesService.getSummaryByEpisode(selectedEpisodeId.value);
          generationResult.value = existingSummary;
        } catch (err) {
          console.error('Erreur chargement summary:', err);
          // Si erreur 404, considérer comme sans summary
          if (err.message.includes('404')) {
            generationResult.value = null;
          }
        } finally {
          loading.value = false;
        }
      } else {
        // Épisode sans summary: nettoyer l'affichage
        generationResult.value = null;
      }
    };

    // Navigation Previous/Next
    const selectPreviousEpisode = async () => {
      if (navLock.value || isGenerating.value) return;

      const idx = currentEpisodeIndex.value;
      if (idx >= 0 && idx < allEpisodes.value.length - 1) {
        navLock.value = true;
        try {
          const prev = allEpisodes.value[idx + 1];  // Plus ancien
          selectedEpisodeId.value = prev.id;
          await onEpisodeChange();
        } finally {
          navLock.value = false;
        }
      }
    };

    const selectNextEpisode = async () => {
      if (navLock.value || isGenerating.value) return;

      const idx = currentEpisodeIndex.value;
      if (idx > 0) {
        navLock.value = true;
        try {
          const next = allEpisodes.value[idx - 1];  // Plus récent
          selectedEpisodeId.value = next.id;
          await onEpisodeChange();
        } finally {
          navLock.value = false;
        }
      }
    };

    // Phase messages
    const setPhase = (phase) => {
      const phases = {
        'fetch': '🔍 Recherche URL RadioFrance...',
        'phase1': '📝 Phase 1: Extraction depuis transcription...',
        'phase2': '✨ Phase 2: Correction avec métadonnées...',
        'save': '💾 Sauvegarde dans MongoDB...'
      };
      currentPhase.value = phases[phase] || 'Traitement...';
    };

    // Fonction pour lancer fetch URL en parallèle (fire-and-forget)
    const fetchEpisodeUrlInParallel = (episodeId) => {
      const episode = allEpisodes.value.find(ep => ep.id === episodeId);

      // Skip si URL déjà présente
      if (!episode || episode.episode_page_url) {
        return;
      }

      // Lancer fetch en fire-and-forget (non-bloquant)
      episodeService.fetchEpisodePageUrl(episodeId)
        .then(result => {
          if (result && result.episode_page_url) {
            // Mettre à jour l'épisode dans la liste
            const episodeIndex = allEpisodes.value.findIndex(ep => ep.id === episodeId);
            if (episodeIndex !== -1) {
              allEpisodes.value[episodeIndex].episode_page_url = result.episode_page_url;
            }
          }
        })
        .catch(urlError => {
          console.warn('Impossible de récupérer l\'URL RadioFrance:', urlError);
          // Silent failure - ne pas bloquer la génération
        });
    };

    // Generate avis critiques
    const generateAvisCritiques = async () => {
      if (!selectedEpisodeId.value || isGenerating.value) return;

      isGenerating.value = true;
      currentPhase.value = '';
      error.value = null;

      try {
        // Simuler phases pour l'UI (le backend fait tout d'un coup)
        setPhase('fetch');
        await new Promise(resolve => setTimeout(resolve, 500));

        // Lancer fetch URL RadioFrance en parallèle (non-bloquant)
        fetchEpisodeUrlInParallel(selectedEpisodeId.value);

        setPhase('phase1');

        // Appel API réel
        const result = await avisCritiquesService.generateAvisCritiques({
          episode_id: selectedEpisodeId.value
        });

        setPhase('phase2');
        await new Promise(resolve => setTimeout(resolve, 300));

        setPhase('save');

        // Sauvegarde automatique
        await avisCritiquesService.saveAvisCritiques({
          episode_id: selectedEpisodeId.value,
          summary: result.summary,
          summary_phase1: result.summary_phase1,
          metadata: result.metadata
        });

        // Afficher le résultat
        generationResult.value = result;

        // Mettre à jour la pastille (passer de gris à vert)
        const episodeIndex = allEpisodes.value.findIndex(ep => ep.id === selectedEpisodeId.value);
        if (episodeIndex !== -1) {
          allEpisodes.value[episodeIndex].has_summary = true;
        }

      } catch (err) {
        console.error('Erreur génération:', err);
        error.value = err.message || 'Erreur lors de la génération';
      } finally {
        isGenerating.value = false;
        currentPhase.value = '';
      }
    };

    const renderMarkdown = (text) => {
      return marked(text);
    };

    // Keyboard navigation
    let keydownHandler = null;

    onMounted(async () => {
      await loadAllEpisodes();

      // Keyboard navigation (ArrowLeft / ArrowRight)
      keydownHandler = async (e) => {
        if (isGenerating.value || navLock.value) return;
        if (!selectedEpisodeId.value) return;

        if (e.key === 'ArrowLeft') {
          e.preventDefault();
          await selectPreviousEpisode();
        } else if (e.key === 'ArrowRight') {
          e.preventDefault();
          await selectNextEpisode();
        }
      };

      window.addEventListener('keydown', keydownHandler, true);  // Capture phase
    });

    onBeforeUnmount(() => {
      if (keydownHandler) {
        window.removeEventListener('keydown', keydownHandler, true);
      }
    });

    return {
      allEpisodes,
      selectedEpisodeId,
      loading,
      error,
      isGenerating,
      currentPhase,
      generationResult,
      generateAvisCritiques,
      renderMarkdown,
      isSummaryEmpty,
      onEpisodeChange,
      currentEpisodeIndex,
      hasPreviousEpisode,
      hasNextEpisode,
      episodeHasSummary,
      selectPreviousEpisode,
      selectNextEpisode
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

.form-label {
  display: block;
  font-weight: 500;
  color: #666;
  margin-bottom: 0.75rem;
  font-size: 0.95rem;
}

.episode-select-wrapper {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  margin-bottom: 1rem;
}

.nav-episode-btn {
  padding: 0.75rem 1rem;
  border: 1px solid #ddd;
  background: white;
  cursor: pointer;
  border-radius: 6px;
  font-size: 0.9rem;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.nav-episode-btn:hover:not(:disabled) {
  border-color: #667eea;
  background: #f5f7ff;
}

.nav-episode-btn:disabled {
  cursor: not-allowed;
  opacity: 0.5;
  color: #999;
}

.action-buttons-top {
  margin-top: 1rem;
  display: flex;
  gap: 0.5rem;
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

.diff-view {
  margin-top: 1rem;
}
</style>
