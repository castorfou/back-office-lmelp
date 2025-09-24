<template>
  <div class="dashboard">
    <!-- Bandeau d'en-tête -->
    <header class="page-header">
      <h1>Back-office LMELP</h1>
      <p class="subtitle">
        Gestion et correction des épisodes du Masque et la Plume
      </p>
    </header>

    <!-- Zone de recherche globale -->
    <section class="search-section">
      <TextSearchEngine :limit="10" />
    </section>

    <main class="dashboard-content">
      <!-- Section Statistiques -->
      <section class="statistics-section">
        <h2>Informations générales</h2>
        <div class="stats-grid">
          <div class="stat-card">
            <div class="stat-value">{{ statistics.totalEpisodes !== null ? statistics.totalEpisodes : '...' }}</div>
            <div class="stat-label">Épisodes au total</div>
          </div>
          <div class="stat-card">
            <div class="stat-value">{{ statistics.episodesWithCorrectedTitles !== null ? statistics.episodesWithCorrectedTitles : '...' }}</div>
            <div class="stat-label">Titres corrigés</div>
          </div>
          <div class="stat-card">
            <div class="stat-value">{{ statistics.episodesWithCorrectedDescriptions !== null ? statistics.episodesWithCorrectedDescriptions : '...' }}</div>
            <div class="stat-label">Descriptions corrigées</div>
          </div>
          <div class="stat-card">
            <div class="stat-value">{{ statistics.criticalReviews !== null ? statistics.criticalReviews : '...' }}</div>
            <div class="stat-label">Avis critiques extraits</div>
          </div>
          <div class="stat-card">
            <div class="stat-value">{{ formattedLastUpdate || '...' }}</div>
            <div class="stat-label">Dernière mise à jour</div>
          </div>
          <div class="stat-card">
            <div class="stat-value">{{ (collectionsStatistics && collectionsStatistics.couples_en_base !== null) ? collectionsStatistics.couples_en_base : '...' }}</div>
            <div class="stat-label">Livres en base</div>
          </div>
          <div class="stat-card">
            <div class="stat-value">{{ (collectionsStatistics && collectionsStatistics.couples_verified_pas_en_base !== null) ? collectionsStatistics.couples_verified_pas_en_base : '...' }}</div>
            <div class="stat-label">Livres vérifiés</div>
          </div>
          <div class="stat-card">
            <div class="stat-value">{{ (collectionsStatistics && collectionsStatistics.couples_suggested_pas_en_base !== null) ? collectionsStatistics.couples_suggested_pas_en_base : '...' }}</div>
            <div class="stat-label">Livres suggérés</div>
          </div>
          <div class="stat-card">
            <div class="stat-value">{{ (collectionsStatistics && collectionsStatistics.couples_not_found_pas_en_base !== null) ? collectionsStatistics.couples_not_found_pas_en_base : '...' }}</div>
            <div class="stat-label">Livres non trouvés</div>
          </div>
        </div>
      </section>

      <!-- Section Fonctions -->
      <section class="functions-section">
        <h2>Fonctions disponibles</h2>
        <div class="functions-grid">
          <div
            class="function-card clickable"
            data-testid="function-episode-edit"
            @click="navigateToEpisodes"
          >
            <div class="function-icon">📝</div>
            <h3>Episode - Modification Titre/Description</h3>
            <p>Sélectionnez un épisode pour modifier son titre et sa description</p>
            <div class="function-arrow">→</div>
          </div>

          <div
            class="function-card clickable"
            data-testid="function-livres-auteurs"
            @click="navigateToLivresAuteurs"
          >
            <div class="function-icon">📚</div>
            <h3>Livres et Auteurs</h3>
            <p>Extraction des informations bibliographiques depuis les avis critiques</p>
            <div class="function-arrow">→</div>
          </div>

          <div
            class="function-card clickable"
            data-testid="function-babelio-test"
            @click="navigateToBabelioTest"
          >
            <div class="function-icon">🔍</div>
            <h3>Test Babelio</h3>
            <p>Vérification orthographique des auteurs, livres et éditeurs via Babelio</p>
            <div class="function-arrow">→</div>
          </div>

          <!-- Placeholder pour futures fonctions -->
          <div class="function-card coming-soon">
            <div class="function-icon">🔎</div>
            <h3>Recherche avancée</h3>
            <p>Recherche avec filtres et critères spécifiques</p>
            <div class="coming-soon-label">Bientôt disponible</div>
          </div>

          <div class="function-card coming-soon">
            <div class="function-icon">📊</div>
            <h3>Rapports et analyses</h3>
            <p>Générer des rapports sur l'état des corrections</p>
            <div class="coming-soon-label">Bientôt disponible</div>
          </div>

          <div class="function-card coming-soon">
            <div class="function-icon">⚙️</div>
            <h3>Configuration</h3>
            <p>Paramètres et configuration du système</p>
            <div class="coming-soon-label">Bientôt disponible</div>
          </div>
        </div>
      </section>
    </main>
  </div>
</template>

<script>
import { statisticsService, livresAuteursService } from '../services/api.js';
import TextSearchEngine from '../components/TextSearchEngine.vue';

export default {
  name: 'Dashboard',

  components: {
    TextSearchEngine,
  },

  data() {
    return {
      statistics: {
        totalEpisodes: null,
        episodesWithCorrectedTitles: null,
        episodesWithCorrectedDescriptions: null,
        criticalReviews: null,
        lastUpdateDate: null
      },
      collectionsStatistics: {
        episodes_non_traites: null,
        couples_en_base: null,
        couples_verified_pas_en_base: null,
        couples_suggested_pas_en_base: null,
        couples_not_found_pas_en_base: null
      },
      loading: true,
      error: null
    };
  },

  computed: {
    formattedLastUpdate() {
      if (!this.statistics.lastUpdateDate) {
        return null;
      }

      try {
        const date = new Date(this.statistics.lastUpdateDate);
        return date.toLocaleDateString('fr-FR', {
          day: '2-digit',
          month: '2-digit',
          year: '2-digit'
        });
      } catch (error) {
        console.error('Erreur de formatage de date:', error);
        return '--';
      }
    }
  },

  async mounted() {
    await this.loadStatistics();
    await this.loadCollectionsStatistics();
  },

  methods: {
    async loadStatistics() {
      try {
        this.loading = true;
        this.error = null;
        const stats = await statisticsService.getStatistics();
        this.statistics = stats;
      } catch (error) {
        console.error('Erreur lors du chargement des statistiques:', error);
        this.error = error.message;
        // Garder les valeurs '...' en cas d'erreur
        this.statistics = {
          totalEpisodes: '--',
          episodesWithCorrectedTitles: '--',
          episodesWithCorrectedDescriptions: '--',
          criticalReviews: '--',
          lastUpdateDate: null
        };
      } finally {
        this.loading = false;
      }
    },

    async loadCollectionsStatistics() {
      try {
        const stats = await livresAuteursService.getCollectionsStatistics();
        this.collectionsStatistics = stats;
      } catch (error) {
        console.error('Erreur lors du chargement des statistiques des collections:', error);
        // Garder les valeurs null en cas d'erreur pour afficher '...'
        this.collectionsStatistics = {
          episodes_non_traites: '--',
          couples_en_base: '--',
          couples_verified_pas_en_base: '--',
          couples_suggested_pas_en_base: '--',
          couples_not_found_pas_en_base: '--'
        };
      }
    },

    navigateToEpisodes() {
      this.$router.push('/episodes');
    },

    navigateToLivresAuteurs() {
      this.$router.push('/livres-auteurs');
    },

    navigateToBabelioTest() {
      this.$router.push('/babelio-test');
    }
  }
};
</script>

<style scoped>
.dashboard {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.page-header {
  text-align: center;
  margin-bottom: 3rem;
  padding: 3rem 2rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-radius: 12px;
  margin: -2rem -2rem 3rem -2rem;
}

.page-header h1 {
  font-size: 3rem;
  margin-bottom: 0.5rem;
  font-weight: 700;
}

.subtitle {
  font-size: 1.2rem;
  opacity: 0.9;
  font-weight: 300;
}

.dashboard-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 3rem;
}

.statistics-section h2,
.functions-section h2 {
  font-size: 1.5rem;
  margin-bottom: 1.5rem;
  color: #333;
  text-align: center;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  margin-bottom: 2rem;
  max-width: 100%;
}

/* Limitation à 4 cartes maximum par ligne pour éviter le débordement */
@media (min-width: 1200px) {
  .stats-grid {
    grid-template-columns: repeat(4, 1fr);
    max-width: 1000px;
    margin: 0 auto 2rem auto;
  }
}

.stat-card {
  background: white;
  padding: 1.2rem;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  text-align: center;
  min-width: 0; /* Permet au contenu de rétrécir */
}

.stat-value {
  font-size: 2.5rem;
  font-weight: bold;
  color: #667eea;
  margin-bottom: 0.5rem;
}

.stat-label {
  font-size: 0.85rem;
  color: #666;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  line-height: 1.2;
  word-wrap: break-word;
  overflow-wrap: break-word;
}

.functions-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1.5rem;
}

.function-card {
  background: white;
  padding: 2rem;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  text-align: center;
  position: relative;
  transition: all 0.3s ease;
}

.function-card.clickable {
  cursor: pointer;
  border: 2px solid transparent;
}

.function-card.clickable:hover {
  transform: translateY(-4px);
  box-shadow: 0 4px 16px rgba(0,0,0,0.15);
  border-color: #667eea;
}

.function-card.coming-soon {
  opacity: 0.7;
  background: #f8f9fa;
}

.function-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.function-card h3 {
  font-size: 1.2rem;
  margin-bottom: 1rem;
  color: #333;
}

.function-card p {
  font-size: 0.9rem;
  color: #666;
  line-height: 1.5;
  margin-bottom: 1rem;
}

.function-arrow {
  font-size: 1.5rem;
  color: #667eea;
  font-weight: bold;
}

.coming-soon-label {
  background: #ffc107;
  color: #333;
  padding: 0.25rem 0.75rem;
  border-radius: 20px;
  font-size: 0.8rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  display: inline-block;
}

.search-section {
  margin-bottom: 2rem;
  padding: 0 2rem;
}

@media (max-width: 768px) {
  .search-section {
    padding: 0 1rem;
  }
}


/* Responsive Design */
/* Règle spécifique pour gérer 5 cartes de statistiques */
@media (max-width: 1024px) and (min-width: 769px) {
  .stats-grid {
    grid-template-columns: repeat(3, 1fr);
    gap: 0.8rem;
  }

  .stat-card {
    padding: 1rem;
  }

  .stat-label {
    font-size: 0.8rem;
  }
}

@media (max-width: 768px) {
  .page-header {
    margin: -2rem -1rem 2rem -1rem;
    padding: 2rem 1rem;
  }

  .page-header h1 {
    font-size: 2.2rem;
  }

  .subtitle {
    font-size: 1rem;
  }

  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 0.75rem;
  }

  .stat-card {
    padding: 1rem;
  }

  .stat-value {
    font-size: 1.8rem;
  }

  .functions-grid {
    grid-template-columns: 1fr;
    gap: 1rem;
  }

  .function-card {
    padding: 1.5rem;
  }

  .dashboard-content {
    gap: 2rem;
  }
}

@media (max-width: 480px) {
  .page-header h1 {
    font-size: 1.8rem;
  }

  .stats-grid {
    grid-template-columns: 1fr;
  }

  .stat-value {
    font-size: 1.5rem;
  }
}
</style>
