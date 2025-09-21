/**
 * Tests simplifiés pour la page Livres/Auteurs
 * Focus sur la structure de base sans interactions complexes
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount } from '@vue/test-utils';
import { createRouter, createWebHistory } from 'vue-router';
import LivresAuteurs from '../../src/views/LivresAuteurs.vue';
import { livresAuteursService } from '../../src/services/api.js';

// Mock du service API
vi.mock('../../src/services/api.js', () => ({
  livresAuteursService: {
    getLivresAuteurs: vi.fn(),
    getEpisodesWithReviews: vi.fn(),
  },
  episodeService: {
    getAllEpisodes: vi.fn(),
    getEpisodeById: vi.fn(),
    updateEpisodeDescription: vi.fn(),
    updateEpisodeTitle: vi.fn(),
  },
  statisticsService: {
    getStatistics: vi.fn(),
  },
  babelioService: {
    verifyAuthor: vi.fn(),
    verifyBook: vi.fn(),
    verifyPublisher: vi.fn(),
  },
  fuzzySearchService: {
    searchEpisode: vi.fn()
  }
}));

describe('LivresAuteurs - Tests simplifiés', () => {
  let wrapper;
  let router;

  const mockEpisodesWithReviews = [
    {
      _id: { $oid: '6865f995a1418e3d7c63d076' }, // pragma: allowlist secret
      titre: 'Les critiques littéraires du Masque & la Plume depuis le festival "Quai du Polar" à Lyon',
      date: '29 juin 2025',
      review_count: 4
    }
  ];

  beforeEach(async () => {
    vi.clearAllMocks();

    // Créer un router de test
    router = createRouter({
      history: createWebHistory(),
      routes: [
        { path: '/', component: { template: '<div>Dashboard</div>' } },
        { path: '/livres-auteurs', component: LivresAuteurs }
      ]
    });

    await router.push('/livres-auteurs');
  });

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount();
    }
  });

  it('charge la page sans erreur et affiche les éléments de base', async () => {
    livresAuteursService.getEpisodesWithReviews.mockResolvedValue(mockEpisodesWithReviews);

    wrapper = mount(LivresAuteurs, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();

    // Vérifier que la page se charge sans erreur
    expect(wrapper.exists()).toBe(true);
    expect(wrapper.text()).toContain('Livres et Auteurs');
  });

  it('affiche le sélecteur d\'épisodes après chargement', async () => {
    livresAuteursService.getEpisodesWithReviews.mockResolvedValue(mockEpisodesWithReviews);

    wrapper = mount(LivresAuteurs, {
      global: {
        plugins: [router]
      }
    });

    // Attendre que le chargement se termine
    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 50));

    // Vérifier que le sélecteur est présent
    expect(wrapper.text()).toContain('Choisir un épisode avec avis critiques');
  });

  it('affiche le message d\'aide initial après chargement', async () => {
    livresAuteursService.getEpisodesWithReviews.mockResolvedValue(mockEpisodesWithReviews);

    wrapper = mount(LivresAuteurs, {
      global: {
        plugins: [router]
      }
    });

    // Attendre que le chargement se termine
    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 50));

    // Vérifier que le message d'aide est présent
    expect(wrapper.text()).toContain('Sélectionnez un épisode pour commencer');
  });

  it('affiche la colonne Validation Biblio dans le tableau', async () => {
    const mockBooks = [
      {
        episode_oid: '6865f995a1418e3d7c63d076', // pragma: allowlist secret
        auteur: 'Michel Houellebecq',
        titre: 'Les Particules élémentaires',
        editeur: 'Flammarion'
      }
    ];

    livresAuteursService.getEpisodesWithReviews.mockResolvedValue(mockEpisodesWithReviews);
    livresAuteursService.getLivresAuteurs.mockResolvedValue(mockBooks);

    wrapper = mount(LivresAuteurs, {
      global: {
        plugins: [router]
      }
    });

    // Attendre que le chargement se termine
    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 50));

    // Sélectionner un épisode
    wrapper.vm.selectedEpisodeId = '6865f995a1418e3d7c63d076'; // pragma: allowlist secret
    await wrapper.vm.loadBooksForEpisode();
    await wrapper.vm.$nextTick();

    // Vérifier que la colonne Validation Biblio est présente
    expect(wrapper.text()).toContain('Validation Biblio');

    // Vérifier qu'il y a des composants BiblioValidationCell
    const validationCells = wrapper.findAllComponents({ name: 'BiblioValidationCell' });
    expect(validationCells.length).toBe(1);

    // Vérifier que le composant reçoit les bonnes props
    expect(validationCells[0].props()).toEqual({
      author: 'Michel Houellebecq',
      title: 'Les Particules élémentaires',
      publisher: 'Flammarion',
      episodeId: '6865f995a1418e3d7c63d076' // pragma: allowlist secret
    });
  });

  it("affiche la petite colonne d'état (programme / coup de coeur) et permet de trier", async () => {
    const mockBooks = [
      {
        episode_oid: '6865f995a1418e3d7c63d076', // pragma: allowlist secret
        auteur: 'Michel Houellebecq',
        titre: 'Les Particules élémentaires',
        editeur: 'Flammarion',
        programme: true,
        coup_de_coeur: false
      }
    ];

    livresAuteursService.getEpisodesWithReviews.mockResolvedValue(mockEpisodesWithReviews);
    livresAuteursService.getLivresAuteurs.mockResolvedValue(mockBooks);

    wrapper = mount(LivresAuteurs, {
      global: {
        plugins: [router]
      }
    });

    // Attendre que le chargement se termine
    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 50));

    // Sélectionner un épisode
  wrapper.vm.selectedEpisodeId = '6865f995a1418e3d7c63d076'; // pragma: allowlist secret
    await wrapper.vm.loadBooksForEpisode();
    await wrapper.vm.$nextTick();

    // Vérifier que l'en-tête de colonne d'état est présent
    const statusHeader = wrapper.find('th.status-header');
    expect(statusHeader.exists()).toBe(true);

    // Vérifier que la cellule d'état contient une icône (programme -> 🎯)
    expect(wrapper.text()).toContain('🎯');

    // Cliquer sur l'en-tête active le tri par 'status'
    await statusHeader.trigger('click');
    expect(wrapper.vm.currentSortField).toBe('status');
  });
});
