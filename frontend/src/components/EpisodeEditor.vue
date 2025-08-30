<template>
  <div v-if="episode" class="episode-editor card">
    <h2>Édition de l'épisode</h2>

    <!-- Informations de l'épisode -->
    <div class="episode-info">
      <h3>{{ episode.titre }}</h3>
      <p class="episode-meta">
        <strong>Date:</strong> {{ formatDate(episode.date) }} |
        <strong>Type:</strong> {{ episode.type || 'Non spécifié' }}
      </p>
    </div>

    <!-- Description originale (lecture seule) -->
    <div class="form-group">
      <label class="form-label">Description originale:</label>
      <textarea
        :value="episode.description"
        class="form-control"
        readonly
        rows="8"
        style="background-color: #f8f9fa; resize: vertical;"
      ></textarea>
    </div>

    <!-- Éditeur de description corrigée -->
    <div class="form-group">
      <label for="description-corrected" class="form-label">
        Description corrigée:
      </label>
      <textarea
        id="description-corrected"
        v-model="correctedDescription"
        @input="onDescriptionChange"
        class="form-control episode-editor"
        rows="8"
        placeholder="Tapez ici votre version corrigée de la description..."
      ></textarea>

      <!-- Statut de sauvegarde -->
      <div class="save-status">
        <span v-if="saveStatus === 'saving'" class="saving">
          💾 Sauvegarde en cours...
        </span>
        <span v-else-if="saveStatus === 'saved'" class="saved">
          ✅ Sauvegardé automatiquement
        </span>
        <span v-else-if="saveStatus === 'error'" class="error">
          ❌ Erreur de sauvegarde - {{ saveError }}
        </span>
        <span v-else-if="hasChanges" class="pending">
          ⏳ Modification en attente...
        </span>
      </div>
    </div>

    <!-- Affichage d'erreur global -->
    <div v-if="error" class="alert alert-error">
      {{ error }}
    </div>
  </div>
</template>

<script>
import debounce from 'lodash.debounce';
import { episodeService } from '../services/api.js';
import { ErrorHandler } from '../utils/errorHandler.js';

export default {
  name: 'EpisodeEditor',

  props: {
    episode: {
      type: Object,
      default: null,
    },
  },

  data() {
    return {
      correctedDescription: '',
      originalCorrectedDescription: '',
      saveStatus: '', // '', 'saving', 'saved', 'error'
      saveError: '',
      error: null,
      hasChanges: false,
    };
  },

  watch: {
    episode: {
      handler(newEpisode) {
        if (newEpisode) {
          this.correctedDescription = newEpisode.description_corrigee || newEpisode.description || '';
          this.originalCorrectedDescription = this.correctedDescription;
          this.hasChanges = false;
          this.saveStatus = '';
          this.error = null;
        }
      },
      immediate: true,
    },
  },

  methods: {
    /**
     * Gère les changements dans la description
     */
    onDescriptionChange() {
      this.hasChanges = this.correctedDescription !== this.originalCorrectedDescription;

      if (this.hasChanges) {
        this.saveStatus = '';
        this.debouncedSave();
      }
    },

    /**
     * Sauvegarde avec debounce (2 secondes)
     */
    debouncedSave: debounce(function() {
      this.saveDescription();
    }, 2000),

    /**
     * Sauvegarde la description corrigée
     */
    async saveDescription() {
      if (!this.hasChanges || !this.episode) {
        return;
      }

      this.saveStatus = 'saving';
      this.error = null;

      try {
        await episodeService.updateEpisodeDescription(
          this.episode.id,
          this.correctedDescription
        );

        this.originalCorrectedDescription = this.correctedDescription;
        this.hasChanges = false;
        this.saveStatus = 'saved';

        // Masquer le statut "sauvegardé" après 3 secondes
        setTimeout(() => {
          if (this.saveStatus === 'saved') {
            this.saveStatus = '';
          }
        }, 3000);

      } catch (error) {
        this.saveStatus = 'error';
        this.saveError = ErrorHandler.handleError(error);
        console.error('Erreur de sauvegarde:', error);
      }
    },

    /**
     * Formate une date pour l'affichage
     * @param {string} dateString - Date ISO
     * @returns {string} Date formatée
     */
    formatDate(dateString) {
      if (!dateString) return 'Date inconnue';

      try {
        return new Date(dateString).toLocaleDateString('fr-FR', {
          year: 'numeric',
          month: 'long',
          day: 'numeric',
        });
      } catch {
        return 'Date invalide';
      }
    },
  },

  beforeUnmount() {
    // Annuler le debounce si le composant est détruit
    if (this.debouncedSave) {
      this.debouncedSave.cancel();
    }
  },
};
</script>

<style scoped>
.episode-editor {
  margin-top: 2rem;
}

.episode-info {
  margin-bottom: 2rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid #eee;
}

.episode-info h3 {
  color: #333;
  margin-bottom: 0.5rem;
}

.episode-meta {
  color: #666;
  font-size: 0.9rem;
}

.episode-editor textarea {
  min-height: 200px;
  resize: vertical;
  font-family: 'Georgia', serif;
  line-height: 1.6;
}

.save-status {
  font-size: 0.9rem;
  margin-top: 0.5rem;
  min-height: 1.2em;
}

.save-status .saving {
  color: #007bff;
}

.save-status .saved {
  color: #28a745;
}

.save-status .error {
  color: #dc3545;
}

.save-status .pending {
  color: #ffc107;
}
</style>
