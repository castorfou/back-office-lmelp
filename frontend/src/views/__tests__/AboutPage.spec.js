/**
 * Tests pour AboutPage.vue (Issue #205)
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
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
