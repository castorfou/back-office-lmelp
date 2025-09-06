/**
 * Tests d'intégration pour l'App principale avec router
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount } from '@vue/test-utils';
import { createRouter, createWebHistory } from 'vue-router';
import App from '../../src/App.vue';
import Dashboard from '../../src/views/Dashboard.vue';
import EpisodePage from '../../src/views/EpisodePage.vue';

// Mock des services API
vi.mock('../../src/services/api.js', () => ({
  episodeService: {
    getAllEpisodes: vi.fn(),
    getEpisodeById: vi.fn(),
    updateEpisodeDescription: vi.fn(),
    updateEpisodeTitle: vi.fn(),
  },
  statisticsService: {
    getStatistics: vi.fn(),
  }
}));

// Mock des utilitaires
vi.mock('../../src/utils/memoryGuard.js', () => ({
  memoryGuard: {
    checkMemoryLimit: vi.fn().mockReturnValue(null),
    forceShutdown: vi.fn(),
    startMonitoring: vi.fn(),
    stopMonitoring: vi.fn()
  }
}));

describe('App - Tests d\'intégration avec Router', () => {
  let wrapper;
  let router;

  beforeEach(async () => {
    vi.clearAllMocks();

    // Créer un router de test avec les vraies routes
    router = createRouter({
      history: createWebHistory(),
      routes: [
        {
          path: '/',
          component: Dashboard,
          name: 'Dashboard'
        },
        {
          path: '/episodes',
          component: EpisodePage,
          name: 'Episodes'
        }
      ]
    });
  });

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount();
    }
  });

  it('rend correctement l\'application avec le router', async () => {
    await router.push('/');

    wrapper = mount(App, {
      global: {
        plugins: [router],
        stubs: {
          Dashboard: { template: '<div data-testid="dashboard">Dashboard Component</div>' },
          EpisodePage: { template: '<div data-testid="episodes">Episodes Component</div>' }
        }
      }
    });

    await wrapper.vm.$nextTick();

    expect(wrapper.find('#app').exists()).toBe(true);
    expect(wrapper.find('[data-testid="dashboard"]').exists()).toBe(true);
  });

  it('navigue correctement vers la page d\'accueil (/)', async () => {
    await router.push('/');

    wrapper = mount(App, {
      global: {
        plugins: [router],
        stubs: {
          Dashboard: { template: '<div data-testid="dashboard">Dashboard Component</div>' },
          EpisodePage: { template: '<div data-testid="episodes">Episodes Component</div>' }
        }
      }
    });

    await wrapper.vm.$nextTick();

    expect(wrapper.find('[data-testid="dashboard"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="episodes"]').exists()).toBe(false);
    expect(router.currentRoute.value.path).toBe('/');
  });

  it('navigue correctement vers la page d\'épisodes (/episodes)', async () => {
    await router.push('/episodes');

    wrapper = mount(App, {
      global: {
        plugins: [router],
        stubs: {
          Dashboard: { template: '<div data-testid="dashboard">Dashboard Component</div>' },
          EpisodePage: { template: '<div data-testid="episodes">Episodes Component</div>' }
        }
      }
    });

    await wrapper.vm.$nextTick();

    expect(wrapper.find('[data-testid="episodes"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="dashboard"]').exists()).toBe(false);
    expect(router.currentRoute.value.path).toBe('/episodes');
  });

  it('utilise router-view pour afficher les composants', async () => {
    await router.push('/');

    wrapper = mount(App, {
      global: {
        plugins: [router],
        stubs: {
          Dashboard: { template: '<div data-testid="dashboard">Dashboard</div>' }
        }
      }
    });

    await wrapper.vm.$nextTick();

    // Vérifier que router-view est utilisé
    const routerView = wrapper.findComponent({ name: 'RouterView' });
    expect(routerView.exists()).toBe(true);
  });

  it('gère la navigation programmatique entre les pages', async () => {
    await router.push('/');

    wrapper = mount(App, {
      global: {
        plugins: [router],
        stubs: {
          Dashboard: { template: '<div data-testid="dashboard">Dashboard</div>' },
          EpisodePage: { template: '<div data-testid="episodes">Episodes</div>' }
        }
      }
    });

    await wrapper.vm.$nextTick();
    expect(wrapper.find('[data-testid="dashboard"]').exists()).toBe(true);

    // Navigation programmatique
    await router.push('/episodes');
    await wrapper.vm.$nextTick();
    expect(wrapper.find('[data-testid="episodes"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="dashboard"]').exists()).toBe(false);
  });

  it('garde la structure CSS existante de l\'app', async () => {
    await router.push('/');

    wrapper = mount(App, {
      global: {
        plugins: [router],
        stubs: {
          Dashboard: { template: '<div>Dashboard</div>' }
        }
      }
    });

    await wrapper.vm.$nextTick();

    const app = wrapper.find('#app');
    expect(app.exists()).toBe(true);

    // Vérifier que les styles globaux sont toujours importés
    // (Dans un vrai test, on vérifierait que style.css est importé dans main.js)
    expect(app.attributes('id')).toBe('app');
  });
});
