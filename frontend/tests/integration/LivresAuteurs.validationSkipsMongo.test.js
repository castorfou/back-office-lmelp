/**
 * « Relancer la validation » ne défait jamais un livre déjà en base (Issue #383) :
 * la validation Babelio ne repasse que les livres sans statut définitif.
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

describe('LivresAuteurs - validation Babelio limitée aux livres à valider (Issue #383)', () => {
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
    livresAuteursService.setValidationResults.mockResolvedValue({ success: true });
    wrapper = mount(LivresAuteurs, { global: { plugins: [router] } });
    await flushPromises();
    wrapper.vm.selectedEpisodeId = EPISODE_OID;
    wrapper.vm.books = makeBooks();
    await flushPromises();
    return wrapper;
  }

  it('ne revalide pas un livre déjà en base', async () => {
    await mountWithBooks();
    wrapper.vm.books = [
      { ...makeBooks()[0], status: 'mongo', cache_id: 'c1' },
      makeBooks()[1],
    ];
    await flushPromises();
    const spy = vi.spyOn(BiblioValidationService, 'validateBiblio').mockResolvedValue({
      status: 'not_found', data: { original: {} },
    });

    await wrapper.vm.autoValidateAndSendResults();

    expect(spy).toHaveBeenCalledTimes(1);
    expect(spy).toHaveBeenCalledWith('Emmanuel Carrère', 'Yoga', 'POL', EPISODE_OID);
    const sent = livresAuteursService.setValidationResults.mock.calls[0][0].books;
    expect(sent.map((b) => b.titre)).toEqual(['Yoga']);
    expect(wrapper.vm.books[0].status).toBe('mongo');
  });
});
