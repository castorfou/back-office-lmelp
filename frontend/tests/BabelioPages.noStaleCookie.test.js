/**
 * Le panneau « Cookie Babelio » ne reprend jamais un cookie gardé dans le navigateur.
 *
 * Le serveur date un cookie au moment où il le reçoit. Un vieux jstsToken resté
 * dans le navigateur, renvoyé tel quel par « Enregistrer », passe donc pour frais :
 * Babelio répond 403, et ses 403 deviennent un ban IP d'environ 24 h.
 * Le champ démarre vide et le badge ne lit que l'état du serveur (/api/babelio/status).
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import axios from 'axios';
import BabelioControl from '../src/views/BabelioControl.vue';
import BabelioMigration from '../src/views/BabelioMigration.vue';
import LivresAuteurs from '../src/views/LivresAuteurs.vue';
import { livresAuteursService } from '../src/services/api.js';

vi.mock('axios');

vi.mock('../src/services/api.js', () => ({
  livresAuteursService: {
    getEpisodesWithReviews: vi.fn(),
    getLivresAuteurs: vi.fn(),
  },
  episodeService: {},
  statisticsService: {},
  babelioService: {},
  fuzzySearchService: {},
}));

const RouterLinkStub = { template: '<a><slot /></a>' };
const OLD_COOKIE = 'jstsToken=old-session-cookie; p=FR; disclaimer=1';

function mockStatus(status) {
  axios.get.mockImplementation((url) => {
    if (url.startsWith('/api/babelio/status')) return Promise.resolve({ data: status });
    return Promise.resolve({ data: [] });
  });
}

async function mountPage(Page) {
  const wrapper = mount(Page, {
    global: {
      stubs: { 'router-link': RouterLinkStub, Navigation: true },
      mocks: { $route: { path: '/babelio', query: {} }, $router: { push: vi.fn(), replace: vi.fn() } },
    },
  });
  await flushPromises();
  if (Page === LivresAuteurs) {
    // Le panneau n'apparaît qu'une fois un épisode choisi
    wrapper.vm.selectedEpisodeId = 'episode-1';
    await flushPromises();
  }
  return wrapper;
}

const PAGES = [
  ['LivresAuteurs', LivresAuteurs],
  ['BabelioMigration', BabelioMigration],
  ['BabelioControl', BabelioControl],
];

describe('Pages Babelio - aucun cookie gardé dans le navigateur', () => {
  let wrapper;

  beforeEach(() => {
    vi.resetAllMocks();
    livresAuteursService.getEpisodesWithReviews.mockResolvedValue([]);
    livresAuteursService.getLivresAuteurs.mockResolvedValue([]);
    axios.post.mockResolvedValue({ data: {} });
    axios.delete.mockResolvedValue({ data: {} });
    localStorage.setItem('babelio_cookies', OLD_COOKIE);
    localStorage.setItem('babelio_cookies_saved_at', String(Date.now() - 3 * 86400000));
  });

  afterEach(() => {
    if (wrapper) wrapper.unmount();
    wrapper = null;
    localStorage.removeItem('babelio_cookies');
    localStorage.removeItem('babelio_cookies_saved_at');
  });

  it.each(PAGES)('%s : serveur sans cookie → champ vide, badge « non configuré »', async (_name, Page) => {
    mockStatus({ cookie_active: false, cookie_age_sec: null, cookie_max_age_sec: 300, cookie_expired: false });
    wrapper = await mountPage(Page);

    const panel = wrapper.find('[data-test="babelio-cookie-panel"]');
    expect(panel.exists()).toBe(true);
    expect(panel.find('textarea').element.value).toBe('');
    const badge = panel.find('[data-test="cookie-badge"]').text();
    expect(badge).not.toContain('Configuré');
    expect(badge).not.toContain('Actif');
    expect(badge).toContain('non configuré');
  });

  it.each(PAGES)('%s : purge le cookie gardé dans localStorage', async (_name, Page) => {
    mockStatus({ cookie_active: false });
    wrapper = await mountPage(Page);

    expect(localStorage.getItem('babelio_cookies')).toBeNull();
    expect(localStorage.getItem('babelio_cookies_saved_at')).toBeNull();
  });

  it.each(PAGES)('%s : cookie serveur périmé → badge « périmé »', async (_name, Page) => {
    mockStatus({ cookie_active: true, cookie_age_sec: 900, cookie_max_age_sec: 300, cookie_expired: true });
    wrapper = await mountPage(Page);

    const badge = wrapper.find('[data-test="babelio-cookie-panel"] [data-test="cookie-badge"]').text();
    expect(badge).toContain('périmé');
    expect(badge).not.toContain('Actif');
  });

  it.each(PAGES)('%s : cookie serveur frais → badge « Actif côté serveur »', async (_name, Page) => {
    mockStatus({ cookie_active: true, cookie_age_sec: 10, cookie_max_age_sec: 300, cookie_expired: false });
    wrapper = await mountPage(Page);

    const badge = wrapper.find('[data-test="babelio-cookie-panel"] [data-test="cookie-badge"]').text();
    expect(badge).toContain('Actif côté serveur');
  });
});
