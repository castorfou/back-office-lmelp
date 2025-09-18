<template>
  <div class="babelio-validation-cell">
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
      <span class="status-text">Non trouvé</span>
    </div>

    <!-- Default/Initial state -->
    <div v-else class="validation-status initial">
      <span class="status-icon">⏳</span>
      <span class="status-text">En attente...</span>
    </div>
  </div>
</template>

<script>
import { babelioService } from '../services/api.js';

export default {
  name: 'BabelioValidationCell',

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
    }
  },

  data() {
    return {
      isLoading: true, // Start with loading state
      hasError: false,
      errorMessage: '',
      validationResult: null,
      lastValidationTime: 0
    };
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

        // Try to verify author first
        const authorResult = await this.verifyAuthor();

        if (authorResult) {
          this.handleVerificationResult('author', authorResult);
        }

      } catch (error) {
        this.handleVerificationError(error);
      } finally {
        this.isLoading = false;
        this.lastValidationTime = Date.now();
      }
    },

    async verifyAuthor() {
      if (!this.author || !this.author.trim()) {
        return null;
      }

      return await babelioService.verifyAuthor(this.author.trim());
    },

    async verifyBook() {
      if (!this.title || !this.title.trim()) {
        return null;
      }

      return await babelioService.verifyBook(
        this.title.trim(),
        this.author ? this.author.trim() : null
      );
    },

    async verifyPublisher() {
      if (!this.publisher || !this.publisher.trim()) {
        return null;
      }

      return await babelioService.verifyPublisher(this.publisher.trim());
    },

    handleVerificationResult(type, result) {
      this.validationResult = {
        type: type,
        ...result
      };
      this.hasError = false;
    },

    handleVerificationError(error) {
      console.error('Erreur de vérification Babelio:', error);
      this.hasError = true;
      this.errorMessage = error.message || 'Erreur de vérification';
      this.validationResult = null;
    },

    async waitForRateLimit() {
      const timeSinceLastCall = Date.now() - this.lastValidationTime;
      const minInterval = 1000; // 1 second

      if (timeSinceLastCall < minInterval) {
        const waitTime = minInterval - timeSinceLastCall;
        await new Promise(resolve => setTimeout(resolve, waitTime));
      }
    },

    getOriginalText() {
      if (!this.validationResult) return '';

      return this.validationResult.original ||
             this.validationResult.original_title ||
             this.validationResult.original_author ||
             '';
    },

    getSuggestedText() {
      if (!this.validationResult) return '';

      return this.validationResult.babelio_suggestion ||
             this.validationResult.babelio_suggestion_title ||
             this.validationResult.babelio_suggestion_author ||
             '';
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

.suggestion-details {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.8rem;
  margin-top: 0.25rem;
}

.original {
  color: #666;
  text-decoration: line-through;
}

.arrow {
  color: #999;
  font-weight: bold;
}

.suggested {
  color: #f57c00;
  font-weight: 600;
}

/* Not found state */
.validation-status.not-found {
  background-color: #fafafa;
  color: #616161;
}

/* Error state */
.validation-status.error {
  background-color: #ffebee;
  color: #c62828;
}

.retry-button {
  background: none;
  border: 1px solid #c62828;
  color: #c62828;
  border-radius: 3px;
  padding: 0.125rem 0.25rem;
  font-size: 0.8rem;
  cursor: pointer;
  margin-left: 0.25rem;
  transition: all 0.2s ease;
}

.retry-button:hover {
  background-color: #c62828;
  color: white;
}

/* Disabled state */
.validation-status.disabled {
  background-color: #f5f5f5;
  color: #9e9e9e;
}

/* Initial state */
.validation-status.initial {
  background-color: #f9f9f9;
  color: #757575;
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .suggestion-details {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.125rem;
  }

  .arrow {
    display: none;
  }
}
</style>
