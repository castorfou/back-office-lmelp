/**
 * Tests TDD pour les boutons Enregistrer/Effacer du cookie Babelio sur la page
 * "Liaison Babelio des livres" (Issue #251).
 *
 * Contexte: cette page sauvegardait le cookie automatiquement à chaque frappe
 * (@input="saveCookies") sans boutons explicites Enregistrer/Effacer, contrairement
 * à la page LivresAuteurs.vue. Alignement demandé par l'utilisateur pour cohérence
 * UX entre les deux pages.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { mount } from '@vue/test-utils';
import BabelioMigration from '../src/views/BabelioMigration.vue';
import axios from 'axios';

vi.mock('axios');

const RouterLinkStub = {
  template: '<a><slot /></a>',
};

describe('BabelioMigration - Boutons Enregistrer/Effacer cookie (Issue #251)', () => {
  let wrapper;

  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount();
    }
    localStorage.clear();
    vi.useRealTimers();
  });

  function mountComponent() {
    axios.get.mockResolvedValue({ data: {} });
    axios.post.mockResolvedValue({ data: {} });
    axios.delete.mockResolvedValue({ data: {} });
    return mount(BabelioMigration, {
      global: {
        stubs: { 'router-link': RouterLinkStub },
        mocks: { $route: { path: '/babelio-migration' } },
      },
    });
  }

  it("n'enregistre pas le cookie tant que le bouton Enregistrer n'est pas cliqué", async () => {
    wrapper = mountComponent();
    await wrapper.vm.$nextTick();

    wrapper.vm.babelioCookieInput = 'jstsToken=abc123; p=FR; disclaimer=1';
    await wrapper.vm.$nextTick();

    expect(localStorage.getItem('babelio_cookies')).toBeNull();
    expect(wrapper.vm.babelioCookies).toBe('');
  });

  it('enregistre le cookie dans localStorage et babelioCookies au clic sur Enregistrer', async () => {
    wrapper = mountComponent();
    await wrapper.vm.$nextTick();

    wrapper.vm.babelioCookieInput = 'jstsToken=abc123; p=FR; disclaimer=1';
    wrapper.vm.saveBabelioCookie();
    await wrapper.vm.$nextTick();

    expect(localStorage.getItem('babelio_cookies')).toBe('jstsToken=abc123; p=FR; disclaimer=1');
    expect(wrapper.vm.babelioCookies).toBe('jstsToken=abc123; p=FR; disclaimer=1');
    expect(wrapper.vm.babelioCookieStored).toBe(true);
  });

  it('affiche une confirmation après la sauvegarde', async () => {
    vi.useFakeTimers();
    wrapper = mountComponent();
    await wrapper.vm.$nextTick();
    vi.useFakeTimers();

    wrapper.vm.babelioCookieInput = 'jstsToken=abc123; p=FR; disclaimer=1';
    wrapper.vm.saveBabelioCookie();
    await wrapper.vm.$nextTick();

    expect(wrapper.vm.babelioCookieJustSaved).toBe(true);

    vi.advanceTimersByTime(3100);
    await wrapper.vm.$nextTick();

    expect(wrapper.vm.babelioCookieJustSaved).toBe(false);
  });

  it('efface le cookie au clic sur Effacer', async () => {
    localStorage.setItem('babelio_cookies', 'jstsToken=old; p=FR; disclaimer=1');
    wrapper = mountComponent();
    await wrapper.vm.$nextTick();

    expect(wrapper.vm.babelioCookieStored).toBe(true);

    wrapper.vm.clearBabelioCookie();
    await wrapper.vm.$nextTick();

    expect(localStorage.getItem('babelio_cookies')).toBeNull();
    expect(wrapper.vm.babelioCookies).toBe('');
    expect(wrapper.vm.babelioCookieStored).toBe(false);
  });

  it('transmet le cookie sauvegardé (pas la saisie en cours non sauvegardée) à update-from-url', async () => {
    wrapper = mountComponent();
    await wrapper.vm.$nextTick();

    wrapper.vm.babelioCookieInput = 'jstsToken=saved; p=FR; disclaimer=1';
    wrapper.vm.saveBabelioCookie();
    await wrapper.vm.$nextTick();

    // L'utilisateur tape un nouveau brouillon sans cliquer Enregistrer
    wrapper.vm.babelioCookieInput = 'jstsToken=draft-not-saved';

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
        babelio_cookies: 'jstsToken=saved; p=FR; disclaimer=1',
      })
    );
  });
});
