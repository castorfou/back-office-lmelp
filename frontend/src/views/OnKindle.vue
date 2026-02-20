<template>
  <div class="onkindle-page">
    <!-- Navigation -->
    <Navigation pageTitle="OnKindle" />

    <!-- Chargement -->
    <div v-if="loading" class="loading" data-test="loading">
      <p>Chargement...</p>
    </div>

    <!-- Calibre non disponible -->
    <div v-else-if="calibreUnavailable" class="unavailable-message">
      <div class="unavailable-card">
        <div class="icon">⚠️</div>
        <h2>Calibre non disponible</h2>
        <p>Le service Calibre n'est pas configuré ou accessible.</p>
      </div>
    </div>

    <!-- Erreur -->
    <div v-else-if="error" class="error-message" data-test="error">
      <strong>Erreur:</strong> {{ error }}
    </div>

    <!-- Contenu -->
    <div v-else class="onkindle-content">
      <div class="onkindle-header">
        <h1>Livres OnKindle</h1>
        <span class="total-count">{{ books.length }} livre{{ books.length > 1 ? 's' : '' }}</span>
      </div>

      <!-- Tableau -->
      <div v-if="books.length > 0" class="palmares-table-container">
        <table class="palmares-table">
          <thead>
            <tr>
              <th
                class="col-auteur sort-header"
                :class="{ 'sort-active': sortKey === 'auteur' }"
                data-test="sort-auteur"
                @click="sortBy('auteur')"
              >
                Auteur <span class="sort-icon">{{ sortKey === 'auteur' ? (sortDir === 'asc' ? '▲' : '▼') : '⇅' }}</span>
              </th>
              <th
                class="col-titre sort-header"
                :class="{ 'sort-active': sortKey === 'titre' }"
                data-test="sort-titre"
                @click="sortBy('titre')"
              >
                Titre <span class="sort-icon">{{ sortKey === 'titre' ? (sortDir === 'asc' ? '▲' : '▼') : '⇅' }}</span>
              </th>
              <th
                class="col-note sort-header"
                :class="{ 'sort-active': sortKey === 'note' }"
                data-test="sort-note"
                @click="sortBy('note')"
              >
                Note <span class="sort-icon">{{ sortKey === 'note' ? (sortDir === 'asc' ? '▲' : '▼') : '⇅' }}</span>
              </th>
              <th class="col-babelio">Babelio</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="book in sortedBooks"
              :key="book.calibre_id"
              data-test="onkindle-row"
              class="palmares-row"
            >
              <!-- Auteur -->
              <td class="col-auteur">
                <router-link
                  v-if="book.auteur_id"
                  :to="`/auteur/${book.auteur_id}`"
                  data-test="auteur-link"
                  class="author-link"
                >{{ book.auteurs && book.auteurs[0] || '' }}</router-link>
                <span v-else data-test="auteur-plain" class="auteur-plain">{{ book.auteurs && book.auteurs[0] || '' }}</span>
              </td>

              <!-- Titre -->
              <td class="col-titre">
                <router-link
                  v-if="book.mongo_livre_id"
                  :to="`/livre/${book.mongo_livre_id}`"
                  data-test="titre-link"
                  class="book-link"
                ><strong>{{ book.titre }}</strong></router-link>
                <strong v-else data-test="titre-plain" class="titre-plain">{{ book.titre }}</strong>
              </td>

              <!-- Note -->
              <td class="col-note">
                <span
                  v-if="book.note_moyenne != null"
                  class="note-badge"
                  :class="noteClass(book.note_moyenne)"
                  data-test="note-badge"
                >
                  {{ book.note_moyenne.toFixed(1) }}
                </span>
                <span v-else class="note-missing" data-test="note-missing">-</span>
              </td>

              <!-- Babelio -->
              <td class="col-babelio">
                <a
                  v-if="book.url_babelio"
                  :href="book.url_babelio"
                  target="_blank"
                  rel="noopener noreferrer"
                  data-test="babelio-link"
                  class="babelio-icon-link"
                  title="Voir sur Babelio"
                >
                  <img
                    src="@/assets/babelio-symbol-liaison.svg"
                    alt="Babelio"
                    class="babelio-icon"
                  />
                </a>
                <span v-else data-test="babelio-missing" class="babelio-missing">-</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Aucun livre -->
      <div v-else class="no-books">
        <p>Aucun livre avec le tag "onkindle" dans Calibre.</p>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios';
import Navigation from '../components/Navigation.vue';

export default {
  name: 'OnKindle',

  components: {
    Navigation,
  },

  data() {
    return {
      loading: true,
      error: null,
      calibreUnavailable: false,
      books: [],
      sortKey: 'titre',
      sortDir: 'asc',
    };
  },

  created() {
    const { sort, dir } = this.$route.query;
    if (sort && ['titre', 'auteur', 'note'].includes(sort)) {
      this.sortKey = sort;
    }
    if (dir && ['asc', 'desc'].includes(dir)) {
      this.sortDir = dir;
    }
  },

  computed: {
    sortedBooks() {
      const sorted = [...this.books];
      sorted.sort((a, b) => {
        if (this.sortKey === 'note') {
          const valA = a.note_moyenne ?? -Infinity;
          const valB = b.note_moyenne ?? -Infinity;
          if (valA < valB) return this.sortDir === 'asc' ? -1 : 1;
          if (valA > valB) return this.sortDir === 'asc' ? 1 : -1;
          return 0;
        }
        const strA = this.sortKey === 'titre'
          ? (a.titre || '')
          : ((a.auteurs && a.auteurs[0]) || '');
        const strB = this.sortKey === 'titre'
          ? (b.titre || '')
          : ((b.auteurs && b.auteurs[0]) || '');
        const cmp = strA.localeCompare(strB, 'fr', { sensitivity: 'base' });
        return this.sortDir === 'asc' ? cmp : -cmp;
      });
      return sorted;
    },
  },

  async mounted() {
    await this.loadOnKindleBooks();
  },

  methods: {
    async sortBy(key) {
      if (this.sortKey === key) {
        this.sortDir = this.sortDir === 'asc' ? 'desc' : 'asc';
      } else {
        this.sortKey = key;
        this.sortDir = key === 'note' ? 'desc' : 'asc';
      }
      await this.$router.replace({
        query: { sort: this.sortKey, dir: this.sortDir },
      });
    },

    async loadOnKindleBooks() {
      try {
        this.loading = true;
        this.error = null;
        this.calibreUnavailable = false;

        const response = await axios.get('/api/calibre/onkindle');
        this.books = response.data.books || [];
      } catch (err) {
        if (err.response && err.response.status === 503) {
          this.calibreUnavailable = true;
        } else {
          this.error = err.message || 'Erreur lors du chargement des livres Calibre';
        }
      } finally {
        this.loading = false;
      }
    },

    noteClass(note) {
      if (note >= 9) return 'note-excellent';
      if (note >= 7) return 'note-good';
      if (note >= 5) return 'note-average';
      return 'note-poor';
    },
  },
};
</script>

<style scoped>
.onkindle-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 2rem 2rem;
}

.loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  padding: 3rem;
  color: #888;
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
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  text-align: center;
  max-width: 600px;
}

.unavailable-card .icon {
  font-size: 4rem;
  margin-bottom: 1rem;
}

.error-message {
  background: #fee;
  border: 1px solid #fcc;
  padding: 1rem;
  border-radius: 8px;
  margin-bottom: 2rem;
  color: #c33;
}

.onkindle-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.onkindle-header h1 {
  font-size: 1.5rem;
  color: #333;
  margin: 0;
}

.total-count {
  background: #f0f2ff;
  color: #667eea;
  padding: 0.4rem 1rem;
  border-radius: 20px;
  font-size: 0.9rem;
  font-weight: 500;
}

/* Sort headers */
.sort-header {
  cursor: pointer;
  user-select: none;
  white-space: nowrap;
}

.sort-header:hover {
  background: #eef0f5;
}

.sort-active {
  color: #667eea;
}

.sort-icon {
  font-size: 0.75rem;
  margin-left: 0.3rem;
  opacity: 0.6;
}

.sort-active .sort-icon {
  opacity: 1;
}

/* Table */
.palmares-table-container {
  overflow-x: auto;
}

.palmares-table {
  width: 100%;
  border-collapse: collapse;
  background: white;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.palmares-table thead {
  background: #f8f9fa;
}

.palmares-table th {
  padding: 0.8rem 1rem;
  text-align: left;
  font-weight: 600;
  color: #555;
  font-size: 0.85rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  border-bottom: 2px solid #e0e0e0;
}

.palmares-table td {
  padding: 0.7rem 1rem;
  border-bottom: 1px solid #f0f0f0;
  vertical-align: middle;
}

.palmares-row:hover {
  background: #f8f9ff;
}

/* Columns */
.col-auteur {
  min-width: 150px;
}

.col-titre {
  min-width: 200px;
}

.col-note {
  width: 70px;
  text-align: center;
}

.col-babelio {
  width: 80px;
  text-align: center;
}

/* Links — style Emissions */
.author-link,
.book-link {
  color: #0066cc;
  text-decoration: none;
}

.author-link:hover,
.book-link:hover {
  text-decoration: underline;
}

.auteur-plain,
.titre-plain {
  color: #444;
}

/* Note badges */
.note-badge {
  display: inline-block;
  padding: 0.2rem 0.5rem;
  border-radius: 8px;
  font-weight: 700;
  font-size: 0.85rem;
  color: white;
  min-width: 35px;
  text-align: center;
}

.note-excellent {
  background-color: #00C851;
}

.note-good {
  background-color: #8BC34A;
}

.note-average {
  background-color: #CDDC39;
  color: #333;
}

.note-poor {
  background-color: #F44336;
}

.note-missing,
.babelio-missing {
  color: #ccc;
}

/* Babelio icon */
.babelio-icon-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  opacity: 0.85;
  transition: opacity 0.2s, transform 0.2s;
}

.babelio-icon-link:hover {
  opacity: 1;
  transform: scale(1.1);
}

.babelio-icon {
  width: 24px;
  height: 24px;
  border-radius: 4px;
}

.no-books {
  text-align: center;
  padding: 3rem;
  color: #666;
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}
</style>
