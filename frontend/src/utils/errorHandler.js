/**
 * Utilitaires pour la gestion centralisée des erreurs
 */

/**
 * Classe pour gérer les erreurs de l'application
 */
export class ErrorHandler {
  /**
   * Traite une erreur et retourne un message utilisateur approprié
   * @param {Error} error - L'erreur à traiter
   * @returns {string} Message d'erreur formaté pour l'utilisateur
   */
  static handleError(error) {
    console.error('Erreur capturée:', error);

    // Types d'erreurs spécifiques
    if (error.message.includes('Timeout')) {
      return 'La requête a pris trop de temps. Veuillez réessayer.';
    }

    if (error.message.includes('réseau')) {
      return 'Problème de connexion. Vérifiez votre connexion internet.';
    }

    if (error.message.includes('non trouvé')) {
      return 'L\'élément demandé n\'a pas été trouvé.';
    }

    if (error.message.includes('serveur')) {
      return 'Erreur du serveur. Veuillez réessayer plus tard.';
    }

    // Message par défaut
    return error.message || 'Une erreur inattendue s\'est produite.';
  }

  /**
   * Fonction de retry avec délai exponentiel
   * @param {Function} fn - Fonction à réessayer
   * @param {number} maxRetries - Nombre maximum de tentatives
   * @param {number} baseDelay - Délai de base en ms
   * @returns {Promise} Résultat de la fonction ou erreur finale
   */
  static async retryWithBackoff(fn, maxRetries = 3, baseDelay = 1000) {
    let lastError;

    for (let attempt = 0; attempt < maxRetries; attempt++) {
      try {
        return await fn();
      } catch (error) {
        lastError = error;

        if (attempt === maxRetries - 1) {
          throw error;
        }

        // Délai exponentiel: 1s, 2s, 4s...
        const delay = baseDelay * Math.pow(2, attempt);
        await new Promise(resolve => setTimeout(resolve, delay));
      }
    }

    throw lastError;
  }
}

/**
 * Mixin Vue pour la gestion d'erreurs dans les composants
 */
export const errorMixin = {
  data() {
    return {
      error: null,
      loading: false,
    };
  },

  methods: {
    /**
     * Exécute une fonction async avec gestion d'erreur
     * @param {Function} asyncFn - Fonction async à exécuter
     */
    async handleAsync(asyncFn) {
      this.error = null;
      this.loading = true;

      try {
        return await asyncFn();
      } catch (error) {
        this.error = ErrorHandler.handleError(error);
        throw error;
      } finally {
        this.loading = false;
      }
    },

    /**
     * Nettoie l'état d'erreur
     */
    clearError() {
      this.error = null;
    },
  },
};
