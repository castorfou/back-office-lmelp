/**
 * Tests unitaires TDD pour les statistiques des livres au programme
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { mount } from '@vue/test-utils';
import { createRouter, createWebHistory } from 'vue-router';
import LivresAuteurs from '../../src/views/LivresAuteurs.vue';

describe('ProgramBooksValidationStats - TDD', () => {
  let wrapper;
  let router;

  beforeEach(() => {
    router = createRouter({
      history: createWebHistory(),
      routes: [{ path: '/', component: { template: '<div></div>' } }]
    });
  });

  it('should count "traités" as books with status === "mongo"', async () => {
    // Arrange: livres avec programme ET coup_de_coeur
    const mockBooks = [
      {
        auteur: 'Agnès Michaud',
        titre: 'Huitsemences vivantes',
        programme: true,
        coup_de_coeur: false,
        status: 'mongo'  // Ce livre est traité (déjà en MongoDB)
      },
      {
        auteur: 'Michel Houellebecq',
        titre: 'Anéantir',
        programme: false,
        coup_de_coeur: true,  // Coup de coeur compte aussi
        status: 'extracted'  // Ce livre n'est pas encore traité, sans suggestion
      },
      {
        auteur: 'Victor Hugo',
        titre: 'Les Misérables',
        programme: false,
        coup_de_coeur: false,  // NI programme NI coup_de_coeur - ne doit pas être compté
        status: 'mongo'
      }
    ];

    // Act: mount et set books
    wrapper = mount(LivresAuteurs, {
      global: { plugins: [router] }
    });
    wrapper.vm.books = mockBooks;
    await wrapper.vm.$nextTick();

    // Assert
    const stats = wrapper.vm.programBooksValidationStats;
    console.log('📊 Stats computed:', stats);

    expect(stats.total).toBe(2); // 2 livres (1 programme + 1 coup_de_coeur)
    expect(stats.traites).toBe(1); // 1 livre avec status === 'mongo'
    expect(stats.not_found).toBe(1); // 1 livre sans suggestion
    expect(stats.suggested).toBe(0);
  });

  it('should count validation statuses independently of traités', async () => {
    // Arrange: Livres avec différents statuts
    const mockBooks = [
      { auteur: 'A1', titre: 'T1', programme: true, status: 'mongo' },
      { auteur: 'A2', titre: 'T2', programme: true, status: 'extracted', suggested_author: 'A2 Corrected' },
      { auteur: 'A3', titre: 'T3', programme: true, status: 'extracted', suggested_title: 'T3 Corrected' },
      { auteur: 'A4', titre: 'T4', programme: true, status: 'extracted' },
    ];

    // Act
    wrapper = mount(LivresAuteurs, {
      global: { plugins: [router] }
    });
    wrapper.vm.books = mockBooks;
    await wrapper.vm.$nextTick();

    // Assert
    const stats = wrapper.vm.programBooksValidationStats;
    console.log('📊 Stats (multiple statuses):', stats);

    expect(stats.total).toBe(4);
    expect(stats.traites).toBe(1); // Seulement le premier (status: mongo)
    expect(stats.suggested).toBe(2); // Deux livres avec suggestions
    expect(stats.not_found).toBe(1); // Un livre sans suggestion
  });

  it('should not count books without programme flag', async () => {
    // Arrange: Tous les livres sont NOT au programme
    const mockBooks = [
      { auteur: 'A1', titre: 'T1', programme: false, status: 'mongo' },
      { auteur: 'A2', titre: 'T2', programme: false, status: 'extracted', suggested_author: 'A2 Corrected' },
    ];

    // Act
    wrapper = mount(LivresAuteurs, {
      global: { plugins: [router] }
    });
    wrapper.vm.books = mockBooks;
    await wrapper.vm.$nextTick();

    // Assert
    const stats = wrapper.vm.programBooksValidationStats;
    console.log('📊 Stats (no programme books):', stats);

    expect(stats.total).toBe(0);
    expect(stats.traites).toBe(0);
    expect(stats.suggested).toBe(0);
    expect(stats.not_found).toBe(0);
  });

  it('should display stats in UI when books exist', async () => {
    // Arrange
    const mockBooks = [
      { auteur: 'A1', titre: 'T1', programme: true, status: 'mongo', editeur: 'E1' },
      { auteur: 'A2', titre: 'T2', programme: true, status: 'extracted', suggested_title: 'T2 Corrected', editeur: 'E2' },
    ];

    // Act
    wrapper = mount(LivresAuteurs, {
      global: { plugins: [router] }
    });
    wrapper.vm.selectedEpisodeId = '123';
    wrapper.vm.books = mockBooks;
    wrapper.vm.loading = false;
    wrapper.vm.error = null;
    await wrapper.vm.$nextTick();

    // Assert
    const statsElement = wrapper.find('.validation-stats');
    expect(statsElement.exists()).toBe(true);

    const text = statsElement.text();
    console.log('📊 Stats UI text:', text);

    expect(text).toContain('au programme');
    expect(text).toContain('1 traités');
    expect(text).toContain('1 suggested');
  });

  it('should count books without any status as "à valider", not "not found"', async () => {
    // La validation Babelio n'est plus automatique : un livre sans statut n'a
    // simplement pas encore été vérifié.
    const mockBooks = [
      { auteur: 'Emma Marsantes', titre: "N'efface pas mes cercles", programme: true },
      { auteur: 'A2', titre: 'T2', programme: true, status: 'extracted' },
    ];

    wrapper = mount(LivresAuteurs, {
      global: { plugins: [router] }
    });
    wrapper.vm.selectedEpisodeId = '123';
    wrapper.vm.books = mockBooks;
    wrapper.vm.loading = false;
    wrapper.vm.error = null;
    await wrapper.vm.$nextTick();

    const stats = wrapper.vm.programBooksValidationStats;
    expect(stats.a_valider).toBe(1);
    expect(stats.not_found).toBe(1);
    expect(wrapper.find('.validation-stats').text()).toContain('1 à valider');
  });
});
