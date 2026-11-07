/**
 * Tests pour AboutPage.vue (Issue #205)
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import axios from 'axios';

// Mock axios
vi.mock('axios');

// Import after mocks
import AboutPage from '../AboutPage.vue';

const mockVersionInfo = {
  commit_hash: 'abc1234567890def1234567890abcdef12345678', // pragma: allowlist secret
  commit_short: 'abc1234',
  commit_date: '2025-01-15 10:30:00 +0100',
  build_date: '2025-01-15T11:00:00Z',
  commit_url: 'https://github.com/castorfou/back-office-lmelp/commit/abc1234567890def1234567890abcdef12345678',
  environment: 'docker',
};

const mockChangelog = [
  {
    hash: 'abc1234',
    date: '2025-01-15 10:30:00 +0100',
    message: 'feat: Add version display (#205)',
  },
  {
    hash: 'def5678',
    date: '2025-01-10 08:00:00 +0100',
    message: 'Merge pull request #210 from castorfou/208-bug-fix',
  },
];

describe('AboutPage.vue (Issue #205)', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('should call /api/version and /api/changelog on mount', async () => {
    axios.get.mockImplementation((url) => {
      if (url === '/api/version') {
        return Promise.resolve({ data: mockVersionInfo });
      }
      if (url === '/api/changelog') {
        return Promise.resolve({ data: mockChangelog });
      }
      return Promise.resolve({ data: {} });
    });

    mount(AboutPage, {
      global: {
        stubs: ['router-link', 'Navigation'],
      },
    });

    await flushPromises();

    expect(axios.get).toHaveBeenCalledWith('/api/version');
    expect(axios.get).toHaveBeenCalledWith('/api/changelog');
  });

  it('should display version info when loaded', async () => {
    axios.get.mockImplementation((url) => {
      if (url === '/api/version') {
        return Promise.resolve({ data: mockVersionInfo });
      }
      if (url === '/api/changelog') {
        return Promise.resolve({ data: mockChangelog });
      }
      return Promise.resolve({ data: {} });
    });

    const wrapper = mount(AboutPage, {
      global: {
        stubs: ['router-link', 'Navigation'],
      },
    });

    await flushPromises();

    expect(wrapper.text()).toContain('abc1234');
    expect(wrapper.text()).toContain('docker');
  });

  it('should display changelog entries', async () => {
    axios.get.mockImplementation((url) => {
      if (url === '/api/version') {
        return Promise.resolve({ data: mockVersionInfo });
      }
      if (url === '/api/changelog') {
        return Promise.resolve({ data: mockChangelog });
      }
      return Promise.resolve({ data: {} });
    });

    const wrapper = mount(AboutPage, {
      global: {
        stubs: ['router-link', 'Navigation'],
      },
    });

    await flushPromises();

    expect(wrapper.text()).toContain('#205');
    expect(wrapper.text()).toContain('#210');
  });

  it('should render issue links from commit messages', async () => {
    axios.get.mockImplementation((url) => {
      if (url === '/api/version') {
        return Promise.resolve({ data: mockVersionInfo });
      }
      if (url === '/api/changelog') {
        return Promise.resolve({ data: mockChangelog });
      }
      return Promise.resolve({ data: {} });
    });

    const wrapper = mount(AboutPage, {
      global: {
        stubs: ['router-link', 'Navigation'],
      },
    });

    await flushPromises();

    // Les numéros #XXX doivent être des liens vers les issues GitHub
    const links = wrapper.findAll('a[href*="issues/"]');
    expect(links.length).toBeGreaterThan(0);
  });

  it('should handle API errors gracefully', async () => {
    axios.get.mockRejectedValue(new Error('Network error'));

    const wrapper = mount(AboutPage, {
      global: {
        stubs: ['router-link', 'Navigation'],
      },
    });

    await flushPromises();

    // La page ne doit pas crasher
    expect(wrapper.exists()).toBe(true);
  });
});

describe('AboutPage.vue — fraîcheur Calibre (Issue #327)', () => {
  // Forme réelle de GET /api/calibre/status (relevée sur le backend local)
  const NOW = new Date('2026-11-07T14:31:30Z');
  const calibreStatus = (overrides = {}) => ({
    available: true,
    library_path: '/calibre',
    total_books: 573,
    virtual_library_tag: 'guillaume',
    custom_columns: { read: 'Read (bool)' },
    error: null,
    metadata_updated_at: '2026-11-07T14:01:16.374143Z',
    latest_book_change: {
      title: 'Hamnet',
      last_modified: '2026-11-07T14:01:08.889976Z',
    },
    ...overrides,
  });

  function mockApis(statusResponse) {
    axios.get.mockImplementation((url) => {
      if (url === '/api/version') return Promise.resolve({ data: mockVersionInfo });
      if (url === '/api/changelog') return Promise.resolve({ data: mockChangelog });
      if (url === '/api/calibre/status') return statusResponse;
      return Promise.reject(new Error(`Unexpected URL: ${url}`));
    });
  }

  async function mountPage() {
    const wrapper = mount(AboutPage, {
      global: { stubs: ['router-link', 'Navigation'] },
    });
    await flushPromises();
    return wrapper;
  }

  beforeEach(() => {
    vi.resetAllMocks();
    vi.useFakeTimers({ toFake: ['Date'] });
    vi.setSystemTime(NOW);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('charge le statut Calibre au montage', async () => {
    mockApis(Promise.resolve({ data: calibreStatus() }));
    await mountPage();
    expect(axios.get).toHaveBeenCalledWith('/api/calibre/status');
  });

  it("affiche l'âge de la copie Calibre et la dernière modification vue", async () => {
    mockApis(Promise.resolve({ data: calibreStatus() }));
    const wrapper = await mountPage();

    const sync = wrapper.find('[data-test="calibre-sync-age"]');
    expect(sync.text()).toContain('il y a 30 min');
    expect(sync.attributes('title')).toBeTruthy();
    expect(wrapper.find('[data-test="calibre-latest-change"]').text()).toContain('Hamnet');
  });

  it("n'alerte pas quand la copie a moins d'une heure", async () => {
    mockApis(Promise.resolve({ data: calibreStatus() }));
    const wrapper = await mountPage();
    expect(wrapper.find('[data-test="calibre-sync-age"]').classes()).not.toContain('stale');
  });

  it("passe en orange quand la copie a plus d'une heure", async () => {
    mockApis(
      Promise.resolve({
        data: calibreStatus({ metadata_updated_at: '2026-11-06T17:15:39Z' }),
      })
    );
    const wrapper = await mountPage();

    const sync = wrapper.find('[data-test="calibre-sync-age"]');
    expect(sync.classes()).toContain('stale');
    expect(sync.text()).toContain('il y a 21 h');
  });

  it('indique quand Calibre est indisponible', async () => {
    mockApis(
      Promise.resolve({
        data: calibreStatus({
          available: false,
          error: 'metadata.db introuvable dans /calibre',
          metadata_updated_at: null,
          latest_book_change: null,
        }),
      })
    );
    const wrapper = await mountPage();

    const section = wrapper.find('[data-test="calibre-section"]');
    expect(section.text()).toContain('Calibre indisponible');
    expect(wrapper.find('[data-test="calibre-sync-age"]').exists()).toBe(false);
  });

  it("une erreur du statut Calibre n'empêche pas la version et l'historique", async () => {
    mockApis(Promise.reject(new Error('Network error')));
    const wrapper = await mountPage();

    expect(wrapper.text()).toContain('abc1234');
    expect(wrapper.find('[data-test="calibre-section"]').exists()).toBe(false);
  });
});
