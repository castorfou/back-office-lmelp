<template>
  <div class="auteur-detail-page">
    <!-- Navigation -->
    <Navigation pageTitle="Détail de l'auteur" />

    <!-- État de chargement -->
    <div v-if="loading" class="loading-state" data-test="loading">
      <div class="loading-spinner"></div>
      <span>Chargement des informations de l'auteur...</span>
    </div>

    <!-- Message d'erreur -->
    <div v-else-if="error" class="error-state" data-test="error">
      <div class="error-icon">⚠️</div>
      <span>{{ error }}</span>
      <button @click="$router.back()" class="btn-secondary">
        Retour
      </button>
    </div>

    <!-- Contenu de l'auteur -->
    <div v-else-if="auteur" class="auteur-content">
      <!-- En-tête auteur -->
      <div class="auteur-header">
        <h1 class="auteur-name">{{ auteur.nom }}</h1>
        <!-- Lien Babelio (Issue #124) -->
        <div v-if="auteur.url_babelio" class="auteur-babelio">
          <BabelioLink :url="auteur.url_babelio" label="Fiche Babelio" />
        </div>
        <div class="auteur-stats">
          <span class="stat-badge">
            {{ auteur.nombre_oeuvres }} œuvre{{ auteur.nombre_oeuvres > 1 ? 's' : '' }}
          </span>
        </div>
      </div>

      <!-- Liste des livres -->
      <section class="livres-section">
        <h2>Œuvres de {{ auteur.nom }}</h2>

        <!-- Message si aucun livre -->
        <div v-if="auteur.livres.length === 0" class="empty-state">
          <p>Aucun livre trouvé pour cet auteur</p>
        </div>

        <!-- Liste des livres -->
        <div v-else class="livres-list">
          <div
            v-for="livre in auteur.livres"
            :key="livre.livre_id"
            class="livre-card"
            data-test="book-item"
          >
            <div class="livre-info">
              <router-link
                :to="`/livre/${livre.livre_id}`"
                class="livre-title-link"
                data-test="book-link"
              >
                <h3 class="livre-title">{{ livre.titre }}</h3>
              </router-link>
              <p class="livre-editor">{{ livre.editeur }}</p>
            </div>
            <div class="livre-arrow">→</div>
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
import BabelioLink from '../components/BabelioLink.vue';

export default {
  name: 'AuteurDetail',
  components: {
    Navigation,
    BabelioLink
  },
  data() {
    return {
      auteur: null,
      loading: false,
      error: null
    };
  },
  async mounted() {
    await this.loadAuteur();
  },
  methods: {
    async loadAuteur() {
      this.loading = true;
      this.error = null;

      try {
        const auteurId = this.$route.params.id;
        // Issue #103: Utiliser une URL relative pour bénéficier du proxy Vite
        const response = await axios.get(`/api/auteur/${auteurId}`);
        this.auteur = response.data;
      } catch (err) {
        console.error('Erreur lors du chargement de l\'auteur:', err);
        if (err.response?.status === 404) {
          this.error = 'Auteur non trouvé';
        } else if (err.response?.data?.detail) {
          this.error = err.response.data.detail;
        } else {
          this.error = 'Une erreur est survenue lors du chargement de l\'auteur';
        }
      } finally {
        this.loading = false;
      }
    }
  }
};
</script>

<style scoped>
.auteur-detail-page {
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

/* Contenu auteur */
.auteur-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}

.auteur-header {
  background: white;
  border-radius: 8px;
  padding: 2rem;
  margin-bottom: 2rem;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.auteur-name {
  font-size: 2rem;
  color: #2c3e50;
  margin: 0 0 1rem 0;
}

.auteur-stats {
  display: flex;
  gap: 1rem;
}

.stat-badge {
  background: #e3f2fd;
  color: #1976d2;
  padding: 0.5rem 1rem;
  border-radius: 20px;
  font-weight: 500;
  font-size: 0.9rem;
}

/* Section livres */
.livres-section {
  background: white;
  border-radius: 8px;
  padding: 2rem;
  margin-bottom: 2rem;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.livres-section h2 {
  font-size: 1.5rem;
  color: #2c3e50;
  margin: 0 0 1.5rem 0;
}

.empty-state {
  text-align: center;
  padding: 3rem;
  color: #757575;
}

.livres-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.livre-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  background: #fafafa;
  transition: all 0.2s ease;
}

.livre-card:hover {
  background: #f5f5f5;
  border-color: #1976d2;
  transform: translateX(4px);
}

.livre-info {
  flex: 1;
}

.livre-title-link {
  text-decoration: none;
  color: inherit;
}

.livre-title {
  font-size: 1.1rem;
  color: #2c3e50;
  margin: 0 0 0.5rem 0;
  transition: color 0.2s ease;
}

.livre-title-link:hover .livre-title {
  color: #1976d2;
}

.livre-editor {
  color: #757575;
  font-size: 0.9rem;
  margin: 0;
}

.livre-arrow {
  color: #1976d2;
  font-size: 1.5rem;
  opacity: 0.5;
  transition: opacity 0.2s ease;
}

.livre-card:hover .livre-arrow {
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
