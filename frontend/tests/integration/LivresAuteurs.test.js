/**
 * Tests simplifiés pour la page Livres/Auteurs
 * Focus sur la structure de base sans interactions complexes
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount } from '@vue/test-utils';
import { createRouter, createWebHistory } from 'vue-router';
import LivresAuteurs from '../../src/views/LivresAuteurs.vue';
import { livresAuteursService } from '../../src/services/api.js';

// Mock du service API
vi.mock('../../src/services/api.js', () => ({
  livresAuteursService: {
    getLivresAuteurs: vi.fn(),
    getEpisodesWithReviews: vi.fn(),
    // Nouveaux endpoints pour Issue #66
    getCollectionsStatistics: vi.fn(),
    autoProcessVerifiedBooks: vi.fn(),
    getBooksByValidationStatus: vi.fn(),
    validateSuggestion: vi.fn(),
    addManualBook: vi.fn(),
    getAllAuthors: vi.fn(),
    getAllBooks: vi.fn(),
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

  const mockEpisodesWithReviews = [
    {
      _id: { $oid: '6865f995a1418e3d7c63d076' }, // pragma: allowlist secret
      titre: 'Les critiques littéraires du Masque & la Plume depuis le festival "Quai du Polar" à Lyon',
      date: '29 juin 2025',
      review_count: 4
    }
  ];

  beforeEach(async () => {
    vi.clearAllMocks();

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
      episodeId: '6865f995a1418e3d7c63d076' // pragma: allowlist secret
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
    it('affiche le dashboard des statistiques collections', async () => {
      const mockStatistics = {
        episodes_non_traites: 25,
        couples_en_base: 142,
        couples_verified_pas_en_base: 18,
        couples_suggested_pas_en_base: 12,
        couples_not_found_pas_en_base: 8
      };

      livresAuteursService.getEpisodesWithReviews.mockResolvedValue(mockEpisodesWithReviews);
      livresAuteursService.getCollectionsStatistics.mockResolvedValue(mockStatistics);

      wrapper = mount(LivresAuteurs, {
        global: {
          plugins: [router]
        }
      });

      await wrapper.vm.$nextTick();
      await wrapper.vm.loadCollectionsStatistics();
      await wrapper.vm.$nextTick();

      // Vérifier que les statistiques sont affichées
      expect(wrapper.text()).toContain('Épisodes non traités : 25');
      expect(wrapper.text()).toContain('Couples en base : 142');
      expect(wrapper.text()).toContain('Verified pas en base : 18');
      expect(wrapper.text()).toContain('Suggested pas en base : 12');
      expect(wrapper.text()).toContain('Not found pas en base : 8');
    });

    it('affiche le bouton de traitement automatique', async () => {
      livresAuteursService.getEpisodesWithReviews.mockResolvedValue(mockEpisodesWithReviews);

      wrapper = mount(LivresAuteurs, {
        global: {
          plugins: [router]
        }
      });

      await wrapper.vm.$nextTick();

      // Vérifier que le bouton de traitement automatique est présent
      const autoProcessButton = wrapper.find('[data-testid="auto-process-button"]');
      expect(autoProcessButton.exists()).toBe(true);
      expect(autoProcessButton.text()).toContain('Traitement automatique');
    });

    it('traite automatiquement les livres verified', async () => {
      const mockProcessResult = {
        processed_count: 15,
        created_authors: 8,
        created_books: 15,
        updated_references: 25
      };

      livresAuteursService.getEpisodesWithReviews.mockResolvedValue(mockEpisodesWithReviews);
      livresAuteursService.autoProcessVerifiedBooks.mockResolvedValue(mockProcessResult);

      wrapper = mount(LivresAuteurs, {
        global: {
          plugins: [router]
        }
      });

      await wrapper.vm.$nextTick();

      // Cliquer sur le bouton de traitement automatique
      const autoProcessButton = wrapper.find('[data-testid="auto-process-button"]');
      await autoProcessButton.trigger('click');
      await wrapper.vm.$nextTick();

      // Vérifier que le service a été appelé
      expect(livresAuteursService.autoProcessVerifiedBooks).toHaveBeenCalled();

      // Vérifier que les résultats sont affichés
      expect(wrapper.text()).toContain('15 livres traités');
      expect(wrapper.text()).toContain('8 auteurs créés');
    });
  });

  describe('Manual Validation Interface (Issue #66)', () => {
    it('affiche les livres suggested avec interface de validation', async () => {
      const mockSuggestedBooks = [
        {
          id: '64f1234567890abcdef12345', // pragma: allowlist secret
          auteur: 'Michel Houllebeck',
          titre: 'Les Particules élémentaires',
          validation_status: 'suggested',
          suggested_author: 'Michel Houellebecq',
          suggested_title: 'Les Particules élémentaires'
        }
      ];

      livresAuteursService.getEpisodesWithReviews.mockResolvedValue(mockEpisodesWithReviews);
      livresAuteursService.getBooksByValidationStatus.mockResolvedValue(mockSuggestedBooks);

      wrapper = mount(LivresAuteurs, {
        global: {
          plugins: [router]
        }
      });

      await wrapper.vm.$nextTick();
      await wrapper.vm.loadSuggestedBooks();
      await wrapper.vm.$nextTick();

      // Vérifier que les livres suggested sont affichés
      expect(wrapper.text()).toContain('Michel Houllebeck');
      expect(wrapper.text()).toContain('Suggestion : Michel Houellebecq');

      // Vérifier que le bouton de validation est présent
      const validateButton = wrapper.find('[data-testid="validate-suggestion-button"]');
      expect(validateButton.exists()).toBe(true);
    });

    it('valide manuellement une suggestion', async () => {
      const mockValidationResult = {
        success: true,
        author_id: '64f1234567890abcdef11111', // pragma: allowlist secret
        book_id: '64f1234567890abcdef22222' // pragma: allowlist secret
      };

      livresAuteursService.validateSuggestion.mockResolvedValue(mockValidationResult);

      wrapper = mount(LivresAuteurs, {
        global: {
          plugins: [router]
        }
      });

      await wrapper.vm.$nextTick();

      const bookData = {
        id: '64f1234567890abcdef12345', // pragma: allowlist secret
        user_validated_author: 'Michel Houellebecq',
        user_validated_title: 'Les Particules élémentaires'
      };

      await wrapper.vm.validateSuggestion(bookData);

      // Vérifier que le service a été appelé avec les bonnes données
      expect(livresAuteursService.validateSuggestion).toHaveBeenCalledWith(bookData);
    });
  });

  describe('Manual Add Interface (Issue #66)', () => {
    it('affiche les livres not_found avec interface d\'ajout manuel', async () => {
      const mockNotFoundBooks = [
        {
          id: '64f1234567890abcdef12345', // pragma: allowlist secret
          auteur: 'Auteur Inconnu',
          titre: 'Livre Introuvable',
          validation_status: 'not_found'
        }
      ];

      livresAuteursService.getEpisodesWithReviews.mockResolvedValue(mockEpisodesWithReviews);
      livresAuteursService.getBooksByValidationStatus.mockResolvedValue(mockNotFoundBooks);

      wrapper = mount(LivresAuteurs, {
        global: {
          plugins: [router]
        }
      });

      await wrapper.vm.$nextTick();
      await wrapper.vm.loadNotFoundBooks();
      await wrapper.vm.$nextTick();

      // Vérifier que les livres not_found sont affichés
      expect(wrapper.text()).toContain('Auteur Inconnu');
      expect(wrapper.text()).toContain('Livre Introuvable');

      // Vérifier que le bouton d'ajout manuel est présent
      const addManualButton = wrapper.find('[data-testid="add-manual-book-button"]');
      expect(addManualButton.exists()).toBe(true);
    });

    it('ajoute manuellement un livre not_found', async () => {
      const mockAddResult = {
        success: true,
        author_id: '64f1234567890abcdef11111', // pragma: allowlist secret
        book_id: '64f1234567890abcdef22222' // pragma: allowlist secret
      };

      livresAuteursService.addManualBook.mockResolvedValue(mockAddResult);

      wrapper = mount(LivresAuteurs, {
        global: {
          plugins: [router]
        }
      });

      await wrapper.vm.$nextTick();

      const bookData = {
        id: '64f1234567890abcdef12345', // pragma: allowlist secret
        user_entered_author: 'Nouvel Auteur',
        user_entered_title: 'Nouveau Titre',
        user_entered_publisher: 'Nouvel Éditeur'
      };

      await wrapper.vm.addManualBook(bookData);

      // Vérifier que le service a été appelé avec les bonnes données
      expect(livresAuteursService.addManualBook).toHaveBeenCalledWith(bookData);
    });
  });

  describe('Collections Management (Issue #66)', () => {
    it('affiche la liste des auteurs créés', async () => {
      const mockAuthors = [
        {
          id: '64f1234567890abcdef11111', // pragma: allowlist secret
          nom: 'Michel Houellebecq',
          livres: ['64f1234567890abcdef22222'], // pragma: allowlist secret
          created_at: '2024-01-01T10:00:00Z'
        }
      ];

      livresAuteursService.getAllAuthors.mockResolvedValue(mockAuthors);

      wrapper = mount(LivresAuteurs, {
        global: {
          plugins: [router]
        }
      });

      await wrapper.vm.$nextTick();
      await wrapper.vm.loadAllAuthors();
      await wrapper.vm.$nextTick();

      // Vérifier que les auteurs sont affichés
      expect(wrapper.text()).toContain('Michel Houellebecq');
    });

    it('affiche la liste des livres créés', async () => {
      const mockBooks = [
        {
          id: '64f1234567890abcdef22222', // pragma: allowlist secret
          titre: 'Les Particules élémentaires',
          auteur_id: '64f1234567890abcdef11111', // pragma: allowlist secret
          editeur: 'Flammarion',
          created_at: '2024-01-01T10:00:00Z'
        }
      ];

      livresAuteursService.getAllBooks.mockResolvedValue(mockBooks);

      wrapper = mount(LivresAuteurs, {
        global: {
          plugins: [router]
        }
      });

      await wrapper.vm.$nextTick();
      await wrapper.vm.loadAllBooks();
      await wrapper.vm.$nextTick();

      // Vérifier que les livres sont affichés
      expect(wrapper.text()).toContain('Les Particules élémentaires');
      expect(wrapper.text()).toContain('Flammarion');
    });
  });
});
