/**
 * Liaison Babelio : un ban IP n'est pas un problème de cookie (Issue #351).
 *
 * Le disjoncteur ouvert par un timeout de connexion (ou un essai TCP en échec)
 * doit dire « IP bannie, inutile de changer le cookie » ; la migration refuse
 * de démarrer (status `unreachable`) quand l'essai d'avant traitement échoue.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import axios from 'axios';
import BabelioMigration from '../../src/views/BabelioMigration.vue';

vi.mock('axios');

const IP_BAN_TEXT = 'Babelio injoignable : IP bannie, inutile de changer le cookie';

const BANNED_STATUS = {
  overall: 'degraded',
  cookie_active: true,
  cookie_expired: false,
  circuit_open: true,
  circuit_reason: 'connect_timeout',
  last_probe: { reachable: false, checked_at: 1763220000.0, duration_ms: 1001.4 },
  cache_entries: 135,
  recent_requests_count: 3,
  min_interval_sec: 10,
  cache_ttl_hours: 24,
};

const IDLE_PROGRESS = { is_running: false, books_processed: 0, logs: [], book_logs: [] };

function mockApi(babelioStatus) {
  axios.get.mockImplementation((url) => {
    if (url.startsWith('/api/babelio/status')) return Promise.resolve({ data: babelioStatus });
    if (url === '/api/babelio-migration/progress') return Promise.resolve({ data: IDLE_PROGRESS });
    if (url === '/api/babelio-migration/status') return Promise.resolve({ data: {} });
    return Promise.resolve({ data: [] });
  });
}

describe('BabelioMigration - ban IP (Issue #351)', () => {
  let wrapper;

  const mountPage = async () => {
    wrapper = mount(BabelioMigration, {
      global: { stubs: { Navigation: true, 'router-link': true } },
    });
    await flushPromises();
  };

  beforeEach(() => {
    vi.resetAllMocks();
    axios.post.mockResolvedValue({ data: {} });
  });

  afterEach(() => {
    wrapper?.unmount();
  });

  it('le bandeau dit « IP bannie » quand le disjoncteur a été ouvert par un timeout de connexion', async () => {
    mockApi(BANNED_STATUS);
    await mountPage();

    const banner = wrapper.find('[data-test="babelio-blocked-banner"]');
    expect(banner.exists()).toBe(true);
    expect(banner.text()).toContain(IP_BAN_TEXT);
    expect(banner.text()).not.toContain('403');
  });

  it('le bandeau reste celui du 403 quand le disjoncteur a été ouvert par un 403', async () => {
    mockApi({ ...BANNED_STATUS, overall: 'blocked_403', cookie_active: false, circuit_reason: 'http_403' });
    await mountPage();

    const banner = wrapper.find('[data-test="babelio-blocked-banner"]');
    expect(banner.text()).toContain('403');
    expect(banner.text()).not.toContain(IP_BAN_TEXT);
  });

  it('démarrage refusé (IP bannie) : message affiché et statut Babelio relu', async () => {
    mockApi({ ...BANNED_STATUS, circuit_open: false, circuit_reason: null });
    await mountPage();
    axios.post.mockResolvedValueOnce({
      data: { status: 'unreachable', message: IP_BAN_TEXT },
    });
    axios.get.mockClear();
    mockApi(BANNED_STATUS);
    const toast = vi.spyOn(wrapper.vm, 'showToast');

    await wrapper.vm.startMigration();
    await flushPromises();

    expect(axios.post).toHaveBeenCalledWith('/api/babelio-migration/start');
    expect(toast).toHaveBeenCalledWith(IP_BAN_TEXT, 'error');
    expect(wrapper.vm.migrationProgress.is_running).toBe(false);
    expect(wrapper.find('[data-test="babelio-blocked-banner"]').text()).toContain(IP_BAN_TEXT);
  });
});
