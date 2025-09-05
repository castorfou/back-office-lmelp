<template>
  <div v-if="episode" class="episode-editor card">
    <!-- En-tête compact avec date et type à droite -->
    <h2>
      Édition de l'épisode | Date: {{ formatDate(episode.date) }} | Type: {{ episode.type || 'Non spécifié' }}
    </h2>

    <!-- Informations de l'épisode -->
    <div class="episode-info">
      <!-- Édition du titre avec indicateur de modification -->
      <div class="form-group">
        <div class="title-header">
          <label for="titre-corrected" class="form-label">Titre:</label>
          <button
            v-if="hasTitleModification"
            @click="toggleOriginalTitle"
            data-testid="title-modification-indicator"
            class="modification-indicator"
            title="Cliquez pour voir/masquer le titre original"
          >
            📝
          </button>
        </div>

        <!-- Titre original (conditionnel) -->
        <div v-if="showOriginalTitle" data-testid="original-title" class="original-content">
          <label class="form-label-small">Titre original:</label>
          <div class="original-text">{{ episode.titre }}</div>
        </div>

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
    </div>

    <!-- Éditeur de description avec indicateur -->
    <div class="form-group">
      <div class="title-header">
        <label for="description-corrected" class="form-label">
          Description:
        </label>
        <button
          v-if="hasDescriptionModification"
          @click="toggleOriginalDescription"
          data-testid="description-modification-indicator"
          class="modification-indicator"
          title="Cliquez pour voir/masquer la description originale"
        >
          📝
        </button>
      </div>

      <!-- Description originale (conditionnelle) -->
      <div v-if="showOriginalDescription" data-testid="original-description" class="original-content">
        <label class="form-label-small">Description originale:</label>
        <textarea
          :value="episode.description"
          class="form-control original-textarea"
          readonly
          rows="4"
        ></textarea>
      </div>
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
      // Nouvel état pour les toggles (Issue #23)
      showOriginalTitle: false,
      showOriginalDescription: false,
      // Persistence des toggles pendant la session
      sessionToggleState: {
        showOriginalTitle: false,
        showOriginalDescription: false
      }
    };
  },

  created() {
    // Créer les fonctions debounced avec cancel
    this.debouncedSaveDescription = debounce(this.saveDescription, 2000);
    this.debouncedSaveTitle = debounce(this.saveTitle, 2000);
  },

  computed: {
    // Détermine si le titre a été modifié par rapport à l'original
    hasTitleModification() {
      return this.episode && this.episode.titre_corrige &&
             this.episode.titre_corrige.trim() !== '' &&
             this.episode.titre_corrige !== this.episode.titre;
    },

    // Détermine si la description a été modifiée par rapport à l'original
    hasDescriptionModification() {
      return this.episode && this.episode.description_corrigee &&
             this.episode.description_corrigee.trim() !== '' &&
             this.episode.description_corrigee !== this.episode.description;
    }
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

          // Restaurer l'état des toggles pour la persistance de session (Issue #23)
          this.showOriginalTitle = this.sessionToggleState.showOriginalTitle;
          this.showOriginalDescription = this.sessionToggleState.showOriginalDescription;
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

    /**
     * Toggle l'affichage du titre original (Issue #23)
     */
    toggleOriginalTitle() {
      this.showOriginalTitle = !this.showOriginalTitle;
      // Sauvegarder l'état pour la persistance de session
      this.sessionToggleState.showOriginalTitle = this.showOriginalTitle;
    },

    /**
     * Toggle l'affichage de la description originale (Issue #23)
     */
    toggleOriginalDescription() {
      this.showOriginalDescription = !this.showOriginalDescription;
      // Sauvegarder l'état pour la persistance de session
      this.sessionToggleState.showOriginalDescription = this.showOriginalDescription;
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

/* Styles pour la nouvelle interface compacte (Issue #23) */
.title-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.modification-indicator {
  background: none;
  border: 1px solid #007bff;
  border-radius: 4px;
  padding: 2px 6px;
  cursor: pointer;
  font-size: 0.8rem;
  transition: all 0.2s ease;
}

.modification-indicator:hover {
  background-color: #007bff;
  color: white;
  transform: scale(1.05);
}

.original-content {
  margin-bottom: 1rem;
  padding: 0.75rem;
  background-color: #f8f9fa;
  border-radius: 4px;
  border-left: 3px solid #007bff;
}

.form-label-small {
  font-size: 0.85rem;
  color: #666;
  font-weight: 500;
  margin-bottom: 0.25rem;
  display: block;
}

.original-text {
  color: #333;
  font-style: italic;
  line-height: 1.4;
}

.original-textarea {
  background-color: #fff !important;
  border-color: #ddd;
  font-size: 0.9rem;
}

/* En-tête compact */
h2 {
  font-size: 1.3rem;
  color: #333;
  margin-bottom: 1.5rem;
  font-weight: 600;
}
</style>
