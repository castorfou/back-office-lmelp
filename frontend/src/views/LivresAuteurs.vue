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
              Choisir un épisode avec avis critiques ({{ episodesWithReviews?.length || 0 }} disponibles)
            </label>
            <div class="episode-select-wrapper">
              <button
                class="nav-episode-btn prev-btn"
                @click.prevent="selectPreviousEpisode"
                :disabled="!hasPreviousEpisode"
                aria-label="Épisode précédent"
                data-testid="prev-episode-button"
              >
                ◀️ Précédent
              </button>
              <EpisodeDropdown
                v-model="selectedEpisodeId"
                :episodes="episodesWithReviews || []"
                @update:modelValue="onEpisodeChange"
              />
              <button
                class="nav-episode-btn next-btn"
                @click.prevent="selectNextEpisode"
                :disabled="!hasNextEpisode"
                aria-label="Épisode suivant"
                data-testid="next-episode-button"
              >
                Suivant ▶️
              </button>
              <button
                v-if="selectedEpisodeId"
                @click="refreshEpisodeCache"
                class="btn-icon-refresh"
                data-testid="refresh-cache-button"
                title="Relancer la validation Biblio"
                aria-label="Relancer la validation Biblio"
              >
                🔄
              </button>
            </div>
          </div>
        </div>

      <!-- Légende des statuts -->
      <section v-if="selectedEpisodeId && !loading && !error && books.length > 0" class="legend-section">
        <div class="legend-box">
          <h6>Statuts des livres :</h6>
          <ul class="legend-list">
            <li>
              <span class="badge bg-success">🟢</span>
              <strong>Mongo</strong>: Livre trouvé et stocké dans MongoDB
            </li>
            <li>
              <span class="badge bg-secondary">⚪</span>
              <strong>Gris</strong>: Épisode sans analyse (pas d'entrée dans livresauteurs_cache)
            </li>
            <li>
              <span class="badge bg-warning">🟠</span>
              <strong>Suggested</strong>: Livre suggéré par Babelio (à vérifier)
            </li>
            <li>
              <span class="badge bg-danger">🔴</span>
              <strong>Rouge</strong>: Analyse incomplète (certains livres pas au statut "mongo")
            </li>
          </ul>
        </div>
      </section>

        <!-- Détails de l'épisode (accordéon replié) -->
        <div v-if="selectedEpisode" class="episode-details-accordion">
          <button
            @click="showEpisodeDetails = !showEpisodeDetails"
            class="accordion-toggle"
            :aria-expanded="showEpisodeDetails"
          >
            <span class="toggle-icon">{{ showEpisodeDetails ? '▼' : '▶' }}</span>
            <span class="toggle-label">Détails de l'épisode (titre et description)</span>
          </button>
          <div v-if="showEpisodeDetails" class="accordion-content">
            <div class="episode-info-container">
              <!-- Logo RadioFrance cliquable à gauche -->
              <a
                v-if="selectedEpisodeFull && selectedEpisodeFull.episode_page_url"
                :href="selectedEpisodeFull.episode_page_url"
                target="_blank"
                rel="noopener noreferrer"
                class="episode-logo-link"
                title="Voir la page de l'épisode sur RadioFrance"
              >
                <img
                  src="@/assets/le-masque-et-la-plume-logo.jpg"
                  alt="Logo Le Masque et la Plume"
                  class="episode-logo"
                />
              </a>

              <!-- Informations de l'épisode à droite -->
              <div class="episode-info">
                <div class="info-section">
                  <strong>Titre :</strong>
                  <p class="episode-title">{{ episodeDisplayTitle }}</p>
                </div>
                <div class="info-section">
                  <strong>Description :</strong>
                  <p class="episode-description">{{ episodeDisplayDescription }}</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>




      <!-- Section simplifiée : nombre de livres extraits seulement -->
      <section v-if="selectedEpisodeId && !loading && !error && books.length > 0" class="stats-section">
        <div class="simple-stats">
          <span class="books-count">{{ books.length }} livre(s) extrait(s)</span><span v-if="programBooksValidationStats.total > 0" class="validation-stats"> — au programme : {{ programBooksValidationStats.traites }} traités, {{ programBooksValidationStats.suggested }} suggested, {{ programBooksValidationStats.not_found }} not found</span>
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
                <th :class="['validation-header', { 'validation-header-expanded': !showYamlColumn }]">
                  Validation Biblio
                  <button
                    v-if="!showYamlColumn"
                    @click="toggleYamlColumn"
                    class="toggle-yaml-btn-inline"
                    title="Afficher la colonne YAML"
                  >
                    👁️‍🗨️
                  </button>
                </th>
                <th v-if="showYamlColumn" class="capture-header">
                  <button
                    @click="toggleYamlColumn"
                    class="toggle-yaml-btn-only"
                    title="Masquer la colonne YAML"
                  >
                    👁️
                  </button>
                </th>
                <th class="actions-header" data-testid="actions-header">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
                <tr v-for="book in filteredBooks" :key="`${book.episode_oid}-${book.auteur}-${book.titre}`" :class="['book-row', { 'mongo-book': book.status === 'mongo' }]" data-testid="book-item">
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
                <td class="author-cell">
                  <!-- Issue #96: Lien cliquable vers page auteur si ID disponible -->
                  <router-link
                    v-if="book.author_id"
                    :to="`/auteur/${book.author_id}`"
                    class="clickable-link"
                    data-test="author-link"
                  >
                    {{ getDisplayedAuthor(book) }}
                  </router-link>
                  <span v-else>{{ getDisplayedAuthor(book) }}</span>
                </td>
                <td class="title-cell">
                  <!-- Issue #96: Lien cliquable vers page livre si ID disponible -->
                  <router-link
                    v-if="book.book_id"
                    :to="`/livre/${book.book_id}`"
                    class="clickable-link"
                    data-test="title-link"
                  >
                    {{ getDisplayedTitle(book) }}
                  </router-link>
                  <span v-else>{{ getDisplayedTitle(book) }}</span>
                </td>
                <td class="publisher-cell">
                  {{ getDisplayedPublisher(book) || '-' }}
                </td>
                <td :class="['validation-cell', { 'validation-cell-expanded': !showYamlColumn }]">
                  <BiblioValidationCell
                    v-if="book.status !== 'mongo'"
                    :author="book.auteur"
                    :title="book.titre"
                    :publisher="book.editeur || ''"
                    :episode-id="selectedEpisodeId"
                    :book-key="getBookKey(book)"
                    @validation-status-change="handleValidationStatusChange"
                  />
                  <span v-else class="mongo-status">✅ Traité</span>
                </td>
                <td v-if="showYamlColumn" class="capture-cell">
                  <button
                    v-if="book.status !== 'mongo'"
                    @click="captureFixtures(book)"
                    class="btn-capture-fixtures"
                    title="Capturer les appels API pour les fixtures"
                    :data-testid="`capture-button-${book.episode_oid}-${book.auteur}-${book.titre}`"
                  >
                    🔄 YAML
                  </button>
                  <span v-else class="mongo-status">-</span>
                </td>
                <td class="actions-cell">
                  <!-- Action buttons hidden for mongo status -->
                  <template v-if="book.status !== 'mongo'">
                    <button
                      v-if="getValidationStatus(book) === 'verified'"
                      @click="autoProcessVerified(book)"
                      class="btn btn-success btn-sm"
                      data-testid="auto-process-verified-btn"
                      title="Traiter automatiquement ce livre vérifié"
                    >
                      ✅ Traiter
                    </button>

                    <button
                      v-if="getValidationStatus(book) === 'corrected'"
                      @click="validateSuggestion(book)"
                      class="btn btn-warning btn-sm"
                      data-testid="validate-suggestion-btn"
                      title="Valider cette suggestion"
                    >
                      🔍 Valider
                    </button>

                    <button
                      v-if="getValidationStatus(book) === 'not_found'"
                      @click="addManualBook(book)"
                      class="btn btn-danger btn-sm"
                      data-testid="manual-add-btn"
                      title="Ajouter manuellement ce livre"
                    >
                      ➕ Ajouter
                    </button>
                  </template>
                  <span v-else class="mongo-status">-</span>
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

          <div class="editable-form">
            <h4>Validation finale (modifiable) :</h4>

            <!-- Issue #159: Champ URL Babelio pour auto-remplissage -->
            <div class="form-group babelio-url-group">
              <label for="validation-babelio-url-input">
                URL Babelio (optionnel) :
                <button
                  v-if="validationBabelioUrl && !validationExtractingFromUrl"
                  @click="extractFromBabelioUrl('validation')"
                  class="btn-extract-url"
                  type="button"
                  title="Extraire les informations depuis l'URL Babelio"
                >
                  🔄 Extraire
                </button>
                <span v-if="validationExtractingFromUrl" class="extracting-indicator">
                  ⏳ Extraction en cours...
                </span>
              </label>
              <input
                id="validation-babelio-url-input"
                v-model="validationBabelioUrl"
                type="text"
                class="form-control"
                data-testid="validation-babelio-url-input"
                placeholder="https://www.babelio.com/livres/..."
              />
              <div v-if="validationUrlError" class="url-error">{{ validationUrlError }}</div>
            </div>

            <div class="form-group">
              <label for="validation-author-input">Auteur :</label>
              <input
                id="validation-author-input"
                v-model="validationForm.author"
                type="text"
                class="form-control"
                data-testid="validation-author-input"
                placeholder="Nom de l'auteur"
              />
            </div>

            <div class="form-group">
              <label for="validation-title-input">Titre :</label>
              <input
                id="validation-title-input"
                v-model="validationForm.title"
                type="text"
                class="form-control"
                data-testid="validation-title-input"
                placeholder="Titre du livre"
              />
            </div>

            <div class="form-group">
              <label for="validation-publisher-input">Éditeur :</label>
              <input
                id="validation-publisher-input"
                v-model="validationForm.publisher"
                type="text"
                class="form-control"
                data-testid="validation-publisher-input"
                placeholder="Nom de l'éditeur"
              />
            </div>
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
          <!-- Issue #159: Champ URL Babelio pour auto-remplissage -->
          <div class="form-group babelio-url-group">
            <label for="manual-babelio-url-input">
              URL Babelio (optionnel) :
              <button
                v-if="manualBabelioUrl && !manualExtractingFromUrl"
                @click="extractFromBabelioUrl('manual')"
                class="btn-extract-url"
                type="button"
                title="Extraire les informations depuis l'URL Babelio"
              >
                🔄 Extraire
              </button>
              <span v-if="manualExtractingFromUrl" class="extracting-indicator">
                ⏳ Extraction en cours...
              </span>
            </label>
            <input
              id="manual-babelio-url-input"
              v-model="manualBabelioUrl"
              type="text"
              class="form-control"
              data-testid="manual-babelio-url-input"
              placeholder="https://www.babelio.com/livres/..."
              @keydown.stop
            />
            <div v-if="manualUrlError" class="url-error">{{ manualUrlError }}</div>
          </div>

          <div class="form-group">
            <label for="author-input">Auteur :</label>
            <input
              id="author-input"
              v-model="manualBookForm.author"
              type="text"
              class="form-control"
              data-testid="author-input"
              placeholder="Nom de l'auteur"
              @keydown.stop
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
              @keydown.stop
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
              @keydown.stop
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
import { livresAuteursService, episodeService } from '../services/api.js';
import Navigation from '../components/Navigation.vue';
import BiblioValidationCell from '../components/BiblioValidationCell.vue';
import EpisodeDropdown from '../components/EpisodeDropdown.vue';
import { fixtureCaptureService } from '../services/FixtureCaptureService.js';
import BiblioValidationService from '../services/BiblioValidationService.js';
import { buildBookDataForBackend } from '../utils/buildBookDataForBackend.js';
import { selectEpisodeByBadgePriority } from '../utils/episodeSelection.js';
import debounce from 'lodash.debounce';
import axios from 'axios';

export default {
  name: 'LivresAuteurs',

  components: {
    Navigation,
    BiblioValidationCell,
    EpisodeDropdown,
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
      validationForm: {
        author: '',
        title: '',
        publisher: ''
      },
      // Issue #159: URL Babelio pour auto-remplissage dans modal validation
      validationBabelioUrl: '',
      validationExtractingFromUrl: false,
      validationUrlError: null,

      // Modal d'ajout manuel pour livres not_found
      showManualAddModal: false,
      currentBookToAdd: null,
      manualBookForm: {
        author: '',
        title: '',
        publisher: ''
      },
      // Issue #159: URL Babelio pour auto-remplissage dans modal ajout manuel
      manualBabelioUrl: '',
      manualExtractingFromUrl: false,
      manualUrlError: null,

      // Contrôle d'affichage de la colonne YAML
      showYamlColumn: false,

  // Contrôle d'affichage des détails de l'épisode
  showEpisodeDetails: false,
  // Full episode details fetched on demand (may include description)
  selectedEpisodeFull: null,
  // Prevent re-entrant navigation while changing episode
  navLock: false,
  // Issue #85: Prevent double loadBooksForEpisode during refreshEpisodeCache
  isRefreshing: false,
  // Issue #160: Global lock to prevent race conditions during episode changes
  changeEpisodeLock: false,

    };
  },

  computed: {
    selectedEpisode() {
      if (!this.selectedEpisodeId) return null;
      return this.episodesWithReviews.find(ep => String(ep.id) === String(this.selectedEpisodeId));
    },


    // Display helpers for episode title/description to match backend fields
    episodeDisplayTitle() {
      const epFull = this.selectedEpisodeFull;
      const ep = epFull || this.selectedEpisode;
      if (!ep) return '';
      return ep.titre_corrige || ep.titre || ep.title || '';
    },

    episodeDisplayDescription() {
      const epFull = this.selectedEpisodeFull;
      const ep = epFull || this.selectedEpisode;
      if (!ep) return '';
      // prefer corrected description, then original description, then any summary field
      return ep.description || ep.description_origin || ep.resume || ep.excerpt || '';
    },

    // Navigation helpers
    currentEpisodeIndex() {
      if (!this.episodesWithReviews || !this.selectedEpisodeId) return -1;
      return this.episodesWithReviews.findIndex(ep => String(ep.id) === String(this.selectedEpisodeId));
    },

    // Note: episodes are sorted from most recent to oldest. "Previous" (left) should go to older
    // episodes (higher index). "Next" (right) goes to more recent (lower index).
    hasPreviousEpisode() {
      return this.currentEpisodeIndex >= 0 && this.currentEpisodeIndex < (this.episodesWithReviews.length - 1);
    },

    hasNextEpisode() {
      return this.currentEpisodeIndex > 0;
    },

    // Statistiques de validation des livres au programme
    programBooksValidationStats() {
      // "Au programme" = TOUS les livres (programme: true ET coup_de_coeur: true)
      const programBooks = this.books.filter(book => book.programme || book.coup_de_coeur);
      const stats = {
        traites: 0,
        suggested: 0,
        not_found: 0,
        total: programBooks.length
      };

      programBooks.forEach(book => {
        if (book.status === 'mongo') {
          // Livre traité (déjà en MongoDB)
          stats.traites++;
        } else if (book.suggested_author || book.suggested_title) {
          // Livre avec suggestion Babelio (pas encore traité)
          stats.suggested++;
        } else {
          // Livre sans suggestion (not found)
          stats.not_found++;
        }
      });

      return stats;
    },

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

  watch: {
    // Issue #159: Auto-déclenchement extraction URL Babelio (modal validation)
    validationBabelioUrl: debounce(function(newUrl) {
      if (newUrl && this.isValidBabelioUrl(newUrl)) {
        this.extractFromBabelioUrl('validation');
      }
    }, 500),

    // Issue #159: Auto-déclenchement extraction URL Babelio (modal ajout manuel)
    manualBabelioUrl: debounce(function(newUrl) {
      if (newUrl && this.isValidBabelioUrl(newUrl)) {
        this.extractFromBabelioUrl('manual');
      }
    }, 500),
  },

  async mounted() {
    await this.loadEpisodesWithReviews();

    // Issue #96: Support pour lien direct vers un épisode via ?episode=<id>
    const episodeIdFromUrl = this.$route?.query?.episode;
    if (episodeIdFromUrl && this.episodesWithReviews) {
      const episodeExists = this.episodesWithReviews.find(ep => ep.id === episodeIdFromUrl);
      if (episodeExists) {
        this.selectedEpisodeId = episodeIdFromUrl;
        await this.onEpisodeChange();
      }
    }

    // Issue #185: Auto-sélection par priorité de pastille (🔴 > ⚪ > 🟢)
    if (!this.selectedEpisodeId && this.episodesWithReviews?.length > 0) {
      const selected = selectEpisodeByBadgePriority(this.episodesWithReviews);
      if (selected) {
        this.selectedEpisodeId = selected.id;
        await this.onEpisodeChange();
      }
    }

    // Keyboard navigation for episode select (left / right)
    // prevent default browser navigation when using arrows and avoid races
    this._onKeydown = async (e) => {
      // Désactiver navigation si un modal est ouvert
      if (this.showValidationModal || this.showManualAddModal) return;

      if (!this.selectedEpisodeId) return;
      if (e.key === 'ArrowLeft') {
        // prevent the native select from changing the option and creating a race
        e.preventDefault();
        await this.selectPreviousEpisode();
      } else if (e.key === 'ArrowRight') {
        e.preventDefault();
        await this.selectNextEpisode();
      }
    };
    // Use capture phase so we receive the keydown before the native <select> handler
    window.addEventListener('keydown', this._onKeydown, true);
  },

  beforeUnmount() {
    if (this._onKeydown) window.removeEventListener('keydown', this._onKeydown, true);
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
     * Retourne l'auteur à afficher selon le statut du livre
     * Pour les livres mongo : utilise suggested_author si disponible
     */
    getDisplayedAuthor(book) {
      if (book.status === 'mongo') {
        return book.suggested_author || book.auteur;
      }
      return book.auteur;
    },

    /**
     * Retourne le titre à afficher selon le statut du livre
     * Pour les livres mongo : utilise suggested_title si disponible
     */
    getDisplayedTitle(book) {
      if (book.status === 'mongo') {
        return book.suggested_title || book.titre;
      }
      return book.titre;
    },

    /**
     * Retourne l'éditeur à afficher selon le statut du livre
     * Pour les livres mongo : utilise babelio_publisher si disponible (enrichissement Issue #85)
     */
    getDisplayedPublisher(book) {
      if (book.status === 'mongo') {
        return book.babelio_publisher || book.editeur;
      }
      return book.editeur;
    },

    /**
     * Récupère le statut de validation pour un livre
     */
    getValidationStatus(book) {
      return this.validationStatuses.get(this.getBookKey(book)) || null;
    },

    /**
     * Toggle l'affichage de la colonne YAML
     */
    toggleYamlColumn() {
      this.showYamlColumn = !this.showYamlColumn;
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
        // L'endpoint auto-process ne prend aucun paramètre (traite tous les livres verified)
        const result = await livresAuteursService.autoProcessVerifiedBooks();

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

        // Récupérer SEULEMENT les livres de cet épisode (cache ou extraction)
        this.books = await livresAuteursService.getLivresAuteurs({ episode_oid: this.selectedEpisodeId });

        // Si pas de statuts ou statuts temporaires → validation biblio + rechargement
        const needsValidation = this.books.some(book =>
          !book.status ||
          !['verified', 'suggested', 'mongo', 'not_found'].includes(book.status)
        );

        if (needsValidation) {
          // Auto-validation des livres avec BiblioValidationService et envoi au backend
          await this.autoValidateAndSendResults();

          // RECHARGER les livres depuis le cache avec les vrais statuts
          // CRITIQUE: Sans ce reload, this.books garde les anciens objets avec statuts temporaires
          // ce qui déclenche des re-validations en cascade dans BiblioValidationCell (cause mémoire)
          this.books = await livresAuteursService.getLivresAuteurs({ episode_oid: this.selectedEpisodeId });
        }

        // Auto-processing automatique des livres verified en arrière-plan (non-bloquant)
        Promise.resolve().then(async () => {
          try {
            await livresAuteursService.autoProcessVerifiedBooks();
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
      // Issue #85: Ignorer l'événement si on est en train de rafraîchir le cache
      // pour éviter un double appel à loadBooksForEpisode()
      if (this.isRefreshing) {
        return;
      }

      // Issue #160: Protection contre les race conditions
      // Si un changement d'épisode est déjà en cours, ignorer ce nouvel appel
      if (this.changeEpisodeLock) {
        console.warn('[Issue #160] Changement d\'épisode déjà en cours, appel ignoré pour éviter une race condition');
        return;
      }

      try {
        // Verrouiller pour empêcher les changements concurrents
        this.changeEpisodeLock = true;

        // Réinitialiser les filtres
        this.searchFilter = '';
        this.sortOrder = 'rating_desc';

        // Reset any previously fetched full episode
        this.selectedEpisodeFull = null;

        // Issue #156: Inverser l'ordre pour afficher d'abord titre/description/lien
        // AVANT de charger les livres (opération lente)

        // 1. D'ABORD: Récupérer les détails complets de l'épisode (description, corrections)
        try {
          const ep = await episodeService.getEpisodeById(this.selectedEpisodeId);
          this.selectedEpisodeFull = ep || null;
        } catch (err) {
          // Ne pas bloquer l'UI si l'endpoint n'est pas disponible
          console.warn('Impossible de récupérer les détails complets de l\'épisode:', err.message || err);
        }

        // 2. ENSUITE: Fetch automatiquement l'URL de la page RadioFrance si elle n'existe pas encore
        // Issue #89: Cela permet d'afficher rapidement le lien avant le chargement des livres
        if (this.selectedEpisodeFull && !this.selectedEpisodeFull.episode_page_url) {
          try {
            const result = await episodeService.fetchEpisodePageUrl(this.selectedEpisodeId);
            if (result.success && result.episode_page_url) {
              // Mettre à jour l'épisode avec l'URL récupérée
              this.selectedEpisodeFull.episode_page_url = result.episode_page_url;
            }
          } catch (err) {
            // Ne pas bloquer l'UI si le fetch échoue (épisode non trouvé sur RadioFrance, etc.)
            console.warn('Impossible de récupérer l\'URL de la page RadioFrance:', err.message || err);
          }
        }

        // 3. ENFIN: Charger les livres pour le nouvel épisode (opération lente)
        await this.loadBooksForEpisode();
      } finally {
        // Issue #160: Toujours déverrouiller, même en cas d'erreur
        this.changeEpisodeLock = false;
      }
    },

    async selectPreviousEpisode() {
      if (this.navLock) return;
      // Move to older episode (to the right on timeline) => index + 1
      const idx = this.currentEpisodeIndex;
      if (idx >= 0 && idx < this.episodesWithReviews.length - 1) {
        this.navLock = true;
        try {
          const prev = this.episodesWithReviews[idx + 1];
          this.selectedEpisodeId = prev.id;
          // trigger change flow
          await this.onEpisodeChange();
        } finally {
          this.navLock = false;
        }
      }
    },

    async selectNextEpisode() {
      if (this.navLock) return;
      // Move to more recent episode (to the left on timeline) => index - 1
      const idx = this.currentEpisodeIndex;
      if (idx > 0) {
        this.navLock = true;
        try {
          const next = this.episodesWithReviews[idx - 1];
          this.selectedEpisodeId = next.id;
          // trigger change flow
          await this.onEpisodeChange();
        } finally {
          this.navLock = false;
        }
      }
    },

    /**
     * Rafraîchit le cache pour l'épisode sélectionné
     */
    async refreshEpisodeCache() {
      if (!this.selectedEpisodeId) return;

      try {
        // Issue #85: Bloquer onEpisodeChange pendant le refresh pour éviter double appel
        this.isRefreshing = true;

        await livresAuteursService.deleteCacheByEpisode(this.selectedEpisodeId);

        // Recharger les données après suppression du cache
        await this.loadBooksForEpisode();
      } catch (error) {
        console.error('Erreur lors de la suppression du cache:', error);
        this.error = 'Erreur lors du rafraîchissement du cache';
      } finally {
        // Issue #85: Débloquer onEpisodeChange après le refresh
        this.isRefreshing = false;
      }
    },

    /**
     * Centre la liste déroulante sur l'épisode sélectionné quand on l'ouvre
     * Issue #164: Améliorer UX en centrant sur l'épisode actuel
     */
    scrollToSelectedEpisode() {
      if (!this.selectedEpisodeId || !this.$refs.episodeSelect) return;

      this.$nextTick(() => {
        const selectElement = this.$refs.episodeSelect;
        const selectedOption = selectElement.querySelector(`option[value="${this.selectedEpisodeId}"]`);

        if (selectedOption) {
          // Calculer l'index de l'option sélectionnée (en comptant l'option par défaut)
          const selectedIndex = Array.from(selectElement.options).indexOf(selectedOption);

          // Définir selectedIndex pour que le navigateur scroll automatiquement
          selectElement.selectedIndex = selectedIndex;
        }
      });
    },

    /**
     * Formate l'affichage d'un épisode dans la liste
     * Issue #164: Utilise des pastilles de couleur pour les statuts
     */
    formatEpisodeOption(episode) {
      const date = new Date(episode.date).toLocaleDateString('fr-FR');
      const title = episode.titre_corrige || episode.titre;

      // 🔴 Pastille rouge pour les épisodes avec livres incomplets (livres à valider)
      if (episode.has_incomplete_books === true) {
        return `🔴 ${date} - ${title}`;
      }

      // 🟢 Pastille verte pour les épisodes déjà traités (tous validés)
      // ⚪ Pastille grise pour les épisodes non traités
      const prefix = episode.has_cached_books ? '🟢 ' : '⚪ ';
      return `${prefix}${date} - ${title}`;
    },

    /**
     * Retourne la classe CSS pour identifier les épisodes incomplets (livres non validés)
     */
    getEpisodeClass(episode) {
      // Épisodes avec livres non validés → couleur orange
      if (episode.has_incomplete_books === true) {
        return 'episode-incomplete';
      }
      return '';
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
      this.currentBookToValidate = book;

      // Pré-remplir le formulaire avec les suggestions (modifiables par l'utilisateur)
      const suggestion = this.validationSuggestions.get(this.getBookKey(book));

      // Issue #88: Utiliser suggestion en PRIORITÉ (même source que l'affichage "Suggestions Babelio")
      // puis book.suggested_* (enrichissement backend), puis fallback sur données originales
      this.validationForm = {
        author: suggestion?.author || book.suggested_author || book.auteur,
        title: suggestion?.title || book.suggested_title || book.titre,
        publisher: book.editeur || ''
      };

      this.showValidationModal = true;
    },

    /**
     * Ouvre le modal d'ajout manuel pour un livre non trouvé (validation_status: 'not_found')
     */
    addManualBook(book) {
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

        // Récupérer l'avis_critique_id depuis l'épisode sélectionné
  const selectedEpisode = this.episodesWithReviews?.find(ep => String(ep.id) === String(this.selectedEpisodeId));

        const validationData = {
          cache_id: book.cache_id, // Utiliser le cache_id du livre
          episode_oid: this.selectedEpisodeId,
          avis_critique_id: selectedEpisode?.avis_critique_id,
          // Issue #159: Utiliser les données validées par l'utilisateur au lieu des données d'origine
          auteur: this.validationForm.author,
          titre: this.validationForm.title,
          editeur: this.validationForm.publisher,
          user_validated_author: this.validationForm.author,
          user_validated_title: this.validationForm.title,
          user_validated_publisher: this.validationForm.publisher
        };

        // Issue #85: Transmettre babelio_url et babelio_publisher si le livre a été enrichi
        console.log('🔍 [DEBUG Issue #85] Structure book COMPLETE:', JSON.stringify(book, null, 2));
        if (book.babelio_url) {
          validationData.babelio_url = book.babelio_url;
          console.log('✅ babelio_url ajouté:', book.babelio_url);
        } else {
          console.log('❌ PAS de babelio_url dans book');
        }
        if (book.babelio_publisher) {
          validationData.babelio_publisher = book.babelio_publisher;
          console.log('✅ babelio_publisher ajouté:', book.babelio_publisher);
        } else {
          console.log('❌ PAS de babelio_publisher dans book');
        }

        console.log('🚀 Données FINALES envoyées pour validation:', JSON.stringify(validationData, null, 2));
        const result = await livresAuteursService.validateSuggestion(validationData);

        // Fermer le modal et recharger les données
        this.closeValidationModal();
        await this.loadBooksForEpisode();
        // Recharger la liste des épisodes pour mettre à jour le flag has_incomplete_books
        await this.loadEpisodesWithReviews();
      } catch (error) {
        console.error('❌ Erreur lors de la validation:', error);
        console.error('❌ Réponse du serveur:', error.response?.data);
        console.error('❌ Status:', error.response?.status);

        // Afficher un message user-friendly
        if (error.response?.status === 422) {
          alert(`Erreur de validation: ${error.response.data.detail || 'Données invalides'}`);
        }
      }
    },

    /**
     * Soumet l'ajout manuel d'un livre (unifié avec validateSuggestion)
     */
    async submitManualAdd() {
      try {
        const book = this.currentBookToAdd;

        // Utiliser directement validateSuggestion pour l'ajout manuel
        // Récupérer l'avis_critique_id depuis l'épisode sélectionné
  const selectedEpisode = this.episodesWithReviews?.find(ep => String(ep.id) === String(this.selectedEpisodeId));

        const validationData = {
          cache_id: book.cache_id,
          episode_oid: this.selectedEpisodeId,
          avis_critique_id: selectedEpisode?.avis_critique_id,
          // Issue #159: Utiliser les données saisies par l'utilisateur au lieu des données d'origine
          auteur: this.manualBookForm.author,
          titre: this.manualBookForm.title,
          editeur: this.manualBookForm.publisher || 'Éditeur inconnu',
          user_validated_author: this.manualBookForm.author,
          user_validated_title: this.manualBookForm.title,
          user_validated_publisher: this.manualBookForm.publisher || 'Éditeur inconnu',
          // Champs suggested pour l'affichage (corrections de l'utilisateur)
          suggested_author: this.manualBookForm.author,
          suggested_title: this.manualBookForm.title
        };

        // Issue #85: Transmettre babelio_url et babelio_publisher si le livre a été enrichi
        if (book.babelio_url) {
          validationData.babelio_url = book.babelio_url;
        }
        if (book.babelio_publisher) {
          validationData.babelio_publisher = book.babelio_publisher;
        }

        // Un seul appel unifié pour créer le livre ET mettre à jour le cache
        await livresAuteursService.validateSuggestion(validationData);

        // Fermer le modal et recharger les données
        this.closeManualAddModal();
        await this.loadBooksForEpisode();
        // Recharger la liste des épisodes pour mettre à jour le flag has_incomplete_books
        await this.loadEpisodesWithReviews();
      } catch (error) {
        console.error('Erreur lors de l\'ajout manuel:', error);
      }
    },

    // ========== MÉTHODES POUR ISSUE #159: URL BABELIO AUTO-FILL ==========

    /**
     * Valide si une URL est une URL Babelio valide
     */
    isValidBabelioUrl(url) {
      return url && url.includes('babelio.com');
    },

    /**
     * Extrait les informations depuis une URL Babelio
     * @param {string} modalType - 'validation' ou 'manual'
     */
    async extractFromBabelioUrl(modalType) {
      const isValidation = modalType === 'validation';
      const url = isValidation ? this.validationBabelioUrl : this.manualBabelioUrl;

      // Validation de l'URL
      if (!this.isValidBabelioUrl(url)) {
        const error = 'URL Babelio invalide';
        if (isValidation) {
          this.validationUrlError = error;
        } else {
          this.manualUrlError = error;
        }
        return;
      }

      // Réinitialiser les erreurs
      if (isValidation) {
        this.validationUrlError = null;
        this.validationExtractingFromUrl = true;
      } else {
        this.manualUrlError = null;
        this.manualExtractingFromUrl = true;
      }

      try {
        // Appeler l'API backend pour extraire les données (Issue #159)
        // Les cookies Babelio sont transmis pour contourner le captcha (Issue #245)
        const response = await axios.post('/api/babelio/extract-from-url', {
          babelio_url: url.trim(),
          babelio_cookies: sessionStorage.getItem('babelio_cookies') || null,
        });

        if (response.data.status === 'success' && response.data.data) {
          const data = response.data.data;

          // Remplir automatiquement les champs avec les données extraites
          const form = isValidation ? this.validationForm : this.manualBookForm;

          // Remplir le titre (priorité: titre extrait)
          if (data.titre) {
            form.title = data.titre;
          }

          // Remplir l'auteur (priorité: auteur extrait)
          if (data.auteur) {
            form.author = data.auteur;
          }

          // Remplir l'éditeur (priorité: éditeur extrait)
          if (data.editeur) {
            form.publisher = data.editeur;
          }

        } else {
          const error = response.data.message || 'Erreur lors de l\'extraction';
          if (isValidation) {
            this.validationUrlError = error;
          } else {
            this.manualUrlError = error;
          }
        }
      } catch (error) {
        const errorMsg = error.response?.data?.message || error.message || 'Erreur lors de l\'extraction';
        if (isValidation) {
          this.validationUrlError = errorMsg;
        } else {
          this.manualUrlError = errorMsg;
        }
        console.error('Erreur extraction URL Babelio:', error);
      } finally {
        // Arrêter l'indicateur de chargement
        if (isValidation) {
          this.validationExtractingFromUrl = false;
        } else {
          this.manualExtractingFromUrl = false;
        }
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
      this.validationForm = {
        author: '',
        title: '',
        publisher: ''
      };
      // Issue #159: Réinitialiser les champs URL Babelio
      this.validationBabelioUrl = '';
      this.validationUrlError = null;
      this.validationExtractingFromUrl = false;
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
      // Issue #159: Réinitialiser les champs URL Babelio
      this.manualBabelioUrl = '';
      this.manualUrlError = null;
      this.manualExtractingFromUrl = false;
    },


    /**
     * Auto-validation des livres et envoi des résultats au backend
     */
    async autoValidateAndSendResults() {
      if (!this.books || this.books.length === 0) return;

      try {
        const validatedBooks = [];

        // Valider chaque livre avec BiblioValidationService
        for (const book of this.books) {
          try {
            const validationResult = await BiblioValidationService.validateBiblio(
              book.auteur,
              book.titre,
              book.editeur || '',
              this.selectedEpisodeId
            );

            // Convertir le résultat de validation au format backend
            let status = validationResult.status;

            // BiblioValidationService retourne 'corrected' mais backend attend 'suggestion'
            if (status === 'corrected') {
              status = 'suggestion';
            }

            // Issue #85: Utiliser buildBookDataForBackend pour construire l'objet
            // Cette fonction pure garantit que TOUS les champs sont transmis,
            // y compris babelio_url et babelio_publisher (enrichissement automatique)
            const bookForBackend = buildBookDataForBackend(book, validationResult, status);

            validatedBooks.push(bookForBackend);

          } catch (validationError) {
            console.warn(`⚠️ Erreur validation ${book.auteur}:`, validationError);
            // En cas d'erreur, garder comme not_found
            validatedBooks.push({
              auteur: book.auteur,
              titre: book.titre,
              editeur: book.editeur || '',
              programme: book.programme || false,
              validation_status: 'not_found'
            });
          }
        }

        // Récupérer l'avis_critique_id depuis l'épisode sélectionné
  const selectedEpisode = this.episodesWithReviews?.find(ep => String(ep.id) === String(this.selectedEpisodeId));
        const avis_critique_id = selectedEpisode?.avis_critique_id;


        // Envoyer les résultats au backend via le service existant
        const result = await livresAuteursService.setValidationResults({
          episode_oid: this.selectedEpisodeId,
          avis_critique_id: avis_critique_id,
          books: validatedBooks
        });

      } catch (error) {
        console.error('❌ Erreur auto-validation:', error);
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

.validation-stats {
  font-size: 0.95rem;
  color: #888;
  margin-left: 0.5rem;
}

.validation-stats .stat-item {
  font-weight: 500;
  color: #555;
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
  overflow-x: auto;
  overflow-y: hidden;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.books-table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
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

/* Style pour les livres avec statut mongo */
.books-table tbody tr.mongo-book {
  background: #f3f4f6;
  opacity: 0.75;
  color: #6b7280;
}

.books-table tbody tr.mongo-book:hover {
  background: #e5e7eb;
}

.books-table tbody tr.mongo-book .author-cell,
.books-table tbody tr.mongo-book .title-cell {
  color: #4b5563;
  font-style: italic;
}

.mongo-status {
  color: #10b981;
  font-size: 0.875rem;
  font-weight: 500;
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

/* Issue #96: Style pour les liens cliquables - inherit le style parent */
.clickable-link {
  color: inherit;
  text-decoration: none;
  cursor: pointer;
}

.clickable-link:hover {
  text-decoration: underline;
}

.publisher-cell {
  color: #666;
}

.validation-header {
  padding: 0.5rem;
  text-align: left;
  font-weight: 600;
  color: #333;
  border-bottom: 2px solid #eee;
  min-width: 180px;
  max-width: 240px;
  width: 240px;
}

.validation-header-expanded {
  max-width: 290px;
  width: 290px;
}

.validation-cell {
  padding: 0.5rem;
  vertical-align: top;
  min-width: 180px;
  max-width: 240px;
  width: 240px;
  word-wrap: break-word;
  overflow-wrap: break-word;
  font-size: 0.85rem;
  line-height: 1.3;
}

.validation-cell-expanded {
  max-width: 290px;
  width: 290px;
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

.episode-select-wrapper {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.nav-episode-btn {
  background: #111827;
  color: #fff;
  border: 1px solid rgba(255,255,255,0.06);
  padding: 0.5rem 0.75rem;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
}

.nav-episode-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.prev-btn {
  margin-right: 0.25rem;
}

.next-btn {
  margin-left: 0.25rem;
}

.form-control {
  flex: 1;
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

/* Issue #164: Limiter la hauteur de la liste déroulante à 8 éléments */
#episode-select {
  max-height: 20em; /* Environ 8 lignes avec la taille de police actuelle */
  overflow-y: auto;
}

.btn-icon-refresh {
  flex-shrink: 0;
  width: 38px;
  height: 38px;
  padding: 0;
  border: 1px solid #ddd;
  border-radius: 6px;
  background: white;
  font-size: 1.2rem;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.btn-icon-refresh:hover {
  background: #f8f9fa;
  border-color: #667eea;
  transform: rotate(180deg);
}

.btn-icon-refresh:active {
  transform: rotate(180deg) scale(0.95);
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
  min-width: 160px;
  width: 200px;
}

.actions-cell {
  width: 200px;
  padding: 0.5rem;
  text-align: center;
  vertical-align: middle;
}

.actions-cell .btn {
  margin: 0 auto;
  display: inline-block;
}

/* Largeurs fixes pour équilibrer le tableau */
.status-header {
  width: 50px;
}

.author-cell,
.books-table th:nth-child(2) {
  width: 180px;
}

.title-cell,
.books-table th:nth-child(3) {
  width: 200px;
}

.publisher-cell,
.books-table th:nth-child(4) {
  width: 120px;
}

/* Colonne YAML visible */
.capture-header,
.capture-cell {
  width: 90px;
  padding: 0.5rem;
  text-align: center;
}

/* Colonne YAML cachée - espace réduit */
.capture-header-hidden {
  width: 40px;
  padding: 0.25rem;
  text-align: center;
  background: #f8f9fa;
}

/* En-tête YAML avec bouton toggle */
.capture-header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.25rem;
}

/* Boutons toggle YAML */
.toggle-yaml-btn,
.toggle-yaml-btn-only,
.toggle-yaml-btn-show,
.toggle-yaml-btn-inline {
  background: none;
  border: none;
  cursor: pointer;
  padding: 0.25rem;
  border-radius: 4px;
  font-size: 0.8rem;
  transition: background-color 0.2s ease;
}

.toggle-yaml-btn:hover,
.toggle-yaml-btn-only:hover,
.toggle-yaml-btn-show:hover,
.toggle-yaml-btn-inline:hover {
  background: rgba(0, 0, 0, 0.1);
}

.toggle-yaml-btn-only {
  width: 100%;
  text-align: center;
  font-size: 1rem;
}

.toggle-yaml-btn-show {
  font-size: 0.7rem;
  color: #666;
  white-space: nowrap;
  width: 100%;
  text-align: center;
}

.toggle-yaml-btn-inline {
  float: right;
  margin-left: 0.5rem;
  font-size: 0.75rem;
  color: #666;
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

/* Accordéon détails de l'épisode */
.episode-details-accordion {
  margin-top: 1rem;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  overflow: hidden;
  background: #f9fafb;
}

.accordion-toggle {
  width: 100%;
  padding: 0.75rem 1rem;
  background: #f3f4f6;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  font-weight: 500;
  color: #374151;
  transition: background-color 0.2s;
}

.accordion-toggle:hover {
  background: #e5e7eb;
}

.toggle-icon {
  font-size: 0.75rem;
  color: #6b7280;
  transition: transform 0.2s;
}

.toggle-label {
  color: #4b5563;
}

.accordion-content {
  padding: 1rem;
  background: white;
  border-top: 1px solid #e5e7eb;
  animation: slideDown 0.2s ease-out;
}

@keyframes slideDown {
  from {
    opacity: 0;
    max-height: 0;
  }
  to {
    opacity: 1;
    max-height: 500px;
  }
}

/* Issue #89: Container pour logo + infos épisode en layout horizontal */
.episode-info-container {
  display: flex;
  gap: 1.5rem;
  align-items: center;
}

/* Issue #89: Logo RadioFrance cliquable */
.episode-logo-link {
  flex-shrink: 0;
  display: block;
  transition: transform 0.2s ease, opacity 0.2s ease;
}

.episode-logo-link:hover {
  transform: scale(1.05);
  opacity: 0.9;
}

.episode-logo {
  width: 80px;
  height: 80px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  object-fit: cover;
}

.episode-info {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  flex: 1;
}

.info-section {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.info-section strong {
  color: #374151;
  font-size: 0.875rem;
}

.episode-title {
  margin: 0;
  padding: 0.5rem;
  background: #f9fafb;
  border-left: 3px solid #3b82f6;
  border-radius: 4px;
  font-size: 0.9rem;
  color: #1f2937;
}

.episode-description {
  margin: 0;
  padding: 0.75rem;
  background: #f9fafb;
  border-left: 3px solid #10b981;
  border-radius: 4px;
  font-size: 0.85rem;
  line-height: 1.6;
  color: #374151;
  max-height: 300px;
  overflow-y: auto;
}

.episode-description::-webkit-scrollbar {
  width: 6px;
}

.episode-description::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 3px;
}

.episode-description::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 3px;
}

.episode-description::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}

/* Épisodes avec livres incomplets (non validés) - couleur orange */
.episode-incomplete {
  color: #f97316; /* orange-500 */
  font-weight: 500;
}

/* ========== STYLES POUR ISSUE #159: URL BABELIO AUTO-FILL ========== */

/* Groupe du champ URL Babelio */
.babelio-url-group {
  background: #f0f9ff;
  padding: 1rem;
  border-radius: 8px;
  border: 1px solid #bae6fd;
  margin-bottom: 1rem;
}

.babelio-url-group label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
  font-weight: 600;
  color: #0369a1;
}

/* Bouton d'extraction */
.btn-extract-url {
  background: #0284c7;
  color: white;
  border: none;
  padding: 0.25rem 0.75rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.85rem;
  font-weight: 500;
  transition: all 0.2s;
  margin-left: auto;
}

.btn-extract-url:hover {
  background: #0369a1;
  transform: translateY(-1px);
}

.btn-extract-url:active {
  transform: translateY(0);
}

/* Indicateur d'extraction en cours */
.extracting-indicator {
  font-size: 0.85rem;
  color: #0369a1;
  font-style: italic;
  margin-left: auto;
}

/* Message d'erreur URL */
.url-error {
  margin-top: 0.5rem;
  padding: 0.5rem;
  background: #fee2e2;
  border: 1px solid #fecaca;
  border-radius: 4px;
  color: #991b1b;
  font-size: 0.85rem;
}

/* Legend styles */
.legend-section {
  margin: 1rem 0;
}

.legend-box {
  background-color: #f8f9fa;
  border: 1px solid #dee2e6;
  border-radius: 0.375rem;
  padding: 1rem;
}

.legend-box h6 {
  font-weight: 600;
  margin-bottom: 0.5rem;
  color: #495057;
}

.legend-list {
  list-style: none;
  padding: 0;
  margin: 0.5rem 0;
}

.legend-list li {
  margin-bottom: 0.5rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.badge {
  display: inline-block;
  padding: 0.25rem 0.5rem;
  font-size: 0.875rem;
  font-weight: 500;
  line-height: 1;
  text-align: center;
  white-space: nowrap;
  vertical-align: baseline;
  border-radius: 0.25rem;
}

.badge.bg-success {
  background-color: #28a745;
  color: white;
}

.badge.bg-secondary {
  background-color: #6c757d;
  color: white;
}

.badge.bg-warning {
  background-color: #ffc107;
  color: #212529;
}

.badge.bg-danger {
  background-color: #dc3545;
  color: white;
}
</style>
