/**
 * Tests TDD pour la propagation du cookie Babelio dans submitUrl() (Issue #251).
 *
 * Contexte: la page "Liaison Babelio des livres" (BabelioMigration.vue) a un champ
 * de cookie Babelio déjà fonctionnel pour /api/babelio/extract-cover-url, mais
 * l'appel à /api/babelio-migration/update-from-url oubliait de le transmettre,
 * causant des 403 silencieux même quand l'utilisateur avait fourni un cookie valide.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { mount } from '@vue/test-utils';
import BabelioMigration from '../src/views/BabelioMigration.vue';
import axios from 'axios';

vi.mock('axios');

const RouterLinkStub = {
  template: '<a><slot /></a>',
};

describe('BabelioMigration - Propagation cookie Babelio (Issue #251)', () => {
  let wrapper;

  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorage.clear();
  });

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount();
    }
    sessionStorage.clear();
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

  it('transmet babelio_cookies à update-from-url quand un cookie est configuré', async () => {
    wrapper = mountComponent();
    await wrapper.vm.$nextTick();

    wrapper.vm.babelioCookies = 'jstsToken=abc123; p=FR; disclaimer=1';
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

    expect(axios.post).toHaveBeenCalledWith(
      '/api/babelio-migration/update-from-url',
      expect.objectContaining({
        babelio_cookies: 'jstsToken=abc123; p=FR; disclaimer=1',
      })
    );
  });

  it('transmet babelio_cookies=null quand aucun cookie configuré', async () => {
    wrapper = mountComponent();
    await wrapper.vm.$nextTick();

    wrapper.vm.babelioCookies = '';
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

    expect(axios.post).toHaveBeenCalledWith(
      '/api/babelio-migration/update-from-url',
      expect.objectContaining({
        babelio_cookies: null,
      })
    );
  });
});
