<template>
  <div class="emissions">
    <!-- Navigation -->
    <Navigation pageTitle="Émissions" />

    <main>
      <!-- Sélecteur d'épisode -->
      <section class="episode-selector-section">
        <div class="episode-selector card">
          <!-- État de chargement des émissions -->
          <div v-if="emissionsLoading" class="loading">
            Chargement des émissions...
          </div>

          <!-- Affichage d'erreur des émissions -->
          <div v-if="emissionsError" class="alert alert-error">
            {{ emissionsError }}
            <button @click="loadAllEmissions" class="btn btn-primary" style="margin-left: 1rem;">
              Réessayer
            </button>
          </div>

          <!-- Sélecteur d'épisode -->
          <div v-if="!emissionsLoading && !emissionsError && emissions.length > 0" class="form-group">
            <label for="episode-select" class="form-label">
              Choisir une émission ({{ emissions.length }} disponibles:
              <span
                class="badge-counters-tooltip"
                :title="`🟢 ${emissionsPerfectCount}: Avis extraits, tous matchés, comptes égaux, toutes notes présentes\n🔴 ${emissionsCountMismatchCount}: Avis extraits mais # livres summary ≠ # livres mongo OU au moins une note manquante\n🟡 ${emissionsUnmatchedCount}: Avis extraits, comptes égaux, toutes notes présentes mais ≥1 livre non matché\n⚪ ${emissionsNoAvisCount}: Avis pas encore extraits`"
              >
                🟢 {{ emissionsPerfectCount }} / 🔴 {{ emissionsCountMismatchCount }} / 🟡 {{ emissionsUnmatchedCount }} / ⚪ {{ emissionsNoAvisCount }}
              </span>)
            </label>
            <div class="episode-select-wrapper">
              <button
                class="nav-episode-btn prev-btn"
                @click.prevent="selectPreviousEpisode"
                :disabled="!hasPreviousEpisode"
                aria-label="Émission précédente"
                data-testid="prev-emission-button"
              >
                ◀️ Précédent
              </button>
              <EpisodeDropdown
                v-model="selectedEmissionId"
                :episodes="emissionsAsEpisodes"
                @update:modelValue="onEmissionChange"
              />
              <button
                class="nav-episode-btn next-btn"
                @click.prevent="selectNextEpisode"
                :disabled="!hasNextEpisode"
                aria-label="Émission suivante"
                data-testid="next-emission-button"
              >
                Suivant ▶️
              </button>

              <!-- Bouton Extraire/Ré-extraire les avis -->
              <button
                v-if="selectedEmissionId && selectedEmissionDetails?.summary && !avisLoading && avis.length === 0"
                @click="reextractAvis"
                :disabled="avisExtracting"
                class="btn-extract"
              >
                {{ avisExtracting ? 'Extraction...' : '🚀 Extraire les avis' }}
              </button>

              <button
                v-else-if="selectedEmissionId && selectedEmissionDetails?.summary && !avisLoading"
                @click="reextractAvis"
                :disabled="avisExtracting"
                class="btn-reextract"
              >
                {{ avisExtracting ? 'Ré-extraction...' : '🔄 Ré-extraire' }}
              </button>
            </div>
          </div>

          <!-- Message si aucune émission -->
          <div v-if="!emissionsLoading && !emissionsError && emissions.length === 0" class="alert alert-info">
            Aucune émission disponible.
          </div>
        </div>

        <!-- Détails de l'épisode (accordéon replié) -->
        <div v-if="selectedEmissionDetails && selectedEmissionDetails.episode" class="episode-details-accordion">
          <button
            @click="showEpisodeDetails = !showEpisodeDetails"
            class="accordion-toggle"
            :aria-expanded="showEpisodeDetails"
          >
            <span class="toggle-icon">{{ showEpisodeDetails ? '▼' : '▶' }}</span>
            <span class="toggle-label">Détails de l'emission (titre et description)</span>
          </button>
          <div v-if="showEpisodeDetails" class="accordion-content">
            <div class="episode-info-container">
              <!-- Logo RadioFrance cliquable à gauche -->
              <a
                v-if="selectedEmissionDetails.episode.episode_page_url"
                :href="selectedEmissionDetails.episode.episode_page_url"
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
                  <p class="episode-title">{{ selectedEmissionDetails.episode.titre || 'Sans titre' }}</p>
                </div>
                <div class="info-section">
                  <strong>Description :</strong>
                  <p class="episode-description">{{ selectedEmissionDetails.episode.description || 'Aucune description disponible' }}</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- Détails de l'émission -->
      <section v-if="selectedEmissionDetails" class="emission-details-section">
        <div class="card">
          <!-- État de chargement des détails -->
          <div v-if="detailsLoading" class="loading">
            Chargement des détails de l'émission...
          </div>

          <!-- Affichage d'erreur des détails -->
          <div v-if="detailsError" class="alert alert-error">
            {{ detailsError }}
          </div>

          <!-- Bloc info émission -->
          <div v-if="!detailsLoading && !detailsError" class="emission-info" :class="{ 'no-border': isSelectedEmissionPerfect }">
            <h2>
              <span v-if="selectedEmissionDetails.episode?.date" class="episode-date-prefix">
                {{ formatDateCompact(selectedEmissionDetails.episode.date) }} -
              </span>
              {{ selectedEmissionDetails.episode?.titre || 'Sans titre' }}
              <span v-if="selectedEmissionDetails.episode?.duree" class="episode-duration-suffix">
                ({{ formatDurationCompact(selectedEmissionDetails.episode.duree) }})
              </span>
            </h2>
          </div>

          <!-- Stats de matching des avis (affiché au-dessus de la liste des livres) -->
          <div v-if="!avisLoading && avisMatchingStats && !isSelectedEmissionPerfect" class="matching-stats">
            <div class="stats-header">
              <span class="stats-warning" v-if="avisMatchingStats.livres_summary !== avisMatchingStats.livres_mongo">
                ⚠️ Livres summary ({{ avisMatchingStats.livres_summary }}) ≠ Livres Mongo ({{ avisMatchingStats.livres_mongo }})
              </span>
            </div>
            <div class="stats-details">
              <span class="stat-item stat-phase1">Phase 1 (exact): {{ avisMatchingStats.match_phase1 }}</span>
              <span class="stat-item stat-phase2">Phase 2 (partiel): {{ avisMatchingStats.match_phase2 }}</span>
              <span class="stat-item stat-phase3">Phase 3 (similarité): {{ avisMatchingStats.match_phase3 }}</span>
              <span class="stat-item stat-phase4" v-if="avisMatchingStats.match_phase4 > 0">Phase 4 (fuzzy): {{ avisMatchingStats.match_phase4 }}</span>
              <span class="stat-item stat-unmatched" v-if="avisMatchingStats.unmatched > 0">
                ⚠ Sans match: {{ avisMatchingStats.unmatched }}
              </span>
            </div>
          </div>

          <!-- Liste des livres (repliable avec mémoire) -->
          <div v-if="!detailsLoading && !detailsError && selectedEmissionDetails.books?.length > 0 && !isSelectedEmissionPerfect" class="collapsible-section">
            <button
              @click="showBooksDetails = !showBooksDetails"
              class="collapsible-toggle"
              :aria-expanded="showBooksDetails"
            >
              <span class="toggle-icon">{{ showBooksDetails ? '▼' : '▶' }}</span>
              Livres discutés ({{ selectedEmissionDetails.books.length }})
            </button>
            <ul v-if="showBooksDetails" class="collapsible-content">
              <li v-for="book in selectedEmissionDetails.books" :key="book._id || book.titre">
                <router-link
                  v-if="book.auteur_id"
                  :to="`/auteur/${book.auteur_id}`"
                  class="author-link"
                >
                  {{ book.auteur }}
                </router-link>
                <span v-else>{{ book.auteur }}</span>
                <span> - </span>
                <router-link
                  v-if="book.livre_id"
                  :to="`/livre/${book.livre_id}`"
                  class="book-link"
                >
                  <strong>{{ book.titre }}</strong>
                </router-link>
                <strong v-else>{{ book.titre }}</strong>
              </li>
            </ul>
          </div>

          <!-- Liste des critiques (repliable avec mémoire) -->
          <div v-if="!detailsLoading && !detailsError && selectedEmissionDetails.critiques?.length > 0 && !isSelectedEmissionPerfect" class="collapsible-section">
            <button
              @click="showCritiquesDetails = !showCritiquesDetails"
              class="collapsible-toggle"
              :aria-expanded="showCritiquesDetails"
            >
              <span class="toggle-icon">{{ showCritiquesDetails ? '▼' : '▶' }}</span>
              Critiques présents ({{ selectedEmissionDetails.critiques.length }})
            </button>
            <ul v-if="showCritiquesDetails" class="collapsible-content">
              <li v-for="critique in selectedEmissionDetails.critiques" :key="critique.id">
                {{ critique.nom }}
                <span v-if="critique.animateur" class="animateur-badge">Animateur</span>
              </li>
            </ul>
          </div>

          <!-- Avis structurés -->
          <div v-if="!detailsLoading && !detailsError && selectedEmissionDetails.summary" class="avis-section-container" :class="{ 'no-top-border': isSelectedEmissionPerfect }">
            <!-- État de chargement des avis -->
            <div v-if="avisLoading" class="loading-small">
              {{ avisExtracting ? 'Extraction des avis en cours...' : 'Chargement des avis...' }}
            </div>

            <!-- Erreur avis -->
            <div v-if="avisError" class="alert alert-warning">
              {{ avisError }}
            </div>

            <!-- Tableau des avis structurés -->
            <AvisTable
              v-if="!avisLoading && !avisError"
              :avis="avis"
              :emission-date="selectedEmissionDetails.episode?.date"
              :matching-stats="avisMatchingStats"
              :livres-mongo-count="avisMatchingStats?.livres_mongo || 0"
            />

            <!-- DEBUG: Affichage du summary markdown pour comparaison (phase de test) -->
            <details v-if="!avisLoading && avis.length > 0 && !isSelectedEmissionPerfect" class="summary-debug">
              <summary class="summary-debug-toggle">Afficher le summary markdown brut (comparaison)</summary>
              <div class="markdown-content summary-debug-content" v-html="renderMarkdown(selectedEmissionDetails.summary)"></div>
            </details>
          </div>
        </div>
      </section>
    </main>
  </div>
</template>

<script>
import { onMounted, onBeforeUnmount, ref, computed, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import Navigation from '../components/Navigation.vue';
import EpisodeDropdown from '../components/EpisodeDropdown.vue';
import AvisTable from '../components/AvisTable.vue';
import { emissionsService, episodeService, avisService } from '../services/api';
import { marked } from 'marked';

export default {
  name: 'Emissions',

  components: {
    Navigation,
    EpisodeDropdown,
    AvisTable,
  },

  setup() {
    const route = useRoute();
    const router = useRouter();

    // État des émissions
    const emissions = ref([]);
    const emissionsLoading = ref(false);
    const emissionsError = ref(null);

    // État des détails de l'émission sélectionnée
    const selectedEmissionId = ref(null);
    const selectedEmissionDetails = ref(null);
    const detailsLoading = ref(false);
    const detailsError = ref(null);

    // Navigation locks
    const isChangingEpisode = ref(false);

    // Affichage détails épisode (accordéon) - avec persistance localStorage
    const showEpisodeDetails = ref(
      localStorage.getItem('emissions.showEpisodeDetails') === 'true'
    );
    const showBooksDetails = ref(
      localStorage.getItem('emissions.showBooksDetails') === 'true'
    );
    const showCritiquesDetails = ref(
      localStorage.getItem('emissions.showCritiquesDetails') === 'true'
    );

    // Watchers pour persister l'état dans localStorage
    watch(showEpisodeDetails, (val) => {
      localStorage.setItem('emissions.showEpisodeDetails', val ? 'true' : 'false');
    });
    watch(showBooksDetails, (val) => {
      localStorage.setItem('emissions.showBooksDetails', val ? 'true' : 'false');
    });
    watch(showCritiquesDetails, (val) => {
      localStorage.setItem('emissions.showCritiquesDetails', val ? 'true' : 'false');
    });

    // État des avis structurés
    const avis = ref([]);
    const avisLoading = ref(false);
    const avisError = ref(null);
    const avisExtracting = ref(false);
    const avisMatchingStats = ref(null);

    /**
     * Charge les avis pour une émission (extraction auto si nécessaire)
     */
    const loadAvisForEmission = async (emissionId) => {
      if (!emissionId) return;

      avisLoading.value = true;
      avisError.value = null;
      avisExtracting.value = false;
      avisMatchingStats.value = null;

      try {
        // 1. Essayer de charger les avis existants
        const result = await avisService.getAvisByEmission(emissionId);
        avis.value = result.avis || [];
        avisMatchingStats.value = result.matching_stats || null;

        // 2. Si pas d'avis, lancer l'extraction automatique
        if (avis.value.length === 0) {
          avisExtracting.value = true;
          try {
            const extractResult = await avisService.extractAvis(emissionId);

            // Si extraction réussie, recharger les avis ET les émissions pour MAJ badge
            if (extractResult.extracted_count > 0) {
              const reloadResult = await avisService.getAvisByEmission(emissionId);
              avis.value = reloadResult.avis || [];
              avisMatchingStats.value = reloadResult.matching_stats || null;

              // Recharger la liste des émissions pour mettre à jour badge_status et compteurs
              try {
                const updatedEmissions = await emissionsService.getAllEmissions();
                emissions.value = updatedEmissions;
              } catch (emissionsError) {
                console.warn('Impossible de recharger les émissions:', emissionsError.message);
              }
            }
          } catch (extractError) {
            // L'extraction peut échouer si pas de summary, ce n'est pas grave
            console.warn('Extraction avis échouée:', extractError.message);
          }
        }
      } catch (error) {
        console.error('Erreur chargement avis:', error);
        avisError.value = error.message || 'Erreur lors du chargement des avis';
      } finally {
        avisLoading.value = false;
        avisExtracting.value = false;
      }
    };

    /**
     * Force la ré-extraction des avis (supprime les anciens et ré-extrait)
     */
    const reextractAvis = async () => {
      if (!selectedEmissionId.value) return;

      avisLoading.value = true;
      avisExtracting.value = true;
      avisError.value = null;

      try {
        // L'endpoint POST /api/avis/extract supprime les anciens avis avant d'extraire
        const extractResult = await avisService.extractAvis(selectedEmissionId.value);

        // Recharger les avis ET les stats de matching (Issue #185)
        const reloadResult = await avisService.getAvisByEmission(selectedEmissionId.value);
        avis.value = reloadResult.avis || [];
        avisMatchingStats.value = reloadResult.matching_stats || null;

        // Recharger la liste des émissions pour mettre à jour badge_status et compteurs
        try {
          const updatedEmissions = await emissionsService.getAllEmissions();
          emissions.value = updatedEmissions;
        } catch (emissionsError) {
          console.warn('Impossible de recharger les émissions:', emissionsError.message);
        }

        console.log(`Ré-extraction terminée: ${extractResult.extracted_count} avis`);
      } catch (error) {
        console.error('Erreur ré-extraction avis:', error);
        avisError.value = error.message || 'Erreur lors de la ré-extraction des avis';
      } finally {
        avisLoading.value = false;
        avisExtracting.value = false;
      }
    };

    /**
     * Sélectionne l'émission par priorité de badge.
     *
     * Priorité : 🔴 count_mismatch > 🟡 unmatched > ⚪ no_avis > 🟢 perfect
     *
     * Dans chaque catégorie, sélectionne la plus récente (déjà triée par date DESC).
     */
    const selectEmissionByBadgePriority = (emissionsList) => {
      if (!emissionsList || emissionsList.length === 0) return null;

      // Ordre de priorité des badges
      const priorityOrder = ['count_mismatch', 'unmatched', 'no_avis', 'perfect'];

      // Pour chaque priorité, chercher la première émission avec ce badge
      for (const badgeStatus of priorityOrder) {
        const found = emissionsList.find(e => e.badge_status === badgeStatus);
        if (found) {
          return found;
        }
      }

      // Fallback : retourner la plus récente (premier élément)
      return emissionsList[0];
    };

    /**
     * Charge toutes les émissions
     */
    const loadAllEmissions = async () => {
      emissionsLoading.value = true;
      emissionsError.value = null;

      try {
        const data = await emissionsService.getAllEmissions();
        emissions.value = data;

        // Auto-sélectionner selon priorité de badge (🔴 > 🟡 > ⚪ > 🟢)
        if (data.length > 0 && !route.params.date) {
          const selectedEmission = selectEmissionByBadgePriority(data);
          if (selectedEmission) {
            const dateStr = formatDateForUrl(selectedEmission.date);
            router.replace(`/emissions/${dateStr}`);
          }
        }
      } catch (error) {
        console.error('Erreur chargement émissions:', error);
        emissionsError.value = error.message || 'Erreur lors du chargement des émissions';
      } finally {
        emissionsLoading.value = false;
      }
    };

    /**
     * Charge les détails d'une émission par ID
     */
    const loadEmissionDetails = async (emissionId) => {
      if (!emissionId) return;

      detailsLoading.value = true;
      detailsError.value = null;

      try {
        const data = await emissionsService.getEmissionDetails(emissionId);
        selectedEmissionDetails.value = data;
      } catch (error) {
        console.error('Erreur chargement détails émission:', error);
        detailsError.value = error.message || 'Erreur lors du chargement des détails';
      } finally {
        detailsLoading.value = false;
      }
    };

    /**
     * Charge une émission par date (format YYYYMMDD)
     */
    const loadEmissionByDate = async (dateStr) => {
      detailsLoading.value = true;
      detailsError.value = null;

      // Reset des avis avant de charger une nouvelle émission
      avis.value = [];
      avisError.value = null;

      try {
        const data = await emissionsService.getEmissionByDate(dateStr);
        selectedEmissionDetails.value = data;
        selectedEmissionId.value = data.emission.id;

        // Auto-fetch URL RadioFrance en arrière-plan (non bloquant)
        if (selectedEmissionDetails.value.episode && !selectedEmissionDetails.value.episode.episode_page_url) {
          const episodeId = data.emission.episode_id;
          if (episodeId) {
            // Lancer fetch en arrière-plan sans await
            episodeService.fetchEpisodePageUrl(episodeId)
              .then(result => {
                if (result && result.episode_page_url && selectedEmissionDetails.value?.episode) {
                  selectedEmissionDetails.value.episode.episode_page_url = result.episode_page_url;
                }
              })
              .catch(urlError => {
                console.warn('Impossible de récupérer l\'URL RadioFrance:', urlError);
                // Ne pas bloquer l'affichage si échec de récupération URL
              });
          }
        }

        // Charger les avis structurés en arrière-plan (extraction auto si nécessaire)
        loadAvisForEmission(data.emission.id);
      } catch (error) {
        console.error('Erreur chargement émission par date:', error);
        detailsError.value = error.message || 'Erreur lors du chargement de l\'émission';
      } finally {
        detailsLoading.value = false;
      }
    };

    /**
     * Transforme les émissions en format épisodes pour EpisodeDropdown
     */
    const emissionsAsEpisodes = computed(() => {
      return emissions.value.map(emission => ({
        id: emission.id,  // EpisodeDropdown attend 'id', pas '_id'
        _id: emission.id,
        titre: emission.episode?.titre || 'Sans titre',
        date: emission.date,
        numero_emission: emission.episode?.numero_emission || null,
        // Badge status pour pastilles (4 états)
        badge_status: emission.badge_status || null,
        // Désactiver les autres pastilles (LivresAuteurs)
        has_cached_books: null,
        has_incomplete_books: null,
      }));
    });

    /**
     * Compteurs par badge status
     */
    const emissionsPerfectCount = computed(() => {
      return emissions.value.filter(e => e.badge_status === 'perfect').length;
    });

    const emissionsCountMismatchCount = computed(() => {
      return emissions.value.filter(e => e.badge_status === 'count_mismatch').length;
    });

    const emissionsUnmatchedCount = computed(() => {
      return emissions.value.filter(e => e.badge_status === 'unmatched').length;
    });

    const emissionsNoAvisCount = computed(() => {
      return emissions.value.filter(e => e.badge_status === 'no_avis').length;
    });

    /**
     * Vérifie si l'émission sélectionnée a un badge "perfect" (🟢)
     * Pour masquer les sections quand tout est parfait
     */
    const isSelectedEmissionPerfect = computed(() => {
      if (!selectedEmissionId.value) return false;
      const selectedEmission = emissions.value.find(e => e.id === selectedEmissionId.value);
      return selectedEmission?.badge_status === 'perfect';
    });

    /**
     * Navigation : émission précédente
     */
    const hasPreviousEpisode = computed(() => {
      if (!selectedEmissionId.value || emissions.value.length === 0) return false;
      const currentIndex = emissions.value.findIndex(e => e.id === selectedEmissionId.value);
      return currentIndex < emissions.value.length - 1 && currentIndex !== -1;
    });

    /**
     * Navigation : émission suivante
     */
    const hasNextEpisode = computed(() => {
      if (!selectedEmissionId.value || emissions.value.length === 0) return false;
      const currentIndex = emissions.value.findIndex(e => e.id === selectedEmissionId.value);
      return currentIndex > 0;
    });

    /**
     * Sélectionner l'émission précédente
     */
    const selectPreviousEpisode = async () => {
      if (!hasPreviousEpisode.value || isChangingEpisode.value) return;

      isChangingEpisode.value = true;
      try {
        const currentIndex = emissions.value.findIndex(e => e.id === selectedEmissionId.value);
        const previousEmission = emissions.value[currentIndex + 1];
        const dateStr = formatDateForUrl(previousEmission.date);
        await router.push(`/emissions/${dateStr}`);
      } finally {
        isChangingEpisode.value = false;
      }
    };

    /**
     * Sélectionner l'émission suivante
     */
    const selectNextEpisode = async () => {
      if (!hasNextEpisode.value || isChangingEpisode.value) return;

      isChangingEpisode.value = true;
      try {
        const currentIndex = emissions.value.findIndex(e => e.id === selectedEmissionId.value);
        const nextEmission = emissions.value[currentIndex - 1];
        const dateStr = formatDateForUrl(nextEmission.date);
        await router.push(`/emissions/${dateStr}`);
      } finally {
        isChangingEpisode.value = false;
      }
    };

    /**
     * Gère le changement d'émission via le dropdown
     */
    const onEmissionChange = async (emissionId) => {
      if (isChangingEpisode.value) return;

      isChangingEpisode.value = true;
      try {
        const emission = emissions.value.find(e => e.id === emissionId);
        if (emission) {
          const dateStr = formatDateForUrl(emission.date);
          await router.push(`/emissions/${dateStr}`);
        }
      } finally {
        isChangingEpisode.value = false;
      }
    };

    /**
     * Formate une date ISO en format français
     */
    const formatDate = (dateStr) => {
      if (!dateStr) return 'Date inconnue';
      const date = new Date(dateStr);
      return date.toLocaleDateString('fr-FR', {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric'
      });
    };

    /**
     * Formate une date ISO en format compact (ex: "24/08/25")
     */
    const formatDateCompact = (dateStr) => {
      if (!dateStr) return '';
      const date = new Date(dateStr);
      const day = String(date.getDate()).padStart(2, '0');
      const month = String(date.getMonth() + 1).padStart(2, '0');
      const year = String(date.getFullYear()).slice(-2);
      return `${day}/${month}/${year}`;
    };

    /**
     * Formate une durée en secondes en format lisible
     */
    const formatDuration = (seconds) => {
      if (!seconds) return 'Durée inconnue';
      const minutes = Math.floor(seconds / 60);
      return `${minutes} minutes`;
    };

    /**
     * Formate une durée en secondes en format compact (ex: "50'")
     */
    const formatDurationCompact = (seconds) => {
      if (!seconds) return '';
      const minutes = Math.floor(seconds / 60);
      return `${minutes}'`;
    };

    /**
     * Formate une date ISO en format YYYYMMDD pour l'URL
     */
    const formatDateForUrl = (dateStr) => {
      if (!dateStr) return '';
      const date = new Date(dateStr);
      const year = date.getFullYear();
      const month = String(date.getMonth() + 1).padStart(2, '0');
      const day = String(date.getDate()).padStart(2, '0');
      return `${year}${month}${day}`;
    };

    /**
     * Convertit le markdown en HTML
     */
    const renderMarkdown = (markdown) => {
      if (!markdown) return '';
      return marked(markdown);
    };

    /**
     * Gestion de la navigation au clavier
     * Flèche gauche (←) = Précédent (plus ancien)
     * Flèche droite (→) = Suivant (plus récent)
     */
    const handleKeydown = (event) => {
      if (event.key === 'ArrowLeft' && hasPreviousEpisode.value) {
        selectPreviousEpisode();
      } else if (event.key === 'ArrowRight' && hasNextEpisode.value) {
        selectNextEpisode();
      }
    };

    /**
     * Initialisation au montage du composant
     */
    onMounted(async () => {
      const dateParam = route.params.date;

      if (dateParam) {
        // Route avec date : charger émission spécifique
        await loadAllEmissions(); // Charger liste pour navigation
        await loadEmissionByDate(dateParam);
      } else {
        // Route sans date : charger liste et rediriger vers plus récent
        await loadAllEmissions();
      }

      // Ajouter listener clavier
      document.addEventListener('keydown', handleKeydown);
    });

    /**
     * Nettoyage au démontage du composant
     */
    onBeforeUnmount(() => {
      document.removeEventListener('keydown', handleKeydown);
    });

    /**
     * Surveiller les changements de route pour recharger les détails
     */
    watch(() => route.params.date, async (newDate) => {
      if (newDate) {
        await loadEmissionByDate(newDate);
      }
    });

    return {
      emissions,
      emissionsLoading,
      emissionsError,
      selectedEmissionId,
      selectedEmissionDetails,
      detailsLoading,
      detailsError,
      showEpisodeDetails,
      showBooksDetails,
      showCritiquesDetails,
      emissionsAsEpisodes,
      // Compteurs de badges
      emissionsPerfectCount,
      emissionsCountMismatchCount,
      emissionsUnmatchedCount,
      emissionsNoAvisCount,
      isSelectedEmissionPerfect,
      hasPreviousEpisode,
      hasNextEpisode,
      loadAllEmissions,
      selectPreviousEpisode,
      selectNextEpisode,
      onEmissionChange,
      formatDate,
      formatDateCompact,
      formatDuration,
      formatDurationCompact,
      renderMarkdown,
      // Avis structurés
      avis,
      avisLoading,
      avisError,
      avisExtracting,
      avisMatchingStats,
      reextractAvis,
    };
  }
};
</script>

<style scoped>
.emissions {
  min-height: 100vh;
  background-color: #f5f5f5;
}

main {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 1rem 2rem;
}

/* Section sélecteur */
.episode-selector-section {
  margin-bottom: 2rem;
}

/* Accordéon détails épisode */
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

/* Container pour logo + infos épisode */
.episode-info-container {
  display: flex;
  gap: 1.5rem;
  align-items: center;
}

/* Logo RadioFrance cliquable */
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

.card {
  background: white;
  border-radius: 8px;
  padding: 1.5rem;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  margin-bottom: 1.5rem;
}

/* États de chargement et erreurs */
.loading {
  text-align: center;
  padding: 2rem;
  color: #666;
}

.alert {
  padding: 1rem;
  border-radius: 4px;
  margin-bottom: 1rem;
}

.alert-error {
  background-color: #fee;
  color: #c33;
  border: 1px solid #fcc;
}

.alert-info {
  background-color: #e7f3ff;
  color: #0066cc;
  border: 1px solid #b3d9ff;
}

/* Formulaire */
.form-group {
  margin-bottom: 1rem;
}

.form-label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 600;
  color: #333;
}

/* Tooltip pour les compteurs de badges */
.badge-counters-tooltip {
  cursor: help;
  border-bottom: 1px dotted #666;
  white-space: pre-line;
}

.badge-counters-tooltip:hover {
  border-bottom-color: #0066cc;
}

.episode-select-wrapper {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.nav-episode-btn {
  padding: 0.5rem 1rem;
  background: #0066cc;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
  white-space: nowrap;
  transition: background-color 0.2s;
}

.nav-episode-btn:hover:not(:disabled) {
  background: #0052a3;
}

.nav-episode-btn:disabled {
  background: #ccc;
  cursor: not-allowed;
  opacity: 0.6;
}

.btn {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
  transition: background-color 0.2s;
}

.btn-primary {
  background: #0066cc;
  color: white;
}

.btn-primary:hover {
  background: #0052a3;
}

/* Détails de l'émission */
.emission-details-section {
  margin-top: 2rem;
}

.emission-info {
  border-bottom: 1px solid #e0e0e0;
  padding-bottom: 1rem;
  margin-bottom: 1.5rem;
}

.emission-info.no-border {
  border-bottom: none;
  margin-bottom: 0.5rem;
}

.emission-info h2 {
  margin: 0;
  color: #333;
  font-size: 1.5rem;
  line-height: 1.4;
}

.episode-date-prefix {
  color: #666;
  font-size: 0.9rem;
  font-weight: normal;
}

.episode-duration-suffix {
  color: #666;
  font-size: 0.9rem;
  font-weight: normal;
  margin-left: 0.3rem;
}

/* Old emission-date, emission-duree, emission-link styles removed (no longer used) */

.emission-link a {
  color: #0066cc;
  text-decoration: none;
}

.emission-link a:hover {
  text-decoration: underline;
}

/* Listes */
.books-list,
.critiques-list {
  margin-bottom: 1.5rem;
}

.books-list h3,
.critiques-list h3,
.summary-section h3 {
  margin: 0 0 1rem 0;
  color: #333;
  font-size: 1.2rem;
}

.books-list ul,
.critiques-list ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.books-list li,
.critiques-list li {
  padding: 0.75rem;
  border-bottom: 1px solid #f0f0f0;
}

.books-list li:last-child,
.critiques-list li:last-child {
  border-bottom: none;
}

.author-link,
.book-link {
  color: #0066cc;
  text-decoration: none;
}

.author-link:hover,
.book-link:hover {
  text-decoration: underline;
}

.animateur-badge {
  display: inline-block;
  margin-left: 0.5rem;
  padding: 0.2rem 0.5rem;
  background: #ffd700;
  color: #333;
  border-radius: 3px;
  font-size: 0.8rem;
  font-weight: 600;
}

/* Section summary markdown */
.summary-section {
  margin-top: 1.5rem;
  padding-top: 1.5rem;
  border-top: 1px solid #e0e0e0;
}

.markdown-content {
  line-height: 1.6;
  color: #333;
}

.markdown-content :deep(h1),
.markdown-content :deep(h2),
.markdown-content :deep(h3) {
  margin-top: 1.5rem;
  margin-bottom: 0.75rem;
  color: #333;
}

.markdown-content :deep(p) {
  margin-bottom: 1rem;
}

.markdown-content :deep(ul),
.markdown-content :deep(ol) {
  margin-bottom: 1rem;
  padding-left: 1.5rem;
}

.markdown-content :deep(strong) {
  font-weight: 600;
  color: #000;
}

/* Section avis structurés */
.avis-section-container {
  margin-top: 1.5rem;
  padding-top: 1.5rem;
  border-top: 1px solid #e0e0e0;
}

.avis-section-container.no-top-border {
  border-top: none;
  margin-top: 0.5rem;
  padding-top: 0;
}

.avis-section-container h3 {
  margin: 0 0 1rem 0;
  color: #333;
  font-size: 1.2rem;
}

/* Boutons d'action avis (style GenerationAvisCritiques) */
.btn-extract {
  background: #4caf50;
  color: white;
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.95rem;
  font-weight: 500;
  transition: background 0.2s;
  white-space: nowrap;
}

.btn-extract:hover:not(:disabled) {
  background: #43a047;
}

.btn-extract:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.btn-reextract {
  background: #ff9800;
  color: white;
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.95rem;
  font-weight: 500;
  transition: background 0.2s;
  white-space: nowrap;
}

.btn-reextract:hover:not(:disabled) {
  background: #f57c00;
}

.btn-reextract:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.loading-small {
  padding: 1rem;
  text-align: center;
  color: #666;
  font-style: italic;
}

.alert {
  padding: 1rem;
  border-radius: 4px;
  margin-bottom: 1rem;
}

.alert-warning {
  background: #fff3cd;
  color: #856404;
  border: 1px solid #ffeeba;
}

.summary-fallback {
  margin-top: 1rem;
}

.fallback-notice {
  padding: 0.5rem 1rem;
  background: #f8f9fa;
  border-left: 3px solid #6c757d;
  color: #6c757d;
  font-size: 0.9rem;
  margin-bottom: 1rem;
}

/* Section debug summary markdown (phase de test) */
.summary-debug {
  margin-top: 2rem;
  border: 1px dashed #ccc;
  border-radius: 4px;
  background: #fafafa;
}

.summary-debug-toggle {
  padding: 0.75rem 1rem;
  cursor: pointer;
  color: #666;
  font-size: 0.9rem;
  font-style: italic;
}

.summary-debug-toggle:hover {
  background: #f0f0f0;
}

.summary-debug-content {
  padding: 1rem;
  border-top: 1px dashed #ccc;
  background: white;
  max-height: 600px;
  overflow-y: auto;
}

/* Stats de matching */
.matching-stats {
  background: #fff8e6;
  border: 1px solid #ffc107;
  border-radius: 6px;
  padding: 0.75rem 1rem;
  margin-bottom: 1rem;
}

.stats-header {
  margin-bottom: 0.5rem;
}

.stats-warning {
  color: #856404;
  font-weight: 600;
}

.stats-details {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
  font-size: 0.9rem;
}

.stat-item {
  padding: 0.25rem 0.5rem;
  border-radius: 3px;
}

.stat-phase1 {
  background: #d4edda;
  color: #155724;
}

.stat-phase2 {
  background: #cce5ff;
  color: #004085;
}

.stat-phase3 {
  background: #fff3cd;
  color: #856404;
}

.stat-unmatched {
  background: #f8d7da;
  color: #721c24;
}

/* Sections repliables (livres, critiques) */
.collapsible-section {
  margin-bottom: 1rem;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  background: #f9fafb;
  overflow: hidden;
}

.collapsible-toggle {
  width: 100%;
  padding: 0.75rem 1rem;
  background: #f3f4f6;
  border: none;
  cursor: pointer;
  font-weight: 600;
  font-size: 1rem;
  color: #374151;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  transition: background-color 0.2s;
}

.collapsible-toggle:hover {
  background: #e5e7eb;
}

.collapsible-toggle .toggle-icon {
  font-size: 0.75rem;
  color: #6b7280;
}

.collapsible-content {
  padding: 0.5rem 1rem 1rem;
  margin: 0;
  border-top: 1px solid #e5e7eb;
  background: white;
  list-style: none;
}

.collapsible-content li {
  padding: 0.25rem 0;
}
</style>
