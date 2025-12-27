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
            <div class="episode-select-wrapper">
              <button
                class="nav-episode-btn prev-btn"
                @click.prevent="selectPreviousEpisode"
                :disabled="!hasPreviousEpisode"
                aria-label="Épisode précédent"
              >
                ◀️ Précédent
              </button>
              <EpisodeDropdown
                v-model="selectedEpisodeId"
                :episodes="episodesWithReviews || []"
                @update:modelValue="onEpisodeChange"
              />
              <button
                class="nav-episode-btn next-btn"
                @click.prevent="selectNextEpisode"
                :disabled="!hasNextEpisode"
                aria-label="Épisode suivant"
              >
                Suivant ▶️
              </button>
              <button
                v-if="selectedEpisodeId"
                @click="refreshCritiquesDetection"
                class="btn-icon-refresh"
                data-testid="refresh-critiques-button"
                title="Relancer la détection des critiques"
                aria-label="Relancer la détection des critiques"
              >
                🔄
              </button>
            </div>
          </div>
        </div>

        <!-- Détails de l'épisode (accordéon replié) -->
        <div v-if="selectedEpisode" class="episode-details-accordion">
          <button
            @click="showEpisodeDetails = !showEpisodeDetails"
            class="accordion-toggle"
            :aria-expanded="showEpisodeDetails"
          >
            <span class="toggle-icon">{{ showEpisodeDetails ? '▼' : '▶' }}</span>
            <span class="toggle-label">Détails de l'épisode (titre et description)</span>
          </button>
          <div v-if="showEpisodeDetails" class="accordion-content">
            <div class="episode-info-container">
              <!-- Logo RadioFrance cliquable à gauche -->
              <a
                v-if="selectedEpisodeFull && selectedEpisodeFull.episode_page_url"
                :href="selectedEpisodeFull.episode_page_url"
                target="_blank"
                rel="noopener noreferrer"
                class="episode-logo-link"
                title="Voir la page de l'épisode sur RadioFrance"
              >
                <img
                  src="@/assets/le-masque-et-la-plume-logo.jpg"
                  alt="Logo Le Masque et la Plume"
                  class="episode-logo"
                />
              </a>

              <!-- Informations de l'épisode à droite -->
              <div class="episode-info">
                <div class="info-section">
                  <strong>Titre :</strong>
                  <p class="episode-title">{{ episodeDisplayTitle }}</p>
                </div>
                <div class="info-section">
                  <strong>Description :</strong>
                  <p class="episode-description">{{ episodeDisplayDescription }}</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- Liste des critiques détectés -->
      <section v-if="selectedEpisodeId" class="critiques-section">
        <div class="card">
          <h2>
            Critiques détectés dans cet épisode
            <span v-if="selectedEpisode" class="episode-date">
              ({{ formatDate(selectedEpisode.date) }})
            </span>
          </h2>

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
                  <!-- Afficher le nom correct pour les existants, sinon le nom détecté -->
                  <span v-if="critique.status === 'existing' && critique.matched_critique">
                    {{ critique.matched_critique }}
                  </span>
                  <span v-else>
                    {{ critique.detected_name }}
                  </span>
                </div>
                <div class="critique-details">
                  <!-- Badge de statut -->
                  <span v-if="critique.status === 'existing'" class="badge badge-success">
                    ✓ Existant
                    <span v-if="critique.match_type === 'exact'">(match exact)</span>
                  </span>
                  <span v-if="critique.status === 'new'" class="badge badge-warning">
                    ✨ Nouveau
                  </span>
                  <!-- Variante détectée (si différente du nom correct) -->
                  <span v-if="critique.status === 'existing' && critique.match_type === 'variante'" class="variante-info">
                    Variante détectée : "{{ critique.detected_name }}"
                  </span>
                </div>
              </div>

              <div class="critique-actions">
                <button
                  v-if="critique.status === 'new'"
                  @click="openCreateModal(critique.detected_name)"
                  class="btn btn-primary btn-sm"
                >
                  Créer
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

      <!-- Modale de création de critique -->
      <div v-if="showCreateModal" class="modal-overlay" @click="closeCreateModal">
        <div class="modal-content" @click.stop>
          <div class="modal-header">
            <h3>Créer un nouveau critique</h3>
            <button @click="closeCreateModal" class="modal-close">&times;</button>
          </div>

          <div class="modal-body">
            <div class="form-group">
              <label for="critique-nom" class="form-label">
                Nom du critique <span class="required">*</span>
              </label>
              <input
                id="critique-nom"
                v-model="critiqueForm.nom"
                type="text"
                class="form-input"
                placeholder="Prénom Nom"
                @keyup.enter="submitCreateCritique"
              />
              <small class="form-help">
                Nom corrigé qui sera enregistré dans la base de données
              </small>
            </div>

            <div class="form-group">
              <label class="form-label">
                Variante détectée
              </label>
              <div class="variante-detected">
                {{ critiqueForm.detectedName }}
              </div>
              <small class="form-help">
                Cette variante sera automatiquement ajoutée pour faciliter la détection future
              </small>
            </div>

            <div class="form-group">
              <label class="checkbox-label">
                <input
                  type="checkbox"
                  v-model="critiqueForm.animateur"
                  class="form-checkbox"
                />
                <span>Animateur</span>
              </label>
              <small class="form-help">
                Cocher cette case si cette personne est un animateur (Jérôme Garcin, Rebecca Manzoni, etc.)
              </small>
            </div>

            <div v-if="createError" class="alert alert-error">
              {{ createError }}
            </div>
          </div>

          <div class="modal-footer">
            <button @click="closeCreateModal" class="btn btn-secondary">
              Annuler
            </button>
            <button
              @click="submitCreateCritique"
              class="btn btn-primary"
              :disabled="!critiqueForm.nom.trim() || creatingCritique"
            >
              {{ creatingCritique ? 'Création...' : 'Créer' }}
            </button>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue';
import axios from 'axios';
import Navigation from '@/components/Navigation.vue';
import EpisodeDropdown from '@/components/EpisodeDropdown.vue';
import { episodeService } from '@/services/api';

// Créer une instance axios pour l'API avec baseURL relative (proxy Vite)
const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

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
    const creatingCritique = ref(false);

    // État de la modale de création
    const showCreateModal = ref(false);
    const critiqueForm = ref({
      nom: '',
      detectedName: '',
      animateur: false
    });
    const createError = ref(null);

    // Contrôle d'affichage des détails de l'épisode
    const showEpisodeDetails = ref(false);
    const selectedEpisodeFull = ref(null);

    // Verrou de navigation pour éviter les clics multiples
    const navLock = ref(false);

    // Charger les épisodes avec avis critiques
    const loadEpisodesWithReviews = async () => {
      episodesLoading.value = true;
      episodesError.value = null;

      try {
        const response = await api.get('/episodes-with-avis-critiques');
        // L'endpoint retourne déjà le champ 'id' via to_summary_dict()
        episodesWithReviews.value = response.data;

        // Sélectionner automatiquement le premier épisode avec critiques "new" (pas en base)
        if (episodesWithReviews.value.length > 0 && !selectedEpisodeId.value) {
          // Utiliser le flag has_incomplete_books (pastille rouge) pour trouver rapidement
          // le premier épisode avec des critiques "new" sans faire de requêtes supplémentaires
          const episodeWithNew = episodesWithReviews.value.find(
            ep => ep.has_incomplete_books === true
          );

          if (episodeWithNew) {
            // Épisode avec critiques "new" trouvé
            selectedEpisodeId.value = episodeWithNew.id;
          } else {
            // Aucun épisode avec critiques "new", sélectionner le premier épisode
            selectedEpisodeId.value = episodesWithReviews.value[0].id;
          }

          // Charger les critiques de l'épisode sélectionné
          await loadDetectedCritiques();
        }

        // Charger les détails complets de l'épisode sélectionné
        if (selectedEpisodeId.value) {
          try {
            const response = await api.get(`/episodes/${selectedEpisodeId.value}`);
            selectedEpisodeFull.value = response.data;

            // Fetch automatiquement l'URL de la page RadioFrance EN ARRIÈRE-PLAN
            // (ne pas bloquer l'affichage des critiques)
            if (selectedEpisodeFull.value && !selectedEpisodeFull.value.episode_page_url) {
              // Lance la requête en arrière-plan (pas de await)
              episodeService.fetchEpisodePageUrl(selectedEpisodeId.value)
                .then(result => {
                  if (result.success && result.episode_page_url && selectedEpisodeFull.value) {
                    selectedEpisodeFull.value.episode_page_url = result.episode_page_url;
                  }
                })
                .catch(err => {
                  console.warn('Impossible de récupérer l\'URL de la page RadioFrance:', err.message || err);
                });
            }
          } catch (error) {
            console.warn('Impossible de récupérer les détails complets de l\'épisode:', error.message || error);
          }
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
        const response = await api.get(
          `/episodes/${selectedEpisodeId.value}/critiques-detectes`
        );
        detectedCritiques.value = response.data.detected_critiques;
      } catch (error) {
        console.error('Erreur lors du chargement des critiques:', error);
        critiquesError.value = error.response?.data?.detail || error.message || 'Erreur lors du chargement des critiques';
      } finally {
        critiquesLoading.value = false;
      }
    };

    // Rafraîchir la détection des critiques pour l'épisode sélectionné
    const refreshCritiquesDetection = async () => {
      if (!selectedEpisodeId.value) return;

      try {
        // Simplement recharger les critiques (l'endpoint re-extrait à chaque fois)
        await loadDetectedCritiques();
      } catch (error) {
        console.error('Erreur lors du rafraîchissement:', error);
        critiquesError.value = error.response?.data?.detail || error.message || 'Erreur lors du rafraîchissement';
      }
    };

    // Ouvrir la modale de création
    const openCreateModal = (detectedName) => {
      critiqueForm.value = {
        nom: detectedName,  // Pré-remplir avec le nom détecté
        detectedName: detectedName,
        animateur: false
      };
      createError.value = null;
      showCreateModal.value = true;
    };

    // Fermer la modale de création
    const closeCreateModal = () => {
      showCreateModal.value = false;
      critiqueForm.value = {
        nom: '',
        detectedName: '',
        animateur: false
      };
      createError.value = null;
    };

    // Soumettre la création du critique
    const submitCreateCritique = async () => {
      if (!critiqueForm.value.nom.trim()) {
        createError.value = 'Le nom du critique est requis';
        return;
      }

      creatingCritique.value = true;
      createError.value = null;

      try {
        // Préparer les variantes
        const variantes = [];

        // Ajouter la variante détectée seulement si elle est différente du nom corrigé
        if (critiqueForm.value.detectedName.trim() !== critiqueForm.value.nom.trim()) {
          variantes.push(critiqueForm.value.detectedName.trim());
        }

        await api.post('/critiques', {
          nom: critiqueForm.value.nom.trim(),
          variantes: variantes,
          animateur: critiqueForm.value.animateur
        });

        // Fermer la modale et recharger les critiques + pastilles
        closeCreateModal();
        await loadDetectedCritiques();

        // Recharger la liste des épisodes pour mettre à jour les pastilles
        await loadEpisodesWithReviews();
      } catch (error) {
        console.error('Erreur lors de la création du critique:', error);
        createError.value = error.response?.data?.detail || error.message || 'Erreur lors de la création du critique';
      } finally {
        creatingCritique.value = false;
      }
    };

    // Navigation entre épisodes
    const selectPreviousEpisode = async () => {
      if (navLock.value || !hasPreviousEpisode.value) return;

      navLock.value = true;
      try {
        // Move to older episode (to the right on timeline) => index + 1
        const idx = currentEpisodeIndex.value;
        if (idx >= 0 && idx < episodesWithReviews.value.length - 1) {
          const prev = episodesWithReviews.value[idx + 1];
          selectedEpisodeId.value = prev.id;
          await onEpisodeChange();
        }
      } finally {
        navLock.value = false;
      }
    };

    const selectNextEpisode = async () => {
      if (navLock.value || !hasNextEpisode.value) return;

      navLock.value = true;
      try {
        // Move to more recent episode (to the left on timeline) => index - 1
        const idx = currentEpisodeIndex.value;
        if (idx > 0) {
          const next = episodesWithReviews.value[idx - 1];
          selectedEpisodeId.value = next.id;
          await onEpisodeChange();
        }
      } finally {
        navLock.value = false;
      }
    };

    // Gérer le changement d'épisode
    const onEpisodeChange = async () => {
      // Réinitialiser les détails de l'épisode
      selectedEpisodeFull.value = null;

      // Charger les détails complets de l'épisode
      if (selectedEpisodeId.value) {
        try {
          const response = await api.get(`/episodes/${selectedEpisodeId.value}`);
          selectedEpisodeFull.value = response.data;

          // Fetch automatiquement l'URL de la page RadioFrance EN ARRIÈRE-PLAN
          // (ne pas bloquer l'affichage des critiques)
          if (selectedEpisodeFull.value && !selectedEpisodeFull.value.episode_page_url) {
            // Lance la requête en arrière-plan (pas de await)
            episodeService.fetchEpisodePageUrl(selectedEpisodeId.value)
              .then(result => {
                if (result.success && result.episode_page_url && selectedEpisodeFull.value) {
                  selectedEpisodeFull.value.episode_page_url = result.episode_page_url;
                }
              })
              .catch(err => {
                console.warn('Impossible de récupérer l\'URL de la page RadioFrance:', err.message || err);
              });
          }
        } catch (error) {
          console.warn('Impossible de récupérer les détails complets de l\'épisode:', error.message || error);
        }
      }

      await loadDetectedCritiques();
    };

    // Propriété computed pour l'épisode sélectionné
    const selectedEpisode = computed(() => {
      if (!selectedEpisodeId.value) return null;
      return episodesWithReviews.value.find(ep => ep.id === selectedEpisodeId.value);
    });

    // Display helpers pour le titre/description de l'épisode
    const episodeDisplayTitle = computed(() => {
      const epFull = selectedEpisodeFull.value;
      const ep = epFull || selectedEpisode.value;
      if (!ep) return '';
      return ep.titre_corrige || ep.titre || ep.title || '';
    });

    const episodeDisplayDescription = computed(() => {
      const epFull = selectedEpisodeFull.value;
      const ep = epFull || selectedEpisode.value;
      if (!ep) return '';
      return ep.description || ep.description_origin || ep.resume || ep.excerpt || '';
    });

    // Computed properties pour la navigation
    const currentEpisodeIndex = computed(() => {
      if (!episodesWithReviews.value || !selectedEpisodeId.value) return -1;
      return episodesWithReviews.value.findIndex(ep => String(ep.id) === String(selectedEpisodeId.value));
    });

    // Note: episodes are sorted from most recent to oldest. "Previous" (left) should go to older
    // episodes (higher index). "Next" (right) goes to more recent (lower index).
    const hasPreviousEpisode = computed(() => {
      return currentEpisodeIndex.value >= 0 && currentEpisodeIndex.value < (episodesWithReviews.value.length - 1);
    });

    const hasNextEpisode = computed(() => {
      return currentEpisodeIndex.value > 0;
    });

    // Formater la date
    const formatDate = (dateStr) => {
      if (!dateStr) return '';
      const date = new Date(dateStr);
      return date.toLocaleDateString('fr-FR', {
        day: '2-digit',
        month: 'short',
        year: 'numeric'
      });
    };

    // Handler pour la navigation au clavier (flèches gauche/droite)
    const handleKeydown = async (e) => {
      // Ne pas intercepter si on est dans un input/textarea
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
        return;
      }

      if (e.key === 'ArrowLeft') {
        // Flèche gauche = épisode précédent (plus ancien)
        e.preventDefault();
        await selectPreviousEpisode();
      } else if (e.key === 'ArrowRight') {
        // Flèche droite = épisode suivant (plus récent)
        e.preventDefault();
        await selectNextEpisode();
      }
    };

    // Charger les épisodes au montage
    onMounted(async () => {
      await loadEpisodesWithReviews();

      // Ajouter le listener pour les touches du clavier
      // Use capture phase pour recevoir l'événement avant les handlers natifs
      window.addEventListener('keydown', handleKeydown, true);
    });

    // Nettoyer le listener avant démontage
    onBeforeUnmount(() => {
      window.removeEventListener('keydown', handleKeydown, true);
    });

    return {
      // Episodes
      episodesWithReviews,
      episodesLoading,
      episodesError,
      selectedEpisodeId,
      selectedEpisode,
      selectedEpisodeFull,
      loadEpisodesWithReviews,

      // Critiques
      detectedCritiques,
      critiquesLoading,
      critiquesError,
      creatingCritique,
      loadDetectedCritiques,
      refreshCritiquesDetection,

      // Modale de création
      showCreateModal,
      critiqueForm,
      createError,
      openCreateModal,
      closeCreateModal,
      submitCreateCritique,

      // Détails de l'épisode
      showEpisodeDetails,
      episodeDisplayTitle,
      episodeDisplayDescription,

      // Navigation
      currentEpisodeIndex,
      hasPreviousEpisode,
      hasNextEpisode,
      selectPreviousEpisode,
      selectNextEpisode,

      // Actions
      onEpisodeChange,

      // Helpers
      formatDate
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

.episode-select-wrapper {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.nav-episode-btn {
  background: #111827;
  color: #fff;
  border: 1px solid rgba(255,255,255,0.06);
  padding: 0.5rem 0.75rem;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
}

.nav-episode-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.prev-btn {
  margin-right: 0.25rem;
}

.next-btn {
  margin-left: 0.25rem;
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

.episode-date {
  font-size: 0.9rem;
  font-weight: normal;
  color: #666;
  margin-left: 0.5rem;
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
  margin-bottom: 0.25rem;
}

.critique-details {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  font-size: 0.9rem;
}

.variante-info {
  font-size: 0.85rem;
  color: #666;
  font-style: italic;
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

/* Styles pour la modale */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
  max-width: 500px;
  width: 90%;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  border-bottom: 1px solid #e0e0e0;
}

.modal-header h3 {
  margin: 0;
  color: #333;
  font-size: 1.25rem;
}

.modal-close {
  background: none;
  border: none;
  font-size: 2rem;
  color: #999;
  cursor: pointer;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: color 0.2s ease;
}

.modal-close:hover {
  color: #333;
}

.modal-body {
  padding: 1.5rem;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
  padding: 1.5rem;
  border-top: 1px solid #e0e0e0;
}

.form-input {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 1rem;
  transition: border-color 0.2s ease;
}

.form-input:focus {
  outline: none;
  border-color: #667eea;
}

.form-help {
  display: block;
  margin-top: 0.5rem;
  color: #666;
  font-size: 0.875rem;
}

.required {
  color: #e53e3e;
}

.variante-detected {
  padding: 0.75rem;
  background: #f7f7f7;
  border-radius: 8px;
  color: #333;
  font-weight: 500;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  cursor: pointer;
  font-weight: 500;
  color: #333;
}

.form-checkbox {
  width: 1.25rem;
  height: 1.25rem;
  cursor: pointer;
  border: 2px solid #ddd;
  border-radius: 4px;
  transition: all 0.2s ease;
}

.form-checkbox:checked {
  background-color: #667eea;
  border-color: #667eea;
}

.form-checkbox:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.2);
}

.btn-secondary {
  background: #e0e0e0;
  color: #333;
}

.btn-secondary:hover {
  background: #d0d0d0;
}

/* Accordéon détails de l'épisode */
.episode-details-accordion {
  margin-top: 1rem;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  overflow: hidden;
  background: white;
}

.accordion-toggle {
  width: 100%;
  padding: 1rem 1.5rem;
  background: #f9fafb;
  border: none;
  border-bottom: 1px solid #e5e7eb;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-size: 0.95rem;
  font-weight: 500;
  color: #374151;
  transition: background-color 0.2s ease;
}

.accordion-toggle:hover {
  background: #f3f4f6;
}

.accordion-toggle[aria-expanded="true"] {
  background: #eff6ff;
  border-bottom-color: #bfdbfe;
}

.toggle-icon {
  color: #667eea;
  font-size: 0.85rem;
  transition: transform 0.2s ease;
}

.toggle-label {
  flex: 1;
  text-align: left;
}

.accordion-content {
  padding: 1.5rem;
  background: white;
  animation: slideDown 0.2s ease-out;
}

@keyframes slideDown {
  from {
    opacity: 0;
    max-height: 0;
  }
  to {
    opacity: 1;
    max-height: 500px;
  }
}

/* Container pour logo + infos épisode en layout horizontal */
.episode-info-container {
  display: flex;
  gap: 1.5rem;
  align-items: center;
}

/* Logo RadioFrance cliquable */
.episode-logo-link {
  flex-shrink: 0;
  display: block;
  transition: transform 0.2s ease, opacity 0.2s ease;
}

.episode-logo-link:hover {
  transform: scale(1.05);
  opacity: 0.9;
}

.episode-logo {
  width: 80px;
  height: 80px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  object-fit: cover;
}

/* Informations de l'épisode */
.episode-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.info-section {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.info-section strong {
  color: #374151;
  font-size: 0.875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.episode-title,
.episode-description {
  margin: 0;
  color: #1f2937;
  line-height: 1.6;
  font-size: 0.95rem;
}

.episode-description {
  color: #4b5563;
}

/* Bouton de rafraîchissement */
.btn-icon-refresh {
  flex-shrink: 0;
  width: 38px;
  height: 38px;
  padding: 0;
  border: 1px solid #ddd;
  border-radius: 6px;
  background: white;
  font-size: 1.2rem;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.btn-icon-refresh:hover {
  background: #f8f9fa;
  border-color: #667eea;
  transform: rotate(180deg);
}

.btn-icon-refresh:active {
  transform: rotate(180deg) scale(0.95);
}
</style>
