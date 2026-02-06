import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount } from '@vue/test-utils';
import LivreDetail from '../LivreDetail.vue';
import axios from 'axios';

// Mock axios
vi.mock('axios', () => ({
  default: {
    get: vi.fn(),
  },
}));

// Mock router
const mockRoute = {
  params: { id: '507f1f77bcf86cd799439011' }, // pragma: allowlist secret
};

const mockRouter = {
  back: vi.fn(),
};

describe('LivreDetail - Avis des critiques (Issue #201)', () => {
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

  it('should display avis section when avis exist', async () => {
    // Mock livre response
    axios.get.mockImplementation((url) => {
      if (url.includes('/api/livre/')) {
        return Promise.resolve({
          data: {
            livre_id: '507f1f77bcf86cd799439011',
            titre: 'Love me tender',
            auteur_id: '507f1f77bcf86cd799439012',
            auteur_nom: 'Constance Debré',
            editeur: 'Flammarion',
            note_moyenne: 7.5,
            nombre_emissions: 1,
            emissions: [],
          },
        });
      }
      if (url.includes('/api/avis/by-livre/')) {
        return Promise.resolve({
          data: {
            avis: [
              {
                id: 'avis1',
                emission_oid: 'em1',
                critique_oid: 'crit1',
                critique_nom: 'Arnaud Viviant',
                critique_nom_extrait: 'Arnaud Viviant',
                commentaire: 'Impressionnant',
                note: 8,
                section: 'programme',
                emission_date: '2025-01-26T00:00:00.000Z',
              },
              {
                id: 'avis2',
                emission_oid: 'em1',
                critique_nom_extrait: 'Elisabeth Philippe',
                commentaire: 'Très beau',
                note: 9,
                section: 'programme',
                emission_date: '2025-01-26T00:00:00.000Z',
              },
            ],
          },
        });
      }
      if (url.includes('/api/config/annas-archive-url')) {
        return Promise.resolve({ data: { url: 'https://fr.annas-archive.org' } });
      }
      return Promise.reject(new Error(`Unexpected URL: ${url}`));
    });

    const wrapper = mountComponent();
    await wrapper.vm.$nextTick();
    // Wait for async mounted
    await new Promise((resolve) => setTimeout(resolve, 50));

    const html = wrapper.html();
    expect(html).toContain('Avis des critiques');
    expect(html).toContain('Arnaud Viviant');
    expect(html).toContain('Impressionnant');
  });

  it('should not display avis section when no avis', async () => {
    axios.get.mockImplementation((url) => {
      if (url.includes('/api/livre/')) {
        return Promise.resolve({
          data: {
            livre_id: '507f1f77bcf86cd799439011',
            titre: 'Livre sans avis',
            auteur_id: '507f1f77bcf86cd799439012',
            auteur_nom: 'Auteur Test',
            editeur: 'Éditeur',
            note_moyenne: null,
            nombre_emissions: 0,
            emissions: [],
          },
        });
      }
      if (url.includes('/api/avis/by-livre/')) {
        return Promise.resolve({ data: { avis: [] } });
      }
      if (url.includes('/api/config/annas-archive-url')) {
        return Promise.resolve({ data: { url: 'https://fr.annas-archive.org' } });
      }
      return Promise.reject(new Error(`Unexpected URL: ${url}`));
    });

    const wrapper = mountComponent();
    await wrapper.vm.$nextTick();
    await new Promise((resolve) => setTimeout(resolve, 50));

    expect(wrapper.find('[data-test="avis-critiques-section"]').exists()).toBe(false);
  });

  it('should group avis by emission date', async () => {
    axios.get.mockImplementation((url) => {
      if (url.includes('/api/livre/')) {
        return Promise.resolve({
          data: {
            livre_id: '507f1f77bcf86cd799439011',
            titre: 'Multi-emission book',
            auteur_id: '507f1f77bcf86cd799439012',
            auteur_nom: 'Auteur Test',
            editeur: 'Éditeur',
            note_moyenne: 8.0,
            nombre_emissions: 2,
            emissions: [],
          },
        });
      }
      if (url.includes('/api/avis/by-livre/')) {
        return Promise.resolve({
          data: {
            avis: [
              {
                id: 'avis1',
                emission_oid: 'em1',
                critique_nom: 'Critique A',
                critique_nom_extrait: 'Critique A',
                commentaire: 'Avis 1',
                note: 8,
                section: 'programme',
                emission_date: '2025-01-26T00:00:00.000Z',
              },
              {
                id: 'avis2',
                emission_oid: 'em2',
                critique_nom: 'Critique B',
                critique_nom_extrait: 'Critique B',
                commentaire: 'Avis 2',
                note: 7,
                section: 'programme',
                emission_date: '2024-12-15T00:00:00.000Z',
              },
            ],
          },
        });
      }
      if (url.includes('/api/config/annas-archive-url')) {
        return Promise.resolve({ data: { url: 'https://fr.annas-archive.org' } });
      }
      return Promise.reject(new Error(`Unexpected URL: ${url}`));
    });

    const wrapper = mountComponent();
    await wrapper.vm.$nextTick();
    await new Promise((resolve) => setTimeout(resolve, 50));

    // Should have avis grouped - verify both critics appear
    const html = wrapper.html();
    expect(html).toContain('Critique A');
    expect(html).toContain('Critique B');
    // Should show emission dates
    expect(html).toContain('26 janvier 2025');
    expect(html).toContain('15 décembre 2024');
  });
});
