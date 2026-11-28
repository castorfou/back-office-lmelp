/**
 * Livres-auteurs : écouter les Passages de l'émission choisie (Issue #427,
 * prototype #423 variante C), avec le store de « Correction des passages ».
 *
 * Une ligne du tableau retrouve son Passage par son livre (`book_id` =
 * `livre_id`), sinon par son titre : un livre pas encore validé n'a que le
 * titre du résumé.
 */
import { reactive } from 'vue';
import { passagesService } from './api.js';
import * as cp from './correctionPassages.js';
import { arreter as arreterLecteurGlobal } from './lecteurPassages.js';
import { removeAccents } from '../utils/textUtils.js';

export const ecoute = reactive({
  episodeId: null,
  pret: false, // Passages et Segments de l'émission chargés
  ligne: null, // clé de la ligne dont on écoute le Passage
  cible: null, // { book, n } : demande à la section de cibler un livre
});

const norm = (titre) => removeAccents(titre || '').toLowerCase().trim();

export const cleDe = (book) => book.book_id || `titre:${norm(book.titre)}`;

export async function chargerEpisode(episodeId) {
  ecoute.episodeId = episodeId;
  ecoute.pret = false;
  ecoute.ligne = null;
  ecoute.cible = null;
  cp.debrancherAudio();
  cp.fermer();
  if (!episodeId) return;
  let data;
  try {
    data = await passagesService.getCorrectionEpisode(episodeId);
  } catch (e) {
    console.warn('Passages non chargés :', e.message);
    return;
  }
  if (ecoute.episodeId !== episodeId || !data.a_des_segments) return;
  cp.charger(episodeId, data);
  ecoute.pret = true;
}

/** Relit les Passages (sans Segments) : un livre validé retrouve son Passage. */
export async function rafraichir() {
  const episodeId = ecoute.episodeId;
  if (!ecoute.pret) return;
  try {
    cp.actualiser(episodeId, await passagesService.getPassagesEpisode(episodeId));
  } catch (e) {
    console.warn('Passages non relus :', e.message);
  }
}

export function quitter() {
  cp.debrancherAudio();
  cp.fermer();
  Object.assign(ecoute, { episodeId: null, pret: false, ligne: null, cible: null });
}

/**
 * Le Passage de chaque ligne, par clé de ligne, calculé une fois pour tout le
 * tableau. Un livre se retrouve par son id ; à défaut, son titre ne retrouve
 * qu'un Passage sans livre (titre pas encore validé).
 */
export function passagesDesLignes(books) {
  const lignes = new Map();
  if (!ecoute.pret) return lignes;
  const parLivre = new Map();
  const parTitre = new Map();
  for (const p of cp.etat.ep.passages) {
    if (p.livre_id) parLivre.set(p.livre_id, p);
    else parTitre.set(norm(p.titre), p);
  }
  for (const book of books) {
    const p = (book.book_id && parLivre.get(book.book_id)) || parTitre.get(norm(book.titre));
    if (p) lignes.set(cleDe(book), p);
  }
  return lignes;
}

export function passageDe(book) {
  return passagesDesLignes([book]).get(cleDe(book)) || null;
}

/** Id du Passage en cours de lecture ; ne change qu'en passant d'un Passage à l'autre. */
export function passageEnLecture() {
  if (!ecoute.pret || !cp.lecteur.enLecture) return null;
  const t = cp.lecteur.t;
  return cp.etat.ep.passages.find((p) => t >= p.debut && t < p.fin)?.id || null;
}

export function enLecture(book) {
  const p = passageDe(book);
  return !!p && passageEnLecture() === p.id;
}

/** Au moins un Passage : le tableau suit alors l'ordre de l'émission. */
export const aDesPassages = () => ecoute.pret && cp.etat.ep.passages.length > 0;

/** Clic sur ▶ / ○ d'une ligne. */
export function ecouterLigne(book) {
  if (enLecture(book)) {
    cp.basculerLecture();
    return;
  }
  // un seul audio à la fois : le lecteur de l'application s'arrête
  if (passageDe(book)) arreterLecteurGlobal();
  ecoute.ligne = cleDe(book);
  ecoute.cible = { book, n: (ecoute.cible?.n || 0) + 1 };
}
