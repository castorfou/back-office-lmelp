/**
 * Les appels Babelio ne transportent plus de cookie du navigateur.
 *
 * Le serveur est la seule source du cookie Babelio : il le date à la réception
 * et refuse de l'utiliser une fois périmé. Un cookie joint à chaque requête
 * échappait à ce contrôle (le serveur l'utilisait quand il n'en avait pas),
 * et un vieux jstsToken ainsi envoyé provoquait un 403, puis un ban IP.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { mount } from '@vue/test-utils';
import BabelioMigration from '../src/views/BabelioMigration.vue';
import axios from 'axios';

vi.mock('axios');

const RouterLinkStub = {
  template: '<a><slot /></a>',
};

describe('BabelioMigration - aucun cookie du navigateur dans les requêtes', () => {
  let wrapper;

  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.setItem('babelio_cookies', 'jstsToken=old; p=FR; disclaimer=1');
  });

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount();
    }
    localStorage.removeItem('babelio_cookies');
  });

  function mountComponent() {
    axios.get.mockResolvedValue({ data: {} });
    return mount(BabelioMigration, {
      global: {
        stubs: { 'router-link': RouterLinkStub },
        mocks: { $route: { path: '/babelio-migration' } },
      },
    });
  }

  it('update-from-url ne transmet pas babelio_cookies', async () => {
    wrapper = mountComponent();
    await wrapper.vm.$nextTick();

    wrapper.vm.babelioUrl = 'https://www.babelio.com/livres/Test/123';
    wrapper.vm.urlPopupCase = {
      type: 'livre',
      livre_id: 'livre-id-1',
      titre_attendu: 'Titre Test',
    };
    axios.post.mockResolvedValue({
      data: { status: 'success', message: 'Livre mis à jour', data: {} },
    });

    await wrapper.vm.submitUrl();

    const call = axios.post.mock.calls.find(([url]) => url === '/api/babelio-migration/update-from-url');
    expect(call).toBeDefined();
    expect(call[1]).not.toHaveProperty('babelio_cookies');
  });

  it('extract-cover-url ne transmet pas babelio_cookies', async () => {
    wrapper = mountComponent();
    await wrapper.vm.$nextTick();
    axios.post.mockResolvedValue({ data: { url_cover: null } });

    await wrapper.vm._extractCoverUrlFromBabelioPage('https://www.babelio.com/livres/Test/123', 'Titre');

    const call = axios.post.mock.calls.find(([url]) => url === '/api/babelio/extract-cover-url');
    expect(call).toBeDefined();
    expect(call[1]).not.toHaveProperty('babelio_cookies');
  });
});
