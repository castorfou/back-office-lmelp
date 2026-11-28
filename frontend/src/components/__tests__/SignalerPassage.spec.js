/**
 * Signaler un Passage mal découpé depuis le lecteur (Issue #427, US 12 à 17).
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import SignalerPassage from '../SignalerPassage.vue';
import { lecteur } from '../../services/lecteurPassages.js';
import { signalementsService } from '@/services/api';

vi.mock('@/services/api', () => ({ signalementsService: { creer: vi.fn() } }));

const FONDATEUR = {
  id: 'p1', titre: 'Le Fondateur', auteur: 'Giuliano da Empoli', livre_id: 'l1',
  debut_ms: 447460, fin_ms: 803880, episode_id: 'e1', date: '2026-11-15',
};

describe('SignalerPassage', () => {
  let page;

  beforeEach(() => {
    vi.resetAllMocks();
    vi.useFakeTimers();
    lecteur.passage = FONDATEUR;
    lecteur.position = 760.4;
    signalementsService.creer.mockResolvedValue({ statut: 'enregistre' });
  });

  afterEach(() => {
    page?.unmount();
    vi.useRealTimers();
    lecteur.passage = null;
  });

  const monter = () => {
    page = mount(SignalerPassage, { attachTo: document.body });
    return page;
  };

  it("ouvre la liste des motifs et envoie le signalement avec l'instant d'écoute", async () => {
    monter();

    await page.find('.sig-btn').trigger('click');
    const motifs = page.findAll('.sig-menu button.motif').map((b) => b.text());
    expect(motifs).toEqual([
      'Début trop tôt', 'Fin trop tôt', 'Déborde sur un autre livre', 'Mauvais livre', 'Autre',
    ]);

    await page.find('.sig-menu textarea').setValue('  Coupé avant la fin du débat  ');
    await page.findAll('.sig-menu button.motif')[1].trigger('click');
    await flushPromises();

    expect(signalementsService.creer).toHaveBeenCalledWith({
      episode_id: 'e1', livre_id: 'l1', debut_ms: 447460, fin_ms: 803880,
      motif: 'fin_trop_tot', instant_ms: 760400, commentaire: 'Coupé avant la fin du débat',
    });
    expect(page.find('.sig-menu').exists()).toBe(false);
    expect(page.find('.sig-merci').text()).toBe('✓ Signalé : Fin trop tôt à 12:40');
  });

  it("joint l'instant où le menu s'ouvre, même si l'écoute continue pendant la saisie", async () => {
    monter();

    await page.find('.sig-btn').trigger('click');
    lecteur.position = 790;
    await page.find('.sig-menu textarea').setValue('Long commentaire');
    await page.findAll('.sig-menu button.motif')[1].trigger('click');
    await flushPromises();

    expect(signalementsService.creer.mock.calls[0][0].instant_ms).toBe(760400);
  });

  it('ne joint pas de commentaire vide', async () => {
    monter();

    await page.find('.sig-btn').trigger('click');
    await page.findAll('.sig-menu button.motif')[4].trigger('click');
    await flushPromises();

    expect(signalementsService.creer.mock.calls[0][0]).not.toHaveProperty('commentaire');
  });

  it('la confirmation disparaît seule', async () => {
    monter();
    await page.find('.sig-btn').trigger('click');
    await page.findAll('.sig-menu button.motif')[0].trigger('click');
    await flushPromises();

    vi.advanceTimersByTime(3000);
    await page.vm.$nextTick();

    expect(page.find('.sig-merci').exists()).toBe(false);
  });

  it('se ferme quand on clique ailleurs', async () => {
    monter();
    await page.find('.sig-btn').trigger('click');
    vi.runAllTimers();

    document.body.click();
    await page.vm.$nextTick();

    expect(page.find('.sig-menu').exists()).toBe(false);
  });

  it("dit pourquoi le signalement n'est pas parti", async () => {
    signalementsService.creer.mockRejectedValue(new Error('Pas de Passage pour cet épisode et ce livre'));
    monter();

    await page.find('.sig-btn').trigger('click');
    await page.findAll('.sig-menu button.motif')[0].trigger('click');
    await flushPromises();

    expect(page.find('.sig-erreur').text()).toContain('Pas de Passage');
  });

  it("n'est pas proposé pour un titre pas encore validé (sans livre)", () => {
    lecteur.passage = { ...FONDATEUR, livre_id: null };
    monter();

    expect(page.find('.sig-btn').exists()).toBe(false);
  });
});
