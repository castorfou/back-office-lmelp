/**
 * Tests TDD pour le bouton "Rafraîchir" de l'état du service Babelio (Issue #287)
 *
 * Problème business réel :
 * - Le badge "État du service" pouvait afficher "OK" sans preuve réelle (buffer
 *   backend vide), sans moyen de forcer une vérification à jour.
 * - Le bouton "🔄 Rafraîchir" doit désormais déclencher un health check actif
 *   côté backend (paramètre live_check=true), MAIS le polling silencieux (30s)
 *   ne doit jamais le faire, pour ne pas spammer Babelio à chaque visite.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { mount } from '@vue/test-utils';
import BabelioControl from '../src/views/BabelioControl.vue';
import axios from 'axios';

vi.mock('axios');

const RouterLinkStub = {
  template: '<a><slot /></a>',
};

describe('BabelioControl - bouton Rafraîchir (live check)', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    axios.get.mockResolvedValue({ data: {} });
  });

  const mountComponent = () => {
    return mount(BabelioControl, {
      global: {
        stubs: { 'router-link': RouterLinkStub, Navigation: true },
      },
    });
  };

  it('should call GET /api/babelio/status without live_check on initial load', async () => {
    const wrapper = mountComponent();
    await wrapper.vm.$nextTick();
    await Promise.resolve();

    const statusCalls = axios.get.mock.calls.filter(([url]) =>
      url.startsWith('/api/babelio/status')
    );
    expect(statusCalls.length).toBeGreaterThan(0);
    expect(statusCalls[0][0]).toBe('/api/babelio/status');
  });

  it('should call GET /api/babelio/status?live_check=true when refresh button is clicked', async () => {
    const wrapper = mountComponent();
    await wrapper.vm.$nextTick();
    await Promise.resolve();
    axios.get.mockClear();

    await wrapper.vm.refreshStatus();

    const statusCalls = axios.get.mock.calls.filter(([url]) =>
      url.startsWith('/api/babelio/status')
    );
    expect(statusCalls).toHaveLength(1);
    expect(statusCalls[0][0]).toBe('/api/babelio/status?live_check=true');
  });

  it('should NOT set live_check on the silent polling call', async () => {
    const wrapper = mountComponent();
    await wrapper.vm.$nextTick();
    await Promise.resolve();
    axios.get.mockClear();

    await wrapper.vm.loadStatus();

    const statusCalls = axios.get.mock.calls.filter(([url]) =>
      url.startsWith('/api/babelio/status')
    );
    expect(statusCalls).toHaveLength(1);
    expect(statusCalls[0][0]).toBe('/api/babelio/status');
  });
});
