<template>
  <div class="livre-detail-page">
    <!-- Navigation -->
    <Navigation pageTitle="Détail du livre" />

    <!-- État de chargement -->
    <div v-if="loading" class="loading-state" data-test="loading">
      <div class="loading-spinner"></div>
      <span>Chargement des informations du livre...</span>
    </div>

    <!-- Message d'erreur -->
    <div v-else-if="error" class="error-state" data-test="error">
      <div class="error-icon">⚠️</div>
      <span>{{ error }}</span>
      <button @click="$router.back()" class="btn-secondary">
        Retour
      </button>
    </div>

    <!-- Contenu du livre -->
    <div v-else-if="livre" class="livre-content">
      <!-- En-tête livre -->
      <div class="livre-header">
        <h1 class="livre-title">{{ livre.titre }}</h1>
        <div class="livre-meta">
          <div class="livre-author">
            Auteur :
            <router-link
              :to="`/auteur/${livre.auteur_id}`"
              class="author-link"
              data-test="auteur-link"
            >
              {{ livre.auteur_nom }}
            </router-link>
          </div>
          <div class="livre-publisher">Éditeur : {{ livre.editeur }}</div>
        </div>
        <div class="livre-stats">
          <span class="stat-badge">
            {{ livre.nombre_episodes }} épisode{{ livre.nombre_episodes > 1 ? 's' : '' }}
          </span>
        </div>
      </div>

      <!-- Liste des épisodes -->
      <section class="episodes-section">
        <h2>Épisodes présentant "{{ livre.titre }}"</h2>

        <!-- Message si aucun épisode -->
        <div v-if="livre.episodes.length === 0" class="empty-state">
          <p>Aucun épisode trouvé pour ce livre</p>
        </div>

        <!-- Liste des épisodes -->
        <div v-else class="episodes-list">
          <div
            v-for="episode in livre.episodes"
            :key="episode.episode_id"
            class="episode-card"
            data-test="episode-item"
          >
            <!-- Icône programme/coup de coeur -->
            <div class="episode-status" v-if="episode.programme !== null && episode.programme !== undefined">
              <!-- Programme: blue target icon -->
              <span v-if="episode.programme" class="status-icon programme" title="Au programme" role="img" aria-label="Programme">
                <svg width="18" height="18" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none">
                  <circle cx="12" cy="12" r="8" fill="#0B5FFF" />
                  <circle cx="12" cy="12" r="4" fill="#FFFFFF" />
                </svg>
              </span>
              <!-- Coup de coeur: red heart -->
              <span v-else class="status-icon coeur" title="Coup de coeur" role="img" aria-label="Coup de coeur">
                <svg width="18" height="18" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none">
                  <path d="M12 21s-7.5-4.5-9.3-7.1C-0.4 9.8 3 5 7.4 7.1 9.1 8 10 9.6 12 11.3c2-1.7 2.9-3.3 4.6-4.2C21 5 24.4 9.8 21.3 13.9 19.5 16.5 12 21 12 21z" fill="#D93025" />
                </svg>
              </span>
            </div>
            <div class="episode-info">
              <!-- Issue #96: Lien vers la validation biblio de cet épisode -->
              <router-link
                :to="`/livres-auteurs?episode=${episode.episode_id}`"
                class="episode-title-link"
                data-test="episode-link"
              >
                <h3 class="episode-title">{{ episode.titre }}</h3>
              </router-link>
              <p class="episode-date">{{ formatDate(episode.date) }}</p>
            </div>
            <div class="episode-arrow">→</div>
          </div>
        </div>
      </section>

      <!-- Bouton retour -->
      <div class="actions">
        <button @click="$router.back()" class="btn-secondary">
          ← Retour
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios';
import Navigation from '../components/Navigation.vue';

export default {
  name: 'LivreDetail',
  components: {
    Navigation
  },
  data() {
    return {
      livre: null,
      loading: false,
      error: null
    };
  },
  async mounted() {
    await this.loadLivre();
  },
  methods: {
    async loadLivre() {
      this.loading = true;
      this.error = null;

      try {
        const livreId = this.$route.params.id;
        // Issue #103: Utiliser une URL relative pour bénéficier du proxy Vite
        const response = await axios.get(`/api/livre/${livreId}`);
        this.livre = response.data;
      } catch (err) {
        console.error('Erreur lors du chargement du livre:', err);
        if (err.response?.status === 404) {
          this.error = 'Livre non trouvé';
        } else if (err.response?.data?.detail) {
          this.error = err.response.data.detail;
        } else {
          this.error = 'Une erreur est survenue lors du chargement du livre';
        }
      } finally {
        this.loading = false;
      }
    },
    formatDate(dateString) {
      // Format date from YYYY-MM-DD to "DD MMMM YYYY"
      if (!dateString) return '';

      const date = new Date(dateString);
      const options = { year: 'numeric', month: 'long', day: 'numeric' };
      return date.toLocaleDateString('fr-FR', options);
    }
  }
};
</script>

<style scoped>
.livre-detail-page {
  min-height: 100vh;
  background-color: #f5f5f5;
}

/* États loading et error */
.loading-state,
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 400px;
  gap: 1rem;
  padding: 2rem;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #2c3e50;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.error-icon {
  font-size: 3rem;
}

.error-state span {
  color: #d32f2f;
  font-size: 1.1rem;
}

/* Contenu livre */
.livre-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}

.livre-header {
  background: white;
  border-radius: 8px;
  padding: 2rem;
  margin-bottom: 2rem;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.livre-title {
  font-size: 2rem;
  color: #2c3e50;
  margin: 0 0 1rem 0;
}

.livre-meta {
  margin: 1rem 0;
  font-size: 1.1rem;
  color: #555;
}

.livre-author {
  margin-bottom: 0.5rem;
}

.author-link {
  color: #1976d2;
  text-decoration: none;
  font-weight: 500;
  transition: color 0.2s ease;
}

.author-link:hover {
  color: #1565c0;
  text-decoration: underline;
}

.livre-publisher {
  color: #757575;
}

.livre-stats {
  display: flex;
  gap: 1rem;
  margin-top: 1rem;
}

.stat-badge {
  background: #e3f2fd;
  color: #1976d2;
  padding: 0.5rem 1rem;
  border-radius: 20px;
  font-weight: 500;
  font-size: 0.9rem;
}

/* Section épisodes */
.episodes-section {
  background: white;
  border-radius: 8px;
  padding: 2rem;
  margin-bottom: 2rem;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.episodes-section h2 {
  font-size: 1.5rem;
  color: #2c3e50;
  margin: 0 0 1.5rem 0;
}

.empty-state {
  text-align: center;
  padding: 3rem;
  color: #757575;
}

.episodes-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.episode-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 1rem;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  background: #fafafa;
  transition: all 0.2s ease;
}

.episode-card:hover {
  background: #f5f5f5;
  border-color: #1976d2;
  transform: translateX(4px);
}

.episode-status {
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 24px;
}

.status-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.episode-info {
  flex: 1;
}

.episode-title-link {
  text-decoration: none;
  color: inherit;
}

.episode-title {
  font-size: 1.1rem;
  color: #2c3e50;
  margin: 0 0 0.5rem 0;
  transition: color 0.2s ease;
}

.episode-title-link:hover .episode-title {
  color: #1976d2;
}

.episode-date {
  color: #757575;
  font-size: 0.9rem;
  margin: 0;
}

.episode-arrow {
  color: #1976d2;
  font-size: 1.5rem;
  opacity: 0.5;
  transition: opacity 0.2s ease;
}

.episode-card:hover .episode-arrow {
  opacity: 1;
}

/* Actions */
.actions {
  display: flex;
  gap: 1rem;
  padding: 1rem 0;
}

.btn-secondary {
  padding: 0.75rem 1.5rem;
  background: #e0e0e0;
  border: none;
  border-radius: 6px;
  color: #2c3e50;
  font-size: 1rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-secondary:hover {
  background: #bdbdbd;
}
</style>
