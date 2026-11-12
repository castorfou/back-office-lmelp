/**
 * Ouvrir une page Babelio ne renvoie jamais le cookie du navigateur au serveur.
 *
 * Ce cookie (jstsToken, durée de vie ~5 min) est souvent périmé quand on revient
 * sur une page. Le renvoyer automatiquement refermait le circuit breaker et
 * faisait passer une requête Babelio vouée au 403, que Babelio transforme en
 * ban IP. Seul le bouton « Enregistrer » envoie un cookie au serveur.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import axios from 'axios';
import BabelioControl from '../src/views/BabelioControl.vue';
import BabelioMigration from '../src/views/BabelioMigration.vue';

vi.mock('axios');

const RouterLinkStub = { template: '<a><slot /></a>' };

describe('Pages Babelio - pas de renvoi du cookie à l\'ouverture', () => {
  let wrapper;

  beforeEach(() => {
    vi.resetAllMocks();
    axios.get.mockResolvedValue({ data: {} });
    axios.post.mockResolvedValue({ data: {} });
    localStorage.setItem('babelio_cookies', 'jstsToken=<REDACTED>');
  });

  afterEach(() => {
    if (wrapper) wrapper.unmount();
    localStorage.removeItem('babelio_cookies');
  });

  it.each([
    ['BabelioControl', BabelioControl],
    ['BabelioMigration', BabelioMigration],
  ])('%s n\'envoie pas le cookie au serveur à l\'ouverture', async (_name, Page) => {
    wrapper = mount(Page, {
      global: {
        stubs: { 'router-link': RouterLinkStub, Navigation: true },
        mocks: { $route: { path: '/babelio' } },
      },
    });
    await flushPromises();

    expect(axios.post).not.toHaveBeenCalledWith('/api/babelio/cookie', expect.anything());
  });
});
