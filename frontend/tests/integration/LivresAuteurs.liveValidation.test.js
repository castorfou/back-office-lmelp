/**
 * Validation Babelio au fil de l'eau (Issue #352) : chaque ligne du tableau
 * prend son statut dès que son livre est validé, sans attendre la fin de la
 * boucle ni le rechargement final, et sans aucune requête en plus.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { createRouter, createWebHistory } from 'vue-router';
import LivresAuteurs from '../../src/views/LivresAuteurs.vue';
import { livresAuteursService } from '../../src/services/api.js';
import BiblioValidationService from '../../src/services/BiblioValidationService.js';
import axios from 'axios';

vi.mock('axios');

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

const EPISODE_OID = '6865f995a1418e3d7c63d076'; // pragma: allowlist secret

const makeBooks = () => [
  {
    episode_oid: EPISODE_OID,
    auteur: 'Valérie Manteau',
    titre: 'Le Sillon',
    editeur: 'Le Tripode',
    programme: true,
  },
  {
    episode_oid: EPISODE_OID,
    auteur: 'Emmanuel Carrère',
    titre: 'Yoga',
    editeur: 'POL',
    programme: true,
  },
];

function deferred() {
  let resolve;
  const promise = new Promise((r) => { resolve = r; });
  return { promise, resolve };
}

describe('LivresAuteurs - tableau mis à jour au fil de la validation (Issue #352)', () => {
  let wrapper;
  let router;

  beforeEach(async () => {
    vi.resetAllMocks();
    axios.get.mockImplementation((url) => {
      if (url.startsWith('/api/babelio/status')) {
        return Promise.resolve({
          data: { cookie_active: true, cookie_age_sec: 10, cookie_max_age_sec: 300, cookie_expired: false },
        });
      }
      return Promise.resolve({ data: {} });
    });
    axios.post.mockImplementation((url) => {
      if (url === '/api/babelio/probe') {
        return Promise.resolve({ data: { reachable: true, circuit_open: false, circuit_reason: null } });
      }
      return Promise.resolve({ data: {} });
    });
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
    if (wrapper) wrapper.unmount();
    sessionStorage.clear();
    vi.restoreAllMocks();
  });

  async function mountWithBooks() {
    livresAuteursService.getEpisodesWithReviews.mockResolvedValue([
      { id: EPISODE_OID, titre: 'Episode test', date: '2025-06-29', review_count: 1 },
    ]);
    livresAuteursService.getLivresAuteurs.mockResolvedValue(makeBooks());
    livresAuteursService.setValidationResults.mockResolvedValue({ success: true });
    wrapper = mount(LivresAuteurs, { global: { plugins: [router] } });
    await flushPromises();
    wrapper.vm.selectedEpisodeId = EPISODE_OID;
    wrapper.vm.books = makeBooks();
    await flushPromises();
    return wrapper;
  }

  function rowOf(titre) {
    return wrapper.findAll('[data-testid="book-item"]').find((row) => row.text().includes(titre));
  }

  it('affiche le statut du premier livre avant que le second soit validé', async () => {
    await mountWithBooks();

    const first = deferred();
    const second = deferred();
    vi.spyOn(BiblioValidationService, 'validateBiblio')
      .mockReturnValueOnce(first.promise)
      .mockReturnValueOnce(second.promise);

    const run = wrapper.vm.autoValidateAndSendResults();

    first.resolve({
      status: 'verified',
      data: { original: { author: 'Valérie Manteau', title: 'Le Sillon' }, source: 'babelio' },
    });
    await flushPromises();

    expect(rowOf('Le Sillon').find('[data-testid="validation-success"]').exists()).toBe(true);
    expect(livresAuteursService.setValidationResults).not.toHaveBeenCalled();

    second.resolve({ status: 'not_found', data: { original: {} } });
    await run;
    expect(livresAuteursService.setValidationResults).toHaveBeenCalledTimes(1);
  });

  it('distingue la ligne du livre en cours de validation', async () => {
    await mountWithBooks();
    const first = deferred();
    vi.spyOn(BiblioValidationService, 'validateBiblio').mockReturnValueOnce(first.promise);

    const run = wrapper.vm.autoValidateAndSendResults();
    await flushPromises();

    expect(rowOf('Le Sillon').find('[data-testid="validation-loading"]').exists()).toBe(true);
    expect(rowOf('Yoga').find('[data-testid="validation-loading"]').exists()).toBe(false);

    first.resolve({ status: 'not_found', data: { original: {} } });
    await run;
  });

  it('ne lance aucun traitement automatique pendant la boucle', async () => {
    await mountWithBooks();
    // Écarter le traitement groupé lancé par le chargement de l'épisode
    livresAuteursService.autoProcessVerifiedBooks.mockClear();
    vi.spyOn(BiblioValidationService, 'validateBiblio').mockResolvedValue({
      status: 'verified', data: { original: {}, source: 'babelio' },
    });

    await wrapper.vm.autoValidateAndSendResults();
    await flushPromises();

    expect(livresAuteursService.autoProcessVerifiedBooks).not.toHaveBeenCalled();
    expect(livresAuteursService.setValidationResults).toHaveBeenCalledTimes(1);
  });

  it('garde « Bloqué (403) » après le rechargement final, sans l\'enregistrer', async () => {
    await mountWithBooks();
    wrapper.vm.babelioCookieState = 'active';
    vi.spyOn(BiblioValidationService, 'validateBiblio')
      .mockResolvedValueOnce({ status: 'blocked_403', data: { original: {} } })
      .mockResolvedValueOnce({ status: 'not_found', data: { original: {} } });
    // Rechargement final : le backend n'a pas enregistré le 403
    livresAuteursService.getLivresAuteurs.mockResolvedValue([
      { ...makeBooks()[0], status: null },
      { ...makeBooks()[1], status: 'not_found', cache_id: 'c2' },
    ]);

    await wrapper.vm.validateWithBabelio();
    await flushPromises();

    expect(rowOf('Le Sillon').find('[data-testid="validation-blocked-403"]').exists()).toBe(true);
    const sent = livresAuteursService.setValidationResults.mock.calls[0][0].books;
    expect(sent.find((b) => b.titre === 'Le Sillon').validation_status).toBe('blocked_403');
  });

  it('efface les statuts transitoires au lancement d\'une nouvelle validation', async () => {
    await mountWithBooks();
    wrapper.vm.babelioCookieState = 'active';
    wrapper.vm.showLiveResult(wrapper.vm.books[0], 'blocked_403');
    await flushPromises();
    expect(rowOf('Le Sillon').find('[data-testid="validation-blocked-403"]').exists()).toBe(true);

    const first = deferred();
    vi.spyOn(BiblioValidationService, 'validateBiblio').mockReturnValue(first.promise);
    const run = wrapper.vm.validateWithBabelio();
    await flushPromises();

    expect(rowOf('Le Sillon').find('[data-testid="validation-blocked-403"]').exists()).toBe(false);
    first.resolve({ status: 'not_found', data: { original: {} } });
    await run;
  });

  it('traite automatiquement les livres vérifiés une fois enregistrés', async () => {
    await mountWithBooks();
    wrapper.vm.babelioCookieState = 'active';
    vi.spyOn(BiblioValidationService, 'validateBiblio').mockResolvedValue({
      status: 'verified', data: { original: {}, source: 'babelio' },
    });
    livresAuteursService.autoProcessVerifiedBooks.mockResolvedValue({ processed_count: 0 });
    livresAuteursService.getLivresAuteurs.mockResolvedValue([
      { ...makeBooks()[0], status: 'verified', cache_id: 'c1' },
      { ...makeBooks()[1], status: 'verified', cache_id: 'c2' },
    ]);

    await wrapper.vm.validateWithBabelio();
    await flushPromises();

    expect(livresAuteursService.autoProcessVerifiedBooks).toHaveBeenCalledWith('c1');
    expect(livresAuteursService.autoProcessVerifiedBooks).toHaveBeenCalledWith('c2');
  });
});
