import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount } from '@vue/test-utils';
import LivreDetail from '../LivreDetail.vue';
import axios from 'axios';

// Mock axios
vi.mock('axios', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

const mockRoute = {
  params: { id: '507f1f77bcf86cd799439011' }, // pragma: allowlist secret
};

const mockRouter = {
  back: vi.fn(),
};

describe('LivreDetail - Refresh Babelio (Issue #189)', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  function mountWithLivre(livreData = {}) {
    const defaultLivre = {
      livre_id: '507f1f77bcf86cd799439011',
      titre: 'Aimez Gil',
      auteur_id: '507f1f77bcf86cd799439012',
      auteur_nom: 'Shane Haddad',
      editeur: 'POL',
      url_babelio: 'https://www.babelio.com/livres/Haddad-Aimez-Gil/1234567',
      note_moyenne: 7.0,
      nombre_emissions: 1,
      emissions: [],
    };

    axios.get.mockImplementation((url) => {
      if (url.includes('/api/livre/')) {
        return Promise.resolve({ data: { ...defaultLivre, ...livreData } });
      }
      if (url.includes('/api/avis/by-livre/')) {
        return Promise.resolve({ data: { avis: [] } });
      }
      if (url.includes('/api/config/annas-archive-url')) {
        return Promise.resolve({ data: { url: 'https://fr.annas-archive.org' } });
      }
      return Promise.reject(new Error(`Unexpected URL: ${url}`));
    });

    return mount(LivreDetail, {
      global: {
        mocks: {
          $route: mockRoute,
          $router: mockRouter,
        },
        stubs: {
          'router-link': {
            template: '<a><slot /></a>',
            props: ['to'],
          },
          Navigation: { template: '<div />' },
        },
      },
    });
  }

  async function waitForMount(wrapper) {
    await wrapper.vm.$nextTick();
    await new Promise((resolve) => setTimeout(resolve, 50));
    vi.advanceTimersByTime(50);
  }

  it('should show refresh button when url_babelio exists', async () => {
    vi.useRealTimers();
    const wrapper = mountWithLivre();
    await wrapper.vm.$nextTick();
    await new Promise((resolve) => setTimeout(resolve, 50));

    const btn = wrapper.find('[data-test="refresh-babelio-btn"]');
    expect(btn.exists()).toBe(true);
  });

  it('should not show refresh button when url_babelio is missing', async () => {
    vi.useRealTimers();
    const wrapper = mountWithLivre({ url_babelio: null });
    await wrapper.vm.$nextTick();
    await new Promise((resolve) => setTimeout(resolve, 50));

    const btn = wrapper.find('[data-test="refresh-babelio-btn"]');
    expect(btn.exists()).toBe(false);
  });

  it('should auto-apply changes and show success toast', async () => {
    vi.useRealTimers();
    const wrapper = mountWithLivre();
    await wrapper.vm.$nextTick();
    await new Promise((resolve) => setTimeout(resolve, 50));

    // Mock preview: changes detected
    axios.post.mockResolvedValueOnce({
      data: {
        status: 'success',
        current: { titre: 'Aimez Gil', editeur: 'POL', auteur_nom: 'Shane Haddad', auteur_url_babelio: null },
        babelio: { titre: 'Aimez Gil', editeur: 'P.O.L', auteur_nom: 'Shane Haddad', auteur_url_babelio: null },
        changes_detected: true,
        editeur_needs_migration: false,
      },
    });

    // Mock apply
    axios.post.mockResolvedValueOnce({
      data: { status: 'success', livre_id: '507f1f77bcf86cd799439011', editeur_created: true },
    });

    await wrapper.vm.refreshFromBabelio();
    await wrapper.vm.$nextTick();

    // Should show success toast, not modal
    expect(wrapper.vm.showRefreshModal).toBe(false);
    expect(wrapper.vm.toast).not.toBeNull();
    expect(wrapper.vm.toast.type).toBe('success');
    // apply-refresh was called automatically
    expect(axios.post).toHaveBeenCalledTimes(2);
    expect(axios.post).toHaveBeenLastCalledWith(
      expect.stringContaining('/apply-refresh'),
      expect.objectContaining({ editeur: 'P.O.L' })
    );
  });

  it('should show info toast when no changes detected', async () => {
    vi.useRealTimers();
    const wrapper = mountWithLivre();
    await wrapper.vm.$nextTick();
    await new Promise((resolve) => setTimeout(resolve, 50));

    axios.post.mockResolvedValueOnce({
      data: {
        status: 'success',
        current: { titre: 'Aimez Gil', editeur: 'Gallimard', auteur_nom: 'Test', auteur_url_babelio: null },
        babelio: { titre: 'Aimez Gil', editeur: 'Gallimard', auteur_nom: 'Test', auteur_url_babelio: null },
        changes_detected: false,
        editeur_needs_migration: false,
      },
    });

    await wrapper.vm.refreshFromBabelio();
    await wrapper.vm.$nextTick();

    // Toast info, no apply called
    expect(wrapper.vm.toast).not.toBeNull();
    expect(wrapper.vm.toast.type).toBe('info');
    expect(axios.post).toHaveBeenCalledTimes(1); // Only preview, no apply
  });

  it('should show error toast on refresh failure', async () => {
    vi.useRealTimers();
    const wrapper = mountWithLivre();
    await wrapper.vm.$nextTick();
    await new Promise((resolve) => setTimeout(resolve, 50));

    axios.post.mockRejectedValueOnce({
      response: { data: { detail: 'Erreur de scraping Babelio' } },
    });

    await wrapper.vm.refreshFromBabelio();
    await wrapper.vm.$nextTick();

    expect(wrapper.vm.toast).not.toBeNull();
    expect(wrapper.vm.toast.type).toBe('error');
    expect(wrapper.vm.toast.message).toContain('Erreur');
  });

  it('should auto-dismiss toast after timeout', async () => {
    // Mount with real timers first
    vi.useRealTimers();
    const wrapper = mountWithLivre();
    await wrapper.vm.$nextTick();
    await new Promise((resolve) => setTimeout(resolve, 50));

    // Switch to fake timers for toast testing
    vi.useFakeTimers();

    wrapper.vm.showToast('success', 'Test message');
    await wrapper.vm.$nextTick();

    expect(wrapper.vm.toast).not.toBeNull();
    const toastEl = wrapper.find('[data-test="toast"]');
    expect(toastEl.exists()).toBe(true);

    // Advance time past the auto-dismiss delay
    vi.advanceTimersByTime(5000);
    await wrapper.vm.$nextTick();

    expect(wrapper.vm.toast).toBeNull();
  });

  it('should render toast in top-right position', async () => {
    vi.useRealTimers();
    const wrapper = mountWithLivre();
    await wrapper.vm.$nextTick();
    await new Promise((resolve) => setTimeout(resolve, 50));

    wrapper.vm.showToast('success', 'Modifications appliquées');
    await wrapper.vm.$nextTick();

    const toastEl = wrapper.find('[data-test="toast"]');
    expect(toastEl.exists()).toBe(true);
    expect(toastEl.classes()).toContain('toast');
    expect(toastEl.classes()).toContain('toast-success');
  });
});
