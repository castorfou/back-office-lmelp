/**
 * Fiche émission : les Passages de l'émission sont chargés et donnés au
 * tableau des avis, qui met un rond d'écoute devant chaque titre (Issue #427).
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { createRouter, createMemoryHistory } from 'vue-router';
import Emissions from '../Emissions.vue';
import AvisTable from '../../components/AvisTable.vue';
import { emissionsService, avisService, passagesService } from '@/services/api';

vi.mock('@/services/api', () => ({
  emissionsService: { getAllEmissions: vi.fn(), getEmissionByDate: vi.fn() },
  avisService: { getAvisByEmission: vi.fn(), extractAvis: vi.fn() },
  episodeService: { fetchEpisodePageUrl: vi.fn() },
  passagesService: { getPassagesEpisode: vi.fn() },
}));

const PASSAGES = {
  a_des_segments: true,
  passages: [{
    id: 'p1', titre: 'Le Fondateur', auteur: 'Giuliano da Empoli', livre_id: 'l1',
    episode_id: 'e1', date: '2026-11-15', debut_ms: 447000, fin_ms: 813000, origine: 'auto',
  }],
  sans_passage: [],
};

async function monterLaFiche() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/emissions/:date?', name: 'emissions', component: Emissions }],
  });
  router.push('/emissions/20261115');
  await router.isReady();
  const fiche = mount(Emissions, {
    global: { plugins: [router], stubs: { Navigation: { template: '<div />' } } },
  });
  await flushPromises();
  return fiche;
}

describe('Emissions.vue - écoute des Passages', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    emissionsService.getAllEmissions.mockResolvedValue([
      { id: 'm1', date: '2026-11-15T09:12:40', badge_status: 'perfect', episode: { titre: 'Le Masque' } },
    ]);
    emissionsService.getEmissionByDate.mockResolvedValue({
      emission: { id: 'm1', date: '2026-11-15T09:12:40', episode_id: 'e1' },
      episode: { titre: 'Le Masque', date: '2026-11-15T09:12:40', episode_page_url: 'https://x' },
      summary: '## 1. LIVRES DISCUTÉS AU PROGRAMME',
    });
    avisService.getAvisByEmission.mockResolvedValue({
      avis: [{
        id: 'a1', section: 'programme', livre_oid: 'l1', livre_titre: 'Le Fondateur',
        livre_titre_extrait: 'Le Fondateur', auteur_nom_extrait: 'Giuliano da Empoli',
        critique_nom_extrait: 'Arnaud Viviant', note: 8,
      }],
      matching_stats: null,
    });
  });

  it("charge les Passages de l'épisode et les donne au tableau des avis", async () => {
    passagesService.getPassagesEpisode.mockResolvedValue(PASSAGES);

    const fiche = await monterLaFiche();

    expect(passagesService.getPassagesEpisode).toHaveBeenCalledWith('e1');
    expect(fiche.findComponent(AvisTable).props('passages')).toEqual(PASSAGES);
    expect(fiche.find('button[aria-label="Écouter le Passage"]').exists()).toBe(true);
  });

  it('garde le tableau des avis, sans rond, quand les Passages ne se chargent pas', async () => {
    passagesService.getPassagesEpisode.mockRejectedValue(new Error('réseau'));

    const fiche = await monterLaFiche();

    expect(fiche.findComponent(AvisTable).exists()).toBe(true);
    expect(fiche.find('.passage-rond').exists()).toBe(false);
  });
});
