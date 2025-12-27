/**
 * Tests du flux utilisateur réel pour la page Émissions (Issue #154 - Bug fix)
 *
 * Ces tests reproduisent les problèmes rapportés par l'utilisateur:
 * 1. Les boutons Précédent/Suivant ne fonctionnent pas
 * 2. Changer d'émission via dropdown ne met pas à jour le contenu
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

describe('Emissions - User Flow Tests (Bug Fix)', () => {
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
        books: [
          { auteur: 'Guillaume Poix', titre: 'Livre Test' }
        ],
        critiques: [
          { id: '123', nom: 'Jérôme Garcin', animateur: true }
        ],
        summary: '## Test Summary'
      });
    });
  });

  describe('🐛 Bug 1: Boutons Précédent/Suivant ne fonctionnent pas', () => {
    it('RED: devrait naviguer vers émission précédente au clic sur Précédent', async () => {
      // Arrange: Charger émission du 21 déc (index 0)
      await router.push('/emissions/20251221');
      wrapper = mount(Emissions, {
        global: {
          plugins: [router]
        }
      });

      await flushPromises();
      await wrapper.vm.$nextTick();

      // Vérifier que l'émission du 21 déc est bien chargée
      expect(wrapper.vm.selectedEmissionDetails.episode.titre).toBe('Émission du 21 déc');

      // Act: Cliquer sur bouton Précédent
      const prevButton = wrapper.find('[data-testid="prev-emission-button"]');
      expect(prevButton.exists()).toBe(true);
      expect(prevButton.attributes('disabled')).toBeUndefined();

      await prevButton.trigger('click');
      await flushPromises();
      await wrapper.vm.$nextTick();

      // Assert: Doit être sur l'émission du 7 déc (plus ancienne, index 1)
      expect(router.currentRoute.value.path).toBe('/emissions/20251207');
      expect(wrapper.vm.selectedEmissionDetails.episode.titre).toBe('Émission du 7 déc');
    });

    it('RED: devrait naviguer vers émission suivante au clic sur Suivant', async () => {
      // Arrange: Charger émission du 7 déc (index 1)
      await router.push('/emissions/20251207');
      wrapper = mount(Emissions, {
        global: {
          plugins: [router]
        }
      });

      await flushPromises();
      await wrapper.vm.$nextTick();

      // Vérifier que l'émission du 7 déc est bien chargée
      expect(wrapper.vm.selectedEmissionDetails.episode.titre).toBe('Émission du 7 déc');

      // Act: Cliquer sur bouton Suivant
      const nextButton = wrapper.find('[data-testid="next-emission-button"]');
      expect(nextButton.exists()).toBe(true);
      expect(nextButton.attributes('disabled')).toBeUndefined();

      await nextButton.trigger('click');
      await flushPromises();
      await wrapper.vm.$nextTick();

      // Assert: Doit être sur l'émission du 21 déc (plus récente, index 0)
      expect(router.currentRoute.value.path).toBe('/emissions/20251221');
      expect(wrapper.vm.selectedEmissionDetails.episode.titre).toBe('Émission du 21 déc');
    });
  });

  describe('🐛 Bug 2: Changement d\'émission via dropdown ne met pas à jour le contenu', () => {
    it('RED: devrait mettre à jour le contenu au changement de sélection dropdown', async () => {
      // Arrange: Charger émission du 21 déc
      await router.push('/emissions/20251221');
      wrapper = mount(Emissions, {
        global: {
          plugins: [router]
        }
      });

      await flushPromises();
      await wrapper.vm.$nextTick();

      expect(wrapper.vm.selectedEmissionDetails.episode.titre).toBe('Émission du 21 déc');

      // Act: Changer de sélection via dropdown (simuler onEmissionChange)
      const newEmissionId = 'emission-07dec';
      await wrapper.vm.onEmissionChange(newEmissionId);
      await flushPromises();
      await wrapper.vm.$nextTick();

      // Assert: Le contenu doit être mis à jour
      expect(router.currentRoute.value.path).toBe('/emissions/20251207');
      expect(wrapper.vm.selectedEmissionDetails.episode.titre).toBe('Émission du 7 déc');
    });

    it('RED: devrait afficher les détails complets de la nouvelle émission', async () => {
      // Arrange: Charger émission du 21 déc
      await router.push('/emissions/20251221');
      wrapper = mount(Emissions, {
        global: {
          plugins: [router]
        }
      });

      await flushPromises();
      await wrapper.vm.$nextTick();

      // Act: Changer vers émission du 7 déc
      await wrapper.vm.onEmissionChange('emission-07dec');
      await flushPromises();
      await wrapper.vm.$nextTick();

      // Assert: Tous les détails doivent être présents
      expect(wrapper.vm.selectedEmissionDetails).toBeTruthy();
      expect(wrapper.vm.selectedEmissionDetails.books).toHaveLength(1);
      expect(wrapper.vm.selectedEmissionDetails.critiques).toHaveLength(1);
      expect(wrapper.vm.selectedEmissionDetails.summary).toBe('## Test Summary');
    });
  });

  describe('✅ Scenario complet: Navigation complète entre 3 émissions', () => {
    it('devrait permettre de naviguer dans toutes les directions sans blocage', async () => {
      // Étape 1: Charger émission du milieu (7 déc)
      await router.push('/emissions/20251207');
      wrapper = mount(Emissions, {
        global: {
          plugins: [router]
        }
      });

      await flushPromises();
      await wrapper.vm.$nextTick();

      expect(wrapper.vm.selectedEmissionDetails.episode.titre).toBe('Émission du 7 déc');

      // Étape 2: Aller vers Suivant (21 déc, plus récent)
      const nextButton = wrapper.find('[data-testid="next-emission-button"]');
      await nextButton.trigger('click');
      await flushPromises();
      await wrapper.vm.$nextTick();

      expect(router.currentRoute.value.path).toBe('/emissions/20251221');
      expect(wrapper.vm.selectedEmissionDetails.episode.titre).toBe('Émission du 21 déc');

      // Étape 3: Aller vers Précédent (7 déc)
      const prevButton = wrapper.find('[data-testid="prev-emission-button"]');
      await prevButton.trigger('click');
      await flushPromises();
      await wrapper.vm.$nextTick();

      expect(router.currentRoute.value.path).toBe('/emissions/20251207');
      expect(wrapper.vm.selectedEmissionDetails.episode.titre).toBe('Émission du 7 déc');

      // Étape 4: Encore Précédent (9 nov, plus ancien)
      await prevButton.trigger('click');
      await flushPromises();
      await wrapper.vm.$nextTick();

      expect(router.currentRoute.value.path).toBe('/emissions/20251109');
      expect(wrapper.vm.selectedEmissionDetails.episode.titre).toBe('Émission du 9 nov');

      // Étape 5: Précédent doit être désactivé (plus ancienne émission)
      expect(prevButton.attributes('disabled')).toBeDefined();
    });
  });
});
