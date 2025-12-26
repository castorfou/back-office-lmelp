<template>
  <div class="identification-critiques">
    <!-- Navigation -->
    <Navigation pageTitle="Identification des Critiques" />

    <main>
      <!-- Sélecteur d'épisode -->
      <section class="episode-selector-section">
        <div class="episode-selector card">
          <!-- État de chargement des épisodes -->
          <div v-if="episodesLoading" class="loading">
            Chargement des épisodes avec avis critiques...
          </div>

          <!-- Affichage d'erreur des épisodes -->
          <div v-if="episodesError" class="alert alert-error">
            {{ episodesError }}
            <button @click="loadEpisodesWithReviews" class="btn btn-primary" style="margin-left: 1rem;">
              Réessayer
            </button>
          </div>

          <!-- Sélecteur d'épisode -->
          <div v-if="!episodesLoading && !episodesError" class="form-group">
            <label for="episode-select" class="form-label">
              Choisir un épisode avec avis critiques ({{ episodesWithReviews?.length || 0 }} disponibles)
            </label>
            <EpisodeDropdown
              v-model="selectedEpisodeId"
              :episodes="episodesWithReviews || []"
              @update:modelValue="onEpisodeChange"
            />
          </div>
        </div>
      </section>

      <!-- Liste des critiques détectés -->
      <section v-if="selectedEpisodeId" class="critiques-section">
        <div class="card">
          <h2>Critiques détectés dans cet épisode</h2>

          <!-- État de chargement des critiques -->
          <div v-if="critiquesLoading" class="loading">
            Chargement des critiques...
          </div>

          <!-- Affichage d'erreur des critiques -->
          <div v-if="critiquesError" class="alert alert-error">
            {{ critiquesError }}
            <button @click="loadDetectedCritiques" class="btn btn-primary" style="margin-left: 1rem;">
              Réessayer
            </button>
          </div>

          <!-- Liste des critiques -->
          <div v-if="!critiquesLoading && !critiquesError && detectedCritiques.length > 0" class="critiques-list">
            <div
              v-for="critique in detectedCritiques"
              :key="critique.detected_name"
              class="critique-item"
              :class="{ 'critique-new': critique.status === 'new', 'critique-existing': critique.status === 'existing' }"
            >
              <div class="critique-info">
                <div class="critique-name">
                  {{ critique.detected_name }}
                </div>
                <div class="critique-status">
                  <span v-if="critique.status === 'existing'" class="badge badge-success">
                    ✓ Existant
                    <span v-if="critique.match_type === 'exact'">(match exact)</span>
                    <span v-if="critique.match_type === 'variante'">(variante de "{{ critique.matched_critique }}")</span>
                  </span>
                  <span v-if="critique.status === 'new'" class="badge badge-warning">
                    ✨ Nouveau
                  </span>
                </div>
              </div>

              <div class="critique-actions">
                <button
                  v-if="critique.status === 'new'"
                  @click="createCritique(critique.detected_name)"
                  class="btn btn-primary btn-sm"
                  :disabled="creatingCritique === critique.detected_name"
                >
                  {{ creatingCritique === critique.detected_name ? 'Création...' : 'Créer' }}
                </button>
              </div>
            </div>
          </div>

          <!-- Aucun critique détecté -->
          <div v-if="!critiquesLoading && !critiquesError && detectedCritiques.length === 0" class="no-critiques">
            Aucun critique détecté dans cet épisode.
          </div>
        </div>
      </section>
    </main>
  </div>
</template>

<script>
import { ref, onMounted, computed } from 'vue';
import axios from 'axios';
import Navigation from '@/components/Navigation.vue';
import EpisodeDropdown from '@/components/EpisodeDropdown.vue';

export default {
  name: 'IdentificationCritiques',

  components: {
    Navigation,
    EpisodeDropdown
  },

  setup() {
    // État des épisodes
    const episodesWithReviews = ref([]);
    const episodesLoading = ref(false);
    const episodesError = ref(null);
    const selectedEpisodeId = ref(null);

    // État des critiques
    const detectedCritiques = ref([]);
    const critiquesLoading = ref(false);
    const critiquesError = ref(null);
    const creatingCritique = ref(null);

    // Backend URL
    const backendUrl = computed(() => {
      return localStorage.getItem('backendUrl') || 'http://localhost:8000';
    });

    // Charger les épisodes avec avis critiques
    const loadEpisodesWithReviews = async () => {
      episodesLoading.value = true;
      episodesError.value = null;

      try {
        const response = await axios.get(`${backendUrl.value}/api/episodes-with-avis-critiques`);
        episodesWithReviews.value = response.data;

        // Sélectionner automatiquement le premier épisode
        if (episodesWithReviews.value.length > 0 && !selectedEpisodeId.value) {
          selectedEpisodeId.value = episodesWithReviews.value[0]._id;
          await loadDetectedCritiques();
        }
      } catch (error) {
        console.error('Erreur lors du chargement des épisodes:', error);
        episodesError.value = error.response?.data?.detail || error.message || 'Erreur lors du chargement des épisodes';
      } finally {
        episodesLoading.value = false;
      }
    };

    // Charger les critiques détectés pour un épisode
    const loadDetectedCritiques = async () => {
      if (!selectedEpisodeId.value) {
        return;
      }

      critiquesLoading.value = true;
      critiquesError.value = null;

      try {
        const response = await axios.get(
          `${backendUrl.value}/api/episodes/${selectedEpisodeId.value}/critiques-detectes`
        );
        detectedCritiques.value = response.data.detected_critiques;
      } catch (error) {
        console.error('Erreur lors du chargement des critiques:', error);
        critiquesError.value = error.response?.data?.detail || error.message || 'Erreur lors du chargement des critiques';
      } finally {
        critiquesLoading.value = false;
      }
    };

    // Créer un nouveau critique
    const createCritique = async (nom) => {
      creatingCritique.value = nom;

      try {
        await axios.post(`${backendUrl.value}/api/critiques`, {
          nom: nom,
          animateur: false
        });

        // Recharger les critiques détectés pour voir le changement de statut
        await loadDetectedCritiques();
      } catch (error) {
        console.error('Erreur lors de la création du critique:', error);
        alert('Erreur lors de la création du critique: ' + (error.response?.data?.detail || error.message));
      } finally {
        creatingCritique.value = null;
      }
    };

    // Gérer le changement d'épisode
    const onEpisodeChange = async () => {
      await loadDetectedCritiques();
    };

    // Charger les épisodes au montage
    onMounted(async () => {
      await loadEpisodesWithReviews();
    });

    return {
      // Episodes
      episodesWithReviews,
      episodesLoading,
      episodesError,
      selectedEpisodeId,
      loadEpisodesWithReviews,

      // Critiques
      detectedCritiques,
      critiquesLoading,
      critiquesError,
      creatingCritique,
      loadDetectedCritiques,
      createCritique,

      // Actions
      onEpisodeChange
    };
  }
};
</script>

<style scoped>
.identification-critiques {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 2rem 2rem;
}

.episode-selector-section {
  margin-bottom: 2rem;
}

.card {
  background: white;
  border-radius: 12px;
  padding: 2rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.form-group {
  margin-bottom: 0;
}

.form-label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 600;
  color: #333;
}

.loading {
  text-align: center;
  padding: 2rem;
  color: #667eea;
  font-style: italic;
}

.alert {
  padding: 1rem;
  border-radius: 8px;
  margin-bottom: 1rem;
}

.alert-error {
  background: #fee;
  color: #c33;
  border: 1px solid #fcc;
}

.btn {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 8px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-primary {
  background: #667eea;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #5a67d8;
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-sm {
  padding: 0.375rem 0.75rem;
  font-size: 0.875rem;
}

.critiques-section h2 {
  margin-top: 0;
  margin-bottom: 1.5rem;
  color: #333;
}

.critiques-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.critique-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  border-radius: 8px;
  border: 2px solid #e0e0e0;
  transition: all 0.2s ease;
}

.critique-item:hover {
  border-color: #667eea;
  box-shadow: 0 2px 4px rgba(102, 126, 234, 0.1);
}

.critique-new {
  background: #fffbf0;
  border-color: #ffa500;
}

.critique-existing {
  background: #f0fff4;
  border-color: #68d391;
}

.critique-info {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.critique-name {
  font-weight: 600;
  font-size: 1.1rem;
  color: #333;
}

.critique-status {
  font-size: 0.9rem;
}

.badge {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  font-weight: 500;
  font-size: 0.875rem;
}

.badge-success {
  background: #c6f6d5;
  color: #22543d;
}

.badge-warning {
  background: #fed7d7;
  color: #742a2a;
}

.no-critiques {
  text-align: center;
  padding: 2rem;
  color: #999;
  font-style: italic;
}
</style>
