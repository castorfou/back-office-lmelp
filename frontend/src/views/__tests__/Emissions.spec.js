/**
 * Tests pour le composant Emissions.vue
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount } from '@vue/test-utils';
import { createRouter, createMemoryHistory } from 'vue-router';
import Emissions from '../Emissions.vue';
import { emissionsService, avisService } from '@/services/api';

// Mock des services API
vi.mock('@/services/api', () => ({
  emissionsService: {
    getAll: vi.fn(),
    getAllEmissions: vi.fn(),
    getByDate: vi.fn(),
    getEmissionByDate: vi.fn(),
    createFromEpisode: vi.fn(),
  },
  avisService: {
    getAvisByEmission: vi.fn(),
    extractAvis: vi.fn(),
  },
  episodeService: {
    getEpisodes: vi.fn(),
    fetchEpisodePageUrl: vi.fn().mockResolvedValue(null),
  },
}));

// Note: The test "should reload matching_stats after reextractAvis (Issue #185)"
// was removed because the reextractAvis functionality is now covered by the
// integration test "should update badge_status from no_avis to perfect after
// auto-extraction" which tests the same scenario end-to-end.

describe('Emissions.vue - Auto-selection by badge priority', () => {
  let wrapper;
  let router;

  beforeEach(() => {
    vi.resetAllMocks();

    // Setup router
    router = createRouter({
      history: createMemoryHistory(),
      routes: [
        {
          path: '/emissions/:date?',
          name: 'emissions',
          component: Emissions,
        },
      ],
    });
  });

  it('should auto-select most recent count_mismatch (🔴) emission when no date param', async () => {
    // Mock emissions with different badge statuses
    // Triées par date DESC (plus récente en premier)
    emissionsService.getAllEmissions = vi.fn().mockResolvedValue([
      {
        id: 'emission1',
        date: '2025-10-15T10:00:00',
        badge_status: 'perfect', // 🟢 Plus récente mais verte
        episode: { titre: 'Émission récente verte' },
      },
      {
        id: 'emission2',
        date: '2025-10-10T10:00:00',
        badge_status: 'count_mismatch', // 🔴 PRIORITÉ 1
        episode: { titre: 'Émission rouge' },
      },
      {
        id: 'emission3',
        date: '2025-10-05T10:00:00',
        badge_status: 'unmatched', // 🟡 Moins récente
        episode: { titre: 'Émission jaune' },
      },
      {
        id: 'emission4',
        date: '2025-09-30T10:00:00',
        badge_status: 'no_avis', // ⚪ Encore moins récente
        episode: { titre: 'Émission grise' },
      },
    ]);

    // Navigate to /emissions WITHOUT date param
    await router.push('/emissions');
    await router.isReady();

    // Mount component
    wrapper = mount(Emissions, {
      global: {
        plugins: [router],
        stubs: {
          AvisTable: true,
          EpisodeDropdown: true,
        },
      },
    });

    await wrapper.vm.$nextTick();
    await new Promise((resolve) => setTimeout(resolve, 100));

    // CRITICAL: Should redirect to most recent count_mismatch (🔴), NOT most recent overall
    expect(router.currentRoute.value.params.date).toBe('20251010'); // emission2 (rouge)
  });

  it('should auto-select most recent unmatched (🟡) if no count_mismatch', async () => {
    emissionsService.getAllEmissions = vi.fn().mockResolvedValue([
      {
        id: 'emission1',
        date: '2025-10-15T10:00:00',
        badge_status: 'perfect', // 🟢 Plus récente mais verte
        episode: { titre: 'Émission verte' },
      },
      {
        id: 'emission2',
        date: '2025-10-10T10:00:00',
        badge_status: 'unmatched', // 🟡 PRIORITÉ 2
        episode: { titre: 'Émission jaune' },
      },
      {
        id: 'emission3',
        date: '2025-10-05T10:00:00',
        badge_status: 'no_avis', // ⚪
        episode: { titre: 'Émission grise' },
      },
    ]);

    await router.push('/emissions');
    await router.isReady();

    wrapper = mount(Emissions, {
      global: {
        plugins: [router],
        stubs: {
          AvisTable: true,
          EpisodeDropdown: true,
        },
      },
    });

    await wrapper.vm.$nextTick();
    await new Promise((resolve) => setTimeout(resolve, 100));

    expect(router.currentRoute.value.params.date).toBe('20251010'); // emission2 (jaune)
  });

  it('should auto-select most recent no_avis (⚪) if no count_mismatch or unmatched', async () => {
    emissionsService.getAllEmissions = vi.fn().mockResolvedValue([
      {
        id: 'emission1',
        date: '2025-10-15T10:00:00',
        badge_status: 'perfect', // 🟢 Plus récente mais verte
        episode: { titre: 'Émission verte' },
      },
      {
        id: 'emission2',
        date: '2025-10-10T10:00:00',
        badge_status: 'no_avis', // ⚪ PRIORITÉ 3
        episode: { titre: 'Émission grise' },
      },
    ]);

    await router.push('/emissions');
    await router.isReady();

    wrapper = mount(Emissions, {
      global: {
        plugins: [router],
        stubs: {
          AvisTable: true,
          EpisodeDropdown: true,
        },
      },
    });

    await wrapper.vm.$nextTick();
    await new Promise((resolve) => setTimeout(resolve, 100));

    expect(router.currentRoute.value.params.date).toBe('20251010'); // emission2 (grise)
  });

  it('should fallback to most recent perfect (🟢) if only perfect emissions', async () => {
    emissionsService.getAllEmissions = vi.fn().mockResolvedValue([
      {
        id: 'emission1',
        date: '2025-10-15T10:00:00',
        badge_status: 'perfect', // 🟢 Plus récente
        episode: { titre: 'Émission verte récente' },
      },
      {
        id: 'emission2',
        date: '2025-10-10T10:00:00',
        badge_status: 'perfect', // 🟢
        episode: { titre: 'Émission verte plus ancienne' },
      },
    ]);

    await router.push('/emissions');
    await router.isReady();

    wrapper = mount(Emissions, {
      global: {
        plugins: [router],
        stubs: {
          AvisTable: true,
          EpisodeDropdown: true,
        },
      },
    });

    await wrapper.vm.$nextTick();
    await new Promise((resolve) => setTimeout(resolve, 100));

    expect(router.currentRoute.value.params.date).toBe('20251015'); // emission1 (la plus récente)
  });
});

describe('Emissions.vue - Badge update after extraction', () => {
  let wrapper;
  let router;

  beforeEach(() => {
    vi.resetAllMocks();

    // Setup router
    router = createRouter({
      history: createMemoryHistory(),
      routes: [
        {
          path: '/emissions/:date?',
          name: 'emissions',
          component: Emissions,
        },
      ],
    });
  });

  it('should update badge_status from no_avis to perfect after auto-extraction', async () => {
    // Mock initial emissions list with no_avis (⚪)
    const initialEmissions = [
      {
        id: 'emission1',
        date: '2025-10-15T10:00:00',
        badge_status: 'no_avis', // ⚪ Pas d'avis extraits
        episode: { titre: 'Émission test', episode_id: 'episode1' },
      },
    ];

    emissionsService.getAllEmissions = vi.fn().mockResolvedValue(initialEmissions);

    // Mock getEmissionByDate - returns emission details
    emissionsService.getEmissionByDate = vi.fn().mockResolvedValue({
      emission: {
        id: 'emission1',
        date: '2025-10-15T10:00:00',
        episode_id: 'episode1',
      },
      episode: { titre: 'Émission test' },
    });

    // Mock getAvisByEmission - initial call returns empty (triggers auto-extraction)
    avisService.getAvisByEmission.mockResolvedValueOnce({
      avis: [],
      matching_stats: null,
    });

    // Mock extractAvis - successful extraction
    avisService.extractAvis.mockResolvedValue({
      extracted_count: 5,
      matching_stats: {
        livres_summary: 5,
        livres_mongo: 5,
        match_phase1: 5,
        match_phase2: 0,
        match_phase3: 0,
        match_phase4: 0,
        unmatched: 0,
      },
    });

    // Mock getAvisByEmission - reload after extraction returns avis
    avisService.getAvisByEmission.mockResolvedValueOnce({
      avis: [
        { id: 'avis1', livre_titre_extrait: 'Livre 1' },
        { id: 'avis2', livre_titre_extrait: 'Livre 2' },
      ],
      matching_stats: {
        livres_summary: 5,
        livres_mongo: 5,
        match_phase1: 5,
        match_phase2: 0,
        match_phase3: 0,
        match_phase4: 0,
        unmatched: 0,
      },
    });

    // Mock getAllEmissions - second call after extraction returns updated badge
    const updatedEmissions = [
      {
        id: 'emission1',
        date: '2025-10-15T10:00:00',
        badge_status: 'perfect', // 🟢 Maintenant perfect
        episode: { titre: 'Émission test', episode_id: 'episode1' },
      },
    ];

    emissionsService.getAllEmissions.mockResolvedValueOnce(updatedEmissions);

    // Navigate to /emissions with date
    await router.push('/emissions/20251015');
    await router.isReady();

    // Mount component
    wrapper = mount(Emissions, {
      global: {
        plugins: [router],
        stubs: {
          AvisTable: true,
          EpisodeDropdown: true,
        },
      },
    });

    await wrapper.vm.$nextTick();
    // Wait for auto-extraction to complete
    await new Promise((resolve) => setTimeout(resolve, 500));

    // CRITICAL: Badge should be updated from no_avis (⚪) to perfect (🟢)
    const emission = wrapper.vm.emissions.find(e => e.id === 'emission1');
    expect(emission.badge_status).toBe('perfect');

    // Verify counters are updated
    expect(wrapper.vm.emissionsNoAvisCount).toBe(0); // Was 1, now 0
    expect(wrapper.vm.emissionsPerfectCount).toBe(1); // Was 0, now 1
  });
});
