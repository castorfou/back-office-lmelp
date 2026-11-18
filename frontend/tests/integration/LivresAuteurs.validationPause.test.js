/**
 * Pause de validation (Issue #352) : quand le cookie Babelio expire pendant
 * « Valider avec Babelio », la validation s'arrête sans rien envoyer, reprend
 * au livre interrompu dès qu'un cookie actif est enregistré, ou s'arrête sur
 * « Arrêter » en enregistrant les résultats déjà obtenus.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { createRouter, createWebHistory } from 'vue-router';
import axios from 'axios';
import LivresAuteurs from '../../src/views/LivresAuteurs.vue';
import { livresAuteursService } from '../../src/services/api.js';
import BiblioValidationService from '../../src/services/BiblioValidationService.js';

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
    fetchEpisodePageUrl: vi.fn(),
  },
  statisticsService: { getStatistics: vi.fn() },
  babelioService: { verifyAuthor: vi.fn(), verifyBook: vi.fn(), verifyPublisher: vi.fn() },
  fuzzySearchService: { searchEpisode: vi.fn() },
}));

const EPISODE_OID = '6865f995a1418e3d7c63d076'; // pragma: allowlist secret

const makeBooks = () => [
  { episode_oid: EPISODE_OID, auteur: 'Valérie Manteau', titre: 'Le Sillon', editeur: 'Le Tripode', programme: true },
  { episode_oid: EPISODE_OID, auteur: 'Emmanuel Carrère', titre: 'Yoga', editeur: 'POL', programme: true },
];

// Résultats réels de validateBiblio (BiblioValidationService)
const verified = { status: 'verified', data: { original: {}, source: 'babelio' } };
const notFound = { status: 'not_found', data: { original: {}, reason: 'no_reliable_match_found' } };
const cookieExpired = { status: 'blocked_403', data: { original: {}, reason: 'cookie_expired' } };
const babelio403 = { status: 'blocked_403', data: { original: {}, reason: 'babelio_blocked_403' } };

const activeStatus = { cookie_active: true, cookie_age_sec: 10, cookie_max_age_sec: 300, cookie_expired: false };

describe('LivresAuteurs - pause de validation (Issue #352)', () => {
  let wrapper;
  let validate;

  beforeEach(async () => {
    vi.resetAllMocks();
    sessionStorage.clear();
    axios.get.mockImplementation((url) => {
      if (url.startsWith('/api/babelio/status')) return Promise.resolve({ data: activeStatus });
      return Promise.resolve({ data: {} });
    });
    axios.post.mockImplementation((url) => {
      if (url === '/api/babelio/probe') {
        return Promise.resolve({ data: { reachable: true, circuit_open: false, circuit_reason: null } });
      }
      return Promise.resolve({ data: {} });
    });
    livresAuteursService.getEpisodesWithReviews.mockResolvedValue([
      { id: EPISODE_OID, titre: 'Episode test', date: '2025-06-29', review_count: 1 },
    ]);
    livresAuteursService.getLivresAuteurs.mockImplementation(async () => makeBooks());
    livresAuteursService.setValidationResults.mockResolvedValue({ success: true });
    livresAuteursService.autoProcessVerifiedBooks.mockResolvedValue({ processed_count: 0 });
    validate = vi.spyOn(BiblioValidationService, 'validateBiblio');

    const router = createRouter({
      history: createWebHistory(),
      routes: [
        { path: '/', component: { template: '<div />' } },
        { path: '/livres-auteurs', component: LivresAuteurs },
      ],
    });
    await router.push('/livres-auteurs');
    wrapper = mount(LivresAuteurs, { global: { plugins: [router] } });
    await flushPromises();
    wrapper.vm.selectedEpisodeId = EPISODE_OID;
    wrapper.vm.books = makeBooks();
    await flushPromises();
    wrapper.vm.babelioCookieState = 'active';
  });

  afterEach(() => {
    wrapper?.unmount();
    vi.restoreAllMocks();
  });

  const button = () => wrapper.find('[data-test="validate-babelio-button"]');
  const sentBooks = () => livresAuteursService.setValidationResults.mock.calls[0][0].books;

  it('se met en pause sur un cookie expiré, puis reprend au livre interrompu', async () => {
    validate
      .mockResolvedValueOnce(verified)
      .mockResolvedValueOnce(cookieExpired)
      .mockResolvedValueOnce(notFound);

    const run = wrapper.vm.validateWithBabelio();
    await flushPromises();

    expect(wrapper.vm.babelioValidationPaused).toBe(true);
    expect(button().text()).toContain('En pause');
    expect(button().text()).toContain('2/2');
    expect(validate).toHaveBeenCalledTimes(2);
    expect(livresAuteursService.setValidationResults).not.toHaveBeenCalled();

    // Cookie frais enregistré depuis le panneau
    await wrapper.vm.onBabelioCookieSaved();
    await run;

    expect(validate).toHaveBeenCalledTimes(3);
    expect(validate.mock.calls[2][1]).toBe('Yoga');
    expect(sentBooks().map((b) => b.validation_status)).toEqual(['verified', 'not_found']);
  });

  it('se met en pause avant un livre si le cookie local a déjà expiré, sans rien envoyer', async () => {
    let resolveFirst;
    validate.mockImplementationOnce(() => new Promise((r) => { resolveFirst = r; }));

    const run = wrapper.vm.validateWithBabelio();
    await flushPromises();
    wrapper.vm.babelioCookieState = 'expired';
    resolveFirst(verified);
    await flushPromises();

    expect(wrapper.vm.babelioValidationPaused).toBe(true);
    expect(validate).toHaveBeenCalledTimes(1);

    wrapper.vm.stopBabelioValidation();
    await run;
  });

  it('« Arrêter » enregistre les résultats déjà obtenus et laisse le reste à valider', async () => {
    validate.mockResolvedValueOnce(verified).mockResolvedValueOnce(cookieExpired);

    const run = wrapper.vm.validateWithBabelio();
    await flushPromises();
    await wrapper.find('[data-test="stop-babelio-validation"]').trigger('click');
    await run;
    await flushPromises();

    expect(validate).toHaveBeenCalledTimes(2);
    expect(sentBooks().map((b) => b.titre)).toEqual(['Le Sillon']);
    expect(wrapper.vm.babelioValidationPaused).toBe(false);
    expect(wrapper.vm.validatingWithBabelio).toBe(false);
  });

  it('un vrai 403 de Babelio ne met pas la validation en pause', async () => {
    validate.mockResolvedValueOnce(babelio403).mockResolvedValueOnce(notFound);

    await wrapper.vm.validateWithBabelio();

    expect(wrapper.vm.babelioValidationPaused).toBe(false);
    expect(sentBooks().map((b) => b.validation_status)).toEqual(['blocked_403', 'not_found']);
  });

  it('désactive le changement d\'épisode pendant la validation', async () => {
    let resolveFirst;
    validate.mockImplementationOnce(() => new Promise((r) => { resolveFirst = r; }));

    const run = wrapper.vm.validateWithBabelio();
    await flushPromises();

    expect(wrapper.findComponent({ name: 'EpisodeDropdown' }).props('disabled')).toBe(true);
    expect(wrapper.find('[data-testid="prev-episode-button"]').attributes('disabled')).toBeDefined();
    expect(wrapper.find('[data-testid="next-episode-button"]').attributes('disabled')).toBeDefined();

    resolveFirst(verified);
    validate.mockResolvedValueOnce(notFound);
    await run;
    await flushPromises();
    expect(wrapper.findComponent({ name: 'EpisodeDropdown' }).props('disabled')).toBe(false);
  });

  it('affiche le temps restant du cookie dans le libellé de progression', async () => {
    let resolveFirst;
    validate.mockImplementationOnce(() => new Promise((r) => { resolveFirst = r; }));
    wrapper.vm.babelioCookieRemaining = '~2 min';

    const run = wrapper.vm.validateWithBabelio();
    await flushPromises();

    expect(button().text()).toContain('Validation 1/2');
    expect(button().text()).toContain('cookie ~2 min');

    resolveFirst(verified);
    validate.mockResolvedValueOnce(notFound);
    await run;
  });

  it('reprend dès que le cookie local redevient actif', async () => {
    let resolveFirst;
    validate.mockImplementationOnce(() => new Promise((r) => { resolveFirst = r; }));
    validate.mockResolvedValueOnce(notFound);

    const run = wrapper.vm.validateWithBabelio();
    await flushPromises();
    wrapper.vm.babelioCookieState = 'expired';
    resolveFirst(verified);
    await flushPromises();
    expect(wrapper.vm.babelioValidationPaused).toBe(true);

    wrapper.vm.babelioCookieState = 'active';
    await run;

    expect(validate).toHaveBeenCalledTimes(2);
    expect(sentBooks().map((b) => b.validation_status)).toEqual(['verified', 'not_found']);
  });

  it('quitter la page arrête la validation sans rien envoyer', async () => {
    let resolveFirst;
    validate.mockImplementationOnce(() => new Promise((r) => { resolveFirst = r; }));

    const run = wrapper.vm.validateWithBabelio();
    await flushPromises();
    wrapper.unmount();
    resolveFirst(verified);
    await run;
    wrapper = null;

    expect(validate).toHaveBeenCalledTimes(1);
    expect(livresAuteursService.setValidationResults).not.toHaveBeenCalled();
  });

  it('quitter la page pendant une pause n\'envoie rien', async () => {
    validate.mockResolvedValueOnce(verified).mockResolvedValueOnce(cookieExpired);

    const run = wrapper.vm.validateWithBabelio();
    await flushPromises();
    expect(wrapper.vm.babelioValidationPaused).toBe(true);
    wrapper.unmount();
    await run;
    wrapper = null;

    expect(livresAuteursService.setValidationResults).not.toHaveBeenCalled();
  });
});
