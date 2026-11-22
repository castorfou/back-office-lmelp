/**
 * Tests de la vue RemisesPap (Issue #378) : intégration des remises livrées
 * par lmelp-pap comme épisodes, remise par remise.
 *
 * Réponses calquées sur PapRemisesService.list_a_integrer() / integrer(),
 * à partir d'une fiche pap_remises réelle.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import RemisesPap from '../src/views/RemisesPap.vue';
import axios from 'axios';

vi.mock('axios');

const ID_2016 =
  'https://media.radiofrance-podcast.net/podcast09/14007-05.06.2016-ITEMA_21002286-2016F4007S0157-27.m4a';
const ID_2015 =
  'https://media.radiofrance-podcast.net/podcast09/14007-04.01.2015-ITEMA_20700000-2015F4007S0004-27.m4a';

const REMISES = [
  {
    remise_id: ID_2016,
    titre: 'Le Masque et la Plume du 5 juin 2016',
    date: '2016-06-05',
    duree: 3287,
    description:
      'durée : 00:54:47  - Le Masque et la Plume - par : Jérôme Garcin - équipe : Didier Lagarde, Lysiane Sellam',
    episode_page_url:
      'https://www.radiofrance.fr/franceinter/podcasts/le-masque-et-la-plume/et-si-on-lisait-4681667',
  },
  {
    remise_id: ID_2015,
    titre: 'Le Masque et la Plume du 4 janvier 2015',
    date: '2015-01-04',
    duree: null,
    description: 'Le Masque et la Plume - par : Jérôme Garcin',
    episode_page_url: null,
  },
];

const mountComponent = () =>
  mount(RemisesPap, {
    global: {
      stubs: {
        'router-link': { props: ['to'], template: '<a :href="to"><slot /></a>' },
        Navigation: true,
      },
    },
  });

const rows = (wrapper) => wrapper.findAll('[data-testid="remise-row"]');

describe('RemisesPap', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('liste les remises dans l\'ordre de l\'API, avec date, durée, description et lien radiofrance.fr', async () => {
    axios.get.mockResolvedValueOnce({ data: REMISES });

    const wrapper = mountComponent();
    await flushPromises();

    expect(axios.get).toHaveBeenCalledWith('/api/pap/remises');
    const [r2016, r2015] = rows(wrapper);
    expect(rows(wrapper)).toHaveLength(2);

    expect(r2016.text()).toContain('Le Masque et la Plume du 5 juin 2016');
    expect(r2016.text()).toContain('05/06/2016');
    expect(r2016.text()).toContain('54 min 47 s');
    expect(r2016.text()).toContain('Jérôme Garcin');
    expect(r2016.find('a.page-link').attributes('href')).toBe(REMISES[0].episode_page_url);

    // Sans page radiofrance.fr ni durée : affichée normalement
    expect(r2015.text()).toContain('04/01/2015');
    expect(r2015.find('a.page-link').exists()).toBe(false);
    expect(r2015.find('[data-testid="remise-duree"]').exists()).toBe(false);
  });

  it('intègre une remise : bouton désactivé pendant l\'appel, ligne retirée, résultat affiché', async () => {
    axios.get.mockResolvedValueOnce({ data: REMISES });
    let resolvePost;
    axios.post.mockReturnValueOnce(new Promise((resolve) => { resolvePost = resolve; }));

    const wrapper = mountComponent();
    await flushPromises();
    const button = rows(wrapper)[0].find('[data-testid="integrer-button"]');
    await button.trigger('click');

    expect(axios.post).toHaveBeenCalledWith('/api/pap/remises/integrer', { remise_id: ID_2016 });
    expect(button.attributes('disabled')).toBeDefined();
    expect(button.text()).toContain('Intégration…');
    // Les autres remises restent intégrables
    expect(rows(wrapper)[1].find('[data-testid="integrer-button"]').attributes('disabled')).toBeUndefined();

    resolvePost({
      data: {
        episode_id: '6af47e76a1c0d162e8518b99',
        remise_id: ID_2016,
        titre: 'Le Masque et la Plume du 5 juin 2016',
        date: '2016-06-05',
        transcription_status: 'started',
      },
    });
    await flushPromises();

    expect(rows(wrapper)).toHaveLength(1);
    expect(rows(wrapper)[0].text()).toContain('4 janvier 2015');
    expect(axios.get).toHaveBeenCalledTimes(1);
    const result = wrapper.find('[data-testid="integration-result"]');
    expect(result.text()).toContain('Le Masque et la Plume du 5 juin 2016');
    expect(result.text()).toContain('05/06/2016');
    expect(result.text()).toContain('Transcription lancée sur PGX');
  });

  it('affiche sur la ligne le refus du serveur et garde la remise', async () => {
    axios.get.mockResolvedValueOnce({ data: REMISES });
    axios.post.mockRejectedValueOnce({
      response: {
        status: 422,
        data: {
          detail: 'Empreinte SHA-256 du fichier audio différente de celle de la remise : copie incomplète ou corrompue',
        },
      },
    });

    const wrapper = mountComponent();
    await flushPromises();
    await rows(wrapper)[0].find('[data-testid="integrer-button"]').trigger('click');
    await flushPromises();

    expect(rows(wrapper)).toHaveLength(2);
    expect(rows(wrapper)[0].find('[data-testid="remise-error"]').text()).toContain('Empreinte SHA-256');
    expect(rows(wrapper)[0].find('[data-testid="integrer-button"]').attributes('disabled')).toBeUndefined();
    expect(wrapper.find('[data-testid="integration-result"]').exists()).toBe(false);
  });

  it('affiche l\'état vide quand aucune remise n\'est à intégrer', async () => {
    axios.get.mockResolvedValueOnce({ data: [] });

    const wrapper = mountComponent();
    await flushPromises();

    expect(wrapper.find('[data-testid="remises-empty"]').text()).toBe('Aucune remise à intégrer.');
  });

  it('affiche l\'état de chargement, puis l\'erreur de chargement', async () => {
    let rejectGet;
    axios.get.mockReturnValueOnce(new Promise((_resolve, reject) => { rejectGet = reject; }));

    const wrapper = mountComponent();
    await wrapper.vm.$nextTick();
    expect(wrapper.find('[data-testid="remises-loading"]').exists()).toBe(true);

    rejectGet({ message: 'Network Error' });
    await flushPromises();

    expect(wrapper.find('[data-testid="remises-loading"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="remises-load-error"]').text()).toContain('Network Error');
  });
});
