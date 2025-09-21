<template>
  <div class="livres-auteurs">
    <!-- Navigation -->
    <Navigation pageTitle="Livres et Auteurs" />

    <main>
      <!-- Sélecteur d'épisode -->
      <section class="episode-selector-section">
        <div class="episode-selector card">
          <!-- État de chargement des épisodes -->
          <div v-if="episodesLoading" class="loading">
            Chargement des épisodes avec avis critiques...
          </div>

          <!-- Affichage d'erreur des épisodes -->
          <div v-if="episodesError" class="alert alert-error">
            {{ episodesError }}
            <button @click="loadEpisodesWithReviews" class="btn btn-primary" style="margin-left: 1rem;">
              Réessayer
            </button>
          </div>

          <!-- Sélecteur d'épisode -->
          <div v-if="!episodesLoading && !episodesError" class="form-group">
            <label for="episode-select" class="form-label">
              Choisir un épisode avec avis critiques ({{ episodesWithReviews.length }} disponibles)
            </label>
            <select
              id="episode-select"
              v-model="selectedEpisodeId"
              @change="onEpisodeChange"
              class="form-control"
            >
              <option value="">-- Sélectionner un épisode --</option>
              <option
                v-for="episode in episodesWithReviews"
                :key="episode.id"
                :value="episode.id"
              >
                {{ formatEpisodeOption(episode) }}
              </option>
            </select>
          </div>
        </div>
      </section>

      <!-- Section simplifiée : nombre de livres extraits seulement -->
      <section v-if="selectedEpisodeId && !loading && !error && books.length > 0" class="stats-section">
        <div class="simple-stats">
          <span class="books-count">{{ books.length }} livre(s) extrait(s)</span>
        </div>
      </section>

      <!-- Message d'aide si aucun épisode sélectionné -->
      <div v-if="!selectedEpisodeId && !episodesLoading && !episodesError" class="help-message card">
        <h3>👆 Sélectionnez un épisode pour commencer</h3>
        <p>
          Choisissez un épisode dans la liste déroulante ci-dessus pour voir les livres et auteurs
          extraits de ses avis critiques.
        </p>
        <div class="features">
          <h4>Fonctionnalités disponibles :</h4>
          <ul>
            <li>📚 Extraction des livres discutés au programme</li>
            <li>✍️ Identification des auteurs et éditeurs</li>
            <li>📋 Affichage en tableau simple et navigable</li>
            <li>🔄 Tri alphabétique par colonnes (cliquez sur les en-têtes)</li>
            <li>🔍 Recherche et filtrage des résultats</li>
          </ul>
        </div>
      </div>

      <!-- ========== DASHBOARD COLLECTIONS MANAGEMENT (ISSUE #66) ========== -->

      <!-- Dashboard statistiques collections - toujours affiché -->
      <section class="collections-dashboard">
        <div class="collections-stats card">
          <h3>📊 Gestion des Collections Auteurs/Livres</h3>

          <!-- État de chargement des statistiques -->
          <div v-if="statisticsLoading" class="loading">
            Chargement des statistiques...
          </div>

          <!-- Affichage des statistiques -->
          <div v-if="collectionsStatistics && !statisticsLoading" class="stats-grid">
            <div class="stat-item">
              <span class="stat-label">Épisodes non traités : </span>
              <span class="stat-value">{{ collectionsStatistics.episodes_non_traites }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">Couples en base : </span>
              <span class="stat-value">{{ collectionsStatistics.couples_en_base }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">Verified pas en base : </span>
              <span class="stat-value">{{ collectionsStatistics.couples_verified_pas_en_base }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">Suggested pas en base : </span>
              <span class="stat-value">{{ collectionsStatistics.couples_suggested_pas_en_base }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">Not found pas en base : </span>
              <span class="stat-value">{{ collectionsStatistics.couples_not_found_pas_en_base }}</span>
            </div>
          </div>

          <!-- Actions de gestion - toujours affichées -->
          <div class="collections-actions">
            <!-- Bouton traitement automatique -->
            <button
              @click="autoProcessVerified"
              :disabled="autoProcessLoading"
              data-testid="auto-process-button"
              class="btn btn-primary"
            >
              {{ autoProcessLoading ? 'Traitement en cours...' : 'Traitement automatique' }}
            </button>

            <!-- Bouton charger statistiques -->
            <button
              @click="loadCollectionsStatistics"
              :disabled="statisticsLoading"
              class="btn btn-secondary"
            >
              {{ statisticsLoading ? 'Chargement...' : 'Actualiser statistiques' }}
            </button>
          </div>

          <!-- Résultats du traitement automatique -->
          <div v-if="autoProcessResult" class="process-results">
            <h4>✅ Traitement automatique terminé :</h4>
            <ul>
              <li>{{ autoProcessResult.processed_count }} livres traités</li>
              <li>{{ autoProcessResult.created_authors }} auteurs créés</li>
              <li>{{ autoProcessResult.created_books }} livres créés</li>
              <li>{{ autoProcessResult.updated_references }} références mises à jour</li>
            </ul>
          </div>
        </div>

        <!-- Section validation manuelle (livres suggested) -->
        <div v-if="suggestedBooks.length > 0" class="manual-validation card">
          <h4>🔍 Validation manuelle (Livres suggested)</h4>
          <div v-for="book in suggestedBooks" :key="book.id" class="validation-item">
            <div class="book-info">
              <span class="original">{{ book.auteur }} - {{ book.titre }}</span>
              <span class="suggestion">Suggestion : {{ book.suggested_author }} - {{ book.suggested_title }}</span>
            </div>
            <button
              @click="validateSuggestion({ id: book.id, user_validated_author: book.suggested_author, user_validated_title: book.suggested_title })"
              data-testid="validate-suggestion-button"
              class="btn btn-success"
            >
              Valider suggestion
            </button>
          </div>
        </div>

        <!-- Section ajout manuel (livres not_found) -->
        <div v-if="notFoundBooks.length > 0" class="manual-add card">
          <h4>➕ Ajout manuel (Livres not found)</h4>
          <div v-for="book in notFoundBooks" :key="book.id" class="add-item">
            <div class="book-info">
              <span class="not-found">{{ book.auteur }} - {{ book.titre }}</span>
            </div>
            <button
              @click="addManualBook({ id: book.id, user_entered_author: book.auteur, user_entered_title: book.titre, user_entered_publisher: 'Éditeur inconnu' })"
              data-testid="add-manual-book-button"
              class="btn btn-warning"
            >
              Ajouter manuellement
            </button>
          </div>
        </div>

        <!-- Section gestion des collections créées -->
        <div v-if="allAuthors.length > 0 || allBooks.length > 0" class="collections-management card">
          <h4>📚 Collections créées</h4>

          <!-- Auteurs -->
          <div v-if="allAuthors.length > 0" class="authors-list">
            <h5>Auteurs ({{ allAuthors.length }})</h5>
            <div v-for="author in allAuthors" :key="author.id" class="author-item">
              {{ author.nom }} ({{ author.livres.length }} livres)
            </div>
          </div>

          <!-- Livres -->
          <div v-if="allBooks.length > 0" class="books-list">
            <h5>Livres ({{ allBooks.length }})</h5>
            <div v-for="book in allBooks" :key="book.id" class="book-item">
              {{ book.titre }} - {{ book.editeur }}
            </div>
          </div>
        </div>
      </section>

      <!-- Filtre de recherche -->
      <section v-if="selectedEpisodeId && !loading && !error && books.length > 0" class="filter-section">
        <div class="filter-controls">
          <input
            v-model="searchFilter"
            type="text"
            placeholder="Filtrer par auteur, titre ou éditeur..."
            class="search-input"
          />
          <span class="search-help">💡 Cliquez sur les en-têtes du tableau pour trier</span>
        </div>
      </section>

      <!-- État de chargement -->
      <div v-if="selectedEpisodeId && loading" class="loading-state">
        <div class="loader"></div>
        <p>Chargement des livres et auteurs...</p>
      </div>

      <!-- État d'erreur -->
      <div v-if="selectedEpisodeId && error" class="error-state">
        <div class="error-icon">❌</div>
        <h3>Erreur de chargement</h3>
        <p>{{ error }}</p>
        <button @click="loadBooksForEpisode" class="retry-button">Réessayer</button>
      </div>

      <!-- État vide -->
      <div v-if="selectedEpisodeId && !loading && !error && books.length === 0" class="empty-state">
        <div class="empty-icon">📚</div>
        <h3>Aucun livre trouvé</h3>
        <p>Aucun livre n'a pu être extrait des avis critiques de cet épisode.</p>
      </div>

      <!-- Tableau des livres -->
      <section v-if="selectedEpisodeId && !loading && !error && filteredBooks.length > 0" class="books-section">
        <div class="table-container">
          <table class="books-table">
            <thead>
              <tr>
                <th class="status-header" @click="setSortOrder('status')" data-testid="status-header" role="columnheader" aria-sort="none" aria-label="Programme ou Coup de coeur">
                  <!-- Petite colonne d'état: programme / coup de coeur -->
                  <span class="status-header-icon" title="Cliquer pour trier" aria-hidden="true">
                    <!-- Outlined circle with transparent interior -->
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Statut">
                      <circle cx="12" cy="12" r="8" stroke="currentColor" stroke-width="2" fill="none" />
                    </svg>
                  </span>
                </th>
                <th class="sortable-header" @click="setSortOrder('author')">
                  Auteur
                  <span class="sort-indicator" :class="getSortClass('author')">↕</span>
                </th>
                <th class="sortable-header" @click="setSortOrder('title')">
                  Titre
                  <span class="sort-indicator" :class="getSortClass('title')">↕</span>
                </th>
                <th class="sortable-header" @click="setSortOrder('publisher')">
                  Éditeur
                  <span class="sort-indicator" :class="getSortClass('publisher')">↕</span>
                </th>
                <th class="validation-header">
                  Validation Biblio
                </th>
                <th class="capture-header">
                  Capture YAML
                </th>
              </tr>
            </thead>
            <tbody>
                <tr v-for="book in filteredBooks" :key="`${book.episode_oid}-${book.auteur}-${book.titre}`" class="book-row" data-testid="book-item">
                <td class="status-cell" style="text-align:center" data-testid="status-cell-{{book.episode_oid}}">
                  <!-- Programme: blue/bold target icon -->
                  <span v-if="book.programme" class="status-icon programme" title="Au programme" role="img" aria-label="Programme">
                    <svg width="18" height="18" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none">
                      <circle cx="12" cy="12" r="8" fill="#0B5FFF" />
                      <circle cx="12" cy="12" r="4" fill="#FFFFFF" />
                    </svg>
                  </span>
                  <!-- Coup de coeur: red heart with high contrast -->
                  <span v-else-if="book.coup_de_coeur" class="status-icon coeur" title="Coup de coeur" role="img" aria-label="Coup de coeur">
                    <svg width="18" height="18" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none">
                      <path d="M12 21s-7.5-4.5-9.3-7.1C-0.4 9.8 3 5 7.4 7.1 9.1 8 10 9.6 12 11.3c2-1.7 2.9-3.3 4.6-4.2C21 5 24.4 9.8 21.3 13.9 19.5 16.5 12 21 12 21z" fill="#D93025" />
                    </svg>
                  </span>
                  <!-- Empty when no flag -->
                  <span v-else class="status-icon empty" aria-hidden="true"></span>
                </td>
                <td class="author-cell">{{ book.auteur }}</td>
                <td class="title-cell">{{ book.titre }}</td>
                <td class="publisher-cell">{{ book.editeur || '-' }}</td>
                <td class="validation-cell">
                  <BiblioValidationCell
                    :author="book.auteur"
                    :title="book.titre"
                    :publisher="book.editeur || ''"
                    :episode-id="selectedEpisodeId"
                  />
                </td>
                <td class="capture-cell">
                  <button
                    @click="captureFixtures(book)"
                    class="btn-capture-fixtures"
                    title="Capturer les appels API pour les fixtures"
                    :data-testid="`capture-button-${book.episode_oid}-${book.auteur}-${book.titre}`"
                  >
                    🔄 YAML
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <!-- Message de filtrage -->
      <div v-if="selectedEpisodeId && !loading && !error && books.length > 0 && filteredBooks.length === 0" class="no-results">
        <div class="no-results-icon">🔍</div>
        <h3>Aucun résultat</h3>
        <p>Aucun livre ne correspond aux critères de recherche "{{ searchFilter }}"</p>
      </div>
    </main>
  </div>
</template>

<script>
import { livresAuteursService } from '../services/api.js';
import Navigation from '../components/Navigation.vue';
import BiblioValidationCell from '../components/BiblioValidationCell.vue';
import { fixtureCaptureService } from '../services/FixtureCaptureService.js';
import BiblioValidationService from '../services/BiblioValidationService.js';

export default {
  name: 'LivresAuteurs',

  components: {
    Navigation,
    BiblioValidationCell,
  },

  data() {
    return {
      // Données pour les épisodes
      episodesWithReviews: [],
      episodesLoading: true,
      episodesError: null,
      selectedEpisodeId: '',

      // Données pour les livres
      books: [],
      loading: false,
      error: null,
      searchFilter: '',
      currentSortField: 'author',
      sortAscending: true,

      // ========== NOUVELLES DONNÉES POUR ISSUE #66 ==========

      // Statistiques des collections
      collectionsStatistics: null,
      statisticsLoading: false,
      statisticsError: null,

      // Traitement automatique
      autoProcessLoading: false,
      autoProcessResult: null,

      // Gestion des livres suggested
      suggestedBooks: [],
      suggestedBooksLoading: false,

      // Gestion des livres not_found
      notFoundBooks: [],
      notFoundBooksLoading: false,

      // Collections management
      allAuthors: [],
      allBooks: [],
      collectionsLoading: false,

      // Interface states
      showCollectionsManager: false,
      showManualValidation: false,
      showManualAdd: false
    };
  },

  computed: {

    filteredBooks() {
      let filtered = [...this.books];

      // Appliquer le filtre de recherche
      if (this.searchFilter.trim()) {
        const search = this.searchFilter.toLowerCase();
        filtered = filtered.filter(book =>
          book.auteur.toLowerCase().includes(search) ||
          book.titre.toLowerCase().includes(search) ||
          book.editeur.toLowerCase().includes(search)
        );
      }

      // Appliquer le tri par colonnes
      filtered.sort((a, b) => {
        let sortValue = 0;

        switch (this.currentSortField) {
          case 'status':
            // Prioritize programme (true) then coup_de_coeur then none
            const scoreA = (a.programme ? 2 : 0) + (a.coup_de_coeur ? 1 : 0);
            const scoreB = (b.programme ? 2 : 0) + (b.coup_de_coeur ? 1 : 0);
            sortValue = scoreA - scoreB;
            break;
          case 'author':
            sortValue = a.auteur.localeCompare(b.auteur, 'fr', { sensitivity: 'base' });
            break;
          case 'title':
            sortValue = a.titre.localeCompare(b.titre, 'fr', { sensitivity: 'base' });
            break;
          case 'publisher':
            const publisherA = a.editeur || '';
            const publisherB = b.editeur || '';
            sortValue = publisherA.localeCompare(publisherB, 'fr', { sensitivity: 'base' });
            break;
          default:
            sortValue = a.auteur.localeCompare(b.auteur, 'fr', { sensitivity: 'base' });
        }

        return this.sortAscending ? sortValue : -sortValue;
      });

      return filtered;
    }
  },

  async mounted() {
    await this.loadEpisodesWithReviews();
    await this.loadCollectionsStatistics();
  },

  methods: {
    /**
     * Charge la liste des épisodes avec avis critiques
     */
    async loadEpisodesWithReviews() {
      try {
        this.episodesLoading = true;
        this.episodesError = null;
        this.episodesWithReviews = await livresAuteursService.getEpisodesWithReviews();
      } catch (error) {
        this.episodesError = error.message;
        console.error('Erreur lors du chargement des épisodes:', error);
      } finally {
        this.episodesLoading = false;
      }
    },

    renderStatusIcon(book) {
      // Return a small icon for programme or coup_de_coeur
      if (book.programme) return '🎯';
      if (book.coup_de_coeur) return '💖';
      return '';
    },

    /**
     * Charge les livres pour un épisode sélectionné
     */
    async loadBooksForEpisode() {
      if (!this.selectedEpisodeId) {
        this.books = [];
        return;
      }

      try {
        this.loading = true;
        this.error = null;

        // Récupérer SEULEMENT les livres de cet épisode (efficace !)
        this.books = await livresAuteursService.getLivresAuteurs({ episode_oid: this.selectedEpisodeId });
      } catch (error) {
        this.error = error.message;
        console.error('Erreur lors du chargement des livres/auteurs:', error);
      } finally {
        this.loading = false;
      }
    },

    /**
     * Gère le changement d'épisode sélectionné
     */
    async onEpisodeChange() {
      // Réinitialiser les filtres
      this.searchFilter = '';
      this.sortOrder = 'rating_desc';

      // Charger les livres pour le nouvel épisode
      await this.loadBooksForEpisode();
    },

    /**
     * Formate l'affichage d'un épisode dans la liste
     */
    formatEpisodeOption(episode) {
      const date = new Date(episode.date).toLocaleDateString('fr-FR');
      const title = episode.titre_corrige || episode.titre;
      return `${date} - ${title}`;
    },

    setSortOrder(field) {
      if (this.currentSortField === field) {
        this.sortAscending = !this.sortAscending;
      } else {
        this.currentSortField = field;
        this.sortAscending = true;
      }
    },

    getSortClass(field) {
      if (this.currentSortField !== field) {
        return '';
      }
      return this.sortAscending ? 'sort-asc' : 'sort-desc';
    },

    /**
     * Capture les appels API pour génération de fixtures YAML
     */
    async captureFixtures(book) {
      console.log('🎯 Starting fixture capture for:', {
        author: book.auteur,
        title: book.titre,
        publisher: book.editeur,
        episodeId: this.selectedEpisodeId
      });

      // Démarrer la capture
      fixtureCaptureService.startCapture();

      try {
        // Rejouer la validation BiblioService avec capture activée
        await BiblioValidationService.validateBiblio(
          book.auteur,
          book.titre,
          book.editeur || '',
          this.selectedEpisodeId
        );

        console.log('✅ BiblioValidation completed');
      } catch (error) {
        console.error('❌ Error during BiblioValidation:', error);
      } finally {
        // Envoyer les appels capturés au backend
        await fixtureCaptureService.stopCaptureAndSend();
      }
    },

    // ========== NOUVELLES MÉTHODES POUR ISSUE #66 ==========

    /**
     * Charge les statistiques des collections
     */
    async loadCollectionsStatistics() {
      try {
        this.statisticsLoading = true;
        this.statisticsError = null;
        this.collectionsStatistics = await livresAuteursService.getCollectionsStatistics();
      } catch (error) {
        this.statisticsError = error.message;
        console.error('Erreur lors du chargement des statistiques:', error);
      } finally {
        this.statisticsLoading = false;
      }
    },

    /**
     * Lance le traitement automatique des livres verified
     */
    async autoProcessVerified() {
      try {
        this.autoProcessLoading = true;
        this.autoProcessResult = await livresAuteursService.autoProcessVerifiedBooks();
        // Recharger les statistiques après traitement
        await this.loadCollectionsStatistics();
      } catch (error) {
        console.error('Erreur lors du traitement automatique:', error);
      } finally {
        this.autoProcessLoading = false;
      }
    },

    /**
     * Charge les livres avec statut 'suggested'
     */
    async loadSuggestedBooks() {
      try {
        this.suggestedBooksLoading = true;
        this.suggestedBooks = await livresAuteursService.getBooksByValidationStatus('suggested');
      } catch (error) {
        console.error('Erreur lors du chargement des livres suggested:', error);
      } finally {
        this.suggestedBooksLoading = false;
      }
    },

    /**
     * Valide manuellement une suggestion
     */
    async validateSuggestion(bookData) {
      try {
        const result = await livresAuteursService.validateSuggestion(bookData);
        // Recharger les données après validation
        await this.loadSuggestedBooks();
        await this.loadCollectionsStatistics();
        return result;
      } catch (error) {
        console.error('Erreur lors de la validation:', error);
        throw error;
      }
    },

    /**
     * Charge les livres avec statut 'not_found'
     */
    async loadNotFoundBooks() {
      try {
        this.notFoundBooksLoading = true;
        this.notFoundBooks = await livresAuteursService.getBooksByValidationStatus('not_found');
      } catch (error) {
        console.error('Erreur lors du chargement des livres not_found:', error);
      } finally {
        this.notFoundBooksLoading = false;
      }
    },

    /**
     * Ajoute manuellement un livre not_found
     */
    async addManualBook(bookData) {
      try {
        const result = await livresAuteursService.addManualBook(bookData);
        // Recharger les données après ajout
        await this.loadNotFoundBooks();
        await this.loadCollectionsStatistics();
        return result;
      } catch (error) {
        console.error('Erreur lors de l\'ajout manuel:', error);
        throw error;
      }
    },

    /**
     * Charge tous les auteurs de la collection
     */
    async loadAllAuthors() {
      try {
        this.collectionsLoading = true;
        this.allAuthors = await livresAuteursService.getAllAuthors();
      } catch (error) {
        console.error('Erreur lors du chargement des auteurs:', error);
      } finally {
        this.collectionsLoading = false;
      }
    },

    /**
     * Charge tous les livres de la collection
     */
    async loadAllBooks() {
      try {
        this.collectionsLoading = true;
        this.allBooks = await livresAuteursService.getAllBooks();
      } catch (error) {
        console.error('Erreur lors du chargement des livres:', error);
      } finally {
        this.collectionsLoading = false;
      }
    }

  }
};
</script>

<style scoped>
.livres-auteurs {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

/* Styles supprimés car remplacés par le composant Navigation standardisé */

/* Contenu principal */
.content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2rem;
  max-width: 1200px;
  margin: 0 auto;
  width: 100%;
}

/* Status column styles */
.status-header {
  width: 40px;
  cursor: pointer; /* indicate clickable */
  text-align: center;
}
.status-header .status-header-icon svg {
  color: #6b7280; /* gray outline */
}
.status-cell .status-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.status-cell .status-icon svg {
  display: block;
}
.status-icon.programme svg {
  /* Blue filled outer, white inner - high contrast */
  filter: drop-shadow(0 0 0 rgba(0,0,0,0));
}
.status-icon.coeur svg {
  shape-rendering: geometricPrecision;
}
.status-header:hover,
.status-cell .status-icon:hover {
  transform: translateY(-1px);
}
.status-header[title] { position: relative; }
.status-header[title]:hover::after {
  content: attr(title);
  position: absolute;
  top: -28px;
  left: 50%;
  transform: translateX(-50%);
  background: #111827;
  color: #fff;
  padding: 4px 8px;
  font-size: 12px;
  border-radius: 4px;
  white-space: nowrap;
  z-index: 10;
}


/* Statistiques */
.simple-stats {
  margin-bottom: 1.5rem;
  text-align: center;
}

.books-count {
  font-size: 1.1rem;
  color: #666;
  font-weight: 500;
}

/* Filtres */
.filter-section {
  background: white;
  padding: 1.5rem;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.filter-controls {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
}

.search-input, .sort-select {
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 1rem;
}

.search-input {
  flex: 1;
  min-width: 250px;
}

.sort-select {
  min-width: 180px;
}

/* États */
.loading-state, .error-state, .empty-state, .no-results {
  text-align: center;
  padding: 3rem;
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.loader {
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 1rem;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.error-icon, .empty-icon, .no-results-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.retry-button {
  background: #667eea;
  color: white;
  border: none;
  padding: 0.75rem 1.5rem;
  border-radius: 8px;
  cursor: pointer;
  font-size: 1rem;
  margin-top: 1rem;
  transition: background-color 0.3s ease;
}

.retry-button:hover {
  background: #5a6fd8;
}

/* Tableau des livres */
.table-container {
  background: white;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.books-table {
  width: 100%;
  border-collapse: collapse;
}

.books-table thead {
  background: #f8f9fa;
}

.books-table th {
  padding: 1rem;
  text-align: left;
  font-weight: 600;
  color: #333;
  border-bottom: 2px solid #eee;
}

.sortable-header {
  cursor: pointer;
  user-select: none;
  position: relative;
  transition: background-color 0.2s ease;
}

.sortable-header:hover {
  background: #e9ecef;
}

.sort-indicator {
  opacity: 0.5;
  margin-left: 0.5rem;
  font-size: 0.8rem;
  transition: opacity 0.2s ease;
}

.sort-asc .sort-indicator {
  opacity: 1;
  color: #667eea;
}

.sort-asc .sort-indicator::before {
  content: '↑';
}

.sort-desc .sort-indicator {
  opacity: 1;
  color: #667eea;
}

.sort-desc .sort-indicator::before {
  content: '↓';
}

.books-table tbody tr {
  border-bottom: 1px solid #eee;
  transition: background-color 0.2s ease;
}

.books-table tbody tr:hover {
  background: #f8f9fa;
}

.books-table td {
  padding: 1rem;
  vertical-align: top;
}

.author-cell {
  font-weight: 500;
  color: #667eea;
}

.title-cell {
  font-weight: 600;
  color: #333;
}

.publisher-cell {
  color: #666;
}

.validation-header {
  padding: 1rem;
  text-align: left;
  font-weight: 600;
  color: #333;
  border-bottom: 2px solid #eee;
  min-width: 180px;
}

.validation-cell {
  padding: 1rem;
  vertical-align: top;
  min-width: 180px;
}

.capture-header {
  padding: 1rem;
  text-align: left;
  font-weight: 600;
  color: #333;
  border-bottom: 2px solid #eee;
  min-width: 120px;
}

.capture-cell {
  padding: 1rem;
  vertical-align: top;
  min-width: 120px;
  text-align: center;
}

.btn-capture-fixtures {
  background: #28a745;
  color: white;
  border: none;
  padding: 0.5rem 0.75rem;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.8rem;
  font-weight: 500;
  transition: background-color 0.2s ease, transform 0.1s ease;
  white-space: nowrap;
  min-width: 80px;
}

.btn-capture-fixtures:hover {
  background: #218838;
  transform: translateY(-1px);
}

.btn-capture-fixtures:active {
  transform: translateY(0);
}

/* Aide pour le tri */
.search-help {
  font-size: 0.85rem;
  color: #666;
  margin-left: 1rem;
  font-style: italic;
}

/* Section ratings et favorites supprimées - design simplifié */

/* Responsive */
@media (max-width: 768px) {
  .page-header {
    padding: 1.5rem 1rem;
    margin: -1rem -1rem 1.5rem -1rem;
  }

  .page-header h1 {
    font-size: 2rem;
  }

  .filter-controls {
    flex-direction: column;
    gap: 1rem;
  }

  .search-input {
    width: 100%;
  }

  .search-help {
    margin-left: 0;
    margin-top: 0.5rem;
    display: block;
  }

  .books-table th,
  .books-table td {
    padding: 0.75rem;
  }

  .table-container {
    margin: 0 -1rem;
    border-radius: 0;
  }

}

/* Styles pour le sélecteur d'épisodes (basés sur EpisodeSelector.vue) */
.episode-selector-section {
  margin-bottom: 2rem;
}

.episode-selector.card {
  background: white;
  border-radius: 12px;
  padding: 2rem;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  margin-bottom: 2rem;
}

.episode-selector h2 {
  margin-bottom: 1rem;
  color: #333;
}

.form-control {
  font-family: monospace;
  font-size: 0.9rem;
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 6px;
  transition: border-color 0.3s ease;
}

.form-control:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.loading {
  text-align: center;
  padding: 1rem;
  color: #666;
  font-style: italic;
}

.alert {
  padding: 1rem;
  border-radius: 6px;
  margin-bottom: 1rem;
}

.alert-error {
  background-color: #fee;
  color: #c33;
  border: 1px solid #fcc;
}

.btn {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.9rem;
  transition: background-color 0.3s ease;
}

.btn-primary {
  background-color: #667eea;
  color: white;
}

.btn-primary:hover {
  background-color: #5a67d8;
}

/* Message d'aide (basé sur EpisodePage.vue) */
.help-message {
  text-align: center;
  padding: 3rem;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  border: none;
  border-radius: 12px;
  margin-bottom: 2rem;
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

/* ========== STYLES POUR COLLECTIONS MANAGEMENT (ISSUE #66) ========== */

.collections-dashboard {
  margin-bottom: 2rem;
}

.collections-stats.card {
  background: white;
  border-radius: 12px;
  padding: 2rem;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  margin-bottom: 1.5rem;
}

.collections-stats h3 {
  margin-bottom: 1.5rem;
  color: #333;
  font-size: 1.4rem;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1rem;
  margin-bottom: 2rem;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  padding: 0.75rem;
  background: #f8f9fa;
  border-radius: 8px;
  border-left: 4px solid #667eea;
}

.stat-label {
  font-weight: 500;
  color: #666;
}

.stat-value {
  font-weight: bold;
  color: #333;
  font-size: 1.1rem;
}

.collections-actions {
  display: flex;
  gap: 1rem;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
}

.process-results {
  background: #d4edda;
  border: 1px solid #c3e6cb;
  border-radius: 8px;
  padding: 1rem;
  margin-top: 1rem;
}

.process-results h4 {
  margin-bottom: 0.5rem;
  color: #155724;
}

.process-results ul {
  margin: 0;
  padding-left: 1.5rem;
}

.process-results li {
  color: #155724;
  margin-bottom: 0.25rem;
}

.manual-validation.card,
.manual-add.card,
.collections-management.card {
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  margin-bottom: 1.5rem;
}

.validation-item,
.add-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  border: 1px solid #ddd;
  border-radius: 8px;
  margin-bottom: 1rem;
}

.book-info {
  flex: 1;
  margin-right: 1rem;
}

.original {
  display: block;
  font-weight: 500;
  color: #333;
  margin-bottom: 0.25rem;
}

.suggestion {
  display: block;
  color: #667eea;
  font-style: italic;
  font-size: 0.9rem;
}

.not-found {
  display: block;
  font-weight: 500;
  color: #dc3545;
}

.btn {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.9rem;
  font-weight: 500;
  transition: background-color 0.3s ease, transform 0.1s ease;
  white-space: nowrap;
}

.btn:hover {
  transform: translateY(-1px);
}

.btn:active {
  transform: translateY(0);
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.btn-primary {
  background: #667eea;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #5a67d8;
}

.btn-secondary {
  background: #6c757d;
  color: white;
}

.btn-secondary:hover:not(:disabled) {
  background: #5a6268;
}

.btn-success {
  background: #28a745;
  color: white;
}

.btn-success:hover:not(:disabled) {
  background: #218838;
}

.btn-warning {
  background: #ffc107;
  color: #212529;
}

.btn-warning:hover:not(:disabled) {
  background: #e0a800;
}

.authors-list,
.books-list {
  margin-bottom: 1.5rem;
}

.authors-list h5,
.books-list h5 {
  margin-bottom: 1rem;
  color: #333;
  font-weight: 600;
}

.author-item,
.book-item {
  padding: 0.5rem;
  background: #f8f9fa;
  border-radius: 6px;
  margin-bottom: 0.5rem;
  color: #555;
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }

  .collections-actions {
    flex-direction: column;
  }

  .validation-item,
  .add-item {
    flex-direction: column;
    align-items: stretch;
  }

  .book-info {
    margin-right: 0;
    margin-bottom: 1rem;
  }

  .btn {
    width: 100%;
  }
}
</style>
