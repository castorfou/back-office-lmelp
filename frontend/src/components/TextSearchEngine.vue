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
        @keydown.esc="clearSearch"
      />
      <button
        v-if="searchQuery.length > 0"
        @click="clearSearch"
        class="clear-button"
        type="button"
        title="Effacer la recherche (ou appuyez sur Escape)"
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
            <li v-for="auteur in results.auteurs" :key="`auteur-${auteur.nom}`" class="result-item">
              <span class="result-name" v-html="highlightSearchTerm(auteur.nom)"></span>
            </li>
          </ul>
        </div>

        <!-- Livres -->
        <div v-if="results.livres.length > 0" class="result-category">
          <h4 class="category-title">📚 LIVRES ({{ results.livres.length }})</h4>
          <ul class="result-list">
            <li v-for="livre in results.livres" :key="`livre-${livre.titre}`" class="result-item">
              <span class="result-name" v-html="highlightSearchTerm(formatLivreDisplay(livre))"></span>
            </li>
          </ul>
        </div>

        <!-- Éditeurs -->
        <div v-if="results.editeurs.length > 0" class="result-category">
          <h4 class="category-title">🏢 ÉDITEURS ({{ results.editeurs.length }})</h4>
          <ul class="result-list">
            <li v-for="editeur in results.editeurs" :key="`editeur-${editeur.nom}`" class="result-item">
              <span class="result-name" v-html="highlightSearchTerm(editeur.nom)"></span>
            </li>
          </ul>
        </div>

        <!-- Épisodes -->
        <div v-if="results.episodes.length > 0" class="result-category">
          <h4 class="category-title">🎙️ ÉPISODES ({{ results.episodes.length }}/{{ results.episodes_total_count || results.episodes.length }})</h4>
          <ul class="result-list">
            <li v-for="episode in results.episodes" :key="`episode-${episode._id}`" class="result-item episode-item">
              <div class="episode-content">
                <div class="episode-main-info">
                  <span class="episode-date-primary">{{ formatDate(episode.date) }}</span>
                  <div class="episode-context" v-html="formatSearchContext(episode)"></div>
                </div>
              </div>
            </li>
          </ul>
        </div>

        <!-- Catégories vides - ne s'affichent plus pour économiser l'espace -->
        <div v-if="results.episodes.length === 0" class="result-category empty">
          <h4 class="category-title">🎙️ ÉPISODES (0)</h4>
          <p class="empty-message">(aucun épisode contenant "{{ lastSearchQuery }}")</p>
        </div>

        <!-- Lien vers recherche avancée -->
        <div class="advanced-search-link">
          <router-link :to="`/search?q=${encodeURIComponent(lastSearchQuery)}`" class="link-button">
            🔍 Voir tous les résultats avec la recherche avancée →
          </router-link>
        </div>
      </div>

      <!-- Aucun résultat -->
      <div v-else class="no-results">
        <div class="no-results-icon">🔍</div>
        <h3>Aucun résultat trouvé</h3>
        <p>Aucun contenu ne correspond à votre recherche "{{ lastSearchQuery }}"</p>
        <p class="suggestion">Essayez avec d'autres mots-clés ou vérifiez l'orthographe.</p>
        <router-link :to="`/search?q=${encodeURIComponent(lastSearchQuery)}`" class="link-button advanced-search-cta">
          🔍 Essayer la recherche avancée
        </router-link>
      </div>
    </div>
  </div>
</template>

<script>
import { searchService } from '../services/api.js';
import { highlightSearchTermAccentInsensitive } from '../utils/textUtils.js';

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
        episodes: [],
        episodes_total_count: 0
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

    formatLivreDisplay(livre) {
      // Format: "auteur_nom - titre" si auteur_nom existe, sinon juste "titre"
      if (livre.auteur_nom) {
        return `${livre.auteur_nom} - ${livre.titre}`;
      }
      return livre.titre;
    },

    highlightSearchTerm(text) {
      // Use accent-insensitive highlighting (Issue #92)
      return highlightSearchTermAccentInsensitive(text, this.lastSearchQuery);
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

    formatSearchContext(episode) {
      // Si on a un contexte de recherche du backend, l'utiliser
      if (episode.search_context && episode.search_context.trim()) {
        return this.highlightSearchTerm(episode.search_context);
      }

      const query = this.lastSearchQuery.trim().toLowerCase();

      // Chercher dans le titre d'abord
      if (episode.titre && episode.titre.toLowerCase().includes(query)) {
        return this.highlightSearchTerm(episode.titre);
      }

      // Chercher dans la description
      if (episode.description && episode.description.toLowerCase().includes(query)) {
        return this.createContextFromText(episode.description, query);
      }

      // Si le backend a retourné cet épisode avec un score > 0, c'est qu'il correspond
      if (episode.score && episode.score > 0) {
        return `Trouvé dans la transcription (recherche: "${this.lastSearchQuery}")`;
      }

      // Fallback final
      if (episode.titre) {
        return episode.titre;
      }

      return `Aucun contexte disponible`;
    },

    createContextFromText(text, query) {
      const textLower = text.toLowerCase();
      const queryIndex = textLower.indexOf(query);

      if (queryIndex === -1) return this.highlightSearchTerm(text);

      // Extraire environ 10 mots avant et après
      const words = text.split(' ');
      const allText = words.join(' ');

      // Trouver l'index du mot contenant la requête
      let wordIndex = 0;
      let charCount = 0;

      for (let i = 0; i < words.length; i++) {
        if (charCount + words[i].length >= queryIndex) {
          wordIndex = i;
          break;
        }
        charCount += words[i].length + 1; // +1 pour l'espace
      }

      // Prendre 10 mots avant et après
      const start = Math.max(0, wordIndex - 10);
      const end = Math.min(words.length, wordIndex + 11);

      let contextWords = words.slice(start, end);
      let context = contextWords.join(' ');

      // Ajouter des ellipses si nécessaire
      if (start > 0) context = '...' + context;
      if (end < words.length) context = context + '...';

      return this.highlightSearchTerm(context);
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
        episodes: [],
        episodes_total_count: 0
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

.episode-context {
  font-size: 0.9rem;
  color: #333;
  line-height: 1.4;
  flex-grow: 1;
  margin-left: 1rem;
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

.advanced-search-link {
  padding: 1.5rem;
  text-align: center;
  background: #f8f9fa;
  border-top: 1px solid #e9ecef;
}

.link-button {
  display: inline-block;
  padding: 0.75rem 1.5rem;
  background: #667eea;
  color: white;
  text-decoration: none;
  border-radius: 8px;
  font-weight: 500;
  transition: all 0.2s ease;
}

.link-button:hover {
  background: #5568d3;
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(102, 126, 234, 0.3);
}

.advanced-search-cta {
  margin-top: 1rem;
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
