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

      <!-- Section simplifiée : nombre de livres extraits seulement -->
      <section v-if="selectedEpisodeId && !loading && !error && books.length > 0" class="stats-section">
        <div class="simple-stats">
          <span class="books-count">{{ books.length }} livre(s) extrait(s)</span>
        </div>
      </section>

      <!-- Message d'aide si aucun épisode sélectionné -->
      <div v-if="!selectedEpisodeId && !episodesLoading && !episodesError" class="help-message card">
        <h3>👆 Sélectionnez un épisode pour commencer</h3>
        <p>
          Choisissez un épisode dans la liste déroulante ci-dessus pour voir les livres et auteurs
          extraits de ses avis critiques.
        </p>
        <div class="features">
          <h4>Fonctionnalités disponibles :</h4>
          <ul>
            <li>📚 Extraction des livres discutés au programme</li>
            <li>✍️ Identification des auteurs et éditeurs</li>
            <li>📋 Affichage en tableau simple et navigable</li>
            <li>🔄 Tri alphabétique par colonnes (cliquez sur les en-têtes)</li>
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
          <span class="search-help">💡 Cliquez sur les en-têtes du tableau pour trier</span>
        </div>
      </section>

      <!-- État de chargement -->
      <div v-if="selectedEpisodeId && loading" class="loading-state">
        <div class="loader"></div>
        <p>Chargement des livres et auteurs...</p>
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

      <!-- Tableau des livres -->
      <section v-if="selectedEpisodeId && !loading && !error && filteredBooks.length > 0" class="books-section">
        <div class="table-container">
          <table class="books-table">
            <thead>
              <tr>
                <th class="sortable-header" @click="setSortOrder('author')">
                  Auteur
                  <span class="sort-indicator" :class="getSortClass('author')">↕</span>
                </th>
                <th class="sortable-header" @click="setSortOrder('title')">
                  Titre
                  <span class="sort-indicator" :class="getSortClass('title')">↕</span>
                </th>
                <th class="sortable-header" @click="setSortOrder('publisher')">
                  Éditeur
                  <span class="sort-indicator" :class="getSortClass('publisher')">↕</span>
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="book in filteredBooks" :key="`${book.episode_oid}-${book.auteur}-${book.titre}`" class="book-row" data-testid="book-item">
                <td class="author-cell">{{ book.auteur }}</td>
                <td class="title-cell">{{ book.titre }}</td>
                <td class="publisher-cell">{{ book.editeur || '-' }}</td>
              </tr>
            </tbody>
          </table>
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
      currentSortField: 'author',
      sortAscending: true
    };
  },

  computed: {

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

      // Appliquer le tri par colonnes
      filtered.sort((a, b) => {
        let sortValue = 0;

        switch (this.currentSortField) {
          case 'author':
            sortValue = a.auteur.localeCompare(b.auteur, 'fr', { sensitivity: 'base' });
            break;
          case 'title':
            sortValue = a.titre.localeCompare(b.titre, 'fr', { sensitivity: 'base' });
            break;
          case 'publisher':
            const publisherA = a.editeur || '';
            const publisherB = b.editeur || '';
            sortValue = publisherA.localeCompare(publisherB, 'fr', { sensitivity: 'base' });
            break;
          default:
            sortValue = a.auteur.localeCompare(b.auteur, 'fr', { sensitivity: 'base' });
        }

        return this.sortAscending ? sortValue : -sortValue;
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

    setSortOrder(field) {
      if (this.currentSortField === field) {
        this.sortAscending = !this.sortAscending;
      } else {
        this.currentSortField = field;
        this.sortAscending = true;
      }
    },

    getSortClass(field) {
      if (this.currentSortField !== field) {
        return '';
      }
      return this.sortAscending ? 'sort-asc' : 'sort-desc';
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
.simple-stats {
  margin-bottom: 1.5rem;
  text-align: center;
}

.books-count {
  font-size: 1.1rem;
  color: #666;
  font-weight: 500;
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

/* Tableau des livres */
.table-container {
  background: white;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.books-table {
  width: 100%;
  border-collapse: collapse;
}

.books-table thead {
  background: #f8f9fa;
}

.books-table th {
  padding: 1rem;
  text-align: left;
  font-weight: 600;
  color: #333;
  border-bottom: 2px solid #eee;
}

.sortable-header {
  cursor: pointer;
  user-select: none;
  position: relative;
  transition: background-color 0.2s ease;
}

.sortable-header:hover {
  background: #e9ecef;
}

.sort-indicator {
  opacity: 0.5;
  margin-left: 0.5rem;
  font-size: 0.8rem;
  transition: opacity 0.2s ease;
}

.sort-asc .sort-indicator {
  opacity: 1;
  color: #667eea;
}

.sort-asc .sort-indicator::before {
  content: '↑';
}

.sort-desc .sort-indicator {
  opacity: 1;
  color: #667eea;
}

.sort-desc .sort-indicator::before {
  content: '↓';
}

.books-table tbody tr {
  border-bottom: 1px solid #eee;
  transition: background-color 0.2s ease;
}

.books-table tbody tr:hover {
  background: #f8f9fa;
}

.books-table td {
  padding: 1rem;
  vertical-align: top;
}

.author-cell {
  font-weight: 500;
  color: #667eea;
}

.title-cell {
  font-weight: 600;
  color: #333;
}

.publisher-cell {
  color: #666;
}

/* Aide pour le tri */
.search-help {
  font-size: 0.85rem;
  color: #666;
  margin-left: 1rem;
  font-style: italic;
}

/* Section ratings et favorites supprimées - design simplifié */

/* Responsive */
@media (max-width: 768px) {
  .page-header {
    padding: 1.5rem 1rem;
    margin: -1rem -1rem 1.5rem -1rem;
  }

  .page-header h1 {
    font-size: 2rem;
  }

  .filter-controls {
    flex-direction: column;
    gap: 1rem;
  }

  .search-input {
    width: 100%;
  }

  .search-help {
    margin-left: 0;
    margin-top: 0.5rem;
    display: block;
  }

  .books-table th,
  .books-table td {
    padding: 0.75rem;
  }

  .table-container {
    margin: 0 -1rem;
    border-radius: 0;
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
