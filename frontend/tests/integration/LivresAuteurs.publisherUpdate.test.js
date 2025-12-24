/**
 * Tests pour la mise à jour de l'éditeur lors de la validation (Issue #159)
 *
 * Bug découvert: Quand l'utilisateur modifie l'éditeur dans la modale de validation,
 * l'ancien éditeur reste affiché dans le cache au lieu du nouvel éditeur validé.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount } from '@vue/test-utils';
import { createRouter, createWebHistory } from 'vue-router';
import LivresAuteurs from '../../src/views/LivresAuteurs.vue';
import { livresAuteursService, episodeService } from '../../src/services/api.js';

// Mock du service API
vi.mock('../../src/services/api.js', () => ({
  livresAuteursService: {
    getLivresAuteurs: vi.fn(),
    getEpisodesWithReviews: vi.fn(),
    validateSuggestion: vi.fn(),
    getAllAuthors: vi.fn(),
    getAllBooks: vi.fn(),
  },
  episodeService: {
    getAllEpisodes: vi.fn(),
    getEpisodeById: vi.fn(),
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
    searchEpisode: vi.fn(),
  },
}));

describe('LivresAuteurs - Mise à jour éditeur lors de validation', () => {
  let wrapper;
  let router;

  beforeEach(() => {
    vi.resetAllMocks();

    router = createRouter({
      history: createWebHistory(),
      routes: [
        {
          path: '/livres-auteurs',
          name: 'LivresAuteurs',
          component: LivresAuteurs,
        },
      ],
    });
  });

  it('RED Test: [Validation] devrait envoyer le nouvel éditeur validé et non l\'ancien éditeur du cache', async () => {
    // Arrange: Simuler un épisode avec un livre à valider
    const mockEpisode = {
      id: 'episode-123',
      titre: 'Émission Test',
      avis_critique_id: 'avis-123',
    };

    const mockBook = {
      cache_id: 'cache-456',
      episode_oid: 'episode-123',
      auteur: 'John Waters',
      titre: 'Monsieur je sais tout',
      editeur: 'Éditions de l\'Olivier', // Ancien éditeur
      babelio_verification_status: 'corrected',
      programme: true,
    };

    episodeService.getEpisodeById.mockResolvedValue(mockEpisode);
    livresAuteursService.getEpisodesWithReviews.mockResolvedValue([
      {
        id: 'episode-123',
        titre: 'Émission Test',
        avis_critique_id: 'avis-123',
        has_incomplete_books: true,
      },
    ]);
    livresAuteursService.getLivresAuteurs.mockResolvedValue([mockBook]);
    livresAuteursService.validateSuggestion.mockResolvedValue({ success: true });

    // Mount component
    wrapper = mount(LivresAuteurs, {
      global: {
        plugins: [router],
        stubs: {
          BiblioValidationCell: true,
        },
      },
    });

    // Attendre que le composant charge les données
    await router.isReady();
    await wrapper.vm.$nextTick();

    // Sélectionner l'épisode
    wrapper.vm.selectedEpisodeId = 'episode-123';
    await wrapper.vm.loadBooksForEpisode();
    await wrapper.vm.$nextTick();

    // Act: Ouvrir le modal de validation et changer l'éditeur
    wrapper.vm.currentBookToValidate = mockBook;
    wrapper.vm.validationForm = {
      author: 'John Waters',
      title: 'M. Je-Sais-Tout : Conseils impurs d\'un vieux dégueulasse',
      publisher: 'Actes Sud', // NOUVEAU éditeur validé
    };
    wrapper.vm.showValidationModal = true;

    // Simuler les données de suggestion (comme si BiblioValidationCell les avait fournies)
    const bookKey = wrapper.vm.getBookKey(mockBook);
    wrapper.vm.validationSuggestions.set(bookKey, {
      suggested_author: 'John Waters',
      suggested_title: 'M. Je-Sais-Tout : Conseils impurs d\'un vieux dégueulasse',
      suggested_publisher: 'Actes Sud',
    });

    // Confirmer la validation
    await wrapper.vm.confirmValidation();

    // Assert: Vérifier que validateSuggestion a été appelé avec le NOUVEAU éditeur
    expect(livresAuteursService.validateSuggestion).toHaveBeenCalledWith(
      expect.objectContaining({
        cache_id: 'cache-456',
        episode_oid: 'episode-123',
        avis_critique_id: 'avis-123',
        auteur: 'John Waters', // Devrait être le validé
        titre: 'M. Je-Sais-Tout : Conseils impurs d\'un vieux dégueulasse', // Devrait être le validé
        editeur: 'Actes Sud', // ❌ ÉCHEC ATTENDU: actuellement "Éditions de l'Olivier"
        user_validated_author: 'John Waters',
        user_validated_title: 'M. Je-Sais-Tout : Conseils impurs d\'un vieux dégueulasse',
        user_validated_publisher: 'Actes Sud',
      })
    );
  });

  it('RED Test: [Ajout manuel] devrait envoyer le nouvel éditeur saisi et non l\'ancien éditeur du cache', async () => {
    // Arrange: Simuler un épisode avec un livre "not_found" à ajouter manuellement
    const mockEpisode = {
      id: 'episode-789',
      titre: 'Émission Test 2',
      avis_critique_id: 'avis-789',
    };

    const mockBook = {
      cache_id: 'cache-999',
      episode_oid: 'episode-789',
      auteur: 'Dario Franceschini',
      titre: 'Ailleurs',
      editeur: 'Éditions de l\'Olivier', // Ancien éditeur
      babelio_verification_status: 'not_found',
      programme: true,
    };

    episodeService.getEpisodeById.mockResolvedValue(mockEpisode);
    livresAuteursService.getEpisodesWithReviews.mockResolvedValue([
      {
        id: 'episode-789',
        titre: 'Émission Test 2',
        avis_critique_id: 'avis-789',
        has_incomplete_books: true,
      },
    ]);
    livresAuteursService.getLivresAuteurs.mockResolvedValue([mockBook]);
    livresAuteursService.validateSuggestion.mockResolvedValue({ success: true });

    // Mount component
    wrapper = mount(LivresAuteurs, {
      global: {
        plugins: [router],
        stubs: {
          BiblioValidationCell: true,
        },
      },
    });

    // Attendre que le composant charge les données
    await router.isReady();
    await wrapper.vm.$nextTick();

    // Sélectionner l'épisode
    wrapper.vm.selectedEpisodeId = 'episode-789';
    await wrapper.vm.loadBooksForEpisode();
    await wrapper.vm.$nextTick();

    // Act: Ouvrir le modal d'ajout manuel et saisir les données
    wrapper.vm.currentBookToAdd = mockBook;
    wrapper.vm.manualBookForm = {
      author: 'Dario Franceschini',
      title: 'Ailleurs',
      publisher: 'Gallimard', // NOUVEAU éditeur saisi manuellement
    };
    wrapper.vm.showManualAddModal = true;

    // Confirmer l'ajout manuel
    await wrapper.vm.submitManualAdd();

    // Assert: Vérifier que validateSuggestion a été appelé avec le NOUVEAU éditeur
    expect(livresAuteursService.validateSuggestion).toHaveBeenCalledWith(
      expect.objectContaining({
        cache_id: 'cache-999',
        episode_oid: 'episode-789',
        avis_critique_id: 'avis-789',
        auteur: 'Dario Franceschini', // Devrait être le saisi
        titre: 'Ailleurs', // Devrait être le saisi
        editeur: 'Gallimard', // ❌ ÉCHEC ATTENDU: actuellement "Éditions de l'Olivier"
        user_validated_author: 'Dario Franceschini',
        user_validated_title: 'Ailleurs',
        user_validated_publisher: 'Gallimard',
      })
    );
  });
});
