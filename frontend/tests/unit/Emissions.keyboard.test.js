/**
 * Tests TDD pour la navigation au clavier sur la page Émissions (Issue #154 - Enhancement)
 *
 * Fonctionnalité: Navigation avec flèches gauche/droite
 * - Flèche gauche (←) = Précédent (plus ancien)
 * - Flèche droite (→) = Suivant (plus récent)
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { createRouter, createMemoryHistory } from 'vue-router';
import Emissions from '../../src/views/Emissions.vue';
import { emissionsService } from '../../src/services/api';

// Mock des services
vi.mock('../../src/services/api', () => ({
  emissionsService: {
    getAllEmissions: vi.fn(),
    getEmissionByDate: vi.fn(),
    getEmissionDetails: vi.fn(),
  }
}));

// Mock de marked
vi.mock('marked', () => ({
  marked: vi.fn((text) => text)
}));

describe('Emissions - Keyboard Navigation Tests (TDD)', () => {
  let router;
  let wrapper;

  const mockEmissions = [
    {
      id: 'emission-21dec',
      date: '2025-12-21T10:00:00',
      episode: { titre: 'Émission du 21 déc', date: '2025-12-21T10:00:00' }
    },
    {
      id: 'emission-07dec',
      date: '2025-12-07T10:00:00',
      episode: { titre: 'Émission du 7 déc', date: '2025-12-07T10:00:00' }
    },
    {
      id: 'emission-09nov',
      date: '2025-11-09T10:00:00',
      episode: { titre: 'Émission du 9 nov', date: '2025-11-09T10:00:00' }
    }
  ];

  beforeEach(() => {
    vi.clearAllMocks();

    // Setup router
    router = createRouter({
      history: createMemoryHistory(),
      routes: [
        {
          path: '/emissions/:date',
          name: 'EmissionDetail',
          component: Emissions
        },
        {
          path: '/emissions',
          name: 'Emissions',
          component: Emissions
        }
      ]
    });

    emissionsService.getAllEmissions.mockResolvedValue(mockEmissions);

    // Mock getEmissionByDate pour retourner l'émission correspondante
    emissionsService.getEmissionByDate.mockImplementation((dateStr) => {
      const emission = mockEmissions.find(e => {
        const emissionDate = new Date(e.date);
        const expectedDate = `${emissionDate.getFullYear()}${String(emissionDate.getMonth() + 1).padStart(2, '0')}${String(emissionDate.getDate()).padStart(2, '0')}`;
        return expectedDate === dateStr;
      });

      if (!emission) return Promise.reject(new Error('Émission non trouvée'));

      return Promise.resolve({
        emission: { id: emission.id },
        episode: {
          ...emission.episode,
          duree: 1800,
          episode_page_url: 'https://example.com'
        },
        books: [],
        critiques: [],
        summary: '## Test Summary'
      });
    });
  });

  describe('🎹 RED Test: Navigation avec flèche gauche (←)', () => {
    it('devrait naviguer vers émission précédente (plus ancienne) avec ArrowLeft', async () => {
      // Arrange: Charger émission du 21 déc (index 0)
      await router.push('/emissions/20251221');
      wrapper = mount(Emissions, {
        global: {
          plugins: [router]
        },
        attachTo: document.body // Nécessaire pour keydown events
      });

      await flushPromises();
      await wrapper.vm.$nextTick();

      expect(wrapper.vm.selectedEmissionDetails.episode.titre).toBe('Émission du 21 déc');

      // Act: Simuler appui sur flèche gauche
      const keydownEvent = new KeyboardEvent('keydown', {
        key: 'ArrowLeft',
        code: 'ArrowLeft',
        bubbles: true
      });
      document.dispatchEvent(keydownEvent);

      await flushPromises();
      await wrapper.vm.$nextTick();

      // Assert: Doit naviguer vers 7 déc (plus ancien, index 1)
      expect(router.currentRoute.value.path).toBe('/emissions/20251207');
      expect(wrapper.vm.selectedEmissionDetails.episode.titre).toBe('Émission du 7 déc');

      wrapper.unmount();
    });

    it('ne devrait PAS naviguer si on est déjà sur la plus ancienne émission', async () => {
      // Arrange: Charger la plus ancienne émission (9 nov, index 2)
      await router.push('/emissions/20251109');
      wrapper = mount(Emissions, {
        global: {
          plugins: [router]
        },
        attachTo: document.body
      });

      await flushPromises();
      await wrapper.vm.$nextTick();

      expect(wrapper.vm.selectedEmissionDetails.episode.titre).toBe('Émission du 9 nov');

      // Act: Appuyer sur flèche gauche
      const keydownEvent = new KeyboardEvent('keydown', {
        key: 'ArrowLeft',
        code: 'ArrowLeft',
        bubbles: true
      });
      document.dispatchEvent(keydownEvent);

      await flushPromises();
      await wrapper.vm.$nextTick();

      // Assert: Doit rester sur 9 nov (pas de navigation possible)
      expect(router.currentRoute.value.path).toBe('/emissions/20251109');
      expect(wrapper.vm.selectedEmissionDetails.episode.titre).toBe('Émission du 9 nov');

      wrapper.unmount();
    });
  });

  describe('🎹 RED Test: Navigation avec flèche droite (→)', () => {
    it('devrait naviguer vers émission suivante (plus récente) avec ArrowRight', async () => {
      // Arrange: Charger émission du 7 déc (index 1)
      await router.push('/emissions/20251207');
      wrapper = mount(Emissions, {
        global: {
          plugins: [router]
        },
        attachTo: document.body
      });

      await flushPromises();
      await wrapper.vm.$nextTick();

      expect(wrapper.vm.selectedEmissionDetails.episode.titre).toBe('Émission du 7 déc');

      // Act: Simuler appui sur flèche droite
      const keydownEvent = new KeyboardEvent('keydown', {
        key: 'ArrowRight',
        code: 'ArrowRight',
        bubbles: true
      });
      document.dispatchEvent(keydownEvent);

      await flushPromises();
      await wrapper.vm.$nextTick();

      // Assert: Doit naviguer vers 21 déc (plus récent, index 0)
      expect(router.currentRoute.value.path).toBe('/emissions/20251221');
      expect(wrapper.vm.selectedEmissionDetails.episode.titre).toBe('Émission du 21 déc');

      wrapper.unmount();
    });

    it('ne devrait PAS naviguer si on est déjà sur la plus récente émission', async () => {
      // Arrange: Charger la plus récente émission (21 déc, index 0)
      await router.push('/emissions/20251221');
      wrapper = mount(Emissions, {
        global: {
          plugins: [router]
        },
        attachTo: document.body
      });

      await flushPromises();
      await wrapper.vm.$nextTick();

      expect(wrapper.vm.selectedEmissionDetails.episode.titre).toBe('Émission du 21 déc');

      // Act: Appuyer sur flèche droite
      const keydownEvent = new KeyboardEvent('keydown', {
        key: 'ArrowRight',
        code: 'ArrowRight',
        bubbles: true
      });
      document.dispatchEvent(keydownEvent);

      await flushPromises();
      await wrapper.vm.$nextTick();

      // Assert: Doit rester sur 21 déc (pas de navigation possible)
      expect(router.currentRoute.value.path).toBe('/emissions/20251221');
      expect(wrapper.vm.selectedEmissionDetails.episode.titre).toBe('Émission du 21 déc');

      wrapper.unmount();
    });
  });

  describe('🎹 RED Test: Nettoyage du listener au démontage', () => {
    it('devrait supprimer le listener keydown au démontage du composant', async () => {
      // Arrange
      const removeEventListenerSpy = vi.spyOn(document, 'removeEventListener');

      await router.push('/emissions/20251221');
      wrapper = mount(Emissions, {
        global: {
          plugins: [router]
        },
        attachTo: document.body
      });

      await flushPromises();

      // Act: Démonter le composant
      wrapper.unmount();

      // Assert: removeEventListener doit avoir été appelé avec 'keydown'
      expect(removeEventListenerSpy).toHaveBeenCalledWith('keydown', expect.any(Function));

      removeEventListenerSpy.mockRestore();
    });
  });

  describe('✅ Scenario complet: Navigation combinée souris + clavier', () => {
    it('devrait permettre de naviguer avec boutons ET clavier sans conflit', async () => {
      // Étape 1: Charger émission du milieu (7 déc)
      await router.push('/emissions/20251207');
      wrapper = mount(Emissions, {
        global: {
          plugins: [router]
        },
        attachTo: document.body
      });

      await flushPromises();
      await wrapper.vm.$nextTick();

      expect(wrapper.vm.selectedEmissionDetails.episode.titre).toBe('Émission du 7 déc');

      // Étape 2: Flèche droite → 21 déc (plus récent)
      let keyEvent = new KeyboardEvent('keydown', { key: 'ArrowRight', bubbles: true });
      document.dispatchEvent(keyEvent);
      await flushPromises();
      await wrapper.vm.$nextTick();

      expect(router.currentRoute.value.path).toBe('/emissions/20251221');
      expect(wrapper.vm.selectedEmissionDetails.episode.titre).toBe('Émission du 21 déc');

      // Étape 3: Clic sur bouton Précédent → 7 déc
      const prevButton = wrapper.find('[data-testid="prev-emission-button"]');
      await prevButton.trigger('click');
      await flushPromises();
      await wrapper.vm.$nextTick();

      expect(router.currentRoute.value.path).toBe('/emissions/20251207');
      expect(wrapper.vm.selectedEmissionDetails.episode.titre).toBe('Émission du 7 déc');

      // Étape 4: Flèche gauche → 9 nov (plus ancien)
      keyEvent = new KeyboardEvent('keydown', { key: 'ArrowLeft', bubbles: true });
      document.dispatchEvent(keyEvent);
      await flushPromises();
      await wrapper.vm.$nextTick();

      expect(router.currentRoute.value.path).toBe('/emissions/20251109');
      expect(wrapper.vm.selectedEmissionDetails.episode.titre).toBe('Émission du 9 nov');

      wrapper.unmount();
    });
  });
});
