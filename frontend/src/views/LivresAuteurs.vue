<template>
  <div class="livres-auteurs">
    <!-- Navigation -->
    <Navigation pageTitle="Livres et Auteurs" />

    <main>
      <!-- Sélecteur d'épisode -->
      <section class="episode-selector-section">
        <div class="episode-selector card">
          <!-- État de chargement des épisodes -->
          <div v-if="episodesLoading" class="loading">
            Chargement des épisodes avec avis critiques...
          </div>

          <!-- Affichage d'erreur des épisodes -->
          <div v-if="episodesError" class="alert alert-error">
            {{ episodesError }}
            <button @click="loadEpisodesWithReviews" class="btn btn-primary" style="margin-left: 1rem;">
              Réessayer
            </button>
          </div>

          <!-- Sélecteur d'épisode -->
          <div v-if="!episodesLoading && !episodesError" class="form-group">
            <label for="episode-select" class="form-label">
              Choisir un épisode avec avis critiques ({{ episodesWithReviews.length }} disponibles)
            </label>
            <select
              id="episode-select"
              v-model="selectedEpisodeId"
              @change="onEpisodeChange"
              class="form-control"
            >
              <option value="">-- Sélectionner un épisode --</option>
              <option
                v-for="episode in episodesWithReviews"
                :key="episode.id"
                :value="episode.id"
              >
                {{ formatEpisodeOption(episode) }}
              </option>
            </select>
          </div>
        </div>
      </section>

      <!-- Statistiques de synthèse -->
      <section v-if="selectedEpisodeId && !loading && !error && books.length > 0" class="stats-section">
        <div class="stats-grid">
          <div class="stat-card">
            <div class="stat-value">{{ books.length }}</div>
            <div class="stat-label">Livres extraits</div>
          </div>
          <div class="stat-card">
            <div class="stat-value">{{ uniqueAuthors }}</div>
            <div class="stat-label">Auteurs différents</div>
          </div>
          <div class="stat-card">
            <div class="stat-value">{{ uniqueEpisodes }}</div>
            <div class="stat-label">Épisodes sources</div>
          </div>
          <div class="stat-card">
            <div class="stat-value">{{ averageRating.toFixed(1) }}</div>
            <div class="stat-label">Note moyenne globale</div>
          </div>
        </div>
      </section>

      <!-- Message d'aide si aucun épisode sélectionné -->
      <div v-if="!selectedEpisodeId && !episodesLoading && !episodesError" class="help-message card">
        <h3>👆 Sélectionnez un épisode pour commencer</h3>
        <p>
          Choisissez un épisode dans la liste déroulante ci-dessus pour voir les livres et auteurs
          extraits de ses avis critiques via LLM.
        </p>
        <div class="features">
          <h4>Fonctionnalités disponibles :</h4>
          <ul>
            <li>📚 Extraction des livres discutés au programme</li>
            <li>✍️ Identification des auteurs et éditeurs</li>
            <li>⭐ Notes moyennes et nombre de critiques</li>
            <li>❤️ Coups de cœur des critiques</li>
            <li>🔍 Recherche et filtrage des résultats</li>
          </ul>
        </div>
      </div>

      <!-- Filtre de recherche -->
      <section v-if="selectedEpisodeId && !loading && !error && books.length > 0" class="filter-section">
        <div class="filter-controls">
          <input
            v-model="searchFilter"
            type="text"
            placeholder="Filtrer par auteur, titre ou éditeur..."
            class="search-input"
          />
          <select v-model="sortOrder" class="sort-select">
            <option value="rating_desc">Note décroissante</option>
            <option value="rating_asc">Note croissante</option>
            <option value="author_asc">Auteur A→Z</option>
            <option value="author_desc">Auteur Z→A</option>
            <option value="date_desc">Date décroissante</option>
            <option value="date_asc">Date croissante</option>
          </select>
        </div>
      </section>

      <!-- État de chargement -->
      <div v-if="selectedEpisodeId && loading" class="loading-state">
        <div class="loader"></div>
        <p>Chargement des extractions LLM...</p>
      </div>

      <!-- État d'erreur -->
      <div v-if="selectedEpisodeId && error" class="error-state">
        <div class="error-icon">❌</div>
        <h3>Erreur de chargement</h3>
        <p>{{ error }}</p>
        <button @click="loadBooksForEpisode" class="retry-button">Réessayer</button>
      </div>

      <!-- État vide -->
      <div v-if="selectedEpisodeId && !loading && !error && books.length === 0" class="empty-state">
        <div class="empty-icon">📚</div>
        <h3>Aucun livre trouvé</h3>
        <p>Aucun livre n'a pu être extrait des avis critiques de cet épisode.</p>
      </div>

      <!-- Liste des livres -->
      <section v-if="selectedEpisodeId && !loading && !error && filteredBooks.length > 0" class="books-section">
        <div class="books-grid">
          <div
            v-for="book in filteredBooks"
            :key="`${book.episode_oid}-${book.auteur}-${book.titre}`"
            class="book-card"
            data-testid="book-item"
          >
            <!-- Métadonnées d'épisode -->
            <div class="episode-metadata">
              <div class="episode-title">{{ book.episode_title }}</div>
              <div class="episode-date">{{ book.episode_date }}</div>
            </div>

            <!-- Informations bibliographiques -->
            <div class="book-info">
              <h3 class="book-title">{{ book.titre }}</h3>
              <div class="book-author">par {{ book.auteur }}</div>
              <div class="book-publisher">{{ book.editeur }}</div>
            </div>

            <!-- Métriques et évaluations -->
            <div class="book-metrics">
              <div class="rating-section">
                <div class="rating-value" :class="getRatingClass(book.note_moyenne)">
                  {{ book.note_moyenne.toFixed(1) }}
                </div>
                <div class="rating-label">{{ book.nb_critiques }} critiques</div>
              </div>

              <!-- Coups de cœur -->
              <div v-if="book.coups_de_coeur.length > 0" class="favorites-section">
                <div class="favorites-label">Coups de cœur :</div>
                <div class="favorites-list">
                  <span
                    v-for="critique in book.coups_de_coeur"
                    :key="critique"
                    class="favorite-tag"
                  >
                    {{ critique }}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- Message de filtrage -->
      <div v-if="selectedEpisodeId && !loading && !error && books.length > 0 && filteredBooks.length === 0" class="no-results">
        <div class="no-results-icon">🔍</div>
        <h3>Aucun résultat</h3>
        <p>Aucun livre ne correspond aux critères de recherche "{{ searchFilter }}"</p>
      </div>
    </main>
  </div>
</template>

<script>
import { livresAuteursService } from '../services/api.js';
import Navigation from '../components/Navigation.vue';

export default {
  name: 'LivresAuteurs',

  components: {
    Navigation,
  },

  data() {
    return {
      // Données pour les épisodes
      episodesWithReviews: [],
      episodesLoading: true,
      episodesError: null,
      selectedEpisodeId: '',

      // Données pour les livres
      books: [],
      loading: false,
      error: null,
      searchFilter: '',
      sortOrder: 'rating_desc'
    };
  },

  computed: {
    uniqueAuthors() {
      const authors = new Set(this.books.map(book => book.auteur));
      return authors.size;
    },

    uniqueEpisodes() {
      const episodes = new Set(this.books.map(book => book.episode_oid));
      return episodes.size;
    },

    averageRating() {
      if (this.books.length === 0) return 0;
      const sum = this.books.reduce((total, book) => total + book.note_moyenne, 0);
      return sum / this.books.length;
    },

    filteredBooks() {
      let filtered = [...this.books];

      // Appliquer le filtre de recherche
      if (this.searchFilter.trim()) {
        const search = this.searchFilter.toLowerCase();
        filtered = filtered.filter(book =>
          book.auteur.toLowerCase().includes(search) ||
          book.titre.toLowerCase().includes(search) ||
          book.editeur.toLowerCase().includes(search)
        );
      }

      // Appliquer le tri
      filtered.sort((a, b) => {
        switch (this.sortOrder) {
          case 'rating_desc':
            return b.note_moyenne - a.note_moyenne;
          case 'rating_asc':
            return a.note_moyenne - b.note_moyenne;
          case 'author_asc':
            return a.auteur.localeCompare(b.auteur);
          case 'author_desc':
            return b.auteur.localeCompare(a.auteur);
          case 'date_desc':
            return new Date(b.episode_date) - new Date(a.episode_date);
          case 'date_asc':
            return new Date(a.episode_date) - new Date(b.episode_date);
          default:
            return 0;
        }
      });

      return filtered;
    }
  },

  async mounted() {
    await this.loadEpisodesWithReviews();
  },

  methods: {
    /**
     * Charge la liste des épisodes avec avis critiques
     */
    async loadEpisodesWithReviews() {
      try {
        this.episodesLoading = true;
        this.episodesError = null;
        this.episodesWithReviews = await livresAuteursService.getEpisodesWithReviews();
      } catch (error) {
        this.episodesError = error.message;
        console.error('Erreur lors du chargement des épisodes:', error);
      } finally {
        this.episodesLoading = false;
      }
    },

    /**
     * Charge les livres pour un épisode sélectionné
     */
    async loadBooksForEpisode() {
      if (!this.selectedEpisodeId) {
        this.books = [];
        return;
      }

      try {
        this.loading = true;
        this.error = null;

        // Récupérer SEULEMENT les livres de cet épisode (efficace !)
        this.books = await livresAuteursService.getLivresAuteurs({ episode_oid: this.selectedEpisodeId });
      } catch (error) {
        this.error = error.message;
        console.error('Erreur lors du chargement des livres/auteurs:', error);
      } finally {
        this.loading = false;
      }
    },

    /**
     * Gère le changement d'épisode sélectionné
     */
    async onEpisodeChange() {
      // Réinitialiser les filtres
      this.searchFilter = '';
      this.sortOrder = 'rating_desc';

      // Charger les livres pour le nouvel épisode
      await this.loadBooksForEpisode();
    },

    /**
     * Formate l'affichage d'un épisode dans la liste
     */
    formatEpisodeOption(episode) {
      const date = new Date(episode.date).toLocaleDateString('fr-FR');
      const title = episode.titre_corrige || episode.titre;
      return `${date} - ${title}`;
    },

    getRatingClass(rating) {
      if (rating >= 8) return 'rating-excellent';
      if (rating >= 7) return 'rating-good';
      if (rating >= 5) return 'rating-average';
      return 'rating-poor';
    }
  }
};
</script>

<style scoped>
.livres-auteurs {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

/* Styles supprimés car remplacés par le composant Navigation standardisé */

/* Contenu principal */
.content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2rem;
  max-width: 1200px;
  margin: 0 auto;
  width: 100%;
}

/* Statistiques */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  margin-bottom: 2rem;
}

.stat-card {
  background: white;
  padding: 1.5rem;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  text-align: center;
}

.stat-value {
  font-size: 2rem;
  font-weight: bold;
  color: #667eea;
  margin-bottom: 0.5rem;
}

.stat-label {
  font-size: 0.9rem;
  color: #666;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

/* Filtres */
.filter-section {
  background: white;
  padding: 1.5rem;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.filter-controls {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
}

.search-input, .sort-select {
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 1rem;
}

.search-input {
  flex: 1;
  min-width: 250px;
}

.sort-select {
  min-width: 180px;
}

/* États */
.loading-state, .error-state, .empty-state, .no-results {
  text-align: center;
  padding: 3rem;
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.loader {
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 1rem;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.error-icon, .empty-icon, .no-results-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.retry-button {
  background: #667eea;
  color: white;
  border: none;
  padding: 0.75rem 1.5rem;
  border-radius: 8px;
  cursor: pointer;
  font-size: 1rem;
  margin-top: 1rem;
  transition: background-color 0.3s ease;
}

.retry-button:hover {
  background: #5a6fd8;
}

/* Grille de livres */
.books-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 1.5rem;
}

.book-card {
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  overflow: hidden;
  transition: transform 0.3s ease, box-shadow 0.3s ease;
}

.book-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(0,0,0,0.15);
}

.episode-metadata {
  background: #f8f9fa;
  padding: 1rem;
  border-bottom: 1px solid #eee;
}

.episode-title {
  font-size: 0.85rem;
  color: #666;
  margin-bottom: 0.25rem;
  line-height: 1.3;
}

.episode-date {
  font-size: 0.8rem;
  color: #999;
}

.book-info {
  padding: 1.5rem;
  border-bottom: 1px solid #eee;
}

.book-title {
  font-size: 1.2rem;
  font-weight: 600;
  color: #333;
  margin-bottom: 0.5rem;
  line-height: 1.3;
}

.book-author {
  font-size: 1rem;
  color: #667eea;
  font-weight: 500;
  margin-bottom: 0.25rem;
}

.book-publisher {
  font-size: 0.9rem;
  color: #666;
}

.book-metrics {
  padding: 1.5rem;
}

.rating-section {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1rem;
}

.rating-value {
  font-size: 1.5rem;
  font-weight: bold;
  padding: 0.25rem 0.75rem;
  border-radius: 6px;
  color: white;
}

.rating-excellent { background-color: #4CAF50; }
.rating-good { background-color: #8BC34A; }
.rating-average { background-color: #FF9800; }
.rating-poor { background-color: #F44336; }

.rating-label {
  font-size: 0.9rem;
  color: #666;
}

.favorites-section {
  margin-top: 1rem;
}

.favorites-label {
  font-size: 0.85rem;
  color: #666;
  margin-bottom: 0.5rem;
}

.favorites-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.favorite-tag {
  background: #e3f2fd;
  color: #1976d2;
  padding: 0.25rem 0.5rem;
  border-radius: 12px;
  font-size: 0.8rem;
  font-weight: 500;
}

/* Responsive */
@media (max-width: 768px) {
  .page-header {
    padding: 1.5rem 1rem;
    margin: -1rem -1rem 1.5rem -1rem;
  }

  .page-header h1 {
    font-size: 2rem;
  }

  .books-grid {
    grid-template-columns: 1fr;
  }

  .filter-controls {
    flex-direction: column;
  }

  .search-input, .sort-select {
    width: 100%;
  }

  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 480px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }
}

/* Styles pour le sélecteur d'épisodes (basés sur EpisodeSelector.vue) */
.episode-selector-section {
  margin-bottom: 2rem;
}

.episode-selector.card {
  background: white;
  border-radius: 12px;
  padding: 2rem;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  margin-bottom: 2rem;
}

.episode-selector h2 {
  margin-bottom: 1rem;
  color: #333;
}

.form-control {
  font-family: monospace;
  font-size: 0.9rem;
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 6px;
  transition: border-color 0.3s ease;
}

.form-control:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.loading {
  text-align: center;
  padding: 1rem;
  color: #666;
  font-style: italic;
}

.alert {
  padding: 1rem;
  border-radius: 6px;
  margin-bottom: 1rem;
}

.alert-error {
  background-color: #fee;
  color: #c33;
  border: 1px solid #fcc;
}

.btn {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.9rem;
  transition: background-color 0.3s ease;
}

.btn-primary {
  background-color: #667eea;
  color: white;
}

.btn-primary:hover {
  background-color: #5a67d8;
}

/* Message d'aide (basé sur EpisodePage.vue) */
.help-message {
  text-align: center;
  padding: 3rem;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  border: none;
  border-radius: 12px;
  margin-bottom: 2rem;
}

.help-message h3 {
  color: #333;
  margin-bottom: 1rem;
  font-size: 1.3rem;
}

.help-message p {
  color: #666;
  margin-bottom: 2rem;
  font-size: 1.1rem;
  line-height: 1.6;
}

.features {
  text-align: left;
  max-width: 500px;
  margin: 0 auto;
}

.features h4 {
  color: #333;
  margin-bottom: 1rem;
  text-align: center;
}

.features ul {
  list-style: none;
  padding: 0;
}

.features li {
  padding: 0.5rem 0;
  font-size: 1rem;
  color: #555;
}
</style>
