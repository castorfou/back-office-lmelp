/**
 * Tests d'intégration pour la page de détail d'un critique (Issue #191)
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { createRouter, createWebHistory } from 'vue-router';
import CritiqueDetail from '../../src/views/CritiqueDetail.vue';
import axios from 'axios';

// Mock axios
vi.mock('axios');

describe('CritiqueDetail - Tests d\'intégration', () => {
  let wrapper;
  let router;

  const mockCritiqueData = {
    critique_id: '694eb58bffd25d11ce052759', // pragma: allowlist secret
    nom: 'Arnaud Viviant',
    animateur: false,
    variantes: ['Arnaud Vivian'],
    nombre_avis: 3,
    note_moyenne: 7.3,
    note_distribution: {
      '2': 0, '3': 0, '4': 0, '5': 0,
      '6': 1, '7': 0, '8': 1, '9': 1, '10': 0
    },
    coups_de_coeur: [
      {
        livre_oid: '6948458b4c7793c317f9f795', // pragma: allowlist secret
        livre_titre: 'Combats de filles',
        auteur_nom: 'Rita Bullwinkel',
        auteur_oid: '694845004c7793c317f9f700', // pragma: allowlist secret
        editeur: 'La Croisée',
        note: 9,
        commentaire: 'Très belle découverte, original',
        section: 'programme',
        emission_date: '2026-01-18',
        emission_oid: '694fea91e46eedc769bcd996' // pragma: allowlist secret
      }
    ],
    oeuvres: [
      {
        livre_oid: '6948458b4c7793c317f9f795', // pragma: allowlist secret
        livre_titre: 'Combats de filles',
        auteur_nom: 'Rita Bullwinkel',
        auteur_oid: '694845004c7793c317f9f700', // pragma: allowlist secret
        editeur: 'La Croisée',
        note: 9,
        commentaire: 'Très belle découverte, original',
        section: 'programme',
        emission_date: '2026-01-18',
        emission_oid: '694fea91e46eedc769bcd996' // pragma: allowlist secret
      },
      {
        livre_oid: '6948458b4c7793c317f9f796', // pragma: allowlist secret
        livre_titre: 'Le Grand Vertige',
        auteur_nom: 'Pierre Ducrozet',
        auteur_oid: '694845004c7793c317f9f701', // pragma: allowlist secret
        editeur: 'Actes Sud',
        note: 8,
        commentaire: 'Roman ambitieux et maîtrisé',
        section: 'programme',
        emission_date: '2025-12-14',
        emission_oid: '694fea91e46eedc769bcd997' // pragma: allowlist secret
      },
      {
        livre_oid: '6948458b4c7793c317f9f797', // pragma: allowlist secret
        livre_titre: 'La Vie nouvelle',
        auteur_nom: 'Tom Crewe',
        auteur_oid: '694845004c7793c317f9f702', // pragma: allowlist secret
        editeur: 'Gallimard',
        note: 6,
        commentaire: 'Intéressant mais inégal',
        section: 'programme',
        emission_date: '2025-11-09',
        emission_oid: '694fea91e46eedc769bcd998' // pragma: allowlist secret
      }
    ]
  };

  beforeEach(async () => {
    vi.clearAllMocks();

    router = createRouter({
      history: createWebHistory(),
      routes: [
        {
          path: '/critique/:id',
          name: 'CritiqueDetail',
          component: CritiqueDetail
        },
        {
          path: '/livre/:id',
          name: 'LivreDetail',
          component: { template: '<div>Livre Detail</div>' }
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

    await router.push('/critique/694eb58bffd25d11ce052759'); // pragma: allowlist secret
    await router.isReady();
  });

  it('should display critique name and avis count', async () => {
    // GIVEN: L'API retourne les données d'un critique
    axios.get.mockResolvedValueOnce({ data: mockCritiqueData });

    // WHEN: Le composant est monté
    wrapper = mount(CritiqueDetail, {
      global: { plugins: [router] }
    });
    await flushPromises();

    // THEN: Le nom et le nombre d'avis sont affichés
    expect(wrapper.text()).toContain('Arnaud Viviant');
    expect(wrapper.text()).toContain('3');
  });

  it('should display note moyenne with correct color class', async () => {
    // GIVEN: L'API retourne un critique avec note_moyenne 7.3
    axios.get.mockResolvedValueOnce({ data: mockCritiqueData });

    // WHEN: Le composant est monté
    wrapper = mount(CritiqueDetail, {
      global: { plugins: [router] }
    });
    await flushPromises();

    // THEN: La note moyenne est affichée avec la bonne classe
    expect(wrapper.text()).toContain('7.3');
    const noteBadge = wrapper.find('[data-test="note-moyenne"]');
    expect(noteBadge.exists()).toBe(true);
    expect(noteBadge.classes()).toContain('note-good');
  });

  it('should display loading state while fetching data', async () => {
    // GIVEN: L'API met du temps à répondre
    let resolvePromise;
    axios.get.mockImplementation(() => new Promise((resolve) => {
      resolvePromise = resolve;
    }));

    // WHEN: Le composant est monté
    wrapper = mount(CritiqueDetail, {
      global: { plugins: [router] }
    });
    await wrapper.vm.$nextTick();

    // THEN: Un indicateur de chargement est affiché
    expect(wrapper.find('[data-test="loading"]').exists()).toBe(true);

    // Cleanup
    if (resolvePromise) {
      resolvePromise({ data: mockCritiqueData });
    }
    await flushPromises();
  });

  it('should display error message when critique not found', async () => {
    // GIVEN: L'API retourne une erreur 404
    axios.get.mockRejectedValueOnce({
      response: {
        status: 404,
        data: { detail: 'Critique non trouvé' }
      }
    });

    // WHEN: Le composant est monté
    wrapper = mount(CritiqueDetail, {
      global: { plugins: [router] }
    });
    await flushPromises();

    // THEN: Un message d'erreur est affiché
    expect(wrapper.find('[data-test="error"]').exists()).toBe(true);
    expect(wrapper.text()).toContain('Critique non trouvé');
  });

  it('should render note distribution bars', async () => {
    // GIVEN: L'API retourne un critique avec distribution des notes
    axios.get.mockResolvedValueOnce({ data: mockCritiqueData });

    // WHEN: Le composant est monté
    wrapper = mount(CritiqueDetail, {
      global: { plugins: [router] }
    });
    await flushPromises();

    // THEN: 9 barres de distribution (notes 2 à 10)
    const bars = wrapper.findAll('[data-test="distribution-bar"]');
    expect(bars).toHaveLength(9);
  });

  it('should display coups de coeur section with note >= 9', async () => {
    // GIVEN: L'API retourne un critique avec des coups de coeur
    axios.get.mockResolvedValueOnce({ data: mockCritiqueData });

    // WHEN: Le composant est monté
    wrapper = mount(CritiqueDetail, {
      global: { plugins: [router] }
    });
    await flushPromises();

    // THEN: La section coups de coeur affiche les bons livres
    expect(wrapper.text()).toContain('Combats de filles');
    const coupDeCoeurItems = wrapper.findAll('[data-test="coup-de-coeur-item"]');
    expect(coupDeCoeurItems.length).toBeGreaterThanOrEqual(1);
  });

  it('should display all oeuvres in the list', async () => {
    // GIVEN: L'API retourne un critique avec 3 oeuvres
    axios.get.mockResolvedValueOnce({ data: mockCritiqueData });

    // WHEN: Le composant est monté
    wrapper = mount(CritiqueDetail, {
      global: { plugins: [router] }
    });
    await flushPromises();

    // THEN: Les 3 oeuvres sont affichées
    const oeuvreItems = wrapper.findAll('[data-test="oeuvre-item"]');
    expect(oeuvreItems).toHaveLength(3);
    expect(wrapper.text()).toContain('Combats de filles');
    expect(wrapper.text()).toContain('Le Grand Vertige');
    expect(wrapper.text()).toContain('La Vie nouvelle');
  });

  it('should filter oeuvres by text search', async () => {
    // GIVEN: Le composant est monté avec des données
    axios.get.mockResolvedValueOnce({ data: mockCritiqueData });
    wrapper = mount(CritiqueDetail, {
      global: { plugins: [router] }
    });
    await flushPromises();

    // WHEN: On filtre par texte
    wrapper.vm.searchFilter = 'Combats';
    await wrapper.vm.$nextTick();

    // THEN: Seule l'oeuvre correspondante est dans filteredOeuvres
    expect(wrapper.vm.filteredOeuvres).toHaveLength(1);
    expect(wrapper.vm.filteredOeuvres[0].livre_titre).toBe('Combats de filles');
  });

  it('should filter oeuvres by note range', async () => {
    // GIVEN: Le composant est monté avec des données
    axios.get.mockResolvedValueOnce({ data: mockCritiqueData });
    wrapper = mount(CritiqueDetail, {
      global: { plugins: [router] }
    });
    await flushPromises();

    // WHEN: On filtre par note >= 9 (excellent)
    wrapper.vm.noteFilter = 'excellent';
    await wrapper.vm.$nextTick();

    // THEN: Seule l'oeuvre avec note 9 est affichée
    expect(wrapper.vm.filteredOeuvres).toHaveLength(1);
    expect(wrapper.vm.filteredOeuvres[0].note).toBe(9);
  });

  it('should call API with correct critique ID from route', async () => {
    // GIVEN: L'API est mockée
    axios.get.mockResolvedValueOnce({ data: mockCritiqueData });

    // WHEN: Le composant est monté
    wrapper = mount(CritiqueDetail, {
      global: { plugins: [router] }
    });
    await flushPromises();

    // THEN: L'API est appelée avec le bon ID et une URL relative
    const callUrl = axios.get.mock.calls[0][0];
    expect(callUrl).toBe('/api/critique/694eb58bffd25d11ce052759'); // pragma: allowlist secret
    expect(callUrl).not.toContain('http://');
    expect(callUrl).not.toContain('localhost');
  });

  it('should display empty state when critique has no avis', async () => {
    // GIVEN: Un critique sans avis
    const critiqueSansAvis = {
      ...mockCritiqueData,
      nombre_avis: 0,
      note_moyenne: null,
      note_distribution: {
        '2': 0, '3': 0, '4': 0, '5': 0,
        '6': 0, '7': 0, '8': 0, '9': 0, '10': 0
      },
      coups_de_coeur: [],
      oeuvres: []
    };
    axios.get.mockResolvedValueOnce({ data: critiqueSansAvis });

    // WHEN: Le composant est monté
    wrapper = mount(CritiqueDetail, {
      global: { plugins: [router] }
    });
    await flushPromises();

    // THEN: Un message d'état vide est affiché
    expect(wrapper.text()).toContain('Aucun avis');
  });
});
