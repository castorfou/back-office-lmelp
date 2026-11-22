/**
 * Page Émissions : écarter un titre du résumé qui n'est pas un livre,
 * et le rétablir (Issue #380).
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { createRouter, createMemoryHistory } from 'vue-router';
import Emissions from '../../src/views/Emissions.vue';
import { emissionsService, avisService } from '../../src/services/api';

vi.mock('../../src/services/api', () => ({
  emissionsService: {
    getAllEmissions: vi.fn(),
    getEmissionByDate: vi.fn(),
    getEmissionDetails: vi.fn(),
  },
  avisService: {
    mergeDuplicateBooks: vi.fn(),
    getAvisByEmission: vi.fn(),
    extractAvis: vi.fn(),
    ecarterLivre: vi.fn(),
    retablirLivre: vi.fn(),
  },
}));

vi.mock('marked', () => ({
  marked: vi.fn((text) => text),
}));

const TITRE = "Divers titres à l'École des loisirs";
const AUTEUR = 'Geneviève Brisac (dir.)';
const LIVRE_ECARTE = { titre: TITRE, auteur: AUTEUR, ecarte_le: '2026-11-22T10:00:00' };

describe('Emissions - Titres écartés (Issue #380)', () => {
  const emission = {
    id: 'emission-1',
    date: '2016-04-24T10:00:00',
    badge_status: 'count_mismatch',
  };

  const statsAvecSansMatch = {
    livres_summary: 9,
    livres_mongo: 8,
    livres_mongo_non_cites: [],
    livres_summary_sans_match: [{ titre: TITRE, auteur: AUTEUR }],
    match_phase1: 8,
    match_phase2: 0,
    match_phase3: 0,
    match_phase4: 0,
    unmatched: 1,
  };

  const createWrapper = async () => {
    const router = createRouter({
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
    const wrapper = mount(Emissions, {
      global: { plugins: [router], stubs: { AvisTable: true } },
    });
    await flushPromises();
    return wrapper;
  };

  const selectEmission = async (wrapper, { badge = 'count_mismatch', stats, ecartes }) => {
    wrapper.vm.emissions = [{ ...emission, badge_status: badge }];
    wrapper.vm.selectedEmissionId = emission.id;
    wrapper.vm.selectedEmissionDetails = { emission: { id: emission.id }, episode: {}, books: [] };
    wrapper.vm.avisMatchingStats = stats;
    wrapper.vm.livresEcartes = ecartes;
    await wrapper.vm.$nextTick();
  };

  beforeEach(() => {
    vi.resetAllMocks();
    emissionsService.getAllEmissions.mockResolvedValue([]);
    avisService.extractAvis.mockResolvedValue({ extracted_count: 8 });
  });

  it('« Ignorer ce livre » écarte le titre puis ré-extrait les avis', async () => {
    const wrapper = await createWrapper();
    await selectEmission(wrapper, { stats: statsAvecSansMatch, ecartes: [] });

    avisService.ecarterLivre.mockResolvedValueOnce({ livres_ecartes: [LIVRE_ECARTE] });
    avisService.getAvisByEmission.mockResolvedValueOnce({
      avis: [],
      matching_stats: { ...statsAvecSansMatch, livres_summary: 8, unmatched: 0, livres_summary_sans_match: [] },
      livres_ecartes: [LIVRE_ECARTE],
    });
    emissionsService.getAllEmissions.mockResolvedValueOnce([{ ...emission, badge_status: 'perfect' }]);

    const button = wrapper.find('[data-testid="ignorer-livre-0"]');
    expect(button.exists()).toBe(true);
    expect(button.text()).toContain('Ignorer ce livre');
    await button.trigger('click');
    await flushPromises();

    expect(avisService.ecarterLivre).toHaveBeenCalledWith('emission-1', TITRE, AUTEUR);
    expect(avisService.extractAvis).toHaveBeenCalledWith('emission-1');
    expect(wrapper.vm.livresEcartes).toEqual([LIVRE_ECARTE]);
  });

  it('affiche les titres écartés même quand l\'émission est parfaite', async () => {
    const wrapper = await createWrapper();
    await selectEmission(wrapper, {
      badge: 'perfect',
      stats: { ...statsAvecSansMatch, livres_summary: 8, unmatched: 0, livres_summary_sans_match: [] },
      ecartes: [LIVRE_ECARTE],
    });

    const block = wrapper.find('[data-testid="livres-ecartes"]');
    expect(block.exists()).toBe(true);
    expect(block.text()).toContain('Titres écartés (1)');
    expect(block.text()).toContain(TITRE);
  });

  it('signale un titre écarté absent du résumé actuel (résumé régénéré)', async () => {
    const wrapper = await createWrapper();
    await selectEmission(wrapper, {
      stats: statsAvecSansMatch,
      ecartes: [
        { ...LIVRE_ECARTE, absent_du_resume: true },
        { titre: 'Autre titre', auteur: 'X', ecarte_le: '2026-11-22T10:00:00', absent_du_resume: false },
      ],
    });

    const items = wrapper.findAll('[data-testid="livres-ecartes"] li');
    // items[0] est l'intitulé de la liste
    expect(items[1].text()).toContain('(absent du résumé actuel)');
    expect(items[2].text()).not.toContain('absent du résumé');
  });

  it('« Rétablir » retire le titre du registre puis ré-extrait les avis', async () => {
    const wrapper = await createWrapper();
    await selectEmission(wrapper, { badge: 'perfect', stats: statsAvecSansMatch, ecartes: [LIVRE_ECARTE] });

    avisService.retablirLivre.mockResolvedValueOnce({ livres_ecartes: [] });
    avisService.getAvisByEmission.mockResolvedValueOnce({
      avis: [],
      matching_stats: statsAvecSansMatch,
      livres_ecartes: [],
    });

    await wrapper.find('[data-testid="retablir-livre-0"]').trigger('click');
    await flushPromises();

    expect(avisService.retablirLivre).toHaveBeenCalledWith('emission-1', TITRE);
    expect(avisService.extractAvis).toHaveBeenCalledWith('emission-1');
    expect(wrapper.vm.livresEcartes).toEqual([]);
    expect(wrapper.find('[data-testid="livres-ecartes"]').exists()).toBe(false);
  });

  it('affiche une erreur si l\'écartement échoue', async () => {
    const wrapper = await createWrapper();
    await selectEmission(wrapper, { stats: statsAvecSansMatch, ecartes: [] });
    avisService.ecarterLivre.mockRejectedValueOnce(new Error('boom'));

    await wrapper.find('[data-testid="ignorer-livre-0"]').trigger('click');
    await flushPromises();

    expect(avisService.extractAvis).not.toHaveBeenCalled();
    expect(wrapper.vm.avisError).toContain('écarter');
  });
});
