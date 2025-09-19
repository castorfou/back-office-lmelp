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

    <!-- Author verified but book not found -->
    <div v-else-if="validationResult && validationResult.status === 'author_verified_book_not_found'"
         class="validation-status partial"
         data-testid="validation-partial">
      <span class="status-icon">✅❓</span>
      <div class="status-content">
        <span class="status-text">Auteur validé</span>
        <div class="partial-details">Livre non trouvé</div>
      </div>
    </div>

    <!-- Invalid suggestion -->
    <div v-else-if="validationResult && validationResult.status === 'suggestion_invalid'"
         class="validation-status invalid"
         data-testid="validation-invalid">
      <span class="status-icon">⚠️</span>
      <div class="status-content">
        <span class="status-text">Suggestion invalide</span>
        <div class="invalid-details">{{ validationResult.reason }}</div>
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

        // Étape 1: Valider l'auteur
        const authorResult = await this.verifyAuthor();

        if (!authorResult) {
          this.handleVerificationResult('author', { status: 'not_found' });
          return;
        }

        // Étape 2: Validation cohérence auteur-livre
        if (this.title && this.title.trim()) {
          await this.validateAuthorBookCoherence(authorResult);
        } else {
          // Si pas de titre, on garde juste la validation auteur
          this.handleVerificationResult('author', authorResult);
        }

      } catch (error) {
        this.handleVerificationError(error);
      } finally {
        this.isLoading = false;
        this.lastValidationTime = Date.now();
      }
    },

    async validateAuthorBookCoherence(authorResult) {
      // Nouvelle approche : chercher le livre indépendamment pour comparer les suggestions

      // Rate limiting pour la deuxième requête
      await this.waitForRateLimit();

      // Étape 1 : Vérifier le livre SANS auteur pour voir quel auteur Babelio suggère
      const bookAloneResult = await this.verifyBookAlone(this.title.trim());

      // Analyser la cohérence entre suggestion d'auteur et auteur du livre trouvé
      if (authorResult.status === 'verified') {
        // Auteur exact trouvé - logique simple sans validation complexe
        if (bookAloneResult && (bookAloneResult.status === 'verified' || bookAloneResult.status === 'corrected')) {
          // Livre trouvé avec auteur exact, couple validé
          this.handleVerificationResult('book', {
            status: bookAloneResult.status === 'verified' ? 'verified' : 'corrected',
            original_author: authorResult.original,
            original_title: this.title,
            babelio_suggestion_author: authorResult.babelio_suggestion,
            babelio_suggestion_title: bookAloneResult.babelio_suggestion_title || this.title,
            confidence_score: Math.min(authorResult.confidence_score || 1.0, bookAloneResult.confidence_score || 1.0)
          });
        } else {
          // Auteur exact mais livre non trouvé
          this.handleVerificationResult('mixed', {
            status: 'author_verified_book_not_found',
            original_author: authorResult.original,
            original_title: this.title,
            babelio_suggestion_author: authorResult.babelio_suggestion,
            confidence_score: authorResult.confidence_score || 1.0,
            reason: 'Livre non trouvé'
          });
        }
      } else if (authorResult.status === 'corrected') {
        // Auteur avec suggestion - vérifier la cohérence
        const suggestedAuthor = authorResult.babelio_suggestion;

        if (bookAloneResult && (bookAloneResult.status === 'verified' || bookAloneResult.status === 'corrected')) {
          // Livre trouvé - extraire l'auteur du livre
          const bookAuthor = this.extractAuthorFromBookResult(bookAloneResult);

          if (bookAuthor) {
            // Rate limiting pour la troisième requête
            await this.waitForRateLimit();

            // ÉTAPE 3A : D'abord vérifier si l'auteur suggéré + livre fonctionne
            const suggestedAuthorBookResult = await this.verifyBook(this.title.trim(), suggestedAuthor);

            // Rate limiting pour la quatrième requête
            await this.waitForRateLimit();

            // ÉTAPE 3B : Vérifier aussi le vrai auteur du livre + le titre pour comparaison
            const correctAuthorBookResult = await this.verifyBook(this.title.trim(), bookAuthor);

            // Vérifier si l'auteur suggéré + livre fonctionne
            const isSuggestedAuthorMatch = suggestedAuthorBookResult &&
              (suggestedAuthorBookResult.status === 'verified' || suggestedAuthorBookResult.status === 'corrected');

            // Vérifier si le vrai auteur + livre fonctionne
            const isCorrectAuthorMatch = correctAuthorBookResult &&
              (correctAuthorBookResult.status === 'verified' || correctAuthorBookResult.status === 'corrected');

            if (isSuggestedAuthorMatch) {
              // L'auteur suggéré + livre fonctionne ! Utiliser cette suggestion
              this.handleVerificationResult('book', {
                status: 'corrected',
                original_author: authorResult.original,
                original_title: this.title,
                babelio_suggestion_author: suggestedAuthor,
                babelio_suggestion_title: suggestedAuthorBookResult.babelio_suggestion_title || this.title,
                confidence_score: Math.min(authorResult.confidence_score || 0.8, suggestedAuthorBookResult.confidence_score || 0.8)
              });
            } else if (isCorrectAuthorMatch) {
              // Seul l'auteur du livre trouvé + livre fonctionne
              // La suggestion d'auteur était incorrecte
              this.handleVerificationResult('book', {
                status: 'corrected',
                original_author: authorResult.original,
                original_title: this.title,
                babelio_suggestion_author: bookAuthor, // Utiliser l'auteur réel du livre
                babelio_suggestion_title: correctAuthorBookResult.babelio_suggestion_title || bookAloneResult.babelio_suggestion_title || this.title,
                confidence_score: Math.max(bookAloneResult.confidence_score || 0.8, correctAuthorBookResult.confidence_score || 0.8)
              });
            } else {
              // Aucun des deux ne fonctionne parfaitement, garder la suggestion d'auteur
              this.handleVerificationResult('author', {
                status: 'corrected',
                original: authorResult.original,
                babelio_suggestion: authorResult.babelio_suggestion,
                confidence_score: authorResult.confidence_score
              });
            }
          } else {
            // Pas d'auteur extrait, garder la suggestion d'auteur
            this.handleVerificationResult('author', {
              status: 'corrected',
              original: authorResult.original,
              babelio_suggestion: authorResult.babelio_suggestion,
              confidence_score: authorResult.confidence_score
            });
          }
        } else {
          // Livre non trouvé - impossible de valider la suggestion d'auteur
          // Dans ce cas, on considère que c'est "non trouvé" plutôt qu'une suggestion
          this.handleVerificationResult('book', {
            status: 'not_found',
            original_author: authorResult.original,
            original_title: this.title,
            confidence_score: 0,
            reason: 'Impossible de valider la suggestion auteur sans le livre correspondant'
          });
        }
      } else {
        // Auteur non trouvé
        this.handleVerificationResult('author', authorResult);
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

      // Pour les résultats combinés auteur-livre
      if (this.validationResult.original_author && this.validationResult.original_title) {
        return `${this.validationResult.original_author} - ${this.validationResult.original_title}`;
      }

      return this.validationResult.original ||
             this.validationResult.original_title ||
             this.validationResult.original_author ||
             '';
    },

    getSuggestedText() {
      if (!this.validationResult) return '';

      // Pour les résultats combinés auteur-livre
      if (this.validationResult.babelio_suggestion_author && this.validationResult.babelio_suggestion_title) {
        const suggestedAuthor = this.validationResult.babelio_suggestion_author;
        const suggestedTitle = this.validationResult.babelio_suggestion_title;

        // Montrer seulement les changements
        const originalAuthor = this.validationResult.original_author || this.author;
        const originalTitle = this.validationResult.original_title || this.title;

        if (suggestedAuthor !== originalAuthor && suggestedTitle !== originalTitle) {
          return `${suggestedAuthor} - ${suggestedTitle}`;
        } else if (suggestedAuthor !== originalAuthor) {
          return suggestedAuthor;
        } else if (suggestedTitle !== originalTitle) {
          return suggestedTitle;
        }
      }

      return this.validationResult.babelio_suggestion ||
             this.validationResult.babelio_suggestion_title ||
             this.validationResult.babelio_suggestion_author ||
             '';
    },

    async verifyBookAlone(title) {
      if (!title || !title.trim()) {
        return null;
      }

      // Chercher le livre SANS auteur pour voir quel auteur Babelio suggère
      return await babelioService.verifyBook(title.trim(), null);
    },

    extractAuthorFromBookResult(bookResult) {
      if (!bookResult || !bookResult.babelio_data) {
        return null;
      }

      const data = bookResult.babelio_data;

      // Construire le nom complet de l'auteur
      if (data.prenoms && data.nom) {
        return `${data.prenoms} ${data.nom}`;
      } else if (data.nom) {
        return data.nom;
      } else if (data.prenoms) {
        return data.prenoms;
      }

      return null;
    },

    authorsMatch(author1, author2) {
      if (!author1 || !author2) {
        return false;
      }

      // Normaliser les noms pour la comparaison
      const normalize = (name) => {
        return name.toLowerCase()
          .replace(/[^\w\s]/g, '') // Supprimer la ponctuation
          .replace(/\s+/g, ' ')    // Normaliser les espaces
          .trim();
      };

      const normalized1 = normalize(author1);
      const normalized2 = normalize(author2);

      // Vérifier la correspondance exacte ou partielle significative
      return normalized1 === normalized2 ||
             (normalized1.length > 5 && normalized2.includes(normalized1)) ||
             (normalized2.length > 5 && normalized1.includes(normalized2));
    },

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

/* Partial validation state */
.validation-status.partial {
  background-color: #fff8e1;
  color: #f57f17;
}

.partial-details {
  font-size: 0.8rem;
  color: #e65100;
  margin-top: 0.25rem;
}

/* Invalid suggestion state */
.validation-status.invalid {
  background-color: #ffebee;
  color: #c62828;
}

.invalid-details {
  font-size: 0.8rem;
  color: #b71c1c;
  margin-top: 0.25rem;
  line-height: 1.2;
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
