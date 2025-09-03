<template>
  <div v-if="episode" class="episode-editor card">
    <h2>Édition de l'épisode</h2>

    <!-- Informations de l'épisode -->
    <div class="episode-info">
      <!-- Édition du titre -->
      <div class="form-group">
        <label for="titre-corrected" class="form-label">Titre:</label>
        <input
          id="titre-corrected"
          v-model="correctedTitle"
          @input="onTitleChange"
          class="form-control"
          placeholder="Titre de l'épisode"
        />

        <!-- Statut de sauvegarde du titre -->
        <div class="save-status">
          <span v-if="titleSaveStatus === 'saving'" class="saving">
            💾 Sauvegarde du titre en cours...
          </span>
          <span v-else-if="titleSaveStatus === 'saved'" class="saved">
            ✅ Titre sauvegardé automatiquement
          </span>
          <span v-else-if="titleSaveStatus === 'error'" class="error">
            ❌ Erreur de sauvegarde du titre - {{ titleSaveError }}
          </span>
          <span v-else-if="hasTitleChanges" class="pending">
            ⏳ Modification du titre en attente...
          </span>
        </div>
      </div>
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

      <!-- Statut de sauvegarde de la description -->
      <div class="save-status">
        <span v-if="descriptionSaveStatus === 'saving'" class="saving">
          💾 Sauvegarde de la description en cours...
        </span>
        <span v-else-if="descriptionSaveStatus === 'saved'" class="saved">
          ✅ Description sauvegardée automatiquement
        </span>
        <span v-else-if="descriptionSaveStatus === 'error'" class="error">
          ❌ Erreur de sauvegarde de la description - {{ descriptionSaveError }}
        </span>
        <span v-else-if="hasDescriptionChanges" class="pending">
          ⏳ Modification de la description en attente...
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
import { memoryGuard } from '../utils/memoryGuard.js';

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
      correctedTitle: '',
      originalCorrectedDescription: '',
      originalCorrectedTitle: '',
      titleSaveStatus: '', // '', 'saving', 'saved', 'error'
      titleSaveError: '',
      descriptionSaveStatus: '', // '', 'saving', 'saved', 'error'
      descriptionSaveError: '',
      error: null,
      hasChanges: false,
      hasTitleChanges: false,
      hasDescriptionChanges: false,
    };
  },

  created() {
    // Créer les fonctions debounced avec cancel
    this.debouncedSaveDescription = debounce(this.saveDescription, 2000);
    this.debouncedSaveTitle = debounce(this.saveTitle, 2000);
  },

  watch: {
    episode: {
      handler(newEpisode) {
        if (newEpisode) {
          this.correctedDescription = newEpisode.description_corrigee || newEpisode.description || '';
          this.correctedTitle = newEpisode.titre_corrige || newEpisode.titre || '';
          this.originalCorrectedDescription = this.correctedDescription;
          this.originalCorrectedTitle = this.correctedTitle;
          this.hasChanges = false;
          this.hasTitleChanges = false;
          this.hasDescriptionChanges = false;
          this.titleSaveStatus = '';
          this.descriptionSaveStatus = '';
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
      this.hasDescriptionChanges = this.correctedDescription !== this.originalCorrectedDescription;
      this.hasChanges = this.hasDescriptionChanges || this.hasTitleChanges;

      if (this.hasDescriptionChanges) {
        this.descriptionSaveStatus = '';
        this.debouncedSaveDescription();
      }
    },

    /**
     * Gère les changements dans le titre
     */
    onTitleChange() {
      this.hasTitleChanges = this.correctedTitle !== this.originalCorrectedTitle;
      this.hasChanges = this.hasTitleChanges || this.hasDescriptionChanges;

      if (this.hasTitleChanges) {
        this.titleSaveStatus = '';
        this.debouncedSaveTitle();
      }
    },


    /**
     * Sauvegarde la description corrigée
     */
    async saveDescription() {
      if (!this.hasChanges || !this.episode) {
        return;
      }

      // Vérification mémoire avant sauvegarde
      const memoryCheck = memoryGuard.checkMemoryLimit();
      if (memoryCheck) {
        if (memoryCheck.includes('LIMITE MÉMOIRE DÉPASSÉE')) {
          memoryGuard.forceShutdown(memoryCheck);
          return;
        }
        console.warn(`⚠️ ${memoryCheck}`);
      }

      this.descriptionSaveStatus = 'saving';
      this.error = null;

      try {
        await episodeService.updateEpisodeDescription(
          this.episode.id,
          this.correctedDescription
        );

        this.originalCorrectedDescription = this.correctedDescription;
        this.hasDescriptionChanges = false;
        this.hasChanges = this.hasTitleChanges;
        this.descriptionSaveStatus = 'saved';

        // Masquer le statut "sauvegardé" après 3 secondes
        setTimeout(() => {
          if (this.descriptionSaveStatus === 'saved') {
            this.descriptionSaveStatus = '';
          }
        }, 3000);

      } catch (error) {
        this.descriptionSaveStatus = 'error';
        this.descriptionSaveError = ErrorHandler.handleError(error);
        // Only log errors in non-test environments
        if (process.env.NODE_ENV !== 'test' && !import.meta.env?.VITEST) {
          console.error('Erreur de sauvegarde:', error);
        }
      }
    },

    /**
     * Sauvegarde le titre corrigé
     */
    async saveTitle() {
      if (!this.hasChanges || !this.episode) {
        return;
      }

      // Vérification mémoire avant sauvegarde
      const memoryCheck = memoryGuard.checkMemoryLimit();
      if (memoryCheck) {
        if (memoryCheck.includes('LIMITE MÉMOIRE DÉPASSÉE')) {
          memoryGuard.forceShutdown(memoryCheck);
          return;
        }
        console.warn(`⚠️ ${memoryCheck}`);
      }

      this.titleSaveStatus = 'saving';
      this.error = null;

      try {
        await episodeService.updateEpisodeTitle(
          this.episode.id,
          this.correctedTitle
        );

        this.originalCorrectedTitle = this.correctedTitle;
        this.hasTitleChanges = false;
        this.hasChanges = this.hasDescriptionChanges;
        this.titleSaveStatus = 'saved';

        // Masquer le statut "sauvegardé" après 3 secondes
        setTimeout(() => {
          if (this.titleSaveStatus === 'saved') {
            this.titleSaveStatus = '';
          }
        }, 3000);

      } catch (error) {
        this.titleSaveStatus = 'error';
        this.titleSaveError = ErrorHandler.handleError(error);
        // Only log errors in non-test environments
        if (process.env.NODE_ENV !== 'test' && !import.meta.env?.VITEST) {
          console.error('Erreur de sauvegarde:', error);
        }
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
        const date = new Date(dateString);
        if (isNaN(date.getTime())) {
          return 'Date invalide';
        }
        return date.toLocaleDateString('fr-FR', {
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
    // Annuler les debounces si le composant est détruit
    if (this.debouncedSaveDescription) {
      this.debouncedSaveDescription.cancel();
    }
    if (this.debouncedSaveTitle) {
      this.debouncedSaveTitle.cancel();
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
