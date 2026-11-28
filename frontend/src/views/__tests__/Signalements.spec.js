/**
 * Page des signalements ouverts (Issue #427, US 19 à 21).
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import Signalements from '../Signalements.vue';
import { signalementsService } from '@/services/api';

vi.mock('@/services/api', () => ({
  signalementsService: { lister: vi.fn(), rejeter: vi.fn() },
}));

// forme de GET /api/signalements
const SIGNALEMENT = {
  id: 's1', episode_id: 'e1', date: '2026-11-15', livre_id: 'l1', titre: 'Le Fondateur',
  motif: 'fin_trop_tot', instant_ms: 760400, commentaire: 'Coupé avant la fin du débat',
  cree_le: '2026-11-28T16:10:00Z', source: 'mobile',
  bornes_ecoutees: { debut_ms: 447460, fin_ms: 803880 },
  bornes_actuelles: { debut_ms: 447460, fin_ms: 803880 },
  passage_id: 'p1',
};

function monter() {
  return mount(Signalements, {
    global: {
      stubs: {
        Navigation: { template: '<div />' },
        'router-link': { template: '<a class="lien" :data-to="JSON.stringify(to)"><slot /></a>', props: ['to'] },
      },
    },
  });
}

describe('Signalements', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('liste chaque signalement ouvert avec ce qu\'il faut pour corriger', async () => {
    signalementsService.lister.mockResolvedValue([SIGNALEMENT]);
    const page = monter();
    await flushPromises();

    const ligne = page.find('[data-test="signalement"]').text();
    expect(ligne).toContain('15 novembre 2026');
    expect(ligne).toContain('Le Fondateur');
    expect(ligne).toContain('Fin trop tôt');
    expect(ligne).toContain('12:40');
    expect(ligne).toContain('Coupé avant la fin du débat');
    expect(ligne).toContain('mobile');
    expect(ligne).toContain('7:27 → 13:23');
    const lien = JSON.parse(page.find('[data-test="corriger"]').attributes('data-to'));
    expect(lien).toEqual({ path: '/correction-passages', query: { episode: 'e1', passage: 'p1' } });
  });

  it('montre que les bornes ont changé depuis le signalement', async () => {
    signalementsService.lister.mockResolvedValue([
      { ...SIGNALEMENT, bornes_actuelles: { debut_ms: 447460, fin_ms: 840000 } },
    ]);
    const page = monter();
    await flushPromises();

    const bornes = page.find('[data-test="bornes"]');
    expect(bornes.text()).toContain('maintenant 7:27 → 14:00');
    expect(bornes.classes()).toContain('changees');
  });

  it('dit quand le Passage a disparu', async () => {
    signalementsService.lister.mockResolvedValue([
      { ...SIGNALEMENT, titre: null, bornes_actuelles: null, passage_id: null },
    ]);
    const page = monter();
    await flushPromises();

    expect(page.find('[data-test="bornes"]').text()).toContain('plus de Passage');
  });

  it('rejette un signalement et le retire de la liste', async () => {
    signalementsService.lister.mockResolvedValue([SIGNALEMENT]);
    signalementsService.rejeter.mockResolvedValue({ statut: 'rejete' });
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    const page = monter();
    await flushPromises();

    await page.find('[data-test="rejeter"]').trigger('click');
    await flushPromises();

    expect(signalementsService.rejeter).toHaveBeenCalledWith('s1');
    expect(page.find('[data-test="signalement"]').exists()).toBe(false);
    expect(page.text()).toContain('Aucun signalement ouvert');
  });

  it('dit pourquoi la liste ne se charge pas', async () => {
    signalementsService.lister.mockRejectedValue(new Error('Erreur réseau'));
    const page = monter();
    await flushPromises();

    expect(page.text()).toContain('Erreur réseau');
  });
});
