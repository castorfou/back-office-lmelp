<template>
  <div class="search-engine">
    <!-- Zone de recherche -->
    <div class="search-input-container">
      <div class="search-icon">🔍</div>
      <input
        v-model="searchQuery"
        type="text"
        placeholder="Rechercher dans le contenu..."
        class="search-input"
        @input="handleSearchInput"
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
        <div class="results-header">
          <h3>Résultats pour "{{ lastSearchQuery }}" :</h3>
        </div>

        <!-- Auteurs -->
        <div v-if="results.auteurs.length > 0" class="result-category">
          <h4 class="category-title">👤 AUTEURS ({{ results.auteurs.length }})</h4>
          <ul class="result-list">
            <li v-for="auteur in results.auteurs" :key="`auteur-${auteur.nom}`" class="result-item" :title="auteur.nom">
              <span class="result-name" v-html="highlightSearchTerm(auteur.nom)"></span>
            </li>
          </ul>
        </div>

        <!-- Livres -->
        <div v-if="results.livres.length > 0" class="result-category">
          <h4 class="category-title">📚 LIVRES ({{ results.livres.length }})</h4>
          <ul class="result-list">
            <li v-for="livre in results.livres" :key="`livre-${livre.titre}`" class="result-item" :title="livre.titre">
              <span class="result-name" v-html="highlightSearchTerm(livre.titre)"></span>
            </li>
          </ul>
        </div>

        <!-- Éditeurs -->
        <div v-if="results.editeurs.length > 0" class="result-category">
          <h4 class="category-title">🏢 ÉDITEURS ({{ results.editeurs.length }})</h4>
          <ul class="result-list">
            <li v-for="editeur in results.editeurs" :key="`editeur-${editeur.nom}`" class="result-item" :title="editeur.nom">
              <span class="result-name" v-html="highlightSearchTerm(editeur.nom)"></span>
            </li>
          </ul>
        </div>

        <!-- Épisodes -->
        <div v-if="results.episodes.length > 0" class="result-category">
          <h4 class="category-title">🎙️ ÉPISODES ({{ results.episodes.length }})</h4>
          <ul class="result-list">
            <li v-for="episode in results.episodes" :key="`episode-${episode._id}`" class="result-item episode-item" :title="createEpisodeTooltip(episode)">
              <div class="episode-content">
                <div class="episode-main-info">
                  <span class="episode-date-primary">{{ formatDate(episode.date) }}</span>
                  <span class="episode-title" v-html="highlightSearchTerm(episode.titre)"></span>
                </div>
                <div v-if="episode.description" class="episode-description" v-html="highlightSearchTerm(truncateText(episode.description, 100))">
                </div>
              </div>
            </li>
          </ul>
        </div>

        <!-- Catégories vides -->
        <div v-if="results.auteurs.length === 0" class="result-category empty">
          <h4 class="category-title">👤 AUTEURS (0)</h4>
          <p class="empty-message">(aucun auteur contenant "{{ lastSearchQuery }}")</p>
        </div>

        <div v-if="results.livres.length === 0" class="result-category empty">
          <h4 class="category-title">📚 LIVRES (0)</h4>
          <p class="empty-message">(aucun livre contenant "{{ lastSearchQuery }}")</p>
        </div>

        <div v-if="results.editeurs.length === 0" class="result-category empty">
          <h4 class="category-title">🏢 ÉDITEURS (0)</h4>
          <p class="empty-message">(aucun éditeur contenant "{{ lastSearchQuery }}")</p>
        </div>

        <div v-if="results.episodes.length === 0" class="result-category empty">
          <h4 class="category-title">🎙️ ÉPISODES (0)</h4>
          <p class="empty-message">(aucun épisode contenant "{{ lastSearchQuery }}")</p>
        </div>
      </div>

      <!-- Aucun résultat -->
      <div v-else class="no-results">
        <div class="no-results-icon">🔍</div>
        <h3>Aucun résultat trouvé</h3>
        <p>Aucun contenu ne correspond à votre recherche "{{ lastSearchQuery }}"</p>
        <p class="suggestion">Essayez avec d'autres mots-clés ou vérifiez l'orthographe.</p>
      </div>
    </div>
  </div>
</template>

<script>
import { searchService } from '../services/api.js';

// Fonction debounce simple pour éviter d'ajouter lodash comme dépendance
function debounce(func, delay) {
  let timeoutId;
  return function (...args) {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => func.apply(this, args), delay);
  };
}

export default {
  name: 'TextSearchEngine',

  props: {
    limit: {
      type: Number,
      default: 10
    }
  },

  data() {
    return {
      searchQuery: '',
      lastSearchQuery: '',
      loading: false,
      error: null,
      results: {
        auteurs: [],
        livres: [],
        editeurs: [],
        episodes: []
      },
      showResults: false
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
    }
  },

  created() {
    // Debounce la fonction de recherche (300ms)
    this.debouncedSearch = debounce(this.performSearch, 300);
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

    async performSearch() {
      const query = this.searchQuery.trim();

      if (query.length < 3) {
        return;
      }

      this.loading = true;
      this.error = null;
      this.lastSearchQuery = query;

      try {
        const response = await searchService.search(query, this.limit);

        this.results = response.results;
        this.showResults = true;
      } catch (error) {
        console.error('Erreur lors de la recherche:', error);
        this.error = error.message || 'Une erreur est survenue';
        this.showResults = false;
      } finally {
        this.loading = false;
      }
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

    truncateText(text, maxLength) {
      if (!text || text.length <= maxLength) return text;
      return text.substring(0, maxLength) + '...';
    },

    highlightSearchTerm(text) {
      if (!text || !this.lastSearchQuery) return text;

      const query = this.lastSearchQuery.trim();
      if (query.length < 3) return text;

      // D'abord essayer la correspondance exacte
      const exactRegex = new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
      let highlightedText = text.replace(exactRegex, '<strong>$1</strong>');

      // Si pas de correspondance exacte, essayer une recherche floue simple
      if (highlightedText === text) {
        // Recherche floue : chercher des mots qui commencent par les mêmes lettres
        const queryLower = query.toLowerCase();
        const words = text.split(/(\s+)/); // Garder les espaces

        for (let i = 0; i < words.length; i++) {
          const word = words[i];
          if (word.trim().length < 3) continue;

          const wordLower = word.toLowerCase();

          // Vérifier plusieurs types de correspondances floues
          const queryStart = queryLower.substring(0, Math.min(4, queryLower.length));

          if (
            wordLower.includes(queryStart) ||  // contient le début
            wordLower.startsWith(queryLower.substring(0, 3)) ||  // commence par 3 lettres
            this.fuzzyMatch(queryLower, wordLower)  // correspondance floue avancée
          ) {
            words[i] = `<strong>${word}</strong>`;
          }
        }

        highlightedText = words.join('');
      }

      return highlightedText;
    },

    fuzzyMatch(query, word) {
      // Correspondance floue simple : vérifier si suffisamment de caractères correspondent
      if (query.length < 3 || word.length < 3) return false;

      const queryChars = query.split('');
      const wordChars = word.split('');

      let matches = 0;
      let queryIndex = 0;

      for (let i = 0; i < wordChars.length && queryIndex < queryChars.length; i++) {
        if (wordChars[i] === queryChars[queryIndex]) {
          matches++;
          queryIndex++;
        }
      }

      // Correspondance si au moins 60% des caractères de la requête sont trouvés dans l'ordre
      return matches >= Math.ceil(query.length * 0.6);
    },

    createEpisodeTooltip(episode) {
      let tooltip = `Titre complet: ${episode.titre}`;

      if (episode.description) {
        tooltip += `\n\nDescription complète: ${episode.description}`;
      }

      if (episode.search_context && episode.search_context.trim()) {
        tooltip += `\n\nContexte de recherche: ${episode.search_context}`;
      } else {
        tooltip += `\n\nContexte de recherche: Non disponible`;
      }

      return tooltip;
    },

    clearSearch() {
      this.searchQuery = '';
      this.showResults = false;
      this.error = null;
      this.loading = false;
      this.lastSearchQuery = '';
      this.results = {
        auteurs: [],
        livres: [],
        editeurs: [],
        episodes: []
      };
    }
  }
};
</script>

<style scoped>
.search-engine {
  max-width: 800px;
  margin: 0 auto;
}

.search-input-container {
  position: relative;
  margin-bottom: 1rem;
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
  padding: 1rem 3rem 1rem 3rem;
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

.clear-button:active {
  background: #e0e0e0;
}

.loading-state {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  gap: 1rem;
  color: #666;
}

.loading-spinner {
  width: 20px;
  height: 20px;
  border: 2px solid #f3f3f3;
  border-top: 2px solid #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.error-state {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
  gap: 0.5rem;
  background: #fee;
  border: 1px solid #fcc;
  border-radius: 8px;
  color: #c33;
}

.search-results {
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  overflow: hidden;
}

.results-header {
  padding: 1.5rem;
  background: #f8f9fa;
  border-bottom: 1px solid #e9ecef;
}

.results-header h3 {
  margin: 0;
  font-size: 1.2rem;
  color: #333;
}

.result-category {
  padding: 1.5rem;
  border-bottom: 1px solid #e9ecef;
}

.result-category:last-child {
  border-bottom: none;
}

.result-category.empty {
  padding: 1rem 1.5rem;
  opacity: 0.6;
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
  transition: background-color 0.2s ease;
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

/* Style pour les termes recherchés mis en évidence */
.result-name strong,
.episode-title strong,
.episode-description strong {
  background: #fff3cd;
  color: #856404;
  padding: 0.1rem 0.2rem;
  border-radius: 3px;
  font-weight: 700;
}

.result-score {
  font-size: 0.9rem;
  color: #667eea;
  font-weight: 600;
  background: rgba(102, 126, 234, 0.1);
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
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

.episode-title {
  font-weight: 600;
  color: #333;
  flex-grow: 1;
}

.episode-description {
  font-size: 0.85rem;
  color: #666;
  line-height: 1.4;
  margin-top: 0.25rem;
}

.empty-message {
  margin: 0;
  color: #666;
  font-style: italic;
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

/* Responsive */
@media (max-width: 768px) {
  .search-engine {
    margin: 0 -1rem;
  }

  .search-input {
    font-size: 16px; /* Évite le zoom sur iOS */
  }

  .result-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.5rem;
  }

  .result-score {
    align-self: flex-end;
  }

  .episode-item {
    flex-direction: row;
    align-items: center;
  }

  .episode-item .result-score {
    align-self: center;
  }
}
</style>
