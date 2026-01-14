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
          <a
            :href="lmelpFrontOfficeUrl"
            class="stat-card clickable-stat"
            target="_blank"
            rel="noopener noreferrer"
            :title="tooltips.lastUpdate"
          >
            <div class="stat-value">{{ formattedLastUpdate || '...' }}</div>
            <div class="stat-label">Dernière mise à jour</div>
          </a>
          <div
            class="stat-card clickable-stat"
            @click="navigateToGenerationAvis"
            :title="tooltips.episodesSansAvis"
          >
            <div class="stat-value">{{ (collectionsStatistics && collectionsStatistics.episodes_without_avis_critiques != null) ? collectionsStatistics.episodes_without_avis_critiques : '...' }}</div>
            <div class="stat-label">Épisodes sans avis critiques</div>
          </div>
          <div
            class="stat-card clickable-stat"
            @click="navigateToLivresAuteurs"
            :title="tooltips.avisSansAnalyse"
          >
            <div class="stat-value">{{ (collectionsStatistics && collectionsStatistics.avis_critiques_without_analysis != null) ? collectionsStatistics.avis_critiques_without_analysis : '...' }}</div>
            <div class="stat-label">Avis critiques sans analyse</div>
          </div>
          <div
            class="stat-card clickable-stat"
            @click="navigateToLivresAuteurs"
            :title="tooltips.livresSuggeres"
          >
            <div class="stat-value">{{ (collectionsStatistics && collectionsStatistics.couples_suggested_pas_en_base !== null) ? collectionsStatistics.couples_suggested_pas_en_base : '...' }}</div>
            <div class="stat-label">Livres suggérés</div>
          </div>
          <div
            class="stat-card clickable-stat"
            @click="navigateToLivresAuteurs"
            :title="tooltips.livresNonTrouves"
          >
            <div class="stat-value">{{ (collectionsStatistics && collectionsStatistics.couples_not_found_pas_en_base !== null) ? collectionsStatistics.couples_not_found_pas_en_base : '...' }}</div>
            <div class="stat-label">Livres non trouvés</div>
          </div>
          <div
            class="stat-card clickable-stat"
            @click="navigateToBabelioMigration"
            :title="tooltips.livresSansLienBabelio"
          >
            <div class="stat-value">{{ (collectionsStatistics && collectionsStatistics.books_without_url_babelio != null) ? collectionsStatistics.books_without_url_babelio : '...' }}</div>
            <div class="stat-label">Livres sans lien Babelio</div>
          </div>
          <div
            class="stat-card clickable-stat"
            @click="navigateToBabelioMigration"
            :title="tooltips.auteursSansLienBabelio"
          >
            <div class="stat-value">{{ (collectionsStatistics && collectionsStatistics.authors_without_url_babelio != null) ? collectionsStatistics.authors_without_url_babelio : '...' }}</div>
            <div class="stat-label">Auteurs sans lien Babelio</div>
          </div>
          <div
            class="stat-card clickable-stat"
            @click="navigateToIdentificationCritiques"
            :title="tooltips.critiquesManquants"
          >
            <div class="stat-value">{{ critiquesManquantsCount !== null ? critiquesManquantsCount : '...' }}</div>
            <div class="stat-label">Critiques manquants</div>
          </div>
          <div
            class="stat-card clickable-stat"
            @click="navigateToEmissions"
            :title="tooltips.episodesSansEmission"
          >
            <div class="stat-value">{{ episodesSansEmissionCount !== null ? episodesSansEmissionCount : '...' }}</div>
            <div class="stat-label">Épisodes sans émission</div>
          </div>
          <div
            class="stat-card clickable-stat"
            @click="navigateToDuplicates"
            :title="tooltips.doublons"
          >
            <div class="stat-value">{{ totalDuplicatesCount !== null ? totalDuplicatesCount : '...' }}</div>
            <div class="stat-label">Doublons</div>
          </div>
        </div>
      </section>

      <!-- Section Fonctions -->
      <section class="functions-section">
        <h2>Fonctions disponibles</h2>
        <div class="functions-grid">
          <div
            class="function-card clickable"
            data-testid="function-emissions"
            @click="navigateToEmissions"
          >
            <div class="function-icon">📺</div>
            <h3>Émissions</h3>
            <p>Affichage structuré des émissions avec livres discutés et critiques présents</p>
            <div class="function-arrow">→</div>
          </div>

          <div
            class="function-card clickable"
            data-testid="function-generation-avis"
            @click="navigateToGenerationAvis"
          >
            <div class="function-icon">🤖</div>
            <h3>Génération Avis Critiques (LLM)</h3>
            <p>Génération automatique 2 phases depuis transcriptions</p>
            <div class="function-arrow">→</div>
          </div>

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
            data-testid="function-identification-critiques"
            @click="navigateToIdentificationCritiques"
          >
            <div class="function-icon">👥</div>
            <h3>Identification des Critiques</h3>
            <p>Gestion et identification automatique des critiques littéraires</p>
            <div class="function-arrow">→</div>
          </div>

          <div
            class="function-card clickable"
            data-testid="function-babelio-test"
            @click="navigateToBabelioTest"
          >
            <div class="function-icon">
              <img :src="babelioIcon" alt="Babelio" class="function-icon-img" />
            </div>
            <h3>Recherche Babelio</h3>
            <p>Vérification orthographique des auteurs, livres et éditeurs via Babelio</p>
            <div class="function-arrow">→</div>
          </div>

          <div
            class="function-card clickable"
            data-testid="function-babelio-migration"
            @click="navigateToBabelioMigration"
          >
            <div class="function-icon">
              <img :src="babelioIconLiaison" alt="BabelioLiaison" class="function-icon-img" />
            </div>
            <h3>Liaison Babelio</h3>
            <p>Lier Auteurs et Livres aux pages Babelio</p>
            <div class="function-arrow">→</div>
          </div>

          <div
            class="function-card clickable"
            data-testid="function-duplicates"
            @click="navigateToDuplicates"
          >
            <div class="function-icon">🔗</div>
            <h3>Gestion des Doublons</h3>
            <p>Détection et fusion des livres en doublon (même URL Babelio)</p>
            <div class="function-arrow">→</div>
          </div>

          <div
            class="function-card clickable"
            data-testid="function-advanced-search"
            @click="navigateToAdvancedSearch"
          >
            <div class="function-icon">🔎</div>
            <h3>Recherche avancée</h3>
            <p>Recherche avec filtres et critères spécifiques</p>
            <div class="function-arrow">→</div>
          </div>

          <div
            class="function-card clickable"
            data-testid="function-masquer-episodes"
            @click="navigateToMasquerEpisodes"
          >
            <div class="function-icon">🙈</div>
            <h3>Masquer les Épisodes</h3>
            <p>Gérer la visibilité des épisodes (masquer/afficher)</p>
            <div class="function-arrow">→</div>
          </div>

          <div
            class="function-card clickable"
            data-testid="function-calibre-library"
            @click="navigateToCalibre"
          >
            <div class="function-icon">
              <img :src="calibreIcon" alt="Calibre" class="function-icon-img" />
            </div>
            <h3>Bibliothèque Calibre</h3>
            <p>Consultation et gestion de la bibliothèque personnelle</p>
            <div class="function-arrow">→</div>
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
import axios from 'axios';
import { statisticsService, livresAuteursService } from '../services/api.js';
import TextSearchEngine from '../components/TextSearchEngine.vue';
import babelioSymbol from '../assets/babelio-symbol.svg';
import babelioSymbolLiaison from '../assets/babelio-symbol-liaison.svg';
import calibreIcon from '../assets/calibre_logo.png';

export default {
  name: 'Dashboard',

  components: {
    TextSearchEngine,
  },

  data() {
    return {
      statistics: {
        totalEpisodes: null,
        maskedEpisodes: null,
        episodesWithCorrectedTitles: null,
        episodesWithCorrectedDescriptions: null,
        criticalReviews: null,
        lastUpdateDate: null
      },
      collectionsStatistics: {
        episodes_non_traites: null,
        couples_en_base: null,
        avis_critiques_analyses: null,
        couples_suggested_pas_en_base: null,
        couples_not_found_pas_en_base: null,
        episodes_without_avis_critiques: null,
        avis_critiques_without_analysis: null,
        books_without_url_babelio: null,
        authors_without_url_babelio: null,
        last_episode_date: null
      },
      tooltips: {
        lastUpdate: `Date du dernier épisode en base\nCollection: episodes\nRequête: episodes.find().sort({diffusion: -1}).limit(1)`,
        episodesSansAvis: `Formule: COUNT(episodes non masqués) - COUNT(avis_critiques non masqués)\nCollections: episodes, avis_critiques\nFiltres: masked ≠ true`,
        avisSansAnalyse: `Formule: COUNT(avis non masqués) - COUNT(livresauteurs_cache non masqués)\nCollections: avis_critiques, livresauteurs_cache, episodes\nFiltres: masked ≠ true`,
        livresSuggeres: `Livres avec statut "suggested" dans le cache\nCollection: livresauteurs_cache\nRequête: couples.status = "suggested"`,
        livresNonTrouves: `Livres avec statut "not_found" dans le cache\nCollection: livresauteurs_cache\nRequête: couples.status = "not_found"`,
        livresSansLienBabelio: `Livres sans URL Babelio et non marqués "not_found"\nCollection: livres\nFiltres: url_babelio IS NULL AND babelio_not_found ≠ true`,
        auteursSansLienBabelio: `Auteurs sans URL Babelio et non marqués "not_found"\nCollection: auteurs\nFiltres: url_babelio IS NULL AND babelio_not_found ≠ true`,
        critiquesManquants: `Épisodes avec noms de critiques non présents en base\nCollections: episodes, avis_critiques, critiques\nLogique: Extraction noms depuis summaries → vérification existence`,
        episodesSansEmission: `Épisodes avec avis critique mais sans émission créée\nCollections: avis_critiques, emissions, episodes\nFormule: COUNT(avis non masqués) - COUNT(emissions)`,
        doublons: `Doublons détectés (livres + auteurs)\nLivres: Même URL Babelio\nAuteurs: Même URL Babelio\nFusion: Scraping Babelio pour données officielles`
      },
      babelioIcon: babelioSymbol,
      babelioIconLiaison: babelioSymbolLiaison,
      calibreIcon: calibreIcon,
      critiquesManquantsCount: null,
      episodesSansEmissionCount: null,
      duplicateBooksCount: null,
      duplicateAuthorsCount: null,
      loading: true,
      error: null
    };
  },

  computed: {
    totalDuplicatesCount() {
      if (this.duplicateBooksCount === null || this.duplicateAuthorsCount === null) {
        return null;
      }
      return this.duplicateBooksCount + this.duplicateAuthorsCount;
    },
    formattedLastUpdate() {
      // Issue #128: Utiliser last_episode_date depuis collectionsStatistics
      const lastDate = this.collectionsStatistics?.last_episode_date || this.statistics.lastUpdateDate;
      if (!lastDate) {
        return null;
      }

      try {
        const date = new Date(lastDate);
        return date.toLocaleDateString('fr-FR', {
          day: '2-digit',
          month: '2-digit',
          year: '2-digit'
        });
      } catch (error) {
        console.error('Erreur de formatage de date:', error);
        return '--';
      }
    },

    lmelpFrontOfficeUrl() {
      // Issue #128: URL vers le front-office lmelp (port 8501)
      return 'http://localhost:8501/';
    },

    lmelpAvisCritiquesUrl() {
      // Issue #128: URL vers la page avis critiques du front-office
      return 'http://localhost:8501/avis_critiques';
    },

    babelioCompletionPercentage() {
      if (!this.collectionsStatistics ||
          this.collectionsStatistics.livres_uniques == null ||
          this.collectionsStatistics.books_without_url_babelio == null) {
        return '...';
      }

      const total = this.collectionsStatistics.livres_uniques;
      const withoutUrl = this.collectionsStatistics.books_without_url_babelio;
      const withUrl = total - withoutUrl;

      if (total === 0) {
        return '0%';
      }

      const percentage = Math.round((withUrl / total) * 100);
      return `${percentage}%`;
    },

    babelioAuthorsCompletionPercentage() {
      if (!this.collectionsStatistics ||
          this.collectionsStatistics.auteurs_uniques == null ||
          this.collectionsStatistics.authors_without_url_babelio == null) {
        return '...';
      }

      const total = this.collectionsStatistics.auteurs_uniques;
      const withoutUrl = this.collectionsStatistics.authors_without_url_babelio;
      const withUrl = total - withoutUrl;

      if (total === 0) {
        return '0%';
      }

      const percentage = Math.round((withUrl / total) * 100);
      return `${percentage}%`;
    }
  },

  async mounted() {
    // Charger toutes les statistiques en parallèle pour un affichage simultané
    await Promise.all([
      this.loadStatistics(),
      this.loadCollectionsStatistics(),
      this.loadCritiquesManquants(),
      this.loadDuplicateStatistics()
    ]);
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
          maskedEpisodes: '--',
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
        // Issue #124: Charger depuis /api/stats qui contient toutes les métriques
        // y compris books_without_url_babelio et authors_without_url_babelio
        const stats = await livresAuteursService.getCollectionsStatistics();
        this.collectionsStatistics = stats;
        // Issue #154: Charger le compteur épisodes sans émission
        this.episodesSansEmissionCount = stats.episodes_sans_emission;
      } catch (error) {
        console.error('Erreur lors du chargement des statistiques des collections:', error);
        // Garder les valeurs null en cas d'erreur pour afficher '...'
        this.collectionsStatistics = {
          episodes_non_traites: '--',
          couples_en_base: '--',
          avis_critiques_analyses: '--',
          couples_suggested_pas_en_base: '--',
          couples_not_found_pas_en_base: '--'
        };
      }
    },

    async loadCritiquesManquants() {
      try {
        const response = await axios.get('/api/stats/critiques-manquants');
        this.critiquesManquantsCount = response.data.count;
      } catch (error) {
        console.error('Erreur lors du chargement du nombre de critiques manquants:', error);
        this.critiquesManquantsCount = null; // Afficher '...' en cas d'erreur
      }
    },

    async loadDuplicateStatistics() {
      try {
        const [booksResponse, authorsResponse] = await Promise.all([
          axios.get('/api/books/duplicates/statistics'),
          axios.get('/api/authors/duplicates/statistics')
        ]);
        this.duplicateBooksCount = booksResponse.data.total_duplicates;
        this.duplicateAuthorsCount = authorsResponse.data.total_duplicates;
      } catch (error) {
        console.error('Erreur lors du chargement des stats doublons:', error);
        this.duplicateBooksCount = null;
        this.duplicateAuthorsCount = null;
      }
    },

    navigateToEpisodes() {
      this.$router.push('/episodes');
    },

    navigateToEmissions() {
      this.$router.push('/emissions');
    },

    navigateToLivresAuteurs() {
      this.$router.push('/livres-auteurs');
    },

    navigateToIdentificationCritiques() {
      this.$router.push('/identification-critiques');
    },

    navigateToBabelioTest() {
      this.$router.push('/babelio-test');
    },

    navigateToBabelioMigration() {
      this.$router.push('/babelio-migration');
    },

    navigateToAdvancedSearch() {
      this.$router.push('/search');
    },

    navigateToMasquerEpisodes() {
      this.$router.push('/masquer-episodes');
    },

    navigateToCalibre() {
      this.$router.push('/calibre');
    },

    navigateToGenerationAvis() {
      this.$router.push('/generation-avis-critiques');
    },

    navigateToDuplicates() {
      this.$router.push('/duplicates');
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
  text-decoration: none;
  color: inherit;
  display: block;
}

.stat-card.clickable-stat {
  cursor: pointer;
  transition: all 0.3s ease;
  border: 2px solid transparent;
}

.stat-card.clickable-stat:hover {
  transform: translateY(-4px);
  box-shadow: 0 4px 16px rgba(0,0,0,0.15);
  border-color: #667eea;
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

.function-icon-img {
  width: 3rem;
  height: auto;
  display: inline-block;
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
