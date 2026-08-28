<template>
  <div class="orphaned-avis-container">
    <Navigation pageTitle="Nettoyage des Avis Orphelins" />

    <main>
      <section v-if="statistics" class="card statistics-card">
        <h2>Statistiques</h2>
        <div class="stats-grid">
          <div class="stat-item">
            <span class="stat-label">Avis orphelins</span>
            <span class="stat-value">{{ statistics.orphaned_count }}</span>
          </div>
        </div>
      </section>

      <div v-if="loading" class="loading">
        Chargement des avis orphelins...
      </div>

      <div v-if="error" class="alert alert-error">
        {{ error }}
      </div>

      <div v-if="!loading && !error && orphanedAvis.length === 0" class="empty-state">
        <p>Aucun avis orphelin détecté ! 🎉</p>
      </div>

      <div v-if="!loading && !error && orphanedAvis.length > 0" class="groups-container">
        <div class="groups-header">
          <h2>📝 Avis orphelins ({{ orphanedAvis.length }})</h2>
        </div>

        <div class="groups-list">
          <div v-for="avis in orphanedAvis" :key="avis.id" class="group-card">
            <div class="group-header">
              <div class="group-info">
                <h3>{{ avis.livre_titre_extrait || 'Titre inconnu' }}</h3>
                <p class="group-count">{{ avis.auteur_nom_extrait }} — {{ avis.critique_nom_extrait }}</p>
                <p class="orphan-oid">livre_oid orphelin : <code>{{ avis.livre_oid }}</code></p>
                <p v-if="avis.suggested_livre_id" class="suggestion-found">
                  📚 Livre trouvé en base : <strong>{{ avis.suggested_livre_titre }}</strong>
                </p>
                <p v-if="avis.commentaire" class="commentaire">{{ avis.commentaire }}</p>
              </div>
              <div class="group-actions">
                <button
                  v-if="avis.suggested_livre_id"
                  class="btn btn-merge"
                  data-testid="repoint-suggested"
                  @click="confirmRepoint(avis, { id: avis.suggested_livre_id, titre: avis.suggested_livre_titre })"
                >
                  Repointer vers ce livre
                </button>
                <button class="btn btn-merge" @click="startRepoint(avis)">
                  Repointer vers un autre livre
                </button>
                <button v-if="!avis.suggested_livre_id" class="btn btn-danger" @click="removeAvis(avis)">
                  Supprimer
                </button>
              </div>
            </div>

            <div v-if="repointingAvisId === avis.id" class="repoint-form">
              <input
                v-model="bookSearchQuery"
                type="text"
                placeholder="Rechercher un livre par titre (3 caractères min)..."
                @input="searchBooks"
              />
              <ul v-if="bookSearchResults.length > 0" class="search-results">
                <li
                  v-for="book in bookSearchResults"
                  :key="book._id"
                  @click="confirmRepoint(avis, { id: book._id, titre: book.titre })"
                >
                  {{ book.auteur_nom ? `${book.auteur_nom} — ${book.titre}` : book.titre }}
                </li>
              </ul>
            </div>

            <div v-if="repointResults[avis.id]" class="merge-result">
              <div v-if="repointResults[avis.id].success" class="result-success">
                ✓ Avis repointé avec succès
              </div>
              <div v-else class="result-error">
                ✗ Erreur: {{ repointResults[avis.id].error }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script>
import Navigation from '../components/Navigation.vue';
import { avisService, searchService } from '../services/api.js';

export default {
  name: 'OrphanedAvis',

  components: {
    Navigation
  },

  data() {
    return {
      statistics: null,
      orphanedAvis: [],
      loading: false,
      error: null,
      repointingAvisId: null,
      bookSearchQuery: '',
      bookSearchResults: [],
      repointResults: {}
    };
  },

  mounted() {
    this.loadData();
  },

  methods: {
    async loadData() {
      this.loading = true;
      this.error = null;

      try {
        const [stats, avis] = await Promise.all([
          avisService.getOrphanedAvisStatistics(),
          avisService.getOrphanedAvis()
        ]);
        this.statistics = stats;
        this.orphanedAvis = avis;
      } catch (err) {
        this.error = `Erreur lors du chargement: ${err.message}`;
        console.error('Load orphaned avis error:', err);
      } finally {
        this.loading = false;
      }
    },

    startRepoint(avis) {
      this.repointingAvisId = avis.id;
      this.bookSearchQuery = '';
      this.bookSearchResults = [];
    },

    async searchBooks() {
      if (!this.bookSearchQuery || this.bookSearchQuery.trim().length < 3) {
        this.bookSearchResults = [];
        return;
      }

      try {
        const results = await searchService.advancedSearch(this.bookSearchQuery, ['livres']);
        this.bookSearchResults = results.livres || [];
      } catch (err) {
        console.error('Book search error:', err);
        this.bookSearchResults = [];
      }
    },

    async confirmRepoint(avis, book) {
      try {
        await avisService.updateAvis(avis.id, { livre_oid: book.id });
        this.repointResults = {
          ...this.repointResults,
          [avis.id]: { success: true }
        };
        this.repointingAvisId = null;
        await this.loadData();
      } catch (err) {
        this.repointResults = {
          ...this.repointResults,
          [avis.id]: { success: false, error: err.message }
        };
      }
    },

    async removeAvis(avis) {
      const label = avis.livre_titre_extrait || avis.id;
      if (!confirm(`Supprimer définitivement cet avis (${label}) ?`)) {
        return;
      }

      try {
        await avisService.deleteAvis(avis.id);
        await this.loadData();
      } catch (err) {
        this.error = `Erreur lors de la suppression: ${err.message}`;
      }
    }
  }
};
</script>

<style scoped>
.orphaned-avis-container {
  padding: 0 2rem 2rem;
  max-width: 1400px;
  margin: 0 auto;
}

main {
  margin-top: 2rem;
}

.card {
  background: white;
  border-radius: 8px;
  padding: 1.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  margin-bottom: 2rem;
}

.statistics-card {
  background: #f8f9fa;
  border: 1px solid #e0e0e0;
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

.loading {
  text-align: center;
  padding: 3rem;
  color: #666;
  font-size: 1.1rem;
}

.empty-state {
  text-align: center;
  padding: 3rem;
  color: #666;
  font-size: 1.1rem;
  background: #f8f9fa;
  border-radius: 8px;
}

.alert {
  padding: 1rem;
  border-radius: 6px;
  margin-bottom: 1.5rem;
}

.alert-error {
  background: #f8d7da;
  color: #721c24;
  border: 1px solid #f5c6cb;
}

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

.orphan-oid {
  color: #721c24;
  font-size: 0.875rem;
  margin: 5px 0;
}

.orphan-oid code {
  background: #f8d7da;
  padding: 2px 6px;
  border-radius: 4px;
}

.commentaire {
  color: #495057;
  font-style: italic;
  margin: 5px 0;
}

.suggestion-found {
  color: #155724;
  background: #d4edda;
  padding: 6px 10px;
  border-radius: 4px;
  margin: 5px 0;
  font-size: 0.9rem;
}

.group-actions {
  display: flex;
  align-items: center;
  gap: 15px;
}

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

.btn-merge {
  background: #28a745;
  color: white;
}

.btn-merge:hover:not(:disabled) {
  background: #218838;
}

.btn-danger {
  background: #dc3545;
  color: white;
}

.btn-danger:hover:not(:disabled) {
  background: #c82333;
}

.repoint-form {
  margin-top: 15px;
  border-top: 1px solid #e9ecef;
  padding-top: 15px;
}

.repoint-form input {
  width: 100%;
  padding: 10px;
  border: 1px solid #ced4da;
  border-radius: 6px;
  font-size: 1rem;
}

.search-results {
  list-style: none;
  margin: 10px 0 0;
  padding: 0;
  border: 1px solid #dee2e6;
  border-radius: 6px;
  max-height: 200px;
  overflow-y: auto;
}

.search-results li {
  padding: 10px;
  cursor: pointer;
  border-bottom: 1px solid #f1f1f1;
}

.search-results li:last-child {
  border-bottom: none;
}

.search-results li:hover {
  background: #f8f9fa;
}

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
