/**
 * Valider une suggestion ou ajouter un livre à la main transmet l'URL Babelio (Issue #339).
 *
 * Bug : l'URL collée dans la modale (utilisée par extract-from-url) n'était jamais
 * envoyée à validate-suggestion — seul book.babelio_url (cache) l'était. Le livre
 * arrivait en base sans url_babelio et repartait dans la page Liaison Babelio.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { createRouter, createWebHistory } from 'vue-router';
import axios from 'axios';
import LivresAuteurs from '../../src/views/LivresAuteurs.vue';
import { livresAuteursService } from '../../src/services/api.js';

vi.mock('axios');

vi.mock('../../src/services/api.js', () => ({
  livresAuteursService: {
    getLivresAuteurs: vi.fn(),
    getEpisodesWithReviews: vi.fn(),
    validateSuggestion: vi.fn(),
    getAllAuthors: vi.fn(),
    getAllBooks: vi.fn(),
  },
  episodeService: {
    getAllEpisodes: vi.fn(),
    getEpisodeById: vi.fn(),
  },
  statisticsService: {
    getStatistics: vi.fn(),
  },
  babelioService: {
    verifyAuthor: vi.fn(),
    verifyBook: vi.fn(),
    verifyPublisher: vi.fn(),
  },
  fuzzySearchService: {
    searchEpisode: vi.fn(),
  },
}));

// Documents réels de livresauteurs_cache (épisode du 01/11/2026)
const EPISODE_ID = '6ae7497087efd8d343531f86';
const AVIS_CRITIQUE_ID = '6ae7780230990f4e6e0392e0';
const BREBIS_URL = 'https://www.babelio.com/livres/Cash-Les-Brebis-egarees/2006493';
const JE_URL = 'https://www.babelio.com/livres/Hassaine-Je/2033456';

const brebis = {
  cache_id: '6af6289c714985e520bd0628',
  episode_oid: EPISODE_ID,
  auteur: 'Madeleine Cash',
  titre: 'Les brebis égarés',
  editeur: 'De Noël',
  status: 'suggested',
  suggested_author: 'Madeline Cash',
  suggested_title: 'Les Brebis égarées',
  babelio_url: BREBIS_URL,
  programme: false,
};

const je = {
  cache_id: '6af6289c714985e520bd0630',
  episode_oid: EPISODE_ID,
  auteur: 'Hassaine',
  titre: 'Je',
  editeur: 'Gallimard',
  status: 'not_found',
  programme: false,
};

describe('LivresAuteurs - URL Babelio transmise à la validation (Issue #339)', () => {
  let wrapper;

  beforeEach(async () => {
    vi.resetAllMocks();
    axios.post.mockResolvedValue({ data: { status: 'success', data: {} } });
    axios.get.mockResolvedValue({ data: {} });
    livresAuteursService.getEpisodesWithReviews.mockResolvedValue([]);
    livresAuteursService.getLivresAuteurs.mockResolvedValue([]);
    livresAuteursService.validateSuggestion.mockResolvedValue({ success: true });

    const router = createRouter({
      history: createWebHistory(),
      routes: [{ path: '/livres-auteurs', name: 'LivresAuteurs', component: LivresAuteurs }],
    });
    wrapper = mount(LivresAuteurs, {
      global: { plugins: [router], stubs: { BiblioValidationCell: true } },
    });
    await router.isReady();
    await wrapper.vm.$nextTick();

    wrapper.vm.selectedEpisodeId = EPISODE_ID;
    wrapper.vm.episodesWithReviews = [
      { id: EPISODE_ID, avis_critique_id: AVIS_CRITIQUE_ID },
    ];
  });

  afterEach(() => {
    wrapper?.unmount();
  });

  const sentData = () => livresAuteursService.validateSuggestion.mock.calls[0][0];

  it('[Validation] envoie l\'URL Babelio collée dans la modale', async () => {
    wrapper.vm.currentBookToValidate = je;
    wrapper.vm.validationForm = { author: 'Hassaine', title: 'Je', publisher: 'Gallimard' };
    wrapper.vm.validationBabelioUrl = JE_URL;

    await wrapper.vm.confirmValidation();

    expect(sentData().babelio_url).toBe(JE_URL);
  });

  it('[Validation] l\'URL collée remplace celle de la suggestion, sans son éditeur', async () => {
    wrapper.vm.currentBookToValidate = { ...brebis, babelio_publisher: 'De Noël' };
    wrapper.vm.validationForm = { author: 'Hassaine', title: 'Je', publisher: 'Gallimard' };
    wrapper.vm.validationBabelioUrl = JE_URL;

    await wrapper.vm.confirmValidation();

    expect(sentData().babelio_url).toBe(JE_URL);
    expect(sentData().babelio_publisher).toBeUndefined();
  });

  it('[Validation] sans URL collée, envoie l\'URL de la suggestion', async () => {
    wrapper.vm.currentBookToValidate = brebis;
    wrapper.vm.validationForm = {
      author: 'Madeline Cash',
      title: 'Les Brebis égarées',
      publisher: 'De Noël',
    };

    await wrapper.vm.confirmValidation();

    expect(sentData().babelio_url).toBe(BREBIS_URL);
  });

  it('[Ajout manuel] envoie l\'URL Babelio collée dans la modale', async () => {
    wrapper.vm.currentBookToAdd = je;
    wrapper.vm.manualBookForm = { author: 'Hassaine', title: 'Je', publisher: 'Gallimard' };
    wrapper.vm.manualBabelioUrl = `  ${JE_URL}  `;

    await wrapper.vm.submitManualAdd();

    expect(sentData().babelio_url).toBe(JE_URL);
  });

  it('[Ajout manuel] ignore une URL collée qui n\'est pas une URL Babelio', async () => {
    wrapper.vm.currentBookToAdd = je;
    wrapper.vm.manualBookForm = { author: 'Hassaine', title: 'Je', publisher: 'Gallimard' };
    wrapper.vm.manualBabelioUrl = 'https://exemple.com/livre';

    await wrapper.vm.submitManualAdd();

    expect(sentData().babelio_url).toBeUndefined();
  });

  it('[Ouverture modale] une suggestion avec URL Babelio pré-remplit le champ URL', () => {
    wrapper.vm.validateSuggestion(brebis);

    expect(wrapper.vm.validationBabelioUrl).toBe(BREBIS_URL);
  });

  it('[Ouverture modale] sans URL Babelio, le champ URL reste vide', () => {
    wrapper.vm.validateSuggestion(je);

    expect(wrapper.vm.validationBabelioUrl).toBe('');
  });

  it('[Ouverture modale] l\'éditeur Babelio remplace celui du markdown', async () => {
    axios.post.mockResolvedValue({
      data: {
        status: 'success',
        data: {
          titre: 'Les Brebis égarées',
          auteur: 'Madeline Cash',
          editeur: 'Éditions Noir sur Blanc',
          url_livre: BREBIS_URL,
        },
      },
    });

    wrapper.vm.validateSuggestion(brebis);
    // Watcher débouncé (500 ms) : lodash.debounce lit Date.now capturé au chargement,
    // les fake timers de Vitest ne l'avancent pas — attendre le vrai délai.
    await new Promise((resolve) => setTimeout(resolve, 650));
    await flushPromises();

    expect(axios.post).toHaveBeenCalledWith(
      '/api/babelio/extract-from-url',
      expect.objectContaining({ babelio_url: BREBIS_URL })
    );
    expect(wrapper.vm.validationForm.publisher).toBe('Éditions Noir sur Blanc');
    expect(wrapper.vm.validationForm.title).toBe('Les Brebis égarées');
  });
});
