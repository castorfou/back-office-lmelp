/**
 * Tests TDD pour la distinction entre échec technique et vrai "not_found" (Issue #282).
 *
 * Bug racine: `autoValidateAndSendResults()` convertissait TOUTE exception levée
 * par `validateBiblio()` (réseau, timeout, Babelio bloqué) en un objet
 * `validation_status: 'not_found'` envoyé au backend — masquant un échec
 * technique retriable comme un vrai "livre introuvable sur Babelio", ce qui
 * bloquait le livre en statut `not_found` indéfiniment (voir aussi le
 * catch backend correspondant dans `set_validation_results`).
 *
 * Note: `validateBiblio()` ne lève en réalité jamais d'exception dans son cas
 * nominal — elle résout avec `{status: 'error', ...}` en cas d'échec interne.
 * C'est ce statut `'error'` qui doit être distingué de `'not_found'`.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount } from '@vue/test-utils';
import { createRouter, createWebHistory } from 'vue-router';
import LivresAuteurs from '../../src/views/LivresAuteurs.vue';
import { livresAuteursService } from '../../src/services/api.js';
import BiblioValidationService from '../../src/services/BiblioValidationService.js';

vi.mock('../../src/services/api.js', () => ({
  livresAuteursService: {
    getLivresAuteurs: vi.fn(),
    getEpisodesWithReviews: vi.fn(),
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
    searchEpisode: vi.fn(),
  },
}));

describe('LivresAuteurs - Distinction échec technique vs not_found (Issue #282)', () => {
  let wrapper;
  let router;

  const mockEpisodesWithReviews = [
    {
      _id: { $oid: '6865f995a1418e3d7c63d076' }, // pragma: allowlist secret
      titre: 'Episode test',
      date: '29 juin 2025',
      review_count: 1,
    },
  ];

  beforeEach(async () => {
    vi.clearAllMocks();
    sessionStorage.clear();
    BiblioValidationService._extractedBooksCache?.clear();

    router = createRouter({
      history: createWebHistory(),
      routes: [
        { path: '/', component: { template: '<div>Dashboard</div>' } },
        { path: '/livres-auteurs', component: LivresAuteurs },
      ],
    });
    await router.push('/livres-auteurs');
  });

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount();
    }
    sessionStorage.clear();
    vi.useRealTimers();
  });

  async function mountPage() {
    livresAuteursService.getEpisodesWithReviews.mockResolvedValue(mockEpisodesWithReviews);
    wrapper = mount(LivresAuteurs, {
      global: { plugins: [router] },
    });
    await wrapper.vm.$nextTick();
    await new Promise((resolve) => setTimeout(resolve, 50));
    return wrapper;
  }

  it("transmet validation_status='error' au backend quand validateBiblio lève une exception (pas 'not_found')", async () => {
    const mockBooks = [
      {
        episode_oid: '6865f995a1418e3d7c63d076', // pragma: allowlist secret
        auteur: 'Valérie Manteau',
        titre: 'Le Sillon',
        editeur: 'Le Tripode',
        validation_status: null,
        programme: false,
      },
    ];

    livresAuteursService.getLivresAuteurs.mockResolvedValue(mockBooks);
    livresAuteursService.setValidationResults.mockResolvedValue({ success: true });

    await mountPage();

    wrapper.vm.books = mockBooks;
    // Simule un échec technique réel (réseau, timeout) — le catch de
    // autoValidateAndSendResults() convertissait auparavant systématiquement
    // ce cas en validation_status: 'not_found', masquant l'échec technique.
    vi.spyOn(BiblioValidationService, 'validateBiblio').mockRejectedValue(
      new Error('Network timeout')
    );

    await wrapper.vm.autoValidateAndSendResults();
    await wrapper.vm.$nextTick();

    expect(livresAuteursService.setValidationResults).toHaveBeenCalled();
    const callArgs = livresAuteursService.setValidationResults.mock.calls[0][0];
    const sentBook = callArgs.books[0];
    expect(sentBook.validation_status).toBe('error');
  });
});
