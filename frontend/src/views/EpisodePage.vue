<template>
  <div class="episode-page">
    <!-- Navigation -->
    <Navigation pageTitle="Gestion des Épisodes" />

    <main>
      <!-- Sélecteur d'épisode -->
      <EpisodeSelector
        ref="episodeSelector"
        @episode-selected="onEpisodeSelected"
      />

      <!-- Éditeur d'épisode -->
      <EpisodeEditor
        v-if="selectedEpisode"
        :episode="selectedEpisode"
        :key="selectedEpisode.id"
        @title-updated="onTitleUpdated"
      />

      <!-- Message d'aide si aucun épisode sélectionné -->
      <div v-if="!selectedEpisode" class="help-message card">
        <h3>👆 Sélectionnez un épisode pour commencer</h3>
        <p>
          Choisissez un épisode dans la liste déroulante ci-dessus pour voir son titre et sa description
          et pouvoir les corriger si nécessaire.
        </p>
        <div class="features">
          <h4>Fonctionnalités disponibles :</h4>
          <ul>
            <li>✅ Visualisation des titres et descriptions (corrigés s'ils existent)</li>
            <li>✏️ Correction des titres et descriptions</li>
            <li>🖥️ Affichage possible des versions originales pour comparaison</li>
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
import Navigation from '../components/Navigation.vue';

export default {
  name: 'EpisodePage',

  components: {
    EpisodeSelector,
    EpisodeEditor,
    Navigation,
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

    /**
     * Gère la mise à jour d'un titre d'épisode
     * Recharge la liste des épisodes pour afficher le nouveau titre
     * @param {Object} data - Données de l'événement (episodeId, newTitle)
     */
    async onTitleUpdated(data) {
      console.log('Titre mis à jour:', data);

      // Recharger la liste des épisodes dans le sélecteur
      if (this.$refs.episodeSelector) {
        await this.$refs.episodeSelector.refreshEpisodesList();
      }
    },
  },
};
</script>

<style scoped>
.episode-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
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
  .help-message {
    padding: 2rem 1rem;
  }
}
</style>
