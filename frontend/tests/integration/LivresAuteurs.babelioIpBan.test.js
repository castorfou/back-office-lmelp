/**
 * Ban IP Babelio détecté par un essai TCP, sans requête HTTP (Issue #351).
 *
 * Un ban IP est un blocage pare-feu : changer le cookie n'y fait rien. Avant
 * « Valider avec Babelio », un essai d'une seconde (POST /api/babelio/probe)
 * arrête tout de suite au lieu d'attendre le timeout de la première requête,
 * et le bandeau dit la vraie cause.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount } from '@vue/test-utils';
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

const EPISODE_ID = '6865f995a1418e3d7c63d076'; // pragma: allowlist secret
const IP_BAN_TEXT = 'Babelio injoignable : IP bannie, inutile de changer le cookie';

describe('LivresAuteurs - ban IP Babelio (Issue #351)', () => {
  let wrapper;
  let router;

  function mockAxios({ reachable = true, status = {} } = {}) {
    axios.get.mockImplementation((url) => {
      if (url.startsWith('/api/babelio/status')) {
        // Cookie actif : sans lui, les boutons Babelio sont grisés (Issue #358)
        return Promise.resolve({
          data: {
            cookie_active: true, cookie_age_sec: 10, cookie_max_age_sec: 300,
            cookie_expired: false, ...status,
          },
        });
      }
      return Promise.resolve({ data: {} });
    });
    axios.post.mockImplementation((url) => {
      if (url === '/api/babelio/probe') {
        return Promise.resolve({
          data: {
            reachable,
            circuit_open: !reachable,
            circuit_reason: reachable ? null : 'connect_timeout',
          },
        });
      }
      return Promise.resolve({ data: {} });
    });
  }

  beforeEach(async () => {
    vi.resetAllMocks();
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
    livresAuteursService.getEpisodesWithReviews.mockResolvedValue([]);
    livresAuteursService.getLivresAuteurs.mockResolvedValue([]);
  });

  afterEach(() => {
    if (wrapper) wrapper.unmount();
    sessionStorage.clear();
  });

  async function mountPage() {
    wrapper = mount(LivresAuteurs, { global: { plugins: [router] } });
    await wrapper.vm.$nextTick();
    await new Promise((resolve) => setTimeout(resolve, 20));
    wrapper.vm.selectedEpisodeId = EPISODE_ID;
    // Laisser le panneau cookie s'afficher et transmettre l'état du cookie
    await wrapper.vm.$nextTick();
    await new Promise((resolve) => setTimeout(resolve, 20));
    return wrapper;
  }

  it('arrête la validation si Babelio est injoignable, sans aucune requête Babelio', async () => {
    mockAxios({ reachable: false });
    await mountPage();
    livresAuteursService.getLivresAuteurs.mockClear();
    const validate = vi.spyOn(BiblioValidationService, 'validateBiblio');

    await wrapper.vm.validateWithBabelio();
    await wrapper.vm.$nextTick();

    expect(axios.post).toHaveBeenCalledWith('/api/babelio/probe');
    expect(livresAuteursService.getLivresAuteurs).not.toHaveBeenCalled();
    expect(validate).not.toHaveBeenCalled();
    expect(wrapper.vm.validatingWithBabelio).toBe(false);
    const banner = wrapper.find('[data-test="babelio-blocked-banner"]');
    expect(banner.exists()).toBe(true);
    expect(banner.text()).toContain(IP_BAN_TEXT);
    expect(banner.text()).not.toContain('403');
  });

  it("n'ouvre pas le panneau cookie pour un ban IP", async () => {
    mockAxios({ reachable: false });
    await mountPage();
    wrapper.vm.cookiePanelOpen = false;

    await wrapper.vm.validateWithBabelio();
    await wrapper.vm.$nextTick();

    expect(wrapper.vm.cookiePanelOpen).toBe(false);
  });

  it('poursuit la validation si Babelio est joignable', async () => {
    mockAxios({ reachable: true });
    await mountPage();
    livresAuteursService.getLivresAuteurs.mockClear();

    await wrapper.vm.validateWithBabelio();

    expect(axios.post).toHaveBeenCalledWith('/api/babelio/probe');
    // Validation puis rechargement des statuts (Issue #352 : plus d'enrichissement)
    expect(livresAuteursService.getLivresAuteurs).toHaveBeenCalledWith({ episode_oid: EPISODE_ID });
    expect(wrapper.find('[data-test="babelio-blocked-banner"]').exists()).toBe(false);
  });

  it('affiche le bandeau ban IP quand le disjoncteur a été ouvert par un timeout de connexion', async () => {
    mockAxios({ status: { circuit_open: true, circuit_reason: 'connect_timeout' } });
    await mountPage();

    wrapper.vm.babelioBlocked = true;
    await new Promise((resolve) => setTimeout(resolve, 0));
    await wrapper.vm.$nextTick();

    const banner = wrapper.find('[data-test="babelio-blocked-banner"]');
    expect(banner.text()).toContain(IP_BAN_TEXT);
  });

  it('garde le bandeau 403 quand le disjoncteur a été ouvert par un 403', async () => {
    mockAxios({ status: { circuit_open: true, circuit_reason: 'http_403' } });
    await mountPage();

    wrapper.vm.babelioBlocked = true;
    await new Promise((resolve) => setTimeout(resolve, 0));
    await wrapper.vm.$nextTick();

    const banner = wrapper.find('[data-test="babelio-blocked-banner"]');
    expect(banner.text()).toContain('403');
    expect(banner.text()).not.toContain(IP_BAN_TEXT);
  });

  // Issue #357 : 403 « Vérification de sécurité » d'un cookie anonyme
  it('affiche le bandeau vérification humaine quand le disjoncteur a été ouvert par un captcha', async () => {
    mockAxios({ status: { circuit_open: true, circuit_reason: 'captcha' } });
    await mountPage();

    wrapper.vm.babelioBlocked = true;
    await new Promise((resolve) => setTimeout(resolve, 0));
    await wrapper.vm.$nextTick();

    const banner = wrapper.find('[data-test="babelio-blocked-banner"]');
    expect(banner.text()).toContain('Babelio demande une vérification humaine : connectez-vous à Babelio, puis collez un nouveau cookie');
    expect(banner.text()).not.toContain('probablement expiré');
    // Un nouveau cookie (après connexion) règle le problème : panneau ouvert
    expect(wrapper.vm.cookiePanelOpen).toBe(true);
  });
});
