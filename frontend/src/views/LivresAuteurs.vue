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
                <th class="actions-header" data-testid="actions-header">
                  Actions
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
                    :book-key="getBookKey(book)"
                    @validation-status-change="handleValidationStatusChange"
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
                <td class="actions-cell">
                  <!-- Action buttons based on validation status -->
                  <button
                    v-if="getValidationStatus(book) === 'verified'"
                    @click="autoProcessVerified(book)"
                    class="btn btn-success btn-sm"
                    data-testid="auto-process-verified-btn"
                    title="Traiter automatiquement ce livre vérifié"
                  >
                    ✅ Traiter automatiquement
                  </button>

                  <button
                    v-if="getValidationStatus(book) === 'corrected'"
                    @click="validateSuggestion(book)"
                    class="btn btn-warning btn-sm"
                    data-testid="validate-suggestion-btn"
                    title="Valider cette suggestion"
                  >
                    🔍 Valider suggestion
                  </button>

                  <button
                    v-if="getValidationStatus(book) === 'not_found'"
                    @click="addManualBook(book)"
                    class="btn btn-danger btn-sm"
                    data-testid="manual-add-btn"
                    title="Ajouter manuellement ce livre"
                  >
                    ➕ Ajouter manuellement
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

    <!-- ========== MODAUX POUR TÂCHE 3 ========== -->

    <!-- Modal de validation des suggestions -->
    <div
      v-if="showValidationModal"
      class="modal-overlay"
      data-testid="validation-modal"
      @click="closeValidationModal"
    >
      <div class="modal-content" @click.stop>
        <h3>Valider la suggestion</h3>

        <div v-if="currentBookToValidate" class="book-validation-info">
          <div class="original-info">
            <h4>Données originales :</h4>
            <p><strong>Auteur :</strong> {{ currentBookToValidate.auteur }}</p>
            <p><strong>Titre :</strong> {{ currentBookToValidate.titre }}</p>
          </div>

          <div class="suggested-info">
            <h4>Suggestions Babelio :</h4>
            <p><strong>Auteur :</strong> {{ getSuggestionForCurrentBook()?.author || 'N/A' }}</p>
            <p><strong>Titre :</strong> {{ getSuggestionForCurrentBook()?.title || 'N/A' }}</p>
          </div>
        </div>

        <div class="modal-actions">
          <button
            @click="confirmValidation"
            class="btn btn-success"
            data-testid="confirm-validation-btn"
          >
            ✅ Confirmer la validation
          </button>
          <button
            @click="closeValidationModal"
            class="btn btn-secondary"
            data-testid="cancel-modal-btn"
          >
            ❌ Annuler
          </button>
        </div>
      </div>
    </div>

    <!-- Modal d'ajout manuel -->
    <div
      v-if="showManualAddModal"
      class="modal-overlay"
      data-testid="manual-add-modal"
      @click="closeManualAddModal"
    >
      <div class="modal-content" @click.stop>
        <h3>Ajouter manuellement un livre</h3>

        <div class="manual-add-form">
          <div class="form-group">
            <label for="author-input">Auteur :</label>
            <input
              id="author-input"
              v-model="manualBookForm.author"
              type="text"
              class="form-control"
              data-testid="author-input"
              placeholder="Nom de l'auteur"
            />
          </div>

          <div class="form-group">
            <label for="title-input">Titre :</label>
            <input
              id="title-input"
              v-model="manualBookForm.title"
              type="text"
              class="form-control"
              data-testid="title-input"
              placeholder="Titre du livre"
            />
          </div>

          <div class="form-group">
            <label for="publisher-input">Éditeur :</label>
            <input
              id="publisher-input"
              v-model="manualBookForm.publisher"
              type="text"
              class="form-control"
              data-testid="publisher-input"
              placeholder="Nom de l'éditeur"
            />
          </div>
        </div>

        <div class="modal-actions">
          <button
            @click="submitManualAdd"
            class="btn btn-primary"
            data-testid="submit-manual-add-btn"
            :disabled="!manualBookForm.author || !manualBookForm.title"
          >
            ➕ Ajouter le livre
          </button>
          <button
            @click="closeManualAddModal"
            class="btn btn-secondary"
            data-testid="cancel-modal-btn"
          >
            ❌ Annuler
          </button>
        </div>
      </div>
    </div>

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

      // ========== DONNÉES POUR TÂCHE 4: COMMUNICATION BIBLIOVALIADATIONCELL ==========
      // Map des statuts de validation par livre (clé: episode_oid-auteur-titre)
      validationStatuses: new Map(),
      validationSuggestions: new Map(),
      // Protection contre le traitement automatique en boucle
      alreadyProcessedBooks: new Set(),

      // ========== DONNÉES POUR TÂCHE 3: MODAUX ==========

      // Modal de validation pour livres suggested
      showValidationModal: false,
      currentBookToValidate: null,

      // Modal d'ajout manuel pour livres not_found
      showManualAddModal: false,
      currentBookToAdd: null,
      manualBookForm: {
        author: '',
        title: '',
        publisher: ''
      }

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
  },

  methods: {
    // ========== MÉTHODES POUR TÂCHE 4: COMMUNICATION BIBLIOVALIADATIONCELL ==========

    /**
     * Génère une clé unique pour identifier un livre
     */
    getBookKey(book) {
      return `${book.episode_oid}-${book.auteur}-${book.titre}`;
    },

    /**
     * Récupère le statut de validation pour un livre
     */
    getValidationStatus(book) {
      return this.validationStatuses.get(this.getBookKey(book)) || null;
    },

    /**
     * Handler appelé par BiblioValidationCell quand le statut change
     */
    handleValidationStatusChange(eventData) {
      const { bookKey, status, suggestion, validationResult } = eventData;

      // Stocker le statut de validation
      this.validationStatuses.set(bookKey, status);

      // Stocker les suggestions si disponibles
      if (suggestion) {
        this.validationSuggestions.set(bookKey, suggestion);
      }

      // Log pour debug
      console.log(`Validation status changed for ${bookKey}: ${status}`, {
        suggestion,
        validationResult
      });

      // Traitement automatique pour les livres verified
      if (status === 'verified') {
        this.triggerAutoProcessIfPossible(bookKey);
      }
    },

    /**
     * Déclenche le traitement automatique si possible pour un livre verified
     */
    async triggerAutoProcessIfPossible(bookKey) {
      // Vérifier si le livre a déjà été traité pour éviter la boucle infinie
      if (this.alreadyProcessedBooks.has(bookKey)) {
        return;
      }

      // Marquer ce livre comme étant en cours de traitement
      this.alreadyProcessedBooks.add(bookKey);

      // Trouver le livre correspondant à la clé
      const book = this.books.find(b => this.getBookKey(b) === bookKey);
      if (book) {
        try {
          // Attendre un peu pour laisser l'UI se mettre à jour
          await this.$nextTick();
          // Déclencher le traitement automatique
          await this.autoProcessVerified(book);
        } catch (error) {
          console.error('Erreur lors du traitement automatique:', error);
          // En cas d'erreur, retirer le livre du Set pour permettre une nouvelle tentative
          this.alreadyProcessedBooks.delete(bookKey);
        }
      }
    },

    /**
     * Traite automatiquement un livre vérifié
     */
    async autoProcessVerified(book) {
      try {
        console.log('Processing verified book:', book);

        // L'endpoint auto-process ne prend aucun paramètre (traite tous les livres verified)
        const result = await livresAuteursService.autoProcessVerifiedBooks();

        console.log('Auto-process result:', result);

        if (result.success) {
          // Actualiser les données après traitement
          await this.loadBooksForEpisode();
        }
      } catch (error) {
        console.error('Erreur lors du traitement automatique:', error);
      }
    },

    // ========== MÉTHODES EXISTANTES ==========

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

        // Auto-processing automatique des livres verified en arrière-plan (non-bloquant)
        Promise.resolve().then(async () => {
          try {
            await livresAuteursService.autoProcessVerifiedBooks();
            console.log('Auto-processing completed in background');
          } catch (error) {
            console.warn('Auto-processing failed in background:', error.message);
          }
        });
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

    // ========== NOUVELLES MÉTHODES POUR TÂCHE 2: BOUTONS PAR LIGNE ==========

    /**
     * Ouvre le modal de validation pour une suggestion (validation_status: 'suggested')
     */
    validateSuggestion(book) {
      console.log('Validating suggestion for book:', book);
      this.currentBookToValidate = book;
      this.showValidationModal = true;
    },

    /**
     * Ouvre le modal d'ajout manuel pour un livre non trouvé (validation_status: 'not_found')
     */
    addManualBook(book) {
      console.log('Adding manual book:', book);
      this.currentBookToAdd = book;
      // Pré-remplir le formulaire avec les données existantes
      this.manualBookForm = {
        author: book.auteur,
        title: book.titre,
        publisher: book.editeur || ''
      };
      this.showManualAddModal = true;
    },

    // ========== NOUVELLES MÉTHODES POUR LES MODAUX ==========

    /**
     * Confirme la validation d'une suggestion
     */
    async confirmValidation() {
      try {
        const book = this.currentBookToValidate;

        // Récupérer les données de suggestion stockées
        const bookKey = this.getBookKey(book);
        const suggestion = this.validationSuggestions.get(bookKey);

        const validationData = {
          id: book.episode_oid,
          auteur: book.auteur,
          titre: book.titre,
          editeur: book.editeur,
          user_validated_author: suggestion?.author || book.auteur,
          user_validated_title: suggestion?.title || book.titre
        };

        const result = await livresAuteursService.validateSuggestion(validationData);
        console.log('Validation result:', result);

        // Fermer le modal et recharger les données
        this.closeValidationModal();
        await this.loadBooksForEpisode();
      } catch (error) {
        console.error('Erreur lors de la validation:', error);
      }
    },

    /**
     * Soumet l'ajout manuel d'un livre
     */
    async submitManualAdd() {
      try {
        const book = this.currentBookToAdd;
        const bookData = {
          id: book.episode_oid,
          user_entered_author: this.manualBookForm.author,
          user_entered_title: this.manualBookForm.title,
          user_entered_publisher: this.manualBookForm.publisher || 'Éditeur inconnu'
        };

        const result = await livresAuteursService.addManualBook(bookData);
        console.log('Manual addition result:', result);

        // Fermer le modal et recharger les données
        this.closeManualAddModal();
        await this.loadBooksForEpisode();
      } catch (error) {
        console.error('Erreur lors de l\'ajout manuel:', error);
      }
    },

    /**
     * Récupère les suggestions pour le livre actuellement en cours de validation
     */
    getSuggestionForCurrentBook() {
      if (!this.currentBookToValidate) return null;
      const bookKey = this.getBookKey(this.currentBookToValidate);
      return this.validationSuggestions.get(bookKey);
    },

    /**
     * Ferme le modal de validation
     */
    closeValidationModal() {
      this.showValidationModal = false;
      this.currentBookToValidate = null;
    },

    /**
     * Ferme le modal d'ajout manuel
     */
    closeManualAddModal() {
      this.showManualAddModal = false;
      this.currentBookToAdd = null;
      this.manualBookForm = {
        author: '',
        title: '',
        publisher: ''
      };
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

/* ========== STYLES POUR LES MODAUX (TÂCHE 3) ========== */

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  border-radius: 12px;
  padding: 2rem;
  max-width: 500px;
  width: 90%;
  max-height: 80vh;
  overflow-y: auto;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
}

.modal-content h3 {
  margin-bottom: 1.5rem;
  color: #333;
  text-align: center;
}

.book-validation-info {
  margin-bottom: 2rem;
}

.original-info, .suggested-info {
  background: #f8f9fa;
  padding: 1rem;
  border-radius: 8px;
  margin-bottom: 1rem;
}

.original-info h4 {
  color: #dc3545;
  margin-bottom: 0.5rem;
}

.suggested-info h4 {
  color: #28a745;
  margin-bottom: 0.5rem;
}

.manual-add-form {
  margin-bottom: 2rem;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.25rem;
  font-weight: 500;
  color: #333;
}

.form-control {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 1rem;
  transition: border-color 0.3s ease;
}

.form-control:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.2);
}

.modal-actions {
  display: flex;
  gap: 1rem;
  justify-content: center;
}

.modal-actions .btn {
  min-width: 120px;
}

.btn-sm {
  padding: 0.25rem 0.5rem;
  font-size: 0.8rem;
}

.btn-success {
  background: #28a745;
  color: white;
}

.btn-success:hover:not(:disabled) {
  background: #218838;
}

.btn-secondary {
  background: #6c757d;
  color: white;
}

.btn-secondary:hover:not(:disabled) {
  background: #5a6268;
}

.actions-cell {
  text-align: center;
  min-width: 150px;
}

.actions-header {
  text-align: center;
  min-width: 150px;
}

@media (max-width: 768px) {
  .modal-content {
    padding: 1rem;
    width: 95%;
  }

  .modal-actions {
    flex-direction: column;
  }

  .modal-actions .btn {
    width: 100%;
  }
}
</style>
