<template>
  <div class="babelio-migration">
    <!-- Navigation -->
    <Navigation pageTitle="Liaison Babelio des livres" />

    <main>
      <!-- Toast notifications -->
    <div v-if="toast" class="toast" :class="toast.type">
      {{ toast.message }}
    </div>

    <!-- Panel de statut -->
    <div v-if="status" class="status-panel">
      <h2>Statut de la liaison</h2>

      <!-- Statistiques Livres -->
      <h3 class="stats-section-title">📚 Livres</h3>
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-value">{{ status.total_books }}</div>
          <div class="stat-label">Livres total</div>
        </div>
        <div class="stat-card success">
          <div class="stat-value">{{ status.migrated_count }}</div>
          <div class="stat-label">Liés avec succès</div>
        </div>
        <div class="stat-card success">
          <div class="stat-value">{{ status.not_found_count }}</div>
          <div class="stat-label">Absents de Babelio</div>
        </div>
        <div class="stat-card warning">
          <div class="stat-value">{{ status.problematic_count }}</div>
          <div class="stat-label">À traiter manuellement</div>
        </div>
        <div class="stat-card pending">
          <div class="stat-value">{{ status.pending_count }}</div>
          <div class="stat-label">En attente de liaison</div>
        </div>
      </div>

      <!-- Statistiques Auteurs -->
      <h3 class="stats-section-title">👤 Auteurs</h3>
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-value">{{ status.total_authors || 0 }}</div>
          <div class="stat-label">Auteurs total</div>
        </div>
        <div class="stat-card success">
          <div class="stat-value">{{ status.authors_with_url || 0 }}</div>
          <div class="stat-label">Liés avec succès</div>
        </div>
        <div class="stat-card pending">
          <div class="stat-value">{{ status.authors_without_url_babelio || 0 }}</div>
          <div class="stat-label">En attente de liaison</div>
        </div>
      </div>

      <!-- Migration button -->
      <div class="migration-button-container">
        <button
          class="btn-migration"
          @click="toggleMigration"
          :disabled="(status.pending_count === 0 && status.authors_without_url_babelio === 0) && !migrationProgress.is_running"
          :class="{ 'migration-running': migrationProgress.is_running }"
          :title="migrationProgress.is_running ? 'Cliquer pour arrêter' : 'Cliquer pour lancer la liaison'"
        >
          <span v-if="migrationProgress.is_running">
            <div class="spinner-inline"></div>
            ⚙️ Liaison en cours...
          </span>
          <span v-else>
            🚀 Lancer la liaison automatique
          </span>
        </button>
      </div>

      <!-- Legend section -->
      <div class="legend-section">
        <h3>Légende</h3>
        <h4>📚 Livres</h4>
        <ul>
          <li><strong>Livres total:</strong> Nombre total de livres dans la base de données</li>
          <li><strong>Liés avec succès:</strong> Livres ayant une URL Babelio associée</li>
          <li><strong>Absents de Babelio:</strong> Livres marqués comme non référencés sur Babelio</li>
          <li><strong>À traiter manuellement:</strong> Livres nécessitant une intervention manuelle (titre incorrect, correspondance ambiguë...)</li>
          <li><strong>En attente de liaison:</strong> Livres restant à traiter par la liaison automatique</li>
        </ul>
        <h4>👤 Auteurs</h4>
        <ul>
          <li><strong>Auteurs total:</strong> Nombre total d'auteurs dans la base de données</li>
          <li><strong>Liés avec succès:</strong> Auteurs ayant une URL Babelio associée</li>
          <li><strong>En attente de liaison:</strong> Auteurs restant à lier (la liaison automatique traite les auteurs en même temps que leurs livres)</li>
        </ul>
      </div>

      <!-- Progress panel for migration -->
      <div v-if="migrationProgress.is_running || migrationProgress.book_logs.length > 0" class="migration-progress-panel">
        <div class="progress-header">
          <h3>
            {{ migrationProgress.is_running ? '⚙️ Liaison en cours' : '✅ Dernière liaison' }}
          </h3>
        </div>

        <div class="progress-summary">
          <div class="progress-stat">
            <strong>Livres traités:</strong> {{ migrationProgress.books_processed }}
          </div>
          <div class="progress-stat" v-if="migrationProgress.start_time">
            <strong>Démarrée:</strong> {{ formatDate(migrationProgress.start_time) }}
          </div>
          <div class="progress-stat" v-if="migrationProgress.last_update">
            <strong>Dernière mise à jour:</strong> {{ formatDate(migrationProgress.last_update) }}
          </div>
        </div>

        <!-- Structured book logs (compact view) -->
        <div v-if="migrationProgress.book_logs && migrationProgress.book_logs.length > 0" class="book-logs-section">
          <h4>Livres traités ({{ migrationProgress.book_logs.length }})</h4>
          <div class="book-logs-list">
            <div
              v-for="(bookLog, index) in migrationProgress.book_logs"
              :key="index"
              class="book-log-item"
            >
              <div class="book-log-header" @click="toggleBookLog(index)">
                <span class="book-log-title">
                  {{ bookLog.titre }} - {{ bookLog.auteur }}
                </span>
                <span class="book-log-status">
                  {{ getStatusIcon(bookLog.livre_status) }}
                  {{ getStatusIcon(bookLog.auteur_status) }}
                  <span class="expand-toggle-book">{{ expandedBooks[index] ? '▼' : '▶' }}</span>
                </span>
              </div>
              <div v-if="expandedBooks[index]" class="book-log-details">
                <div
                  v-for="(detail, detailIndex) in bookLog.details"
                  :key="detailIndex"
                  class="book-log-detail-line"
                >
                  {{ detail }}
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Actions -->
        <div class="migration-actions">
          <button
            v-if="migrationProgress.is_running"
            @click="stopMigration"
            class="btn-stop"
          >
            ⏹️ Arrêter la liaison
          </button>
        </div>
      </div>
    </div>

    <!-- Message d'erreur -->
    <div v-if="error" class="error-message">
      {{ error }}
    </div>

    <!-- Liste des cas problématiques -->
    <div v-if="problematicCases.length > 0" class="cases-list">
      <h2>Cas à traiter manuellement ({{ problematicCases.length }})</h2>

      <div v-for="cas in problematicCases" :key="cas.livre_id" class="case-card">
        <div class="case-header">
          <h3>{{ cas.titre_attendu }}</h3>
          <span class="author">{{ cas.auteur }}</span>
        </div>

        <div class="case-body">
          <div class="case-info">
            <div class="info-row">
              <span class="label">Raison:</span>
              <span class="value reason">{{ cas.raison }}</span>
            </div>
            <div v-if="cas.titre_trouve" class="info-row">
              <span class="label">Titre trouvé:</span>
              <span class="value">{{ cas.titre_trouve }}</span>
            </div>
            <div v-if="cas.url_babelio && cas.url_babelio !== 'N/A'" class="info-row">
              <span class="label">URL Babelio:</span>
              <a :href="cas.url_babelio" target="_blank" class="value link">
                {{ cas.url_babelio }}
              </a>
            </div>
            <div class="info-row">
              <span class="label">Date:</span>
              <span class="value">{{ formatDate(cas.timestamp) }}</span>
            </div>
          </div>

          <!-- Zone d'édition pour retry -->
          <div v-if="editingCase === cas.livre_id" class="edit-zone">
            <label>
              Nouveau titre à essayer:
              <input
                v-model="newTitle"
                type="text"
                class="input-title"
                placeholder="Entrez un nouveau titre"
              />
            </label>
          </div>

          <!-- Actions -->
          <div class="case-actions">
            <!-- Accepter la suggestion (si URL disponible) -->
            <button
              v-if="cas.url_babelio && cas.url_babelio !== 'N/A'"
              @click="acceptSuggestion(cas)"
              :disabled="processingCase === cas.livre_id"
              class="btn-accept"
            >
              ✓ Accepter suggestion
            </button>

            <!-- Marquer comme not found -->
            <button
              @click="markNotFound(cas)"
              :disabled="processingCase === cas.livre_id"
              class="btn-not-found"
            >
              ✗ Pas sur Babelio
            </button>

            <!-- Modifier et réessayer -->
            <button
              v-if="editingCase !== cas.livre_id"
              @click="startEditing(cas)"
              :disabled="processingCase === cas.livre_id"
              class="btn-edit"
            >
              ✎ Modifier titre
            </button>

            <!-- Sauvegarder le titre corrigé -->
            <button
              v-if="editingCase === cas.livre_id"
              @click="saveCorrectedTitle(cas)"
              :disabled="processingCase === cas.livre_id || !newTitle.trim()"
              class="btn-save"
              title="Sauvegarder le titre sans relancer la recherche Babelio"
            >
              💾 Sauvegarder titre
            </button>

            <!-- Valider le retry -->
            <button
              v-if="editingCase === cas.livre_id"
              @click="retryWithNewTitle(cas)"
              :disabled="processingCase === cas.livre_id || !newTitle.trim()"
              class="btn-retry"
              title="Corriger le titre ET relancer la recherche Babelio"
            >
              ↻ Réessayer Babelio
            </button>

            <!-- Annuler l'édition -->
            <button
              v-if="editingCase === cas.livre_id"
              @click="cancelEditing"
              class="btn-cancel"
            >
              Annuler
            </button>
          </div>

          <!-- Résultat du retry -->
          <div v-if="retryResults[cas.livre_id]" class="retry-result">
            <h4>Résultat de la recherche:</h4>
            <div class="result-content">
              <div><strong>Status:</strong> {{ retryResults[cas.livre_id].status }}</div>
              <div v-if="retryResults[cas.livre_id].babelio_suggestion_title">
                <strong>Titre trouvé:</strong> {{ retryResults[cas.livre_id].babelio_suggestion_title }}
              </div>
              <div v-if="retryResults[cas.livre_id].babelio_suggestion_author">
                <strong>Auteur:</strong> {{ retryResults[cas.livre_id].babelio_suggestion_author }}
              </div>
              <div v-if="retryResults[cas.livre_id].babelio_url">
                <strong>URL:</strong>
                <a :href="retryResults[cas.livre_id].babelio_url" target="_blank">
                  {{ retryResults[cas.livre_id].babelio_url }}
                </a>
              </div>
              <div v-if="retryResults[cas.livre_id].confidence_score">
                <strong>Confiance:</strong> {{ (retryResults[cas.livre_id].confidence_score * 100).toFixed(1) }}%
              </div>
            </div>

            <!-- Bouton pour accepter le résultat du retry -->
            <div v-if="retryResults[cas.livre_id].babelio_url" class="retry-actions">
              <button
                @click="acceptSuggestionFromRetry(cas, retryResults[cas.livre_id])"
                :disabled="processingCase === cas.livre_id"
                class="btn-accept"
              >
                ✓ Accepter ce résultat
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Message si aucun cas -->
    <div v-else-if="!loading" class="no-cases">
      <p>Aucun cas problématique à traiter! 🎉</p>
    </div>
    </main>
  </div>
</template>

<script>
import axios from 'axios';
import Navigation from '../components/Navigation.vue';

export default {
  name: 'BabelioMigration',
  components: {
    Navigation,
  },
  data() {
    return {
      status: null,
      problematicCases: [],
      loading: false,
      error: null,
      editingCase: null,
      newTitle: '',
      processingCase: null,
      retryResults: {},
      toast: null,
      migrationProgress: {
        is_running: false,
        start_time: null,
        books_processed: 0,
        last_update: null,
        book_logs: [],
      },
      expandedBooks: {},
      progressInterval: null,
    };
  },
  mounted() {
    this.loadData();
    this.checkMigrationProgress();
    // Poll progress every 2 seconds when migration is running
    this.progressInterval = setInterval(() => {
      if (this.migrationProgress.is_running) {
        this.checkMigrationProgress();
        this.loadData(); // Refresh status to see pending count decrease
      }
    }, 2000);
  },
  beforeUnmount() {
    if (this.progressInterval) {
      clearInterval(this.progressInterval);
    }
  },
  methods: {
    showToast(message, type = 'success') {
      this.toast = { message, type };
      setTimeout(() => {
        this.toast = null;
      }, 3000); // Disparaît après 3 secondes
    },

    async loadData() {
      this.loading = true;
      this.error = null;

      try {
        // Charger le statut
        const statusRes = await axios.get('/api/babelio-migration/status');
        this.status = statusRes.data;

        // Charger les cas problématiques
        const casesRes = await axios.get('/api/babelio-migration/problematic-cases');
        this.problematicCases = casesRes.data;
      } catch (err) {
        this.error = `Erreur lors du chargement: ${err.response?.data?.error || err.message}`;
        console.error('Erreur chargement:', err);
      } finally {
        this.loading = false;
      }
    },

    async acceptSuggestion(cas) {
      this.processingCase = cas.livre_id;

      try {
        const response = await axios.post('/api/babelio-migration/accept-suggestion', {
          livre_id: cas.livre_id,
          babelio_url: cas.url_babelio,
          babelio_author_url: null,
          corrected_title: cas.titre_trouve || null,
        });

        this.showToast(response.data.message || `✓ "${cas.titre_attendu}" accepté!`, 'success');
        await this.loadData();
      } catch (err) {
        this.showToast(`Erreur: ${err.response?.data?.message || err.message}`, 'error');
      } finally {
        this.processingCase = null;
      }
    },

    async markNotFound(cas) {
      this.processingCase = cas.livre_id;

      try {
        const response = await axios.post('/api/babelio-migration/mark-not-found', {
          livre_id: cas.livre_id,
          reason: 'Livre non disponible sur Babelio',
        });

        this.showToast(response.data.message || `✗ "${cas.titre_attendu}" marqué not found`, 'info');
        await this.loadData();
      } catch (err) {
        this.showToast(`Erreur: ${err.response?.data?.message || err.message}`, 'error');
      } finally {
        this.processingCase = null;
      }
    },

    startEditing(cas) {
      this.editingCase = cas.livre_id;
      this.newTitle = cas.titre_attendu;
      // Clear previous retry result
      delete this.retryResults[cas.livre_id];
    },

    cancelEditing() {
      this.editingCase = null;
      this.newTitle = '';
    },

    async saveCorrectedTitle(cas) {
      this.processingCase = cas.livre_id;

      try {
        const response = await axios.post('/api/babelio-migration/correct-title', {
          livre_id: cas.livre_id,
          new_title: this.newTitle.trim(),
        });

        this.showToast(response.data.message || `✏️ Titre corrigé: "${this.newTitle}"`, 'success');
        this.editingCase = null;
        this.newTitle = '';
        await this.loadData();
      } catch (err) {
        this.showToast(`Erreur: ${err.response?.data?.message || err.message}`, 'error');
      } finally {
        this.processingCase = null;
      }
    },

    async retryWithNewTitle(cas) {
      this.processingCase = cas.livre_id;

      try {
        const response = await axios.post('/api/babelio-migration/retry-with-title', {
          livre_id: cas.livre_id,
          new_title: this.newTitle.trim(),
          author: cas.auteur || null,
        });

        // Store the result - force Vue reactivity by creating new object
        this.retryResults = {
          ...this.retryResults,
          [cas.livre_id]: response.data
        };

        if (response.data.status === 'verified' || response.data.status === 'corrected') {
          this.showToast(`✓ Livre trouvé: "${response.data.babelio_suggestion_title}"`, 'success');
        } else {
          this.showToast(`Livre non trouvé (${response.data.status})`, 'warning');
        }
      } catch (err) {
        this.showToast(`Erreur: ${err.response?.data?.message || err.message}`, 'error');
      } finally {
        this.processingCase = null;
      }
    },

    async acceptSuggestionFromRetry(cas, retryData) {
      this.processingCase = cas.livre_id;

      try {
        const response = await axios.post('/api/babelio-migration/accept-suggestion', {
          livre_id: cas.livre_id,
          babelio_url: retryData.babelio_url,
          babelio_author_url: retryData.babelio_author_url || null,
          corrected_title: retryData.babelio_suggestion_title || null,
        });

        this.showToast(response.data.message || '✓ Suggestion acceptée!', 'success');
        await this.loadData();
        this.cancelEditing();
      } catch (err) {
        this.showToast(`Erreur: ${err.response?.data?.message || err.message}`, 'error');
      } finally {
        this.processingCase = null;
      }
    },

    async toggleMigration() {
      if (this.migrationProgress.is_running) {
        await this.stopMigration();
      } else {
        await this.startMigration();
      }
    },

    async startMigration() {
      try {
        const response = await axios.post('/api/babelio-migration/start');

        if (response.data.status === 'started') {
          this.showToast('Migration démarrée!', 'success');
          this.migrationProgress.is_running = true;
          // Start polling immediately
          this.checkMigrationProgress();
        } else if (response.data.status === 'already_running') {
          this.showToast('Migration déjà en cours', 'info');
        } else {
          this.showToast(`Erreur: ${response.data.message}`, 'error');
        }
      } catch (err) {
        this.showToast(`Erreur: ${err.response?.data?.message || err.message}`, 'error');
      }
    },

    async stopMigration() {
      try {
        const response = await axios.post('/api/babelio-migration/stop');

        if (response.data.status === 'stopped') {
          this.showToast('Migration arrêtée', 'info');
          this.migrationProgress.is_running = false;
        } else {
          this.showToast(`Erreur: ${response.data.message}`, 'error');
        }
      } catch (err) {
        this.showToast(`Erreur: ${err.response?.data?.message || err.message}`, 'error');
      }
    },

    async checkMigrationProgress() {
      try {
        const response = await axios.get('/api/babelio-migration/progress');
        this.migrationProgress = response.data;
      } catch (err) {
        console.error('Error checking migration progress:', err);
      }
    },

    formatDate(timestamp) {
      if (!timestamp) return 'N/A';
      return new Date(timestamp).toLocaleString('fr-FR');
    },

    toggleBookLog(index) {
      this.expandedBooks = {
        ...this.expandedBooks,
        [index]: !this.expandedBooks[index]
      };
    },

    getStatusIcon(status) {
      const icons = {
        'success': '✅',
        'error': '❌',
        'not_found': '❌',
        'none': '❌'
      };
      return icons[status] || '❓';
    },
  },
};
</script>

<style scoped>
.babelio-migration {
  position: relative;
}

main {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

/* Toast Notification */
.toast {
  position: fixed;
  top: 20px;
  right: 20px;
  padding: 16px 24px;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  z-index: 1000;
  font-weight: 500;
  animation: slideIn 0.3s ease-out;
  min-width: 300px;
  max-width: 500px;
}

@keyframes slideIn {
  from {
    transform: translateX(400px);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}

.toast.success {
  background: #28a745;
  color: white;
}

.toast.error {
  background: #dc3545;
  color: white;
}

.toast.warning {
  background: #ffc107;
  color: #333;
}

.toast.info {
  background: #17a2b8;
  color: white;
}

h1 {
  color: #2c3e50;
  margin-bottom: 30px;
}

h2 {
  color: #34495e;
  margin: 20px 0 15px 0;
}

/* Status Panel */
.status-panel {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 30px;
}

.stats-section-title {
  margin: 20px 0 10px 0;
  color: #495057;
  font-size: 1.1em;
  font-weight: 600;
  border-bottom: 2px solid #dee2e6;
  padding-bottom: 8px;
}

.stats-section-title:first-of-type {
  margin-top: 10px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 15px;
  margin-top: 15px;
}

.stat-card {
  background: white;
  border-radius: 6px;
  padding: 15px;
  text-align: center;
  border: 2px solid #dee2e6;
}

.stat-card.success {
  border-color: #28a745;
}

.stat-card.warning {
  border-color: #ffc107;
}

.stat-card.info {
  border-color: #17a2b8;
}

.stat-card.pending {
  border-color: #6c757d;
}

.stat-card.clickable {
  cursor: pointer;
  transition: all 0.2s ease;
  position: relative;
}

.stat-card.clickable:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0,0,0,0.1);
  border-color: #495057;
}

.stat-card.migration-running {
  border-color: #007bff;
  background: linear-gradient(135deg, #ffffff 0%, #e3f2fd 100%);
}

.migration-indicator {
  margin-top: 10px;
}

.spinner {
  width: 20px;
  height: 20px;
  border: 3px solid #f3f3f3;
  border-top: 3px solid #007bff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.stat-card.pending {
  border-color: #6c757d;
}

/* Migration Button */
.migration-button-container {
  margin: 30px 0;
  text-align: center;
}

.btn-migration {
  background: linear-gradient(135deg, #007bff 0%, #0056b3 100%);
  color: white;
  border: none;
  padding: 15px 40px;
  font-size: 1.1em;
  font-weight: 600;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 4px 6px rgba(0, 123, 255, 0.3);
  display: inline-flex;
  align-items: center;
  gap: 10px;
}

.btn-migration:hover:not(:disabled) {
  background: linear-gradient(135deg, #0056b3 0%, #003d82 100%);
  transform: translateY(-2px);
  box-shadow: 0 6px 12px rgba(0, 123, 255, 0.4);
}

.btn-migration:disabled {
  background: #6c757d;
  cursor: not-allowed;
  opacity: 0.6;
  box-shadow: none;
}

.btn-migration.migration-running {
  background: linear-gradient(135deg, #dc3545 0%, #c82333 100%);
  box-shadow: 0 4px 6px rgba(220, 53, 69, 0.3);
}

.btn-migration.migration-running:hover {
  background: linear-gradient(135deg, #c82333 0%, #a71d2a 100%);
}

.spinner-inline {
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 2px solid #f3f3f3;
  border-top: 2px solid #007bff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-right: 8px;
}

/* Legend Section */
.legend-section {
  background: #f8f9fa;
  border: 1px solid #dee2e6;
  border-radius: 8px;
  padding: 20px;
  margin: 20px 0;
}

.legend-section h3 {
  margin-top: 0;
  margin-bottom: 15px;
  color: #2c3e50;
  font-size: 1.1em;
}

.legend-section ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.legend-section li {
  padding: 8px 0;
  border-bottom: 1px solid #e9ecef;
  color: #495057;
  line-height: 1.6;
}

.legend-section li:last-child {
  border-bottom: none;
}

.legend-section strong {
  color: #2c3e50;
}

.stat-value {
  font-size: 2em;
  font-weight: bold;
  color: #2c3e50;
}

.stat-label {
  font-size: 0.9em;
  color: #6c757d;
  margin-top: 5px;
}

/* Error Message */
.error-message {
  background: #f8d7da;
  color: #721c24;
  padding: 15px;
  border-radius: 4px;
  margin: 20px 0;
  border: 1px solid #f5c6cb;
}

/* No Cases */
.no-cases {
  text-align: center;
  padding: 40px;
  background: #f8f9fa;
  border-radius: 8px;
  font-size: 1.2em;
  color: #6c757d;
}

/* Cases List */
.cases-list {
  margin-top: 30px;
}

.case-card {
  background: white;
  border: 1px solid #dee2e6;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 20px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.case-header {
  border-bottom: 2px solid #e9ecef;
  padding-bottom: 10px;
  margin-bottom: 15px;
}

.case-header h3 {
  margin: 0 0 5px 0;
  color: #2c3e50;
}

.case-header .author {
  color: #6c757d;
  font-style: italic;
}

.case-body {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.case-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.info-row {
  display: flex;
  gap: 10px;
  align-items: baseline;
}

.info-row .label {
  font-weight: bold;
  color: #495057;
  min-width: 120px;
}

.info-row .value {
  color: #212529;
}

.info-row .value.reason {
  color: #dc3545;
  font-weight: 500;
}

.info-row .value.link {
  color: #007bff;
  text-decoration: none;
  word-break: break-all;
}

.info-row .value.link:hover {
  text-decoration: underline;
}

/* Edit Zone */
.edit-zone {
  background: #e7f3ff;
  padding: 15px;
  border-radius: 4px;
}

.edit-zone label {
  display: block;
  font-weight: 500;
  margin-bottom: 8px;
}

.input-title {
  width: 100%;
  padding: 8px;
  border: 1px solid #ced4da;
  border-radius: 4px;
  font-size: 1em;
}

/* Actions */
.case-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  padding-top: 10px;
  border-top: 1px solid #e9ecef;
}

.case-actions button {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.95em;
  transition: all 0.2s;
}

.case-actions button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-accept {
  background: #28a745;
  color: white;
}

.btn-accept:hover:not(:disabled) {
  background: #218838;
}

.btn-not-found {
  background: #dc3545;
  color: white;
}

.btn-not-found:hover:not(:disabled) {
  background: #c82333;
}

.btn-edit {
  background: #ffc107;
  color: #212529;
}

.btn-edit:hover:not(:disabled) {
  background: #e0a800;
}

.btn-save {
  background: #17a2b8;
  color: white;
}

.btn-save:hover:not(:disabled) {
  background: #117a8b;
}

.btn-retry {
  background: #007bff;
  color: white;
}

.btn-retry:hover:not(:disabled) {
  background: #0056b3;
}

.btn-cancel {
  background: #6c757d;
  color: white;
}

.btn-cancel:hover {
  background: #5a6268;
}

/* Retry Result */
.retry-result {
  background: #d4edda;
  border: 1px solid #c3e6cb;
  border-radius: 4px;
  padding: 15px;
  margin-top: 10px;
}

.retry-result h4 {
  margin: 0 0 10px 0;
  color: #155724;
}

.result-content {
  display: flex;
  flex-direction: column;
  gap: 5px;
  font-size: 0.95em;
}

.result-content a {
  color: #007bff;
  text-decoration: none;
  word-break: break-all;
}

.result-content a:hover {
  text-decoration: underline;
}

.retry-actions {
  margin-top: 15px;
  display: flex;
  gap: 10px;
}

.retry-actions button {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.95em;
  transition: all 0.2s;
}

/* Migration Progress Panel */
.migration-progress-panel {
  background: #f8f9fa;
  border: 2px solid #007bff;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 30px;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  margin-bottom: 15px;
  padding-bottom: 10px;
  border-bottom: 1px solid #dee2e6;
}

.progress-header h3 {
  margin: 0;
  color: #007bff;
}

.progress-summary {
  display: flex;
  gap: 20px;
  margin-bottom: 15px;
  flex-wrap: wrap;
}

.progress-stat {
  font-size: 0.95em;
  color: #495057;
}

.migration-actions {
  margin-top: 15px;
  display: flex;
  gap: 10px;
}

.btn-stop {
  padding: 10px 20px;
  background: #dc3545;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1em;
  font-weight: 500;
}

.btn-stop:hover {
  background: #c82333;
}

/* Book Logs Section */
.book-logs-section {
  margin-top: 20px;
  padding-top: 15px;
  border-top: 1px solid #dee2e6;
}

.book-logs-section h4 {
  margin: 0 0 15px 0;
  color: #495057;
  font-size: 1em;
  font-weight: 600;
}

.book-logs-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.book-log-item {
  background: #ffffff;
  border: 1px solid #dee2e6;
  border-radius: 4px;
  overflow: hidden;
}

.book-log-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 15px;
  cursor: pointer;
  transition: background-color 0.2s;
  user-select: none;
}

.book-log-header:hover {
  background-color: #f8f9fa;
}

.book-log-title {
  flex: 1;
  font-weight: 500;
  color: #2c3e50;
  font-size: 0.95em;
}

.book-log-status {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 1.1em;
}

.expand-toggle-book {
  color: #6c757d;
  font-size: 0.9em;
  margin-left: 5px;
}

.book-log-details {
  padding: 10px 15px;
  background: #f8f9fa;
  border-top: 1px solid #dee2e6;
  font-family: 'Courier New', monospace;
  font-size: 0.85em;
}

.book-log-detail-line {
  margin-bottom: 3px;
  white-space: pre-wrap;
  word-break: break-word;
  color: #495057;
  line-height: 1.4;
}
</style>
