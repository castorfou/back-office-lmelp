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


export default api;
