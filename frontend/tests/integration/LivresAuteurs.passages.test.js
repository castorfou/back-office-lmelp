/**
 * Livres-auteurs : écouter les Passages de l'émission (Issue #427, prototype
 * #423 variante C). Rond ▶/○ devant chaque titre, colonne « ⏱ Émission »,
 * ordre de l'émission par défaut, section « Écouter l'émission » sous le tableau.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { createRouter, createWebHistory } from 'vue-router';
import LivresAuteurs from '../../src/views/LivresAuteurs.vue';
import { livresAuteursService, passagesService } from '../../src/services/api.js';
import axios from 'axios';

vi.mock('axios');

vi.mock('../../src/services/api.js', () => ({
  livresAuteursService: {
    getLivresAuteurs: vi.fn(),
    getEpisodesWithReviews: vi.fn(),
    getCollectionsStatistics: vi.fn(),
    autoProcessVerifiedBooks: vi.fn(),
    autoProcessVerified: vi.fn(),
    getBooksByValidationStatus: vi.fn(),
    validateSuggestion: vi.fn(),
    addManualBook: vi.fn(),
    getAllAuthors: vi.fn(),
    getAllBooks: vi.fn(),
    setValidationResults: vi.fn(),
    deleteCacheByEpisode: vi.fn(),
  },
  episodeService: {
    getAllEpisodes: vi.fn(),
    getEpisodeById: vi.fn(),
    updateEpisodeDescription: vi.fn(),
    updateEpisodeTitle: vi.fn(),
  },
  statisticsService: { getStatistics: vi.fn() },
  babelioService: { verifyAuthor: vi.fn(), verifyBook: vi.fn(), verifyPublisher: vi.fn() },
  fuzzySearchService: { searchEpisode: vi.fn() },
  passagesService: {
    getCorrectionEpisode: vi.fn(),
    getPassagesEpisode: vi.fn(),
  },
}));

const EPISODE_OID = '6af98629a3c9beafb9dcb702'; // pragma: allowlist secret

// lignes relevées sur GET /api/livres-auteurs?episode_oid=… (15/11/2026)
const LIGNES = [
  {
    episode_oid: EPISODE_OID, titre: 'Paradisi Gloria', auteur: 'Elise Lespade', editeur: 'Gallimard',
    book_id: 'l-paradisi', status: 'mongo', programme: true, coup_de_coeur: false, cache_id: 'c1',
  },
  {
    // titre validé différent du titre du résumé : le Passage se retrouve par le livre
    episode_oid: EPISODE_OID, titre: 'Le Fondateur', auteur: 'Giuliano da Empoli', editeur: 'Gallimard',
    book_id: 'l-fondateur', status: 'mongo', programme: true, coup_de_coeur: false, cache_id: 'c2',
  },
  {
    // pas encore validé : pas de livre, le Passage se retrouve par le titre
    episode_oid: EPISODE_OID, titre: 'Rouge truite', auteur: 'Pierric Bailly', editeur: 'P.O.L',
    book_id: null, status: 'suggested', programme: true, coup_de_coeur: false, cache_id: 'c3',
  },
  {
    episode_oid: EPISODE_OID, titre: 'Vivre après', auteur: 'Jérôme Garcin', editeur: 'Gallimard',
    book_id: null, status: 'not_found', programme: false, coup_de_coeur: true, cache_id: 'c4',
  },
];

const passage = (id, titre, livreId, debutMs, finMs) => ({
  id, titre, auteur: 'x', section: 1, livre_id: livreId, episode_id: EPISODE_OID,
  date: '2026-11-15', debut_ms: debutMs, fin_ms: finMs, origine: 'auto', place_main: false,
});

const ETAT = {
  segments: [
    [0, 447460, 'Générique.'],
    [447460, 600000, 'On commence avec le Fondateur.'],
    [600000, 803880, 'Arnaud ?'],
    [803880, 1159720, 'On enchaîne avec Paradisi Gloria.'],
    [1159720, 1613240, 'Le courrier.'],
    [1613240, 2021920, 'Après ce livre, Rouge Truite.'],
  ],
  a_des_segments: true,
  valide: false,
  passages: [
    passage('pa', 'Le fondateur', 'l-fondateur', 447460, 803880),
    passage('pb', 'Paradisi Gloria', 'l-paradisi', 803880, 1159720),
    passage('pc', 'Rouge Truite', null, 1613240, 2021920),
  ],
  supprimes: [],
  sans_passage: [{ titre: 'Vivre après', auteur: 'Jérôme Garcin', section: 2, livre_id: null, raison: 'non_repere' }],
};

const SANS_SEGMENTS = {
  segments: [], a_des_segments: false, valide: false, passages: [], supprimes: [],
  sans_passage: LIGNES.map((l) => ({ titre: l.titre, auteur: l.auteur, section: 1, livre_id: l.book_id, raison: 'pas_de_segments' })),
};

describe('LivresAuteurs - écoute des Passages (Issue #427)', () => {
  let wrapper;
  let router;

  beforeEach(async () => {
    vi.resetAllMocks();
    HTMLMediaElement.prototype.play = vi.fn(() => Promise.resolve());
    HTMLMediaElement.prototype.pause = vi.fn();
    Element.prototype.scrollIntoView = vi.fn();
    Element.prototype.scrollTo = vi.fn();
    axios.get.mockImplementation((url) => {
      if (url.startsWith('/api/babelio/status')) {
        return Promise.resolve({
          data: { cookie_active: true, cookie_age_sec: 10, cookie_max_age_sec: 300, cookie_expired: false },
        });
      }
      return Promise.resolve({ data: {} });
    });
    axios.post.mockResolvedValue({ data: {} });
    sessionStorage.clear();
    livresAuteursService.autoProcessVerifiedBooks.mockResolvedValue({});
    livresAuteursService.getEpisodesWithReviews.mockResolvedValue([
      { id: EPISODE_OID, titre: 'CRITIQUE', date: '2026-11-15T09:12:40', review_count: 1 },
    ]);
    livresAuteursService.getLivresAuteurs.mockImplementation(() => Promise.resolve(LIGNES.map((l) => ({ ...l }))));
    passagesService.getCorrectionEpisode.mockResolvedValue(ETAT);
    passagesService.getPassagesEpisode.mockResolvedValue({ ...ETAT, segments: [] });

    router = createRouter({
      history: createWebHistory(),
      routes: [
        { path: '/', component: { template: '<div />' } },
        { path: '/livres-auteurs', component: LivresAuteurs },
        { path: '/livre/:id', component: { template: '<div />' } },
        { path: '/auteur/:id', component: { template: '<div />' } },
      ],
    });
    await router.push('/livres-auteurs');
  });

  afterEach(() => {
    if (wrapper) wrapper.unmount();
    sessionStorage.clear();
    vi.restoreAllMocks();
  });

  async function monter() {
    wrapper = mount(LivresAuteurs, { global: { plugins: [router] } });
    await flushPromises();
    wrapper.vm.selectedEpisodeId = EPISODE_OID;
    await flushPromises();
    await wrapper.vm.loadBooksForEpisode();
    await flushPromises();
    return wrapper;
  }

  const lignes = () => wrapper.findAll('[data-testid="book-item"]');
  const ligne = (titre) => lignes().find((l) => l.find('.title-cell').text().includes(titre));

  it("trie les livres dans l'ordre de l'émission, livres sans Passage à la fin", async () => {
    await monter();

    expect(passagesService.getCorrectionEpisode).toHaveBeenCalledWith(EPISODE_OID);
    expect(lignes().map((l) => l.find('.passage-heure').text())).toEqual(['07:27', '13:23', '26:53', '—']);
    expect(wrapper.find('th.th-emission').text()).toContain('⏱ Émission');
  });

  it('met ▶ devant un titre qui a un Passage, validé ou non, et ○ sinon', async () => {
    await monter();

    expect(ligne('Le Fondateur').find('.la-rond').classes()).not.toContain('absent');
    expect(ligne('Rouge truite').find('.la-rond').classes()).not.toContain('absent');
    expect(ligne('Vivre après').find('.la-rond').classes()).toContain('absent');
  });

  it("▶ amène la section « Écouter l'émission » sur le Passage du livre et le joue", async () => {
    await monter();

    await ligne('Paradisi Gloria').find('.la-rond').trigger('click');
    await flushPromises();

    const section = wrapper.find('[data-test="ecouter-emission"]');
    expect(section.exists()).toBe(true);
    expect(section.find('[data-carte="pb"]').classes()).toContain('choisi');
    expect(HTMLMediaElement.prototype.play).toHaveBeenCalled();
    expect(wrapper.find('audio').element.currentTime).toBeCloseTo(803.88);
    expect(ligne('Paradisi Gloria').classes()).toContain('la-ligne-active');
  });

  it('○ met « À placer » en évidence dans la section', async () => {
    await monter();

    await ligne('Vivre après').find('.la-rond').trigger('click');
    await flushPromises();

    const aPlacer = wrapper.find('[data-test="ecouter-emission"] .a-placer');
    expect(aPlacer.text()).toContain('Vivre après');
    expect(aPlacer.classes()).toContain('ee-flash');
    expect(HTMLMediaElement.prototype.play).not.toHaveBeenCalled();
  });

  it('relit les Passages quand les livres sont rechargés (un titre validé retrouve son Passage)', async () => {
    await monter();
    passagesService.getPassagesEpisode.mockClear();

    await wrapper.vm.loadBooksForEpisode();
    await flushPromises();

    expect(passagesService.getPassagesEpisode).toHaveBeenCalledWith(EPISODE_OID);
  });

  it("n'ajoute ni rond, ni colonne, ni section à une émission sans Segments", async () => {
    passagesService.getCorrectionEpisode.mockResolvedValue(SANS_SEGMENTS);
    await monter();

    expect(lignes()).toHaveLength(4);
    expect(wrapper.find('.la-rond').exists()).toBe(false);
    expect(wrapper.find('th.th-emission').exists()).toBe(false);
    expect(wrapper.find('[data-test="ecouter-emission"]').exists()).toBe(false);
  });

  it('garde le tableau quand les Passages ne se chargent pas', async () => {
    passagesService.getCorrectionEpisode.mockRejectedValue(new Error('réseau'));
    await monter();

    expect(lignes()).toHaveLength(4);
    expect(wrapper.find('.la-rond').exists()).toBe(false);
  });
});
