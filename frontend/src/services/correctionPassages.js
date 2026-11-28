/**
 * Page « Correction des passages » : état de l'émission ouverte, corrections
 * et lecteur de page (Issue #427, prototype validé dans #398, #400, #401).
 *
 * Le serveur fait foi : chaque correction part à l'API, qui applique les règles
 * (frontière partagée, bornes à l'heure d'un Segment, dépôt dans un trou) et
 * renvoie l'état de l'émission, que la page affiche tel quel. Une correction
 * refusée laisse l'état inchangé et sa raison va au journal.
 *
 * Les heures sont en secondes dans la page (comme dans le prototype) et en
 * millisecondes à l'API ; une borne garde l'heure exacte de son Segment.
 */
import { reactive } from 'vue';
import { passagesService } from './api.js';

export const etat = reactive({
  ep: null, // { id, segments, passages, supprimes, livresSansPassage, avaitAPlacer, valide, journal }
  statuts: {}, // episode_id -> 'valide' | 'a_verifier'
  choisi: null, // id du Passage mis en avant
  glisse: null, // livre « À placer » en cours de glisser
  retour: null, // livre placé à la main glissé vers « À placer »
});

export const PASSAGE_COURT_S = 30;
export const TROU_LONG_S = 120;

const enSecondes = (ms) => ms / 1000;
const enMs = (s) => Math.round(s * 1000);

const versPage = (p) => ({ ...p, debut: enSecondes(p.debut_ms), fin: enSecondes(p.fin_ms) });

/** Applique un état renvoyé par l'API ; les Segments ne changent pas. */
function appliquer(data) {
  const ep = etat.ep;
  ep.passages = data.passages.map(versPage);
  ep.supprimes = data.supprimes;
  // un livre dont le Passage est supprimé se restaure : il n'est pas « À placer »
  ep.livresSansPassage = data.sans_passage.filter((l) => l.raison === 'non_repere');
  ep.valide = data.valide;
  etat.statuts[ep.id] = data.valide ? 'valide' : 'a_verifier';
  // une couleur par Passage, gardée tant que la page reste sur l'émission
  for (const p of ep.passages) {
    if (!(p.id in ep.couleurs)) ep.couleurs[p.id] = Object.keys(ep.couleurs).length;
  }
}

export function charger(episodeId, data) {
  etat.ep = reactive({
    id: episodeId,
    segments: data.segments.map(([debut, fin, texte]) => [enSecondes(debut), enSecondes(fin), texte]),
    passages: [],
    supprimes: [],
    livresSansPassage: [],
    valide: false,
    avaitAPlacer: false,
    couleurs: {},
    journal: [],
  });
  appliquer(data);
  // la liste « À placer » reste affichée pour une émission qui avait des livres à placer
  etat.ep.avaitAPlacer = etat.ep.livresSansPassage.length > 0;
  etat.choisi = null;
}

/** Relit l'état de l'émission ouverte (sans Segments), par exemple après une validation de livre. */
export function actualiser(episodeId, data) {
  if (etat.ep?.id === episodeId) appliquer(data);
}

export function fermer() {
  etat.ep = null;
  etat.choisi = null;
  etat.glisse = null;
  etat.retour = null;
}

const log = (msg) => etat.ep.journal.unshift(`${new Date().toLocaleTimeString()} — ${msg}`);

export const fmt = (s) => {
  if (s == null || Number.isNaN(s)) return '—';
  const v = Math.max(0, Math.floor(s)); // affichage tronqué ; les bornes gardent les centièmes du Segment
  return `${String(Math.floor(v / 60)).padStart(2, '0')}:${String(v % 60).padStart(2, '0')}`;
};

const PALETTE = ['#1e88e5', '#43a047', '#8e24aa', '#f4511e', '#00897b', '#6d4c41', '#c0ca33', '#d81b60', '#3949ab', '#fb8c00'];
export const couleur = (p) => {
  const i = etat.ep?.couleurs[p.id] ?? 0;
  return PALETTE[i % PALETTE.length];
};

export const visibles = () => [...(etat.ep?.passages || [])].sort((a, b) => a.debut - b.debut);

export const estCourt = (p) => p.fin - p.debut < PASSAGE_COURT_S;

// Trous : zones entre deux Passages voisins qu'aucun Passage ne couvre (repérage qui a
// manqué un livre, ou Passage supprimé). Le début et la fin de l'émission n'en sont pas.
export const trous = () => {
  const v = visibles();
  const t = [];
  v.forEach((p, k) => {
    if (k + 1 < v.length && v[k + 1].debut - p.fin > 0.5) {
      const fin = v[k + 1].debut;
      t.push({ id: `trou-${p.id}`, debut: p.fin, fin, long: fin - p.fin > TROU_LONG_S });
    }
  });
  return t;
};

/**
 * Journalise les bornes qu'une correction a déplacées : celles du Passage corrigé
 * d'abord, puis celles des voisins qui ont suivi (« ↳ »).
 */
function journaliser(avant, corrigeId) {
  const apres = Object.fromEntries(etat.ep.passages.map((p) => [p.id, p]));
  const ordre = [...avant].sort((a, b) => (b.id === corrigeId) - (a.id === corrigeId));
  for (const p of ordre) {
    const q = apres[p.id];
    if (!q) continue;
    const suit = corrigeId && p.id !== corrigeId ? '↳ ' : '';
    const verbe = suit ? ' suit' : '';
    if (q.debut !== p.debut) log(`${suit}début de « ${p.titre} »${verbe} : ${fmt(p.debut)} → ${fmt(q.debut)}`);
    if (q.fin !== p.fin) log(`${suit}fin de « ${p.titre} »${verbe} : ${fmt(p.fin)} → ${fmt(q.fin)}`);
  }
}

async function corriger(action, description, corrigeId = null) {
  const ep = etat.ep;
  const avant = ep.passages.map((p) => ({ ...p }));
  const etaitValide = ep.valide;
  try {
    const data = await action();
    if (etat.ep !== ep) return null; // une autre émission a été ouverte entre-temps
    appliquer(data);
    if (description) log(description);
    journaliser(avant, corrigeId);
    if (etaitValide && !ep.valide && description !== VALIDATION_RETIREE) {
      log('↳ émission repassée en 🟠 (correction après validation)');
    }
    return data;
  } catch (e) {
    if (etat.ep === ep) log(`refusé : ${e.message}`);
    return null;
  }
}

const VALIDATION_RETIREE = 'validation retirée';

const trouver = (id) => etat.ep.passages.find((x) => x.id === id);

export function setDebut(id, s) {
  return corriger(() => passagesService.deplacerDebut(id, enMs(s)), null, id);
}

export function setFin(id, s) {
  return corriger(() => passagesService.deplacerFin(id, enMs(s)), null, id);
}

export function supprimer(id) {
  const p = trouver(id);
  if (!p) return null;
  return corriger(
    () => passagesService.supprimer(id),
    `« ${p.titre} » supprimé (conservé : une relance ne le recrée pas)`,
  );
}

export function restaurer(id) {
  const p = etat.ep.supprimes.find((x) => x.id === id);
  return corriger(() => passagesService.restaurer(id), `« ${p?.titre} » restauré`);
}

// Glisser-déposer un livre sans Passage :
// - sur un trou, depuis la frise (t absent) : le livre prend tout le trou ;
// - sur un trou, depuis le texte (t = début de la phrase) : le livre commence à cette phrase,
//   ce qui précède reste un trou.
// Puis un clic sur le livre placé : tout / première partie / dernière partie (occuper()).
export async function deposer(livre, trou, t = null) {
  if (!etat.ep.livresSansPassage.includes(livre)) return null;
  const debut = t == null ? trou.debut : t;
  const data = await corriger(
    () => passagesService.deposer(etat.ep.id, livre.titre, enMs(debut), enMs(trou.fin)),
    `« ${livre.titre} » déposé dans le trou ${fmt(trou.debut)}–${fmt(trou.fin)} : ${fmt(debut)}–${fmt(trou.fin)}`,
  );
  if (!data) return null;
  const p = etat.ep.passages.find((x) => x.place_main && x.titre === livre.titre) || null;
  if (p) etat.choisi = p.id;
  return p;
}

// Un livre placé à la main : 'tout' = tout l'espace libre autour de lui ; 'tete' = coupé en
// deux, le livre en première partie ; 'fin' = coupé en deux, le livre en dernière partie.
export function occuper(p, mode) {
  const quoi = mode === 'tete' ? 'première partie' : mode === 'fin' ? 'dernière partie' : 'tout le trou';
  return corriger(() => passagesService.occuper(p.id, mode), `« ${p.titre} » : ${quoi}`, p.id);
}

// Reprendre un livre placé à la main et le remettre dans « À placer » (son trou réapparaît).
export function remettre(p) {
  if (!p.place_main) return null;
  if (etat.choisi === p.id) etat.choisi = null;
  return corriger(() => passagesService.remettre(p.id), `« ${p.titre} » remis à placer`);
}

export function basculerValidation() {
  const id = etat.ep.id;
  return etat.ep.valide
    ? corriger(() => passagesService.retirerValidation(id), VALIDATION_RETIREE)
    : corriger(() => passagesService.valider(id), '✅ Passages validés');
}

// --- Lecteur de page : un <audio> propre à la page, source fixée par la page ---
export const lecteur = reactive({ t: 0, duree: 0, enLecture: false, arret: null });
let audioEl = null;
let ecouteurs = {};

export function debrancherAudio() {
  if (audioEl) {
    audioEl.pause();
    for (const [evenement, ecouteur] of Object.entries(ecouteurs)) {
      audioEl.removeEventListener(evenement, ecouteur);
    }
  }
  audioEl = null;
  ecouteurs = {};
  Object.assign(lecteur, { t: 0, duree: 0, enLecture: false, arret: null });
}

export function brancherAudio(el) {
  if (audioEl === el) return;
  debrancherAudio();
  audioEl = el;
  ecouteurs = {
    timeupdate: () => {
      lecteur.t = el.currentTime;
      if (lecteur.arret != null && el.currentTime >= lecteur.arret) {
        el.pause();
        lecteur.arret = null;
      }
    },
    loadedmetadata: () => (lecteur.duree = el.duration),
    play: () => (lecteur.enLecture = true),
    pause: () => (lecteur.enLecture = false),
  };
  for (const [evenement, ecouteur] of Object.entries(ecouteurs)) {
    el.addEventListener(evenement, ecouteur);
  }
}

export function jouer(de, jusqua = null) {
  if (!audioEl) return;
  audioEl.currentTime = Math.max(0, de);
  lecteur.arret = jusqua;
  audioEl.play();
}

export function basculerLecture() {
  if (!audioEl) return;
  if (audioEl.paused) { lecteur.arret = null; audioEl.play(); } else audioEl.pause();
}

export function avancer(d) { if (audioEl) audioEl.currentTime = Math.max(0, audioEl.currentTime + d); }
