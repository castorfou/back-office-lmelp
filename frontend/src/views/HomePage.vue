<template>
  <div class="home-page">
    <header class="page-header">
      <h1>Back-office LMELP</h1>
      <p class="subtitle">
        Gestion et correction des épisodes du Masque et la Plume
      </p>
    </header>

    <main>
      <!-- Sélecteur d'épisode -->
      <EpisodeSelector @episode-selected="onEpisodeSelected" />

      <!-- Éditeur d'épisode -->
      <EpisodeEditor
        v-if="selectedEpisode"
        :episode="selectedEpisode"
        :key="selectedEpisode.id"
      />

      <!-- Message d'aide si aucun épisode sélectionné -->
      <div v-if="!selectedEpisode" class="help-message card">
        <h3>👆 Sélectionnez un épisode pour commencer</h3>
        <p>
          Choisissez un épisode dans la liste déroulante ci-dessus pour voir sa description
          et pouvoir la corriger si nécessaire.
        </p>
        <div class="features">
          <h4>Fonctionnalités disponibles :</h4>
          <ul>
            <li>✅ Visualisation de la description originale</li>
            <li>✏️ Édition de la description corrigée</li>
            <li>💾 Sauvegarde automatique (2 secondes après modification)</li>
            <li>🔄 Gestion robuste des erreurs avec retry automatique</li>
          </ul>
        </div>
      </div>
    </main>

    <footer class="page-footer">
      <p>
        Version 0.1.0 - Back-office pour le projet
        <a href="https://github.com/castorfou/lmelp" target="_blank">LMELP</a>
      </p>
    </footer>
  </div>
</template>

<script>
import EpisodeSelector from '../components/EpisodeSelector.vue';
import EpisodeEditor from '../components/EpisodeEditor.vue';

export default {
  name: 'HomePage',

  components: {
    EpisodeSelector,
    EpisodeEditor,
  },

  data() {
    return {
      selectedEpisode: null,
    };
  },

  methods: {
    /**
     * Gère la sélection d'un épisode
     * @param {Object|null} episode - Épisode sélectionné ou null
     */
    onEpisodeSelected(episode) {
      this.selectedEpisode = episode;
    },
  },
};
</script>

<style scoped>
.home-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.page-header {
  text-align: center;
  margin-bottom: 3rem;
  padding: 2rem 0;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-radius: 12px;
  margin: -2rem -2rem 3rem -2rem;
  padding: 3rem 2rem;
}

.page-header h1 {
  font-size: 2.5rem;
  margin-bottom: 0.5rem;
  font-weight: 700;
}

.subtitle {
  font-size: 1.1rem;
  opacity: 0.9;
  font-weight: 300;
}

main {
  flex: 1;
}

.help-message {
  text-align: center;
  padding: 3rem;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  border: none;
}

.help-message h3 {
  color: #333;
  margin-bottom: 1rem;
  font-size: 1.3rem;
}

.help-message p {
  color: #666;
  margin-bottom: 2rem;
  font-size: 1.1rem;
  line-height: 1.6;
}

.features {
  text-align: left;
  max-width: 500px;
  margin: 0 auto;
}

.features h4 {
  color: #333;
  margin-bottom: 1rem;
  text-align: center;
}

.features ul {
  list-style: none;
  padding: 0;
}

.features li {
  padding: 0.5rem 0;
  font-size: 1rem;
  color: #555;
}

.page-footer {
  margin-top: 4rem;
  text-align: center;
  padding: 2rem 0;
  color: #666;
  font-size: 0.9rem;
  border-top: 1px solid #eee;
}

.page-footer a {
  color: #007bff;
  text-decoration: none;
}

.page-footer a:hover {
  text-decoration: underline;
}

@media (max-width: 768px) {
  .page-header {
    margin: -2rem -1rem 2rem -1rem;
    padding: 2rem 1rem;
  }

  .page-header h1 {
    font-size: 2rem;
  }

  .help-message {
    padding: 2rem 1rem;
  }
}
</style>
