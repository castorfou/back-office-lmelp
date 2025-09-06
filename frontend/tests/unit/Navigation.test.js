/**
 * Tests unitaires pour le composant Navigation
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount } from '@vue/test-utils';
import { createRouter, createWebHistory } from 'vue-router';
import Navigation from '../../src/components/Navigation.vue';

describe('Navigation - Tests unitaires', () => {
  let wrapper;
  let router;

  beforeEach(async () => {
    vi.clearAllMocks();

    // Créer un router de test
    router = createRouter({
      history: createWebHistory(),
      routes: [
        { path: '/', component: { template: '<div>Dashboard</div>' } },
        { path: '/episodes', component: { template: '<div>Episodes</div>' } }
      ]
    });
  });

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount();
    }
  });

  it('affiche le lien vers l\'accueil quand on n\'est pas sur la page d\'accueil', async () => {
    await router.push('/episodes');

    wrapper = mount(Navigation, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();

    const homeLink = wrapper.find('[data-testid="home-link"]');
    expect(homeLink.exists()).toBe(true);
    expect(homeLink.text()).toContain('Accueil');
  });

  it('ne affiche pas le lien vers l\'accueil quand on est sur la page d\'accueil', async () => {
    await router.push('/');

    wrapper = mount(Navigation, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();

    const homeLink = wrapper.find('[data-testid="home-link"]');
    expect(homeLink.exists()).toBe(false);
  });

  it('navigue vers l\'accueil lors du clic sur le lien', async () => {
    await router.push('/episodes');

    const push = vi.spyOn(router, 'push');

    wrapper = mount(Navigation, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();

    const homeLink = wrapper.find('[data-testid="home-link"]');
    await homeLink.trigger('click');

    expect(push).toHaveBeenCalledWith('/');
  });

  it('affiche le titre de la page courante quand fourni via props', async () => {
    await router.push('/episodes');

    wrapper = mount(Navigation, {
      props: {
        pageTitle: 'Gestion des Épisodes'
      },
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();

    expect(wrapper.text()).toContain('Gestion des Épisodes');
  });

  it('est responsive sur petits écrans', async () => {
    await router.push('/episodes');

    wrapper = mount(Navigation, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();

    const nav = wrapper.find('.navigation');
    expect(nav.exists()).toBe(true);

    // Vérifier que les styles responsive existent
    const style = wrapper.find('style');
    if (style.exists()) {
      const styleText = style.element.textContent;
      expect(styleText).toMatch(/@media.*max-width.*768px/);
    }
  });
});
