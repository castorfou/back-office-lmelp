/**
 * Tests TDD pour l'affichage des stats de matching Phase 4 (Issue #185)
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { mount } from '@vue/test-utils';
import { createRouter, createMemoryHistory } from 'vue-router';
import Emissions from '../../src/views/Emissions.vue';
import { emissionsService, avisService } from '../../src/services/api';

// Mock des services
vi.mock('../../src/services/api', () => ({
  emissionsService: {
    getAllEmissions: vi.fn(),
    getEmissionByDate: vi.fn(),
    getEmissionDetails: vi.fn(),
  },
  avisService: {
    mergeDuplicateBooks: vi.fn(),
  },
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

describe('Emissions - Livres Mongo non cités (TDD Issue #267)', () => {
  let router;
  let wrapper;

  const mockEmissions = [
    {
      id: 'emission-1',
      date: '2026-01-18T10:00:00',
      episode: { titre: 'Émission du 18 janv', date: '2026-01-18T10:00:00' }
    }
  ];

  const mockEmissionDetailsWithEcart = {
    emission: { id: 'emission-1' },
    episode: {
      titre: 'Émission du 18 janv',
      date: '2026-01-18T10:00:00'
    },
    books: [
      { _id: 'livre1', titre: 'Protocoles', auteur: 'Constance Debré' },
    ],
    avis: [],
    avis_matching_stats: {
      livres_summary: 1,
      livres_mongo: 3,
      livres_mongo_non_cites: [
        { livre_oid: 'livre2', titre: 'Paris', auteur: 'Annemarie Schwarzenbach' },
        { livre_oid: 'livre3', titre: 'Un roman', auteur: 'Un auteur' },
      ],
      match_phase1: 1,
      match_phase2: 0,
      match_phase3: 0,
      match_phase4: 0,
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
    emissionsService.getEmissionDetails.mockResolvedValue({ data: mockEmissionDetailsWithEcart });
  });

  it('should display the list of livres_mongo_non_cites when counts mismatch', async () => {
    /**
     * TDD RED (Issue #267): quand livres_summary != livres_mongo, l'écran doit
     * lister explicitement les livres MongoDB non cités par l'avis critique,
     * au lieu de se limiter à deux compteurs opaques.
     */
    wrapper = await createWrapper();
    await wrapper.vm.$nextTick();

    wrapper.vm.selectedEmission = mockEmissions[0];
    wrapper.vm.selectedEmissionDetails = mockEmissionDetailsWithEcart;
    wrapper.vm.avisMatchingStats = mockEmissionDetailsWithEcart.avis_matching_stats;
    await wrapper.vm.$nextTick();

    const html = wrapper.html();

    expect(html).toContain('Paris');
    expect(html).toContain('Annemarie Schwarzenbach');
    expect(html).toContain('Un roman');
  });

  it('should use unambiguous labels for livres_summary and livres_mongo', async () => {
    /**
     * TDD (Issue #267): "Livres summary" et "Livres Mongo" sont des libellés
     * ambigus qui ne clarifient pas l'origine des deux comptages.
     */
    wrapper = await createWrapper();
    await wrapper.vm.$nextTick();

    wrapper.vm.selectedEmission = mockEmissions[0];
    wrapper.vm.selectedEmissionDetails = mockEmissionDetailsWithEcart;
    wrapper.vm.avisMatchingStats = mockEmissionDetailsWithEcart.avis_matching_stats;
    await wrapper.vm.$nextTick();

    const html = wrapper.html();

    expect(html).toContain('Livres cités dans l\'avis critique');
    expect(html).toContain('Livres liés à cet épisode en base');
  });
});

describe('Emissions - Fusion de doublons probables (TDD Issue #267)', () => {
  let router;
  let wrapper;

  const mockEmissions = [
    {
      id: 'emission-1',
      date: '2026-01-18T10:00:00',
      episode: { titre: 'Émission du 18 janv', date: '2026-01-18T10:00:00' }
    }
  ];

  const mockEmissionDetailsWithDuplicate = {
    emission: { id: 'emission-1' },
    episode: {
      titre: 'Émission du 18 janv',
      date: '2026-01-18T10:00:00'
    },
    books: [
      { _id: 'livre-cite', titre: "L'affaire Alaska Sanders", auteur: 'Joël Dicker' },
    ],
    avis: [],
    avis_matching_stats: {
      livres_summary: 1,
      livres_mongo: 2,
      livres_mongo_non_cites: [
        {
          livre_oid: 'livre-doublon',
          titre: "L'Affaire Alaska Sanders",
          auteur: 'Joël Dicker',
          doublon_probable_de: 'livre-cite',
          url_babelio: 'https://www.babelio.com/livres/Dicker-LAffaire-Alaska-Sanders/1380950',
        },
      ],
      match_phase1: 1,
      match_phase2: 0,
      match_phase3: 0,
      match_phase4: 0,
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
    emissionsService.getEmissionDetails.mockResolvedValue({ data: mockEmissionDetailsWithDuplicate });
  });

  it('should display a "Doublon probable" badge and a merge button', async () => {
    /**
     * TDD RED (Issue #267): un livre en écart dont le titre normalisé
     * correspond à un livre déjà cité doit afficher un badge et un bouton
     * de fusion, au lieu d'être présenté comme un simple écart opaque.
     */
    wrapper = await createWrapper();
    await wrapper.vm.$nextTick();

    wrapper.vm.selectedEmission = mockEmissions[0];
    wrapper.vm.selectedEmissionDetails = mockEmissionDetailsWithDuplicate;
    wrapper.vm.avisMatchingStats = mockEmissionDetailsWithDuplicate.avis_matching_stats;
    await wrapper.vm.$nextTick();

    const html = wrapper.html();

    expect(html).toContain('Doublon probable');
    const button = wrapper.find('[data-testid="merge-duplicate-livre-doublon"]');
    expect(button.exists()).toBe(true);
  });

  it('should call avisService.mergeDuplicateBooks when clicking the merge button', async () => {
    /**
     * TDD: le clic sur le bouton de fusion doit appeler l'API de fusion
     * existante avec l'URL Babelio et les deux book_ids concernés.
     */
    avisService.mergeDuplicateBooks.mockResolvedValue({ status: 'success' });

    wrapper = await createWrapper();
    await wrapper.vm.$nextTick();

    wrapper.vm.selectedEmission = mockEmissions[0];
    wrapper.vm.selectedEmissionDetails = mockEmissionDetailsWithDuplicate;
    wrapper.vm.avisMatchingStats = mockEmissionDetailsWithDuplicate.avis_matching_stats;
    await wrapper.vm.$nextTick();

    const button = wrapper.find('[data-testid="merge-duplicate-livre-doublon"]');
    await button.trigger('click');
    await wrapper.vm.$nextTick();

    expect(avisService.mergeDuplicateBooks).toHaveBeenCalledWith(
      'https://www.babelio.com/livres/Dicker-LAffaire-Alaska-Sanders/1380950',
      expect.arrayContaining(['livre-doublon', 'livre-cite'])
    );
  });
});
