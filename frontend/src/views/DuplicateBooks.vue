<template>
  <div class="duplicate-books-container">
    <h1>Gestion des doublons de livres</h1>

    <!-- Statistics Card -->
    <div v-if="statistics" class="statistics-card">
      <h2>Statistiques</h2>
      <div class="stats-grid">
        <div class="stat-item">
          <span class="stat-label">Groupes de doublons</span>
          <span class="stat-value">{{ statistics.total_groups }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">Livres en doublon</span>
          <span class="stat-value">{{ statistics.total_duplicates }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">Groupes fusionnés</span>
          <span class="stat-value">{{ statistics.merged_count }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">En attente</span>
          <span class="stat-value">{{ statistics.pending_count }}</span>
        </div>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="loading">
      Chargement des doublons...
    </div>

    <!-- Error State -->
    <div v-if="error" class="error-message">
      {{ error }}
    </div>

    <!-- Duplicate Groups List -->
    <div v-if="!loading && !error && duplicateGroups.length > 0" class="groups-container">
      <div class="groups-header">
        <h2>Groupes de doublons ({{ duplicateGroups.length }})</h2>
        <button
          class="btn btn-primary"
          :disabled="isBatchRunning"
          @click="startBatchMerge"
        >
          {{ isBatchRunning ? 'Fusion en cours...' : 'Fusionner tous les groupes' }}
        </button>
      </div>

      <!-- Batch Progress -->
      <div v-if="isBatchRunning" class="batch-progress">
        <div class="progress-bar">
          <div
            class="progress-fill"
            :style="{ width: batchProgressPercent + '%' }"
          ></div>
        </div>
        <p>{{ batchProgress.current }} / {{ batchProgress.total }} groupes traités</p>
      </div>

      <!-- Groups List -->
      <div class="groups-list">
        <div
          v-for="group in duplicateGroups"
          :key="group.url_babelio"
          class="group-card"
          :class="{ 'group-processing': processingGroup === group.url_babelio }"
        >
          <div class="group-header">
            <div class="group-info">
              <h3>{{ group.titres[0] }}</h3>
              <p class="group-count">{{ group.count }} livres en doublon</p>
              <a
                :href="group.url_babelio"
                target="_blank"
                class="babelio-link"
              >
                Voir sur Babelio ↗
              </a>
            </div>
            <div class="group-actions">
              <label class="skip-checkbox">
                <input
                  type="checkbox"
                  :checked="skipList.includes(group.url_babelio)"
                  @change="toggleSkip(group.url_babelio)"
                >
                Ignorer
              </label>
              <button
                class="btn btn-merge"
                :disabled="processingGroup === group.url_babelio"
                @click="mergeGroup(group)"
              >
                {{ processingGroup === group.url_babelio ? 'Fusion...' : 'Fusionner' }}
              </button>
            </div>
          </div>

          <div class="group-details">
            <div class="titles-list">
              <strong>Titres variantes:</strong>
              <ul>
                <li v-for="(titre, index) in group.titres" :key="index">
                  {{ titre }}
                </li>
              </ul>
            </div>
          </div>

          <!-- Merge Result -->
          <div v-if="mergeResults[group.url_babelio]" class="merge-result">
            <div
              v-if="mergeResults[group.url_babelio].success"
              class="result-success"
            >
              ✓ Fusion réussie:
              {{ mergeResults[group.url_babelio].result.episodes_merged }} épisodes,
              {{ mergeResults[group.url_babelio].result.avis_critiques_merged }} avis fusionnés
            </div>
            <div v-else class="result-error">
              ✗ Erreur: {{ mergeResults[group.url_babelio].error }}
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div v-if="!loading && !error && duplicateGroups.length === 0" class="empty-state">
      <p>Aucun doublon détecté ! 🎉</p>
    </div>
  </div>
</template>

<script>
import axios from 'axios';

export default {
  name: 'DuplicateBooks',

  data() {
    return {
      statistics: null,
      duplicateGroups: [],
      loading: false,
      error: null,
      processingGroup: null,
      skipList: [],
      isBatchRunning: false,
      batchProgress: {
        current: 0,
        total: 0
      },
      mergeResults: {}
    };
  },

  computed: {
    batchProgressPercent() {
      if (this.batchProgress.total === 0) return 0;
      return Math.round((this.batchProgress.current / this.batchProgress.total) * 100);
    }
  },

  mounted() {
    this.loadData();
  },

  methods: {
    async loadData() {
      this.loading = true;
      this.error = null;

      try {
        // Load statistics and groups in parallel
        const [statsResponse, groupsResponse] = await Promise.all([
          axios.get(`${import.meta.env.VITE_API_BASE_URL}/api/books/duplicates/statistics`),
          axios.get(`${import.meta.env.VITE_API_BASE_URL}/api/books/duplicates/groups`)
        ]);

        this.statistics = statsResponse.data;
        this.duplicateGroups = groupsResponse.data;
      } catch (err) {
        this.error = `Erreur lors du chargement: ${err.message}`;
        console.error('Load data error:', err);
      } finally {
        this.loading = false;
      }
    },

    toggleSkip(url) {
      const index = this.skipList.indexOf(url);
      if (index === -1) {
        this.skipList.push(url);
      } else {
        this.skipList.splice(index, 1);
      }
    },

    async mergeGroup(group) {
      this.processingGroup = group.url_babelio;
      this.error = null;

      try {
        const response = await axios.post(
          `${import.meta.env.VITE_API_BASE_URL}/api/books/duplicates/merge`,
          {
            url_babelio: group.url_babelio,
            book_ids: group.book_ids
          }
        );

        // Store result
        this.mergeResults[group.url_babelio] = {
          success: true,
          result: response.data.result
        };

        // Remove from list after successful merge
        setTimeout(() => {
          this.duplicateGroups = this.duplicateGroups.filter(
            g => g.url_babelio !== group.url_babelio
          );
          // Reload statistics
          this.loadStatistics();
        }, 2000);

      } catch (err) {
        this.mergeResults[group.url_babelio] = {
          success: false,
          error: err.response?.data?.detail || err.message
        };
        console.error('Merge error:', err);
      } finally {
        this.processingGroup = null;
      }
    },

    async startBatchMerge() {
      if (this.isBatchRunning) return;

      this.isBatchRunning = true;
      this.batchProgress.current = 0;
      this.batchProgress.total = this.duplicateGroups.filter(
        g => !this.skipList.includes(g.url_babelio)
      ).length;

      // Sequential merge of non-skipped groups
      for (const group of this.duplicateGroups) {
        if (this.skipList.includes(group.url_babelio)) {
          continue;
        }

        await this.mergeGroup(group);
        this.batchProgress.current++;

        // Small delay between merges to avoid overwhelming the server
        await new Promise(resolve => setTimeout(resolve, 1000));
      }

      this.isBatchRunning = false;
      this.batchProgress = { current: 0, total: 0 };
    },

    async loadStatistics() {
      try {
        const response = await axios.get(
          `${import.meta.env.VITE_API_BASE_URL}/api/books/duplicates/statistics`
        );
        this.statistics = response.data;
      } catch (err) {
        console.error('Load statistics error:', err);
      }
    }
  }
};
</script>

<style scoped>
.duplicate-books-container {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

h1 {
  font-size: 2rem;
  margin-bottom: 20px;
}

/* Statistics Card */
.statistics-card {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 30px;
}

.statistics-card h2 {
  font-size: 1.5rem;
  margin-bottom: 15px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 15px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  padding: 15px;
  background: white;
  border-radius: 6px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.stat-label {
  font-size: 0.875rem;
  color: #666;
  margin-bottom: 5px;
}

.stat-value {
  font-size: 2rem;
  font-weight: bold;
  color: #007bff;
}

/* Loading & Error States */
.loading, .empty-state {
  text-align: center;
  padding: 40px;
  color: #666;
  font-size: 1.1rem;
}

.error-message {
  background: #f8d7da;
  color: #721c24;
  padding: 15px;
  border-radius: 6px;
  margin-bottom: 20px;
}

/* Groups Container */
.groups-container {
  margin-top: 30px;
}

.groups-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.groups-header h2 {
  font-size: 1.5rem;
}

/* Buttons */
.btn {
  padding: 10px 20px;
  border: none;
  border-radius: 6px;
  font-size: 1rem;
  cursor: pointer;
  transition: background-color 0.2s;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary {
  background: #007bff;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #0056b3;
}

.btn-merge {
  background: #28a745;
  color: white;
}

.btn-merge:hover:not(:disabled) {
  background: #218838;
}

/* Batch Progress */
.batch-progress {
  background: #e9ecef;
  padding: 20px;
  border-radius: 6px;
  margin-bottom: 20px;
}

.progress-bar {
  width: 100%;
  height: 24px;
  background: #dee2e6;
  border-radius: 12px;
  overflow: hidden;
  margin-bottom: 10px;
}

.progress-fill {
  height: 100%;
  background: #007bff;
  transition: width 0.3s ease;
}

.batch-progress p {
  text-align: center;
  margin: 0;
  font-weight: bold;
}

/* Groups List */
.groups-list {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.group-card {
  background: white;
  border: 1px solid #dee2e6;
  border-radius: 8px;
  padding: 20px;
  transition: box-shadow 0.2s;
}

.group-card:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.group-card.group-processing {
  border-color: #007bff;
  background: #f0f8ff;
}

.group-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 15px;
}

.group-info h3 {
  margin: 0 0 5px 0;
  font-size: 1.25rem;
}

.group-count {
  color: #666;
  margin: 5px 0;
}

.babelio-link {
  color: #007bff;
  text-decoration: none;
  font-size: 0.875rem;
}

.babelio-link:hover {
  text-decoration: underline;
}

.group-actions {
  display: flex;
  align-items: center;
  gap: 15px;
}

.skip-checkbox {
  display: flex;
  align-items: center;
  gap: 5px;
  cursor: pointer;
}

.skip-checkbox input {
  cursor: pointer;
}

/* Group Details */
.group-details {
  border-top: 1px solid #e9ecef;
  padding-top: 15px;
}

.titles-list ul {
  list-style: none;
  padding-left: 20px;
  margin-top: 5px;
}

.titles-list li {
  padding: 3px 0;
  color: #495057;
}

/* Merge Results */
.merge-result {
  margin-top: 15px;
  padding: 10px;
  border-radius: 6px;
}

.result-success {
  background: #d4edda;
  color: #155724;
  padding: 10px;
  border-radius: 6px;
}

.result-error {
  background: #f8d7da;
  color: #721c24;
  padding: 10px;
  border-radius: 6px;
}
</style>
