/**
 * Tests TDD pour la détection des blocages Babelio 403 et le feedback cookie (Issue #251).
 *
 * Contexte: Issue #247 a ajouté un mécanisme de cookie Babelio (jstsToken) mais
 * sans feedback visible quand Babelio bloque réellement les requêtes (403).
 * Le backend renvoie désormais status='blocked_403' au lieu de 'not_found'
 * quand un blocage anti-bot est détecté.
 *
 * Cette suite vérifie que le frontend :
 * 1. Affiche une bannière d'alerte quand un 403 est détecté
 * 2. Confirme visuellement la sauvegarde du cookie
 * 3. Affiche un badge "probablement expiré" après 5 minutes
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

describe('LivresAuteurs - Détection blocage Babelio 403 (Issue #251)', () => {
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

  describe('Bannière de blocage 403', () => {
    it('ne montre pas la bannière par défaut', async () => {
      await mountPage();
      expect(wrapper.vm.babelioBlocked).toBe(false);
      expect(wrapper.find('[data-test="babelio-blocked-banner"]').exists()).toBe(false);
    });

    it('affiche la bannière quand babelioBlocked est mis à true', async () => {
      await mountPage();
      wrapper.vm.babelioBlocked = true;
      await wrapper.vm.$nextTick();

      const banner = wrapper.find('[data-test="babelio-blocked-banner"]');
      expect(banner.exists()).toBe(true);
      expect(banner.text()).toContain('403');
    });

    it('efface la bannière en sauvegardant un nouveau cookie', async () => {
      await mountPage();
      wrapper.vm.babelioBlocked = true;
      wrapper.vm.babelioCookieInput = 'jstsToken=fresh123; p=FR; disclaimer=1';
      wrapper.vm.saveBabelioCookie();
      await wrapper.vm.$nextTick();

      expect(wrapper.vm.babelioBlocked).toBe(false);
    });
  });

  describe('Confirmation de sauvegarde du cookie', () => {
    it('affiche un message de confirmation après saveBabelioCookie()', async () => {
      await mountPage();
      vi.useFakeTimers();

      wrapper.vm.babelioCookieInput = 'jstsToken=abc123; p=FR; disclaimer=1';
      wrapper.vm.saveBabelioCookie();
      await wrapper.vm.$nextTick();

      expect(wrapper.vm.babelioCookieJustSaved).toBe(true);

      vi.advanceTimersByTime(3100);
      await wrapper.vm.$nextTick();

      expect(wrapper.vm.babelioCookieJustSaved).toBe(false);
    });

    it("n'affiche pas de confirmation si le champ cookie est vide", async () => {
      await mountPage();

      wrapper.vm.babelioCookieInput = '   ';
      wrapper.vm.saveBabelioCookie();
      await wrapper.vm.$nextTick();

      expect(wrapper.vm.babelioCookieJustSaved).toBe(false);
    });
  });

  describe('Badge d\'expiration probable (TTL ~5min)', () => {
    it('ne considère pas le cookie comme expiré juste après sauvegarde', async () => {
      await mountPage();

      wrapper.vm.babelioCookieInput = 'jstsToken=abc123; p=FR; disclaimer=1';
      wrapper.vm.saveBabelioCookie();
      await wrapper.vm.$nextTick();

      expect(wrapper.vm.babelioCookieLikelyExpired).toBe(false);
    });

    it('considère le cookie comme probablement expiré après 5 minutes', async () => {
      await mountPage();

      wrapper.vm.babelioCookieInput = 'jstsToken=abc123; p=FR; disclaimer=1';
      wrapper.vm.saveBabelioCookie();
      await wrapper.vm.$nextTick();

      // babelioCookieLikelyExpired compare Date.now() à babelioCookieSavedAt:
      // on recule artificiellement la date de sauvegarde plutôt que d'avancer
      // une fausse horloge (évite les conflits avec le setTimeout de confirmation).
      wrapper.vm.babelioCookieSavedAt = Date.now() - (5 * 60 * 1000 + 1000);
      await wrapper.vm.$nextTick();

      expect(wrapper.vm.babelioCookieLikelyExpired).toBe(true);
    });

    it('ne marque pas un cookie pré-existant (session précédente) comme expiré sans date connue', async () => {
      sessionStorage.setItem('babelio_cookies', 'jstsToken=old; p=FR; disclaimer=1');
      await mountPage();

      // Pas de babelioCookieSavedAt connu pour ce cookie restauré depuis une session précédente
      expect(wrapper.vm.babelioCookieSavedAt).toBeNull();
      expect(wrapper.vm.babelioCookieLikelyExpired).toBe(false);
    });
  });

  describe('Détection du status blocked_403 lors de la validation', () => {
    it('active babelioBlocked quand autoValidateAndSendResults reçoit status=blocked_403', async () => {
      const mockBooks = [
        {
          episode_oid: '6865f995a1418e3d7c63d076', // pragma: allowlist secret
          auteur: 'Boualem Sansal',
          titre: 'La Légende',
          editeur: 'Grasset',
          validation_status: null,
          programme: false,
        },
      ];

      livresAuteursService.getLivresAuteurs.mockResolvedValue(mockBooks);
      livresAuteursService.setValidationResults.mockResolvedValue({ success: true });

      await mountPage();

      wrapper.vm.books = mockBooks;
      vi.spyOn(BiblioValidationService, 'validateBiblio').mockResolvedValue({
        status: 'blocked_403',
        error_message: 'Babelio a bloqué la requête (403).',
      });

      await wrapper.vm.autoValidateAndSendResults();
      await wrapper.vm.$nextTick();

      expect(wrapper.vm.babelioBlocked).toBe(true);
    });
  });
});
