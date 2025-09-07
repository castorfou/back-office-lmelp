/**
 * Service API pour communiquer avec le backend FastAPI
 */

import axios from 'axios';

// Configuration axios
const api = axios.create({
  baseURL: '/api',
  timeout: 10000,
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
 * Service pour la gestion des livres/auteurs extraits via LLM
 */
export const livresAuteursService = {
  /**
   * Récupère la liste des livres/auteurs extraits des avis critiques
   * @param {Object} params - Paramètres optionnels (limit, etc.)
   * @returns {Promise<Array>} Liste des livres avec métadonnées
   */
  async getLivresAuteurs(params = {}) {
    const response = await api.get('/livres-auteurs', { params });
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
 * Service pour la gestion des livres et auteurs extraits via LLM
 */
export const livresAuteursService = {
  /**
   * Récupère la liste des livres/auteurs extraits depuis les avis critiques
   * @param {Object} params - Paramètres de requête (ex: limit)
   * @returns {Promise<Array>} Liste des livres avec métadonnées
   */
  async getLivresAuteurs(params = {}) {
    const response = await api.get('/livres-auteurs', { params });
    return response.data;
  },
};

export default api;
