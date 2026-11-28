/**
 * Rond ▶ devant le titre d'un livre et lecteur fixé en bas de page
 * (Issue #427, variante B du prototype #418).
 */
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { mount } from '@vue/test-utils';
import { createRouter, createMemoryHistory } from 'vue-router';
import PassageBouton from '../PassageBouton.vue';
import PassageDock from '../PassageDock.vue';
import {
  lecteur, brancherAudio, arreter, jouer, verifierFin,
} from '../../services/lecteurPassages.js';

const FONDATEUR = {
  id: 'p1', titre: 'Le Fondateur', auteur: 'Giuliano da Empoli', livre_id: 'l1',
  debut_ms: 447000, fin_ms: 813000, episode_id: 'e1', date: '2026-11-15',
};
const PARADISI = {
  id: 'p2', titre: 'Paradisi Gloria', auteur: 'Philippe Vasset', livre_id: null,
  debut_ms: 813000, fin_ms: 1159000, episode_id: 'e1', date: '2026-11-15',
};

function fauxAudio() {
  return {
    src: '', currentTime: 0, readyState: 4,
    play: vi.fn(() => Promise.resolve()), pause: vi.fn(), load: vi.fn(),
    addEventListener: () => {},
  };
}

function monter(composant, props = {}) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: { template: '<div />' } },
      { path: '/livre/:id', component: { template: '<div />' } },
      { path: '/emissions/:date', component: { template: '<div />' } },
    ],
  });
  return mount(composant, { props, global: { plugins: [router] } });
}

let audio;
beforeEach(() => {
  audio = fauxAudio();
  brancherAudio(audio);
  arreter();
});

describe('PassageBouton', () => {
  it("lit le Passage du livre d'un clic", async () => {
    const bouton = monter(PassageBouton, { passage: FONDATEUR, liste: [FONDATEUR, PARADISI] });

    await bouton.find('button').trigger('click');

    expect(lecteur.passage).toEqual(FONDATEUR);
    expect(audio.src).toContain('/api/episodes/e1/audio');
  });

  it('montre la pause pendant la lecture de son Passage', async () => {
    const bouton = monter(PassageBouton, { passage: FONDATEUR, liste: [] });

    await jouer(FONDATEUR, []);
    await bouton.vm.$nextTick();

    expect(bouton.find('button').attributes('aria-label')).toBe('Pause');
  });

  it("dit pourquoi un livre n'a pas de Passage", () => {
    const bouton = monter(PassageBouton, { passage: null, raison: 'pas_de_segments' });

    expect(bouton.find('button').exists()).toBe(false);
    expect(bouton.find('.passage-absent').attributes('title')).toMatch(
      /pas de transcription horodatée/,
    );
  });
});

describe('PassageDock', () => {
  it("n'apparaît pas sans Passage en cours", () => {
    expect(monter(PassageDock).find('.passage-dock').exists()).toBe(false);
  });

  it("montre le livre, son auteur et l'émission du Passage en cours", async () => {
    const dock = monter(PassageDock);

    await jouer(FONDATEUR, []);
    await dock.vm.$nextTick();

    expect(dock.text()).toContain('Le Fondateur');
    expect(dock.text()).toContain('Giuliano da Empoli');
    expect(dock.find('a[href="/livre/l1"]').exists()).toBe(true);
    expect(dock.find('a[href="/emissions/20261115"]').exists()).toBe(true);
  });

  it('propose le Passage suivant à la fin, et le lit', async () => {
    const dock = monter(PassageDock);
    await jouer(FONDATEUR, [FONDATEUR, PARADISI]);
    audio.currentTime = 814;
    verifierFin();
    await dock.vm.$nextTick();

    expect(dock.text()).toContain('Fin du passage');
    const suivant = dock.findAll('button').find((b) => b.text().includes('Paradisi Gloria'));
    await suivant.trigger('click');

    expect(lecteur.passage).toEqual(PARADISI);
  });

  it('se ferme et arrête la lecture', async () => {
    const dock = monter(PassageDock);
    await jouer(FONDATEUR, []);
    await dock.vm.$nextTick();

    await dock.find('[aria-label="Fermer le lecteur"]').trigger('click');

    expect(lecteur.passage).toBeNull();
    expect(dock.find('.passage-dock').exists()).toBe(false);
  });
});
