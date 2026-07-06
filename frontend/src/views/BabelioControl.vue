<template>
  <div class="babelio-control">
    <Navigation pageTitle="Contrôle Babelio" />

    <main>
      <!-- État du service -->
      <section class="card status-section">
        <h2>
          <span class="status-badge" :class="statusClass">{{ statusLabel }}</span>
          État du service Babelio
        </h2>

        <div v-if="loading.status" class="loading">Chargement...</div>

        <div v-else-if="status" class="status-details">
          <div class="stat-row">
            <span class="stat-label">Cookie serveur :</span>
            <span class="stat-value">
              <span v-if="status.cookie_active" class="badge badge-ok">✓ Actif</span>
              <span v-else class="badge badge-warning">⚠ Non configuré</span>
            </span>
          </div>
          <div class="stat-row">
            <span class="stat-label">Circuit breaker :</span>
            <span class="stat-value">
              <span v-if="status.circuit_open" class="badge badge-expired">🚫 Ouvert — requêtes bloquées</span>
              <span v-else class="badge badge-ok">✓ Fermé</span>
            </span>
          </div>
          <div class="stat-row">
            <span class="stat-label">Intervalle minimum entre requêtes :</span>
            <span class="stat-value">{{ status.min_interval_sec }}s (BABELIO_FAIR_SEC)</span>
          </div>
          <div class="stat-row">
            <span class="stat-label">Durée de rétention du cache :</span>
            <span class="stat-value">
              <span v-if="status.cache_ttl_hours != null">{{ (status.cache_ttl_hours / 24).toFixed(1) }}j (BABELIO_CACHE_DAY)</span>
              <span v-else class="text-muted">—</span>
            </span>
          </div>
          <div class="stat-row">
            <span class="stat-label">Entrées en cache :</span>
            <span class="stat-value">{{ status.cache_entries }}</span>
          </div>
          <div class="stat-row">
            <span class="stat-label">Requêtes récentes enregistrées :</span>
            <span class="stat-value">{{ status.recent_requests_count }}</span>
          </div>
        </div>

        <button @click="loadStatus" class="btn btn-secondary refresh-btn" :disabled="loading.status">
          🔄 Rafraîchir
        </button>
      </section>

      <!-- Gestion des cookies -->
      <section class="card cookie-section">
        <h2>🔑 Cookie Babelio</h2>
        <p class="section-help">
          Le cookie <code>jstsToken</code> (TTL ~5 min) est requis pour éviter les blocages 403.
          Il est stocké <strong>côté serveur</strong> et utilisé automatiquement par toutes les requêtes Babelio.
        </p>

        <div class="cookie-status-row">
          <span v-if="status && status.cookie_active" class="badge badge-ok">✓ Actif côté serveur</span>
          <span v-else-if="babelioCookieStored && babelioCookieLikelyExpired" class="badge badge-expired">⏰ Probablement expiré</span>
          <span v-else class="badge badge-warning">⚠ Non configuré</span>
        </div>

        <div class="cookie-instructions">
          <details>
            <summary>Comment obtenir le cookie ?</summary>
            <ol>
              <li>Ouvre <a href="https://www.babelio.com" target="_blank" rel="noopener">babelio.com</a> et connecte-toi</li>
              <li>Ouvre les DevTools (F12) → onglet <strong>Réseau</strong></li>
              <li>Recharge la page, clique sur une requête babelio.com</li>
              <li>Dans <strong>En-têtes de requête</strong>, copie la valeur du champ <strong>Cookie</strong></li>
              <li>Colle-la ci-dessous et clique Enregistrer</li>
            </ol>
          </details>
        </div>

        <textarea
          v-model="babelioCookieInput"
          class="cookie-input"
          placeholder="jstsToken=...; p=FR; disclaimer=1; ..."
          rows="2"
        ></textarea>
        <div class="cookie-actions">
          <button @click="saveBabelioCookie" class="btn btn-primary" :disabled="!babelioCookieInput.trim()">
            Enregistrer
          </button>
          <button v-if="babelioCookieStored" @click="clearBabelioCookie" class="btn btn-danger">
            Effacer
          </button>
          <span v-if="cookieSaved" class="save-confirmation">✓ Cookie enregistré</span>
        </div>
      </section>

      <!-- Cache -->
      <section class="card cache-section">
        <div class="section-header">
          <h2>💾 Cache Babelio</h2>
          <div class="cache-actions">
            <button @click="loadCacheEntries" class="btn btn-secondary" :disabled="loading.cache">
              🔄 Rafraîchir
            </button>
            <button
              v-if="cacheEntries.length > 0"
              @click="clearAllCache"
              class="btn btn-danger"
              :disabled="loading.clearCache"
            >
              🗑 Vider tout le cache
            </button>
          </div>
        </div>

        <p class="section-help">
          Les requêtes vers Babelio (recherches AJAX et pages scraping) sont mises en cache
          pour éviter les requêtes redondantes. Durée de validité configurable via
          <code>BABELIO_CACHE_DAY</code>.
        </p>

        <div v-if="loading.cache" class="loading">Chargement...</div>
        <div v-else-if="cacheEntries.length === 0" class="empty-state">Cache vide</div>

        <div v-else class="cache-table-wrapper">
          <table class="cache-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Type</th>
                <th>Terme / URL</th>
                <th>Taille</th>
                <th>Statut</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="entry in cacheEntries"
                :key="entry.id"
                :class="{ 'expired-row': entry.expired }"
              >
                <td class="td-date">{{ formatDate(entry.timestamp) }}</td>
                <td class="td-type">
                  <span class="type-badge" :class="entry.search_type === 'search' ? 'type-search' : 'type-page'">
                    {{ entry.search_type || '?' }}
                  </span>
                </td>
                <td class="td-key" :title="entry.key">{{ truncate(entry.key, 60) }}</td>
                <td class="td-size">{{ formatSize(entry.size_bytes) }}</td>
                <td class="td-expired">
                  <span v-if="entry.expired" class="badge badge-expired">Expiré</span>
                  <span v-else class="badge badge-ok">Valide</span>
                </td>
                <td class="td-action">
                  <button
                    @click="deleteEntry(entry.id)"
                    class="btn-icon-delete"
                    title="Invalider cette entrée"
                    :disabled="deleting[entry.id]"
                  >
                    🗑
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <!-- Requêtes récentes -->
      <section class="card requests-section">
        <div class="section-header">
          <h2>📋 Requêtes récentes</h2>
          <button @click="loadRecentRequests" class="btn btn-secondary" :disabled="loading.requests">
            🔄 Rafraîchir
          </button>
        </div>

        <div v-if="loading.requests" class="loading">Chargement...</div>
        <div v-else-if="recentRequests.length === 0" class="empty-state">Aucune requête enregistrée depuis le démarrage du serveur</div>

        <div v-else class="requests-table-wrapper">
          <table class="requests-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Type</th>
                <th>Terme / URL</th>
                <th>Statut</th>
                <th>Cache</th>
                <th>Durée</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="(req, idx) in recentRequests"
                :key="idx"
                :class="reqRowClass(req)"
              >
                <td class="td-date">{{ formatDate(req.timestamp) }}</td>
                <td>
                  <span class="type-badge" :class="req.type === 'search' ? 'type-search' : 'type-page'">
                    {{ req.type }}
                  </span>
                </td>
                <td class="td-key" :title="req.term_or_url">{{ truncate(req.term_or_url, 60) }}</td>
                <td>
                  <span class="status-code" :class="'code-' + req.status_code">{{ req.status_code }}</span>
                </td>
                <td>
                  <span v-if="req.cache_hit" class="badge badge-cache">cache</span>
                  <span v-else class="badge badge-network">réseau</span>
                </td>
                <td>{{ req.duration_ms ? req.duration_ms + ' ms' : '—' }}</td>
              </tr>
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

const COOKIE_TTL_MS = 5 * 60 * 1000; // ~5 minutes

export default {
  name: 'BabelioControl',
  components: { Navigation },

  data() {
    return {
      status: null,
      cacheEntries: [],
      recentRequests: [],
      babelioCookieInput: localStorage.getItem('babelio_cookies') || '',
      babelioCookieStored: !!localStorage.getItem('babelio_cookies'),
      babelioCookieSavedAt: parseInt(localStorage.getItem('babelio_cookies_saved_at') || '0'),
      cookieSaved: false,
      loading: { status: false, cache: false, requests: false, clearCache: false },
      deleting: {},
      error: null,
      pollInterval: null,
    };
  },

  computed: {
    statusClass() {
      if (!this.status) return 'status-unknown';
      const map = {
        ok: 'status-ok',
        blocked_403: 'status-blocked',
        captcha: 'status-captcha',
        degraded: 'status-degraded',
        unknown: 'status-unknown',
      };
      return map[this.status.overall] || 'status-unknown';
    },

    statusLabel() {
      if (!this.status) return '❓ Inconnu';
      const map = {
        ok: '✅ OK',
        blocked_403: '🚫 Bloqué (403)',
        captcha: '⚠️ Captcha',
        degraded: '🟡 Dégradé',
        unknown: '❓ Inconnu',
      };
      return map[this.status.overall] || '❓ Inconnu';
    },

    babelioCookieLikelyExpired() {
      if (!this.babelioCookieStored || !this.babelioCookieSavedAt) return false;
      return Date.now() - this.babelioCookieSavedAt > COOKIE_TTL_MS;
    },
  },

  mounted() {
    this.syncCookieToServer();
    this.loadAll();
    this.pollInterval = setInterval(() => this.loadStatus(), 30000);
  },

  beforeUnmount() {
    if (this.pollInterval) {
      clearInterval(this.pollInterval);
      this.pollInterval = null;
    }
  },

  methods: {
    syncCookieToServer() {
      const stored = localStorage.getItem('babelio_cookies');
      if (stored) {
        axios.post('/api/babelio/cookie', { cookie: stored }).catch(() => {});
      }
    },

    async loadAll() {
      await Promise.all([
        this.loadStatus(),
        this.loadCacheEntries(),
        this.loadRecentRequests(),
      ]);
    },

    async loadStatus() {
      this.loading.status = true;
      try {
        const res = await axios.get('/api/babelio/status');
        this.status = res.data;
      } catch (e) {
        console.error('Erreur chargement statut Babelio', e);
      } finally {
        this.loading.status = false;
      }
    },

    async loadCacheEntries() {
      this.loading.cache = true;
      try {
        const res = await axios.get('/api/babelio/cache/entries');
        this.cacheEntries = res.data;
      } catch (e) {
        console.error('Erreur chargement cache Babelio', e);
      } finally {
        this.loading.cache = false;
      }
    },

    async loadRecentRequests() {
      this.loading.requests = true;
      try {
        const res = await axios.get('/api/babelio/requests/recent');
        this.recentRequests = res.data;
      } catch (e) {
        console.error('Erreur chargement requêtes récentes', e);
      } finally {
        this.loading.requests = false;
      }
    },

    async deleteEntry(entryId) {
      this.deleting = { ...this.deleting, [entryId]: true };
      try {
        await axios.delete(`/api/babelio/cache/${entryId}`);
        this.cacheEntries = this.cacheEntries.filter(e => e.id !== entryId);
      } catch (e) {
        console.error('Erreur suppression entrée cache', e);
      } finally {
        const d = { ...this.deleting };
        delete d[entryId];
        this.deleting = d;
      }
    },

    async clearAllCache() {
      if (!confirm('Vider tout le cache Babelio ? Cette action est irréversible.')) return;
      this.loading.clearCache = true;
      try {
        await axios.delete('/api/babelio/cache');
        this.cacheEntries = [];
        await this.loadStatus();
      } catch (e) {
        console.error('Erreur vidage cache', e);
      } finally {
        this.loading.clearCache = false;
      }
    },

    async saveBabelioCookie() {
      const val = this.babelioCookieInput.trim();
      if (!val) return;
      // Stocker côté serveur (central) ET localement (fallback legacy)
      await axios.post('/api/babelio/cookie', { cookie: val });
      localStorage.setItem('babelio_cookies', val);
      localStorage.setItem('babelio_cookies_saved_at', String(Date.now()));
      this.babelioCookieStored = true;
      this.babelioCookieSavedAt = Date.now();
      this.cookieSaved = true;
      await this.loadStatus();
      setTimeout(() => { this.cookieSaved = false; }, 3000);
    },

    async clearBabelioCookie() {
      await axios.delete('/api/babelio/cookie');
      localStorage.removeItem('babelio_cookies');
      localStorage.removeItem('babelio_cookies_saved_at');
      this.babelioCookieInput = '';
      this.babelioCookieStored = false;
      this.babelioCookieSavedAt = 0;
      await this.loadStatus();
    },

    formatDate(ts) {
      if (!ts) return '—';
      return new Date(ts * 1000).toLocaleString('fr-FR', {
        day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit'
      });
    },

    formatSize(bytes) {
      if (!bytes) return '—';
      if (bytes < 1024) return bytes + ' B';
      if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
      return (bytes / 1024 / 1024).toFixed(1) + ' MB';
    },

    truncate(str, max) {
      if (!str) return '';
      return str.length > max ? str.slice(0, max) + '…' : str;
    },

    reqRowClass(req) {
      if (req.status_code === 403) return 'row-error';
      if (req.status_code !== 200) return 'row-warning';
      if (req.cache_hit) return 'row-cache';
      return '';
    },
  },
};
</script>

<style scoped>
.babelio-control main {
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
  display: flex;
  align-items: center;
  gap: 0.5rem;
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

/* Status badge */
.status-badge {
  display: inline-block;
  padding: 0.2rem 0.6rem;
  border-radius: 12px;
  font-size: 0.9rem;
  font-weight: bold;
}
.status-ok { background: #d4edda; color: #155724; }
.status-blocked { background: #f8d7da; color: #721c24; }
.status-captcha { background: #fff3cd; color: #856404; }
.status-degraded { background: #fff3cd; color: #856404; }
.status-unknown { background: #e2e3e5; color: #383d41; }

/* Stat rows */
.stat-row {
  display: flex;
  gap: 1rem;
  padding: 0.4rem 0;
  border-bottom: 1px solid #f0f0f0;
}
.stat-label { color: #666; flex: 0 0 280px; }
.stat-value { font-weight: 600; }

.refresh-btn { margin-top: 1rem; }

/* Cookie */
.cookie-status-row { margin-bottom: 0.75rem; }
.cookie-instructions { margin-bottom: 1rem; font-size: 0.9rem; }
.cookie-instructions ol { margin: 0.5rem 0 0 1.5rem; }
.cookie-instructions li { margin-bottom: 0.25rem; }
.cookie-input {
  width: 100%;
  box-sizing: border-box;
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-family: monospace;
  font-size: 0.85rem;
  resize: vertical;
  margin-bottom: 0.75rem;
}
.cookie-actions { display: flex; gap: 0.5rem; align-items: center; }
.save-confirmation { color: #28a745; font-size: 0.9rem; }

/* Badges */
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
.badge-cache { background: #cce5ff; color: #004085; }
.badge-network { background: #e2e3e5; color: #383d41; }

/* Type badges */
.type-badge {
  display: inline-block;
  padding: 0.1rem 0.4rem;
  border-radius: 8px;
  font-size: 0.75rem;
  font-weight: 600;
}
.type-search { background: #e3f2fd; color: #0d47a1; }
.type-page { background: #f3e5f5; color: #4a148c; }

/* Tables */
.cache-table-wrapper,
.requests-table-wrapper { overflow-x: auto; }

.cache-table,
.requests-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
}
.cache-table th,
.requests-table th {
  text-align: left;
  padding: 0.5rem 0.75rem;
  background: #f8f9fa;
  border-bottom: 2px solid #dee2e6;
  font-weight: 600;
}
.cache-table td,
.requests-table td {
  padding: 0.4rem 0.75rem;
  border-bottom: 1px solid #f0f0f0;
  vertical-align: middle;
}
.expired-row { background: #fff8f8; }
.row-error { background: #fff0f0; }
.row-warning { background: #fffdf0; }
.row-cache { background: #f0f8ff; }

.td-date { white-space: nowrap; color: #666; font-size: 0.8rem; }
.td-key { max-width: 300px; word-break: break-all; color: #333; }
.td-type { white-space: nowrap; }
.td-size { white-space: nowrap; color: #666; }
.td-action { text-align: center; }

.status-code {
  display: inline-block;
  padding: 0.1rem 0.4rem;
  border-radius: 4px;
  font-weight: bold;
  font-size: 0.85rem;
}
.code-200 { background: #d4edda; color: #155724; }
.code-403 { background: #f8d7da; color: #721c24; }
.code-404 { background: #fff3cd; color: #856404; }

/* Buttons */
.btn {
  padding: 0.4rem 0.9rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
  transition: opacity 0.2s;
}
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-primary { background: #007bff; color: white; }
.btn-primary:hover:not(:disabled) { background: #0056b3; }
.btn-secondary { background: #6c757d; color: white; }
.btn-secondary:hover:not(:disabled) { background: #545b62; }
.btn-danger { background: #dc3545; color: white; }
.btn-danger:hover:not(:disabled) { background: #a71d2a; }
.btn-icon-delete {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 1rem;
  padding: 0.2rem 0.4rem;
  border-radius: 4px;
  transition: background 0.15s;
}
.btn-icon-delete:hover:not(:disabled) { background: #fee2e2; }
.btn-icon-delete:disabled { opacity: 0.3; cursor: not-allowed; }

.loading { color: #666; font-style: italic; padding: 1rem 0; }
.empty-state { color: #999; font-style: italic; padding: 1rem 0; }
</style>
