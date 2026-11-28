/**
 * Lecteur de Passages (Issue #427) : un seul <audio> pour toute l'application,
 * qui lit l'audio de l'émission depuis le backend et s'arrête net à la fin
 * du Passage.
 *
 * Un faux élément audio remplace le vrai (jsdom ne sait pas lire) : il garde
 * src, currentTime, et déclenche ses événements à la demande.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  lecteur,
  brancherAudio,
  jouer,
  basculer,
  pause,
  reprendre,
  aller,
  sauter,
  arreter,
  enCours,
  verifierFin,
} from '../lecteurPassages.js';

function fauxAudio() {
  const ecouteurs = {};
  return {
    src: '',
    currentTime: 0,
    readyState: 4,
    play: vi.fn(() => Promise.resolve()),
    pause: vi.fn(),
    load: vi.fn(),
    addEventListener: (nom, fn) => { ecouteurs[nom] = fn; },
    declencher: (nom) => ecouteurs[nom]?.(),
  };
}

const FONDATEUR = {
  id: 'p1', titre: 'Le Fondateur', auteur: 'Giuliano da Empoli', livre_id: 'l1',
  debut_ms: 447000, fin_ms: 813000, episode_id: 'e1', date: '2026-11-15',
};
const PARADISI = {
  id: 'p2', titre: 'Paradisi Gloria', auteur: 'Philippe Vasset', livre_id: 'l2',
  debut_ms: 813000, fin_ms: 1159000, episode_id: 'e1', date: '2026-11-15',
};

describe('lecteur de Passages', () => {
  let audio;

  beforeEach(() => {
    audio = fauxAudio();
    brancherAudio(audio);
    arreter();
    lecteur.erreur = null;
  });

  it("lit l'audio de l'émission à partir du début du Passage", async () => {
    await jouer(FONDATEUR, [FONDATEUR, PARADISI]);
    audio.declencher('loadedmetadata');

    expect(audio.src).toContain('/api/episodes/e1/audio');
    expect(audio.currentTime).toBe(447);
    expect(lecteur.passage).toEqual(FONDATEUR);
    expect(lecteur.statut).toBe('lecture');
  });

  it("s'arrête net à la fin du Passage et propose le suivant", async () => {
    await jouer(FONDATEUR, [FONDATEUR, PARADISI]);

    audio.currentTime = 813.2;

    verifierFin();

    expect(audio.pause).toHaveBeenCalled();
    expect(lecteur.statut).toBe('fini');
    expect(lecteur.suivant).toEqual(PARADISI);
  });

  it('ne propose pas de suivant après le dernier Passage', async () => {
    await jouer(PARADISI, [FONDATEUR, PARADISI]);

    audio.currentTime = 1160;

    verifierFin();

    expect(lecteur.statut).toBe('fini');
    expect(lecteur.suivant).toBeNull();
  });

  it('reste dans les bornes du Passage quand on se déplace', async () => {
    await jouer(FONDATEUR, []);


    aller(10);
    expect(audio.currentTime).toBe(447);
    sauter(10_000);
    expect(audio.currentTime).toBeLessThan(813);
  });

  it('met en pause puis reprend le même Passage', async () => {
    await jouer(FONDATEUR, []);


    basculer(FONDATEUR, []);
    expect(lecteur.statut).toBe('pause');
    expect(enCours(FONDATEUR)).toBe(true);

    await reprendre();
    expect(lecteur.statut).toBe('lecture');
  });

  it('rejoue le Passage depuis son début une fois fini', async () => {
    await jouer(FONDATEUR, []);

    audio.currentTime = 814;
    verifierFin();

    reprendre();

    expect(audio.currentTime).toBe(447);
  });

  it("dit pourquoi l'audio ne se lit pas : fichier absent", async () => {
    globalThis.fetch = vi.fn(() => Promise.resolve({ ok: false, status: 404 }));
    // un vrai play() échoue quand le fichier ne se charge pas
    audio.play = vi.fn(() => Promise.reject(new Error('NotSupportedError')));
    jouer(FONDATEUR, []);

    audio.declencher('error');
    await vi.waitFor(() => expect(lecteur.erreur).not.toBeNull());

    expect(lecteur.statut).toBe('erreur');
    expect(lecteur.erreur).toMatch(/absent/);
  });

  it("arrête la lecture et oublie le Passage", async () => {
    await jouer(FONDATEUR, []);


    arreter();

    expect(audio.pause).toHaveBeenCalled();
    expect(lecteur.passage).toBeNull();
    expect(enCours(FONDATEUR)).toBe(false);
  });
});
