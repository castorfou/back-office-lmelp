import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount } from '@vue/test-utils';
import { createRouter, createMemoryHistory } from 'vue-router';
import OrphanedAvis from '../OrphanedAvis.vue';
import { avisService, searchService } from '../../services/api.js';

vi.mock('../../services/api.js', () => ({
  avisService: {
    getOrphanedAvis: vi.fn(),
    getOrphanedAvisStatistics: vi.fn(),
    updateAvis: vi.fn(),
    deleteAvis: vi.fn(),
  },
  searchService: {
    advancedSearch: vi.fn(),
  },
}));

describe('OrphanedAvis.vue', () => {
  let wrapper;
  let router;

  const mockStatistics = { orphaned_count: 2 };

  const mockOrphanedAvis = [
    {
      id: 'avis1',
      livre_oid: '6a8b17df16a04bd8be0446af', // pragma: allowlist secret
      livre_titre_extrait: "L'Affaire Alaska Sanders",
      auteur_nom_extrait: 'Joël Dicker',
      critique_nom_extrait: 'Elisabeth Philippe',
      emission_oid: 'emission1',
      commentaire: 'Un thriller efficace',
      note: 8,
      suggested_livre_id: null,
      suggested_livre_titre: null,
    },
    {
      id: 'avis2',
      livre_oid: '6a8b180916a04bd8be0446b0', // pragma: allowlist secret
      livre_titre_extrait: 'La Promesse',
      auteur_nom_extrait: 'Damon Galgut',
      critique_nom_extrait: 'Arnaud Viviant',
      emission_oid: 'emission2',
      commentaire: 'Prix Booker mérité',
      note: 9,
      suggested_livre_id: null,
      suggested_livre_titre: null,
    },
  ];

  beforeEach(async () => {
    vi.clearAllMocks();

    router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: '/avis-orphelins', component: OrphanedAvis }],
    });

    await router.push('/avis-orphelins');
  });

  it('loads statistics and orphaned avis list on mount', async () => {
    avisService.getOrphanedAvisStatistics.mockResolvedValue(mockStatistics);
    avisService.getOrphanedAvis.mockResolvedValue(mockOrphanedAvis);

    wrapper = mount(OrphanedAvis, {
      global: { plugins: [router] },
    });

    await new Promise((resolve) => setTimeout(resolve, 50));
    await wrapper.vm.$nextTick();

    expect(avisService.getOrphanedAvisStatistics).toHaveBeenCalled();
    expect(avisService.getOrphanedAvis).toHaveBeenCalled();
    expect(wrapper.text()).toContain("L'Affaire Alaska Sanders");
    expect(wrapper.text()).toContain('La Promesse');
  });

  it('displays empty state when no orphaned avis', async () => {
    avisService.getOrphanedAvisStatistics.mockResolvedValue({ orphaned_count: 0 });
    avisService.getOrphanedAvis.mockResolvedValue([]);

    wrapper = mount(OrphanedAvis, {
      global: { plugins: [router] },
    });

    await new Promise((resolve) => setTimeout(resolve, 50));
    await wrapper.vm.$nextTick();

    expect(wrapper.find('.empty-state').exists()).toBe(true);
  });

  it('displays orphaned avis card with livre_oid, titre, commentaire', async () => {
    avisService.getOrphanedAvisStatistics.mockResolvedValue(mockStatistics);
    avisService.getOrphanedAvis.mockResolvedValue(mockOrphanedAvis);

    wrapper = mount(OrphanedAvis, {
      global: { plugins: [router] },
    });

    await new Promise((resolve) => setTimeout(resolve, 50));
    await wrapper.vm.$nextTick();

    const cards = wrapper.findAll('.group-card');
    expect(cards.length).toBe(2);
    expect(cards[0].text()).toContain('6a8b17df16a04bd8be0446af'); // pragma: allowlist secret
    expect(cards[0].text()).toContain('Un thriller efficace');
  });

  it('repoints an avis to a selected book successfully', async () => {
    avisService.getOrphanedAvisStatistics.mockResolvedValue(mockStatistics);
    avisService.getOrphanedAvis.mockResolvedValue(mockOrphanedAvis);
    searchService.advancedSearch.mockResolvedValue({
      livres: [{ _id: '694918984c7793c317f9f79f', titre: "L'Affaire Alaska Sanders", auteur_nom: 'Joël Dicker' }], // pragma: allowlist secret
    });
    avisService.updateAvis.mockResolvedValue({ message: 'ok' });

    wrapper = mount(OrphanedAvis, {
      global: { plugins: [router] },
    });

    await new Promise((resolve) => setTimeout(resolve, 50));
    await wrapper.vm.$nextTick();

    wrapper.vm.startRepoint(mockOrphanedAvis[0]);
    wrapper.vm.bookSearchQuery = 'Alaska Sanders';
    await wrapper.vm.searchBooks();
    await wrapper.vm.$nextTick();

    expect(searchService.advancedSearch).toHaveBeenCalledWith('Alaska Sanders', ['livres']);

    await wrapper.vm.confirmRepoint(mockOrphanedAvis[0], {
      id: '694918984c7793c317f9f79f', // pragma: allowlist secret
      titre: "L'Affaire Alaska Sanders",
    });

    expect(avisService.updateAvis).toHaveBeenCalledWith('avis1', {
      livre_oid: '694918984c7793c317f9f79f', // pragma: allowlist secret
    });
    // loadData is called again after repoint
    expect(avisService.getOrphanedAvis).toHaveBeenCalledTimes(2);
  });

  it('deletes an orphaned avis after confirmation', async () => {
    avisService.getOrphanedAvisStatistics.mockResolvedValue(mockStatistics);
    avisService.getOrphanedAvis.mockResolvedValue(mockOrphanedAvis);
    avisService.deleteAvis.mockResolvedValue({ message: 'deleted' });
    vi.spyOn(window, 'confirm').mockReturnValue(true);

    wrapper = mount(OrphanedAvis, {
      global: { plugins: [router] },
    });

    await new Promise((resolve) => setTimeout(resolve, 50));
    await wrapper.vm.$nextTick();

    await wrapper.vm.removeAvis(mockOrphanedAvis[1]);

    expect(avisService.deleteAvis).toHaveBeenCalledWith('avis2');
    expect(avisService.getOrphanedAvis).toHaveBeenCalledTimes(2);
  });

  it('cancels deletion when confirmation is declined', async () => {
    avisService.getOrphanedAvisStatistics.mockResolvedValue(mockStatistics);
    avisService.getOrphanedAvis.mockResolvedValue(mockOrphanedAvis);
    vi.spyOn(window, 'confirm').mockReturnValue(false);

    wrapper = mount(OrphanedAvis, {
      global: { plugins: [router] },
    });

    await new Promise((resolve) => setTimeout(resolve, 50));
    await wrapper.vm.$nextTick();

    await wrapper.vm.removeAvis(mockOrphanedAvis[1]);

    expect(avisService.deleteAvis).not.toHaveBeenCalled();
  });

  it('displays error message on fetch failure', async () => {
    avisService.getOrphanedAvisStatistics.mockRejectedValue(new Error('network error'));
    avisService.getOrphanedAvis.mockRejectedValue(new Error('network error'));

    wrapper = mount(OrphanedAvis, {
      global: { plugins: [router] },
    });

    await new Promise((resolve) => setTimeout(resolve, 50));
    await wrapper.vm.$nextTick();

    expect(wrapper.find('.alert-error').exists()).toBe(true);
  });

  describe('Suggestion de livre existant (Issue #271 - Partie 3bis)', () => {
    const mockAvisWithSuggestion = [
      {
        id: 'avis3',
        livre_oid: '6a8b17df16a04bd8be0446af', // pragma: allowlist secret
        livre_titre_extrait: "L'Affaire Alaska Sanders",
        auteur_nom_extrait: 'Joël Dicker',
        critique_nom_extrait: 'Nelly Kapriélian',
        emission_oid: 'emission1',
        commentaire: 'Structure efficace',
        note: 4,
        suggested_livre_id: '694918984c7793c317f9f79f', // pragma: allowlist secret
        suggested_livre_titre: "L'Affaire Alaska Sanders",
      },
    ];

    it('hides the Supprimer button when a matching book is suggested', async () => {
      avisService.getOrphanedAvisStatistics.mockResolvedValue({ orphaned_count: 1 });
      avisService.getOrphanedAvis.mockResolvedValue(mockAvisWithSuggestion);

      wrapper = mount(OrphanedAvis, {
        global: { plugins: [router] },
      });

      await new Promise((resolve) => setTimeout(resolve, 50));
      await wrapper.vm.$nextTick();

      const card = wrapper.find('.group-card');
      expect(card.find('.btn-danger').exists()).toBe(false);
      expect(card.text()).toContain("L'Affaire Alaska Sanders");
    });

    it('shows the Supprimer button when no matching book is suggested', async () => {
      avisService.getOrphanedAvisStatistics.mockResolvedValue(mockStatistics);
      avisService.getOrphanedAvis.mockResolvedValue(mockOrphanedAvis);

      wrapper = mount(OrphanedAvis, {
        global: { plugins: [router] },
      });

      await new Promise((resolve) => setTimeout(resolve, 50));
      await wrapper.vm.$nextTick();

      const cards = wrapper.findAll('.group-card');
      expect(cards[0].find('.btn-danger').exists()).toBe(true);
    });

    it('repoints directly to the suggested book on one click', async () => {
      avisService.getOrphanedAvisStatistics.mockResolvedValue({ orphaned_count: 1 });
      avisService.getOrphanedAvis.mockResolvedValue(mockAvisWithSuggestion);
      avisService.updateAvis.mockResolvedValue({ message: 'ok' });

      wrapper = mount(OrphanedAvis, {
        global: { plugins: [router] },
      });

      await new Promise((resolve) => setTimeout(resolve, 50));
      await wrapper.vm.$nextTick();

      const suggestButton = wrapper.find('[data-testid="repoint-suggested"]');
      expect(suggestButton.exists()).toBe(true);

      await suggestButton.trigger('click');
      await wrapper.vm.$nextTick();

      expect(avisService.updateAvis).toHaveBeenCalledWith('avis3', {
        livre_oid: '694918984c7793c317f9f79f', // pragma: allowlist secret
      });
    });
  });
});
