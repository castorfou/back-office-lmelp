<template>
  <div class="biblio-validation-cell">
    <!-- Disabled state (missing required props) -->
    <div v-if="!hasValidProps"
         class="validation-status disabled"
         data-testid="validation-disabled">
      <span class="status-icon">—</span>
      <span class="status-text">N/A</span>
    </div>

    <!-- Loading state -->
    <div v-else-if="isLoading" class="validation-status loading" data-testid="validation-loading">
      <span class="status-icon">⏳</span>
      <span class="status-text">Vérification...</span>
    </div>

    <!-- Error state -->
    <div v-else-if="hasError" class="validation-status error" data-testid="validation-error">
      <span class="status-icon">⚠️</span>
      <div class="status-content">
        <span class="status-text">Erreur</span>
        <button
          @click="startValidation"
          class="retry-button"
          data-testid="retry-button"
          title="Réessayer la vérification"
        >
          ↻
        </button>
      </div>
    </div>

    <!-- Success - Perfect match -->
    <div v-else-if="validationResult && validationResult.status === 'verified'"
         class="validation-status success"
         data-testid="validation-success">
      <span class="status-icon">✅</span>
      <span class="status-text">Validé</span>
    </div>

    <!-- Success - With suggestion -->
    <div v-else-if="validationResult && validationResult.status === 'corrected'"
         class="validation-status suggestion"
         data-testid="validation-suggestion">
      <span class="status-icon">🔄</span>
      <div class="status-content">
        <span class="status-text">Suggestion</span>
        <div class="suggestion-details">
          <div class="original">{{ getOriginalText() }}</div>
          <div class="arrow">→</div>
          <div class="suggested">{{ getSuggestedText() }}</div>
        </div>
      </div>
    </div>

    <!-- Not found -->
    <div v-else-if="validationResult && validationResult.status === 'not_found'"
         class="validation-status not-found"
         data-testid="validation-not-found">
      <span class="status-icon">❓</span>
      <div class="status-content">
        <span class="status-text">Non trouvé</span>
      </div>
    </div>

    <!-- Fallback for unknown states -->
    <div v-else class="validation-status disabled" data-testid="validation-unknown">
      <span class="status-icon">—</span>
      <span class="status-text">Inconnu</span>
    </div>
  </div>
</template>

<script>
import { babelioService, fuzzySearchService } from '../services/api.js';
import { BiblioValidationService } from '../services/BiblioValidationService.js';

export default {
  name: 'BiblioValidationCell',

  props: {
    author: {
      type: String,
      required: true
    },
    title: {
      type: String,
      required: true
    },
    publisher: {
      type: String,
      default: ''
    },
    episodeId: {
      type: String,
      default: null
    }
  },

  data() {
    return {
      isLoading: true, // Start with loading state
      hasError: false,
      errorMessage: '',
      validationResult: null,
      lastValidationTime: 0,
      biblioValidationService: null
    };
  },

  created() {
    // Initialize BiblioValidationService with required dependencies
    this.biblioValidationService = new BiblioValidationService({
      fuzzySearchService,
      babelioService,
      localAuthorService: {
        findAuthor: () => Promise.resolve(null)
      }
    });
  },

  computed: {
    hasValidProps() {
      return this.author && this.author.trim().length > 0;
    }
  },

  mounted() {
    if (this.hasValidProps) {
      // Start validation immediately
      this.startValidation();
    } else {
      // If no valid props, stop loading
      this.isLoading = false;
    }
  },

  methods: {
    async startValidation() {
      if (!this.hasValidProps) {
        this.isLoading = false;
        return;
      }

      this.isLoading = true;
      this.hasError = false;
      this.errorMessage = '';
      this.validationResult = null;

      try {
        // Respect rate limiting (1 req/sec)
        await this.waitForRateLimit();

        // Use BiblioValidationService for intelligent validation
        const result = await this.biblioValidationService.validateBiblio(
          this.author.trim(),
          this.title?.trim() || '',
          this.publisher?.trim() || '',
          this.episodeId
        );

        // Convert service result to component format
        this.convertServiceResult(result);

      } catch (error) {
        this.handleVerificationError(error);
      } finally {
        this.isLoading = false;
        this.lastValidationTime = Date.now();
      }
    },

    convertServiceResult(serviceResult) {
      // Simplification : stocker directement le résultat du service avec mapping de statut
      this.validationResult = {
        status: this.mapServiceStatus(serviceResult.status),
        original: serviceResult.data.original,
        suggested: serviceResult.data.suggested,
        corrections: serviceResult.data.corrections,
        confidence_score: serviceResult.data.confidence_score,
        source: serviceResult.data.source,
        reason: serviceResult.data.reason,
        attempts: serviceResult.data.attempts,
        error: serviceResult.data.error
      };
    },

    mapServiceStatus(serviceStatus) {
      // Mapper les statuts du service vers les statuts du composant
      switch (serviceStatus) {
        case 'verified': return 'verified';
        case 'suggestion': return 'corrected';
        case 'not_found': return 'not_found';
        case 'error': return 'error';
        default: return 'error';
      }
    },

    handleVerificationError(error) {
      console.error('Erreur de vérification Babelio:', error);
      this.hasError = true;
      this.errorMessage = error.message || 'Erreur lors de la vérification Babelio';
    },

    async waitForRateLimit() {
      const minInterval = 1000; // 1 second minimum between requests
      const timeSinceLastRequest = Date.now() - this.lastValidationTime;

      if (timeSinceLastRequest < minInterval) {
        const waitTime = minInterval - timeSinceLastRequest;
        await new Promise(resolve => setTimeout(resolve, waitTime));
      }
    },

    getOriginalText() {
      if (!this.validationResult?.original) return '';

      const parts = [];
      if (this.validationResult.original.author) {
        parts.push(this.validationResult.original.author);
      }
      if (this.validationResult.original.title) {
        parts.push(this.validationResult.original.title);
      }

      return parts.join(' - ');
    },

    getSuggestedText() {
      if (!this.validationResult?.suggested) return '';

      const parts = [];
      if (this.validationResult.suggested.author) {
        parts.push(this.validationResult.suggested.author);
      }
      if (this.validationResult.suggested.title) {
        parts.push(this.validationResult.suggested.title);
      }

      return parts.join(' - ');
    }
  }
};
</script>

<style scoped>
.babelio-validation-cell {
  min-width: 120px;
}

.validation-status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.9rem;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  min-height: 2rem;
}

.status-icon {
  font-size: 1rem;
  flex-shrink: 0;
}

.status-text {
  font-weight: 500;
  white-space: nowrap;
}

.status-content {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  flex: 1;
}

/* Loading state */
.validation-status.loading {
  background-color: #e3f2fd;
  color: #1976d2;
}

.loading .status-icon {
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* Success state */
.validation-status.success {
  background-color: #e8f5e8;
  color: #2e7d32;
}

/* Suggestion state */
.validation-status.suggestion {
  background-color: #fff3e0;
  color: #f57c00;
}

/* Error state */
.validation-status.error {
  background-color: #ffebee;
  color: #c62828;
}

/* Not found state */
.validation-status.not-found {
  background-color: #f3e5f5;
  color: #7b1fa2;
}

/* Disabled state */
.validation-status.disabled {
  background-color: #f5f5f5;
  color: #757575;
}

/* Suggestion details */
.suggestion-details {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.8rem;
  margin-top: 0.25rem;
}

.suggestion-details .original {
  color: #666;
  text-decoration: line-through;
}

.suggestion-details .arrow {
  color: #999;
  font-weight: bold;
}

.suggestion-details .suggested {
  color: #2e7d32;
  font-weight: 600;
}

/* Retry button */
.retry-button {
  background: none;
  border: none;
  color: inherit;
  cursor: pointer;
  font-size: 1rem;
  padding: 0.125rem;
  border-radius: 2px;
  margin-left: 0.25rem;
}

.retry-button:hover {
  background-color: rgba(255, 255, 255, 0.2);
}

.retry-button:active {
  transform: scale(0.95);
}
</style>
