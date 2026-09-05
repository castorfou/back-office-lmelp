/**
 * Tests d'intégration pour la page d'accueil (Dashboard)
 *
 * Issue #279: les statistiques sont chargées via un seul appel agrégé
 * GET /api/dashboard/stats (mis en cache côté backend), plus un bouton
 * "Actualiser" qui invalide le cache avant de recharger.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount } from '@vue/test-utils';
import { createRouter, createWebHistory } from 'vue-router';
import Dashboard from '../../src/views/Dashboard.vue';
import axios from 'axios';

vi.mock('axios');

// Issue #279: Dashboard.vue n'utilise plus statisticsService/livresAuteursService
// (remplacés par un seul GET /api/dashboard/stats), mais le mock reste nécessaire
// tant que api.js (import via axios.create()) est importé ailleurs dans l'app.
vi.mock('../../src/services/api.js', () => ({
  statisticsService: { getStatistics: vi.fn() },
  livresAuteursService: { getCollectionsStatistics: vi.fn() }
}));

// Mock des utilitaires
vi.mock('../../src/utils/memoryGuard.js', () => ({
  memoryGuard: {
    checkMemoryLimit: vi.fn().mockReturnValue(null),
    forceShutdown: vi.fn(),
    startMonitoring: vi.fn(),
    stopMonitoring: vi.fn()
  }
}));

describe('Dashboard - Tests d\'intégration', () => {
  let wrapper;
  let router;

  const mockStatistics = {
    totalEpisodes: 142,
    maskedEpisodes: 5,
    episodesWithCorrectedTitles: 37,
    episodesWithCorrectedDescriptions: 45,
    criticalReviews: 28,
    lastUpdateDate: '2025-09-06T10:30:00Z'
  };

  const mockCollectionsStatistics = {
    episodes_non_traites: 5,
    couples_en_base: 42,
    couples_suggested_pas_en_base: 12,
    couples_not_found_pas_en_base: 8,
    // Issue #128: Nouvelles métriques
    episodes_without_avis_critiques: 117,
    avis_critiques_without_analysis: 0,
    last_episode_date: '2024-12-10T20:00:00',
    books_without_url_babelio: 5,
    authors_without_url_babelio: 3
  };

  function buildDashboardStatsPayload(overrides = {}) {
    return {
      statistics: mockStatistics,
      collections_statistics: mockCollectionsStatistics,
      critiques_manquants_count: 0,
      duplicate_books_count: 0,
      duplicate_authors_count: 0,
      orphaned_avis_count: 0,
      ...overrides
    };
  }

  function mockDashboardStats(payload) {
    axios.get.mockImplementation((url) => {
      if (url === '/api/dashboard/stats') {
        return Promise.resolve({ data: payload });
      }
      if (url === '/api/version') {
        return Promise.resolve({ data: {} });
      }
      if (url === '/api/dashboard/stats/cache/invalidate') {
        return Promise.reject(new Error(`GET non attendu sur ${url}`));
      }
      return Promise.reject(new Error(`URL non mockée: ${url}`));
    });
    axios.post.mockImplementation((url) => {
      if (url === '/api/dashboard/stats/cache/invalidate') {
        return Promise.resolve({ data: { status: 'ok' } });
      }
      return Promise.reject(new Error(`POST non mocké: ${url}`));
    });
  }

  beforeEach(async () => {
    vi.clearAllMocks();
    mockDashboardStats(buildDashboardStatsPayload());

    // Créer un router de test
    router = createRouter({
      history: createWebHistory(),
      routes: [
        { path: '/', component: Dashboard },
        { path: '/episodes', component: { template: '<div>Episodes Page</div>' } }
      ]
    });

    // Naviguer vers la page d'accueil
    await router.push('/');
  });

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount();
    }
  });

  it('affiche le titre et la description de la page d\'accueil', async () => {
    wrapper = mount(Dashboard, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();

    expect(wrapper.find('h1').text()).toBe('Back-office LMELP');
    expect(wrapper.text()).toContain('Gestion et correction des épisodes du Masque et la Plume');
  });

  it('affiche le bandeau d\'en-tête avec le bon style', async () => {
    wrapper = mount(Dashboard, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();

    const header = wrapper.find('.page-header');
    expect(header.exists()).toBe(true);
    expect(header.find('h1').text()).toBe('Back-office LMELP');
  });

  it('affiche la fonction Episode - Modification Titre/Description comme cliquable', async () => {
    wrapper = mount(Dashboard, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();

    const episodeFunction = wrapper.find('[data-testid="function-episode-edit"]');
    expect(episodeFunction.exists()).toBe(true);
    expect(episodeFunction.text()).toContain('Episode - Modification Titre/Description');

    // Vérifier que c'est cliquable
    expect(episodeFunction.element.tagName.toLowerCase()).toMatch(/^(a|button|div)$/);
  });

  it('limite la largeur de la grille Contrôle Babelio car elle ne contient qu\'une seule tuile (Issue #269)', async () => {
    wrapper = mount(Dashboard, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();

    const babelioCard = wrapper.find('[data-testid="function-babelio-control"]');
    const babelioGrid = babelioCard.element.closest('.functions-grid');

    expect(babelioGrid.classList.contains('functions-grid--single')).toBe(true);
  });

  it('navigue vers la page d\'épisodes lors du clic sur la fonction', async () => {
    const push = vi.spyOn(router, 'push');

    wrapper = mount(Dashboard, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();

    const episodeFunction = wrapper.find('[data-testid="function-episode-edit"]');
    await episodeFunction.trigger('click');

    expect(push).toHaveBeenCalledWith('/episodes');
  });

  it('est responsive sur petits écrans', async () => {
    wrapper = mount(Dashboard, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();

    // Vérifier qu'il y a des classes CSS pour la responsivité
    const dashboard = wrapper.find('.dashboard');
    expect(dashboard.exists()).toBe(true);

    // Vérifier que les styles responsive existent (au moins une règle @media dans le style)
    const style = wrapper.find('style');
    if (style.exists()) {
      const styleText = style.element.textContent;
      expect(styleText).toMatch(/@media.*max-width.*768px/);
    }
  });

  // ========== TESTS TDD POUR LES STATISTIQUES AGRÉGÉES (Issue #279) ==========

  it('appelle GET /api/dashboard/stats une seule fois au montage du composant', async () => {
    wrapper = mount(Dashboard, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 50));

    const dashboardStatsCalls = axios.get.mock.calls.filter(
      ([url]) => url === '/api/dashboard/stats'
    );
    expect(dashboardStatsCalls).toHaveLength(1);
  });

  it('affiche les statistiques des collections dans les cartes existantes', async () => {
    wrapper = mount(Dashboard, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 50));

    // Vérifier que les valeurs des collections sont affichées (Issue #128)
    expect(wrapper.text()).toContain('12'); // couples_suggested_pas_en_base
    expect(wrapper.text()).toContain('8');  // couples_not_found_pas_en_base
    expect(wrapper.text()).toContain('117'); // episodes_without_avis_critiques
    // Note: avis_critiques_without_analysis=0 is hidden (Issue #212)
  });

  it('affiche les libellés des statistiques des collections (Issue #128)', async () => {
    wrapper = mount(Dashboard, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 50));

    // Vérifier que les nouveaux libellés Issue #128 sont présents (avec valeurs non-zéro dans le mock)
    expect(wrapper.text()).toMatch(/livres.*suggérés/i);
    expect(wrapper.text()).toMatch(/livres.*non.*trouvés/i);
    expect(wrapper.text()).toMatch(/épisodes.*sans.*avis.*critiques/i);
    // Note: avis_critiques_without_analysis=0 dans le mock → carte masquée (Issue #212)
    expect(wrapper.text()).not.toMatch(/avis.*critiques.*sans.*analyse/i);
    expect(wrapper.text()).toMatch(/livres.*sans.*lien.*babelio/i);
    expect(wrapper.text()).toMatch(/auteurs.*sans.*lien.*babelio/i);
  });

  it('gère les erreurs de chargement des statistiques dashboard', async () => {
    axios.get.mockImplementation((url) => {
      if (url === '/api/dashboard/stats') {
        return Promise.reject(new Error('Erreur réseau'));
      }
      if (url === '/api/version') {
        return Promise.resolve({ data: {} });
      }
      return Promise.reject(new Error(`URL non mockée: ${url}`));
    });

    wrapper = mount(Dashboard, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 50));

    // Les statistiques doivent afficher des valeurs par défaut
    expect(wrapper.text()).toContain('--');
  });

  it('affiche des indicateurs de chargement pour les statistiques', async () => {
    let resolveDashboardStats;
    const dashboardStatsPromise = new Promise(resolve => {
      resolveDashboardStats = resolve;
    });
    axios.get.mockImplementation((url) => {
      if (url === '/api/dashboard/stats') {
        return dashboardStatsPromise;
      }
      if (url === '/api/version') {
        return Promise.resolve({ data: {} });
      }
      return Promise.reject(new Error(`URL non mockée: ${url}`));
    });

    wrapper = mount(Dashboard, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();

    // Vérifier qu'un état de chargement est affiché
    expect(wrapper.text()).toContain('...'); // Loading indicator

    // Résoudre les statistiques
    resolveDashboardStats({ data: buildDashboardStatsPayload() });
    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 50));

    // Vérifier que les données sont maintenant affichées (Issue #128)
    expect(wrapper.text()).toContain('117'); // episodes_without_avis_critiques
  });

  // ========== TESTS TDD POUR ISSUE #128 - NOUVELLES MÉTRIQUES ==========

  it('affiche "Avis critiques sans analyse" (Issue #128)', async () => {
    wrapper = mount(Dashboard, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 50));

    // Test TDD: "Avis critiques sans analyse" masquée si valeur=0 (Issue #212)
    expect(wrapper.text()).not.toMatch(/avis.*critiques.*sans.*analyse/i);

    // Test TDD: "Livres vérifiés" NE DOIT PAS être présent
    expect(wrapper.text()).not.toMatch(/livres.*vérifiés/i);
  });

  it('affiche "Épisodes sans avis critiques" (Issue #128)', async () => {
    wrapper = mount(Dashboard, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 50));

    expect(wrapper.text()).toMatch(/épisodes.*sans.*avis.*critiques/i);
    expect(wrapper.text()).toContain('117');
  });

  it('gère l\'absence de nouvelles métriques Issue #128 dans la réponse API', async () => {
    const incompleteCollectionsStats = {
      episodes_non_traites: 5,
      couples_en_base: 42,
      couples_suggested_pas_en_base: 12,
      couples_not_found_pas_en_base: 8
      // Nouvelles métriques Issue #128 manquantes volontairement
    };

    mockDashboardStats(
      buildDashboardStatsPayload({ collections_statistics: incompleteCollectionsStats })
    );

    wrapper = mount(Dashboard, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 50));

    // Test TDD: Doit afficher '...' quand les nouvelles métriques sont absentes
    const text = wrapper.text();
    expect(text).toMatch(/avis.*critiques.*sans.*analyse/i);
    expect(text).toMatch(/épisodes.*sans.*avis.*critiques/i);

    const statCards = wrapper.findAll('.stat-card');
    let foundAvisCritiquesCard = false;
    let foundEpisodesCard = false;

    for (let card of statCards) {
      const cardText = card.text();
      if (cardText.includes('Avis critiques sans analyse')) {
        expect(cardText).toContain('...');
        foundAvisCritiquesCard = true;
      }
      if (cardText.includes('Épisodes sans avis critiques')) {
        expect(cardText).toContain('...');
        foundEpisodesCard = true;
      }
    }

    expect(foundAvisCritiquesCard).toBe(true);
    expect(foundEpisodesCard).toBe(true);
  });

  // ========== TESTS TDD POUR ISSUE #212 - MASQUER STATS À 0 ==========

  it('masque les cartes de statistiques dont la valeur est 0 (Issue #212)', async () => {
    const statsWithZeros = {
      episodes_non_traites: 5,
      couples_en_base: 42,
      couples_suggested_pas_en_base: 0,
      couples_not_found_pas_en_base: 0,
      episodes_without_avis_critiques: 117,
      avis_critiques_without_analysis: 0,
      last_episode_date: '2024-12-10T20:00:00',
      books_without_url_babelio: 0,
      authors_without_url_babelio: 0,
      emissions_sans_avis: 0,
      emissions_with_problems: 0
    };

    mockDashboardStats(
      buildDashboardStatsPayload({ collections_statistics: statsWithZeros })
    );

    wrapper = mount(Dashboard, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 50));

    // Les cartes avec valeur 0 ne doivent PAS être rendues
    const statCards = wrapper.findAll('.stat-card');
    const cardLabels = statCards.map(card => card.text());

    expect(cardLabels.some(t => t.includes('Livres suggérés'))).toBe(false);
    expect(cardLabels.some(t => t.includes('Livres non trouvés'))).toBe(false);
    expect(cardLabels.some(t => t.includes('Avis critiques sans analyse'))).toBe(false);
    expect(cardLabels.some(t => t.includes('Livres sans lien Babelio'))).toBe(false);
    expect(cardLabels.some(t => t.includes('Auteurs sans lien Babelio'))).toBe(false);
    expect(cardLabels.some(t => t.includes('Émissions sans avis'))).toBe(false);
    expect(cardLabels.some(t => t.includes('Émissions avec problème'))).toBe(false);

    // Les cartes avec valeur non-zéro DOIVENT être présentes
    expect(cardLabels.some(t => t.includes('Épisodes sans avis critiques'))).toBe(true);

    // La carte "Dernière mise à jour" doit toujours être visible
    expect(cardLabels.some(t => t.includes('Dernière mise à jour'))).toBe(true);
  });

  it('affiche les cartes de statistiques dont la valeur est non-zéro (Issue #212)', async () => {
    const statsAllNonZero = {
      episodes_non_traites: 5,
      couples_en_base: 42,
      couples_suggested_pas_en_base: 12,
      couples_not_found_pas_en_base: 8,
      episodes_without_avis_critiques: 117,
      avis_critiques_without_analysis: 3,
      last_episode_date: '2024-12-10T20:00:00',
      books_without_url_babelio: 5,
      authors_without_url_babelio: 3,
      emissions_sans_avis: 2,
      emissions_with_problems: 1
    };

    mockDashboardStats(
      buildDashboardStatsPayload({ collections_statistics: statsAllNonZero })
    );

    wrapper = mount(Dashboard, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 50));

    const statCards = wrapper.findAll('.stat-card');
    const cardLabels = statCards.map(card => card.text());

    expect(cardLabels.some(t => t.includes('Livres suggérés'))).toBe(true);
    expect(cardLabels.some(t => t.includes('Livres non trouvés'))).toBe(true);
    expect(cardLabels.some(t => t.includes('Avis critiques sans analyse'))).toBe(true);
    expect(cardLabels.some(t => t.includes('Livres sans lien Babelio'))).toBe(true);
    expect(cardLabels.some(t => t.includes('Auteurs sans lien Babelio'))).toBe(true);
    expect(cardLabels.some(t => t.includes('Émissions sans avis'))).toBe(true);
    expect(cardLabels.some(t => t.includes('Émissions avec problème'))).toBe(true);
    expect(cardLabels.some(t => t.includes('Épisodes sans avis critiques'))).toBe(true);
    expect(cardLabels.some(t => t.includes('Dernière mise à jour'))).toBe(true);
  });

  it('affiche les cartes en chargement (null) même si valeur finale sera 0 (Issue #212)', async () => {
    let resolveDashboardStats;
    const dashboardStatsPromise = new Promise(resolve => {
      resolveDashboardStats = resolve;
    });
    axios.get.mockImplementation((url) => {
      if (url === '/api/dashboard/stats') {
        return dashboardStatsPromise;
      }
      if (url === '/api/version') {
        return Promise.resolve({ data: {} });
      }
      return Promise.reject(new Error(`URL non mockée: ${url}`));
    });

    wrapper = mount(Dashboard, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();

    // Pendant le chargement (valeurs null), les cartes doivent être visibles avec '...'
    const statCards = wrapper.findAll('.stat-card');
    const cardLabels = statCards.map(card => card.text());

    expect(cardLabels.some(t => t.includes('Livres suggérés'))).toBe(true);
    expect(cardLabels.some(t => t.includes('Avis critiques sans analyse'))).toBe(true);
    expect(cardLabels.some(t => t.includes('...'))).toBe(true);
  });

  // ========== TESTS TDD POUR LE BOUTON "ACTUALISER" (Issue #279) ==========

  it('affiche un bouton "Actualiser" dans la section statistiques', async () => {
    wrapper = mount(Dashboard, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 50));

    const refreshButton = wrapper.find('[data-test="dashboard-refresh-button"]');
    expect(refreshButton.exists()).toBe(true);
    expect(refreshButton.text()).toBe('Actualiser');
  });

  it('invalide le cache puis recharge les stats au clic sur "Actualiser"', async () => {
    wrapper = mount(Dashboard, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 50));

    axios.get.mockClear();
    axios.post.mockClear();

    const refreshButton = wrapper.find('[data-test="dashboard-refresh-button"]');
    await refreshButton.trigger('click');
    await new Promise(resolve => setTimeout(resolve, 50));

    expect(axios.post).toHaveBeenCalledWith('/api/dashboard/stats/cache/invalidate');
    expect(axios.get).toHaveBeenCalledWith('/api/dashboard/stats');
  });

  it('désactive le bouton "Actualiser" pendant le rafraîchissement', async () => {
    wrapper = mount(Dashboard, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 50));

    let resolveInvalidate;
    axios.post.mockImplementation(() => new Promise(resolve => {
      resolveInvalidate = resolve;
    }));

    const refreshButton = wrapper.find('[data-test="dashboard-refresh-button"]');
    await refreshButton.trigger('click');
    await wrapper.vm.$nextTick();

    expect(wrapper.find('[data-test="dashboard-refresh-button"]').attributes('disabled')).toBeDefined();
    expect(wrapper.find('[data-test="dashboard-refresh-button"]').text()).toBe('Actualisation…');

    resolveInvalidate({ data: { status: 'ok' } });
    await new Promise(resolve => setTimeout(resolve, 50));
    await wrapper.vm.$nextTick();

    expect(wrapper.find('[data-test="dashboard-refresh-button"]').attributes('disabled')).toBeUndefined();
  });
});

describe('Dashboard - URL front-office lmelp dynamique (Issue #265)', () => {
  let wrapper;
  let router;
  const originalLocation = window.location;

  function setHostname(hostname) {
    delete window.location;
    window.location = { ...originalLocation, hostname };
  }

  const mockStatistics = {
    totalEpisodes: 142,
    maskedEpisodes: 5,
    episodesWithCorrectedTitles: 37,
    episodesWithCorrectedDescriptions: 45,
    criticalReviews: 28,
    lastUpdateDate: '2025-09-06T10:30:00Z'
  };

  const mockCollectionsStatistics = {
    episodes_non_traites: 5,
    couples_en_base: 42,
    couples_suggested_pas_en_base: 12,
    couples_not_found_pas_en_base: 8,
    episodes_without_avis_critiques: 117,
    avis_critiques_without_analysis: 0,
    last_episode_date: '2024-12-10T20:00:00',
    books_without_url_babelio: 5,
    authors_without_url_babelio: 3
  };

  beforeEach(async () => {
    vi.clearAllMocks();

    axios.get.mockImplementation((url) => {
      if (url === '/api/dashboard/stats') {
        return Promise.resolve({
          data: {
            statistics: mockStatistics,
            collections_statistics: mockCollectionsStatistics,
            critiques_manquants_count: 0,
            duplicate_books_count: 0,
            duplicate_authors_count: 0,
            orphaned_avis_count: 0
          }
        });
      }
      if (url === '/api/version') {
        return Promise.resolve({ data: {} });
      }
      return Promise.reject(new Error(`URL non mockée: ${url}`));
    });

    router = createRouter({
      history: createWebHistory(),
      routes: [
        { path: '/', component: Dashboard },
        { path: '/episodes', component: { template: '<div>Episodes Page</div>' } }
      ]
    });

    await router.push('/');
  });

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount();
    }
    window.location = originalLocation;
  });

  it('pointe vers localhost:8501 quand le back-office est accédé via localhost', async () => {
    setHostname('localhost');

    wrapper = mount(Dashboard, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();

    expect(wrapper.vm.lmelpFrontOfficeUrl).toBe('http://localhost:8501/');
  });

  it('pointe vers le domaine front-office sans le suffixe -bo quand le back-office est accédé via un nom de domaine', async () => {
    setHostname('lmelp-bo.ascot63.synology.me');

    wrapper = mount(Dashboard, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();

    expect(wrapper.vm.lmelpFrontOfficeUrl).toBe('https://lmelp.ascot63.synology.me/');

    const tile = wrapper.find('.clickable-stat');
    expect(tile.attributes('href')).toBe('https://lmelp.ascot63.synology.me/');
  });
});

describe('Dashboard - Tuile Avis orphelins (Issue #271)', () => {
  let wrapper;
  let router;

  const mockStatistics = {
    totalEpisodes: 142,
    maskedEpisodes: 5,
    episodesWithCorrectedTitles: 37,
    episodesWithCorrectedDescriptions: 45,
    criticalReviews: 28,
    lastUpdateDate: '2025-09-06T10:30:00Z'
  };

  const mockCollectionsStatistics = {
    episodes_non_traites: 5,
    couples_en_base: 42,
    couples_suggested_pas_en_base: 0,
    couples_not_found_pas_en_base: 0,
    episodes_without_avis_critiques: 0,
    avis_critiques_without_analysis: 0,
    last_episode_date: '2024-12-10T20:00:00',
    books_without_url_babelio: 0,
    authors_without_url_babelio: 0,
    emissions_sans_avis: 0,
    emissions_with_problems: 0
  };

  function mockAxiosGet(orphanedCount) {
    axios.get.mockImplementation((url) => {
      if (url === '/api/dashboard/stats') {
        return Promise.resolve({
          data: {
            statistics: mockStatistics,
            collections_statistics: mockCollectionsStatistics,
            critiques_manquants_count: 0,
            duplicate_books_count: 0,
            duplicate_authors_count: 0,
            orphaned_avis_count: orphanedCount
          }
        });
      }
      if (url === '/api/version') {
        return Promise.resolve({ data: {} });
      }
      return Promise.reject(new Error(`URL non mockée: ${url}`));
    });
  }

  beforeEach(async () => {
    vi.clearAllMocks();

    router = createRouter({
      history: createWebHistory(),
      routes: [
        { path: '/', component: Dashboard },
        { path: '/avis-orphelins', component: { template: '<div>Avis Orphelins Page</div>' } }
      ]
    });

    await router.push('/');
  });

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount();
    }
  });

  it("affiche la tuile 'Avis orphelins' avec le compte quand il est non nul", async () => {
    mockAxiosGet(5);

    wrapper = mount(Dashboard, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 50));

    const statCards = wrapper.findAll('.stat-card');
    const cardLabels = statCards.map(card => card.text());

    expect(cardLabels.some(t => t.includes('Avis orphelins') && t.includes('5'))).toBe(true);
  });

  it("masque la tuile 'Avis orphelins' quand le compte est 0 (pattern Issue #212)", async () => {
    mockAxiosGet(0);

    wrapper = mount(Dashboard, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 50));

    const statCards = wrapper.findAll('.stat-card');
    const cardLabels = statCards.map(card => card.text());

    expect(cardLabels.some(t => t.includes('Avis orphelins'))).toBe(false);
  });

  it("navigue vers /avis-orphelins au clic sur la tuile", async () => {
    mockAxiosGet(3);

    wrapper = mount(Dashboard, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 50));

    const statCards = wrapper.findAll('.stat-card');
    const orphanedCard = statCards.find(card => card.text().includes('Avis orphelins'));
    expect(orphanedCard).toBeTruthy();

    const pushSpy = vi.spyOn(wrapper.vm.$router, 'push');
    await orphanedCard.trigger('click');

    expect(pushSpy).toHaveBeenCalledWith('/avis-orphelins');
  });
});
