/**
 * Test de debug pour comprendre la structure des données réelles
 */

import { describe, it, expect } from 'vitest';
import { mount } from '@vue/test-utils';
import { createRouter, createWebHistory } from 'vue-router';
import LivresAuteurs from '../../src/views/LivresAuteurs.vue';

describe('Debug: Real data structure', () => {
  it('should show what fields are actually present in books', async () => {
    const router = createRouter({
      history: createWebHistory(),
      routes: [{ path: '/', component: { template: '<div></div>' } }]
    });

    // Simule les données telles qu'elles arrivent du backend
    const mockBooks = [
      {
        auteur: 'Agnès Michaud',
        titre: 'Huitsemences vivantes',
        editeur: 'Cherche Midi',
        programme: true,
        coup_de_coeur: false,
        episode_oid: '123',
        avis_critique_id: '456',
        // Note: peut-être que 'status' et 'validation_status' sont absents ?
      }
    ];

    const wrapper = mount(LivresAuteurs, {
      global: { plugins: [router] }
    });
    wrapper.vm.books = mockBooks;
    await wrapper.vm.$nextTick();

    const stats = wrapper.vm.programBooksValidationStats;

    console.log('🔍 Book structure:', JSON.stringify(mockBooks[0], null, 2));
    console.log('🔍 Stats result:', stats);
    console.log('🔍 book.status:', mockBooks[0].status);
    console.log('🔍 book.validation_status:', mockBooks[0].validation_status);

    // Assert: Real assertions based on simplified logic
    expect(stats.total).toBe(1);
    expect(stats.traites).toBe(0); // No status field
    expect(stats.suggested).toBe(0); // No suggested_* fields
    expect(stats.not_found).toBe(1); // No status, no suggestions = not_found
  });
});
