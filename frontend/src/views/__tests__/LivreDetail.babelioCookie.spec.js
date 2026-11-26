/**
 * Fiche livre : « ↻ Ré-extraire » lit quatre fois Babelio (Issue #406).
 * Sans cookie, Babelio répond 403, et un 403 peut tourner au ban IP (~24 h).
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import axios from 'axios';
import LivreDetail from '../LivreDetail.vue';
import BabelioCookiePanel from '../../components/BabelioCookiePanel.vue';

vi.mock('axios', () => ({ default: { get: vi.fn(), post: vi.fn() } }));

// Forme réelle de GET /api/babelio/status (app.py, get_babelio_status)
const ACTIVE = { overall: 'ok', cookie_active: true, cookie_age_sec: 60, cookie_max_age_sec: 1200, cookie_expired: false };
const MISSING = { overall: 'unknown', cookie_active: false, cookie_age_sec: null, cookie_max_age_sec: 1200, cookie_expired: false };
const LIVRE_ID = '6b0687113a756aaf913fe9f0'; // pragma: allowlist secret

const LIVRE = {
  livre_id: LIVRE_ID,
  titre: "L'autre Simenon",
  auteur_id: '6b074b7356795681a647b7dd', // pragma: allowlist secret
  auteur_nom: 'P. Roegiers',
  editeur: 'Grasset',
  url_babelio: 'https://www.babelio.com/livres/Roegiers-Lautre-Simenon/722392',
  note_moyenne: null,
  nombre_emissions: 0,
  emissions: [],
};

async function mountPage(status) {
  axios.get.mockImplementation((url) => {
    if (url === '/api/babelio/status') return Promise.resolve({ data: status });
    if (url.includes('/api/livre/')) return Promise.resolve({ data: LIVRE });
    if (url.includes('/api/avis/by-livre/')) return Promise.resolve({ data: { avis: [] } });
    if (url.includes('/api/config/annas-archive-url')) return Promise.resolve({ data: { url: 'https://fr.annas-archive.org' } });
    return Promise.reject(new Error(`URL inattendue ${url}`));
  });
  const wrapper = mount(LivreDetail, {
    global: {
      mocks: { $route: { params: { id: LIVRE_ID } }, $router: { back: vi.fn() } },
      stubs: { 'router-link': { template: '<a><slot /></a>', props: ['to'] }, Navigation: true },
    },
  });
  await flushPromises();
  return wrapper;
}

const refreshButton = (wrapper) => wrapper.find('[data-test="refresh-babelio-btn"]');
const statusCalls = () => axios.get.mock.calls.filter(([u]) => u === '/api/babelio/status').length;

describe('LivreDetail — cookie Babelio', () => {
  beforeEach(() => vi.resetAllMocks());

  it('affiche le panneau cookie alimenté par le statut du serveur', async () => {
    const wrapper = await mountPage(ACTIVE);

    expect(wrapper.findComponent(BabelioCookiePanel).props('status')).toEqual(ACTIVE);
  });

  it('désactive « Ré-extraire » tant que le cookie n\'est pas actif', async () => {
    const wrapper = await mountPage(MISSING);

    expect(refreshButton(wrapper).attributes('disabled')).toBeDefined();
  });

  it('autorise « Ré-extraire » avec un cookie actif', async () => {
    const wrapper = await mountPage(ACTIVE);

    expect(refreshButton(wrapper).attributes('disabled')).toBeUndefined();
  });

  it('ne lance pas la ré-extraction quand la sonde dit Babelio injoignable', async () => {
    const wrapper = await mountPage(ACTIVE);
    axios.post.mockImplementation((url) => {
      if (url === '/api/babelio/probe') return Promise.resolve({ data: { reachable: false } });
      return Promise.resolve({ data: {} });
    });

    await wrapper.vm.refreshFromBabelio();

    expect(axios.post).toHaveBeenCalledWith('/api/babelio/probe');
    expect(axios.post).not.toHaveBeenCalledWith(`/api/livres/${LIVRE_ID}/refresh-babelio`);
  });

  it('recharge le statut Babelio après une ré-extraction en échec', async () => {
    const wrapper = await mountPage(ACTIVE);
    axios.post.mockImplementation((url) => {
      if (url === '/api/babelio/probe') return Promise.resolve({ data: { reachable: true } });
      return Promise.reject({ response: { data: { detail: 'Erreur lors du scraping Babelio: 403' } } });
    });
    const before = statusCalls();

    await wrapper.vm.refreshFromBabelio();

    expect(statusCalls()).toBe(before + 1);
  });
});
