/**
 * Tests simplifiés pour la page Livres/Auteurs
 * Focus sur la structure de base sans interactions complexes
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount } from '@vue/test-utils';
import { createRouter, createWebHistory } from 'vue-router';
import LivresAuteurs from '../../src/views/LivresAuteurs.vue';
import { livresAuteursService, episodeService } from '../../src/services/api.js';
import BiblioValidationService from '../../src/services/BiblioValidationService.js';

// Mock du service API
vi.mock('../../src/services/api.js', () => ({
  livresAuteursService: {
    getLivresAuteurs: vi.fn(),
    getEpisodesWithReviews: vi.fn(),
    // Nouveaux endpoints pour Issue #66
    getCollectionsStatistics: vi.fn(),
    autoProcessVerifiedBooks: vi.fn(),
    autoProcessVerified: vi.fn(),
    getBooksByValidationStatus: vi.fn(),
    validateSuggestion: vi.fn(),
    addManualBook: vi.fn(),
    getAllAuthors: vi.fn(),
    getAllBooks: vi.fn(),
    setValidationResults: vi.fn(),
    deleteCacheByEpisode: vi.fn(),
  },
  episodeService: {
    getAllEpisodes: vi.fn(),
    getEpisodeById: vi.fn(),
    updateEpisodeDescription: vi.fn(),
    updateEpisodeTitle: vi.fn(),
  },
  statisticsService: {
    getStatistics: vi.fn(),
  },
  babelioService: {
    verifyAuthor: vi.fn(),
    verifyBook: vi.fn(),
    verifyPublisher: vi.fn(),
  },
  fuzzySearchService: {
    searchEpisode: vi.fn()
  }
}));

describe('LivresAuteurs - Tests simplifiés', () => {
  let wrapper;
  let router;

  // TDD: Test pour auto-processing automatique au chargement des livres
  describe('Auto-processing automatique', () => {
    it('should automatically process verified books in background after loading books for episode', async () => {
      const mockBooks = [
        {
          episode_oid: 'test-episode-id',
          auteur: 'Maria Pourchet',
          titre: 'Tressaillir',
          editeur: 'Stock',
          babelio_verification_status: 'verified',
          programme: true
        }
      ];

      // Add missing essential mocks that all other tests have
      episodeService.getEpisodeById.mockResolvedValue(mockEpisode);
      livresAuteursService.getEpisodesWithReviews.mockResolvedValue(mockEpisodesWithReviews);
      livresAuteursService.getLivresAuteurs.mockResolvedValue(mockBooks);
      livresAuteursService.autoProcessVerifiedBooks.mockResolvedValue({
        success: true,
        processed_count: 1,
        created_authors: 1,
        created_books: 1
      });

      const router = createRouter({
        history: createWebHistory(),
        routes: [
          { path: '/', component: LivresAuteurs },
          { path: '/livres-auteurs', component: LivresAuteurs }
        ]
      });

      const wrapper = mount(LivresAuteurs, {
        global: {
          plugins: [router]
        }
      });

      // Simuler la sélection d'un épisode
      wrapper.vm.selectedEpisodeId = 'test-episode-id';

      // Appeler loadBooksForEpisode
      await wrapper.vm.loadBooksForEpisode();

      // L'auto-processing se lance en arrière-plan, attendre qu'il s'exécute
      await new Promise(resolve => setTimeout(resolve, 10));

      // Vérifier que autoProcessVerifiedBooks a été appelé automatiquement en arrière-plan
      expect(livresAuteursService.autoProcessVerifiedBooks).toHaveBeenCalled();
    });
  });

  const mockEpisodesWithReviews = [
    {
      _id: { $oid: '6865f995a1418e3d7c63d076' }, // pragma: allowlist secret
      titre: 'Les critiques littéraires du Masque & la Plume depuis le festival "Quai du Polar" à Lyon',
      date: '29 juin 2025',
      review_count: 4
    }
  ];

  const mockEpisode = {
    id: '6865f995a1418e3d7c63d076', // pragma: allowlist secret
    titre: 'Les critiques littéraires du Masque & la Plume depuis le festival "Quai du Polar" à Lyon',
    date: '29 juin 2025',
    review_count: 4
  };

  const mockBooks = [
    {
      episode_oid: '64f1234567890abcdef12345', // pragma: allowlist secret
      auteur: 'Auteur Test',
      titre: 'Livre Test',
      editeur: 'Éditeur Test',
      validation_status: null,
      suggested_author: null,
      suggested_title: null,
      programme: false,
      coup_de_coeur: false
    }
  ];

  beforeEach(async () => {
    vi.clearAllMocks();

    // Nettoyer le cache BiblioValidationService pour éviter les accumulations mémoire entre tests
    BiblioValidationService._extractedBooksCache?.clear();

    // Créer un router de test
    router = createRouter({
      history: createWebHistory(),
      routes: [
        { path: '/', component: { template: '<div>Dashboard</div>' } },
        { path: '/livres-auteurs', component: LivresAuteurs }
      ]
    });

    await router.push('/livres-auteurs');
  });

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount();
    }
  });

  it('charge la page sans erreur et affiche les éléments de base', async () => {
    livresAuteursService.getEpisodesWithReviews.mockResolvedValue(mockEpisodesWithReviews);

    wrapper = mount(LivresAuteurs, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();

    // Vérifier que la page se charge sans erreur
    expect(wrapper.exists()).toBe(true);
    expect(wrapper.text()).toContain('Livres et Auteurs');
  });

  it('affiche le sélecteur d\'épisodes après chargement', async () => {
    livresAuteursService.getEpisodesWithReviews.mockResolvedValue(mockEpisodesWithReviews);

    wrapper = mount(LivresAuteurs, {
      global: {
        plugins: [router]
      }
    });

    // Attendre que le chargement se termine
    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 50));

    // Vérifier que le sélecteur est présent
    expect(wrapper.text()).toContain('Choisir un épisode avec avis critiques');
  });

  it('affiche le message d\'aide initial après chargement', async () => {
    livresAuteursService.getEpisodesWithReviews.mockResolvedValue(mockEpisodesWithReviews);

    wrapper = mount(LivresAuteurs, {
      global: {
        plugins: [router]
      }
    });

    // Attendre que le chargement se termine
    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 50));

    // Vérifier que le message d'aide est présent
    expect(wrapper.text()).toContain('Sélectionnez un épisode pour commencer');
  });

  it('affiche la colonne Validation Biblio dans le tableau', async () => {
    const mockBooks = [
      {
        episode_oid: '6865f995a1418e3d7c63d076', // pragma: allowlist secret
        auteur: 'Michel Houellebecq',
        titre: 'Les Particules élémentaires',
        editeur: 'Flammarion'
      }
    ];

    livresAuteursService.getEpisodesWithReviews.mockResolvedValue(mockEpisodesWithReviews);
    livresAuteursService.getLivresAuteurs.mockResolvedValue(mockBooks);

    wrapper = mount(LivresAuteurs, {
      global: {
        plugins: [router]
      }
    });

    // Attendre que le chargement se termine
    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 50));

    // Sélectionner un épisode
    wrapper.vm.selectedEpisodeId = '6865f995a1418e3d7c63d076'; // pragma: allowlist secret
    await wrapper.vm.loadBooksForEpisode();
    await wrapper.vm.$nextTick();

    // Vérifier que la colonne Validation Biblio est présente
    expect(wrapper.text()).toContain('Validation Biblio');

    // Vérifier qu'il y a des composants BiblioValidationCell
    const validationCells = wrapper.findAllComponents({ name: 'BiblioValidationCell' });
    expect(validationCells.length).toBe(1);

    // Vérifier que le composant reçoit les bonnes props
    expect(validationCells[0].props()).toEqual({
      author: 'Michel Houellebecq',
      title: 'Les Particules élémentaires',
      publisher: 'Flammarion',
      episodeId: '6865f995a1418e3d7c63d076', // pragma: allowlist secret
      bookKey: '6865f995a1418e3d7c63d076-Michel Houellebecq-Les Particules élémentaires'
    });
  });

  it("affiche la petite colonne d'état (programme / coup de coeur) et permet de trier", async () => {
    const mockBooks = [
      {
        episode_oid: '6865f995a1418e3d7c63d076', // pragma: allowlist secret
        auteur: 'Michel Houellebecq',
        titre: 'Les Particules élémentaires',
        editeur: 'Flammarion',
        programme: true,
        coup_de_coeur: false
      }
    ];

    livresAuteursService.getEpisodesWithReviews.mockResolvedValue(mockEpisodesWithReviews);
    livresAuteursService.getLivresAuteurs.mockResolvedValue(mockBooks);

    wrapper = mount(LivresAuteurs, {
      global: {
        plugins: [router]
      }
    });

    // Attendre que le chargement se termine
    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 50));

    // Sélectionner un épisode
  wrapper.vm.selectedEpisodeId = '6865f995a1418e3d7c63d076'; // pragma: allowlist secret
    await wrapper.vm.loadBooksForEpisode();
    await wrapper.vm.$nextTick();

  // Vérifier que l'en-tête de colonne d'état est présent et accessible
  const statusHeader = wrapper.find('[data-testid="status-header"]');
  expect(statusHeader.exists()).toBe(true);
  expect(statusHeader.attributes('aria-label')).toBe('Programme ou Coup de coeur');

  // Vérifier que la cellule d'état contient une icône (programme -> 🎯)
  const statusCell = wrapper.find('[data-testid^="status-cell-"]');
  expect(statusCell.exists()).toBe(true);
  // The UI now uses SVG icons for status; ensure the programme icon is present
  const programmeIcon = statusCell.find('.status-icon.programme');
  const programmeSvg = statusCell.find('svg[aria-label="Programme"]');
  expect(programmeIcon.exists() || programmeSvg.exists()).toBe(true);

  // Cliquer sur l'en-tête active le tri par 'status'
  await statusHeader.trigger('click');
  expect(wrapper.vm.currentSortField).toBe('status');
  });

  // ========== NOUVEAUX TESTS TDD POUR ISSUE #66 ==========

  describe('Collections Management Dashboard (Issue #66)', () => {
    it('ne doit PAS afficher le dashboard global des statistiques collections', async () => {
      livresAuteursService.getEpisodesWithReviews.mockResolvedValue(mockEpisodesWithReviews);

      wrapper = mount(LivresAuteurs, {
        global: {
          plugins: [router]
        }
      });

      await wrapper.vm.$nextTick();

      // Vérifier que le dashboard global n'est PAS affiché
      // Note: Les statistiques doivent être sur la page Dashboard principale
      expect(wrapper.text()).not.toContain('Épisodes non traités :');
      expect(wrapper.text()).not.toContain('Couples en base :');
      expect(wrapper.text()).not.toContain('Verified pas en base :');
      expect(wrapper.text()).not.toContain('Suggested pas en base :');
      expect(wrapper.text()).not.toContain('Not found pas en base :');
    });

    it('ne doit PAS afficher le bouton de traitement automatique global', async () => {
      livresAuteursService.getEpisodesWithReviews.mockResolvedValue(mockEpisodesWithReviews);

      wrapper = mount(LivresAuteurs, {
        global: {
          plugins: [router]
        }
      });

      await wrapper.vm.$nextTick();

      // Vérifier que le bouton de traitement automatique global n'est PAS présent
      // Note: Le traitement doit être fait ligne par ligne selon le statut de validation
      const autoProcessButton = wrapper.find('[data-testid="auto-process-button"]');
      expect(autoProcessButton.exists()).toBe(false);
    });

    it('ne doit PAS permettre le traitement automatique global', async () => {
      livresAuteursService.getEpisodesWithReviews.mockResolvedValue(mockEpisodesWithReviews);

      wrapper = mount(LivresAuteurs, {
        global: {
          plugins: [router]
        }
      });

      await wrapper.vm.$nextTick();

      // Vérifier qu'il n'y a pas de bouton de traitement automatique global
      const autoProcessButton = wrapper.find('[data-testid="auto-process-button"]');
      expect(autoProcessButton.exists()).toBe(false);

      // Vérifier qu'il n'y a pas de résultats de traitement global affichés
      expect(wrapper.text()).not.toContain('livres traités');
      expect(wrapper.text()).not.toContain('auteurs créés');
    });
  });

  // Note: Les tests pour validation manuelle, ajout manuel et gestion des collections
  // sont supprimés car ces fonctionnalités doivent être implémentées ligne par ligne
  // dans le tableau des livres, et non pas comme un dashboard global séparé.

  // ========== NOUVEAUX TESTS TDD POUR TÂCHE 2: BOUTONS PAR LIGNE ==========

  describe('Per-Line Action Buttons (Tâche 2)', () => {
    it('affiche un bouton "Traiter automatiquement" pour les livres verified', async () => {
      const mockBooksWithVerified = [
        {
          episode_oid: '64f1234567890abcdef12345', // pragma: allowlist secret // pragma: allowlist secret
          auteur: 'Michel Houellebecq',
          titre: 'Les Particules élémentaires',
          editeur: 'Flammarion',
          validation_status: 'verified',
          suggested_author: 'Michel Houellebecq',
          suggested_title: 'Les Particules élémentaires',
          programme: false,
          coup_de_coeur: false
        }
      ];

      episodeService.getEpisodeById.mockResolvedValue(mockEpisode);
      livresAuteursService.getEpisodesWithReviews.mockResolvedValue(mockEpisodesWithReviews);
      livresAuteursService.getLivresAuteurs.mockResolvedValue(mockBooksWithVerified);

      wrapper = mount(LivresAuteurs, {
        global: {
          plugins: [router]
        }
      });

      await wrapper.vm.$nextTick();
      wrapper.vm.selectedEpisodeId = mockEpisode.id;
      await wrapper.vm.loadBooksForEpisode();
      await wrapper.vm.$nextTick();

      // Définir le statut de validation pour qu'un bouton s'affiche
      const book = wrapper.vm.books[0]; // Premier livre
      const bookKey = wrapper.vm.getBookKey(book);
      wrapper.vm.validationStatuses.set(bookKey, 'verified');
      await wrapper.vm.$nextTick();

      // Vérifier qu'un bouton "Traiter automatiquement" est affiché pour le livre verified
      const autoProcessButton = wrapper.find('[data-testid="auto-process-verified-btn"]');
      expect(autoProcessButton.exists()).toBe(true);
      expect(autoProcessButton.text()).toContain('Traiter');
    });

    it('affiche un bouton "Valider suggestion" pour les livres suggested', async () => {
      const mockBooksWithSuggested = [
        {
          episode_oid: '64f1234567890abcdef12345', // pragma: allowlist secret // pragma: allowlist secret
          auteur: 'Michel Houllebeck',
          titre: 'Les Particules élémentaires',
          editeur: 'Flammarion',
          validation_status: 'suggested',
          suggested_author: 'Michel Houellebecq',
          suggested_title: 'Les Particules élémentaires',
          programme: false,
          coup_de_coeur: false
        }
      ];

      episodeService.getEpisodeById.mockResolvedValue(mockEpisode);
      livresAuteursService.getEpisodesWithReviews.mockResolvedValue(mockEpisodesWithReviews);
      livresAuteursService.getLivresAuteurs.mockResolvedValue(mockBooksWithSuggested);

      wrapper = mount(LivresAuteurs, {
        global: {
          plugins: [router]
        }
      });

      await wrapper.vm.$nextTick();
      wrapper.vm.selectedEpisodeId = mockEpisode.id;
      await wrapper.vm.loadBooksForEpisode();
      await wrapper.vm.$nextTick();

      // Définir le statut de validation 'corrected' pour qu'un bouton s'affiche
      const book = wrapper.vm.books[0]; // Premier livre
      const bookKey = wrapper.vm.getBookKey(book);
      wrapper.vm.validationStatuses.set(bookKey, 'corrected');
      await wrapper.vm.$nextTick();

      // Vérifier qu'un bouton "Valider suggestion" est affiché pour le livre suggested
      const validateButton = wrapper.find('[data-testid="validate-suggestion-btn"]');
      expect(validateButton.exists()).toBe(true);
      expect(validateButton.text()).toContain('Valider');
    });

    it('affiche un bouton "Ajouter manuellement" pour les livres not_found', async () => {
      const mockBooksWithNotFound = [
        {
          episode_oid: '64f1234567890abcdef12345', // pragma: allowlist secret // pragma: allowlist secret
          auteur: 'Auteur Inconnu',
          titre: 'Livre Introuvable',
          editeur: 'Éditeur Inconnu',
          validation_status: 'not_found',
          suggested_author: null,
          suggested_title: null,
          programme: false,
          coup_de_coeur: false
        }
      ];

      episodeService.getEpisodeById.mockResolvedValue(mockEpisode);
      livresAuteursService.getEpisodesWithReviews.mockResolvedValue(mockEpisodesWithReviews);
      livresAuteursService.getLivresAuteurs.mockResolvedValue(mockBooksWithNotFound);

      wrapper = mount(LivresAuteurs, {
        global: {
          plugins: [router]
        }
      });

      await wrapper.vm.$nextTick();
      wrapper.vm.selectedEpisodeId = mockEpisode.id;
      await wrapper.vm.loadBooksForEpisode();
      await wrapper.vm.$nextTick();

      // Définir le statut de validation 'not_found' pour qu'un bouton s'affiche
      const book = wrapper.vm.books[0]; // Premier livre
      const bookKey = wrapper.vm.getBookKey(book);
      wrapper.vm.validationStatuses.set(bookKey, 'not_found');
      await wrapper.vm.$nextTick();

      // Vérifier qu'un bouton "Ajouter manuellement" est affiché pour le livre not_found
      const addManualButton = wrapper.find('[data-testid="manual-add-btn"]');
      expect(addManualButton.exists()).toBe(true);
      expect(addManualButton.text()).toContain('Ajouter');
    });

    it('n\'affiche aucun bouton pour les livres sans validation_status', async () => {
      const mockBooksWithoutStatus = [
        {
          episode_oid: '64f1234567890abcdef12345', // pragma: allowlist secret // pragma: allowlist secret
          auteur: 'Auteur Normal',
          titre: 'Livre Normal',
          editeur: 'Éditeur Normal',
          validation_status: null,
          suggested_author: null,
          suggested_title: null,
          programme: false,
          coup_de_coeur: false
        }
      ];

      episodeService.getEpisodeById.mockResolvedValue(mockEpisode);
      livresAuteursService.getEpisodesWithReviews.mockResolvedValue(mockEpisodesWithReviews);
      livresAuteursService.getLivresAuteurs.mockResolvedValue(mockBooksWithoutStatus);

      wrapper = mount(LivresAuteurs, {
        global: {
          plugins: [router]
        }
      });

      await wrapper.vm.$nextTick();
      wrapper.vm.selectedEpisodeId = mockEpisode.id;
      await wrapper.vm.loadBooksForEpisode();
      await wrapper.vm.$nextTick();

      // Vérifier qu'aucun bouton d'action n'est affiché pour les livres sans statut
      expect(wrapper.find('[data-testid="auto-process-verified-btn"]').exists()).toBe(false);
      expect(wrapper.find('[data-testid="validate-suggestion-btn"]').exists()).toBe(false);
      expect(wrapper.find('[data-testid="manual-add-btn"]').exists()).toBe(false);
    });

    it('ajoute une colonne "Actions" dans l\'en-tête du tableau', async () => {
      episodeService.getEpisodeById.mockResolvedValue(mockEpisode);
      livresAuteursService.getEpisodesWithReviews.mockResolvedValue(mockEpisodesWithReviews);
      livresAuteursService.getLivresAuteurs.mockResolvedValue(mockBooks);

      wrapper = mount(LivresAuteurs, {
        global: {
          plugins: [router]
        }
      });

      await wrapper.vm.$nextTick();
      wrapper.vm.selectedEpisodeId = mockEpisode.id;
      await wrapper.vm.loadBooksForEpisode();
      await wrapper.vm.$nextTick();

      // Vérifier qu'une colonne "Actions" est présente dans l'en-tête
      const actionsHeader = wrapper.find('[data-testid="actions-header"]');
      expect(actionsHeader.exists()).toBe(true);
      expect(actionsHeader.text()).toContain('Actions');
    });
  });

  // ========== TESTS TDD POUR LA COMMUNICATION AVEC BIBLIOVALIADATIONCELL ==========

  describe('BiblioValidationCell Communication (Tâche 4)', () => {
    const mockEpisode = {
      _id: '64f1234567890abcdef12345',
      titre: 'Test Episode'
    };

    const mockBooksWithValidation = [
      {
        episode_oid: '64f1234567890abcdef12345', // pragma: allowlist secret
        auteur: 'Maria Pourchet',
        titre: 'Feu',
        editeur: 'Gallimard',
        programme: false,
        coup_de_coeur: false
      },
      {
        episode_oid: '64f1234567890abcdef12345', // pragma: allowlist secret
        auteur: 'Michel Houllebeck',
        titre: 'Les Particules élémentaires',
        editeur: 'Flammarion',
        programme: false,
        coup_de_coeur: false
      },
      {
        episode_oid: '64f1234567890abcdef12345', // pragma: allowlist secret
        auteur: 'Auteur Inconnu',
        titre: 'Livre Introuvable',
        editeur: 'Éditeur Inconnu',
        programme: false,
        coup_de_coeur: false
      }
    ];

    it('affiche le bouton de traitement automatique pour les livres verified', async () => {
      episodeService.getEpisodeById.mockResolvedValue(mockEpisode);
      livresAuteursService.getEpisodesWithReviews.mockResolvedValue(mockEpisodesWithReviews);
      livresAuteursService.getLivresAuteurs.mockResolvedValue(mockBooksWithValidation);

      wrapper = mount(LivresAuteurs, {
        global: {
          plugins: [router]
        }
      });

      await wrapper.vm.$nextTick();

      // Charger l'épisode et les livres
      wrapper.vm.selectedEpisodeId = mockEpisode._id;
      await wrapper.vm.loadBooksForEpisode();
      await wrapper.vm.$nextTick();

      // Simuler un statut "verified" depuis BiblioValidationCell pour le livre réel dans les données
      wrapper.vm.handleValidationStatusChange({
        bookKey: '64f1234567890abcdef12345-Maria Pourchet-Feu',
        status: 'verified',
        suggestion: {
          author: 'Maria Pourchet',
          title: 'Feu',
          publisher: 'Gallimard'
        },
        validationResult: { status: 'verified' }
      });

      await wrapper.vm.$nextTick();

      const autoProcessBtn = wrapper.find('[data-testid="auto-process-verified-btn"]');
      expect(autoProcessBtn.exists()).toBe(true);
      expect(autoProcessBtn.text()).toContain('Traiter');
    });

    it('affiche le bouton de validation pour les livres corrected/suggestion', async () => {
      episodeService.getEpisodeById.mockResolvedValue(mockEpisode);
      livresAuteursService.getEpisodesWithReviews.mockResolvedValue(mockEpisodesWithReviews);
      livresAuteursService.getLivresAuteurs.mockResolvedValue(mockBooksWithValidation);

      wrapper = mount(LivresAuteurs, {
        global: {
          plugins: [router]
        }
      });

      await wrapper.vm.$nextTick();

      // Charger l'épisode et les livres
      wrapper.vm.selectedEpisodeId = mockEpisode._id;
      await wrapper.vm.loadBooksForEpisode();
      await wrapper.vm.$nextTick();

      // Simuler un statut "corrected" depuis BiblioValidationCell
      wrapper.vm.handleValidationStatusChange({
        bookKey: '64f1234567890abcdef12345-Michel Houllebeck-Les Particules élémentaires',
        status: 'corrected',
        suggestion: {
          author: 'Michel Houellebecq',
          title: 'Les Particules élémentaires',
          publisher: 'Flammarion'
        },
        validationResult: { status: 'corrected' }
      });

      await wrapper.vm.$nextTick();

      const validateBtn = wrapper.find('[data-testid="validate-suggestion-btn"]');
      expect(validateBtn.exists()).toBe(true);
      expect(validateBtn.text()).toContain('Valider');
    });

    it('affiche le bouton d\'ajout manuel pour les livres not_found', async () => {
      episodeService.getEpisodeById.mockResolvedValue(mockEpisode);
      livresAuteursService.getEpisodesWithReviews.mockResolvedValue(mockEpisodesWithReviews);
      livresAuteursService.getLivresAuteurs.mockResolvedValue(mockBooksWithValidation);

      wrapper = mount(LivresAuteurs, {
        global: {
          plugins: [router]
        }
      });

      await wrapper.vm.$nextTick();

      // Charger l'épisode et les livres
      wrapper.vm.selectedEpisodeId = mockEpisode._id;
      await wrapper.vm.loadBooksForEpisode();
      await wrapper.vm.$nextTick();

      // Simuler un statut "not_found" depuis BiblioValidationCell
      wrapper.vm.handleValidationStatusChange({
        bookKey: '64f1234567890abcdef12345-Auteur Inconnu-Livre Introuvable',
        status: 'not_found',
        suggestion: null,
        validationResult: { status: 'not_found' }
      });

      await wrapper.vm.$nextTick();

      const manualAddBtn = wrapper.find('[data-testid="manual-add-btn"]');
      expect(manualAddBtn.exists()).toBe(true);
      expect(manualAddBtn.text()).toContain('Ajouter');
    });

    it('traite automatiquement les livres verified', async () => {
      episodeService.getEpisodeById.mockResolvedValue(mockEpisode);
      livresAuteursService.getEpisodesWithReviews.mockResolvedValue(mockEpisodesWithReviews);
      livresAuteursService.getLivresAuteurs.mockResolvedValue(mockBooksWithValidation);
      livresAuteursService.autoProcessVerifiedBooks.mockResolvedValue({
        success: true,
        processed_count: 1
      });

      wrapper = mount(LivresAuteurs, {
        global: {
          plugins: [router]
        }
      });

      await wrapper.vm.$nextTick();

      // Charger l'épisode et les livres
      wrapper.vm.selectedEpisodeId = mockEpisode._id;
      await wrapper.vm.loadBooksForEpisode();
      await wrapper.vm.$nextTick();

      // Simuler un statut "verified" et cliquer sur traitement automatique
      wrapper.vm.handleValidationStatusChange({
        bookKey: '64f1234567890abcdef12345-Maria Pourchet-Feu',
        status: 'verified',
        suggestion: {
          author: 'Maria Pourchet',
          title: 'Feu',
          publisher: 'Gallimard'
        },
        validationResult: { status: 'verified' }
      });

      await wrapper.vm.$nextTick();

      const autoProcessBtn = wrapper.find('[data-testid="auto-process-verified-btn"]');
      expect(autoProcessBtn.exists()).toBe(true);

      // Simuler le clic en appelant directement la méthode avec le vrai livre
      const book = wrapper.vm.books[0];
      await wrapper.vm.autoProcessVerified(book);
      await wrapper.vm.$nextTick();

      // L'endpoint auto-process ne prend aucun paramètre
      expect(livresAuteursService.autoProcessVerifiedBooks).toHaveBeenCalledWith();
    });
  });

  // ========== NOUVEAUX TESTS TDD POUR CORRECTION API FORMATS ==========

  describe('API Format Corrections (TDD)', () => {
    const mockEpisode = {
      _id: '64f1234567890abcdef12345',
      titre: 'Test Episode'
    };

    const mockBooksWithValidation = [
      {
        cache_id: '64f1234567890abcdef11111', // pragma: allowlist secret
        episode_oid: '64f1234567890abcdef12345', // pragma: allowlist secret
        auteur: 'Maria Pourchet',
        titre: 'Feu',
        editeur: 'Gallimard',
        programme: false,
        coup_de_coeur: false
      },
      {
        cache_id: '64f1234567890abcdef22222', // pragma: allowlist secret
        episode_oid: '64f1234567890abcdef12345', // pragma: allowlist secret
        auteur: 'Michel Houllebeck',
        titre: 'Les Particules élémentaires',
        editeur: 'Flammarion',
        programme: false,
        coup_de_coeur: false
      }
    ];

    it('envoie les données au bon format pour validateSuggestion', async () => {
      episodeService.getEpisodeById.mockResolvedValue(mockEpisode);
      livresAuteursService.getEpisodesWithReviews.mockResolvedValue(mockEpisodesWithReviews);
      livresAuteursService.getLivresAuteurs.mockResolvedValue(mockBooksWithValidation);

      const wrapper = mount(LivresAuteurs, {
        global: {
          plugins: [router]
        }
      });
      await wrapper.vm.$nextTick();

      // Charger l'épisode et les livres d'abord
      wrapper.vm.selectedEpisodeId = mockEpisode._id;
      await wrapper.vm.loadBooksForEpisode();
      await wrapper.vm.$nextTick();

      // Simuler un livre avec suggestion
      const book = {
        cache_id: '64f1234567890abcdef11111', // pragma: allowlist secret
        episode_oid: '64f1234567890abcdef12345', // pragma: allowlist secret
        auteur: 'Alain Mabancou',
        titre: 'Ramsés de Paris',
        editeur: 'Seuil'
      };

      // Stocker les données de suggestion
      const bookKey = '64f1234567890abcdef12345-Alain Mabancou-Ramsés de Paris';
      wrapper.vm.validationSuggestions.set(bookKey, {
        author: 'Alain Mabanckou',
        title: 'Ramsés de Paris',
        publisher: 'Seuil'
      });

      wrapper.vm.currentBookToValidate = book;

      // Simuler les données du formulaire de validation
      wrapper.vm.validationForm = {
        author: 'Alain Mabanckou',
        title: 'Ramsés de Paris',
        publisher: 'Seuil'
      };

      // Appeler la validation
      await wrapper.vm.confirmValidation();

      // Vérifier le bon format API
      expect(livresAuteursService.validateSuggestion).toHaveBeenCalledWith({
        cache_id: '64f1234567890abcdef11111', // pragma: allowlist secret
        episode_oid: '64f1234567890abcdef12345', // pragma: allowlist secret
        auteur: 'Alain Mabancou',
        titre: 'Ramsés de Paris',
        editeur: 'Seuil',
        avis_critique_id: undefined,
        user_validated_author: 'Alain Mabanckou',
        user_validated_title: 'Ramsés de Paris',
        user_validated_publisher: 'Seuil'
      });
    });


    it('affiche correctement les suggestions dans le modal', async () => {
      episodeService.getEpisodeById.mockResolvedValue(mockEpisode);
      livresAuteursService.getEpisodesWithReviews.mockResolvedValue(mockEpisodesWithReviews);
      livresAuteursService.getLivresAuteurs.mockResolvedValue(mockBooksWithValidation);

      const wrapper = mount(LivresAuteurs, {
        global: {
          plugins: [router]
        }
      });
      await wrapper.vm.$nextTick();

      // Simuler un livre avec suggestion
      const book = {
        episode_oid: '64f1234567890abcdef12345', // pragma: allowlist secret
        auteur: 'Alain Mabancou',
        titre: 'Ramsés de Paris',
        editeur: 'Seuil'
      };

      // Stocker les données de suggestion
      const bookKey = '64f1234567890abcdef12345-Alain Mabancou-Ramsés de Paris';
      wrapper.vm.validationSuggestions.set(bookKey, {
        author: 'Alain Mabanckou',
        title: 'Ramsés de Paris',
        publisher: 'Seuil'
      });

      wrapper.vm.currentBookToValidate = book;
      wrapper.vm.showValidationModal = true;
      await wrapper.vm.$nextTick();

      // Vérifier que les suggestions sont affichées
      const modal = wrapper.find('[data-testid="validation-modal"]');
      expect(modal.exists()).toBe(true);
      expect(modal.text()).toContain('Alain Mabanckou'); // Suggestion author
      expect(modal.text()).toContain('Ramsés de Paris'); // Suggestion title
    });
  });

// ========== NOUVEAUX TESTS TDD POUR TÂCHE 3: FORMULAIRES MODAUX ==========

  describe('Modal Forms (Tâche 3) - Complex DOM interactions', () => {
    it('ouvre un modal de validation pour les livres suggested', async () => {
      const mockBooksWithSuggested = [
        {
          episode_oid: '64f1234567890abcdef12345', // pragma: allowlist secret // pragma: allowlist secret
          auteur: 'Michel Houllebeck',
          titre: 'Les Particules élémentaires',
          editeur: 'Flammarion',
          validation_status: 'suggested',
          suggested_author: 'Michel Houellebecq',
          suggested_title: 'Les Particules élémentaires',
          programme: false,
          coup_de_coeur: false
        }
      ];

      episodeService.getEpisodeById.mockResolvedValue(mockEpisode);
      livresAuteursService.getEpisodesWithReviews.mockResolvedValue(mockEpisodesWithReviews);
      livresAuteursService.getLivresAuteurs.mockResolvedValue(mockBooksWithSuggested);

      wrapper = mount(LivresAuteurs, {
        global: {
          plugins: [router]
        }
      });

      await wrapper.vm.$nextTick();
      wrapper.vm.selectedEpisodeId = mockEpisode.id;
      await wrapper.vm.loadBooksForEpisode();
      await wrapper.vm.$nextTick();

      // Définir le statut de validation et les suggestions pour afficher le bouton
      const book = wrapper.vm.books[0];
      const bookKey = wrapper.vm.getBookKey(book);
      wrapper.vm.validationStatuses.set(bookKey, 'corrected');

      // Simuler les suggestions Babelio stockées
      wrapper.vm.validationSuggestions.set(bookKey, {
        author: 'Michel Houellebecq',
        title: 'Les Particules élémentaires',
        publisher: 'Flammarion'
      });

      await wrapper.vm.$nextTick();

      // Cliquer sur le bouton de validation
      const validateButton = wrapper.find('[data-testid="validate-suggestion-btn"]');
      expect(validateButton.exists()).toBe(true);
      await validateButton.trigger('click');
      await wrapper.vm.$nextTick();

      // Vérifier qu'un modal s'ouvre pour la validation
      const modal = wrapper.find('[data-testid="validation-modal"]');
      expect(modal.exists()).toBe(true);
      expect(modal.isVisible()).toBe(true);

      // Vérifier que le modal contient les informations du livre
      expect(modal.text()).toContain('Michel Houllebeck');
      expect(modal.text()).toContain('Les Particules élémentaires');
      expect(modal.text()).toContain('Michel Houellebecq');
    });

    it('ouvre un modal d\'ajout manuel pour les livres not_found', async () => {
      const mockBooksWithNotFound = [
        {
          episode_oid: '64f1234567890abcdef12345', // pragma: allowlist secret // pragma: allowlist secret
          auteur: 'Auteur Inconnu',
          titre: 'Livre Introuvable',
          editeur: 'Éditeur Inconnu',
          validation_status: 'not_found',
          suggested_author: null,
          suggested_title: null,
          programme: false,
          coup_de_coeur: false
        }
      ];

      episodeService.getEpisodeById.mockResolvedValue(mockEpisode);
      livresAuteursService.getEpisodesWithReviews.mockResolvedValue(mockEpisodesWithReviews);
      livresAuteursService.getLivresAuteurs.mockResolvedValue(mockBooksWithNotFound);

      wrapper = mount(LivresAuteurs, {
        global: {
          plugins: [router]
        }
      });

      await wrapper.vm.$nextTick();
      wrapper.vm.selectedEpisodeId = mockEpisode.id;
      await wrapper.vm.loadBooksForEpisode();
      await wrapper.vm.$nextTick();

      // Définir le statut not_found pour afficher le bouton
      const book = wrapper.vm.books[0];
      const bookKey = wrapper.vm.getBookKey(book);
      wrapper.vm.validationStatuses.set(bookKey, 'not_found');
      await wrapper.vm.$nextTick();

      // Cliquer sur le bouton d'ajout manuel
      const addButton = wrapper.find('[data-testid="manual-add-btn"]');
      expect(addButton.exists()).toBe(true);
      await addButton.trigger('click');
      await wrapper.vm.$nextTick();

      // Vérifier qu'un modal s'ouvre pour l'ajout manuel
      const modal = wrapper.find('[data-testid="manual-add-modal"]');
      expect(modal.exists()).toBe(true);
      expect(modal.isVisible()).toBe(true);

      // Vérifier que le modal contient des champs de saisie
      expect(modal.find('[data-testid="author-input"]').exists()).toBe(true);
      expect(modal.find('[data-testid="title-input"]').exists()).toBe(true);
      expect(modal.find('[data-testid="publisher-input"]').exists()).toBe(true);
    });

    it('permet de valider une suggestion via le modal', async () => {
      const mockBooksWithSuggested = [
        {
          episode_oid: '64f1234567890abcdef12345', // pragma: allowlist secret // pragma: allowlist secret
          auteur: 'Michel Houllebeck',
          titre: 'Les Particules élémentaires',
          editeur: 'Flammarion',
          validation_status: 'suggested',
          suggested_author: 'Michel Houellebecq',
          suggested_title: 'Les Particules élémentaires',
          programme: false,
          coup_de_coeur: false
        }
      ];

      const mockValidationResult = {
        success: true,
        author_id: '64f1234567890abcdef11111', // pragma: allowlist secret
        book_id: '64f1234567890abcdef22222' // pragma: allowlist secret
      };

      episodeService.getEpisodeById.mockResolvedValue(mockEpisode);
      livresAuteursService.getEpisodesWithReviews.mockResolvedValue(mockEpisodesWithReviews);
      livresAuteursService.getLivresAuteurs.mockResolvedValue(mockBooksWithSuggested);
      livresAuteursService.validateSuggestion.mockResolvedValue(mockValidationResult);

      wrapper = mount(LivresAuteurs, {
        global: {
          plugins: [router]
        }
      });

      await wrapper.vm.$nextTick();
      wrapper.vm.selectedEpisodeId = mockEpisode.id;
      await wrapper.vm.loadBooksForEpisode();
      await wrapper.vm.$nextTick();

      // Définir le statut de validation et les suggestions pour afficher le bouton
      const book = wrapper.vm.books[0];
      const bookKey = wrapper.vm.getBookKey(book);
      wrapper.vm.validationStatuses.set(bookKey, 'corrected');

      // Simuler les suggestions Babelio stockées
      wrapper.vm.validationSuggestions.set(bookKey, {
        author: 'Michel Houellebecq',
        title: 'Les Particules élémentaires',
        publisher: 'Flammarion'
      });

      await wrapper.vm.$nextTick();

      // Ouvrir le modal
      const validateButton = wrapper.find('[data-testid="validate-suggestion-btn"]');
      await validateButton.trigger('click');
      await wrapper.vm.$nextTick();

      // Confirmer la validation dans le modal
      const confirmButton = wrapper.find('[data-testid="confirm-validation-btn"]');
      await confirmButton.trigger('click');
      await wrapper.vm.$nextTick();

      // Vérifier que le service a été appelé
      expect(livresAuteursService.validateSuggestion).toHaveBeenCalled();

      // Vérifier que le modal se ferme
      const modal = wrapper.find('[data-testid="validation-modal"]');
      expect(modal.exists()).toBe(false);
    });

    it('permet d\'ajouter manuellement un livre via le modal', async () => {
      const mockBooksWithNotFound = [
        {
          episode_oid: '64f1234567890abcdef12345', // pragma: allowlist secret // pragma: allowlist secret
          auteur: 'Auteur Inconnu',
          titre: 'Livre Introuvable',
          editeur: 'Éditeur Inconnu',
          validation_status: 'not_found',
          suggested_author: null,
          suggested_title: null,
          programme: false,
          coup_de_coeur: false
        }
      ];

      const mockAddResult = {
        success: true,
        author_id: '64f1234567890abcdef11111', // pragma: allowlist secret
        book_id: '64f1234567890abcdef22222' // pragma: allowlist secret
      };

      episodeService.getEpisodeById.mockResolvedValue(mockEpisode);
      livresAuteursService.getEpisodesWithReviews.mockResolvedValue(mockEpisodesWithReviews);
      livresAuteursService.getLivresAuteurs.mockResolvedValue(mockBooksWithNotFound);
      livresAuteursService.validateSuggestion.mockResolvedValue(mockAddResult);

      wrapper = mount(LivresAuteurs, {
        global: {
          plugins: [router]
        }
      });

      await wrapper.vm.$nextTick();
      wrapper.vm.selectedEpisodeId = mockEpisode.id;
      await wrapper.vm.loadBooksForEpisode();
      await wrapper.vm.$nextTick();

      // Définir le statut de validation pour afficher le bouton d'ajout manuel
      const book = wrapper.vm.books[0];
      const bookKey = wrapper.vm.getBookKey(book);
      wrapper.vm.validationStatuses.set(bookKey, 'not_found');

      await wrapper.vm.$nextTick();

      // Ouvrir le modal
      const addButton = wrapper.find('[data-testid="manual-add-btn"]');
      await addButton.trigger('click');
      await wrapper.vm.$nextTick();

      // Remplir les champs
      const authorInput = wrapper.find('[data-testid="author-input"]');
      const titleInput = wrapper.find('[data-testid="title-input"]');
      const publisherInput = wrapper.find('[data-testid="publisher-input"]');

      await authorInput.setValue('Nouvel Auteur');
      await titleInput.setValue('Nouveau Titre');
      await publisherInput.setValue('Nouvel Éditeur');

      // Soumettre le formulaire
      const submitButton = wrapper.find('[data-testid="submit-manual-add-btn"]');
      await submitButton.trigger('click');
      await wrapper.vm.$nextTick();

      // Vérifier que le service a été appelé avec les bonnes données
      expect(livresAuteursService.validateSuggestion).toHaveBeenCalledWith(
        expect.objectContaining({
          user_validated_author: 'Nouvel Auteur',
          user_validated_title: 'Nouveau Titre',
          user_validated_publisher: 'Nouvel Éditeur'
        })
      );

      // Vérifier que le modal se ferme
      const modal = wrapper.find('[data-testid="manual-add-modal"]');
      expect(modal.exists()).toBe(false);
    });

    it('permet de fermer les modaux avec le bouton Annuler', async () => {
      const mockBooksWithSuggested = [
        {
          episode_oid: '64f1234567890abcdef12345', // pragma: allowlist secret // pragma: allowlist secret
          auteur: 'Michel Houllebeck',
          titre: 'Les Particules élémentaires',
          editeur: 'Flammarion',
          validation_status: 'suggested',
          suggested_author: 'Michel Houellebecq',
          suggested_title: 'Les Particules élémentaires',
          programme: false,
          coup_de_coeur: false
        }
      ];

      episodeService.getEpisodeById.mockResolvedValue(mockEpisode);
      livresAuteursService.getEpisodesWithReviews.mockResolvedValue(mockEpisodesWithReviews);
      livresAuteursService.getLivresAuteurs.mockResolvedValue(mockBooksWithSuggested);

      wrapper = mount(LivresAuteurs, {
        global: {
          plugins: [router]
        }
      });

      await wrapper.vm.$nextTick();
      wrapper.vm.selectedEpisodeId = mockEpisode.id;
      await wrapper.vm.loadBooksForEpisode();
      await wrapper.vm.$nextTick();

      // Définir le statut de validation et les suggestions pour afficher le bouton
      const book = wrapper.vm.books[0];
      const bookKey = wrapper.vm.getBookKey(book);
      wrapper.vm.validationStatuses.set(bookKey, 'corrected');

      // Simuler les suggestions Babelio stockées
      wrapper.vm.validationSuggestions.set(bookKey, {
        author: 'Michel Houellebecq',
        title: 'Les Particules élémentaires',
        publisher: 'Flammarion'
      });

      await wrapper.vm.$nextTick();

      // Ouvrir le modal
      const validateButton = wrapper.find('[data-testid="validate-suggestion-btn"]');
      await validateButton.trigger('click');
      await wrapper.vm.$nextTick();

      // Vérifier que le modal est ouvert
      let modal = wrapper.find('[data-testid="validation-modal"]');
      expect(modal.exists()).toBe(true);

      // Cliquer sur Annuler
      const cancelButton = wrapper.find('[data-testid="cancel-modal-btn"]');
      await cancelButton.trigger('click');
      await wrapper.vm.$nextTick();

      // Vérifier que le modal se ferme
      modal = wrapper.find('[data-testid="validation-modal"]');
      expect(modal.exists()).toBe(false);
    });
  });

  describe('Cache Management', () => {
    it('should display refresh cache button when episode is selected', async () => {
      // Arrange
      const episodeOid = '68d98f74edbcf1765933a9b5'; // pragma: allowlist secret
      livresAuteursService.getLivresAuteurs.mockResolvedValue([
        {
          episode_oid: episodeOid,
          episode_title: 'Test Episode',
          auteur: 'Test Author',
          titre: 'Test Book',
          editeur: 'Test Publisher',
        }
      ]);

      // Act
      wrapper = mount(LivresAuteurs, {
        global: { plugins: [router] }
      });
      await wrapper.vm.$nextTick();

      // Sélectionner un épisode
      wrapper.vm.selectedEpisodeId = episodeOid;
      await wrapper.vm.$nextTick();
      await new Promise(resolve => setTimeout(resolve, 100));

      // Assert
      const refreshButton = wrapper.find('[data-testid="refresh-cache-button"]');
      expect(refreshButton.exists()).toBe(true);
    });

    it('should call deleteCacheByEpisode when refresh button is clicked', async () => {
      // Arrange
      const episodeOid = '68d98f74edbcf1765933a9b5'; // pragma: allowlist secret
      livresAuteursService.getLivresAuteurs.mockResolvedValue([
        {
          episode_oid: episodeOid,
          episode_title: 'Test Episode',
          auteur: 'Test Author',
          titre: 'Test Book',
          editeur: 'Test Publisher',
        }
      ]);
      livresAuteursService.deleteCacheByEpisode = vi.fn().mockResolvedValue({ deleted_count: 3 });

      wrapper = mount(LivresAuteurs, {
        global: { plugins: [router] }
      });
      await wrapper.vm.$nextTick();

      // Sélectionner un épisode
      wrapper.vm.selectedEpisodeId = episodeOid;
      await wrapper.vm.$nextTick();
      await new Promise(resolve => setTimeout(resolve, 100));

      // Act
      const refreshButton = wrapper.find('[data-testid="refresh-cache-button"]');
      await refreshButton.trigger('click');
      await wrapper.vm.$nextTick();

      // Assert
      expect(livresAuteursService.deleteCacheByEpisode).toHaveBeenCalledWith(episodeOid);
    });
  });

  describe('Validation Statistics Display', () => {
    it('should compute validation statistics for programme books', async () => {
      // Arrange
      const episodeOid = '507f1f77bcf86cd799439011'; // pragma: allowlist secret
      const mockBooks = [
        { auteur: 'Auteur 1', titre: 'Livre 1', programme: true, status: 'mongo' },
        { auteur: 'Auteur 2', titre: 'Livre 2', programme: true, status: 'extracted', suggested_author: 'Auteur 2 Corrected' },
        { auteur: 'Auteur 3', titre: 'Livre 3', programme: true, status: 'extracted', suggested_title: 'Livre 3 Corrected' },
        { auteur: 'Auteur 4', titre: 'Livre 4', programme: true, status: 'extracted' },
        { auteur: 'Auteur 5', titre: 'Livre 5', programme: false, status: 'mongo' }, // Not counted (not programme)
      ];

      livresAuteursService.getLivresAuteurs.mockResolvedValueOnce(mockBooks);
      livresAuteursService.getEpisodesWithReviews.mockResolvedValueOnce([
        { id: episodeOid, titre: 'Test Episode', date: '2025-01-01' }
      ]);
      episodeService.getEpisodeById.mockResolvedValueOnce({
        id: episodeOid,
        titre: 'Test Episode',
        description: 'Test description'
      });

      wrapper = mount(LivresAuteurs, {
        global: { plugins: [router] }
      });
      await wrapper.vm.$nextTick();

      // Act: select episode and set books
      wrapper.vm.selectedEpisodeId = episodeOid;
      wrapper.vm.books = mockBooks;
      await wrapper.vm.$nextTick();

      // Assert: check computed property
      const stats = wrapper.vm.programBooksValidationStats;
      expect(stats.total).toBe(4); // 4 books with programme: true
      expect(stats.traites).toBe(1); // 1 book with status === 'mongo'
      expect(stats.suggested).toBe(2); // 2 books with suggestions
      expect(stats.not_found).toBe(1); // 1 book without suggestions
    });

    it('should display validation stats in the UI when programme books exist', async () => {
      // Arrange
      const episodeOid = '507f1f77bcf86cd799439011'; // pragma: allowlist secret
      const mockBooks = [
        { auteur: 'Auteur 1', titre: 'Livre 1', programme: true, status: 'mongo' },
        { auteur: 'Auteur 2', titre: 'Livre 2', programme: true, status: 'extracted', suggested_title: 'Livre 2 Corrected' },
      ];

      livresAuteursService.getLivresAuteurs.mockResolvedValueOnce(mockBooks);
      livresAuteursService.getEpisodesWithReviews.mockResolvedValueOnce([
        { id: episodeOid, titre: 'Test Episode', date: '2025-01-01' }
      ]);
      episodeService.getEpisodeById.mockResolvedValueOnce({
        id: episodeOid,
        titre: 'Test Episode',
        description: 'Test description'
      });

      wrapper = mount(LivresAuteurs, {
        global: { plugins: [router] }
      });
      await wrapper.vm.$nextTick();

      // Act: select episode and set books
      wrapper.vm.selectedEpisodeId = episodeOid;
      wrapper.vm.books = mockBooks;
      await wrapper.vm.$nextTick();

      // Assert: check that validation stats are visible
      const statsElement = wrapper.find('.validation-stats');
      expect(statsElement.exists()).toBe(true);
      expect(statsElement.text()).toContain('au programme');
      expect(statsElement.text()).toContain('1 traités');
      expect(statsElement.text()).toContain('1 suggested');
    });

    it('should not display validation stats when no programme books exist', async () => {
      // Arrange
      const episodeOid = '507f1f77bcf86cd799439011'; // pragma: allowlist secret
      const mockBooks = [
        { auteur: 'Auteur 1', titre: 'Livre 1', programme: false, validation_status: 'verified' },
      ];

      livresAuteursService.getLivresAuteurs.mockResolvedValueOnce(mockBooks);
      livresAuteursService.getEpisodesWithReviews.mockResolvedValueOnce([
        { id: episodeOid, titre: 'Test Episode', date: '2025-01-01' }
      ]);
      episodeService.getEpisodeById.mockResolvedValueOnce({
        id: episodeOid,
        titre: 'Test Episode',
        description: 'Test description'
      });

      wrapper = mount(LivresAuteurs, {
        global: { plugins: [router] }
      });
      await wrapper.vm.$nextTick();

      // Act: select episode and set books
      wrapper.vm.selectedEpisodeId = episodeOid;
      wrapper.vm.books = mockBooks;
      await wrapper.vm.$nextTick();

      // Assert: validation stats should not be visible
      const statsElement = wrapper.find('.validation-stats');
      expect(statsElement.exists()).toBe(false);
    });
  });
});
