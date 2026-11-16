/**
 * Contrôle Babelio : accès réseau d'après l'essai TCP, sans requête HTTP (Issue #351).
 */
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import axios from 'axios';
import BabelioControl from '../src/views/BabelioControl.vue';

vi.mock('axios');

const BASE_STATUS = {
  overall: 'unknown',
  cookie_active: false,
  cookie_age_sec: null,
  cookie_max_age_sec: 300,
  cookie_expired: false,
  browser_user_agent: null,
  browser_accept_language: null,
  circuit_open: false,
  circuit_reason: null,
  last_probe: null,
  cache_entries: 0,
  recent_requests_count: 0,
  min_interval_sec: 10,
  cache_ttl_hours: 24,
};

function mountWith(status) {
  axios.get.mockImplementation((url) => {
    if (url.startsWith('/api/babelio/status')) return Promise.resolve({ data: status });
    return Promise.resolve({ data: [] });
  });
  return mount(BabelioControl, {
    global: { stubs: { Navigation: true, 'router-link': true, BabelioCookiePanel: true } },
  });
}

describe('BabelioControl - accès réseau (essai TCP)', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('« non testé » tant qu’aucun essai n’a eu lieu', async () => {
    const wrapper = mountWith(BASE_STATUS);
    await flushPromises();

    expect(wrapper.find('[data-test="babelio-reachability"]').text()).toContain('Non testé');
  });

  it('« Joignable » après un essai réussi', async () => {
    const wrapper = mountWith({
      ...BASE_STATUS,
      last_probe: { reachable: true, checked_at: 1763220000.0, duration_ms: 31.2 },
    });
    await flushPromises();

    expect(wrapper.find('[data-test="babelio-reachability"]').text()).toContain('Joignable');
  });

  it('« IP bannie » après un essai en échec, et motif du disjoncteur affiché', async () => {
    const wrapper = mountWith({
      ...BASE_STATUS,
      circuit_open: true,
      circuit_reason: 'connect_timeout',
      last_probe: { reachable: false, checked_at: 1763220000.0, duration_ms: 5001.0 },
    });
    await flushPromises();

    expect(wrapper.find('[data-test="babelio-reachability"]').text()).toContain('IP bannie');
    expect(wrapper.find('[data-test="babelio-circuit"]').text()).toContain('IP bannie');
  });

  it('le motif 403 du disjoncteur est affiché', async () => {
    const wrapper = mountWith({ ...BASE_STATUS, circuit_open: true, circuit_reason: 'http_403' });
    await flushPromises();

    expect(wrapper.find('[data-test="babelio-circuit"]').text()).toContain('403');
  });

  describe('badge « État du service »', () => {
    it('« Joignable » plutôt que « Inconnu » quand seul un essai TCP réussi existe', async () => {
      const wrapper = mountWith({
        ...BASE_STATUS,
        last_probe: { reachable: true, checked_at: 1763220000.0, duration_ms: 31.2 },
      });
      await flushPromises();

      const badge = wrapper.find('.status-badge');
      expect(badge.text()).toContain('Joignable');
      expect(badge.text()).not.toContain('Inconnu');
      expect(badge.classes()).toContain('status-reachable');
    });

    it('« IP bannie » quand le disjoncteur a été ouvert par un ban IP', async () => {
      const wrapper = mountWith({
        ...BASE_STATUS,
        overall: 'degraded',
        circuit_open: true,
        circuit_reason: 'connect_timeout',
        last_probe: { reachable: false, checked_at: 1763220000.0, duration_ms: 5001.0 },
      });
      await flushPromises();

      const badge = wrapper.find('.status-badge');
      expect(badge.text()).toContain('IP bannie');
      expect(badge.classes()).toContain('status-blocked');
    });

    it('le résultat d’une vraie requête HTTP reste prioritaire sur l’essai TCP', async () => {
      const wrapper = mountWith({
        ...BASE_STATUS,
        overall: 'blocked_403',
        last_probe: { reachable: true, checked_at: 1763220000.0, duration_ms: 31.2 },
      });
      await flushPromises();

      expect(wrapper.find('.status-badge').text()).toContain('403');
    });

    it('« Non testé » sans requête ni essai TCP', async () => {
      const wrapper = mountWith(BASE_STATUS);
      await flushPromises();

      expect(wrapper.find('.status-badge').text()).toContain('Non testé');
    });
  });

  // Issue #357 : 403 « Vérification de sécurité » d'un cookie anonyme
  it('motif captcha : statut « Captcha » et disjoncteur « vérification humaine »', async () => {
    const wrapper = mountWith({
      ...BASE_STATUS,
      overall: 'captcha',
      cookie_active: true,
      circuit_open: true,
      circuit_reason: 'captcha',
    });
    await flushPromises();

    const circuit = wrapper.find('[data-test="babelio-circuit"]').text();
    expect(circuit).toContain('vérification humaine');
    expect(circuit).toContain('connectez-vous à Babelio');
    expect(wrapper.text()).toContain('Captcha');
  });
});
