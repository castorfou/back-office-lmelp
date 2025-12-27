/**
 * Tests TDD pour la navigation des émissions (Issue #154)
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { mount } from '@vue/test-utils';
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

describe('Emissions - Navigation Tests (TDD)', () => {
  let router;
  let wrapper;

  const mockEmissions = [
    {
      id: 'emission-1',
      date: '2025-12-21T10:00:00',
      episode: { titre: 'Émission du 21 déc', date: '2025-12-21T10:00:00' }
    },
    {
      id: 'emission-2',
      date: '2025-12-14T10:00:00',
      episode: { titre: 'Émission du 14 déc', date: '2025-12-14T10:00:00' }
    },
    {
      id: 'emission-3',
      date: '2025-12-07T10:00:00',
      episode: { titre: 'Émission du 7 déc', date: '2025-12-07T10:00:00' }
    }
  ];

  const mockEmissionDetails = {
    emission: { id: 'emission-1' },
    episode: {
      titre: 'Émission du 21 déc',
      date: '2025-12-21T10:00:00',
      duree: 1800,
      episode_page_url: 'https://example.com'
    },
    books: [],
    critiques: [],
    summary: '## Test'
  };

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

    // Mock getEmissionByDate pour retourner l'émission correspondante à la date
    emissionsService.getEmissionByDate.mockImplementation((dateStr) => {
      const emission = mockEmissions.find(e => {
        const emissionDate = new Date(e.date);
        const expectedDate = `${emissionDate.getFullYear()}${String(emissionDate.getMonth() + 1).padStart(2, '0')}${String(emissionDate.getDate()).padStart(2, '0')}`;
        return expectedDate === dateStr;
      });

      if (!emission) return Promise.reject(new Error('Émission non trouvée'));

      return Promise.resolve({
        emission: { id: emission.id },
        episode: emission.episode,
        books: [],
        critiques: [],
        summary: '## Test'
      });
    });
  });

  describe('RED Test: Chargement des détails au changement de route', () => {
    it('devrait charger les détails quand route.params.date change', async () => {
      // Arrange: Démarrer sur la première émission
      await router.push('/emissions/20251221');
      wrapper = mount(Emissions, {
        global: {
          plugins: [router]
        }
      });

      await wrapper.vm.$nextTick();
      await new Promise(resolve => setTimeout(resolve, 100));

      // Vérifier que les détails de la première émission sont chargés
      expect(emissionsService.getEmissionByDate).toHaveBeenCalledWith('20251221');
      expect(wrapper.vm.selectedEmissionDetails).toBeTruthy();

      // Act: Changer vers une autre émission via l'URL
      vi.clearAllMocks();
      emissionsService.getEmissionByDate.mockResolvedValue({
        ...mockEmissionDetails,
        episode: { ...mockEmissionDetails.episode, titre: 'Émission du 14 déc' }
      });

      await router.push('/emissions/20251214');
      await wrapper.vm.$nextTick();
      await new Promise(resolve => setTimeout(resolve, 100));

      // Assert: Les nouveaux détails doivent être chargés
      expect(emissionsService.getEmissionByDate).toHaveBeenCalledWith('20251214');
      expect(wrapper.vm.selectedEmissionDetails.episode.titre).toBe('Émission du 14 déc');
    });
  });

  describe('RED Test: Ordre de navigation correct', () => {
    it('Précédent devrait aller vers émission PLUS ANCIENNE (index + 1)', async () => {
      // Arrange: Émissions triées DESC (plus récent d'abord)
      // Index 0: 21 déc (plus récent)
      // Index 1: 14 déc
      // Index 2: 7 déc (plus ancien)

      await router.push('/emissions/20251221'); // Émission index 0
      wrapper = mount(Emissions, {
        global: {
          plugins: [router]
        }
      });

      await wrapper.vm.$nextTick();
      await new Promise(resolve => setTimeout(resolve, 100));

      // Act: Cliquer sur "Précédent"
      const prevButton = wrapper.find('[data-testid="prev-emission-button"]');
      expect(prevButton.exists()).toBe(true);
      expect(prevButton.attributes('disabled')).toBeUndefined();

      await prevButton.trigger('click');
      await wrapper.vm.$nextTick();
      await new Promise(resolve => setTimeout(resolve, 100));

      // Assert: Doit naviguer vers 14 déc (index 1, plus ancien)
      expect(router.currentRoute.value.path).toBe('/emissions/20251214');
    });

    it('Suivant devrait aller vers émission PLUS RÉCENTE (index - 1)', async () => {
      // Arrange: Commencer à index 1 (14 déc)
      await router.push('/emissions/20251214');
      wrapper = mount(Emissions, {
        global: {
          plugins: [router]
        }
      });

      await wrapper.vm.$nextTick();
      await new Promise(resolve => setTimeout(resolve, 100));

      // Act: Cliquer sur "Suivant"
      const nextButton = wrapper.find('[data-testid="next-emission-button"]');
      expect(nextButton.exists()).toBe(true);
      expect(nextButton.attributes('disabled')).toBeUndefined();

      await nextButton.trigger('click');
      await wrapper.vm.$nextTick();
      await new Promise(resolve => setTimeout(resolve, 100));

      // Assert: Doit naviguer vers 21 déc (index 0, plus récent)
      expect(router.currentRoute.value.path).toBe('/emissions/20251221');
    });

    it('Précédent devrait être désactivé pour la PLUS ANCIENNE émission', async () => {
      // Arrange: Aller à la dernière émission (7 déc, index 2)
      await router.push('/emissions/20251207');
      wrapper = mount(Emissions, {
        global: {
          plugins: [router]
        }
      });

      await wrapper.vm.$nextTick();
      await new Promise(resolve => setTimeout(resolve, 100));

      // Assert: Précédent doit être désactivé (pas d'émission plus ancienne)
      const prevButton = wrapper.find('[data-testid="prev-emission-button"]');
      expect(prevButton.attributes('disabled')).toBeDefined();
    });

    it('Suivant devrait être désactivé pour la PLUS RÉCENTE émission', async () => {
      // Arrange: Aller à la première émission (21 déc, index 0)
      await router.push('/emissions/20251221');
      wrapper = mount(Emissions, {
        global: {
          plugins: [router]
        }
      });

      await wrapper.vm.$nextTick();
      await new Promise(resolve => setTimeout(resolve, 100));

      // Assert: Suivant doit être désactivé (pas d'émission plus récente)
      const nextButton = wrapper.find('[data-testid="next-emission-button"]');
      expect(nextButton.attributes('disabled')).toBeDefined();
    });
  });
});
