<template>
  <div class="episode-selector card">
    <!-- État de chargement -->
    <div v-if="loading" class="loading">
      Chargement des épisodes...
    </div>

    <!-- Affichage d'erreur -->
    <div v-if="error" class="alert alert-error">
      {{ error }}
      <button @click="loadEpisodes" class="btn btn-primary" style="margin-left: 1rem;">
        Réessayer
      </button>
    </div>

    <!-- Sélecteur d'épisode -->
    <div v-if="!loading && !error" class="form-group">
      <label for="episode-select" class="form-label">
        Choisir un épisode ({{ episodes.length }} disponibles)
      </label>
      <select
        id="episode-select"
        v-model="selectedEpisodeId"
        @change="onEpisodeChange"
        class="form-control"
      >
        <option value="">-- Sélectionner un épisode --</option>
        <option
          v-for="episode in episodes"
          :key="episode.id"
          :value="episode.id"
        >
          {{ formatEpisodeOption(episode) }}
        </option>
      </select>
    </div>
  </div>
</template>

<script>
import { episodeService } from '../services/api.js';
import { errorMixin } from '../utils/errorHandler.js';

export default {
  name: 'EpisodeSelector',

  mixins: [errorMixin],

  emits: ['episode-selected'],

  data() {
    return {
      episodes: [],
      selectedEpisodeId: '',
    };
  },

  async mounted() {
    await this.loadEpisodes();
  },

  methods: {
    /**
     * Charge la liste des épisodes depuis l'API
     */
    async loadEpisodes() {
      await this.handleAsync(async () => {
        this.episodes = await episodeService.getAllEpisodes();
      });
    },

    /**
     * Recharge la liste des épisodes (utilisé pour la mise à jour dynamique)
     * Méthode publique appelable depuis un composant parent
     */
    async refreshEpisodesList() {
      await this.loadEpisodes();
    },

    /**
     * Gère le changement de sélection d'épisode
     */
    async onEpisodeChange() {
      if (!this.selectedEpisodeId) {
        this.$emit('episode-selected', null);
        return;
      }

      await this.handleAsync(async () => {
        const episode = await episodeService.getEpisodeById(this.selectedEpisodeId);
        this.$emit('episode-selected', episode);
      });
    },

    /**
     * Formate l'option d'épisode pour l'affichage
     * Nouveau format: "24 août 2025 - titre corrigé"
     * @param {Object} episode - L'épisode à formater
     * @returns {string} Texte formaté
     */
    formatEpisodeOption(episode) {
      const date = episode.date ? this.formatDateLitteraire(episode.date) : 'Date inconnue';
      const titre = episode.titre; // Nouvelle logique: titre contient déjà la version corrigée

      return `${date} - ${titre}`;
    },

    /**
     * Formate une date au format littéraire français
     * @param {string} dateStr - Date au format ISO
     * @returns {string} Date formatée (ex: "24 août 2025")
     */
    formatDateLitteraire(dateStr) {
      const date = new Date(dateStr);
      const options = {
        day: 'numeric',
        month: 'long',
        year: 'numeric'
      };
      return date.toLocaleDateString('fr-FR', options);
    },
  },
};
</script>

<style scoped>
.episode-selector {
  margin-bottom: 2rem;
}

.episode-selector h2 {
  margin-bottom: 1rem;
  color: #333;
}

.form-control {
  font-family: monospace;
  font-size: 0.9rem;
}

.loading {
  padding: 2rem;
  text-align: center;
  color: #666;
}
</style>
