<template>
  <div class="recommendations-page">
    <Navigation pageTitle="Mes Recommandations" />

    <!-- Bandeau d'avertissement expérimental -->
    <div class="warning-banner">
      <span class="warning-icon">⚠️</span>
      Recommandations <strong>expérimentales</strong> — Collaborative filtering SVD,
      Hit Rate @20 ~1.4% (baseline 1.2%). Résultats indicatifs uniquement.
    </div>

    <!-- Loading state -->
    <div v-if="loading" class="loading-state" data-test="loading">
      <div class="loading-spinner"></div>
      <span>Calcul des recommandations en cours (~10 secondes)…</span>
    </div>

    <!-- Error state -->
    <div v-else-if="error" class="error-state" data-test="error">
      <div class="error-icon">⚠️</div>
      <span>{{ error }}</span>
      <button @click="loadRecommendations" class="btn-secondary">Réessayer</button>
    </div>

    <!-- Empty state -->
    <div v-else-if="recommendations.length === 0" class="empty-state" data-test="empty">
      <div class="empty-icon">📚</div>
      <p>Aucune recommandation disponible.</p>
      <p class="empty-hint">
        Assurez-vous que Calibre est disponible et que vous avez noté des livres.
      </p>
    </div>

    <!-- Contenu principal -->
    <div v-else class="page-content">
      <div class="page-header">
        <h1>Mes Recommandations</h1>
        <span class="total-count">{{ recommendations.length }} livre(s)</span>
      </div>

      <div class="table-container">
        <table class="recommendations-table" data-test="recommendations-table">
          <thead>
            <tr>
              <th class="col-rank">#</th>
              <th class="col-title">Titre</th>
              <th class="col-author">Auteur</th>
              <th class="col-score">Score</th>
              <th class="col-svd">SVD</th>
              <th class="col-masque">Masque</th>
              <th class="col-count">N critiques</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="item in recommendations"
              :key="item.livre_id"
              class="recommendation-row"
              data-test="recommendation-row"
            >
              <td class="col-rank">{{ item.rank }}</td>
              <td class="col-title">
                <router-link
                  :to="`/livre/${item.livre_id}`"
                  class="livre-link"
                  data-test="livre-link"
                >
                  {{ item.titre || '—' }}
                </router-link>
              </td>
              <td class="col-author">
                <router-link
                  v-if="item.auteur_id"
                  :to="`/auteur/${item.auteur_id}`"
                  class="auteur-link"
                  data-test="auteur-link"
                >
                  {{ item.auteur_nom || '—' }}
                </router-link>
                <span v-else>{{ item.auteur_nom || '—' }}</span>
              </td>
              <td class="col-score">
                <span class="score-badge" :class="scoreBadgeClass(item.score_hybride)">
                  {{ item.score_hybride.toFixed(2) }}
                </span>
              </td>
              <td class="col-svd">{{ item.svd_predict.toFixed(2) }}</td>
              <td class="col-masque">{{ item.masque_mean.toFixed(1) }}</td>
              <td class="col-count">{{ item.masque_count }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios';
import Navigation from '../components/Navigation.vue';

const RECOMMENDATIONS_TIMEOUT = 60000; // 60 secondes pour calcul SVD

export default {
  name: 'Recommendations',
  components: { Navigation },

  data() {
    return {
      recommendations: [],
      loading: true,
      error: null,
    };
  },

  async mounted() {
    await this.loadRecommendations();
  },

  methods: {
    async loadRecommendations() {
      this.loading = true;
      this.error = null;
      try {
        const response = await axios.get('/api/recommendations/me', {
          params: { top_n: 20 },
          timeout: RECOMMENDATIONS_TIMEOUT,
        });
        this.recommendations = response.data;
      } catch (err) {
        this.error = err.response?.data?.detail || err.message || 'Erreur inconnue';
      } finally {
        this.loading = false;
      }
    },

    scoreBadgeClass(score) {
      if (score >= 8) return 'score-high';
      if (score >= 6) return 'score-medium';
      return 'score-low';
    },
  },
};
</script>

<style scoped>
.recommendations-page {
  min-height: 100vh;
  background-color: #f8f9fa;
}

.warning-banner {
  background: #fff3cd;
  color: #856404;
  padding: 0.75rem 1.5rem;
  border-bottom: 1px solid #ffc107;
  font-size: 0.9rem;
}

.warning-icon {
  margin-right: 0.5rem;
}

.page-content {
  padding: 1.5rem;
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  align-items: baseline;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.page-header h1 {
  font-size: 1.6rem;
  color: #333;
  margin: 0;
}

.total-count {
  color: #888;
  font-size: 0.9rem;
}

/* Loading / Error / Empty */
.loading-state,
.error-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 3rem;
  gap: 1rem;
  color: #666;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #e9ecef;
  border-top-color: #667eea;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.error-icon,
.empty-icon {
  font-size: 2rem;
}

.empty-hint {
  color: #999;
  font-size: 0.9rem;
}

.btn-secondary {
  padding: 0.6rem 1.2rem;
  background: #6c757d;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
}

.btn-secondary:hover {
  background: #5a6268;
}

/* Table */
.table-container {
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  overflow: hidden;
}

.recommendations-table {
  width: 100%;
  border-collapse: collapse;
}

.recommendations-table th {
  padding: 0.8rem 1rem;
  text-align: left;
  font-weight: 600;
  color: #555;
  font-size: 0.85rem;
  text-transform: uppercase;
  border-bottom: 2px solid #e0e0e0;
  background: #f8f9fa;
}

.recommendations-table td {
  padding: 0.7rem 1rem;
  border-bottom: 1px solid #f0f0f0;
  vertical-align: middle;
}

.recommendation-row:last-child td {
  border-bottom: none;
}

.recommendation-row:hover {
  background: #f8f9ff;
}

/* Colonnes */
.col-rank {
  width: 3rem;
  text-align: center;
  color: #999;
  font-weight: 600;
}

.col-title {
  min-width: 200px;
}

.col-author {
  min-width: 150px;
}

.col-score,
.col-svd,
.col-masque,
.col-count {
  text-align: center;
  width: 6rem;
}

/* Liens */
.livre-link,
.auteur-link {
  color: #667eea;
  text-decoration: none;
  font-weight: 500;
}

.livre-link:hover,
.auteur-link:hover {
  text-decoration: underline;
}

/* Badges score */
.score-badge {
  display: inline-block;
  padding: 0.2rem 0.5rem;
  border-radius: 12px;
  font-weight: 600;
  font-size: 0.9rem;
}

.score-high {
  background: #d4edda;
  color: #155724;
}

.score-medium {
  background: #fff3cd;
  color: #856404;
}

.score-low {
  background: #f8f9fa;
  color: #666;
}
</style>
