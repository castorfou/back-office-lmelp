/**
 * Tests TDD pour l'affichage des stats de matching Phase 4 (Issue #185)
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

describe('Emissions - Matching Stats Display (TDD Issue #185)', () => {
  let router;
  let wrapper;

  const mockEmissions = [
    {
      id: 'emission-1',
      date: '2026-01-18T10:00:00',
      episode: { titre: 'Émission du 18 janv', date: '2026-01-18T10:00:00' }
    }
  ];

  const mockEmissionDetailsWithPhase4 = {
    emission: { id: 'emission-1' },
    episode: {
      titre: 'Émission du 18 janv',
      date: '2026-01-18T10:00:00'
    },
    books: [
      { _id: 'livre1', titre: 'Protocoles', auteur: 'Constance Debré' },
      { _id: 'livre2', titre: 'Paris', auteur: 'Annemarie Schwarzenbach' }
    ],
    avis: [],
    avis_matching_stats: {
      livres_summary: 2,
      livres_mongo: 2,
      match_phase1: 1,
      match_phase2: 0,
      match_phase3: 0,
      match_phase4: 1,  // Phase 4 fuzzy match!
      unmatched: 0
    }
  };

  const createWrapper = async () => {
    router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/', component: { template: '<div>Home</div>' } },
        { path: '/emissions', component: Emissions },
        { path: '/livre/:id', component: { template: '<div>Livre</div>' } },
        { path: '/auteur/:id', component: { template: '<div>Auteur</div>' } },
      ],
    });

    await router.push('/emissions');
    await router.isReady();

    return mount(Emissions, {
      global: {
        plugins: [router],
        stubs: {
          AvisTable: true
        }
      },
    });
  };

  beforeEach(() => {
    vi.clearAllMocks();
    emissionsService.getAllEmissions.mockResolvedValue({ data: mockEmissions });
    emissionsService.getEmissionDetails.mockResolvedValue({ data: mockEmissionDetailsWithPhase4 });
  });

  it('should display Phase 4 (fuzzy) stats when present', async () => {
    /**
     * TDD RED: Ce test vérifie que les stats Phase 4 sont affichées.
     *
     * Actuellement le frontend n'affiche que Phase 1, 2, 3.
     * Ce test doit échouer jusqu'à ce qu'on ajoute Phase 4.
     */
    wrapper = await createWrapper();
    await wrapper.vm.$nextTick();

    // Simuler la sélection d'une émission
    wrapper.vm.selectedEmission = mockEmissions[0];
    wrapper.vm.selectedEmissionDetails = mockEmissionDetailsWithPhase4;
    wrapper.vm.avisMatchingStats = mockEmissionDetailsWithPhase4.avis_matching_stats;
    await wrapper.vm.$nextTick();

    const html = wrapper.html();

    // Vérifier que Phase 4 est affichée
    expect(html).toContain('Phase 4');
    expect(html).toContain('fuzzy');
  });

  it('should not display Phase 4 stats when value is 0', async () => {
    /**
     * TDD: Phase 4 ne devrait pas être affichée si match_phase4 == 0
     */
    const statsWithoutPhase4 = {
      ...mockEmissionDetailsWithPhase4,
      avis_matching_stats: {
        livres_summary: 2,
        livres_mongo: 2,
        match_phase1: 2,
        match_phase2: 0,
        match_phase3: 0,
        match_phase4: 0,
        unmatched: 0
      }
    };

    emissionsService.getEmissionDetails.mockResolvedValue({ data: statsWithoutPhase4 });

    wrapper = await createWrapper();
    await wrapper.vm.$nextTick();

    wrapper.vm.selectedEmission = mockEmissions[0];
    wrapper.vm.selectedEmissionDetails = statsWithoutPhase4;
    wrapper.vm.avisMatchingStats = statsWithoutPhase4.avis_matching_stats;
    await wrapper.vm.$nextTick();

    const html = wrapper.html();

    // Phase 4 ne devrait pas apparaître si == 0
    expect(html).not.toContain('Phase 4');
  });
});
