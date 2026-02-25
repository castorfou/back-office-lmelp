<template>
  <div class="critiques-page">
    <!-- Navigation -->
    <Navigation pageTitle="Critiques" />

    <!-- État de chargement -->
    <div v-if="loading" class="loading-state">
      <div class="loading-spinner"></div>
      <span>Chargement des critiques...</span>
    </div>

    <!-- Message d'erreur -->
    <div v-else-if="error" class="error-state">
      <div class="error-icon">⚠️</div>
      <span>Erreur : {{ error }}</span>
      <button @click="loadCritiques" class="btn-secondary">Réessayer</button>
    </div>

    <!-- Contenu principal -->
    <div v-else class="critiques-content">
      <!-- En-tête -->
      <div class="critiques-header">
        <h1>Liste des critiques</h1>
        <span class="total-count">{{ critiques.length }} critique(s)</span>
      </div>

      <!-- Message si vide -->
      <div v-if="critiques.length === 0" class="empty-state">
        <p>Aucun critique trouvé.</p>
      </div>

      <!-- Table des critiques -->
      <div v-else class="table-container">
        <table class="critiques-table">
          <thead>
            <tr>
              <th
                data-sort="nom"
                class="sortable"
                @click="sortBy('nom')"
              >
                Nom
                <span class="sort-indicator">{{ sortColumn === 'nom' ? (sortDir === 'asc' ? '↑' : '↓') : '↕' }}</span>
              </th>
              <th
                data-sort="nombre_avis"
                class="sortable"
                @click="sortBy('nombre_avis')"
              >
                Avis
                <span class="sort-indicator">{{ sortColumn === 'nombre_avis' ? (sortDir === 'asc' ? '↑' : '↓') : '↕' }}</span>
              </th>
              <th
                data-sort="note_moyenne"
                class="sortable"
                @click="sortBy('note_moyenne')"
              >
                Note moy.
                <span class="sort-indicator">{{ sortColumn === 'note_moyenne' ? (sortDir === 'asc' ? '↑' : '↓') : '↕' }}</span>
              </th>
              <th>Animateur</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="critique in sortedCritiques"
              :key="critique.id"
              class="critique-row"
              @click="navigateToCritique(critique.id)"
              title="Voir la fiche détaillée"
            >
              <td class="nom-cell">
                <span class="critique-nom-link">{{ critique.nom }}</span>
                <span class="row-arrow">→</span>
              </td>
              <td class="avis-cell">{{ critique.nombre_avis }}</td>
              <td class="note-cell">{{ critique.note_moyenne !== null ? critique.note_moyenne.toFixed(1) : '—' }}</td>
              <td class="animateur-cell">{{ critique.animateur ? '✓' : '' }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Section merge -->
      <div class="merge-section">
        <h2>Fusionner deux critiques doublons</h2>
        <p class="merge-description">
          Fusionne tous les avis du critique source vers le critique cible, puis supprime le doublon.
        </p>

        <div class="merge-form">
          <div class="merge-fields">
            <div class="form-group">
              <label for="merge-source">Critique source (à supprimer)</label>
              <select id="merge-source" v-model="mergeSourceId" class="form-select">
                <option value="">— Sélectionner —</option>
                <option v-for="c in critiques" :key="c.id" :value="c.id">
                  {{ c.nom }} ({{ c.nombre_avis }} avis)
                </option>
              </select>
            </div>

            <div class="form-group">
              <label for="merge-target">Critique cible (à conserver)</label>
              <select id="merge-target" v-model="mergeTargetId" class="form-select">
                <option value="">— Sélectionner —</option>
                <option v-for="c in critiques" :key="c.id" :value="c.id" :disabled="c.id === mergeSourceId">
                  {{ c.nom }} ({{ c.nombre_avis }} avis)
                </option>
              </select>
            </div>

            <div class="form-group">
              <label for="merge-confirmation">
                Confirmation : saisir le nom exact du critique cible
              </label>
              <input
                id="merge-confirmation"
                v-model="mergeConfirmation"
                type="text"
                class="form-input"
                :placeholder="mergeTargetNom || 'Nom exact du critique cible'"
              />
              <small class="form-hint">
                <span v-if="mergeTargetNom">
                  Nom attendu : <strong>{{ mergeTargetNom }}</strong>
                </span>
              </small>
            </div>
          </div>

          <div class="merge-actions">
            <button
              data-testid="merge-btn"
              class="btn-danger"
              :disabled="!canMerge"
              @click="executeMerge"
            >
              🔀 Fusionner
            </button>
          </div>

          <div v-if="mergeResult" class="merge-result success">
            ✓ Fusion réussie : {{ mergeResult.merged_avis }} avis repontés.
          </div>
          <div v-if="mergeError" class="merge-result error">
            ⚠️ Erreur : {{ mergeError }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios';
import Navigation from '../components/Navigation.vue';

export default {
  name: 'Critiques',
  components: { Navigation },

  data() {
    return {
      critiques: [],
      loading: true,
      error: null,
      sortColumn: 'nom',
      sortDir: 'asc',
      // Merge
      mergeSourceId: '',
      mergeTargetId: '',
      mergeConfirmation: '',
      mergeResult: null,
      mergeError: null,
      merging: false,
    };
  },

  computed: {
    sortedCritiques() {
      const sorted = [...this.critiques];
      sorted.sort((a, b) => {
        let valA = a[this.sortColumn];
        let valB = b[this.sortColumn];

        if (this.sortColumn === 'nom') {
          const cmp = (valA || '').localeCompare(valB || '', 'fr', { sensitivity: 'base' });
          return this.sortDir === 'asc' ? cmp : -cmp;
        }

        // Colonnes numériques : null en dernier
        if (valA === null || valA === undefined) return 1;
        if (valB === null || valB === undefined) return -1;
        return this.sortDir === 'asc' ? valA - valB : valB - valA;
      });
      return sorted;
    },

    mergeTargetNom() {
      if (!this.mergeTargetId) return '';
      const target = this.critiques.find(c => c.id === this.mergeTargetId);
      return target ? target.nom : '';
    },

    canMerge() {
      return (
        this.mergeSourceId &&
        this.mergeTargetId &&
        this.mergeSourceId !== this.mergeTargetId &&
        this.mergeConfirmation === this.mergeTargetNom
      );
    },
  },

  async mounted() {
    await this.loadCritiques();
  },

  methods: {
    async loadCritiques() {
      this.loading = true;
      this.error = null;
      try {
        const response = await axios.get('/api/critiques');
        this.critiques = response.data;
      } catch (err) {
        this.error = err.response?.data?.detail || err.message || 'Erreur inconnue';
      } finally {
        this.loading = false;
      }
    },

    sortBy(column) {
      if (this.sortColumn === column) {
        this.sortDir = this.sortDir === 'asc' ? 'desc' : 'asc';
      } else {
        this.sortColumn = column;
        this.sortDir = 'asc';
      }
    },

    navigateToCritique(id) {
      this.$router.push(`/critique/${id}`);
    },

    async executeMerge() {
      if (!this.canMerge || this.merging) return;
      this.merging = true;
      this.mergeResult = null;
      this.mergeError = null;
      try {
        const response = await axios.post('/api/critiques/merge', {
          source_id: this.mergeSourceId,
          target_id: this.mergeTargetId,
          target_nom: this.mergeConfirmation,
        });
        this.mergeResult = response.data;
        // Recharger la liste sans le critique fusionné
        await this.loadCritiques();
        this.mergeSourceId = '';
        this.mergeTargetId = '';
        this.mergeConfirmation = '';
      } catch (err) {
        this.mergeError = err.response?.data?.detail || err.message || 'Erreur inconnue';
      } finally {
        this.merging = false;
      }
    },
  },
};
</script>

<style scoped>
.critiques-page {
  min-height: 100vh;
  background-color: #f8f9fa;
}

.loading-state,
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 3rem;
  gap: 1rem;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #e9ecef;
  border-top-color: #007bff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.critiques-content {
  padding: 1.5rem;
  max-width: 1200px;
  margin: 0 auto;
}

.critiques-header {
  display: flex;
  align-items: baseline;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.critiques-header h1 {
  font-size: 1.8rem;
  font-weight: 700;
  color: #1a1a2e;
  margin: 0;
}

.total-count {
  color: #6c757d;
  font-size: 0.95rem;
}

.empty-state {
  text-align: center;
  padding: 3rem;
  color: #6c757d;
}

.table-container {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
  overflow: hidden;
  margin-bottom: 2rem;
}

.critiques-table {
  width: 100%;
  border-collapse: collapse;
}

.critiques-table th {
  background: #f8f9fa;
  padding: 0.85rem 1rem;
  text-align: left;
  font-size: 0.85rem;
  font-weight: 600;
  color: #495057;
  border-bottom: 2px solid #dee2e6;
}

.critiques-table th.sortable {
  cursor: pointer;
  user-select: none;
}

.critiques-table th.sortable:hover {
  background: #e9ecef;
}

.sort-indicator {
  margin-left: 0.4rem;
  color: #adb5bd;
}

.critiques-table td {
  padding: 0.85rem 1rem;
  border-bottom: 1px solid #f1f3f4;
  font-size: 0.9rem;
}

.critique-row {
  cursor: pointer;
  transition: background-color 0.15s ease;
}

.critique-row:hover {
  background-color: #f0f4ff;
}

.critique-row:hover .critique-nom-link {
  color: #2b6cb0;
  text-decoration: underline;
}

.critique-row:hover .row-arrow {
  opacity: 1;
}

.nom-cell {
  font-weight: 500;
  color: #1a1a2e;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.critique-nom-link {
  transition: color 0.15s ease;
}

.row-arrow {
  opacity: 0;
  color: #2b6cb0;
  font-size: 0.85rem;
  transition: opacity 0.15s ease;
}

.avis-cell,
.note-cell,
.animateur-cell {
  color: #495057;
}

/* Section merge */
.merge-section {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
  padding: 1.5rem;
  margin-top: 2rem;
  border-left: 4px solid #dc3545;
}

.merge-section h2 {
  font-size: 1.2rem;
  font-weight: 600;
  color: #dc3545;
  margin: 0 0 0.5rem;
}

.merge-description {
  color: #6c757d;
  font-size: 0.9rem;
  margin-bottom: 1.5rem;
}

.merge-fields {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 1rem;
  margin-bottom: 1rem;
}

@media (max-width: 768px) {
  .merge-fields {
    grid-template-columns: 1fr;
  }
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.form-group label {
  font-size: 0.85rem;
  font-weight: 500;
  color: #495057;
}

.form-select,
.form-input {
  padding: 0.5rem 0.75rem;
  border: 1px solid #ced4da;
  border-radius: 4px;
  font-size: 0.9rem;
  color: #212529;
  background: white;
}

.form-select:focus,
.form-input:focus {
  outline: none;
  border-color: #80bdff;
  box-shadow: 0 0 0 2px rgba(0,123,255,0.15);
}

.form-hint {
  font-size: 0.8rem;
  color: #6c757d;
}

.merge-actions {
  margin-top: 1rem;
}

.btn-danger {
  padding: 0.6rem 1.5rem;
  background-color: #dc3545;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  transition: background-color 0.15s ease;
}

.btn-danger:hover:not(:disabled) {
  background-color: #c82333;
}

.btn-danger:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  padding: 0.6rem 1.2rem;
  background: #6c757d;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.merge-result {
  margin-top: 1rem;
  padding: 0.75rem 1rem;
  border-radius: 4px;
  font-size: 0.9rem;
}

.merge-result.success {
  background: #d4edda;
  color: #155724;
  border: 1px solid #c3e6cb;
}

.merge-result.error {
  background: #f8d7da;
  color: #721c24;
  border: 1px solid #f5c6cb;
}
</style>
