<template>
  <div class="about-page">
    <Navigation pageTitle="À propos" />

    <div class="about-content">
      <!-- Version courante -->
      <section class="version-section" v-if="versionInfo">
        <h2>Version courante</h2>
        <div class="version-card">
          <div class="version-detail">
            <span class="version-label">Commit :</span>
            <a
              v-if="versionInfo.commit_url"
              :href="versionInfo.commit_url"
              target="_blank"
              rel="noopener noreferrer"
              class="commit-link"
            >
              {{ versionInfo.commit_short }}
            </a>
            <span v-else class="commit-hash">{{ versionInfo.commit_short }}</span>
          </div>
          <div class="version-detail">
            <span class="version-label">Date :</span>
            <span>{{ formatDate(versionInfo.commit_date) }}</span>
          </div>
          <div class="version-detail" v-if="versionInfo.build_date">
            <span class="version-label">Build :</span>
            <span>{{ formatDate(versionInfo.build_date) }}</span>
          </div>
          <div class="version-detail">
            <span class="version-label">Environnement :</span>
            <span class="env-badge" :class="'env-' + versionInfo.environment">
              {{ versionInfo.environment }}
            </span>
          </div>
        </div>
      </section>

      <!-- Changelog -->
      <section class="changelog-section">
        <h2>Historique des modifications</h2>
        <p class="changelog-description">
          Commits référençant des issues ou pull requests.
        </p>

        <div v-if="changelog.length === 0 && !loading" class="empty-state">
          Aucun historique disponible.
        </div>

        <div v-if="loading" class="loading-state">Chargement...</div>

        <table v-if="changelog.length > 0" class="changelog-table">
          <thead>
            <tr>
              <th class="col-hash">Commit</th>
              <th class="col-date">Date</th>
              <th class="col-message">Description</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="entry in changelog" :key="entry.hash">
              <td class="col-hash">
                <a
                  :href="commitUrl(entry.hash)"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="commit-link"
                >
                  {{ entry.hash }}
                </a>
              </td>
              <td class="col-date">{{ formatDate(entry.date) }}</td>
              <td class="col-message" v-html="linkifyIssues(entry.message)"></td>
            </tr>
          </tbody>
        </table>
      </section>
    </div>
  </div>
</template>

<script>
import axios from 'axios';
import Navigation from '../components/Navigation.vue';

const GITHUB_REPO_URL = 'https://github.com/castorfou/back-office-lmelp';

export default {
  name: 'AboutPage',

  components: {
    Navigation,
  },

  data() {
    return {
      versionInfo: null,
      changelog: [],
      loading: true,
    };
  },

  async mounted() {
    await Promise.all([
      this.loadVersionInfo(),
      this.loadChangelog(),
    ]);
    this.loading = false;
  },

  methods: {
    async loadVersionInfo() {
      try {
        const response = await axios.get('/api/version');
        this.versionInfo = response.data;
      } catch (error) {
        console.error('Erreur lors du chargement de la version:', error);
      }
    },

    async loadChangelog() {
      try {
        const response = await axios.get('/api/changelog');
        this.changelog = response.data;
      } catch (error) {
        console.error('Erreur lors du chargement du changelog:', error);
      }
    },

    formatDate(dateStr) {
      if (!dateStr || dateStr === 'unknown') return '--';
      try {
        const date = new Date(dateStr);
        return date.toLocaleDateString('fr-FR', {
          day: '2-digit',
          month: '2-digit',
          year: '2-digit',
        });
      } catch {
        return dateStr;
      }
    },

    commitUrl(hash) {
      return `${GITHUB_REPO_URL}/commit/${hash}`;
    },

    linkifyIssues(message) {
      // Remplace #XXX par des liens vers les issues GitHub
      // Échappe le HTML d'abord pour éviter l'injection
      const escaped = message
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
      return escaped.replace(
        /#(\d+)/g,
        `<a href="${GITHUB_REPO_URL}/issues/$1" target="_blank" rel="noopener noreferrer">#$1</a>`
      );
    },
  },
};
</script>

<style scoped>
.about-page {
  min-height: 100vh;
}

.about-content {
  max-width: 900px;
  margin: 0 auto;
  padding: 2rem;
}

.version-section,
.changelog-section {
  margin-bottom: 2rem;
}

.version-section h2,
.changelog-section h2 {
  font-size: 1.3rem;
  color: #333;
  margin-bottom: 1rem;
  border-bottom: 2px solid #667eea;
  padding-bottom: 0.5rem;
}

.version-card {
  background: white;
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.version-detail {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.version-label {
  font-weight: 600;
  color: #555;
  min-width: 120px;
}

.commit-link {
  font-family: monospace;
  color: #667eea;
  text-decoration: none;
}

.commit-link:hover {
  text-decoration: underline;
}

.commit-hash {
  font-family: monospace;
}

.env-badge {
  padding: 0.15rem 0.5rem;
  border-radius: 12px;
  font-size: 0.8rem;
  font-weight: 600;
}

.env-docker {
  background: #e3f2fd;
  color: #1565c0;
}

.env-development {
  background: #e8f5e9;
  color: #2e7d32;
}

.env-unknown {
  background: #f5f5f5;
  color: #757575;
}

.changelog-description {
  color: #666;
  font-size: 0.9rem;
  margin-bottom: 1rem;
}

.changelog-table {
  width: 100%;
  border-collapse: collapse;
  background: white;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.changelog-table th {
  background: #f8f9fa;
  padding: 0.75rem;
  text-align: left;
  font-size: 0.85rem;
  color: #555;
  border-bottom: 2px solid #dee2e6;
}

.changelog-table td {
  padding: 0.6rem 0.75rem;
  border-bottom: 1px solid #f0f0f0;
  font-size: 0.85rem;
  vertical-align: top;
}

.changelog-table tr:hover {
  background: #f8f9fa;
}

.col-hash {
  width: 80px;
  white-space: nowrap;
}

.col-date {
  width: 90px;
  white-space: nowrap;
  color: #666;
}

.col-message {
  word-break: break-word;
}

.empty-state,
.loading-state {
  text-align: center;
  padding: 2rem;
  color: #999;
}

@media (max-width: 768px) {
  .about-content {
    padding: 1rem;
  }

  .changelog-table {
    font-size: 0.8rem;
  }

  .col-hash {
    width: 70px;
  }

  .col-date {
    width: 80px;
  }

  .version-detail {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.2rem;
  }

  .version-label {
    min-width: auto;
  }
}
</style>
