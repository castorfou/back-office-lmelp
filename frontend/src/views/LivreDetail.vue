<template>
  <div class="livre-detail-page">
    <!-- Navigation -->
    <Navigation pageTitle="Détail du livre" />

    <!-- État de chargement -->
    <div v-if="loading" class="loading-state" data-test="loading">
      <div class="loading-spinner"></div>
      <span>Chargement des informations du livre...</span>
    </div>

    <!-- Message d'erreur -->
    <div v-else-if="error" class="error-state" data-test="error">
      <div class="error-icon">⚠️</div>
      <span>{{ error }}</span>
      <button @click="$router.back()" class="btn-secondary">
        Retour
      </button>
    </div>

    <!-- Contenu du livre -->
    <div v-else-if="livre" class="livre-content">
      <!-- En-tête livre -->
      <div class="livre-header">
        <div class="livre-header-container">
          <!-- Icônes externes à gauche -->
          <div class="external-links">
            <!-- Icône Babelio (Issue #124) -->
            <a
              v-if="livre.url_babelio"
              :href="livre.url_babelio"
              target="_blank"
              rel="noopener noreferrer"
              class="external-logo-link"
              title="Voir sur Babelio"
            >
              <img
                src="@/assets/babelio-symbol-liaison.svg"
                alt="Icône Babelio"
                class="external-logo"
              />
            </a>

            <!-- Icône Anna's Archive (Issue #165) -->
            <a
              :href="getAnnasArchiveUrl()"
              target="_blank"
              rel="noopener noreferrer"
              class="external-logo-link"
              title="Rechercher sur Anna's Archive"
              data-test="annas-archive-link"
            >
              <img
                src="@/assets/annas-archive-icon.svg"
                alt="Icône Anna's Archive"
                class="external-logo"
                data-test="annas-archive-icon"
              />
            </a>
          </div>

          <!-- Informations du livre à droite -->
          <div class="livre-info">
            <div class="livre-title-row">
              <h1 class="livre-title">{{ livre.titre }}</h1>
              <span
                v-if="livre.note_moyenne != null"
                class="note-badge"
                :class="noteClass(livre.note_moyenne)"
                data-test="note-moyenne-globale"
              >
                {{ livre.note_moyenne.toFixed(1) }}
              </span>
            </div>
            <div class="livre-meta">
              <div class="livre-author">
                Auteur :
                <router-link
                  :to="`/auteur/${livre.auteur_id}`"
                  class="author-link"
                  data-test="auteur-link"
                >
                  {{ livre.auteur_nom }}
                </router-link>
              </div>
              <div class="livre-publisher">Éditeur : {{ livre.editeur }}</div>
            </div>
            <div class="livre-stats">
              <span class="stat-badge">
                {{ livre.nombre_emissions }} émission{{ livre.nombre_emissions > 1 ? 's' : '' }}
              </span>
              <!-- Tags Calibre (Issue #200) -->
              <span
                v-if="livre.calibre_tags && livre.calibre_tags.length > 0"
                class="tags-section"
                data-test="tags-section"
              >
                <span
                  v-for="tag in livre.calibre_tags"
                  :key="tag"
                  class="tag-badge"
                  data-test="tag-badge"
                >{{ tag }}</span>
                <button
                  @click="copyTags"
                  class="copy-tags-btn"
                  :title="tagsCopied ? 'Copié !' : 'Copier les tags'"
                  data-test="copy-tags-btn"
                >
                  {{ tagsCopied ? '✓' : '📋' }}
                </button>
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- Liste des émissions (Issue #190) -->
      <section class="emissions-section">
        <h2>Émissions présentant "{{ livre.titre }}"</h2>

        <!-- Message si aucune émission -->
        <div v-if="livre.emissions.length === 0" class="empty-state">
          <p>Aucune émission trouvée pour ce livre</p>
        </div>

        <!-- Liste des émissions -->
        <div v-else class="emissions-list">
          <div
            v-for="emission in livre.emissions"
            :key="emission.emission_id"
            class="emission-card"
            data-test="emission-item"
          >
            <div class="emission-info">
              <router-link
                :to="`/emissions/${formatDateForUrl(emission.date)}`"
                class="emission-date-link"
                data-test="emission-link"
              >
                <h3 class="emission-date-title">{{ formatDate(emission.date) }}</h3>
              </router-link>
              <p class="emission-avis-count">{{ emission.nombre_avis }} avis</p>
            </div>
            <span
              v-if="emission.note_moyenne != null"
              class="note-badge"
              :class="noteClass(emission.note_moyenne)"
              data-test="emission-note"
            >
              {{ emission.note_moyenne.toFixed(1) }}
            </span>
            <div class="emission-arrow">→</div>
          </div>
        </div>
      </section>

      <!-- Avis des critiques (Issue #201) -->
      <section
        v-if="avisGrouped.length > 0"
        class="avis-critiques-section"
        data-test="avis-critiques-section"
      >
        <h2>Avis des critiques</h2>

        <div
          v-for="group in avisGrouped"
          :key="group.emission_oid"
          class="avis-emission-group"
          data-test="avis-emission-group"
        >
          <h3 class="emission-group-header">
            <router-link
              v-if="group.emission_date"
              :to="`/emissions/${formatDateForUrl(group.emission_date_raw)}`"
              class="emission-date-link"
            >
              {{ group.emission_date }}
            </router-link>
            <span v-else>Émission inconnue</span>
          </h3>

          <table class="avis-table">
            <thead>
              <tr>
                <th>Critique</th>
                <th>Commentaire</th>
                <th>Note</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="avis in group.avis"
                :key="avis.id"
                data-test="avis-row"
              >
                <td class="critique-cell">
                  <router-link
                    v-if="avis.critique_oid"
                    :to="`/critique/${avis.critique_oid}`"
                    class="critique-link"
                  >
                    {{ avis.critique_nom || avis.critique_nom_extrait }}
                  </router-link>
                  <span v-else>{{ avis.critique_nom_extrait }}</span>
                </td>
                <td class="commentaire-cell">{{ avis.commentaire }}</td>
                <td class="note-cell">
                  <span
                    v-if="avis.note != null"
                    class="note-badge-small"
                    :class="noteClass(avis.note)"
                  >
                    {{ avis.note }}
                  </span>
                  <span v-else class="note-missing">-</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <!-- Bouton retour -->
      <div class="actions">
        <button @click="$router.back()" class="btn-secondary">
          ← Retour
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios';
import Navigation from '../components/Navigation.vue';

export default {
  name: 'LivreDetail',
  components: {
    Navigation
  },
  data() {
    return {
      livre: null,
      loading: false,
      error: null,
      annasArchiveBaseUrl: 'https://fr.annas-archive.li', // Fallback default (Issue #188)
      tagsCopied: false, // Issue #200: Copy feedback
      avis: [] // Issue #201: Avis des critiques
    };
  },
  computed: {
    avisGrouped() {
      if (!this.avis || this.avis.length === 0) return [];

      // Group avis by emission_oid
      const groups = new Map();
      for (const avis of this.avis) {
        const key = avis.emission_oid || 'unknown';
        if (!groups.has(key)) {
          groups.set(key, {
            emission_oid: key,
            emission_date: avis.emission_date ? this.formatDate(avis.emission_date) : null,
            emission_date_raw: avis.emission_date ? avis.emission_date.split('T')[0] : null,
            avis: [],
          });
        }
        groups.get(key).avis.push(avis);
      }

      // Sort groups by date descending, sort avis within by critique name
      const sorted = Array.from(groups.values()).sort((a, b) => {
        if (!a.emission_date_raw) return 1;
        if (!b.emission_date_raw) return -1;
        return b.emission_date_raw.localeCompare(a.emission_date_raw);
      });

      for (const group of sorted) {
        group.avis.sort((a, b) => {
          const nameA = (a.critique_nom || a.critique_nom_extrait || '').toLowerCase();
          const nameB = (b.critique_nom || b.critique_nom_extrait || '').toLowerCase();
          return nameA.localeCompare(nameB);
        });
      }

      return sorted;
    },
  },
  async mounted() {
    // Charger livre, URL Anna's Archive et avis en parallèle
    await Promise.all([
      this.loadLivre(),
      this.loadAnnasArchiveUrl(),
      this.loadAvis()
    ]);
  },
  methods: {
    async loadLivre() {
      this.loading = true;
      this.error = null;

      try {
        const livreId = this.$route.params.id;
        // Issue #103: Utiliser une URL relative pour bénéficier du proxy Vite
        const response = await axios.get(`/api/livre/${livreId}`);
        this.livre = response.data;
      } catch (err) {
        console.error('Erreur lors du chargement du livre:', err);
        if (err.response?.status === 404) {
          this.error = 'Livre non trouvé';
        } else if (err.response?.data?.detail) {
          this.error = err.response.data.detail;
        } else {
          this.error = 'Une erreur est survenue lors du chargement du livre';
        }
      } finally {
        this.loading = false;
      }
    },
    async loadAvis() {
      // Issue #201: Load critic reviews for this book
      try {
        const livreId = this.$route.params.id;
        const response = await axios.get(`/api/avis/by-livre/${livreId}`);
        this.avis = response.data.avis || [];
      } catch (err) {
        // Silently handle - avis are not critical for the page
        console.warn('Failed to load avis:', err);
        this.avis = [];
      }
    },
    async loadAnnasArchiveUrl() {
      // Issue #188: Charger l'URL dynamique d'Anna's Archive depuis le backend
      try {
        const response = await axios.get('/api/config/annas-archive-url');
        this.annasArchiveBaseUrl = response.data.url;
      } catch (err) {
        // Silently fallback to default (already set in data)
        console.warn('Failed to load Anna\'s Archive URL, using default:', err);
      }
    },
    formatDate(dateString) {
      // Format date from YYYY-MM-DD to "DD MMMM YYYY"
      if (!dateString) return '';

      const date = new Date(dateString);
      const options = { year: 'numeric', month: 'long', day: 'numeric' };
      return date.toLocaleDateString('fr-FR', options);
    },
    formatDateForUrl(dateString) {
      // Format date from YYYY-MM-DD to YYYYMMDD for /emissions/:date route
      if (!dateString) return '';
      return dateString.replace(/-/g, '');
    },
    noteClass(note) {
      // Color scale matching AvisTable.vue
      if (note >= 9) return 'note-excellent';
      if (note >= 7) return 'note-good';
      if (note >= 5) return 'note-average';
      return 'note-poor';
    },
    getAnnasArchiveUrl() {
      // Issue #165 + #188: Générer l'URL de recherche Anna's Archive (URL dynamique)
      if (!this.livre) return '';

      const titre = this.livre.titre || '';
      const auteur = this.livre.auteur_nom || '';
      const searchQuery = `${titre} - ${auteur}`;

      // Encoder l'URL selon le format Anna's Archive :
      // - Remplacer espaces par +
      // - Encoder les caractères spéciaux y compris ' et !
      const encodedQuery = encodeURIComponent(searchQuery)
        .replace(/%20/g, '+')      // Espaces → +
        .replace(/'/g, '%27')       // Apostrophes → %27
        .replace(/!/g, '%21');      // Points d'exclamation → %21

      // Utiliser l'URL dynamique au lieu du hardcoded (Issue #188)
      return `${this.annasArchiveBaseUrl}/search?index=&page=1&sort=&display=&q=${encodedQuery}`;
    },
    async copyTags() {
      // Issue #200: Copy Calibre tags to clipboard
      if (!this.livre?.calibre_tags?.length) return;
      const tagsString = this.livre.calibre_tags.join(', ');
      try {
        await navigator.clipboard.writeText(tagsString);
        this.tagsCopied = true;
        setTimeout(() => { this.tagsCopied = false; }, 2000);
      } catch (err) {
        console.error('Erreur copie tags:', err);
      }
    }
  }
};
</script>

<style scoped>
.livre-detail-page {
  min-height: 100vh;
  background-color: #f5f5f5;
}

/* États loading et error */
.loading-state,
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 400px;
  gap: 1rem;
  padding: 2rem;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #2c3e50;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.error-icon {
  font-size: 3rem;
}

.error-state span {
  color: #d32f2f;
  font-size: 1.1rem;
}

/* Contenu livre */
.livre-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}

.livre-header {
  background: white;
  border-radius: 8px;
  padding: 2rem;
  margin-bottom: 2rem;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.livre-header-container {
  display: flex;
  gap: 1.5rem;
  align-items: center;
}

/* Icônes externes à gauche (Issues #124, #165) */
.external-links {
  flex-shrink: 0;
  display: flex;
  gap: 1rem;
  align-items: center;
}

.external-logo-link {
  display: block;
  transition: transform 0.2s ease, opacity 0.2s ease;
}

.external-logo-link:hover {
  transform: scale(1.05);
  opacity: 0.9;
}

.external-logo {
  width: 80px;
  height: 80px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  object-fit: contain;
}

.livre-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.livre-title {
  font-size: 2rem;
  color: #2c3e50;
  margin: 0;
}

.livre-meta {
  margin: 1rem 0;
  font-size: 1.1rem;
  color: #555;
}

.livre-author {
  margin-bottom: 0.5rem;
}

.author-link {
  color: #1976d2;
  text-decoration: none;
  font-weight: 500;
  transition: color 0.2s ease;
}

.author-link:hover {
  color: #1565c0;
  text-decoration: underline;
}

.livre-publisher {
  color: #757575;
}

.livre-stats {
  display: flex;
  gap: 1rem;
  margin-top: 1rem;
}

.stat-badge {
  background: #e3f2fd;
  color: #1976d2;
  padding: 0.5rem 1rem;
  border-radius: 20px;
  font-weight: 500;
  font-size: 0.9rem;
}

/* Tags Calibre (Issue #200) */
.tags-section {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  flex-wrap: wrap;
}

.tag-badge {
  background: #f3e5f5;
  color: #7b1fa2;
  padding: 0.3rem 0.7rem;
  border-radius: 12px;
  font-size: 0.8rem;
  font-weight: 500;
  font-family: monospace;
}

.copy-tags-btn {
  background: none;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  padding: 0.25rem 0.5rem;
  cursor: pointer;
  font-size: 0.85rem;
  transition: all 0.2s ease;
}

.copy-tags-btn:hover {
  background: #f5f5f5;
  border-color: #7b1fa2;
}

/* Title row with note badge */
.livre-title-row {
  display: flex;
  align-items: center;
  gap: 1rem;
}

/* Note badges (Issue #190) */
.note-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 40px;
  height: 32px;
  padding: 0 0.5rem;
  border-radius: 16px;
  color: white;
  font-weight: 700;
  font-size: 0.9rem;
  flex-shrink: 0;
}

.note-excellent {
  background: #00C851;
}

.note-good {
  background: #8BC34A;
}

.note-average {
  background: #CDDC39;
  color: #333;
}

.note-poor {
  background: #F44336;
}

/* Section émissions (Issue #190) */
.emissions-section {
  background: white;
  border-radius: 8px;
  padding: 2rem;
  margin-bottom: 2rem;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.emissions-section h2 {
  font-size: 1.5rem;
  color: #2c3e50;
  margin: 0 0 1.5rem 0;
}

.empty-state {
  text-align: center;
  padding: 3rem;
  color: #757575;
}

.emissions-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.emission-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 1rem;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  background: #fafafa;
  transition: all 0.2s ease;
}

.emission-card:hover {
  background: #f5f5f5;
  border-color: #1976d2;
  transform: translateX(4px);
}

.emission-info {
  flex: 1;
}

.emission-date-link {
  text-decoration: none;
  color: inherit;
}

.emission-date-title {
  font-size: 1.1rem;
  color: #2c3e50;
  margin: 0 0 0.5rem 0;
  transition: color 0.2s ease;
}

.emission-date-link:hover .emission-date-title {
  color: #1976d2;
}

.emission-avis-count {
  color: #757575;
  font-size: 0.9rem;
  margin: 0;
}

.emission-arrow {
  color: #1976d2;
  font-size: 1.5rem;
  opacity: 0.5;
  transition: opacity 0.2s ease;
}

.emission-card:hover .emission-arrow {
  opacity: 1;
}

/* Section avis des critiques (Issue #201) */
.avis-critiques-section {
  background: white;
  border-radius: 8px;
  padding: 2rem;
  margin-bottom: 2rem;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.avis-critiques-section h2 {
  font-size: 1.5rem;
  color: #2c3e50;
  margin: 0 0 1.5rem 0;
}

.avis-emission-group {
  margin-bottom: 1.5rem;
}

.avis-emission-group:last-child {
  margin-bottom: 0;
}

.emission-group-header {
  font-size: 1.1rem;
  color: #555;
  margin: 0 0 0.75rem 0;
  padding-bottom: 0.5rem;
  border-bottom: 2px solid #e0e0e0;
}

.avis-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
}

.avis-table th,
.avis-table td {
  padding: 0.75rem;
  text-align: left;
  border-bottom: 1px solid #e0e0e0;
  vertical-align: top;
}

.avis-table th {
  background: #f5f5f5;
  font-weight: 600;
  color: #333;
}

.avis-table tbody tr:hover {
  background: #fafafa;
}

.critique-cell {
  white-space: nowrap;
  font-weight: 500;
}

.critique-link {
  color: #1976d2;
  text-decoration: none;
}

.critique-link:hover {
  text-decoration: underline;
}

.commentaire-cell {
  font-style: italic;
  color: #555;
}

.note-cell {
  text-align: center;
  width: 60px;
}

.note-badge-small {
  display: inline-block;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  font-weight: 700;
  font-size: 0.9rem;
  color: white;
}

.note-missing {
  color: #999;
}

/* Actions */
.actions {
  display: flex;
  gap: 1rem;
  padding: 1rem 0;
}

.btn-secondary {
  padding: 0.75rem 1.5rem;
  background: #e0e0e0;
  border: none;
  border-radius: 6px;
  color: #2c3e50;
  font-size: 1rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-secondary:hover {
  background: #bdbdbd;
}
</style>
