<template>
  <div class="ajout-emission">
    <Navigation pageTitle="Ajouter une émission" />

    <main>
      <section class="card">
        <h2>➕ Ajouter une émission depuis radiofrance.fr</h2>
        <p class="section-help">
          Pour une émission absente du flux RSS (trop ancienne). Collez l'URL de sa
          page sur radiofrance.fr : titre, date, description et audio complet y sont
          lus, l'audio est téléchargé, l'émission est ajoutée, puis sa transcription
          est lancée, comme pour un épisode du flux RSS.
        </p>

        <form class="add-form" @submit.prevent="addEpisode">
          <label for="page-url">URL de la page radiofrance.fr</label>
          <div class="input-row">
            <input
              id="page-url"
              v-model.trim="pageUrl"
              data-testid="page-url-input"
              type="url"
              placeholder="https://www.radiofrance.fr/franceinter/podcasts/le-masque-et-la-plume/…"
              :disabled="loading"
            />
            <button
              type="submit"
              class="btn btn-primary"
              data-testid="add-button"
              :disabled="!pageUrl || loading"
            >
              {{ loading ? 'Ajout en cours…' : 'Ajouter l\'émission' }}
            </button>
          </div>
          <p v-if="loading" class="loading">
            Téléchargement de l'audio (jusqu'à une minute)…
          </p>
        </form>

        <div v-if="error" class="error-message" data-testid="add-error">
          {{ error }}
        </div>

        <div v-if="result" class="add-result" data-testid="add-result">
          <p class="success-title">✅ Émission ajoutée</p>
          <dl>
            <dt>Titre</dt>
            <dd>{{ result.titre }}</dd>
            <dt>Date</dt>
            <dd>{{ formatDate(result.date) }}</dd>
            <dt>Durée</dt>
            <dd>{{ formatDuration(result.duree) }}</dd>
          </dl>
          <p class="transcription-status" data-testid="transcription-status">
            {{ transcriptionStatusLabel(result.transcription_status) }}
          </p>
          <p class="next-steps-help">
            Une fois la transcription terminée (notification ntfy), la suite est la même
            que pour un épisode du flux RSS :
          </p>
          <div class="next-steps">
            <router-link to="/transcription-pgx">Suivre la transcription</router-link>
            <router-link to="/generation-avis-critiques">Génération Avis Critiques</router-link>
          </div>
        </div>
      </section>
    </main>
  </div>
</template>

<script>
import Navigation from '../components/Navigation.vue';
import axios from 'axios';

export default {
  name: 'AjoutEmission',
  components: { Navigation },
  data() {
    return {
      pageUrl: '',
      loading: false,
      result: null,
      error: null,
    };
  },
  methods: {
    async addEpisode() {
      if (!this.pageUrl || this.loading) return;
      this.loading = true;
      this.result = null;
      this.error = null;
      try {
        const res = await axios.post('/api/episodes/from-radiofrance-page', { url: this.pageUrl });
        this.result = res.data;
      } catch (e) {
        this.error = e.response?.data?.detail || `Erreur : ${e.message}`;
      } finally {
        this.loading = false;
      }
    },
    transcriptionStatusLabel(status) {
      if (status === 'started') return '🖥️ Transcription lancée sur PGX (nouvel essai toutes les heures si PGX est éteint).';
      if (status === 'already_running') return '🖥️ Transcription déjà en cours : l\'émission sera traitée au prochain cycle.';
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
  },
};
</script>

<style scoped>
.ajout-emission main {
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

.add-form label {
  display: block;
  font-weight: 600;
  margin-bottom: 0.4rem;
}

.input-row {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.input-row input {
  flex: 1 1 300px;
  min-width: 0;
  padding: 0.4rem 0.6rem;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 0.9rem;
}

.btn {
  padding: 0.4rem 0.9rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary {
  background: #007bff;
  color: white;
}

.loading {
  color: #666;
  font-size: 0.85rem;
  margin-top: 0.5rem;
}

.error-message {
  margin-top: 1rem;
  padding: 0.75rem 1rem;
  background: #f8d7da;
  color: #721c24;
  border-radius: 4px;
}

.add-result {
  margin-top: 1rem;
  padding: 0.75rem 1rem;
  background: #d4edda;
  color: #155724;
  border-radius: 4px;
}

.success-title {
  font-weight: 600;
  margin: 0 0 0.5rem;
}

.add-result dl {
  display: grid;
  grid-template-columns: max-content 1fr;
  gap: 0.25rem 1rem;
  margin: 0 0 0.75rem;
}

.add-result dt {
  font-weight: 600;
}

.add-result dd {
  margin: 0;
}

.transcription-status {
  margin: 0 0 0.5rem;
}

.next-steps-help {
  margin: 0 0 0.4rem;
  font-size: 0.9rem;
}

.next-steps {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
}
</style>
