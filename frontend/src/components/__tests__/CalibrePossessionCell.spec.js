/**
 * Tests pour CalibrePossessionCell.vue (Issue #325)
 *
 * Cellule partagée Palmarès / Mes Recommandations :
 * - livre possédé : ◯ ou ✓ Lu (+ note Calibre), lien vers /calibre?search=<titre>
 * - livre absent de Calibre : lien de recherche Anna's Archive
 */

import { describe, it, expect } from 'vitest';
import { mount } from '@vue/test-utils';
import { createRouter, createMemoryHistory } from 'vue-router';
import CalibrePossessionCell from '../CalibrePossessionCell.vue';

const BASE_URL = 'https://fr.annas-archive.se';

function makeItem(overrides = {}) {
  return {
    titre: "L'Œuvre au noir",
    auteur_nom: 'Marguerite Yourcenar',
    calibre_in_library: false,
    calibre_read: null,
    calibre_rating: null,
    ...overrides,
  };
}

async function mountCell(item) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: { template: '<div />' } },
      { path: '/calibre', component: { template: '<div />' } },
    ],
  });
  await router.push('/');
  await router.isReady();
  return mount(CalibrePossessionCell, {
    props: { item, annasArchiveBaseUrl: BASE_URL },
    global: { plugins: [router] },
  });
}

describe('CalibrePossessionCell', () => {
  it('affiche ◯ cliquable vers la recherche Calibre pour un livre possédé non lu', async () => {
    const wrapper = await mountCell(makeItem({ calibre_in_library: true }));

    const link = wrapper.find('[data-test="calibre-link"]');
    expect(link.exists()).toBe(true);
    expect(link.text()).toBe('◯');
    expect(link.attributes('href')).toBe(
      `/calibre?search=${encodeURIComponent("L'Œuvre au noir")}`
    );
    expect(wrapper.find('[data-test="annas-archive-link"]').exists()).toBe(false);
  });

  it('affiche ✓ Lu et la note Calibre pour un livre lu noté', async () => {
    const wrapper = await mountCell(
      makeItem({ calibre_in_library: true, calibre_read: true, calibre_rating: 8 })
    );

    expect(wrapper.find('[data-test="calibre-link"]').text()).toBe('✓ Lu');
    expect(wrapper.find('[data-test="calibre-rating"]').text()).toBe('8/10');
  });

  it("n'affiche pas de note quand le livre n'est pas noté", async () => {
    const wrapper = await mountCell(
      makeItem({ calibre_in_library: true, calibre_read: true })
    );

    expect(wrapper.find('[data-test="calibre-rating"]').exists()).toBe(false);
  });

  it("affiche un lien Anna's Archive pour un livre absent de Calibre", async () => {
    const wrapper = await mountCell(makeItem());

    expect(wrapper.find('[data-test="calibre-link"]').exists()).toBe(false);
    const link = wrapper.find('[data-test="annas-archive-link"]');
    expect(link.attributes('target')).toBe('_blank');
    expect(link.attributes('href')).toBe(
      `${BASE_URL}/search?index=&page=1&sort=&display=&q=` +
        'L%27%C5%92uvre+au+noir+-+Marguerite+Yourcenar'
    );
  });
});
