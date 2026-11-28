/**
 * Fiche livre : écouter les critiques parler du livre dans chacune de ses
 * émissions (Issue #427).
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import LivreDetail from '../LivreDetail.vue';
import axios from 'axios';

vi.mock('axios', () => ({ default: { get: vi.fn() } }));

const LIVRE_ID = '6afd594de81df360960133fb'; // pragma: allowlist secret

const LIVRE = {
  livre_id: LIVRE_ID,
  titre: 'Le Fondateur',
  auteur_id: 'a1',
  auteur_nom: 'Giuliano da Empoli',
  editeur: 'Gallimard',
  note_moyenne: 7.5,
  nombre_emissions: 2,
  emissions: [
    { emission_id: 'm1', episode_id: 'e1', date: '2026-11-15', nombre_avis: 4, note_moyenne: 7.5 },
    { emission_id: 'm2', episode_id: 'e2', date: '2026-10-04', nombre_avis: 1, note_moyenne: null },
  ],
};

const PASSAGE = {
  id: 'p1', titre: 'Le Fondateur', auteur: 'Giuliano da Empoli', livre_id: LIVRE_ID,
  debut_ms: 447000, fin_ms: 813000, episode_id: 'e1', date: '2026-11-15', origine: 'auto',
};

function monter() {
  return mount(LivreDetail, {
    global: {
      mocks: { $route: { params: { id: LIVRE_ID } }, $router: { back: vi.fn() } },
      stubs: {
        'router-link': { template: '<a><slot /></a>', props: ['to'] },
        Navigation: { template: '<div />' },
      },
    },
  });
}

describe('LivreDetail - écoute des Passages', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    axios.get.mockImplementation((url) => {
      if (url.includes('/api/livres/') && url.endsWith('/passages')) {
        return Promise.resolve({
          data: {
            passages: [PASSAGE],
            sans_passage: [{ episode_id: 'e2', raison: 'pas_de_segments' }],
          },
        });
      }
      if (url.includes('/api/livre/')) return Promise.resolve({ data: LIVRE });
      if (url.includes('/api/avis/by-livre/')) return Promise.resolve({ data: { avis: [] } });
      if (url.includes('/api/config/annas-archive-url')) {
        return Promise.resolve({ data: { url: 'https://fr.annas-archive.org' } });
      }
      return Promise.reject(new Error(`URL inattendue : ${url}`));
    });
  });

  it("met un rond d'écoute sur l'émission où le livre a un Passage, et dit pourquoi ailleurs", async () => {
    const fiche = monter();
    await flushPromises();

    const [avecPassage, sansPassage] = fiche.findAll('[data-test="emission-item"]');
    expect(avecPassage.find('button[aria-label="Écouter le Passage"]').exists()).toBe(true);
    expect(sansPassage.find('.passage-absent').attributes('title')).toMatch(
      /pas de transcription horodatée/,
    );
  });

  it('garde la fiche quand les Passages ne se chargent pas', async () => {
    axios.get.mockImplementation((url) => {
      if (url.endsWith('/passages')) return Promise.reject(new Error('réseau'));
      if (url.includes('/api/livre/')) return Promise.resolve({ data: LIVRE });
      if (url.includes('/api/avis/by-livre/')) return Promise.resolve({ data: { avis: [] } });
      return Promise.resolve({ data: { url: 'https://fr.annas-archive.org' } });
    });

    const fiche = monter();
    await flushPromises();

    expect(fiche.findAll('[data-test="emission-item"]')).toHaveLength(2);
    expect(fiche.find('.passage-rond').exists()).toBe(false);
  });
});
