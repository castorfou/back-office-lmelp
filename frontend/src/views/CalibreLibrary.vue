<template>
  <div class="calibre-library">
    <!-- Navigation -->
    <Navigation pageTitle="Bibliothèque Calibre" />

    <!-- Message d'erreur -->
    <div v-if="error" class="error-message">
      <strong>Erreur:</strong> {{ error }}
    </div>

    <!-- Calibre non disponible -->
    <div v-if="!calibreStatus.available && !loading" class="unavailable-message">
      <div class="unavailable-card">
        <div class="icon">⚠️</div>
        <h2>Calibre non disponible</h2>
        <p v-if="calibreStatus.error">{{ calibreStatus.error }}</p>
        <p v-else>Le service Calibre n'est pas configuré.</p>
        <div class="help-text">
          <p>Pour activer l'intégration Calibre, configurez la variable d'environnement :</p>
          <code>CALIBRE_LIBRARY_PATH=/chemin/vers/bibliothèque</code>
        </div>
      </div>
    </div>

    <!-- Calibre disponible -->
    <div v-if="calibreStatus.available && !loading" class="calibre-content">
      <!-- Barre de recherche -->
      <section class="search-section">
        <input
          v-model="searchText"
          data-testid="search-input"
          type="text"
          class="search-input"
          placeholder="Rechercher par titre ou auteur..."
        />
      </section>

      <!-- Filtres de statut lecture -->
      <section class="filters">
        <button
          data-testid="filter-all"
          :class="['filter-btn', { active: readFilter === null }]"
          @click="setReadFilter(null)"
        >
          Tous ({{ calibreStatus.total_books }})
        </button>
        <button
          data-testid="filter-read"
          :class="['filter-btn', { active: readFilter === true }]"
          @click="setReadFilter(true)"
        >
          Lus<span v-if="calibreStatistics.books_read !== null"> ({{ calibreStatistics.books_read }})</span>
        </button>
        <button
          data-testid="filter-unread"
          :class="['filter-btn', { active: readFilter === false }]"
          @click="setReadFilter(false)"
        >
          Non lus<span v-if="booksUnread !== null"> ({{ booksUnread }})</span>
        </button>
      </section>

      <!-- Boutons de tri -->
      <section class="sort-section">
        <label>Trier par :</label>
        <button
          data-testid="sort-date-added"
          :class="['sort-btn', { active: sortBy === 'date-added' }]"
          @click="setSortBy('date-added')"
        >
          Derniers ajoutés
        </button>
        <button
          data-testid="sort-title-az"
          :class="['sort-btn', { active: sortBy === 'title-az' }]"
          @click="setSortBy('title-az')"
        >
          Titre A→Z
        </button>
        <button
          data-testid="sort-title-za"
          :class="['sort-btn', { active: sortBy === 'title-za' }]"
          @click="setSortBy('title-za')"
        >
          Titre Z→A
        </button>
        <button
          data-testid="sort-author-az"
          :class="['sort-btn', { active: sortBy === 'author-az' }]"
          @click="setSortBy('author-az')"
        >
          Auteur A→Z
        </button>
        <button
          data-testid="sort-author-za"
          :class="['sort-btn', { active: sortBy === 'author-za' }]"
          @click="setSortBy('author-za')"
        >
          Auteur Z→A
        </button>
      </section>

      <!-- Compteur de livres affichés -->
      <div class="books-count">
        <span v-if="filteredBooks.length === allBooks.length">
          {{ allBooks.length }} livres au total
        </span>
        <span v-else>
          {{ filteredBooks.length }} livre{{ filteredBooks.length > 1 ? 's' : '' }} affiché{{ filteredBooks.length > 1 ? 's' : '' }} sur {{ allBooks.length }}
        </span>
      </div>

      <!-- Liste des livres -->
      <section v-if="filteredBooks.length > 0" class="books-section">
        <div data-testid="books-list" class="books-grid">
          <div
            v-for="book in filteredBooks"
            :key="book.id"
            data-testid="book-card"
            class="book-card"
          >
            <div class="book-header">
              <h3 class="book-title" v-html="highlightText(book.title, searchText)"></h3>
              <span v-if="book.read !== null" class="read-badge" :class="{ read: book.read }">
                {{ book.read ? '✓ Lu' : '◯ Non lu' }}
              </span>
            </div>
            <p class="book-authors" v-html="highlightText(book.authors.join(', '), searchText)"></p>
            <div class="book-details">
              <span v-if="book.isbn" class="detail">ISBN: {{ book.isbn }}</span>
              <span v-if="book.publisher" class="detail">Éditeur: {{ book.publisher }}</span>
              <span v-if="book.rating" class="detail">
                Note: {{ book.rating / 2 }}/5 ⭐
              </span>
            </div>
            <div v-if="book.tags && book.tags.length > 0" class="book-tags">
              <span v-for="tag in book.tags" :key="tag" class="tag">{{ tag }}</span>
            </div>
          </div>
        </div>
      </section>

      <!-- Aucun livre trouvé -->
      <div v-if="filteredBooks.length === 0 && allBooks.length > 0" class="no-books">
        <p>Aucun livre trouvé avec les filtres sélectionnés.</p>
      </div>
    </div>

    <!-- Chargement -->
    <div v-if="loading" class="loading">
      <p>Chargement...</p>
    </div>
  </div>
</template>

<script>
import { calibreService } from '../services/api.js';
import { highlightSearchTermAccentInsensitive, removeAccents } from '../utils/textUtils.js';
import Navigation from '../components/Navigation.vue';

export default {
  name: 'CalibreLibrary',

  components: {
    Navigation
  },

  data() {
    return {
      loading: true,
      error: null,
      calibreStatus: {
        available: false,
        library_path: null,
        total_books: null,
        virtual_library_tag: null,
        custom_columns: {},
        error: null
      },
      calibreStatistics: {
        books_read: null
      },
      allBooks: [],  // All books loaded at once
      searchText: '',
      readFilter: null,
      sortBy: 'date-added' // Default sort
    };
  },

  computed: {
    booksUnread() {
      if (this.calibreStatistics.books_read !== null && this.calibreStatus.total_books !== null) {
        return this.calibreStatus.total_books - this.calibreStatistics.books_read;
      }
      return null;
    },

    filteredBooks() {
      let result = [...this.allBooks];

      // Apply read filter
      if (this.readFilter !== null) {
        if (this.readFilter === false) {
          // For "unread" filter, include books with read === false OR read === null
          result = result.filter(book => book.read === false || book.read === null);
        } else {
          // For "read" filter, only include books with read === true
          result = result.filter(book => book.read === true);
        }
      }

      // Apply search filter (case-insensitive, accent-insensitive, typographic-insensitive)
      // Issue #173: Support for typographic characters (œ, –, ')
      if (this.searchText.trim()) {
        const search = removeAccents(this.searchText.toLowerCase().trim());
        result = result.filter(book => {
          const titleNormalized = removeAccents(book.title?.toLowerCase() || '');
          const authorsNormalized = book.authors?.map(a => removeAccents(a.toLowerCase())) || [];

          const titleMatch = titleNormalized.includes(search);
          const authorMatch = authorsNormalized.some(author => author.includes(search));

          return titleMatch || authorMatch;
        });
      }

      // Apply sorting
      result = this.sortBooks(result);

      return result;
    }
  },

  async mounted() {
    await this.loadCalibreStatus();
    if (this.calibreStatus.available) {
      await Promise.all([
        this.loadAllBooks(),
        this.loadCalibreStatistics()
      ]);
    }
  },

  methods: {
    async loadCalibreStatus() {
      try {
        this.loading = true;
        this.error = null;
        const status = await calibreService.getStatus();
        this.calibreStatus = status;
      } catch (err) {
        console.error('Erreur lors du chargement du statut Calibre:', err);
        this.error = err.message;
        this.calibreStatus.available = false;
      } finally {
        this.loading = false;
      }
    },

    async loadCalibreStatistics() {
      try {
        const stats = await calibreService.getStatistics();
        this.calibreStatistics = stats;
      } catch (err) {
        console.error('Erreur lors du chargement des statistiques Calibre:', err);
        // Les statistiques ne sont pas critiques, on ne bloque pas l'affichage
      }
    },

    async loadAllBooks() {
      try {
        this.loading = true;
        this.error = null;

        // Load ALL books at once with a large limit
        const result = await calibreService.getBooks({ limit: 10000, offset: 0 });
        this.allBooks = result.books;
      } catch (err) {
        console.error('Erreur lors du chargement des livres:', err);
        this.error = err.message;
      } finally {
        this.loading = false;
      }
    },

    setReadFilter(value) {
      this.readFilter = value;
    },

    setSortBy(sortType) {
      this.sortBy = sortType;
    },

    sortBooks(books) {
      const sorted = [...books];

      switch (this.sortBy) {
        case 'title-az':
          return sorted.sort((a, b) => a.title.localeCompare(b.title));

        case 'title-za':
          return sorted.sort((a, b) => b.title.localeCompare(a.title));

        case 'author-az':
          return sorted.sort((a, b) => {
            const authorA = a.authors?.[0] || '';
            const authorB = b.authors?.[0] || '';
            return authorA.localeCompare(authorB);
          });

        case 'author-za':
          return sorted.sort((a, b) => {
            const authorA = a.authors?.[0] || '';
            const authorB = b.authors?.[0] || '';
            return authorB.localeCompare(authorA);
          });

        case 'date-added':
          // Most recent first (descending)
          return sorted.sort((a, b) => {
            if (!a.timestamp) return 1;
            if (!b.timestamp) return -1;
            return new Date(b.timestamp) - new Date(a.timestamp);
          });

        default:
          return sorted;
      }
    },

    highlightText(text, searchTerm) {
      // Use accent-insensitive highlighting (same as TextSearchEngine)
      return highlightSearchTermAccentInsensitive(text, searchTerm || this.searchText);
    }
  }
};
</script>

<style scoped>
.calibre-library {
  min-height: 100vh;
  padding: 2rem;
}

/* Messages */
.error-message {
  background: #fee;
  border: 1px solid #fcc;
  padding: 1rem;
  border-radius: 8px;
  margin-bottom: 2rem;
  color: #c33;
}

.unavailable-message {
  display: flex;
  justify-content: center;
  padding: 3rem 0;
}

.unavailable-card {
  background: white;
  padding: 3rem;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  text-align: center;
  max-width: 600px;
}

.unavailable-card .icon {
  font-size: 4rem;
  margin-bottom: 1rem;
}

.unavailable-card h2 {
  color: #333;
  margin-bottom: 1rem;
}

.help-text {
  margin-top: 2rem;
  text-align: left;
  background: #f5f5f5;
  padding: 1rem;
  border-radius: 8px;
}

.help-text code {
  display: block;
  background: #333;
  color: #0f0;
  padding: 0.5rem;
  margin-top: 0.5rem;
  border-radius: 4px;
  font-family: monospace;
}

/* Barre de recherche */
.search-section {
  margin-bottom: 1.5rem;
}

.search-input {
  width: 100%;
  padding: 0.75rem 1rem;
  font-size: 1rem;
  border: 2px solid #ddd;
  border-radius: 8px;
  transition: border-color 0.2s ease;
}

.search-input:focus {
  outline: none;
  border-color: #667eea;
}

/* Filtres de statut lecture */
.filters {
  display: flex;
  gap: 1rem;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
}

.filter-btn {
  padding: 0.75rem 1.5rem;
  border: 2px solid #ddd;
  background: white;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 1rem;
}

.filter-btn:hover {
  border-color: #667eea;
  background: #f5f7ff;
}

.filter-btn.active {
  background: #667eea;
  color: white;
  border-color: #667eea;
}

/* Boutons de tri */
.sort-section {
  display: flex;
  gap: 0.75rem;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
  align-items: center;
}

.sort-section label {
  font-weight: 600;
  color: #555;
}

.sort-btn {
  padding: 0.5rem 1rem;
  border: 1px solid #ddd;
  background: white;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 0.9rem;
}

.sort-btn:hover {
  border-color: #667eea;
  background: #f5f7ff;
}

.sort-btn.active {
  background: #667eea;
  color: white;
  border-color: #667eea;
}

/* Compteur de livres */
.books-count {
  margin-bottom: 1.5rem;
  padding: 0.75rem 1rem;
  background: #f5f7ff;
  border-radius: 6px;
  color: #555;
  font-size: 0.95rem;
}

/* Books grid */
.books-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.book-card {
  background: white;
  padding: 1.5rem;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.book-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(0,0,0,0.15);
}

.book-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 0.5rem;
}

.book-title {
  font-size: 1.2rem;
  color: #333;
  margin: 0;
  flex: 1;
}

.read-badge {
  background: #e0e0e0;
  color: #666;
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  font-size: 0.85rem;
  white-space: nowrap;
}

.read-badge.read {
  background: #d4edda;
  color: #155724;
}

.book-authors {
  color: #666;
  font-size: 0.95rem;
  margin: 0.5rem 0;
}

.book-details {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  margin: 1rem 0;
  font-size: 0.9rem;
  color: #555;
}

.book-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 1rem;
}

.tag {
  background: #f0f0f0;
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  font-size: 0.85rem;
  color: #666;
}

.no-books {
  text-align: center;
  padding: 3rem;
  color: #666;
}

.loading {
  text-align: center;
  padding: 3rem;
  font-size: 1.2rem;
  color: #666;
}

/* Responsive */
@media (max-width: 768px) {
  .page-header {
    padding: 2rem 1rem;
  }

  .page-header h1 {
    font-size: 2rem;
  }

  .books-grid {
    grid-template-columns: 1fr;
  }

  .library-info {
    flex-direction: column;
  }

  .filters {
    flex-direction: column;
  }

  .filter-btn {
    width: 100%;
  }
}
</style>
