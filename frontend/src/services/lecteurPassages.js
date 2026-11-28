/**
 * Lecteur de Passages (Issue #427).
 *
 * Un seul <audio> pour toute l'application : il lit l'audio de l'émission
 * depuis le backend lmelp (GET /api/episodes/{id}/audio, en réseau local,
 * sans clé) et borne le Passage en JavaScript, de `debut_ms` à `fin_ms`,
 * sans marge : la lecture s'arrête net à la fin.
 *
 * Un Passage : { id, titre, auteur, livre_id, debut_ms, fin_ms, episode_id, date }.
 * `liste` est le contexte de lecture (Passages de l'émission ou du livre),
 * dans l'ordre : à la fin d'un Passage, le suivant est proposé.
 */
import { reactive } from 'vue';

export const lecteur = reactive({
  passage: null,
  liste: [],
  statut: 'arret', // arret | chargement | lecture | pause | fini | erreur
  position: 0, // secondes dans l'audio de l'émission
  erreur: null,
  suivant: null,
});

let audio = null;
let positionEnAttente = null;
let boucle = null;

const planifier = (fn) =>
  (globalThis.requestAnimationFrame ? globalThis.requestAnimationFrame(fn) : setTimeout(fn, 100));
const annuler = (id) =>
  (globalThis.cancelAnimationFrame ? globalThis.cancelAnimationFrame(id) : clearTimeout(id));

/** Début et fin d'un Passage, en secondes dans l'audio de l'émission. */
export const debutSecondes = (p) => p.debut_ms / 1000;
export const finSecondes = (p) => p.fin_ms / 1000;
export const dureeSecondes = (p) => finSecondes(p) - debutSecondes(p);
const debutS = debutSecondes;
const finS = finSecondes;
const urlAudio = (p) => `/api/episodes/${p.episode_id}/audio`;

/** Branche l'élément audio (un vrai <audio>, ou un faux dans les tests). */
export function brancherAudio(element) {
  audio = element;
  audio.preload = 'none';
  audio.addEventListener('loadedmetadata', () => {
    if (positionEnAttente != null) {
      audio.currentTime = positionEnAttente;
      positionEnAttente = null;
    }
  });
  audio.addEventListener('error', diagnostiquer);
  // requestAnimationFrame est suspendu dans un onglet en arrière-plan :
  // timeupdate (environ 4 fois par seconde) arrête quand même à la fin
  audio.addEventListener('timeupdate', verifierFin);
}

function element() {
  if (!audio) brancherAudio(new Audio());
  return audio;
}

/**
 * Un <audio> ne dit pas pourquoi il échoue (fichier absent et format non lu
 * donnent la même erreur) : on redemande un octet au backend.
 */
async function diagnostiquer() {
  if (!lecteur.passage) return;
  lecteur.statut = 'erreur';
  let message;
  try {
    const reponse = await fetch(urlAudio(lecteur.passage), { headers: { Range: 'bytes=0-0' } });
    if (reponse.status === 404) message = "Fichier audio de l'émission absent";
    else if (reponse.ok) message = 'Ce navigateur ne sait pas lire ce format audio';
    else message = `Audio indisponible (lmelp répond ${reponse.status})`;
  } catch {
    message = 'Audio injoignable : lmelp ne répond pas';
  }
  lecteur.erreur = message;
}

/** Arrête la lecture à la fin du Passage et propose le suivant. */
export function verifierFin() {
  const p = lecteur.passage;
  if (!p || !audio) return;
  lecteur.position = audio.currentTime;
  if (lecteur.statut === 'lecture' && audio.currentTime >= finS(p)) {
    audio.pause();
    annuler(boucle);
    lecteur.position = finS(p);
    lecteur.statut = 'fini';
    const index = lecteur.liste.findIndex((x) => x.id === p.id);
    lecteur.suivant = index >= 0 ? lecteur.liste[index + 1] || null : null;
  }
}

function suivre() {
  verifierFin();
  if (lecteur.statut === 'lecture') boucle = planifier(suivre);
}

function lancer() {
  return Promise.resolve(element().play()).then(
    () => {
      if (lecteur.statut === 'erreur') return;
      lecteur.statut = 'lecture';
      annuler(boucle);
      boucle = planifier(suivre);
    },
    () => {}, // une erreur de chargement passe par l'événement « error »
  );
}

/** Lit un Passage depuis son début ; `liste` sert à proposer le suivant. */
export function jouer(passage, liste = []) {
  const audioEl = element();
  lecteur.erreur = null;
  lecteur.suivant = null;
  lecteur.liste = liste;
  lecteur.passage = passage;
  lecteur.position = debutS(passage);
  if (audioEl.src && audioEl.src.endsWith(urlAudio(passage)) && audioEl.readyState >= 1) {
    audioEl.currentTime = debutS(passage);
  } else {
    lecteur.statut = 'chargement';
    positionEnAttente = debutS(passage);
    audioEl.src = urlAudio(passage);
    audioEl.load();
  }
  return lancer();
}

export function pause() {
  if (!audio) return;
  audio.pause();
  annuler(boucle);
  lecteur.statut = 'pause';
}

export function reprendre() {
  const p = lecteur.passage;
  if (!p) return undefined;
  if (lecteur.statut === 'fini') return jouer(p, lecteur.liste);
  return lancer();
}

/** Lecture ou pause du Passage, ou lecture d'un autre Passage. */
export function basculer(passage, liste = []) {
  if (enCours(passage) && lecteur.statut === 'lecture') return pause();
  if (enCours(passage) && lecteur.statut === 'pause') return reprendre();
  return jouer(passage, liste);
}

/** Se place à `secondes` dans l'audio, sans sortir du Passage. */
export function aller(secondes) {
  const p = lecteur.passage;
  if (!p || !audio) return;
  const borne = Math.min(Math.max(secondes, debutS(p)), finS(p) - 0.05);
  audio.currentTime = borne;
  lecteur.position = borne;
  if (lecteur.statut === 'fini') {
    lecteur.statut = 'pause';
    lecteur.suivant = null;
  }
}

export function sauter(secondes) {
  aller(lecteur.position + secondes);
}

export function arreter() {
  if (audio) audio.pause();
  annuler(boucle);
  lecteur.passage = null;
  lecteur.statut = 'arret';
  lecteur.suivant = null;
  lecteur.erreur = null;
}

export function enCours(passage) {
  return !!passage && lecteur.passage?.id === passage.id && lecteur.statut !== 'arret';
}

/** 447.8 → « 7:27 », 3725 → « 1:02:05 ». */
export function formaterDuree(secondes) {
  const t = Math.max(0, Math.floor(secondes || 0));
  const h = Math.floor(t / 3600);
  const m = Math.floor((t % 3600) / 60);
  const s = String(t % 60).padStart(2, '0');
  return h ? `${h}:${String(m).padStart(2, '0')}:${s}` : `${m}:${s}`;
}
