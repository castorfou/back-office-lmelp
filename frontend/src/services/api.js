/**
 * Service API pour communiquer avec le backend FastAPI
 */

import axios from 'axios';

// Configuration axios
const api = axios.create({
  baseURL: '/api',
  timeout: 30000, // 30 secondes pour permettre le fallback parsing
  headers: {
    'Content-Type': 'application/json',
  },
});

// Intercepteur pour gérer les erreurs globalement
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('Erreur API:', error);

    if (error.code === 'ECONNABORTED') {
      throw new Error('Timeout: La requête a pris trop de temps');
    }

    if (error.response) {
      // Erreur avec réponse du serveur
      throw new Error(error.response.data.detail || 'Erreur serveur');
    } else if (error.request) {
      // Erreur réseau
      throw new Error('Erreur réseau: Impossible de contacter le serveur');
    } else {
      // Autre erreur
      throw new Error('Erreur inconnue');
    }
  }
);

/**
 * Service pour la gestion des statistiques
 */
export const statisticsService = {
  /**
   * Récupère les statistiques générales de l'application
   * @returns {Promise<Object>} Statistiques
   */
  async getStatistics() {
    const response = await api.get('/statistics');
    return response.data;
  },
};

/**
 * Service pour la gestion des livres/auteurs extraits des avis critiques
 */
export const livresAuteursService = {
  /**
   * Récupère la liste des livres/auteurs extraits des avis critiques
   * @param {Object} params - Paramètres optionnels (limit, episode_oid, etc.)
   * @returns {Promise<Array>} Liste des livres avec métadonnées
   */
  async getLivresAuteurs(params = {}) {
    const response = await api.get('/livres-auteurs', { params });
    return response.data;
  },

  /**
   * Récupère les épisodes qui ont des avis critiques
   * @returns {Promise<Array>} Liste des épisodes avec avis critiques
   */
  async getEpisodesWithReviews() {
    const response = await api.get('/episodes-with-reviews');
    return response.data;
  },

  // ========== NOUVEAUX ENDPOINTS POUR ISSUE #66 ==========

  /**
   * Récupère les statistiques pour la gestion des collections
   * @returns {Promise<Object>} Statistiques des collections
   */
  async getCollectionsStatistics() {
    const response = await api.get('/livres-auteurs/statistics');
    return response.data;
  },

  /**
   * Lance le traitement automatique des livres verified
   * @returns {Promise<Object>} Résultats du traitement automatique
   */
  async autoProcessVerifiedBooks() {
    const response = await api.post('/livres-auteurs/auto-process-verified');
    return response.data;
  },

  /**
   * Récupère les livres par statut de validation
   * @param {string} status - Statut de validation (verified, suggested, not_found)
   * @returns {Promise<Array>} Liste des livres avec le statut demandé
   */
  async getBooksByValidationStatus(status) {
    const response = await api.get(`/livres-auteurs/books/${status}`);
    return response.data;
  },

  /**
   * Valide manuellement une suggestion d'auteur/livre
   * @param {Object} bookData - Données du livre avec corrections utilisateur
   * @returns {Promise<Object>} Résultat de la validation
   */
  async validateSuggestion(bookData) {
    const response = await api.post('/livres-auteurs/validate-suggestion', bookData);
    return response.data;
  },


  /**
   * Récupère tous les auteurs de la collection
   * @returns {Promise<Array>} Liste de tous les auteurs
   */
  async getAllAuthors() {
    const response = await api.get('/authors');
    return response.data;
  },

  /**
   * Récupère tous les livres de la collection
   * @returns {Promise<Array>} Liste de tous les livres
   */
  async getAllBooks() {
    const response = await api.get('/books');
    return response.data;
  },

  /**
   * Envoie les résultats de validation biblio du frontend au backend
   * @param {Object} validationData - Données de validation des livres
   * @returns {Promise<Object>} Résultat de l'opération
   */
  async setValidationResults(validationData) {
    const response = await api.post('/set-validation-results', validationData);
    return response.data;
  },

  /**
   * Supprime toutes les entrées de cache pour un épisode donné
   * @param {string} episodeOid - ID de l'épisode dont on veut supprimer le cache
   * @returns {Promise<Object>} Nombre de documents supprimés
   */
  async deleteCacheByEpisode(episodeOid) {
    const response = await api.delete(`/livres-auteurs/cache/episode/${episodeOid}`);
    return response.data;
  },
};

/**
 * Service pour la gestion des épisodes
 */
export const episodeService = {
  /**
   * Récupère tous les épisodes
   * @returns {Promise<Array>} Liste des épisodes
   */
  async getAllEpisodes() {
    const response = await api.get('/episodes');
    return response.data;
  },

  /**
   * Récupère un épisode par son ID
   * @param {string} episodeId - ID de l'épisode
   * @returns {Promise<Object>} Détails de l'épisode
   */
  async getEpisodeById(episodeId) {
    const response = await api.get(`/episodes/${episodeId}`);
    return response.data;
  },

  /**
   * Met à jour la description corrigée d'un épisode
   * @param {string} episodeId - ID de l'épisode
   * @param {string} descriptionCorrigee - Nouvelle description
   * @returns {Promise<Object>} Résultat de la mise à jour
   */
  async updateEpisodeDescription(episodeId, descriptionCorrigee) {
    const response = await api.put(`/episodes/${episodeId}`, descriptionCorrigee, {
      headers: {
        'Content-Type': 'text/plain',
      },
    });
    return response.data;
  },

  /**
   * Met à jour le titre corrigé d'un épisode
   * @param {string} episodeId - ID de l'épisode
   * @param {string} titreCorrige - Nouveau titre
   * @returns {Promise<Object>} Résultat de la mise à jour
   */
  async updateEpisodeTitle(episodeId, titreCorrige) {
    const response = await api.put(`/episodes/${episodeId}/title`, titreCorrige, {
      headers: {
        'Content-Type': 'text/plain',
      },
    });
    return response.data;
  },
};

/**
 * Service pour la recherche textuelle multi-entités
 */
export const searchService = {
  /**
   * Effectue une recherche textuelle dans toutes les entités
   * @param {string} query - Terme de recherche (minimum 3 caractères)
   * @param {number} limit - Nombre maximum de résultats par catégorie (optionnel)
   * @returns {Promise<Object>} Résultats de recherche structurés par catégorie
   */
  async search(query, limit = 10) {
    if (!query || query.trim().length < 3) {
      throw new Error('La recherche nécessite au moins 3 caractères');
    }

    const params = { q: query.trim() };
    if (limit && limit !== 10) {
      params.limit = limit;
    }

    const response = await api.get('/search', { params });
    return response.data;
  },
};

/**
 * Service pour la vérification Babelio
 */
export const babelioService = {
  /**
   * Vérifie un auteur via l'API Babelio
   * @param {string} name - Nom de l'auteur
   * @returns {Promise<Object>} Résultat de vérification Babelio
   */
  async verifyAuthor(name) {
    const response = await api.post('/verify-babelio', {
      type: 'author',
      name: name
    });
    return response.data;
  },

  /**
   * Vérifie un livre via l'API Babelio
   * @param {string} title - Titre du livre
   * @param {string} author - Auteur du livre (optionnel)
   * @returns {Promise<Object>} Résultat de vérification Babelio
   */
  async verifyBook(title, author = null) {
    const response = await api.post('/verify-babelio', {
      type: 'book',
      title: title,
      author: author
    });
    return response.data;
  },

  /**
   * Vérifie un éditeur via l'API Babelio
   * @param {string} name - Nom de l'éditeur
   * @returns {Promise<Object>} Résultat de vérification Babelio
   */
  async verifyPublisher(name) {
    const response = await api.post('/verify-babelio', {
      type: 'publisher',
      name: name
    });
    return response.data;
  },
};

/**
 * Service de recherche fuzzy pour les épisodes
 */
export const fuzzySearchService = {
  /**
   * Recherche fuzzy dans un épisode spécifique
   * @param {string} episodeId - ID de l'épisode
   * @param {Object} searchTerms - Termes de recherche {author, title}
   * @returns {Promise<Object>} Résultat de recherche fuzzy
   */
  async searchEpisode(episodeId, searchTerms) {
    if (!episodeId || !searchTerms) {
      return {
        found_suggestions: false,
        titleMatches: [],
        authorMatches: []
      };
    }

    try {
      const response = await api.post('/fuzzy-search-episode', {
        episode_id: episodeId,
        query_title: searchTerms.title || '',
        query_author: searchTerms.author || ''
      });

      // Transform API response to expected format
      const data = response.data;
      return {
        found_suggestions: data.found_suggestions || false,
        titleMatches: data.title_matches || [],
        authorMatches: data.author_matches || []
      };
    } catch (error) {
      console.warn('Fuzzy search failed:', error.message);
      return {
        found_suggestions: false,
        titleMatches: [],
        authorMatches: []
      };
    }
  }
};

export default api;
