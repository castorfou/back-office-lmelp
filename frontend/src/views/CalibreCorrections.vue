<template>
  <div class="calibre-corrections-page">
    <!-- Navigation -->
    <Navigation pageTitle="Corrections Calibre" />

    <!-- Loading state -->
    <div v-if="loading" class="loading-state" data-test="loading">
      <div class="loading-spinner"></div>
      <span>Chargement des corrections Calibre...</span>
    </div>

    <!-- Error state -->
    <div v-else-if="error" class="error-state" data-test="error">
      <div class="error-icon">&#9888;</div>
      <span>{{ error }}</span>
      <button @click="$router.back()" class="btn-secondary">Retour</button>
    </div>

    <!-- Content -->
    <div v-else class="corrections-content" data-test="content">
      <!-- Page header -->
      <div class="corrections-header">
        <div class="header-title">
          <img :src="calibreIcon" alt="Calibre" class="header-icon" />
          <h1>Corrections Calibre</h1>
        </div>
        <span class="total-count" data-test="total-matches">
          {{ corrections.statistics.total_matches }} livres match&eacute;s
        </span>
      </div>

      <!-- Statistics (always visible, clickable cards) -->
      <div class="statistics-grid" data-test="statistics-grid">
        <div class="stat-card">
          <div class="stat-value" data-test="stat-total-matches">
            {{ corrections.statistics.total_matches }}
          </div>
          <div class="stat-label">Total matches</div>
        </div>
        <div class="stat-card stat-card-clickable" @click="scrollToSection('authors')" data-test="stat-authors-link">
          <div class="stat-value" data-test="stat-author-corrections">
            {{ corrections.statistics.total_author_corrections }}
          </div>
          <div class="stat-label">Corrections auteurs</div>
        </div>
        <div class="stat-card stat-card-clickable" @click="scrollToSection('titles')" data-test="stat-titles-link">
          <div class="stat-value" data-test="stat-title-corrections">
            {{ corrections.statistics.total_title_corrections }}
          </div>
          <div class="stat-label">Corrections titres</div>
        </div>
        <div class="stat-card stat-card-clickable" @click="scrollToSection('tags')" data-test="stat-tags-link">
          <div class="stat-value" data-test="stat-missing-tags">
            {{ corrections.statistics.total_missing_lmelp_tags }}
          </div>
          <div class="stat-label">Tags manquants</div>
        </div>
      </div>

      <!-- Section 1: Auteurs a corriger -->
      <div class="correction-section" ref="section-authors" data-test="section-authors">
        <div
          class="section-header"
          @click="toggleSection('authors')"
          data-test="section-authors-header"
        >
          <span class="section-toggle">{{ sections.authors ? '&#9660;' : '&#9654;' }}</span>
          <h2>Auteurs &agrave; corriger</h2>
          <span class="count-badge" data-test="authors-count">
            {{ corrections.author_corrections.length }}
          </span>
        </div>
        <div v-if="sections.authors" class="section-body">
          <div v-if="corrections.author_corrections.length === 0" class="empty-section">
            Aucune correction d'auteur n&eacute;cessaire.
          </div>
          <table v-else class="corrections-table">
            <thead>
              <tr>
                <th>Titre Calibre</th>
                <th>Auteur Calibre</th>
                <th>Auteur MongoDB (Babelio)</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="item in corrections.author_corrections"
                :key="'author-' + item.calibre_id"
                data-test="author-row"
              >
                <td>
                  <router-link
                    :to="{ name: 'LivreDetail', params: { id: item.mongo_livre_id } }"
                    class="livre-link"
                    data-test="author-livre-link"
                  >{{ item.calibre_title }}</router-link>
                </td>
                <td>
                  <span class="calibre-value">{{ formatAuthors(item.calibre_authors) }}</span>
                </td>
                <td>
                  <span class="mongodb-value">{{ item.mongodb_author }}</span>
                </td>
                <td>
                  <button
                    class="btn-copy"
                    @click="copyToClipboard(item.mongodb_author)"
                    title="Copier le nom de l'auteur MongoDB"
                    data-test="copy-author-btn"
                  >
                    Copier
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Section 2: Titres differents -->
      <div class="correction-section" ref="section-titles" data-test="section-titles">
        <div
          class="section-header"
          @click="toggleSection('titles')"
          data-test="section-titles-header"
        >
          <span class="section-toggle">{{ sections.titles ? '&#9660;' : '&#9654;' }}</span>
          <h2>Titres diff&eacute;rents</h2>
          <span class="count-badge" data-test="titles-count">
            {{ corrections.title_corrections.length }}
          </span>
        </div>
        <div v-if="sections.titles" class="section-body">
          <div v-if="corrections.title_corrections.length === 0" class="empty-section">
            Aucune diff&eacute;rence de titre d&eacute;tect&eacute;e.
          </div>
          <table v-else class="corrections-table">
            <thead>
              <tr>
                <th>Titre Calibre</th>
                <th>Titre MongoDB (Babelio)</th>
                <th>Auteur</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="item in corrections.title_corrections"
                :key="'title-' + item.calibre_id"
                data-test="title-row"
              >
                <td>{{ item.calibre_title }}</td>
                <td>
                  <router-link
                    :to="{ name: 'LivreDetail', params: { id: item.mongo_livre_id } }"
                    class="livre-link mongodb-value"
                    data-test="title-livre-link"
                  >{{ item.mongodb_title }}</router-link>
                </td>
                <td>{{ item.author }}</td>
                <td>
                  <button
                    class="btn-copy"
                    @click="copyToClipboard(item.mongodb_title)"
                    title="Copier le titre MongoDB"
                    data-test="copy-title-btn"
                  >
                    Copier
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Section 3: Tags lmelp_ manquants -->
      <div class="correction-section" ref="section-tags" data-test="section-tags">
        <div
          class="section-header"
          @click="toggleSection('tags')"
          data-test="section-tags-header"
        >
          <span class="section-toggle">{{ sections.tags ? '&#9660;' : '&#9654;' }}</span>
          <h2>Tags lmelp_ manquants</h2>
          <span class="count-badge" data-test="tags-count">
            {{ corrections.missing_lmelp_tags.length }}
          </span>
        </div>
        <div v-if="sections.tags" class="section-body">
          <div v-if="corrections.missing_lmelp_tags.length === 0" class="empty-section">
            Tous les livres ont un tag lmelp_.
          </div>
          <table v-else class="corrections-table">
            <thead>
              <tr>
                <th>Titre Calibre</th>
                <th>Tags manquants</th>
                <th>Auteur</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="item in corrections.missing_lmelp_tags"
                :key="'tag-' + item.calibre_id"
                data-test="tag-row"
              >
                <td>
                  <router-link
                    :to="{ name: 'LivreDetail', params: { id: item.mongo_livre_id } }"
                    class="livre-link"
                    data-test="tag-livre-link"
                  >{{ item.calibre_title }}</router-link>
                </td>
                <td>
                  <span
                    v-for="tag in item.expected_lmelp_tags"
                    :key="tag"
                    class="tag-chip tag-chip-missing"
                    data-test="missing-tag"
                  >
                    {{ tag }}
                  </span>
                  <span v-if="!item.expected_lmelp_tags || item.expected_lmelp_tags.length === 0" class="no-tags">
                    Aucun tag attendu
                  </span>
                </td>
                <td>{{ item.author }}</td>
                <td>
                  <button
                    class="btn-copy"
                    @click="copyToClipboard(formatTagsForCopy(item.all_tags_to_copy))"
                    title="Copier tous les tags pour Calibre"
                    data-test="copy-tags-btn"
                  >
                    Copier
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

    </div>
  </div>
</template>

<script>
import axios from 'axios';
import Navigation from '../components/Navigation.vue';
import calibreIcon from '../assets/calibre_logo.png';

export default {
  name: 'CalibreCorrections',

  components: {
    Navigation,
  },

  data() {
    return {
      corrections: {
        author_corrections: [],
        title_corrections: [],
        missing_lmelp_tags: [],
        statistics: {
          total_author_corrections: 0,
          total_title_corrections: 0,
          total_missing_lmelp_tags: 0,
          total_matches: 0,
        },
      },
      loading: true,
      error: null,
      calibreIcon: calibreIcon,
      sections: {
        authors: true,
        titles: true,
        tags: true,
      },
      copyFeedback: null,
    };
  },

  async mounted() {
    await this.loadCorrections();
  },

  methods: {
    async loadCorrections() {
      this.loading = true;
      this.error = null;

      try {
        const response = await axios.get('/api/calibre/corrections');
        this.corrections = response.data;
      } catch (err) {
        console.error('Erreur lors du chargement des corrections Calibre:', err);
        this.error = 'Une erreur est survenue lors du chargement des corrections Calibre.';
      } finally {
        this.loading = false;
      }
    },

    toggleSection(section) {
      this.sections[section] = !this.sections[section];
    },

    scrollToSection(section) {
      // Open the section if collapsed
      this.sections[section] = true;
      // Scroll to the section after DOM update
      this.$nextTick(() => {
        const el = this.$refs[`section-${section}`];
        if (el) {
          el.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      });
    },

    formatAuthors(authors) {
      if (!authors || authors.length === 0) return '';
      return authors.join(', ');
    },

    formatTagsForCopy(tags) {
      if (!tags || tags.length === 0) return '';
      return tags.join(', ');
    },

    async copyToClipboard(text) {
      try {
        await navigator.clipboard.writeText(text);
        this.copyFeedback = text;
        setTimeout(() => {
          this.copyFeedback = null;
        }, 2000);
        // Invalidate cache since user will correct this entry in Calibre
        await this.invalidateCache();
      } catch {
        // Fallback for environments without clipboard API
        console.warn('Clipboard API not available');
      }
    },

    async invalidateCache() {
      try {
        await axios.post('/api/calibre/cache/invalidate');
      } catch {
        // Cache invalidation is best-effort, don't show error
        console.warn('Cache invalidation failed');
      }
    },
  },
};
</script>

<style scoped>
.calibre-corrections-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 2rem 2rem;
}

.corrections-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1.5rem;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.header-icon {
  width: 32px;
  height: 32px;
  object-fit: contain;
}

.corrections-header h1 {
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

/* Sections */
.correction-section {
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  margin-bottom: 1rem;
  overflow: hidden;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem 1.25rem;
  cursor: pointer;
  user-select: none;
  background: #f8f9fa;
  border-bottom: 1px solid #e0e0e0;
  transition: background 0.2s;
}

.section-header:hover {
  background: #f0f2ff;
}

.section-toggle {
  font-size: 0.8rem;
  color: #888;
  min-width: 16px;
}

.section-header h2 {
  font-size: 1.1rem;
  color: #333;
  margin: 0;
  font-weight: 600;
}

.count-badge {
  background: #667eea;
  color: white;
  padding: 0.15rem 0.6rem;
  border-radius: 12px;
  font-size: 0.8rem;
  font-weight: 600;
  margin-left: auto;
}

.section-body {
  padding: 1rem 1.25rem;
}

.empty-section {
  color: #888;
  font-style: italic;
  padding: 0.5rem 0;
}

/* Tables */
.corrections-table {
  width: 100%;
  border-collapse: collapse;
}

.corrections-table thead {
  background: #f8f9fa;
}

.corrections-table th {
  padding: 0.7rem 1rem;
  text-align: left;
  font-weight: 600;
  color: #555;
  font-size: 0.85rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  border-bottom: 2px solid #e0e0e0;
}

.corrections-table td {
  padding: 0.6rem 1rem;
  border-bottom: 1px solid #f0f0f0;
  vertical-align: middle;
}

.corrections-table tbody tr:hover {
  background: #f8f9ff;
}

/* Values */
.calibre-value {
  color: #e67e22;
  font-weight: 500;
}

.mongodb-value {
  color: #27ae60;
  font-weight: 500;
}

.livre-link {
  color: #667eea;
  text-decoration: none;
}

.livre-link:hover {
  text-decoration: underline;
}

a.livre-link.mongodb-value {
  color: #27ae60;
}

/* Match badges */
.match-badge {
  display: inline-block;
  padding: 0.15rem 0.5rem;
  border-radius: 8px;
  font-size: 0.8rem;
  font-weight: 600;
}

.match-exact {
  background: #d4edda;
  color: #155724;
}

.match-containment {
  background: #fff3cd;
  color: #856404;
}

.match-author_validated {
  background: #d1ecf1;
  color: #0c5460;
}

/* Tag chips */
.tag-chip {
  display: inline-block;
  background: #e8e8e8;
  color: #555;
  padding: 0.15rem 0.5rem;
  border-radius: 6px;
  font-size: 0.8rem;
  margin: 0.1rem 0.2rem;
}

.tag-chip-missing {
  background: #fff3cd;
  color: #856404;
  border: 1px solid #ffc107;
}

.no-tags {
  color: #aaa;
  font-style: italic;
  font-size: 0.85rem;
}

/* Buttons */
.btn-copy {
  padding: 0.3rem 0.8rem;
  background: #f0f2ff;
  color: #667eea;
  border: 1px solid #667eea;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.8rem;
  font-weight: 500;
  transition: all 0.2s;
}

.btn-copy:hover {
  background: #667eea;
  color: white;
}

/* Statistics */
.statistics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.stat-card {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 1rem;
  text-align: center;
  border: 1px solid #e0e0e0;
}

.stat-card-clickable {
  cursor: pointer;
  transition: all 0.2s;
}

.stat-card-clickable:hover {
  background: #f0f2ff;
  border-color: #667eea;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.15);
}

.stat-value {
  font-size: 1.8rem;
  font-weight: 700;
  color: #667eea;
}

.stat-label {
  font-size: 0.85rem;
  color: #888;
  margin-top: 0.25rem;
}

/* Loading state */
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

/* Responsive */
@media (max-width: 768px) {
  .calibre-corrections-page {
    padding: 0 1rem 1rem;
  }

  .corrections-header {
    flex-direction: column;
    gap: 0.5rem;
    align-items: flex-start;
  }

  .corrections-table th,
  .corrections-table td {
    padding: 0.4rem 0.5rem;
    font-size: 0.85rem;
  }

  .statistics-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
