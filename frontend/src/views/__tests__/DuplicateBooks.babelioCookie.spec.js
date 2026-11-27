/**
 * Page Gestion des doublons : la fusion lit le nom officiel sur Babelio (Issue #406).
 * Sans cookie, Babelio répond 403, et un 403 peut tourner au ban IP (~24 h).
 * La page gère donc le cookie comme les autres pages Babelio : panneau cookie,
 * fusion impossible sans cookie actif, sonde TCP avant chaque fusion, statut
 * rechargé après un échec.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import axios from 'axios';
import DuplicateBooks from '../DuplicateBooks.vue';
import BabelioCookiePanel from '../../components/BabelioCookiePanel.vue';

vi.mock('axios');

// Forme réelle de GET /api/babelio/status (app.py, get_babelio_status)
const ACTIVE = { overall: 'ok', cookie_active: true, cookie_age_sec: 60, cookie_max_age_sec: 1200, cookie_expired: false };
const MISSING = { overall: 'unknown', cookie_active: false, cookie_age_sec: null, cookie_max_age_sec: 1200, cookie_expired: false };

const AUTHOR_GROUP = {
  url_babelio: 'https://www.babelio.com/auteur/Patrick-Roegiers/6213',
  count: 2,
  auteur_ids: ['a1', 'a2'],
  noms: ['Patrick J. Rogers', 'Patrick Roegiers'],
};
const BOOK_GROUP = {
  url_babelio: 'https://www.babelio.com/livres/book1',
  count: 2,
  book_ids: ['b1', 'b2'],
  titres: ['Titre', 'Titre bis'],
  auteur_ids: ['a1', 'a1'],
};

function mockGets(status) {
  axios.get.mockImplementation((url) => {
    if (url === '/api/babelio/status') return Promise.resolve({ data: status });
    if (url.includes('/books/duplicates/statistics')) return Promise.resolve({ data: { total_groups: 1, total_duplicates: 2 } });
    if (url.includes('/books/duplicates/groups')) return Promise.resolve({ data: [BOOK_GROUP] });
    if (url.includes('/authors/duplicates/statistics')) return Promise.resolve({ data: { total_groups: 1, total_duplicates: 2 } });
    if (url.includes('/authors/duplicates/groups')) return Promise.resolve({ data: [AUTHOR_GROUP] });
    return Promise.reject(new Error(`URL inattendue ${url}`));
  });
}

async function mountPage(status) {
  mockGets(status);
  const wrapper = mount(DuplicateBooks, {
    global: { stubs: { Navigation: true, 'router-link': true } },
  });
  await flushPromises();
  return wrapper;
}

function mergeButtons(wrapper) {
  return wrapper.findAll('button').filter((b) => /Fusionner|Tout fusionner/.test(b.text()));
}

describe('DuplicateBooks — cookie Babelio', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    axios.get = vi.fn();
    axios.post = vi.fn();
  });

  it('affiche le panneau cookie alimenté par le statut du serveur', async () => {
    const wrapper = await mountPage(ACTIVE);

    const panel = wrapper.findComponent(BabelioCookiePanel);
    expect(panel.exists()).toBe(true);
    expect(panel.props('status')).toEqual(ACTIVE);
  });

  it('désactive toutes les fusions tant que le cookie n\'est pas actif', async () => {
    const wrapper = await mountPage(MISSING);

    const buttons = mergeButtons(wrapper);
    expect(buttons.length).toBe(3);
    buttons.forEach((b) => expect(b.attributes('disabled')).toBeDefined());
    expect(wrapper.text()).toContain('cookie Babelio');
  });

  it('autorise les fusions avec un cookie actif', async () => {
    const wrapper = await mountPage(ACTIVE);

    mergeButtons(wrapper).forEach((b) => expect(b.attributes('disabled')).toBeUndefined());
  });

  it('ne fusionne pas quand la sonde dit Babelio injoignable', async () => {
    const wrapper = await mountPage(ACTIVE);
    axios.post.mockImplementation((url) => {
      if (url === '/api/babelio/probe') return Promise.resolve({ data: { reachable: false } });
      return Promise.resolve({ data: { result: {} } });
    });

    await wrapper.vm.mergeAuthorGroup(AUTHOR_GROUP);

    expect(axios.post).toHaveBeenCalledWith('/api/babelio/probe');
    expect(axios.post).not.toHaveBeenCalledWith('/api/authors/duplicates/merge', expect.anything());
    expect(wrapper.vm.authorMergeResults[AUTHOR_GROUP.url_babelio].success).toBe(false);
  });

  it('recharge le statut Babelio après une fusion en échec', async () => {
    const wrapper = await mountPage(ACTIVE);
    axios.post.mockImplementation((url) => {
      if (url === '/api/babelio/probe') return Promise.resolve({ data: { reachable: true } });
      return Promise.reject({ response: { data: { detail: 'Erreur serveur: Babelio 403 scraping' } } });
    });
    const statusCallsBefore = axios.get.mock.calls.filter(([u]) => u === '/api/babelio/status').length;

    await wrapper.vm.mergeAuthorGroup(AUTHOR_GROUP);

    const statusCallsAfter = axios.get.mock.calls.filter(([u]) => u === '/api/babelio/status').length;
    expect(statusCallsAfter).toBe(statusCallsBefore + 1);
  });

  it('arrête « Tout fusionner » au premier échec', async () => {
    const wrapper = await mountPage(ACTIVE);
    wrapper.vm.duplicateAuthors = [AUTHOR_GROUP, { ...AUTHOR_GROUP, url_babelio: 'https://www.babelio.com/auteur/X/1' }];
    axios.post.mockImplementation((url) => {
      if (url === '/api/babelio/probe') return Promise.resolve({ data: { reachable: true } });
      return Promise.reject({ response: { data: { detail: 'Erreur serveur: Babelio 403 scraping' } } });
    });
    vi.useFakeTimers();

    const run = wrapper.vm.startGlobalBatchMerge();
    await vi.runAllTimersAsync();
    await run;
    vi.useRealTimers();

    const merges = axios.post.mock.calls.filter(([u]) => u.includes('/duplicates/merge'));
    expect(merges.length).toBe(1);
  });
});
