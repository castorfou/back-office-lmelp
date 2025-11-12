/**
 * Tests d'intégration pour la page de détail d'un livre (Issue #96 - Phase 2)
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { createRouter, createWebHistory } from 'vue-router';
import LivreDetail from '../../src/views/LivreDetail.vue';
import axios from 'axios';

// Mock axios
vi.mock('axios');

describe('LivreDetail - Tests d\'intégration', () => {
  let wrapper;
  let router;

  const mockLivreData = {
    livre_id: '68e841e6066cb40c25d5d283',
    titre: 'Capitaine',
    auteur_id: '68e841e6066cb40c25d5d282',
    auteur_nom: 'Adrien Bosc',
    editeur: 'Stock',
    nombre_episodes: 2,
    episodes: [
      {
        episode_id: '68e841e6066cb40c25d5d286',
        titre: 'Émission du 15 septembre 2024',
        date: '2024-09-15',
        programme: true
      },
      {
        episode_id: '68e841e6066cb40c25d5d287',
        titre: 'Émission du 12 mars 2024',
        date: '2024-03-12',
        programme: false
      }
    ]
  };

  beforeEach(async () => {
    vi.clearAllMocks();

    // Créer un router de test
    router = createRouter({
      history: createWebHistory(),
      routes: [
        {
          path: '/livre/:id',
          name: 'LivreDetail',
          component: LivreDetail
        },
        {
          path: '/auteur/:id',
          name: 'AuteurDetail',
          component: { template: '<div>Auteur Detail</div>' }
        },
        {
          path: '/episode/:id',
          name: 'EpisodeDetail',
          component: { template: '<div>Episode Detail</div>' }
        }
      ]
    });

    // Naviguer vers la route livre
    await router.push('/livre/68e841e6066cb40c25d5d283');
    await router.isReady();
  });

  it('should display book title, author name and episode count', async () => {
    // GIVEN: L'API retourne les données d'un livre
    axios.get.mockResolvedValueOnce({ data: mockLivreData });

    // WHEN: Le composant est monté
    wrapper = mount(LivreDetail, {
      global: {
        plugins: [router]
      }
    });

    await flushPromises();

    // THEN: Le titre du livre, l'auteur et le nombre d'épisodes sont affichés
    expect(wrapper.text()).toContain('Capitaine');
    expect(wrapper.text()).toContain('Adrien Bosc');
    expect(wrapper.text()).toContain('Stock');
    expect(wrapper.text()).toContain('2');
    expect(wrapper.text()).toMatch(/2.*épisode/i);
  });

  it('should display all episodes sorted by date (most recent first)', async () => {
    // GIVEN: L'API retourne les données d'un livre avec plusieurs épisodes
    axios.get.mockResolvedValueOnce({ data: mockLivreData });

    // WHEN: Le composant est monté
    wrapper = mount(LivreDetail, {
      global: {
        plugins: [router]
      }
    });

    await flushPromises();

    // THEN: Tous les épisodes sont affichés
    expect(wrapper.text()).toContain('Émission du 15 septembre 2024');
    expect(wrapper.text()).toContain('Émission du 12 mars 2024');

    // THEN: Les épisodes sont triés par date (plus récent d'abord)
    const episodeItems = wrapper.findAll('[data-test="episode-item"]').map(el => el.text());
    expect(episodeItems[0]).toContain('15 septembre 2024');
    expect(episodeItems[1]).toContain('12 mars 2024');
  });

  it('should display date for each episode', async () => {
    // GIVEN: L'API retourne les données d'un livre
    axios.get.mockResolvedValueOnce({ data: mockLivreData });

    // WHEN: Le composant est monté
    wrapper = mount(LivreDetail, {
      global: {
        plugins: [router]
      }
    });

    await flushPromises();

    // THEN: La date est affichée pour chaque épisode (en format français)
    const episodeItems = wrapper.findAll('[data-test="episode-item"]');
    expect(episodeItems).toHaveLength(2);
    expect(episodeItems[0].text()).toContain('15 septembre 2024');
    expect(episodeItems[1].text()).toContain('12 mars 2024');
  });

  it('should make author name clickable with correct route', async () => {
    // GIVEN: L'API retourne les données d'un livre
    axios.get.mockResolvedValueOnce({ data: mockLivreData });

    // WHEN: Le composant est monté
    wrapper = mount(LivreDetail, {
      global: {
        plugins: [router]
      }
    });

    await flushPromises();

    // THEN: Le nom de l'auteur est un lien cliquable
    const auteurLink = wrapper.find('[data-test="auteur-link"]');
    expect(auteurLink.exists()).toBe(true);
    expect(auteurLink.attributes('href')).toBe('/auteur/68e841e6066cb40c25d5d282');
  });

  it('should make episode titles clickable with correct route', async () => {
    // GIVEN: L'API retourne les données d'un livre
    axios.get.mockResolvedValueOnce({ data: mockLivreData });

    // WHEN: Le composant est monté
    wrapper = mount(LivreDetail, {
      global: {
        plugins: [router]
      }
    });

    await flushPromises();

    // THEN: Les titres d'épisodes sont des liens cliquables
    const episodeLinks = wrapper.findAll('[data-test="episode-link"]');
    expect(episodeLinks).toHaveLength(2);

    // Vérifier que les liens pointent vers les bonnes routes
    expect(episodeLinks[0].attributes('href')).toBe('/episode/68e841e6066cb40c25d5d286');
    expect(episodeLinks[1].attributes('href')).toBe('/episode/68e841e6066cb40c25d5d287');
  });

  it('should display loading state while fetching data', async () => {
    // GIVEN: L'API met du temps à répondre
    let resolvePromise;
    axios.get.mockImplementation(() => new Promise((resolve) => {
      resolvePromise = resolve;
    }));

    // WHEN: Le composant est monté
    wrapper = mount(LivreDetail, {
      global: {
        plugins: [router]
      }
    });

    // Attendre que Vue ait traité les mises à jour du DOM
    await wrapper.vm.$nextTick();

    // THEN: Un indicateur de chargement est affiché
    expect(wrapper.find('[data-test="loading"]').exists()).toBe(true);

    // Cleanup: résoudre la promesse pour éviter les fuites mémoire
    if (resolvePromise) {
      resolvePromise({ data: mockLivreData });
    }
    await flushPromises();
  });

  it('should display error message when book not found', async () => {
    // GIVEN: L'API retourne une erreur 404
    axios.get.mockRejectedValueOnce({
      response: {
        status: 404,
        data: { detail: 'Livre non trouvé' }
      }
    });

    // WHEN: Le composant est monté
    wrapper = mount(LivreDetail, {
      global: {
        plugins: [router]
      }
    });

    await flushPromises();

    // THEN: Un message d'erreur est affiché
    expect(wrapper.find('[data-test="error"]').exists()).toBe(true);
    expect(wrapper.text()).toContain('Livre non trouvé');
  });

  it('should display empty state when book has no episodes', async () => {
    // GIVEN: L'API retourne un livre sans épisodes
    const livreSansEpisodes = {
      livre_id: '68e841e6066cb40c25d5d283',
      titre: 'Nouveau Livre',
      auteur_id: '68e841e6066cb40c25d5d282',
      auteur_nom: 'Nouvel Auteur',
      editeur: 'Nouvel Editeur',
      nombre_episodes: 0,
      episodes: []
    };
    axios.get.mockResolvedValueOnce({ data: livreSansEpisodes });

    // WHEN: Le composant est monté
    wrapper = mount(LivreDetail, {
      global: {
        plugins: [router]
      }
    });

    await flushPromises();

    // THEN: Un message indiquant l'absence d'épisodes est affiché
    expect(wrapper.text()).toContain('Aucun épisode');
    expect(wrapper.text()).toContain('0');
  });

  it('should call API with correct livre ID from route', async () => {
    // GIVEN: L'API est mockée
    axios.get.mockResolvedValueOnce({ data: mockLivreData });

    // WHEN: Le composant est monté
    wrapper = mount(LivreDetail, {
      global: {
        plugins: [router]
      }
    });

    await flushPromises();

    // THEN: L'API est appelée avec le bon ID
    expect(axios.get).toHaveBeenCalledWith(
      expect.stringContaining('/api/livre/68e841e6066cb40c25d5d283')
    );
  });
});
