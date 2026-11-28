/**
 * Page « Correction des passages » (Issue #427, prototype #398/#400/#401) :
 * chaque correction part au serveur, la page affiche l'état qu'il renvoie.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import CorrectionPassages from '../CorrectionPassages.vue';
import { emissionsService, passagesService } from '@/services/api';
import {
  EPISODE_ID, EMISSIONS, PASSAGE_A, PASSAGE_B, PASSAGE_C, LIVRE_A_PLACER,
  etatEmission, sansSegments,
} from './fixtures/correctionPassages';

vi.mock('@/services/api', () => ({
  emissionsService: { getAllEmissions: vi.fn() },
  passagesService: {
    getCorrectionEpisode: vi.fn(), getStatuts: vi.fn(),
    deplacerDebut: vi.fn(), deplacerFin: vi.fn(), supprimer: vi.fn(), restaurer: vi.fn(),
    deposer: vi.fn(), occuper: vi.fn(), remettre: vi.fn(),
    valider: vi.fn(), retirerValidation: vi.fn(),
  },
}));

async function monter() {
  const page = mount(CorrectionPassages, {
    global: {
      stubs: {
        Navigation: { template: '<div />' },
        'router-link': { template: '<a class="lien-livre"><slot /></a>', props: ['to'] },
      },
    },
  });
  await flushPromises();
  return page;
}

const carte = (page, p) => page.find(`[data-carte="${p.id}"]`);
const segment = (page, texte) => page.findAll('.seg').find((s) => s.text().includes(texte));

describe('CorrectionPassages', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    HTMLMediaElement.prototype.play = vi.fn(() => Promise.resolve());
    HTMLMediaElement.prototype.pause = vi.fn();
    // jsdom ne fait pas défiler
    Element.prototype.scrollIntoView = vi.fn();
    Element.prototype.scrollTo = vi.fn();
    emissionsService.getAllEmissions.mockResolvedValue(EMISSIONS);
    passagesService.getStatuts.mockResolvedValue({ [EPISODE_ID]: 'a_verifier' });
    passagesService.getCorrectionEpisode.mockResolvedValue(etatEmission());
  });

  it("met une pastille par émission et ouvre la première qui a des Segments", async () => {
    const page = await monter();

    const options = page.findAll('.dropdown-option').map((o) => o.text());
    expect(options.some((t) => t.startsWith('🟠'))).toBe(true);
    expect(options.some((t) => t.startsWith('🔴'))).toBe(true);
    expect(passagesService.getCorrectionEpisode).toHaveBeenCalledWith(EPISODE_ID);
    expect(page.findAll('[data-carte]')).toHaveLength(3);
    expect(page.find('audio').attributes('src')).toBe(`/api/episodes/${EPISODE_ID}/audio`);
  });

  it("dit qu'il n'y a rien à corriger sur une émission sans Segments", async () => {
    const page = await monter();

    await page.vm.choisir('m2');
    await flushPromises();

    expect(page.text()).toContain('Pas de Segments horodatés');
    expect(passagesService.getCorrectionEpisode).toHaveBeenCalledTimes(1);
  });

  it("pose le début d'un Passage à l'heure exacte du Segment cliqué", async () => {
    const deplace = { ...PASSAGE_B, debut_ms: 60000, origine: 'corrige' };
    passagesService.deplacerDebut.mockResolvedValue(sansSegments(etatEmission({
      passages: [{ ...PASSAGE_A, fin_ms: 60000, origine: 'corrige' }, deplace, PASSAGE_C],
    })));
    const page = await monter();

    await carte(page, PASSAGE_B).find('[title^="Placer le début"]').trigger('click');
    await segment(page, 'Arnaud ?').trigger('click');
    await flushPromises();

    expect(passagesService.deplacerDebut).toHaveBeenCalledWith('pb', 60000);
    expect(carte(page, PASSAGE_B).text()).toContain('01:00');
    expect(carte(page, PASSAGE_B).find('.badge').text()).toBe('corrigé');
    // la frontière partagée : la fin de A a suivi
    const journal = page.findAll('.journal li').map((l) => l.text());
    expect(journal.some((l) => l.includes('début de « Paradisi Gloria » : 02:00 → 01:00'))).toBe(true);
    expect(journal.some((l) => l.includes('↳ fin de « Le Fondateur » suit : 02:00 → 01:00'))).toBe(true);
    // les Segments restent affichés : les corrections ne les renvoient pas
    expect(page.findAll('.seg').length).toBeGreaterThan(5);
  });

  it('pose la fin à la fin du Segment cliqué', async () => {
    passagesService.deplacerFin.mockResolvedValue(sansSegments(etatEmission()));
    const page = await monter();

    await carte(page, PASSAGE_B).find('[title^="Placer la fin"]').trigger('click');
    await segment(page, 'Le courrier').trigger('click');
    await flushPromises();

    expect(passagesService.deplacerFin).toHaveBeenCalledWith('pb', 400000);
  });

  it('écrit dans le journal la raison d\'une correction refusée', async () => {
    passagesService.deplacerDebut.mockRejectedValue(new Error("Le début passerait avant celui de « Le Fondateur »"));
    const page = await monter();

    await carte(page, PASSAGE_B).find('[title^="Placer le début"]').trigger('click');
    await segment(page, 'Le masque').trigger('click');
    await flushPromises();

    expect(page.find('.journal').text()).toContain('refusé : Le début passerait avant');
    expect(carte(page, PASSAGE_B).find('.badge').text()).toBe('repéré auto');
  });

  it("valide les Passages de l'émission et passe sa pastille en 🟢", async () => {
    passagesService.valider.mockResolvedValue(sansSegments(etatEmission({ valide: true })));
    const page = await monter();

    await page.find('[data-test="valider"]').trigger('click');
    await flushPromises();

    expect(passagesService.valider).toHaveBeenCalledWith(EPISODE_ID);
    expect(page.find('[data-test="valider"]').text()).toContain('Passages validés (annuler)');
    expect(page.findAll('.dropdown-option').some((o) => o.text().startsWith('🟢'))).toBe(true);
  });

  it('retire la validation au deuxième clic', async () => {
    passagesService.getCorrectionEpisode.mockResolvedValue(etatEmission({ valide: true }));
    passagesService.retirerValidation.mockResolvedValue(sansSegments(etatEmission()));
    const page = await monter();

    await page.find('[data-test="valider"]').trigger('click');
    await flushPromises();

    expect(passagesService.retirerValidation).toHaveBeenCalledWith(EPISODE_ID);
  });

  it('supprime un Passage après confirmation, puis le restaure', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    passagesService.supprimer.mockResolvedValue(sansSegments(etatEmission({
      passages: [PASSAGE_A, PASSAGE_C], supprimes: [{ id: 'pb', titre: 'Paradisi Gloria' }],
      sans_passage: [LIVRE_A_PLACER, { ...LIVRE_A_PLACER, titre: 'Paradisi Gloria', raison: 'supprime' }],
    })));
    passagesService.restaurer.mockResolvedValue(sansSegments(etatEmission()));
    const page = await monter();

    await carte(page, PASSAGE_B).find('[title^="Supprimer"]').trigger('click');
    await flushPromises();

    expect(passagesService.supprimer).toHaveBeenCalledWith('pb');
    expect(carte(page, PASSAGE_B).exists()).toBe(false);
    // un livre supprimé se restaure, il n'est pas « À placer »
    expect(page.find('.a-placer').text()).not.toContain('Paradisi Gloria');

    await page.find('.manque button').trigger('click');
    await flushPromises();

    expect(passagesService.restaurer).toHaveBeenCalledWith('pb');
    expect(carte(page, PASSAGE_B).exists()).toBe(true);
  });

  it('dépose un livre « À placer » sur un trou de la frise, puis lui donne la première partie', async () => {
    const place = {
      ...PASSAGE_C, id: 'pm', titre: 'Vivre après', debut_ms: 240000, fin_ms: 540000,
      origine: 'corrige', place_main: true, livre_id: 'l-vivre',
    };
    passagesService.deposer.mockResolvedValue(sansSegments(etatEmission({
      passages: [PASSAGE_A, PASSAGE_B, place, PASSAGE_C], sans_passage: [],
    })));
    passagesService.occuper.mockResolvedValue(sansSegments(etatEmission({
      passages: [PASSAGE_A, PASSAGE_B, { ...place, fin_ms: 400000 }, PASSAGE_C], sans_passage: [],
    })));
    const page = await monter();

    await page.find('.puce').trigger('dragstart', { dataTransfer: { setData: vi.fn() } });
    await page.find('.frise .trou').trigger('drop');
    await flushPromises();

    expect(passagesService.deposer).toHaveBeenCalledWith(EPISODE_ID, 'Vivre après', 240000, 540000);
    expect(page.find('.a-placer').text()).toContain('Tous les livres sont placés');

    await page.findAll('.menu button').find((b) => b.text().includes('Première partie')).trigger('click');
    await flushPromises();

    expect(passagesService.occuper).toHaveBeenCalledWith('pm', 'tete');
  });

  it("dépose un livre sur une phrase d'un trou : il commence à cette phrase", async () => {
    passagesService.deposer.mockResolvedValue(sansSegments(etatEmission()));
    const page = await monter();

    await page.find('.puce').trigger('dragstart', { dataTransfer: { setData: vi.fn() } });
    await segment(page, 'Une lettre de Brest').trigger('drop');
    await flushPromises();

    expect(passagesService.deposer).toHaveBeenCalledWith(EPISODE_ID, 'Vivre après', 400000, 540000);
  });

  it('remet à placer un livre placé à la main', async () => {
    const place = { ...PASSAGE_C, id: 'pm', titre: 'Vivre après', debut_ms: 240000, fin_ms: 540000, origine: 'corrige', place_main: true };
    passagesService.getCorrectionEpisode.mockResolvedValue(etatEmission({
      passages: [PASSAGE_A, PASSAGE_B, place, PASSAGE_C], sans_passage: [],
    }));
    passagesService.remettre.mockResolvedValue(sansSegments(etatEmission()));
    const page = await monter();

    await page.find('[data-bloc="pm"]').trigger('click');
    await page.findAll('.menu button').find((b) => b.text().includes('Remettre à placer')).trigger('click');
    await flushPromises();

    expect(passagesService.remettre).toHaveBeenCalledWith('pm');
    expect(page.find('.a-placer').text()).toContain('Vivre après');
  });

  it("signale un Passage de moins de 30 s et un trou de plus de 2 min", async () => {
    const page = await monter();

    expect(carte(page, PASSAGE_C).find('.court').exists()).toBe(true);
    expect(carte(page, PASSAGE_A).find('.court').exists()).toBe(false);
    expect(page.find('.frise .trou').classes()).toContain('long');
    expect(page.find('.trou-entete').classes()).toContain('long');
  });

  it("dit dans le journal qu'une correction retire la validation", async () => {
    passagesService.getCorrectionEpisode.mockResolvedValue(etatEmission({ valide: true }));
    passagesService.deplacerFin.mockResolvedValue(sansSegments(etatEmission()));
    const page = await monter();

    await carte(page, PASSAGE_B).find('[title^="Placer la fin"]').trigger('click');
    await segment(page, 'Le courrier').trigger('click');
    await flushPromises();

    expect(page.find('.journal').text()).toContain('émission repassée en 🟠');
    expect(page.findAll('.dropdown-option').some((o) => o.text().startsWith('🟠'))).toBe(true);
  });

  it('garde la couleur de chaque Passage quand un autre est supprimé', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    passagesService.supprimer.mockResolvedValue(sansSegments(etatEmission({
      passages: [PASSAGE_A, PASSAGE_C], supprimes: [{ id: 'pb', titre: 'Paradisi Gloria' }],
    })));
    const page = await monter();
    const couleurC = carte(page, PASSAGE_C).attributes('style');

    await carte(page, PASSAGE_B).find('[title^="Supprimer"]').trigger('click');
    await flushPromises();

    expect(carte(page, PASSAGE_C).attributes('style')).toBe(couleurC);
  });

  it('marque « à valider » un titre pas encore validé, sans lien vers la fiche livre', async () => {
    const page = await monter();

    expect(carte(page, PASSAGE_C).find('.a-valider').exists()).toBe(true);
    expect(carte(page, PASSAGE_C).find('.lien-livre').exists()).toBe(false);
    expect(carte(page, PASSAGE_A).find('.lien-livre').exists()).toBe(true);
  });
});
