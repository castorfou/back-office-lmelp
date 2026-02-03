<template>
  <div class="critique-detail-page">
    <!-- Navigation -->
    <Navigation pageTitle="Détail du critique" />

    <!-- État de chargement -->
    <div v-if="loading" class="loading-state" data-test="loading">
      <div class="loading-spinner"></div>
      <span>Chargement des informations du critique...</span>
    </div>

    <!-- Message d'erreur -->
    <div v-else-if="error" class="error-state" data-test="error">
      <div class="error-icon">⚠️</div>
      <span>{{ error }}</span>
      <button @click="$router.back()" class="btn-secondary">
        Retour
      </button>
    </div>

    <!-- Contenu du critique -->
    <div v-else-if="critique" class="critique-content">
      <!-- En-tête critique -->
      <div class="critique-header">
        <div class="critique-header-container">
          <div class="critique-icon">🎙️</div>
          <div class="critique-info">
            <h1 class="critique-name">
              {{ critique.nom }}
              <span v-if="critique.animateur" class="animateur-badge" data-test="animateur-badge">
                Animateur
              </span>
            </h1>
            <div class="critique-stats">
              <span class="stat-badge">
                {{ critique.nombre_avis }} avis
              </span>
              <span
                v-if="critique.note_moyenne != null"
                class="note-badge"
                :class="noteClass(critique.note_moyenne)"
                data-test="note-moyenne"
              >
                {{ critique.note_moyenne.toFixed(1) }}
              </span>
            </div>
            <div v-if="critique.variantes && critique.variantes.length > 0" class="variantes">
              <span class="variantes-label">Variantes :</span>
              {{ critique.variantes.join(', ') }}
            </div>
          </div>
        </div>
      </div>

      <!-- Distribution des notes -->
      <section v-if="critique.nombre_avis > 0" class="distribution-section">
        <h2>Distribution des notes</h2>
        <div class="distribution-chart">
          <div
            v-for="note in noteLabels"
            :key="note"
            class="distribution-column"
            data-test="distribution-bar"
          >
            <div class="bar-container">
              <div
                class="bar"
                :class="noteClass(parseInt(note))"
                :style="{ height: barHeight(critique.note_distribution[note]) + '%' }"
              >
                <span v-if="critique.note_distribution[note] > 0" class="bar-count">
                  {{ critique.note_distribution[note] }}
                </span>
              </div>
            </div>
            <div class="bar-label">{{ note }}</div>
          </div>
        </div>
        <div class="distribution-legend">
          <span>
            Note moyenne :
            <strong
              v-if="critique.note_moyenne != null"
              :class="noteClass(critique.note_moyenne)"
            >
              {{ critique.note_moyenne.toFixed(1) }}
            </strong>
            <strong v-else>-</strong>
          </span>
          <span>{{ critique.nombre_avis }} avis au total</span>
        </div>
      </section>

      <!-- Coups de coeur -->
      <section v-if="critique.coups_de_coeur.length > 0" class="coups-de-coeur-section">
        <h2>
          Coups de cœur
          <span class="section-count">{{ critique.coups_de_coeur.length }}</span>
        </h2>
        <div class="coups-de-coeur-list">
          <div
            v-for="(coup, index) in critique.coups_de_coeur"
            :key="index"
            class="coup-de-coeur-card"
            data-test="coup-de-coeur-item"
          >
            <div class="coup-info">
              <div class="coup-title-row">
                <router-link
                  v-if="coup.livre_oid"
                  :to="`/livre/${coup.livre_oid}`"
                  class="livre-link"
                >
                  {{ coup.livre_titre }}
                </router-link>
                <span v-else>{{ coup.livre_titre }}</span>
                <span class="note-badge" :class="noteClass(coup.note)">
                  {{ coup.note }}
                </span>
              </div>
              <div class="coup-meta">
                <router-link
                  v-if="coup.auteur_oid"
                  :to="`/auteur/${coup.auteur_oid}`"
                  class="auteur-link"
                >
                  {{ coup.auteur_nom }}
                </router-link>
                <span v-else class="auteur-name">{{ coup.auteur_nom }}</span>
                <span v-if="coup.editeur" class="editeur">· {{ coup.editeur }}</span>
              </div>
              <p v-if="coup.commentaire" class="commentaire">{{ coup.commentaire }}</p>
              <router-link
                v-if="coup.emission_date"
                :to="`/emissions/${formatDateForUrl(coup.emission_date)}`"
                class="emission-date-chip"
              >
                {{ formatDate(coup.emission_date) }}
              </router-link>
            </div>
          </div>
        </div>
      </section>

      <!-- Liste des oeuvres avec filtres -->
      <section class="oeuvres-section">
        <h2>
          Œuvres critiquées
          <span class="section-count">{{ filteredOeuvres.length }}/{{ critique.oeuvres.length }}</span>
        </h2>

        <!-- Filtres -->
        <div v-if="critique.oeuvres.length > 0" class="filters">
          <input
            v-model="searchFilter"
            type="text"
            placeholder="Rechercher un titre ou un auteur..."
            class="filter-input"
            data-test="search-filter"
          />
          <select v-model="noteFilter" class="filter-select" data-test="note-filter">
            <option value="all">Toutes les notes</option>
            <option value="excellent">9-10 (Excellent)</option>
            <option value="good">7-8 (Bon)</option>
            <option value="average">5-6 (Moyen)</option>
            <option value="poor">&lt; 5 (Faible)</option>
          </select>
          <select v-model="sectionFilter" class="filter-select" data-test="section-filter">
            <option value="all">Toutes les sections</option>
            <option value="programme">Programme</option>
            <option value="coup_de_coeur">Coup de cœur</option>
          </select>
        </div>

        <!-- Message si aucune oeuvre -->
        <div v-if="critique.oeuvres.length === 0" class="empty-state">
          <p>Aucun avis trouvé pour ce critique</p>
        </div>

        <!-- Message si filtres vident la liste -->
        <div v-else-if="filteredOeuvres.length === 0" class="empty-state">
          <p>Aucun résultat pour ces critères de recherche</p>
        </div>

        <!-- Liste des oeuvres -->
        <div v-else class="oeuvres-list">
          <div
            v-for="(oeuvre, index) in filteredOeuvres"
            :key="index"
            class="oeuvre-card"
            data-test="oeuvre-item"
          >
            <div class="oeuvre-info">
              <div class="oeuvre-title-row">
                <router-link
                  v-if="oeuvre.livre_oid"
                  :to="`/livre/${oeuvre.livre_oid}`"
                  class="livre-link"
                >
                  {{ oeuvre.livre_titre }}
                </router-link>
                <span v-else>{{ oeuvre.livre_titre }}</span>
                <span
                  v-if="oeuvre.note != null"
                  class="note-badge"
                  :class="noteClass(oeuvre.note)"
                >
                  {{ oeuvre.note }}
                </span>
              </div>
              <div class="oeuvre-meta">
                <router-link
                  v-if="oeuvre.auteur_oid"
                  :to="`/auteur/${oeuvre.auteur_oid}`"
                  class="auteur-link"
                >
                  {{ oeuvre.auteur_nom }}
                </router-link>
                <span v-else class="auteur-name">{{ oeuvre.auteur_nom }}</span>
                <span v-if="oeuvre.editeur" class="editeur">· {{ oeuvre.editeur }}</span>
                <span v-if="oeuvre.section" class="section-badge">{{ oeuvre.section }}</span>
              </div>
              <p v-if="oeuvre.commentaire" class="commentaire">{{ oeuvre.commentaire }}</p>
              <router-link
                v-if="oeuvre.emission_date"
                :to="`/emissions/${formatDateForUrl(oeuvre.emission_date)}`"
                class="emission-date-chip"
              >
                {{ formatDate(oeuvre.emission_date) }}
              </router-link>
            </div>
          </div>
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
import { removeAccents } from '@/utils/textUtils';

export default {
  name: 'CritiqueDetail',
  components: {
    Navigation
  },
  data() {
    return {
      critique: null,
      loading: false,
      error: null,
      searchFilter: '',
      noteFilter: 'all',
      sectionFilter: 'all',
      noteLabels: ['2', '3', '4', '5', '6', '7', '8', '9', '10']
    };
  },
  computed: {
    filteredOeuvres() {
      if (!this.critique) return [];
      let oeuvres = [...this.critique.oeuvres];

      // Filtre texte (insensible aux accents)
      if (this.searchFilter.trim()) {
        const search = removeAccents(this.searchFilter.toLowerCase());
        oeuvres = oeuvres.filter(o =>
          removeAccents((o.livre_titre || '').toLowerCase()).includes(search) ||
          removeAccents((o.auteur_nom || '').toLowerCase()).includes(search)
        );
      }

      // Filtre par plage de notes
      if (this.noteFilter !== 'all') {
        oeuvres = oeuvres.filter(o => {
          if (o.note == null) return false;
          switch (this.noteFilter) {
            case 'excellent': return o.note >= 9;
            case 'good': return o.note >= 7 && o.note < 9;
            case 'average': return o.note >= 5 && o.note < 7;
            case 'poor': return o.note < 5;
            default: return true;
          }
        });
      }

      // Filtre par section
      if (this.sectionFilter !== 'all') {
        oeuvres = oeuvres.filter(o => o.section === this.sectionFilter);
      }

      return oeuvres;
    },
    maxDistributionCount() {
      if (!this.critique?.note_distribution) return 1;
      return Math.max(...Object.values(this.critique.note_distribution), 1);
    }
  },
  async mounted() {
    await this.loadCritique();
  },
  methods: {
    async loadCritique() {
      this.loading = true;
      this.error = null;

      try {
        const critiqueId = this.$route.params.id;
        const response = await axios.get(`/api/critique/${critiqueId}`);
        this.critique = response.data;
      } catch (err) {
        console.error('Erreur lors du chargement du critique:', err);
        if (err.response?.status === 404) {
          this.error = 'Critique non trouvé';
        } else if (err.response?.data?.detail) {
          this.error = err.response.data.detail;
        } else {
          this.error = 'Une erreur est survenue lors du chargement du critique';
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
    barHeight(count) {
      return Math.round((count / this.maxDistributionCount) * 100);
    },
    formatDate(dateString) {
      if (!dateString) return '';
      const date = new Date(dateString);
      const options = { year: 'numeric', month: 'long', day: 'numeric' };
      return date.toLocaleDateString('fr-FR', options);
    },
    formatDateForUrl(dateString) {
      if (!dateString) return '';
      return dateString.replace(/-/g, '');
    }
  }
};
</script>

<style scoped>
.critique-detail-page {
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

/* Contenu critique */
.critique-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}

/* En-tête */
.critique-header {
  background: white;
  border-radius: 8px;
  padding: 2rem;
  margin-bottom: 2rem;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.critique-header-container {
  display: flex;
  gap: 1.5rem;
  align-items: center;
}

.critique-icon {
  font-size: 3rem;
  flex-shrink: 0;
}

.critique-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.critique-name {
  font-size: 2rem;
  color: #2c3e50;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.animateur-badge {
  background: #ff9800;
  color: white;
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  font-size: 0.8rem;
  font-weight: 600;
}

.critique-stats {
  display: flex;
  gap: 1rem;
  align-items: center;
}

.stat-badge {
  background: #e3f2fd;
  color: #1976d2;
  padding: 0.5rem 1rem;
  border-radius: 20px;
  font-weight: 500;
  font-size: 0.9rem;
}

.variantes {
  color: #757575;
  font-size: 0.9rem;
}

.variantes-label {
  font-weight: 600;
}

/* Note badges */
.note-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 36px;
  height: 28px;
  padding: 0 0.4rem;
  border-radius: 14px;
  color: white;
  font-weight: 700;
  font-size: 0.85rem;
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

/* Distribution des notes */
.distribution-section {
  background: white;
  border-radius: 8px;
  padding: 2rem;
  margin-bottom: 2rem;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.distribution-section h2 {
  font-size: 1.5rem;
  color: #2c3e50;
  margin: 0 0 1.5rem 0;
}

.distribution-chart {
  display: flex;
  align-items: flex-end;
  gap: 0.5rem;
  height: 220px;
  padding: 1rem 0;
  border-bottom: 2px solid #e0e0e0;
}

.distribution-column {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.bar-container {
  width: 100%;
  height: 180px;
  display: flex;
  align-items: flex-end;
  justify-content: center;
}

.bar {
  width: 80%;
  max-width: 60px;
  border-radius: 4px 4px 0 0;
  transition: height 0.3s ease;
  position: relative;
  min-height: 2px;
}

.bar-count {
  position: absolute;
  top: -20px;
  left: 50%;
  transform: translateX(-50%);
  font-size: 0.75rem;
  font-weight: 600;
  color: #333;
}

.bar-label {
  margin-top: 0.5rem;
  font-weight: 600;
  color: #555;
}

.distribution-legend {
  display: flex;
  justify-content: space-between;
  padding-top: 1rem;
  color: #757575;
  font-size: 0.9rem;
}

/* Coups de coeur */
.coups-de-coeur-section {
  background: white;
  border-radius: 8px;
  padding: 2rem;
  margin-bottom: 2rem;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.coups-de-coeur-section h2 {
  font-size: 1.5rem;
  color: #2c3e50;
  margin: 0 0 1.5rem 0;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.section-count {
  background: #e3f2fd;
  color: #1976d2;
  padding: 0.2rem 0.6rem;
  border-radius: 12px;
  font-size: 0.85rem;
  font-weight: 500;
}

.coups-de-coeur-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.coup-de-coeur-card {
  padding: 1rem;
  border: 1px solid #c8e6c9;
  border-left: 4px solid #00C851;
  border-radius: 6px;
  background: #f1f8e9;
  transition: all 0.2s ease;
}

.coup-de-coeur-card:hover {
  border-color: #00C851;
  box-shadow: 0 2px 8px rgba(0, 200, 81, 0.15);
}

/* Oeuvres section */
.oeuvres-section {
  background: white;
  border-radius: 8px;
  padding: 2rem;
  margin-bottom: 2rem;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.oeuvres-section h2 {
  font-size: 1.5rem;
  color: #2c3e50;
  margin: 0 0 1.5rem 0;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

/* Filtres */
.filters {
  display: flex;
  gap: 1rem;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
}

.filter-input {
  flex: 1;
  min-width: 200px;
  padding: 0.6rem 1rem;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  font-size: 0.9rem;
  transition: border-color 0.2s ease;
}

.filter-input:focus {
  outline: none;
  border-color: #1976d2;
  box-shadow: 0 0 0 2px rgba(25, 118, 210, 0.1);
}

.filter-select {
  padding: 0.6rem 1rem;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  font-size: 0.9rem;
  background: white;
  cursor: pointer;
}

.filter-select:focus {
  outline: none;
  border-color: #1976d2;
}

/* Empty state */
.empty-state {
  text-align: center;
  padding: 3rem;
  color: #757575;
}

/* Liste des oeuvres */
.oeuvres-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.oeuvre-card {
  padding: 1rem;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  background: #fafafa;
  transition: all 0.2s ease;
}

.oeuvre-card:hover {
  background: #f5f5f5;
  border-color: #1976d2;
  transform: translateX(4px);
}

.oeuvre-info,
.coup-info {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.oeuvre-title-row,
.coup-title-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.livre-link {
  text-decoration: none;
  color: #2c3e50;
  font-weight: 600;
  font-size: 1.05rem;
  transition: color 0.2s ease;
}

.livre-link:hover {
  color: #1976d2;
}

.oeuvre-meta,
.coup-meta {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: #757575;
  font-size: 0.9rem;
}

.auteur-link {
  text-decoration: none;
  color: #1976d2;
  transition: color 0.2s ease;
}

.auteur-link:hover {
  color: #1565c0;
  text-decoration: underline;
}

.auteur-name {
  color: #555;
}

.editeur {
  color: #9e9e9e;
}

.section-badge {
  background: #f3e5f5;
  color: #7b1fa2;
  padding: 0.15rem 0.5rem;
  border-radius: 10px;
  font-size: 0.75rem;
  font-weight: 500;
}

.commentaire {
  color: #555;
  font-size: 0.9rem;
  font-style: italic;
  margin: 0.25rem 0;
  line-height: 1.4;
}

/* Emission date chips */
.emission-date-chip {
  display: inline-block;
  padding: 0.2rem 0.6rem;
  background: #e3f2fd;
  color: #1976d2;
  border-radius: 12px;
  font-size: 0.8rem;
  text-decoration: none;
  transition: background 0.2s ease;
  align-self: flex-start;
}

.emission-date-chip:hover {
  background: #bbdefb;
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
