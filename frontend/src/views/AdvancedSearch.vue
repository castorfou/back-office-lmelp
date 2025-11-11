<template>
  <div class="advanced-search-page">
    <!-- Navigation -->
    <Navigation pageTitle="Recherche avancée" />

    <!-- Zone de recherche principale -->
    <div class="search-section">
      <div class="search-input-container">
        <div class="search-icon">🔍</div>
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Rechercher dans le contenu (minimum 3 caractères)..."
          class="search-input"
          @input="handleSearchInput"
          @keydown.enter="performSearch"
          @keydown.esc="clearSearch"
        />
        <button
          v-if="searchQuery.length > 0"
          @click="clearSearch"
          class="clear-button"
          type="button"
          title="Effacer la recherche"
        >
          ✕
        </button>
      </div>

      <!-- Filtres par entités -->
      <div class="filters-section">
        <h3>Filtrer par type de contenu :</h3>
        <div class="filter-checkboxes">
          <label class="filter-checkbox">
            <input type="checkbox" v-model="filters.episodes" @change="handleFilterChange" />
            <span class="checkbox-label">🎙️ Épisodes</span>
          </label>
          <label class="filter-checkbox">
            <input type="checkbox" v-model="filters.auteurs" @change="handleFilterChange" />
            <span class="checkbox-label">👤 Auteurs</span>
          </label>
          <label class="filter-checkbox">
            <input type="checkbox" v-model="filters.livres" @change="handleFilterChange" />
            <span class="checkbox-label">📚 Livres</span>
          </label>
          <label class="filter-checkbox">
            <input type="checkbox" v-model="filters.editeurs" @change="handleFilterChange" />
            <span class="checkbox-label">🏢 Éditeurs</span>
          </label>
        </div>
        <div class="filter-actions">
          <button @click="selectAllFilters" class="btn-secondary">Tout sélectionner</button>
          <button @click="deselectAllFilters" class="btn-secondary">Tout désélectionner</button>
        </div>
      </div>
    </div>

    <!-- État de chargement -->
    <div v-if="loading" class="loading-state">
      <div class="loading-spinner"></div>
      <span>Recherche en cours...</span>
    </div>

    <!-- Message d'erreur -->
    <div v-if="error" class="error-state">
      <div class="error-icon">⚠️</div>
      <span>Erreur lors de la recherche: {{ error }}</span>
    </div>

    <!-- Résultats de recherche -->
    <div v-if="showResults && !loading && !error" class="search-results">
      <div v-if="hasResults" class="results-container">
        <!-- En-tête des résultats -->
        <div class="results-header">
          <h2>Résultats pour "{{ lastSearchQuery }}"</h2>
          <p class="results-summary">
            {{ totalResults }} résultat{{ totalResults > 1 ? 's' : '' }} trouvé{{ totalResults > 1 ? 's' : '' }}
          </p>
        </div>

        <!-- Auteurs -->
        <div v-if="results.auteurs && results.auteurs.length > 0" class="result-category">
          <h3 class="category-title">👤 AUTEURS ({{ results.auteurs_total_count || results.auteurs.length }})</h3>
          <ul class="result-list">
            <li v-for="(auteur, index) in results.auteurs" :key="`auteur-${index}`" class="result-item clickable-item">
              <router-link :to="`/auteur/${auteur._id}`" class="result-link">
                <span class="result-name" v-html="highlightSearchTerm(auteur.nom)"></span>
                <span class="result-arrow">→</span>
              </router-link>
            </li>
          </ul>
        </div>

        <!-- Livres -->
        <div v-if="results.livres && results.livres.length > 0" class="result-category">
          <h3 class="category-title">📚 LIVRES ({{ results.livres_total_count || results.livres.length }})</h3>
          <ul class="result-list">
            <li v-for="(livre, index) in results.livres" :key="`livre-${index}`" class="result-item">
              <span class="result-name" v-html="highlightSearchTerm(formatLivreDisplay(livre))"></span>
            </li>
          </ul>
        </div>

        <!-- Éditeurs -->
        <div v-if="results.editeurs && results.editeurs.length > 0" class="result-category">
          <h3 class="category-title">🏢 ÉDITEURS ({{ results.editeurs.length }})</h3>
          <ul class="result-list">
            <li v-for="(editeur, index) in results.editeurs" :key="`editeur-${index}`" class="result-item">
              <span class="result-name" v-html="highlightSearchTerm(editeur.nom)"></span>
            </li>
          </ul>
        </div>

        <!-- Épisodes -->
        <div v-if="results.episodes && results.episodes.length > 0" class="result-category">
          <h3 class="category-title">🎙️ ÉPISODES ({{ results.episodes_total_count || results.episodes.length }})</h3>
          <ul class="result-list">
            <li v-for="episode in results.episodes" :key="`episode-${episode._id}`" class="result-item episode-item">
              <div class="episode-content">
                <div class="episode-main-info">
                  <span class="episode-date-primary">{{ formatDate(episode.date) }}</span>
                  <div class="episode-context" v-html="episode.search_context || episode.titre"></div>
                </div>
              </div>
            </li>
          </ul>
        </div>

        <!-- Pagination -->
        <div v-if="pagination.total_pages > 1" class="pagination">
          <button
            @click="goToPage(pagination.page - 1)"
            :disabled="pagination.page === 1"
            class="pagination-button"
          >
            ← Précédent
          </button>
          <span class="pagination-info">
            Page {{ pagination.page }} sur {{ pagination.total_pages }}
          </span>
          <button
            @click="goToPage(pagination.page + 1)"
            :disabled="pagination.page === pagination.total_pages"
            class="pagination-button"
          >
            Suivant →
          </button>
        </div>
      </div>

      <!-- Aucun résultat -->
      <div v-else class="no-results">
        <div class="no-results-icon">🔍</div>
        <h3>Aucun résultat trouvé</h3>
        <p>Aucun contenu ne correspond à votre recherche "{{ lastSearchQuery }}"</p>
        <p class="suggestion">Essayez avec d'autres mots-clés ou modifiez les filtres.</p>
      </div>
    </div>
  </div>
</template>

<script>
import { searchService } from '../services/api.js';
import Navigation from '../components/Navigation.vue';
import { highlightSearchTermAccentInsensitive } from '../utils/textUtils.js';

// Fonction debounce pour éviter trop de requêtes
function debounce(func, delay) {
  let timeoutId;
  return function (...args) {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => func.apply(this, args), delay);
  };
}

export default {
  name: 'AdvancedSearch',

  components: {
    Navigation
  },

  data() {
    return {
      searchQuery: '',
      lastSearchQuery: '',
      loading: false,
      error: null,
      showResults: false,
      filters: {
        episodes: true,
        auteurs: true,
        livres: true,
        editeurs: true
      },
      results: {
        auteurs: [],
        auteurs_total_count: 0,
        livres: [],
        livres_total_count: 0,
        editeurs: [],
        episodes: [],
        episodes_total_count: 0
      },
      pagination: {
        page: 1,
        limit: 20,
        total_pages: 1
      }
    };
  },

  computed: {
    hasResults() {
      return (
        this.results.auteurs.length > 0 ||
        this.results.livres.length > 0 ||
        this.results.editeurs.length > 0 ||
        this.results.episodes.length > 0
      );
    },
    totalResults() {
      return (
        this.results.auteurs_total_count +
        this.results.livres_total_count +
        this.results.episodes_total_count +
        this.results.editeurs.length
      );
    },
    selectedEntities() {
      const entities = [];
      if (this.filters.episodes) entities.push('episodes');
      if (this.filters.auteurs) entities.push('auteurs');
      if (this.filters.livres) entities.push('livres');
      if (this.filters.editeurs) entities.push('editeurs');
      return entities;
    }
  },

  created() {
    // Debounce la fonction de recherche (300ms)
    this.debouncedSearch = debounce(this.performSearch, 300);

    // Récupérer la requête depuis l'URL si présente
    const urlParams = new URLSearchParams(window.location.search);
    const queryFromUrl = urlParams.get('q');
    if (queryFromUrl && queryFromUrl.length >= 3) {
      this.searchQuery = queryFromUrl;
      this.performSearch();
    }
  },

  methods: {
    handleSearchInput() {
      // Cacher les résultats si l'input est vide
      if (this.searchQuery.trim().length === 0) {
        this.showResults = false;
        this.error = null;
        this.loading = false;
        return;
      }

      // Ne pas rechercher si moins de 3 caractères
      if (this.searchQuery.trim().length < 3) {
        this.showResults = false;
        this.error = null;
        this.loading = false;
        return;
      }

      // Déclencher la recherche avec debounce
      this.debouncedSearch();
    },

    handleFilterChange() {
      // Relancer la recherche si une recherche a déjà été effectuée
      if (this.lastSearchQuery) {
        this.pagination.page = 1; // Reset à la page 1
        this.performSearch();
      }
    },

    async performSearch() {
      const query = this.searchQuery.trim();

      if (query.length < 3) {
        return;
      }

      // Vérifier qu'au moins un filtre est sélectionné
      if (this.selectedEntities.length === 0) {
        this.error = 'Veuillez sélectionner au moins un type de contenu';
        this.showResults = false;
        return;
      }

      this.loading = true;
      this.error = null;
      this.lastSearchQuery = query;

      try {
        // Appel à l'endpoint advanced-search
        const response = await searchService.advancedSearch(
          query,
          this.selectedEntities,
          this.pagination.page,
          this.pagination.limit
        );

        this.results = response.results;
        this.pagination = response.pagination;
        this.showResults = true;

        // Mettre à jour l'URL sans recharger la page
        const newUrl = `${window.location.pathname}?q=${encodeURIComponent(query)}`;
        window.history.pushState({}, '', newUrl);
      } catch (error) {
        console.error('Erreur lors de la recherche:', error);
        this.error = error.message || 'Une erreur est survenue';
        this.showResults = false;
      } finally {
        this.loading = false;
      }
    },

    goToPage(page) {
      if (page < 1 || page > this.pagination.total_pages) {
        return;
      }
      this.pagination.page = page;
      this.performSearch();
      // Scroll vers le haut
      window.scrollTo({ top: 0, behavior: 'smooth' });
    },

    selectAllFilters() {
      this.filters.episodes = true;
      this.filters.auteurs = true;
      this.filters.livres = true;
      this.filters.editeurs = true;
      this.handleFilterChange();
    },

    deselectAllFilters() {
      this.filters.episodes = false;
      this.filters.auteurs = false;
      this.filters.livres = false;
      this.filters.editeurs = false;
    },

    clearSearch() {
      this.searchQuery = '';
      this.showResults = false;
      this.error = null;
      this.loading = false;
      this.lastSearchQuery = '';
      this.pagination.page = 1;
      this.results = {
        auteurs: [],
        auteurs_total_count: 0,
        livres: [],
        livres_total_count: 0,
        editeurs: [],
        episodes: [],
        episodes_total_count: 0
      };
      // Nettoyer l'URL
      window.history.pushState({}, '', window.location.pathname);
    },

    formatDate(dateString) {
      if (!dateString) return '';
      try {
        const date = new Date(dateString);
        return date.toLocaleDateString('fr-FR', {
          day: '2-digit',
          month: '2-digit',
          year: 'numeric'
        });
      } catch (error) {
        return dateString;
      }
    },

    formatLivreDisplay(livre) {
      if (livre.auteur_nom) {
        return `${livre.auteur_nom} - ${livre.titre}`;
      }
      return livre.titre;
    },

    highlightSearchTerm(text) {
      // Use accent-insensitive highlighting (Issue #92)
      return highlightSearchTermAccentInsensitive(text, this.lastSearchQuery);
    }
  }
};
</script>

<style scoped>
.advanced-search-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}

.search-section {
  background: white;
  padding: 2rem;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  margin-bottom: 2rem;
}

.search-input-container {
  position: relative;
  margin-bottom: 2rem;
}

.search-icon {
  position: absolute;
  left: 1rem;
  top: 50%;
  transform: translateY(-50%);
  font-size: 1.2rem;
  color: #666;
  pointer-events: none;
}

.search-input {
  width: 100%;
  padding: 1rem 3rem;
  border: 2px solid #ddd;
  border-radius: 12px;
  font-size: 1rem;
  background: white;
  transition: border-color 0.3s ease, box-shadow 0.3s ease;
}

.search-input:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.clear-button {
  position: absolute;
  right: 1rem;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  font-size: 1.2rem;
  color: #999;
  cursor: pointer;
  padding: 0.25rem;
  border-radius: 50%;
  width: 1.5rem;
  height: 1.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}

.clear-button:hover {
  background: #f0f0f0;
  color: #666;
}

.filters-section {
  border-top: 1px solid #e9ecef;
  padding-top: 1.5rem;
}

.filters-section h3 {
  font-size: 1rem;
  margin-bottom: 1rem;
  color: #333;
}

.filter-checkboxes {
  display: flex;
  gap: 1.5rem;
  flex-wrap: wrap;
  margin-bottom: 1rem;
}

.filter-checkbox {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
  font-size: 1rem;
}

.filter-checkbox input[type="checkbox"] {
  width: 18px;
  height: 18px;
  cursor: pointer;
}

.checkbox-label {
  user-select: none;
}

.filter-actions {
  display: flex;
  gap: 1rem;
}

.btn-secondary {
  padding: 0.5rem 1rem;
  background: #f8f9fa;
  border: 1px solid #ddd;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.9rem;
  transition: all 0.2s ease;
}

.btn-secondary:hover {
  background: #e9ecef;
}

.loading-state {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 3rem;
  gap: 1rem;
  color: #666;
}

.loading-spinner {
  width: 24px;
  height: 24px;
  border: 3px solid #f3f3f3;
  border-top: 3px solid #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}

.error-state {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.5rem;
  gap: 0.5rem;
  background: #fee;
  border: 1px solid #fcc;
  border-radius: 8px;
  color: #c33;
}

.search-results {
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.results-header {
  padding: 1.5rem;
  background: #f8f9fa;
  border-bottom: 1px solid #e9ecef;
}

.results-header h2 {
  margin: 0 0 0.5rem 0;
  font-size: 1.5rem;
  color: #333;
}

.results-summary {
  margin: 0;
  color: #666;
  font-size: 0.9rem;
}

.result-category {
  padding: 1.5rem;
  border-bottom: 1px solid #e9ecef;
}

.result-category:last-child {
  border-bottom: none;
}

.category-title {
  margin: 0 0 1rem 0;
  font-size: 1rem;
  font-weight: 600;
  color: #333;
}

.result-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.result-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem;
  margin-bottom: 0.5rem;
  background: #f8f9fa;
  border-radius: 8px;
}

.result-item.clickable-item {
  padding: 0;
  background: none;
  transition: transform 0.2s ease;
}

.result-item.clickable-item:hover {
  transform: translateX(4px);
}

.result-link {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  padding: 0.75rem;
  background: #f8f9fa;
  border-radius: 8px;
  text-decoration: none;
  color: inherit;
  transition: all 0.2s ease;
}

.result-link:hover {
  background: #e9ecef;
  border-color: #1976d2;
}

.result-arrow {
  color: #1976d2;
  font-size: 1.2rem;
  opacity: 0.5;
  transition: opacity 0.2s ease;
}

.result-link:hover .result-arrow {
  opacity: 1;
}

.result-item:hover {
  background: #e9ecef;
  cursor: pointer;
}

.result-item:last-child {
  margin-bottom: 0;
}

.result-name {
  font-weight: 500;
  color: #333;
  flex-grow: 1;
}

.episode-item .episode-content {
  display: flex;
  flex-direction: column;
  flex-grow: 1;
  gap: 0.5rem;
}

.episode-main-info {
  display: flex;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
}

.episode-date-primary {
  font-size: 0.9rem;
  font-weight: 600;
  color: #667eea;
  background: rgba(102, 126, 234, 0.1);
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  flex-shrink: 0;
}

.episode-context {
  font-size: 0.9rem;
  color: #333;
  line-height: 1.4;
  flex-grow: 1;
}

.no-results {
  padding: 3rem;
  text-align: center;
  color: #666;
}

.no-results-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
  opacity: 0.5;
}

.no-results h3 {
  margin-bottom: 1rem;
  color: #333;
}

.no-results p {
  margin-bottom: 0.5rem;
}

.suggestion {
  font-size: 0.9rem;
  color: #888;
}

.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 2rem;
  padding: 1.5rem;
  background: #f8f9fa;
  border-top: 1px solid #e9ecef;
}

.pagination-button {
  padding: 0.5rem 1rem;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.9rem;
  transition: all 0.2s ease;
}

.pagination-button:hover:not(:disabled) {
  background: #5568d3;
}

.pagination-button:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.pagination-info {
  font-weight: 500;
  color: #333;
}

/* Responsive */
@media (max-width: 768px) {
  .advanced-search-page {
    padding: 1rem;
  }

  .search-section {
    padding: 1rem;
  }

  .filter-checkboxes {
    flex-direction: column;
    gap: 0.75rem;
  }

  .pagination {
    flex-direction: column;
    gap: 1rem;
  }
}
</style>
