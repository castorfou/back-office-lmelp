/**
 * Page Recherche Babelio : chaque recherche interroge Babelio (Issue #406).
 * Sans cookie, Babelio répond 403, et un 403 peut tourner au ban IP (~24 h).
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import axios from 'axios';
import BabelioTest from '../BabelioTest.vue';
import BabelioCookiePanel from '../../components/BabelioCookiePanel.vue';

vi.mock('axios', () => ({ default: { get: vi.fn(), post: vi.fn() } }));

// Forme réelle de GET /api/babelio/status (app.py, get_babelio_status)
const ACTIVE = { overall: 'ok', cookie_active: true, cookie_age_sec: 60, cookie_max_age_sec: 1200, cookie_expired: false };
const MISSING = { overall: 'unknown', cookie_active: false, cookie_age_sec: null, cookie_max_age_sec: 1200, cookie_expired: false };

async function mountPage(status) {
  axios.get.mockImplementation((url) => {
    if (url === '/api/babelio/status') return Promise.resolve({ data: status });
    return Promise.reject(new Error(`URL inattendue ${url}`));
  });
  const wrapper = mount(BabelioTest, { global: { stubs: { Navigation: true, 'router-link': true } } });
  await flushPromises();
  // Formulaires remplis : seul le cookie peut alors désactiver les boutons
  wrapper.vm.forms.author.name = 'Patrick Roegiers';
  wrapper.vm.forms.book.title = "L'autre Simenon";
  wrapper.vm.forms.publisher.name = 'Grasset';
  await flushPromises();
  return wrapper;
}

const searchButtons = (wrapper) => wrapper.findAll('form button[type="submit"]');
const statusCalls = () => axios.get.mock.calls.filter(([u]) => u === '/api/babelio/status').length;

describe('BabelioTest — cookie Babelio', () => {
  beforeEach(() => vi.resetAllMocks());

  it('affiche le panneau cookie alimenté par le statut du serveur', async () => {
    const wrapper = await mountPage(ACTIVE);

    expect(wrapper.findComponent(BabelioCookiePanel).props('status')).toEqual(ACTIVE);
  });

  it('désactive les recherches tant que le cookie n\'est pas actif', async () => {
    const wrapper = await mountPage(MISSING);

    const buttons = searchButtons(wrapper);
    expect(buttons.length).toBe(3);
    buttons.forEach((b) => expect(b.attributes('disabled')).toBeDefined());
  });

  it('autorise les recherches avec un cookie actif', async () => {
    const wrapper = await mountPage(ACTIVE);

    searchButtons(wrapper).forEach((b) => expect(b.attributes('disabled')).toBeUndefined());
  });

  it('ne lance pas la recherche quand la sonde dit Babelio injoignable', async () => {
    const wrapper = await mountPage(ACTIVE);
    axios.post.mockImplementation((url) => {
      if (url === '/api/babelio/probe') return Promise.resolve({ data: { reachable: false } });
      return Promise.resolve({ data: {} });
    });

    await wrapper.vm.verifyAuthor();

    expect(axios.post).toHaveBeenCalledWith('/api/babelio/probe');
    expect(axios.post).not.toHaveBeenCalledWith('/api/verify-babelio', expect.anything());
    expect(wrapper.vm.error).toContain('injoignable');
  });

  it('recharge le statut Babelio après une recherche en échec', async () => {
    const wrapper = await mountPage(ACTIVE);
    axios.post.mockImplementation((url) => {
      if (url === '/api/babelio/probe') return Promise.resolve({ data: { reachable: true } });
      return Promise.reject({ response: { data: { detail: 'Babelio 403' } } });
    });
    const before = statusCalls();

    await wrapper.vm.verifyBook();

    expect(statusCalls()).toBe(before + 1);
  });
});
