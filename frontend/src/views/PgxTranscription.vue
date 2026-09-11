<template>
  <div class="pgx-transcription">
    <Navigation pageTitle="Transcription PGX" />

    <main>
      <section id="pgx" class="card pgx-section">
        <div class="section-header">
          <h2>🖥️ Téléchargement transcription PGX</h2>
          <button
            data-testid="pgx-refresh-button"
            class="btn btn-secondary"
            :disabled="refreshing"
            @click="refreshStatus"
          >
            🔄 Rafraîchir le statut
          </button>
        </div>
        <p class="section-help">
          Lance/suit le pipeline de transcription automatisée via la station GPU PGX
          pour tous les épisodes en attente.
        </p>

        <div v-if="pgxMissingVars.length > 0" class="pgx-config-warning">
          Configuration PGX incomplète — variables manquantes :
          {{ pgxMissingVars.join(', ') }}
        </div>

        <div class="pgx-diagnostics">
          <div
            v-for="diag in pgxDiagnosticsDisplay"
            :key="diag.name"
            class="pgx-diag-row"
          >
            <span class="badge" :class="pgxStatusBadgeClass(diag.status)">
              {{ pgxStatusIcon(diag.status) }}
            </span>
            <strong>{{ diag.name }}</strong> — {{ diag.detail }}
          </div>
        </div>

        <div v-if="sshPublicKey" data-testid="pgx-ssh-public-key" class="pgx-ssh-key-section">
          <p class="pgx-ssh-key-label">Clé SSH dédiée — à autoriser sur PGX :</p>
          <pre class="pgx-ssh-key-block"><code>{{ sshPublicKey }}</code></pre>
          <p class="pgx-ssh-key-label">Commande à exécuter sur PGX :</p>
          <pre class="pgx-ssh-key-block"><code>echo '{{ sshPublicKey }}' >> ~/.ssh/authorized_keys</code></pre>
        </div>

        <template v-if="pgxMissingVars.length === 0">
          <div v-if="pgxEpisodes.length > 0" class="pgx-episodes-summary">
            <p class="pgx-episodes-count">{{ pgxEpisodes.length }} épisode(s) seront traités :</p>
            <ul class="pgx-episodes-list">
              <li v-for="ep in pgxEpisodes" :key="ep.id">
                <span class="episode-date">{{ formatEpisodeDate(ep.date) }}</span>
                <strong>{{ ep.titre }}</strong>
              </li>
            </ul>
          </div>
          <div v-else class="empty-state">Aucun épisode en attente de transcription</div>

          <button
            data-testid="pgx-start-button"
            class="btn btn-primary"
            :disabled="!pgxReady || pgxEpisodes.length === 0 || pgxProgress.is_running"
            @click="startPgxTranscription"
          >
            ▶️ Lancer la transcription des épisodes en attente
          </button>
        </template>

        <div
          v-if="pgxProgress.is_running || pgxProgress.logs.length > 0"
          class="pgx-progress-panel"
        >
          <div class="progress-header">
            <strong v-if="pgxProgress.is_running">
              Transcription en cours — épisode
              {{ pgxProgress.current_episode_index + 1 }}/{{ pgxProgress.episode_ids.length }}
            </strong>
            <strong v-else>Traitement terminé</strong>
          </div>
          <div v-if="pgxProgress.retry_pending" class="pgx-retry-banner">
            ⏳ PGX injoignable — nouvelle tentative programmée
            <span v-if="pgxProgress.next_attempt_at">
              vers {{ formatDateTime(pgxProgress.next_attempt_at) }}
            </span>
          </div>
          <div v-if="pgxProgress.episode_ids.length > 0" class="progress-bar-container">
            <div class="progress-bar-track">
              <div
                class="progress-bar-fill"
                :style="{ width: pgxProgressPercentage + '%' }"
              ></div>
            </div>
            <div class="progress-bar-label">
              {{ pgxProgress.processed.length }} / {{ pgxProgress.episode_ids.length }}
              traité(s) ({{ pgxProgressPercentage }}%)
            </div>
          </div>
          <ul class="pgx-logs-list">
            <li v-for="(log, idx) in pgxProgress.logs" :key="idx">{{ log }}</li>
          </ul>
        </div>
      </section>

      <!-- Historique (Issue #309) -->
      <section class="card history-section">
        <div class="section-header">
          <h2>📋 Historique des transcriptions</h2>
          <button
            @click="loadPgxLogs"
            class="btn btn-secondary"
            :disabled="loadingPgxLogs"
          >
            🔄 Rafraîchir
          </button>
        </div>

        <div v-if="loadingPgxLogs" class="loading">Chargement...</div>
        <div v-else-if="pgxLogs.length === 0" class="empty-state">
          Aucune transcription enregistrée
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
              <template v-for="log in pgxLogs" :key="log._id">
                <tr class="pgx-log-row" @click="togglePgxLogDetail(log._id)">
                  <td class="td-date">{{ formatDateTime(log.started_at) }}</td>
                  <td>{{ log.trigger }}</td>
                  <td>
                    <span class="badge" :class="pgxLogStatusBadgeClass(log.status)">{{ log.status }}</span>
                  </td>
                  <td>{{ (log.episodes || []).length }}</td>
                </tr>
                <tr v-if="expandedPgxLogId === log._id" class="detail-row">
                  <td colspan="4">
                    <div v-if="loadingPgxLogDetail" class="loading">Chargement...</div>
                    <div v-else-if="detailedPgxLog" class="log-detail">
                      <div v-if="detailedPgxLog.error_message" class="error-message">
                        {{ detailedPgxLog.error_message }}
                      </div>
                      <ul>
                        <li v-for="(ep, idx) in detailedPgxLog.episodes" :key="idx">
                          <strong>{{ ep.titre }}</strong> —
                          <span class="badge" :class="ep.success ? 'badge-ok' : 'badge-expired'">
                            {{ ep.success ? 'succès' : 'échec' }}
                          </span>
                          <span v-if="ep.error"> : {{ ep.error }}</span>
                        </li>
                      </ul>
                      <div v-if="(detailedPgxLog.retry_attempts || []).length > 0" class="retry-attempts">
                        <p class="pgx-ssh-key-label">Tentatives de retry :</p>
                        <ul>
                          <li v-for="(attempt, idx) in detailedPgxLog.retry_attempts" :key="idx">
                            {{ formatDateTime(attempt.attempted_at) }} —
                            {{ attempt.reachable ? 'PGX joignable' : 'PGX injoignable' }}
                          </li>
                        </ul>
                      </div>
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

const PGX_DIAGNOSTIC_STEP_NAMES = [
  'Machine joignable',
  'Authentification SSH (clé dédiée)',
  'Répertoire audio distant',
  'Répertoire transcriptions distant',
];

export default {
  name: 'PgxTranscription',
  components: { Navigation },

  data() {
    return {
      pgxDiagnostics: [],
      pgxMissingVars: [],
      pgxEpisodes: [],
      sshPublicKey: null,
      pgxProgress: {
        is_running: false,
        episode_ids: [],
        current_episode_id: null,
        current_episode_index: 0,
        processed: [],
        start_time: null,
        logs: [],
        last_update: null,
        retry_pending: false,
        next_attempt_at: null,
      },
      pgxPollInterval: null,
      refreshing: false,
      pgxLogs: [],
      expandedPgxLogId: null,
      detailedPgxLog: null,
      loadingPgxLogs: false,
      loadingPgxLogDetail: false,
    };
  },

  computed: {
    pgxReady() {
      return (
        this.pgxMissingVars.length === 0 &&
        this.pgxDiagnostics.length > 0 &&
        this.pgxDiagnostics.every((d) => d.status === 'ok')
      );
    },

    pgxDiagnosticsDisplay() {
      // Issue #310: la checklist reste toujours visible, même quand la
      // config PGX est incomplète — dans ce cas le backend renvoie une
      // liste vide (pas d'appel réseau, piège lmelp #110), donc on affiche
      // les 4 étapes connues avec un statut "skipped" grisé plutôt que de
      // masquer toute la section derrière le seul message d'avertissement.
      if (this.pgxMissingVars.length > 0) {
        return PGX_DIAGNOSTIC_STEP_NAMES.map((name) => ({
          name,
          status: 'skipped',
          detail: 'Configuration PGX incomplète',
        }));
      }
      return this.pgxDiagnostics;
    },

    pgxProgressPercentage() {
      if (this.pgxProgress.episode_ids.length === 0) return 0;
      return Math.round(
        (this.pgxProgress.processed.length / this.pgxProgress.episode_ids.length) * 100
      );
    },
  },

  mounted() {
    this.loadPgxDiagnostics();
    this.loadPgxSshKey();
    this.loadPgxEpisodes();
    this.checkPgxProgress();
    this.loadPgxLogs();
  },

  beforeUnmount() {
    this.stopPgxPolling();
  },

  methods: {
    async refreshStatus() {
      this.refreshing = true;
      try {
        await Promise.all([
          this.loadPgxDiagnostics(),
          this.loadPgxSshKey(),
          this.loadPgxEpisodes(),
        ]);
      } finally {
        this.refreshing = false;
      }
    },

    async loadPgxDiagnostics() {
      try {
        const res = await axios.get('/api/pgx/diagnostics');
        this.pgxDiagnostics = res.data.diagnostics;
        this.pgxMissingVars = res.data.missing_vars;
      } catch (e) {
        console.error('Erreur chargement diagnostics PGX', e);
      }
    },

    async loadPgxSshKey() {
      try {
        const res = await axios.get('/api/pgx/ssh-key');
        this.sshPublicKey = res.data.public_key;
      } catch (e) {
        console.error('Erreur chargement clé SSH PGX', e);
      }
    },

    async loadPgxEpisodes() {
      try {
        const res = await axios.get('/api/pgx/episodes-without-transcription');
        this.pgxEpisodes = res.data.episodes;
      } catch (e) {
        console.error('Erreur chargement épisodes sans transcription', e);
      }
    },

    async checkPgxProgress() {
      try {
        const res = await axios.get('/api/pgx/transcription/progress');
        this.pgxProgress = res.data;
        if (!res.data.is_running && this.pgxPollInterval) {
          this.stopPgxPolling();
          await this.loadPgxEpisodes();
        }
      } catch (e) {
        console.error('Erreur récupération progression PGX', e);
      }
    },

    startPgxPolling() {
      if (this.pgxPollInterval) return;
      this.pgxPollInterval = setInterval(() => {
        this.checkPgxProgress();
      }, 2000);
    },

    stopPgxPolling() {
      if (this.pgxPollInterval) {
        clearInterval(this.pgxPollInterval);
        this.pgxPollInterval = null;
      }
    },

    async startPgxTranscription() {
      try {
        const res = await axios.post('/api/pgx/transcription/start');
        if (res.data.status === 'started') {
          this.pgxProgress.is_running = true;
          this.startPgxPolling();
          await this.checkPgxProgress();
        }
      } catch (e) {
        console.error('Erreur déclenchement transcription PGX', e);
      }
    },

    pgxStatusIcon(status) {
      if (status === 'ok') return '🟢';
      if (status === 'fail') return '🔴';
      return '⚪';
    },

    pgxStatusBadgeClass(status) {
      if (status === 'ok') return 'badge-ok';
      if (status === 'fail') return 'badge-expired';
      return 'badge-network';
    },

    formatEpisodeDate(value) {
      if (!value) return '—';
      return new Date(value).toLocaleDateString('fr-FR', {
        day: '2-digit', month: '2-digit', year: '2-digit'
      });
    },

    formatDateTime(value) {
      if (!value) return '—';
      return new Date(value).toLocaleString('fr-FR', {
        day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit'
      });
    },

    async loadPgxLogs() {
      this.loadingPgxLogs = true;
      try {
        const res = await axios.get('/api/pgx/logs');
        this.pgxLogs = res.data;
      } catch (e) {
        console.error('Erreur chargement historique PGX', e);
      } finally {
        this.loadingPgxLogs = false;
      }
    },

    async togglePgxLogDetail(logId) {
      if (this.expandedPgxLogId === logId) {
        this.expandedPgxLogId = null;
        this.detailedPgxLog = null;
        return;
      }
      this.expandedPgxLogId = logId;
      this.detailedPgxLog = null;
      this.loadingPgxLogDetail = true;
      try {
        const res = await axios.get(`/api/pgx/logs/${logId}`);
        this.detailedPgxLog = res.data;
      } catch (e) {
        console.error('Erreur chargement détail transcription PGX', e);
      } finally {
        this.loadingPgxLogDetail = false;
      }
    },

    pgxLogStatusBadgeClass(status) {
      if (status === 'success') return 'badge-ok';
      if (status === 'partial_error') return 'badge-warning';
      return 'badge-expired';
    },
  },
};
</script>

<style scoped>
.pgx-transcription main {
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
.badge-expired { background: #f8d7da; color: #721c24; }
.badge-network { background: #e2e3e5; color: #383d41; }

.empty-state { color: #999; font-style: italic; padding: 1rem 0; }

.pgx-config-warning {
  background: #fff3cd;
  color: #856404;
  padding: 0.75rem 1rem;
  border-radius: 4px;
  margin-bottom: 1rem;
}

.pgx-diagnostics { margin-bottom: 1rem; }
.pgx-diag-row { padding: 0.25rem 0; font-size: 0.9rem; }

.pgx-ssh-key-section {
  margin-bottom: 1rem;
  padding: 0.75rem 1rem;
  background: #f8f9fa;
  border-radius: 4px;
  border: 1px solid #dee2e6;
}
.pgx-ssh-key-label { margin: 0.5rem 0 0.25rem; font-size: 0.85rem; font-weight: 600; color: #495057; }
.pgx-ssh-key-label:first-child { margin-top: 0; }
.pgx-ssh-key-block {
  margin: 0;
  padding: 0.5rem;
  background: #fff;
  border: 1px solid #dee2e6;
  border-radius: 4px;
  font-size: 0.8rem;
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-all;
}

.pgx-episodes-summary {
  margin-bottom: 1rem;
  font-size: 0.9rem;
  color: #333;
}

.pgx-episodes-count { margin: 0 0 0.5rem; font-weight: 600; }

.pgx-episodes-list {
  margin: 0;
  padding-left: 1.2rem;
  list-style: none;
}
.pgx-episodes-list li { padding: 0.2rem 0; }

.episode-date { color: #666; font-variant-numeric: tabular-nums; margin-right: 0.4rem; }

.pgx-progress-panel {
  margin-top: 1.5rem;
  padding: 1rem;
  background: #f8f9fa;
  border-radius: 8px;
  border: 1px solid #dee2e6;
}

.progress-header { margin-bottom: 0.75rem; }

.progress-bar-container {
  margin: 16px 0;
  padding: 12px;
  background-color: #f8f9fa;
  border-radius: 8px;
  border: 1px solid #dee2e6;
}

.progress-bar-track {
  width: 100%;
  height: 24px;
  background-color: #e9ecef;
  border-radius: 12px;
  overflow: hidden;
  position: relative;
}

.progress-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #0066cc 0%, #0052a3 100%);
  transition: width 0.3s ease-out;
  border-radius: 12px;
  box-shadow: 0 2px 4px rgba(0, 102, 204, 0.3);
}

.progress-bar-label {
  margin-top: 8px;
  text-align: center;
  font-size: 14px;
  font-weight: 500;
  color: #495057;
}

.pgx-logs-list {
  margin: 0.5rem 0 0;
  padding-left: 1.2rem;
  font-size: 0.85rem;
  color: #495057;
  max-height: 200px;
  overflow-y: auto;
}

.pgx-retry-banner {
  margin-bottom: 0.75rem;
  padding: 0.6rem 0.9rem;
  background: #fff3cd;
  color: #856404;
  border-radius: 4px;
  font-size: 0.9rem;
}

.badge-warning { background: #fff3cd; color: #856404; }

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}
.section-header h2 { margin: 0; }

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
.pgx-log-row { cursor: pointer; }
.pgx-log-row:hover { background: #f8f9fa; }
.detail-row td { background: #fafafa; }
.log-detail ul { margin: 0; padding-left: 1.2rem; }
.error-message { color: #721c24; margin-bottom: 0.5rem; }
.retry-attempts { margin-top: 0.5rem; }

.loading { color: #666; font-style: italic; padding: 1rem 0; }
</style>
