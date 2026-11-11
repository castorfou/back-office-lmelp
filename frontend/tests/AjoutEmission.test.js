/**
 * Tests de la vue AjoutEmission (Issue #334) : ajout d'une émission absente
 * du flux RSS à partir de sa page radiofrance.fr.
 *
 * Réponse de POST /api/episodes/from-radiofrance-page calquée sur le
 * résultat réel de ManualEpisodeService.add_from_radiofrance_page().
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { mount } from '@vue/test-utils';
import AjoutEmission from '../src/views/AjoutEmission.vue';
import axios from 'axios';

vi.mock('axios');

const PAGE_URL =
  'https://www.radiofrance.fr/franceinter/podcasts/le-masque-et-la-plume/' +
  'le-masque-et-la-plume-du-dimanche-21-juillet-2024-6686255';

const ADDED = {
  episode_id: '6732a1b2c3d4e5f6a7b8c9d0',
  titre: 'Zadie Smith, Emmanuelle Salasc, Yasmina Liassine, Julien Blanc-Gras... Que lire cet été ?',
  date: '2024-07-21',
  duree: 2809,
  episode_page_url: PAGE_URL,
  audio_rel_filename: '2024/14007-21.07.2024-ITEMA_23808923-2024F4007S0203-27.m4a',
  transcription_status: 'started',
};

const mountComponent = () =>
  mount(AjoutEmission, {
    global: {
      stubs: {
        'router-link': { props: ['to'], template: '<a :href="to"><slot /></a>' },
        Navigation: true,
      },
    },
  });

describe('AjoutEmission', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('envoie l\'URL de la page et affiche l\'émission ajoutée avec les liens de suite', async () => {
    axios.post.mockResolvedValueOnce({ data: ADDED });

    const wrapper = mountComponent();
    await wrapper.find('[data-testid="page-url-input"]').setValue(PAGE_URL);
    await wrapper.vm.addEpisode();
    await wrapper.vm.$nextTick();

    expect(axios.post).toHaveBeenCalledWith('/api/episodes/from-radiofrance-page', { url: PAGE_URL });

    const result = wrapper.find('[data-testid="add-result"]');
    expect(result.text()).toContain('Zadie Smith');
    expect(result.text()).toContain('21/07/2024');
    expect(result.text()).toContain('46 min 49 s');

    // L'émission (collection emissions) n'existe qu'après génération des
    // avis critiques : pas de lien vers /emissions à ce stade.
    const links = result.findAll('a').map((a) => a.attributes('href'));
    expect(links).toEqual(['/transcription-pgx', '/generation-avis-critiques']);
    expect(result.text()).toContain('Transcription lancée');
    expect(wrapper.find('[data-testid="add-error"]').exists()).toBe(false);
  });

  it.each([
    ['already_running', 'Transcription déjà en cours'],
    ['error', 'Transcription non lancée'],
  ])('indique le statut de transcription %s', async (status, expected) => {
    axios.post.mockResolvedValueOnce({ data: { ...ADDED, transcription_status: status } });

    const wrapper = mountComponent();
    await wrapper.find('[data-testid="page-url-input"]').setValue(PAGE_URL);
    await wrapper.vm.addEpisode();
    await wrapper.vm.$nextTick();

    expect(wrapper.find('[data-testid="transcription-status"]').text()).toContain(expected);
  });

  it('affiche le motif du refus renvoyé par le backend', async () => {
    axios.post.mockRejectedValueOnce({
      response: {
        status: 409,
        data: { detail: 'Une émission existe déjà le 21/07/2024 : « Lectures d\'été »' },
      },
    });

    const wrapper = mountComponent();
    await wrapper.find('[data-testid="page-url-input"]').setValue(PAGE_URL);
    await wrapper.vm.addEpisode();
    await wrapper.vm.$nextTick();

    expect(wrapper.find('[data-testid="add-error"]').text()).toContain('existe déjà le 21/07/2024');
    expect(wrapper.find('[data-testid="add-result"]').exists()).toBe(false);
  });

  it('affiche un message générique si le backend ne répond pas', async () => {
    axios.post.mockRejectedValueOnce(new Error('Network Error'));

    const wrapper = mountComponent();
    await wrapper.find('[data-testid="page-url-input"]').setValue(PAGE_URL);
    await wrapper.vm.addEpisode();
    await wrapper.vm.$nextTick();

    expect(wrapper.find('[data-testid="add-error"]').text()).toContain('Network Error');
  });

  it('désactive le bouton tant que l\'URL est vide ou qu\'un ajout est en cours', async () => {
    let resolvePost;
    axios.post.mockReturnValueOnce(new Promise((resolve) => { resolvePost = resolve; }));

    const wrapper = mountComponent();
    const button = wrapper.find('[data-testid="add-button"]');
    expect(button.attributes('disabled')).toBeDefined();

    await wrapper.find('[data-testid="page-url-input"]').setValue(PAGE_URL);
    expect(button.attributes('disabled')).toBeUndefined();

    const pending = wrapper.vm.addEpisode();
    await wrapper.vm.$nextTick();
    expect(button.attributes('disabled')).toBeDefined();

    resolvePost({ data: ADDED });
    await pending;
    await wrapper.vm.$nextTick();
    expect(button.attributes('disabled')).toBeUndefined();
  });
});
