/**
 * Tests d'intégration pour la page de détail d'un livre (Issue #96 - Phase 2, updated Issue #190)
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
    note_moyenne: 7.5,
    nombre_emissions: 2,
    emissions: [
      {
        emission_id: '68e841e6066cb40c25d5d290',
        date: '2024-09-15',
        note_moyenne: 8.0,
        nombre_avis: 3
      },
      {
        emission_id: '68e841e6066cb40c25d5d291',
        date: '2024-03-12',
        note_moyenne: 7.0,
        nombre_avis: 2
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
          path: '/emissions/:date',
          name: 'EmissionDetail',
          component: { template: '<div>Emission Detail</div>' }
        }
      ]
    });

    // Naviguer vers la route livre
    await router.push('/livre/68e841e6066cb40c25d5d283');
    await router.isReady();
  });

  it('should display book title, author name and emission count', async () => {
    // GIVEN: L'API retourne les données d'un livre
    axios.get.mockResolvedValueOnce({ data: mockLivreData });

    // WHEN: Le composant est monté
    wrapper = mount(LivreDetail, {
      global: {
        plugins: [router]
      }
    });

    await flushPromises();

    // THEN: Le titre du livre, l'auteur et le nombre d'émissions sont affichés
    expect(wrapper.text()).toContain('Capitaine');
    expect(wrapper.text()).toContain('Adrien Bosc');
    expect(wrapper.text()).toContain('Stock');
    expect(wrapper.text()).toContain('2');
    expect(wrapper.text()).toMatch(/2.*émission/i);
  });

  it('should display overall note_moyenne with color badge', async () => {
    // GIVEN: L'API retourne les données d'un livre avec note moyenne
    axios.get.mockResolvedValueOnce({ data: mockLivreData });

    // WHEN: Le composant est monté
    wrapper = mount(LivreDetail, {
      global: {
        plugins: [router]
      }
    });

    await flushPromises();

    // THEN: La note moyenne globale est affichée
    const noteBadge = wrapper.find('[data-test="note-moyenne-globale"]');
    expect(noteBadge.exists()).toBe(true);
    expect(noteBadge.text()).toContain('7.5');
  });

  it('should display emissions sorted by date with per-emission note', async () => {
    // GIVEN: L'API retourne les données d'un livre avec émissions
    axios.get.mockResolvedValueOnce({ data: mockLivreData });

    // WHEN: Le composant est monté
    wrapper = mount(LivreDetail, {
      global: {
        plugins: [router]
      }
    });

    await flushPromises();

    // THEN: Les émissions sont affichées avec leurs notes
    const emissionItems = wrapper.findAll('[data-test="emission-item"]');
    expect(emissionItems).toHaveLength(2);

    // Émissions triées par date (plus récent d'abord)
    expect(emissionItems[0].text()).toContain('15 septembre 2024');
    expect(emissionItems[1].text()).toContain('12 mars 2024');
  });

  it('should link emissions to /emissions/:date route', async () => {
    // GIVEN: L'API retourne les données d'un livre avec émissions
    axios.get.mockResolvedValueOnce({ data: mockLivreData });

    // WHEN: Le composant est monté
    wrapper = mount(LivreDetail, {
      global: {
        plugins: [router]
      }
    });

    await flushPromises();

    // THEN: Les liens pointent vers /emissions/YYYYMMDD
    const emissionLinks = wrapper.findAll('[data-test="emission-link"]');
    expect(emissionLinks).toHaveLength(2);
    expect(emissionLinks[0].attributes('href')).toBe('/emissions/20240915');
    expect(emissionLinks[1].attributes('href')).toBe('/emissions/20240312');
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

  it('should display empty state when book has no emissions', async () => {
    // GIVEN: L'API retourne un livre sans émissions
    const livreSansEmissions = {
      livre_id: '68e841e6066cb40c25d5d283',
      titre: 'Nouveau Livre',
      auteur_id: '68e841e6066cb40c25d5d282',
      auteur_nom: 'Nouvel Auteur',
      editeur: 'Nouvel Editeur',
      note_moyenne: null,
      nombre_emissions: 0,
      emissions: []
    };
    axios.get.mockResolvedValueOnce({ data: livreSansEmissions });

    // WHEN: Le composant est monté
    wrapper = mount(LivreDetail, {
      global: {
        plugins: [router]
      }
    });

    await flushPromises();

    // THEN: Un message indiquant l'absence d'émissions est affiché
    expect(wrapper.text()).toContain('Aucune émission');
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

  it('should use relative URL to leverage Vite proxy (Issue #103)', async () => {
    // GIVEN: L'API est mockée
    axios.get.mockResolvedValueOnce({ data: mockLivreData });

    // WHEN: Le composant est monté
    wrapper = mount(LivreDetail, {
      global: {
        plugins: [router]
      }
    });

    await flushPromises();

    // THEN: L'API est appelée avec une URL relative (pas d'URL absolue avec localhost)
    const callUrl = axios.get.mock.calls[0][0];
    expect(callUrl).toBe('/api/livre/68e841e6066cb40c25d5d283');
    expect(callUrl).not.toContain('http://');
    expect(callUrl).not.toContain('localhost');
  });
});
