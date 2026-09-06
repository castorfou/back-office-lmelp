<template>
  <div class="rss-monitoring">
    <Navigation pageTitle="Monitoring RSS Le Masque et la Plume" />

    <main>
      <!-- Déclenchement manuel -->
      <section class="card sync-section">
        <h2>🔄 Synchronisation RSS</h2>
        <p class="section-help">
          Télécharge les nouveaux épisodes "livres" (&gt; 15 min) détectés sur le
          flux RSS Le Masque et la Plume et les insère en base.
        </p>

        <button
          @click="triggerSync"
          class="btn btn-primary"
          :disabled="loading.sync"
        >
          🔄 Rafraîchir Episodes
        </button>

        <div v-if="lastSyncResult" class="last-sync-result">
          <span
            class="badge"
            :class="lastSyncResult.status === 'success' ? 'badge-ok' : 'badge-expired'"
          >
            {{ lastSyncResult.status }}
          </span>
          {{ lastSyncResult.episodes.length }} épisode(s) traité(s)
        </div>
      </section>

      <!-- Historique -->
      <section class="card history-section">
        <div class="section-header">
          <h2>📋 Historique des synchronisations</h2>
          <button @click="loadLogs" class="btn btn-secondary" :disabled="loading.logs">
            🔄 Rafraîchir
          </button>
        </div>

        <div v-if="loading.logs" class="loading">Chargement...</div>
        <div v-else-if="logs.length === 0" class="empty-state">
          Aucune synchronisation enregistrée
        </div>

        <div v-else class="logs-table-wrapper">
          <table class="logs-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Déclenchement</th>
                <th>Statut</th>
                <th>Épisodes</th>
              </tr>
            </thead>
            <tbody>
              <template v-for="log in logs" :key="log._id">
                <tr class="log-row" @click="toggleDetail(log._id)">
                  <td class="td-date">{{ formatDate(log.started_at) }}</td>
                  <td>{{ log.trigger }}</td>
                  <td>
                    <span class="badge" :class="statusBadgeClass(log.status)">{{ log.status }}</span>
                  </td>
                  <td>{{ (log.episodes || []).length }}</td>
                </tr>
                <tr v-if="expandedLogId === log._id" class="detail-row">
                  <td colspan="4">
                    <div v-if="loading.detail" class="loading">Chargement...</div>
                    <div v-else-if="detailedLog" class="log-detail">
                      <div v-if="detailedLog.error_message" class="error-message">
                        {{ detailedLog.error_message }}
                      </div>
                      <ul>
                        <li v-for="(ep, idx) in detailedLog.episodes" :key="idx">
                          <span class="episode-date">{{ formatEpisodeDate(ep.date) }}</span>
                          <strong>{{ ep.titre }}</strong> —
                          <span class="badge" :class="outcomeBadgeClass(ep.outcome)">{{ ep.outcome }}</span>
                          <span v-if="ep.error_message"> : {{ ep.error_message }}</span>
                        </li>
                      </ul>
                    </div>
                  </td>
                </tr>
              </template>
            </tbody>
          </table>
        </div>
      </section>
    </main>
  </div>
</template>

<script>
import Navigation from '../components/Navigation.vue';
import axios from 'axios';

export default {
  name: 'RssMonitoring',
  components: { Navigation },

  data() {
    return {
      logs: [],
      lastSyncResult: null,
      expandedLogId: null,
      detailedLog: null,
      loading: { sync: false, logs: false, detail: false },
    };
  },

  mounted() {
    this.loadLogs();
  },

  methods: {
    async triggerSync() {
      this.loading.sync = true;
      try {
        const res = await axios.post('/api/rss/sync', { trigger: 'manual' });
        this.lastSyncResult = res.data;
        await this.loadLogs();
      } catch (e) {
        console.error('Erreur déclenchement synchronisation RSS', e);
      } finally {
        this.loading.sync = false;
      }
    },

    async loadLogs() {
      this.loading.logs = true;
      try {
        const res = await axios.get('/api/rss/logs');
        this.logs = res.data;
      } catch (e) {
        console.error('Erreur chargement historique RSS', e);
      } finally {
        this.loading.logs = false;
      }
    },

    async toggleDetail(logId) {
      if (this.expandedLogId === logId) {
        this.expandedLogId = null;
        this.detailedLog = null;
        return;
      }
      this.expandedLogId = logId;
      this.detailedLog = null;
      this.loading.detail = true;
      try {
        const res = await axios.get(`/api/rss/logs/${logId}`);
        this.detailedLog = res.data;
      } catch (e) {
        console.error('Erreur chargement détail synchronisation RSS', e);
      } finally {
        this.loading.detail = false;
      }
    },

    statusBadgeClass(status) {
      if (status === 'success') return 'badge-ok';
      if (status === 'partial_error') return 'badge-warning';
      return 'badge-expired';
    },

    outcomeBadgeClass(outcome) {
      if (outcome === 'downloaded') return 'badge-ok';
      if (outcome === 'already_exists' || outcome === 'skipped_not_book') return 'badge-network';
      return 'badge-expired';
    },

    formatDate(value) {
      if (!value) return '—';
      return new Date(value).toLocaleString('fr-FR', {
        day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit'
      });
    },

    formatEpisodeDate(value) {
      if (!value) return '—';
      return new Date(value).toLocaleDateString('fr-FR', {
        day: '2-digit', month: '2-digit', year: '2-digit'
      });
    },
  },
};
</script>

<style scoped>
.rss-monitoring main {
  padding: 1.5rem;
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.card {
  background: white;
  border-radius: 8px;
  padding: 1.5rem;
  box-shadow: 0 1px 4px rgba(0,0,0,0.1);
}

h2 {
  margin: 0 0 1rem;
  font-size: 1.2rem;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}
.section-header h2 { margin: 0; }

.section-help {
  color: #666;
  font-size: 0.9rem;
  margin-bottom: 1rem;
}

.last-sync-result { margin-top: 1rem; }

.btn {
  padding: 0.4rem 0.9rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
}
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-primary { background: #007bff; color: white; }
.btn-secondary { background: #6c757d; color: white; }

.badge {
  display: inline-block;
  padding: 0.15rem 0.5rem;
  border-radius: 10px;
  font-size: 0.8rem;
  font-weight: 600;
}
.badge-ok { background: #d4edda; color: #155724; }
.badge-warning { background: #fff3cd; color: #856404; }
.badge-expired { background: #f8d7da; color: #721c24; }
.badge-network { background: #e2e3e5; color: #383d41; }

.logs-table-wrapper { overflow-x: auto; }
.logs-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
}
.logs-table th {
  text-align: left;
  padding: 0.5rem 0.75rem;
  background: #f8f9fa;
  border-bottom: 2px solid #dee2e6;
}
.logs-table td {
  padding: 0.4rem 0.75rem;
  border-bottom: 1px solid #f0f0f0;
}
.log-row { cursor: pointer; }
.log-row:hover { background: #f8f9fa; }
.detail-row td { background: #fafafa; }
.log-detail ul { margin: 0; padding-left: 1.2rem; }
.error-message { color: #721c24; margin-bottom: 0.5rem; }
.episode-date { color: #666; font-variant-numeric: tabular-nums; margin-right: 0.4rem; }

.loading { color: #666; font-style: italic; padding: 1rem 0; }
.empty-state { color: #999; font-style: italic; padding: 1rem 0; }
</style>
