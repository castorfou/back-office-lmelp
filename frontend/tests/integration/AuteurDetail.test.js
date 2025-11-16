/**
 * Tests d'intégration pour la page de détail d'un auteur (Issue #96 - Phase 1)
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { createRouter, createWebHistory } from 'vue-router';
import AuteurDetail from '../../src/views/AuteurDetail.vue';
import axios from 'axios';

// Mock axios
vi.mock('axios');

describe('AuteurDetail - Tests d\'intégration', () => {
  let wrapper;
  let router;

  const mockAuteurData = {
    auteur_id: '68e841e6066cb40c25d5d282',
    nom: 'Adrien Bosc',
    nombre_oeuvres: 3,
    livres: [
      {
        livre_id: '68e841e6066cb40c25d5d283',
        titre: 'Capitaine',
        editeur: 'Stock'
      },
      {
        livre_id: '68e841e6066cb40c25d5d284',
        titre: 'L\'invention de Tristan',
        editeur: 'Stock'
      },
      {
        livre_id: '68e841e6066cb40c25d5d285',
        titre: 'Procès',
        editeur: 'Stock'
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
          path: '/auteur/:id',
          name: 'AuteurDetail',
          component: AuteurDetail
        },
        {
          path: '/livre/:id',
          name: 'LivreDetail',
          component: { template: '<div>Livre Detail</div>' }
        }
      ]
    });

    // Naviguer vers la route auteur
    await router.push('/auteur/68e841e6066cb40c25d5d282');
    await router.isReady();
  });

  it('should display author name and book count', async () => {
    // GIVEN: L'API retourne les données d'un auteur
    axios.get.mockResolvedValueOnce({ data: mockAuteurData });

    // WHEN: Le composant est monté
    wrapper = mount(AuteurDetail, {
      global: {
        plugins: [router]
      }
    });

    await flushPromises();

    // THEN: Le nom de l'auteur et le nombre d'œuvres sont affichés
    expect(wrapper.text()).toContain('Adrien Bosc');
    expect(wrapper.text()).toContain('3');
    expect(wrapper.text()).toMatch(/3.*œuvre/i);
  });

  it('should display all books sorted alphabetically', async () => {
    // GIVEN: L'API retourne les données d'un auteur avec plusieurs livres
    axios.get.mockResolvedValueOnce({ data: mockAuteurData });

    // WHEN: Le composant est monté
    wrapper = mount(AuteurDetail, {
      global: {
        plugins: [router]
      }
    });

    await flushPromises();

    // THEN: Tous les livres sont affichés
    expect(wrapper.text()).toContain('Capitaine');
    expect(wrapper.text()).toContain('L\'invention de Tristan');
    expect(wrapper.text()).toContain('Procès');

    // THEN: Les livres sont triés alphabétiquement (vérifier l'ordre dans le HTML)
    const bookTitles = wrapper.findAll('[data-test="book-item"]').map(el => el.text());
    expect(bookTitles[0]).toContain('Capitaine');
    expect(bookTitles[1]).toContain('L\'invention de Tristan');
    expect(bookTitles[2]).toContain('Procès');
  });

  it('should display publisher for each book', async () => {
    // GIVEN: L'API retourne les données d'un auteur
    axios.get.mockResolvedValueOnce({ data: mockAuteurData });

    // WHEN: Le composant est monté
    wrapper = mount(AuteurDetail, {
      global: {
        plugins: [router]
      }
    });

    await flushPromises();

    // THEN: L'éditeur est affiché pour chaque livre
    const bookItems = wrapper.findAll('[data-test="book-item"]');
    expect(bookItems).toHaveLength(3);
    bookItems.forEach(item => {
      expect(item.text()).toContain('Stock');
    });
  });

  it('should make book titles clickable with correct route', async () => {
    // GIVEN: L'API retourne les données d'un auteur
    axios.get.mockResolvedValueOnce({ data: mockAuteurData });

    // WHEN: Le composant est monté
    wrapper = mount(AuteurDetail, {
      global: {
        plugins: [router]
      }
    });

    await flushPromises();

    // THEN: Les titres de livres sont des liens cliquables
    const bookLinks = wrapper.findAll('[data-test="book-link"]');
    expect(bookLinks).toHaveLength(3);

    // Vérifier que le premier lien pointe vers la bonne route
    expect(bookLinks[0].attributes('href')).toBe('/livre/68e841e6066cb40c25d5d283');
  });

  it('should display loading state while fetching data', async () => {
    // GIVEN: L'API met du temps à répondre
    let resolvePromise;
    axios.get.mockImplementation(() => new Promise((resolve) => {
      resolvePromise = resolve;
    }));

    // WHEN: Le composant est monté
    wrapper = mount(AuteurDetail, {
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
      resolvePromise({ data: mockAuteurData });
    }
    await flushPromises();
  });

  it('should display error message when author not found', async () => {
    // GIVEN: L'API retourne une erreur 404
    axios.get.mockRejectedValueOnce({
      response: {
        status: 404,
        data: { detail: 'Auteur non trouvé' }
      }
    });

    // WHEN: Le composant est monté
    wrapper = mount(AuteurDetail, {
      global: {
        plugins: [router]
      }
    });

    await flushPromises();

    // THEN: Un message d'erreur est affiché
    expect(wrapper.find('[data-test="error"]').exists()).toBe(true);
    expect(wrapper.text()).toContain('Auteur non trouvé');
  });

  it('should display empty state when author has no books', async () => {
    // GIVEN: L'API retourne un auteur sans livres
    const auteurSansLivres = {
      auteur_id: '68e841e6066cb40c25d5d282',
      nom: 'Nouvel Auteur',
      nombre_oeuvres: 0,
      livres: []
    };
    axios.get.mockResolvedValueOnce({ data: auteurSansLivres });

    // WHEN: Le composant est monté
    wrapper = mount(AuteurDetail, {
      global: {
        plugins: [router]
      }
    });

    await flushPromises();

    // THEN: Un message indiquant l'absence de livres est affiché
    expect(wrapper.text()).toContain('Aucun livre');
    expect(wrapper.text()).toContain('0');
  });

  it('should call API with correct auteur ID from route', async () => {
    // GIVEN: L'API est mockée
    axios.get.mockResolvedValueOnce({ data: mockAuteurData });

    // WHEN: Le composant est monté
    wrapper = mount(AuteurDetail, {
      global: {
        plugins: [router]
      }
    });

    await flushPromises();

    // THEN: L'API est appelée avec le bon ID
    expect(axios.get).toHaveBeenCalledWith(
      expect.stringContaining('/api/auteur/68e841e6066cb40c25d5d282')
    );
  });

  it('should use relative URL to leverage Vite proxy (Issue #103)', async () => {
    // GIVEN: L'API est mockée
    axios.get.mockResolvedValueOnce({ data: mockAuteurData });

    // WHEN: Le composant est monté
    wrapper = mount(AuteurDetail, {
      global: {
        plugins: [router]
      }
    });

    await flushPromises();

    // THEN: L'API est appelée avec une URL relative (pas d'URL absolue avec localhost)
    const callUrl = axios.get.mock.calls[0][0];
    expect(callUrl).toBe('/api/auteur/68e841e6066cb40c25d5d282');
    expect(callUrl).not.toContain('http://');
    expect(callUrl).not.toContain('localhost');
  });
});
