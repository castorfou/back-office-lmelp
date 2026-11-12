/**
 * Ouvrir la page Livres et Auteurs ne doit rien envoyer à Babelio.
 *
 * Babelio transforme ses 403 en ban IP (~24 h). À l'ouverture, la page
 * renvoyait au serveur le cookie gardé dans le navigateur (souvent périmé, et
 * cet envoi refermait le circuit breaker), puis validait automatiquement les
 * livres de l'épisode auto-sélectionné. La validation se lance désormais avec
 * le bouton « Valider avec Babelio ».
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { createRouter, createMemoryHistory } from 'vue-router';
import axios from 'axios';
import LivresAuteurs from '../../src/views/LivresAuteurs.vue';

vi.mock('axios');

vi.mock('../../src/services/api.js', () => ({
  livresAuteursService: {
    getEpisodesWithReviews: vi.fn(),
    getLivresAuteurs: vi.fn(),
    deleteCacheByEpisode: vi.fn(),
    setValidationResults: vi.fn(),
    autoProcessVerifiedBooks: vi.fn(),
  },
  episodeService: {
    getEpisodeById: vi.fn(),
  },
  babelioService: {},
  fuzzySearchService: {},
}));

// Les cellules BiblioValidationCell créent leur propre instance du service :
// leurs appels sont comptés dans cellValidateBiblio.
const { cellValidateBiblio } = vi.hoisted(() => ({ cellValidateBiblio: vi.fn() }));

vi.mock('../../src/services/BiblioValidationService.js', () => ({
  default: {
    validateBiblio: vi.fn(),
  },
  BiblioValidationService: class {
    validateBiblio(...args) {
      return cellValidateBiblio(...args);
    }
  },
}));

import { livresAuteursService, episodeService } from '../../src/services/api.js';
import BiblioValidationService from '../../src/services/BiblioValidationService.js';

const EPISODE_ID = '68c707ad6e51b9428ab87e9e'; // pragma: allowlist secret

const bookWithoutStatus = {
  cache_id: 'cache1',
  episode_oid: EPISODE_ID,
  auteur: 'Emmanuelle Salasc',
  titre: 'Ni de lait, ni de laine',
  editeur: 'P.O.L',
  programme: true,
};

function mountPage() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/livres-auteurs', component: LivresAuteurs }],
  });
  router.push('/livres-auteurs');
  return router.isReady().then(() =>
    mount(LivresAuteurs, { global: { plugins: [router] } })
  );
}

describe('LivresAuteurs - aucune requête Babelio à l\'ouverture', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    localStorage.setItem('babelio_cookies', 'jstsToken=<REDACTED>');
    axios.get.mockResolvedValue({ data: {} });
    axios.post.mockResolvedValue({ data: {} });
    livresAuteursService.getEpisodesWithReviews.mockResolvedValue([
      {
        id: EPISODE_ID,
        date: '2024-07-21',
        titre: 'Que lire cet été ?',
        has_cached_books: false,
        has_incomplete_books: false,
      },
    ]);
    livresAuteursService.getLivresAuteurs.mockResolvedValue([bookWithoutStatus]);
    livresAuteursService.setValidationResults.mockResolvedValue({ success: true });
    livresAuteursService.autoProcessVerifiedBooks.mockResolvedValue({ success: true });
    episodeService.getEpisodeById.mockResolvedValue({ id: EPISODE_ID });
    BiblioValidationService.validateBiblio.mockResolvedValue({ status: 'verified', data: {} });
    cellValidateBiblio.mockResolvedValue({ status: 'verified', data: {} });
  });

  afterEach(() => {
    localStorage.removeItem('babelio_cookies');
  });

  it('n\'envoie ni cookie ni validation Babelio à l\'ouverture', async () => {
    const wrapper = await mountPage();
    await flushPromises();

    expect(wrapper.vm.selectedEpisodeId).toBe(EPISODE_ID);
    expect(BiblioValidationService.validateBiblio).not.toHaveBeenCalled();
    expect(cellValidateBiblio).not.toHaveBeenCalled();
    expect(axios.post).not.toHaveBeenCalledWith('/api/babelio/cookie', expect.anything());
  });

  it('valide les livres avec Babelio sur clic du bouton', async () => {
    const wrapper = await mountPage();
    await flushPromises();

    await wrapper.find('[data-test="validate-babelio-button"]').trigger('click');
    await flushPromises();

    // L'enrichissement Babelio de l'extraction n'a lieu que sur ce clic
    expect(livresAuteursService.getLivresAuteurs).toHaveBeenCalledWith({
      episode_oid: EPISODE_ID,
      enrich_babelio: true,
    });
    expect(BiblioValidationService.validateBiblio).toHaveBeenCalledWith(
      'Emmanuelle Salasc', 'Ni de lait, ni de laine', 'P.O.L', EPISODE_ID
    );
  });

  it('affiche la progression pendant la validation', async () => {
    const wrapper = await mountPage();
    await flushPromises();

    // Enrichissement en attente : le bouton annonce la phase en cours
    let resolveEnrich;
    livresAuteursService.getLivresAuteurs.mockImplementationOnce(
      () => new Promise((resolve) => { resolveEnrich = resolve; })
    );
    let resolveValidation;
    BiblioValidationService.validateBiblio.mockImplementationOnce(
      () => new Promise((resolve) => { resolveValidation = resolve; })
    );

    await wrapper.find('[data-test="validate-babelio-button"]').trigger('click');
    await flushPromises();
    const button = () => wrapper.find('[data-test="validate-babelio-button"]');
    expect(button().text()).toContain('Enrichissement Babelio');

    resolveEnrich([bookWithoutStatus]);
    await flushPromises();
    expect(button().text()).toContain('Validation 1/1');
    expect(button().text()).toContain('Ni de lait, ni de laine');

    resolveValidation({ status: 'verified', data: {} });
    await flushPromises();
    expect(button().text()).toContain('Valider avec Babelio');
  });

  it('ouvre le panneau cookie quand l\'extraction depuis une URL est refusée (403)', async () => {
    const wrapper = await mountPage();
    await flushPromises();

    const message = 'Cookie Babelio périmé (606s, max 300s) — collez un cookie frais';
    axios.post.mockRejectedValueOnce({
      response: { status: 403, data: { status: 'blocked', message } },
    });
    wrapper.vm.validationBabelioUrl = 'https://www.babelio.com/livres/Hassaine-Je/2033456';
    await wrapper.vm.extractFromBabelioUrl('validation');

    expect(wrapper.vm.validationUrlError).toBe(message);
    expect(wrapper.vm.babelioBlocked).toBe(true);
  });
});
