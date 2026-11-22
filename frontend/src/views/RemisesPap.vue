<template>
  <div class="remises-pap">
    <Navigation pageTitle="Remises pap" />

    <main>
      <section class="card">
        <h2>📦 Remises pap à intégrer</h2>
        <p class="section-help">
          Émissions anciennes livrées par lmelp-pap (audio copié dans le dossier audio
          de lmelp). « Intégrer » en fait un épisode, vérifie l'empreinte du fichier,
          puis lance sa transcription, comme pour un épisode du flux RSS.
        </p>

        <div v-if="lastResult" class="integration-result" data-testid="integration-result">
          <p class="success-title">✅ Remise intégrée : {{ lastResult.titre }} ({{ formatDate(lastResult.date) }})</p>
          <p class="transcription-status">
            {{ transcriptionStatusLabel(lastResult.transcription_status) }}
          </p>
          <div class="next-steps">
            <router-link to="/transcription-pgx">Suivre la transcription</router-link>
            <router-link to="/generation-avis-critiques">Génération Avis Critiques</router-link>
          </div>
        </div>

        <div v-if="loading" class="loading" data-testid="remises-loading">
          Chargement des remises…
        </div>

        <div v-else-if="loadError" class="error-message" data-testid="remises-load-error">
          {{ loadError }}
        </div>

        <p v-else-if="remises.length === 0" class="empty" data-testid="remises-empty">
          Aucune remise à intégrer.
        </p>

        <ul v-else class="remises-list">
          <li
            v-for="remise in remises"
            :key="remise.remise_id"
            class="remise-row"
            data-testid="remise-row"
          >
            <div class="remise-info">
              <div class="remise-title">{{ remise.titre }}</div>
              <div class="remise-meta">
                <span>{{ formatDate(remise.date) }}</span>
                <span v-if="remise.duree != null" data-testid="remise-duree">
                  · {{ formatDuration(remise.duree) }}
                </span>
                <template v-if="remise.episode_page_url">
                  ·
                  <a
                    class="page-link"
                    :href="remise.episode_page_url"
                    target="_blank"
                    rel="noopener noreferrer"
                  >page radiofrance.fr ↗</a>
                </template>
              </div>
              <p class="remise-description" :title="remise.description">
                {{ excerpt(remise.description) }}
              </p>
              <div v-if="errors[remise.remise_id]" class="error-message row-error" data-testid="remise-error">
                {{ errors[remise.remise_id] }}
              </div>
            </div>
            <button
              type="button"
              class="btn btn-primary"
              data-testid="integrer-button"
              :disabled="!!integrating[remise.remise_id]"
              @click="integrer(remise)"
            >
              {{ integrating[remise.remise_id] ? 'Intégration…' : 'Intégrer' }}
            </button>
          </li>
        </ul>
      </section>
    </main>
  </div>
</template>

<script>
import Navigation from '../components/Navigation.vue';
import axios from 'axios';

const EXCERPT_LENGTH = 200;

export default {
  name: 'RemisesPap',
  components: { Navigation },
  data() {
    return {
      remises: [],
      loading: true,
      loadError: null,
      // Par remise_id : intégration en cours, message de refus
      integrating: {},
      errors: {},
      lastResult: null,
    };
  },
  async mounted() {
    await this.loadRemises();
  },
  methods: {
    async loadRemises() {
      this.loading = true;
      this.loadError = null;
      try {
        const res = await axios.get('/api/pap/remises');
        this.remises = res.data;
      } catch (e) {
        this.loadError = `Erreur lors du chargement des remises : ${e.response?.data?.detail || e.message}`;
      } finally {
        this.loading = false;
      }
    },
    async integrer(remise) {
      const id = remise.remise_id;
      if (this.integrating[id]) return;
      this.integrating = { ...this.integrating, [id]: true };
      const { [id]: _previous, ...otherErrors } = this.errors;
      this.errors = otherErrors;
      try {
        const res = await axios.post('/api/pap/remises/integrer', { remise_id: id });
        this.remises = this.remises.filter((r) => r.remise_id !== id);
        this.lastResult = res.data;
      } catch (e) {
        this.errors = {
          ...this.errors,
          [id]: e.response?.data?.detail || `Erreur : ${e.message}`,
        };
      } finally {
        const { [id]: _done, ...stillIntegrating } = this.integrating;
        this.integrating = stillIntegrating;
      }
    },
    transcriptionStatusLabel(status) {
      if (status === 'started') return '🖥️ Transcription lancée sur PGX (nouvel essai toutes les heures si PGX est éteint).';
      if (status === 'already_running') return '🖥️ Transcription déjà en cours : l\'épisode sera traité au prochain cycle.';
      if (status === 'nothing_to_do') return '🖥️ Aucune transcription à lancer.';
      return '⚠️ Transcription non lancée : la lancer depuis Transcriptions PGX.';
    },
    formatDate(isoDate) {
      const [year, month, day] = (isoDate || '').split('-');
      return year && month && day ? `${day}/${month}/${year}` : '—';
    },
    formatDuration(seconds) {
      const minutes = Math.floor(seconds / 60);
      const secs = String(seconds % 60).padStart(2, '0');
      return `${minutes} min ${secs} s`;
    },
    excerpt(text) {
      const value = (text || '').trim();
      return value.length > EXCERPT_LENGTH ? `${value.slice(0, EXCERPT_LENGTH)}…` : value;
    },
  },
};
</script>

<style scoped>
.remises-pap main {
  padding: 1.5rem;
  max-width: 1200px;
  margin: 0 auto;
}

.card {
  background: white;
  border-radius: 8px;
  padding: 1.5rem;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.1);
}

h2 {
  margin: 0 0 1rem;
  font-size: 1.2rem;
}

.section-help {
  color: #666;
  font-size: 0.9rem;
  margin-bottom: 1rem;
}

.loading,
.empty {
  color: #666;
}

.error-message {
  margin: 1rem 0;
  padding: 0.75rem 1rem;
  background: #f8d7da;
  color: #721c24;
  border-radius: 4px;
}

.remises-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.remise-row {
  display: flex;
  gap: 1rem;
  align-items: flex-start;
  justify-content: space-between;
  flex-wrap: wrap;
  padding: 0.9rem 0;
  border-top: 1px solid #eee;
}

.remise-info {
  flex: 1 1 300px;
  min-width: 0;
}

.remise-title {
  font-weight: 600;
}

.remise-meta {
  color: #555;
  font-size: 0.9rem;
  margin-top: 0.2rem;
}

.btn {
  padding: 0.4rem 0.9rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
  flex: 0 0 auto;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary {
  background: #007bff;
  color: white;
}

.row-error {
  margin: 0.5rem 0 0;
  font-size: 0.9rem;
}

.integration-result {
  margin-bottom: 1rem;
  padding: 0.75rem 1rem;
  background: #d4edda;
  color: #155724;
  border-radius: 4px;
}

.success-title {
  font-weight: 600;
  margin: 0 0 0.4rem;
}

.transcription-status {
  margin: 0 0 0.5rem;
}

.next-steps {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
}

.remise-description {
  color: #666;
  font-size: 0.85rem;
  margin: 0.4rem 0 0;
  overflow-wrap: anywhere;
}
</style>
