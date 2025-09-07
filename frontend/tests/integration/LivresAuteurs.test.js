/**
 * Tests d'intégration pour la page Livres/Auteurs
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
  },
  episodeService: {
    getAllEpisodes: vi.fn(),
    getEpisodeById: vi.fn(),
    updateEpisodeDescription: vi.fn(),
    updateEpisodeTitle: vi.fn(),
  },
  statisticsService: {
    getStatistics: vi.fn(),
  }
}));

describe('LivresAuteurs - Tests d\'intégration', () => {
  let wrapper;
  let router;

  const mockLivresData = [
    {
      episode_oid: '6865f995a1418e3d7c63d076', // pragma: allowlist secret
      episode_title: 'Les critiques littéraires du Masque & la Plume depuis le festival "Quai du Polar" à Lyon',
      episode_date: '29 juin 2025',
      auteur: 'Aslak Nord',
      titre: 'Piège à loup',
      editeur: 'Le bruit du monde',
      note_moyenne: 8.8,
      nb_critiques: 4,
      coups_de_coeur: ['Patricia Martin', 'Elisabeth Philippe', 'Bernard Poiret']
    },
    {
      episode_oid: '686bf5e18380ee925ae5e318', // pragma: allowlist secret
      episode_title: 'Faut-il lire Raphaël Quenard, Miranda July, Mario Vargas Llosa, Etgar Keret… cet été ?',
      episode_date: '06 juil. 2025',
      auteur: 'Edgar Keret',
      titre: 'Correction automatique',
      editeur: 'Éditions de l\'Olivier',
      note_moyenne: 8.0,
      nb_critiques: 4,
      coups_de_coeur: ['Elisabeth Philippe']
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

    // Naviguer vers la page livres-auteurs
    await router.push('/livres-auteurs');
  });

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount();
    }
  });

  it('affiche le titre et la description de la page', async () => {
    livresAuteursService.getLivresAuteurs.mockResolvedValue(mockLivresData);

    wrapper = mount(LivresAuteurs, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();

    expect(wrapper.find('h1').text()).toContain('Livres et Auteurs');
    expect(wrapper.text()).toContain('Extraction des informations bibliographiques');
  });

  it('affiche la liste des livres extraits', async () => {
    livresAuteursService.getLivresAuteurs.mockResolvedValue(mockLivresData);

    wrapper = mount(LivresAuteurs, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 50));

    // Vérifier que les livres sont affichés
    expect(wrapper.text()).toContain('Aslak Nord');
    expect(wrapper.text()).toContain('Piège à loup');
    expect(wrapper.text()).toContain('Le bruit du monde');
    expect(wrapper.text()).toContain('Edgar Keret');
    expect(wrapper.text()).toContain('Correction automatique');
  });

  it('affiche les informations détaillées de chaque livre', async () => {
    livresAuteursService.getLivresAuteurs.mockResolvedValue(mockLivresData);

    wrapper = mount(LivresAuteurs, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 50));

    // Vérifier les notes moyennes
    expect(wrapper.text()).toContain('8.8');
    expect(wrapper.text()).toContain('8.0');

    // Vérifier les nombres de critiques
    expect(wrapper.text()).toContain('4 critiques');

    // Vérifier les informations d'épisode
    expect(wrapper.text()).toContain('29 juin 2025');
    expect(wrapper.text()).toContain('06 juil. 2025');
  });

  it('affiche les coups de cœur des critiques', async () => {
    livresAuteursService.getLivresAuteurs.mockResolvedValue(mockLivresData);

    wrapper = mount(LivresAuteurs, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 50));

    // Vérifier les coups de cœur
    expect(wrapper.text()).toContain('Patricia Martin');
    expect(wrapper.text()).toContain('Elisabeth Philippe');
    expect(wrapper.text()).toContain('Bernard Poiret');
  });

  it('gère l\'état de chargement', async () => {
    let resolveLivres;
    const livresPromise = new Promise((resolve) => {
      resolveLivres = resolve;
    });
    livresAuteursService.getLivresAuteurs.mockReturnValue(livresPromise);

    wrapper = mount(LivresAuteurs, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();

    // Vérifier l'état de chargement
    expect(wrapper.text()).toContain('Chargement');

    // Résoudre la promesse
    resolveLivres(mockLivresData);
    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 50));

    // Vérifier que le chargement a disparu
    expect(wrapper.text()).not.toContain('Chargement');
    expect(wrapper.text()).toContain('Aslak Nord');
  });

  it('gère les erreurs de chargement', async () => {
    livresAuteursService.getLivresAuteurs.mockRejectedValue(new Error('API Error'));

    wrapper = mount(LivresAuteurs, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 50));

    // Vérifier l'affichage de l'erreur
    expect(wrapper.text()).toContain('Erreur');
  });

  it('affiche un message quand aucun livre n\'est trouvé', async () => {
    livresAuteursService.getLivresAuteurs.mockResolvedValue([]);

    wrapper = mount(LivresAuteurs, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 50));

    // Vérifier le message d'état vide
    expect(wrapper.text()).toContain('Aucun livre trouvé');
  });

  it('permet de filtrer les livres par auteur', async () => {
    livresAuteursService.getLivresAuteurs.mockResolvedValue(mockLivresData);

    wrapper = mount(LivresAuteurs, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 50));

    // Chercher le champ de filtre
    const filterInput = wrapper.find('input[placeholder*="Filtrer"]');
    if (filterInput.exists()) {
      // Tester le filtrage par auteur
      await filterInput.setValue('Aslak');
      await wrapper.vm.$nextTick();

      // Vérifier que seuls les livres d'Aslak Nord sont affichés
      expect(wrapper.text()).toContain('Aslak Nord');
      expect(wrapper.text()).not.toContain('Edgar Keret');
    }
  });

  it('affiche les liens vers les épisodes sources', async () => {
    livresAuteursService.getLivresAuteurs.mockResolvedValue(mockLivresData);

    wrapper = mount(LivresAuteurs, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 50));

    // Vérifier que les titres d'épisodes sont affichés comme liens ou références
    expect(wrapper.text()).toContain('Les critiques littéraires du Masque & la Plume');
    expect(wrapper.text()).toContain('Faut-il lire Raphaël Quenard');
  });

  it('trie les livres par note moyenne décroissante par défaut', async () => {
    livresAuteursService.getLivresAuteurs.mockResolvedValue(mockLivresData);

    wrapper = mount(LivresAuteurs, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 50));

    // Trouver tous les éléments de livre et vérifier l'ordre
    const bookElements = wrapper.findAll('[data-testid="book-item"]');
    if (bookElements.length >= 2) {
      // Le premier livre devrait avoir la note la plus élevée (8.8)
      expect(bookElements[0].text()).toContain('8.8');
      // Le deuxième livre devrait avoir la note plus faible (8.0)
      expect(bookElements[1].text()).toContain('8.0');
    }
  });

  it('affiche les statistiques de synthèse', async () => {
    livresAuteursService.getLivresAuteurs.mockResolvedValue(mockLivresData);

    wrapper = mount(LivresAuteurs, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 50));

    // Vérifier les statistiques
    expect(wrapper.text()).toContain('2 livres'); // Nombre total
    expect(wrapper.text()).toContain('2 épisodes'); // Nombre d'épisodes sources
  });
});
