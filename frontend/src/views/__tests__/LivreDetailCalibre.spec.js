import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount } from '@vue/test-utils';
import LivreDetail from '../LivreDetail.vue';
import axios from 'axios';

// Mock axios
vi.mock('axios', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

// Mock router
const mockRoute = {
  params: { id: '507f1f77bcf86cd799439011' }, // pragma: allowlist secret
};

const mockRouter = {
  back: vi.fn(),
};

describe('LivreDetail - Calibre enrichment (Issue #214)', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  function mountComponent() {
    return mount(LivreDetail, {
      global: {
        mocks: {
          $route: mockRoute,
          $router: mockRouter,
        },
        stubs: {
          'router-link': {
            template: '<a><slot /></a>',
            props: ['to'],
          },
          Navigation: { template: '<div />' },
        },
      },
    });
  }

  function mockAxiosWithLivre(livreData) {
    axios.get.mockImplementation((url) => {
      if (url.includes('/api/livre/')) {
        return Promise.resolve({ data: livreData });
      }
      if (url.includes('/api/avis/by-livre/')) {
        return Promise.resolve({ data: { avis: [] } });
      }
      if (url.includes('/api/config/annas-archive-url')) {
        return Promise.resolve({ data: { url: 'https://fr.annas-archive.org' } });
      }
      return Promise.reject(new Error(`Unexpected URL: ${url}`));
    });
  }

  const baseLivreData = {
    livre_id: '507f1f77bcf86cd799439011',
    titre: 'L\'Adversaire',
    auteur_id: '507f1f77bcf86cd799439012',
    auteur_nom: 'Emmanuel Carrère',
    editeur: 'Gallimard',
    note_moyenne: 7.5,
    nombre_emissions: 1,
    emissions: [],
    calibre_tags: ['lmelp_240324'],
    calibre_in_library: false,
    calibre_read: null,
    calibre_rating: null,
    calibre_current_tags: null,
  };

  it('shows Calibre in-library badge when book is in Calibre', async () => {
    mockAxiosWithLivre({
      ...baseLivreData,
      calibre_in_library: true,
      calibre_read: false,
      calibre_rating: null,
      calibre_current_tags: [],
    });

    const wrapper = mountComponent();
    await wrapper.vm.$nextTick();
    await new Promise((resolve) => setTimeout(resolve, 50));

    expect(wrapper.find('[data-test="calibre-in-library"]').exists()).toBe(true);
  });

  it('hides Calibre in-library badge when book is not in Calibre', async () => {
    mockAxiosWithLivre({
      ...baseLivreData,
      calibre_in_library: false,
    });

    const wrapper = mountComponent();
    await wrapper.vm.$nextTick();
    await new Promise((resolve) => setTimeout(resolve, 50));

    expect(wrapper.find('[data-test="calibre-in-library"]').exists()).toBe(false);
  });

  it('hides Anna\'s Archive icon when book is in Calibre library', async () => {
    mockAxiosWithLivre({
      ...baseLivreData,
      calibre_in_library: true,
      calibre_read: false,
      calibre_rating: null,
      calibre_current_tags: [],
    });

    const wrapper = mountComponent();
    await wrapper.vm.$nextTick();
    await new Promise((resolve) => setTimeout(resolve, 50));

    expect(wrapper.find('[data-test="annas-archive-link"]').exists()).toBe(false);
  });

  it('shows Anna\'s Archive icon when book is not in Calibre library', async () => {
    mockAxiosWithLivre({
      ...baseLivreData,
      calibre_in_library: false,
    });

    const wrapper = mountComponent();
    await wrapper.vm.$nextTick();
    await new Promise((resolve) => setTimeout(resolve, 50));

    expect(wrapper.find('[data-test="annas-archive-link"]').exists()).toBe(true);
  });

  it('shows "Lu" badge with rating when book is read and has rating', async () => {
    mockAxiosWithLivre({
      ...baseLivreData,
      calibre_in_library: true,
      calibre_read: true,
      calibre_rating: 8,
      calibre_current_tags: ['lmelp_240324'],
    });

    const wrapper = mountComponent();
    await wrapper.vm.$nextTick();
    await new Promise((resolve) => setTimeout(resolve, 50));

    expect(wrapper.find('[data-test="calibre-read-badge"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="calibre-read-badge"]').text()).toContain('Lu');
    expect(wrapper.find('[data-test="calibre-rating"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="calibre-rating"]').text()).toContain('8');
  });

  it('shows "Non lu" badge when book is in Calibre but not read', async () => {
    mockAxiosWithLivre({
      ...baseLivreData,
      calibre_in_library: true,
      calibre_read: false,
      calibre_rating: null,
      calibre_current_tags: [],
    });

    const wrapper = mountComponent();
    await wrapper.vm.$nextTick();
    await new Promise((resolve) => setTimeout(resolve, 50));

    expect(wrapper.find('[data-test="calibre-read-badge"]').exists()).toBe(true);
    const badgeText = wrapper.find('[data-test="calibre-read-badge"]').text();
    expect(badgeText).not.toContain('Lu');
  });

  it('highlights tags missing from Calibre (tag delta) in different style', async () => {
    mockAxiosWithLivre({
      ...baseLivreData,
      calibre_tags: ['lmelp_240101', 'lmelp_240324', 'lmelp_arnaud_viviant'],
      calibre_in_library: true,
      calibre_read: true,
      calibre_rating: 7,
      // Only lmelp_240101 is in Calibre currently
      calibre_current_tags: ['lmelp_240101', 'babelio'],
    });

    const wrapper = mountComponent();
    await wrapper.vm.$nextTick();
    await new Promise((resolve) => setTimeout(resolve, 50));

    // Tags missing from Calibre should have a distinct marker
    const missingTags = wrapper.findAll('[data-test="tag-missing"]');
    expect(missingTags.length).toBeGreaterThan(0);

    // lmelp_240324 and lmelp_arnaud_viviant should be marked as missing
    const missingTexts = missingTags.map((el) => el.text());
    expect(missingTexts).toContain('lmelp_240324');
    expect(missingTexts).toContain('lmelp_arnaud_viviant');
  });

  it('shows no tag delta when book is not in Calibre', async () => {
    mockAxiosWithLivre({
      ...baseLivreData,
      calibre_tags: ['lmelp_240324'],
      calibre_in_library: false,
      calibre_current_tags: null,
    });

    const wrapper = mountComponent();
    await wrapper.vm.$nextTick();
    await new Promise((resolve) => setTimeout(resolve, 50));

    expect(wrapper.find('[data-test="tag-missing"]').exists()).toBe(false);
  });

  it('shows no tag delta when all tags are present in Calibre', async () => {
    mockAxiosWithLivre({
      ...baseLivreData,
      calibre_tags: ['lmelp_240324'],
      calibre_in_library: true,
      calibre_read: false,
      calibre_rating: null,
      calibre_current_tags: ['lmelp_240324', 'babelio'],
    });

    const wrapper = mountComponent();
    await wrapper.vm.$nextTick();
    await new Promise((resolve) => setTimeout(resolve, 50));

    expect(wrapper.find('[data-test="tag-missing"]').exists()).toBe(false);
  });

  it('does not show guillaume in tag delta comparison', async () => {
    // guillaume is the virtual library tag, it should be excluded from delta
    mockAxiosWithLivre({
      ...baseLivreData,
      // calibre_tags includes "guillaume" as first tag (virtual library tag)
      calibre_tags: ['guillaume', 'lmelp_240324'],
      calibre_in_library: true,
      calibre_read: false,
      calibre_rating: null,
      // guillaume is NOT in calibre_current_tags, but it should be ignored in delta
      calibre_current_tags: ['lmelp_240324'],
    });

    const wrapper = mountComponent();
    await wrapper.vm.$nextTick();
    await new Promise((resolve) => setTimeout(resolve, 50));

    // No tags should be missing (guillaume is excluded from delta)
    expect(wrapper.find('[data-test="tag-missing"]').exists()).toBe(false);
  });

  it('copy button includes notable tags (babelio, lu, onkindle) already in Calibre', async () => {
    // Real case: Calibre has babelio, guillaume, lmelp_210912, lu
    // Copy should produce: guillaume, lmelp_210912, babelio, lu
    // i.e. all calibre_tags + notable tags already in calibre_current_tags
    const writeTextMock = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, 'clipboard', {
      value: { writeText: writeTextMock },
      writable: true,
    });

    mockAxiosWithLivre({
      ...baseLivreData,
      calibre_tags: ['guillaume', 'lmelp_210912'],
      calibre_in_library: true,
      calibre_read: true,
      calibre_rating: null,
      // Current Calibre tags include notable tags: babelio, lu
      calibre_current_tags: ['babelio', 'guillaume', 'lmelp_210912', 'lu'],
    });

    const wrapper = mountComponent();
    await wrapper.vm.$nextTick();
    await new Promise((resolve) => setTimeout(resolve, 50));

    // Click copy button
    await wrapper.find('[data-test="copy-tags-btn"]').trigger('click');
    await wrapper.vm.$nextTick();

    // The copied string should include babelio and lu (notable tags from Calibre)
    expect(writeTextMock).toHaveBeenCalledOnce();
    const copiedText = writeTextMock.mock.calls[0][0];
    expect(copiedText).toContain('babelio');
    expect(copiedText).toContain('lu');
    expect(copiedText).toContain('lmelp_210912');
    expect(copiedText).toContain('guillaume');
  });

  it('copy button does NOT include non-notable tags from Calibre (e.g. onkindle not present)', async () => {
    // Only notable tags that are ALREADY in calibre_current_tags should be included
    const writeTextMock = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, 'clipboard', {
      value: { writeText: writeTextMock },
      writable: true,
    });

    mockAxiosWithLivre({
      ...baseLivreData,
      calibre_tags: ['guillaume', 'lmelp_240324'],
      calibre_in_library: true,
      calibre_read: false,
      calibre_rating: null,
      // Only babelio is in Calibre (not onkindle, not lu)
      calibre_current_tags: ['babelio', 'guillaume', 'lmelp_240324'],
    });

    const wrapper = mountComponent();
    await wrapper.vm.$nextTick();
    await new Promise((resolve) => setTimeout(resolve, 50));

    await wrapper.find('[data-test="copy-tags-btn"]').trigger('click');
    await wrapper.vm.$nextTick();

    expect(writeTextMock).toHaveBeenCalledOnce();
    const copiedText = writeTextMock.mock.calls[0][0];
    expect(copiedText).toContain('babelio');
    expect(copiedText).not.toContain('onkindle'); // not in calibre_current_tags
    expect(copiedText).not.toContain('lu');       // not in calibre_current_tags
  });

  it('copy button works normally (no notable tags added) when book is not in Calibre', async () => {
    const writeTextMock = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, 'clipboard', {
      value: { writeText: writeTextMock },
      writable: true,
    });

    mockAxiosWithLivre({
      ...baseLivreData,
      calibre_tags: ['guillaume', 'lmelp_240324'],
      calibre_in_library: false,
      calibre_current_tags: null,
    });

    const wrapper = mountComponent();
    await wrapper.vm.$nextTick();
    await new Promise((resolve) => setTimeout(resolve, 50));

    await wrapper.find('[data-test="copy-tags-btn"]').trigger('click');
    await wrapper.vm.$nextTick();

    expect(writeTextMock).toHaveBeenCalledOnce();
    const copiedText = writeTextMock.mock.calls[0][0];
    expect(copiedText).toContain('guillaume');
    expect(copiedText).toContain('lmelp_240324');
    // No notable tags added since not in Calibre
    expect(copiedText).not.toContain('babelio');
    expect(copiedText).not.toContain('lu');
  });
});
