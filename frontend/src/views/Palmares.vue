<template>
  <div class="palmares-page">
    <!-- Navigation -->
    <Navigation pageTitle="Palmarès" />

    <!-- État de chargement initial -->
    <div v-if="loading && items.length === 0" class="loading-state" data-test="loading">
      <div class="loading-spinner"></div>
      <span>Chargement du palmarès...</span>
    </div>

    <!-- Message d'erreur -->
    <div v-else-if="error" class="error-state" data-test="error">
      <div class="error-icon">⚠️</div>
      <span>{{ error }}</span>
      <button @click="$router.back()" class="btn-secondary">Retour</button>
    </div>

    <!-- Contenu du palmarès -->
    <div v-else class="palmares-content">
      <!-- En-tête avec total -->
      <div class="palmares-header">
        <h1>Palmarès des livres</h1>
        <div class="header-controls">
          <span
            class="filter-chip"
            :class="{ active: filterRead }"
            data-test="filter-read"
            @click="filterRead = !filterRead"
          >
            Lus
          </span>
          <span
            class="filter-chip"
            :class="{ active: filterUnread }"
            data-test="filter-unread"
            @click="filterUnread = !filterUnread"
          >
            Non lus
          </span>
          <span
            class="filter-chip"
            :class="{ active: filterInCalibre }"
            data-test="filter-in-calibre"
            @click="filterInCalibre = !filterInCalibre"
          >
            Dans Calibre
          </span>
          <span class="total-count" data-test="total-count">
            {{ filteredItems.length }} livres classés
          </span>
        </div>
      </div>

      <!-- Tableau -->
      <div class="palmares-table-container">
        <table class="palmares-table">
          <thead>
            <tr>
              <th class="col-rank">#</th>
              <th class="col-title">Livre</th>
              <th class="col-author">Auteur</th>
              <th class="col-note">Note</th>
              <th class="col-avis">Avis</th>
              <th class="col-calibre">Calibre</th>
              <th class="col-links">Liens</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(item, index) in filteredItems"
              :key="item.livre_id"
              class="palmares-row"
              data-test="palmares-row"
            >
              <td class="col-rank" data-test="palmares-rank">
                {{ index + 1 }}
              </td>
              <td class="col-title">
                <router-link
                  :to="`/livre/${item.livre_id}`"
                  class="livre-link"
                  data-test="livre-link"
                >
                  {{ item.titre }}
                </router-link>
              </td>
              <td class="col-author">
                <router-link
                  :to="`/auteur/${item.auteur_id}`"
                  class="auteur-link"
                  data-test="auteur-link"
                >
                  {{ item.auteur_nom }}
                </router-link>
              </td>
              <td class="col-note">
                <span
                  class="note-badge"
                  :class="noteClass(item.note_moyenne)"
                  data-test="note-badge"
                >
                  {{ item.note_moyenne.toFixed(1) }}
                </span>
              </td>
              <td class="col-avis">
                {{ item.nombre_avis }}
              </td>
              <td class="col-calibre" data-test="calibre-info">
                <div v-if="item.calibre_in_library" class="calibre-info">
                  <span class="calibre-badge in-library" title="Dans la bibliothèque Calibre">
                    {{ item.calibre_read ? '✓ Lu' : '◯' }}
                  </span>
                  <span
                    v-if="item.calibre_rating != null"
                    class="calibre-note"
                    :title="`Note Calibre: ${item.calibre_rating}/10`"
                  >
                    {{ item.calibre_rating }}/10
                  </span>
                </div>
                <span v-else class="calibre-badge not-in-library" title="Pas dans Calibre">
                  —
                </span>
              </td>
              <td class="col-links">
                <div class="links-container">
                  <!-- Lien Calibre -->
                  <router-link
                    :to="getCalibreUrl(item)"
                    class="external-link"
                    title="Rechercher dans Calibre"
                    data-test="calibre-link"
                  >
                    <img
                      :src="calibreIcon"
                      alt="Calibre"
                      class="link-icon"
                    />
                  </router-link>
                  <!-- Lien Anna's Archive -->
                  <a
                    :href="getAnnasArchiveUrl(item)"
                    target="_blank"
                    rel="noopener noreferrer"
                    class="external-link"
                    title="Rechercher sur Anna's Archive"
                    data-test="annas-archive-link"
                  >
                    <img
                      src="@/assets/annas-archive-icon.svg"
                      alt="Anna's Archive"
                      class="link-icon"
                    />
                  </a>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Sentinelle pour infinite scroll -->
      <div
        v-if="hasMore"
        ref="scrollSentinel"
        class="scroll-sentinel"
        data-test="scroll-sentinel"
      >
        <div v-if="loading" class="loading-more">
          <div class="loading-spinner-small"></div>
          <span>Chargement...</span>
        </div>
      </div>

      <!-- Fin de liste -->
      <div v-if="!hasMore && items.length > 0" class="end-of-list">
        Fin du palmarès
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios';
import Navigation from '../components/Navigation.vue';
import calibreIcon from '../assets/calibre_logo.png';

export default {
  name: 'Palmares',

  components: {
    Navigation,
  },

  data() {
    const saved = (() => {
      try {
        const raw = localStorage.getItem('palmares-filters');
        return raw ? JSON.parse(raw) : null;
      } catch {
        return null;
      }
    })();

    return {
      items: [],
      total: 0,
      currentPage: 0,
      totalPages: 0,
      pageSize: 30,
      loading: false,
      error: null,
      annasArchiveBaseUrl: 'https://fr.annas-archive.li',
      calibreIcon: calibreIcon,
      observer: null,
      filterRead: saved?.filterRead ?? true,
      filterUnread: saved?.filterUnread ?? true,
      filterInCalibre: saved?.filterInCalibre ?? true,
    };
  },

  watch: {
    filterRead() { this.saveFilters(); },
    filterUnread() { this.saveFilters(); },
    filterInCalibre() { this.saveFilters(); },
  },

  computed: {
    hasMore() {
      return this.currentPage < this.totalPages;
    },
    filteredItems() {
      return this.items.filter(item => {
        const isRead = item.calibre_read === true;
        const isInCalibre = item.calibre_in_library === true;

        // Determine item category
        if (isRead) {
          // Book is read (implies in Calibre)
          return this.filterRead && this.filterInCalibre;
        }
        if (isInCalibre) {
          // In Calibre but not read
          return this.filterUnread && this.filterInCalibre;
        }
        // Not in Calibre at all
        return this.filterUnread;
      });
    },
  },

  async mounted() {
    await Promise.all([
      this.loadMore(),
      this.loadAnnasArchiveUrl(),
    ]);
    this.setupIntersectionObserver();
  },

  beforeUnmount() {
    if (this.observer) {
      this.observer.disconnect();
      this.observer = null;
    }
  },

  methods: {
    async loadMore() {
      if (this.loading) return;
      if (this.currentPage >= this.totalPages && this.currentPage > 0) return;

      this.loading = true;
      const nextPage = this.currentPage + 1;

      try {
        const response = await axios.get('/api/palmares', {
          params: { page: nextPage, limit: this.pageSize },
        });

        const data = response.data;
        this.items = [...this.items, ...data.items];
        this.total = data.total;
        this.currentPage = data.page;
        this.totalPages = data.total_pages;
      } catch (err) {
        console.error('Erreur lors du chargement du palmarès:', err);
        if (this.items.length === 0) {
          this.error = 'Une erreur est survenue lors du chargement du palmarès';
        }
      } finally {
        this.loading = false;
      }
    },

    async loadAnnasArchiveUrl() {
      try {
        const response = await axios.get('/api/config/annas-archive-url');
        this.annasArchiveBaseUrl = response.data.url;
      } catch (err) {
        console.warn('Failed to load Anna\'s Archive URL, using default:', err);
      }
    },

    setupIntersectionObserver() {
      this.$nextTick(() => {
        const sentinel = this.$refs.scrollSentinel;
        if (!sentinel) return;

        try {
          this.observer = new IntersectionObserver(
            (entries) => {
              if (entries[0].isIntersecting && this.hasMore && !this.loading) {
                this.loadMore();
              }
            },
            { threshold: 0.1 }
          );

          if (this.observer && typeof this.observer.observe === 'function') {
            this.observer.observe(sentinel);
          }
        } catch {
          // IntersectionObserver not available (e.g., in tests)
        }
      });
    },

    noteClass(note) {
      if (note >= 9) return 'note-excellent';
      if (note >= 7) return 'note-good';
      if (note >= 5) return 'note-average';
      return 'note-poor';
    },

    getCalibreUrl(item) {
      const searchQuery = item.titre || '';
      return `/calibre?search=${encodeURIComponent(searchQuery)}`;
    },

    saveFilters() {
      try {
        localStorage.setItem('palmares-filters', JSON.stringify({
          filterRead: this.filterRead,
          filterUnread: this.filterUnread,
          filterInCalibre: this.filterInCalibre,
        }));
      } catch {
        // localStorage not available
      }
    },

    getAnnasArchiveUrl(item) {
      const titre = item.titre || '';
      const auteur = item.auteur_nom || '';
      const searchQuery = `${titre} - ${auteur}`;

      const encodedQuery = encodeURIComponent(searchQuery)
        .replace(/%20/g, '+')
        .replace(/'/g, '%27')
        .replace(/!/g, '%21');

      return `${this.annasArchiveBaseUrl}/search?index=&page=1&sort=&display=&q=${encodedQuery}`;
    },
  },
};
</script>

<style scoped>
.palmares-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 2rem 2rem;
}

.palmares-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1.5rem;
}

.palmares-header h1 {
  font-size: 1.5rem;
  color: #333;
  margin: 0;
}

.header-controls {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.total-count {
  background: #f0f2ff;
  color: #667eea;
  padding: 0.4rem 1rem;
  border-radius: 20px;
  font-size: 0.9rem;
  font-weight: 500;
}

/* Filter chips */
.filter-chip {
  background: #e8e8e8;
  color: #999;
  padding: 0.4rem 1rem;
  border-radius: 20px;
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  user-select: none;
  transition: background 0.2s, color 0.2s;
}

.filter-chip.active {
  background: #f0f2ff;
  color: #667eea;
}

.filter-chip:hover {
  opacity: 0.8;
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
.col-rank {
  width: 50px;
  text-align: center;
  font-weight: 700;
  color: #888;
  font-size: 0.95rem;
}

.col-title {
  min-width: 200px;
}

.col-author {
  min-width: 150px;
}

.col-note {
  width: 70px;
  text-align: center;
}

.col-avis {
  width: 60px;
  text-align: center;
  color: #888;
  font-size: 0.9rem;
}

.col-calibre {
  width: 90px;
  text-align: center;
}

.col-links {
  width: 80px;
  text-align: center;
}

/* Links */
.livre-link,
.auteur-link {
  color: #667eea;
  text-decoration: none;
  font-weight: 500;
  transition: color 0.2s;
}

.livre-link:hover,
.auteur-link:hover {
  color: #5a67d8;
  text-decoration: underline;
}

.links-container {
  display: flex;
  gap: 0.5rem;
  justify-content: center;
  align-items: center;
}

.external-link {
  display: flex;
  align-items: center;
  opacity: 0.7;
  transition: opacity 0.2s;
}

.external-link:hover {
  opacity: 1;
}

.link-icon {
  width: 20px;
  height: 20px;
  object-fit: contain;
}

/* Calibre info */
.calibre-info {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.2rem;
}

.calibre-badge {
  font-size: 0.8rem;
  font-weight: 500;
}

.calibre-badge.in-library {
  color: #00C851;
}

.calibre-badge.not-in-library {
  color: #ccc;
}

.calibre-note {
  font-size: 0.75rem;
  color: #888;
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

/* Loading states */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  padding: 3rem;
  color: #888;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #e0e0e0;
  border-top-color: #667eea;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.loading-spinner-small {
  width: 24px;
  height: 24px;
  border: 2px solid #e0e0e0;
  border-top-color: #667eea;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Error state */
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  padding: 3rem;
  color: #e74c3c;
}

.error-icon {
  font-size: 2rem;
}

.btn-secondary {
  padding: 0.5rem 1.5rem;
  background: #f0f0f0;
  border: 1px solid #ddd;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.9rem;
  color: #555;
}

.btn-secondary:hover {
  background: #e0e0e0;
}

/* Scroll sentinel */
.scroll-sentinel {
  padding: 2rem;
  text-align: center;
}

.loading-more {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  color: #888;
}

.end-of-list {
  text-align: center;
  padding: 1.5rem;
  color: #aaa;
  font-style: italic;
}

/* Responsive */
@media (max-width: 768px) {
  .palmares-page {
    padding: 0 1rem 1rem;
  }

  .palmares-header {
    flex-direction: column;
    gap: 0.5rem;
    align-items: flex-start;
  }

  .palmares-table th,
  .palmares-table td {
    padding: 0.5rem;
    font-size: 0.85rem;
  }

  .col-avis {
    display: none;
  }

  .col-rank {
    width: 35px;
  }
}
</style>
