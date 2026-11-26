/**
 * Tests d'intégration pour la page Recherche Babelio
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { createRouter, createWebHistory } from 'vue-router';
import BabelioTest from '../../src/views/BabelioTest.vue';
import axios from 'axios';

// Mock d'axios
vi.mock('axios', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn()
  }
}));

describe('BabelioTest - Tests d\'intégration', () => {
  let wrapper;
  let router;

  const mockBabelioResponse = {
    data: {
      type: 'author',
      original: 'Amélie Notombe',
      suggestion: 'Amélie Nothomb',
      confidence: 0.85,
      found: true,
      babelio_data: {
        id: 123,
        name: 'Amélie Nothomb',
        url: 'https://www.babelio.com/auteur/Amelie-Nothomb/123'
      }
    }
  };

  beforeEach(async () => {
    vi.clearAllMocks();

    // Créer un router de test
    router = createRouter({
      history: createWebHistory(),
      routes: [
        { path: '/', component: { template: '<div>Home</div>' } },
        { path: '/babelio-test', component: BabelioTest }
      ]
    });

    // Naviguer vers la page BabelioTest
    await router.push('/babelio-test');
  });

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount();
    }
  });

  it('affiche le titre et la description de la page', async () => {
    wrapper = mount(BabelioTest, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();

    expect(wrapper.find('h1').text()).toBe('Recherche Babelio');
    expect(wrapper.text()).toContain('Testez la vérification orthographique des auteurs, livres et éditeurs');
  });

  it('affiche les trois formulaires de test (auteur, livre, éditeur)', async () => {
    wrapper = mount(BabelioTest, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();

    // Vérifier que les trois sections de formulaires sont présentes
    expect(wrapper.text()).toContain('✍️ Vérifier un auteur');
    expect(wrapper.text()).toContain('📚 Vérifier un livre');
    expect(wrapper.text()).toContain('🏢 Vérifier un éditeur');

    // Vérifier les champs de formulaire
    expect(wrapper.find('#author-name').exists()).toBe(true);
    expect(wrapper.find('#book-title').exists()).toBe(true);
    expect(wrapper.find('#book-author').exists()).toBe(true);
    expect(wrapper.find('#publisher-name').exists()).toBe(true);
  });

  it('permet de saisir des données dans le formulaire auteur', async () => {
    wrapper = mount(BabelioTest, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();

    const authorInput = wrapper.find('#author-name');
    await authorInput.setValue('Amélie Notombe');

    expect(wrapper.vm.forms.author.name).toBe('Amélie Notombe');
  });

  it('permet de saisir des données dans le formulaire livre', async () => {
    wrapper = mount(BabelioTest, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();

    const titleInput = wrapper.find('#book-title');
    const authorInput = wrapper.find('#book-author');

    await titleInput.setValue('Le petite prince');
    await authorInput.setValue('Antoine de Saint-Exupéry');

    expect(wrapper.vm.forms.book.title).toBe('Le petite prince');
    expect(wrapper.vm.forms.book.author).toBe('Antoine de Saint-Exupéry');
  });

  it('permet de saisir des données dans le formulaire éditeur', async () => {
    wrapper = mount(BabelioTest, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();

    const publisherInput = wrapper.find('#publisher-name');
    await publisherInput.setValue('Galimard');

    expect(wrapper.vm.forms.publisher.name).toBe('Galimard');
  });

  it('désactive les boutons quand les champs obligatoires sont vides', async () => {
    wrapper = mount(BabelioTest, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();

    const buttons = wrapper.findAll('.submit-button');
    expect(buttons).toHaveLength(3);

    // Tous les boutons doivent être désactivés initialement
    buttons.forEach(button => {
      expect(button.element.disabled).toBe(true);
    });
  });

  it('active les boutons quand les champs obligatoires sont remplis', async () => {
    // Cookie Babelio actif côté serveur (Issue #406) : seuls les champs comptent
    axios.get.mockResolvedValue({
      data: { cookie_active: true, cookie_age_sec: 60, cookie_max_age_sec: 1200, cookie_expired: false }
    });
    wrapper = mount(BabelioTest, {
      global: {
        plugins: [router]
      }
    });

    await flushPromises();

    // Remplir le champ auteur
    const authorInput = wrapper.find('#author-name');
    await authorInput.setValue('Test Author');

    const authorButton = wrapper.findAll('.submit-button')[0];
    expect(authorButton.element.disabled).toBe(false);

    // Remplir le champ livre
    const titleInput = wrapper.find('#book-title');
    await titleInput.setValue('Test Book');

    const bookButton = wrapper.findAll('.submit-button')[1];
    expect(bookButton.element.disabled).toBe(false);

    // Remplir le champ éditeur
    const publisherInput = wrapper.find('#publisher-name');
    await publisherInput.setValue('Test Publisher');

    const publisherButton = wrapper.findAll('.submit-button')[2];
    expect(publisherButton.element.disabled).toBe(false);
  });

  it('appelle l\'API et affiche les résultats lors de la vérification d\'auteur', async () => {
    axios.post.mockResolvedValue(mockBabelioResponse);

    wrapper = mount(BabelioTest, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();

    // Remplir et soumettre le formulaire auteur
    const authorInput = wrapper.find('#author-name');
    await authorInput.setValue('Amélie Notombe');

    const authorForm = wrapper.findAll('.test-form')[0];
    await authorForm.trigger('submit');

    // Attendre que l'appel API se termine
    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 10));

    // Vérifier l'appel API
    expect(axios.post).toHaveBeenCalledWith('/api/verify-babelio', {
      type: 'author',
      name: 'Amélie Notombe'
    });

    // Vérifier que le résultat est affiché
    await wrapper.vm.$nextTick();
    expect(wrapper.vm.results.author).toEqual(mockBabelioResponse.data);
  });

  it('appelle l\'API et affiche les résultats lors de la vérification de livre', async () => {
    const mockBookResponse = {
      data: {
        type: 'book',
        original: 'Le petite prince',
        suggestion: 'Le Petit Prince',
        confidence: 0.90,
        found: true,
        babelio_data: {
          id: 456,
          title: 'Le Petit Prince',
          author: 'Antoine de Saint-Exupéry'
        }
      }
    };

    axios.post.mockResolvedValue(mockBookResponse);

    wrapper = mount(BabelioTest, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();

    // Remplir et soumettre le formulaire livre
    const titleInput = wrapper.find('#book-title');
    const authorInput = wrapper.find('#book-author');

    await titleInput.setValue('Le petite prince');
    await authorInput.setValue('Antoine de Saint-Exupéry');

    const bookForm = wrapper.findAll('.test-form')[1];
    await bookForm.trigger('submit');

    // Attendre que l'appel API se termine
    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 10));

    // Vérifier l'appel API
    expect(axios.post).toHaveBeenCalledWith('/api/verify-babelio', {
      type: 'book',
      title: 'Le petite prince',
      author: 'Antoine de Saint-Exupéry'
    });

    // Vérifier que le résultat est affiché
    await wrapper.vm.$nextTick();
    expect(wrapper.vm.results.book).toEqual(mockBookResponse.data);
  });

  it('appelle l\'API et affiche les résultats lors de la vérification d\'éditeur', async () => {
    const mockPublisherResponse = {
      data: {
        type: 'publisher',
        original: 'Galimard',
        suggestion: 'Gallimard',
        confidence: 0.92,
        found: true,
        babelio_data: {
          id: 789,
          name: 'Gallimard'
        }
      }
    };

    axios.post.mockResolvedValue(mockPublisherResponse);

    wrapper = mount(BabelioTest, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();

    // Remplir et soumettre le formulaire éditeur
    const publisherInput = wrapper.find('#publisher-name');
    await publisherInput.setValue('Galimard');

    const publisherForm = wrapper.findAll('.test-form')[2];
    await publisherForm.trigger('submit');

    // Attendre que l'appel API se termine
    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 10));

    // Vérifier l'appel API
    expect(axios.post).toHaveBeenCalledWith('/api/verify-babelio', {
      type: 'publisher',
      name: 'Galimard'
    });

    // Vérifier que le résultat est affiché
    await wrapper.vm.$nextTick();
    expect(wrapper.vm.results.publisher).toEqual(mockPublisherResponse.data);
  });

  it('gère les erreurs d\'API', async () => {
    const mockError = {
      response: {
        data: {
          detail: 'Erreur de service'
        }
      }
    };

    axios.post.mockRejectedValue(mockError);

    wrapper = mount(BabelioTest, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();

    // Remplir et soumettre le formulaire auteur
    const authorInput = wrapper.find('#author-name');
    await authorInput.setValue('Test');

    const authorForm = wrapper.findAll('.test-form')[0];
    await authorForm.trigger('submit');

    // Attendre que l'appel API se termine
    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 10));

    // Vérifier que l'erreur est affichée
    await wrapper.vm.$nextTick();
    expect(wrapper.vm.error).toContain('Erreur de service');
    expect(wrapper.find('.error-banner').exists()).toBe(true);
  });

  it('affiche l\'état de chargement pendant les requêtes', async () => {
    let resolveRequest;
    const requestPromise = new Promise((resolve) => {
      resolveRequest = resolve;
    });
    axios.post.mockReturnValue(requestPromise);

    wrapper = mount(BabelioTest, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();

    // Remplir et soumettre le formulaire auteur
    const authorInput = wrapper.find('#author-name');
    await authorInput.setValue('Test');

    const authorForm = wrapper.findAll('.test-form')[0];
    await authorForm.trigger('submit');

    await wrapper.vm.$nextTick();

    // Vérifier l'état de chargement
    expect(wrapper.vm.loading.author).toBe(true);
    const authorButton = wrapper.findAll('.submit-button')[0];
    expect(authorButton.text()).toBe('Vérification...');
    expect(authorButton.element.disabled).toBe(true);

    // Résoudre la requête
    resolveRequest(mockBabelioResponse);
    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 10));

    // Vérifier que l'état de chargement est terminé
    await wrapper.vm.$nextTick();
    expect(wrapper.vm.loading.author).toBe(false);
  });

  it('affiche le guide d\'utilisation', async () => {
    wrapper = mount(BabelioTest, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();

    expect(wrapper.text()).toContain('💡 Guide d\'utilisation');
    expect(wrapper.text()).toContain('✍️ Test Auteur');
    expect(wrapper.text()).toContain('📚 Test Livre');
    expect(wrapper.text()).toContain('🏢 Test Éditeur');
    expect(wrapper.text()).toContain('Résultats');
  });

  it('est responsive sur petits écrans', async () => {
    wrapper = mount(BabelioTest, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();

    // Vérifier que les classes CSS pour la responsivité existent
    const babelioTest = wrapper.find('.babelio-test');
    expect(babelioTest.exists()).toBe(true);

    const testForms = wrapper.find('.test-forms');
    expect(testForms.exists()).toBe(true);

    // Vérifier que les styles responsive existent dans le composant
    expect(wrapper.html()).toContain('test-forms');
  });

  it('nettoie les erreurs lors d\'une nouvelle soumission', async () => {
    wrapper = mount(BabelioTest, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();

    // Simuler une erreur
    wrapper.vm.error = 'Erreur précédente';
    await wrapper.vm.$nextTick();

    axios.post.mockResolvedValue(mockBabelioResponse);

    // Remplir et soumettre le formulaire
    const authorInput = wrapper.find('#author-name');
    await authorInput.setValue('Test');

    const authorForm = wrapper.findAll('.test-form')[0];
    await authorForm.trigger('submit');

    // Vérifier que l'erreur est effacée
    expect(wrapper.vm.error).toBe(null);
  });

  it('nettoie les résultats précédents lors d\'une nouvelle soumission', async () => {
    let resolveRequest;
    const requestPromise = new Promise((resolve) => {
      resolveRequest = resolve;
    });
    axios.post.mockReturnValue(requestPromise);

    wrapper = mount(BabelioTest, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();

    // Simuler des résultats précédents
    wrapper.vm.results.author = { old: 'data' };
    await wrapper.vm.$nextTick();

    // Remplir et soumettre le formulaire
    const authorInput = wrapper.find('#author-name');
    await authorInput.setValue('Test');

    const authorForm = wrapper.findAll('.test-form')[0];
    await authorForm.trigger('submit');

    await wrapper.vm.$nextTick();

    // Vérifier que les anciens résultats sont effacés au début de la soumission
    expect(wrapper.vm.results.author).toBe(null);

    // Résoudre la requête pour éviter les avertissements
    resolveRequest(mockBabelioResponse);
    await wrapper.vm.$nextTick();
  });
});
