// PROTOTYPE JETABLE — page « Correction des passages » (wayfinder #398).
// État en mémoire du navigateur (perdu au rechargement), aucune écriture serveur.
// Règles :
// - une correction passe le Passage en `corrige` ;
// - PAS DE RECOUVREMENT : deux Passages voisins partagent une seule frontière.
//   Déplacer le début d'un Passage déplace la fin du précédent, déplacer sa fin
//   déplace le début du suivant (les deux deviennent `corrige`). Remplace la règle
//   « fin = début du suivant + 10 s » du repérage (#391/#395) : la marge d'écoute,
//   si on la garde, sera ajoutée par le lecteur, pas stockée ;
// - supprimer = `supprime: true`, conservé ;
// Pas de bouton « Relancer le repérage » (décidé en #398 : un meilleur algorithme
// passera par une reprise des données, pas par un bouton par émission).
import { reactive } from 'vue';

// episode_id -> { passages, initial, livresSansPassage, segments, journal }
const parEpisode = {};
export const etat = reactive({ ep: null, valides: new Set(), choisi: null, glisse: null, retour: null });

// Retire le recouvrement du repérage : la fin d'un Passage s'arrête au début du suivant.
const sansRecouvrement = (liste) => {
  const v = liste.filter((p) => !p.supprime).sort((a, b) => a.debut - b.debut);
  v.forEach((p, k) => { if (k + 1 < v.length && p.fin > v[k + 1].debut) p.fin = v[k + 1].debut; });
  return liste;
};

export function charger(data) {
  if (!parEpisode[data.episode_id]) {
    parEpisode[data.episode_id] = reactive({
      id: data.episode_id,
      segments: data.segments,
      initial: sansRecouvrement(JSON.parse(JSON.stringify(data.passages))),
      passages: sansRecouvrement(JSON.parse(JSON.stringify(data.passages))),
      livresSansPassage: [...data.livres_sans_passage],
      simulation: data.simulation || null,
      // la liste « À placer » reste affichée pour une émission qui avait des livres à placer
      avaitAPlacer: data.livres_sans_passage.length > 0,
      journal: [],
    });
  }
  etat.ep = parEpisode[data.episode_id];
  etat.choisi = null;
}

const log = (msg) => etat.ep.journal.unshift(`${new Date().toLocaleTimeString()} — ${msg}`);

export const fmt = (s) => {
  if (s == null || Number.isNaN(s)) return '—';
  const v = Math.max(0, Math.floor(s)); // affichage tronqué ; les bornes gardent les centièmes du Segment
  return `${String(Math.floor(v / 60)).padStart(2, '0')}:${String(v % 60).padStart(2, '0')}`;
};

const PALETTE = ['#1e88e5', '#43a047', '#8e24aa', '#f4511e', '#00897b', '#6d4c41', '#c0ca33', '#d81b60', '#3949ab', '#fb8c00'];
export const couleur = (p) => {
  const i = etat.ep ? etat.ep.passages.indexOf(p) : 0;
  return PALETTE[(i < 0 ? 0 : i) % PALETTE.length];
};

export const visibles = () =>
  (etat.ep?.passages || []).filter((p) => !p.supprime).sort((a, b) => a.debut - b.debut);

const trouver = (id) => etat.ep.passages.find((x) => x.id === id);

const voisins = (p) => {
  const v = visibles();
  const i = v.findIndex((x) => x.id === p.id);
  return { prev: i > 0 ? v[i - 1] : null, next: i >= 0 && i + 1 < v.length ? v[i + 1] : null };
};

// Toute correction retire la validation de l'émission (#400 : elle repasse en 🟠).
const devalider = () => {
  if (etat.valides.has(etat.ep.id)) {
    etat.valides.delete(etat.ep.id);
    log('↳ émission repassée en 🟠 (correction après validation)');
  }
};

const marquer = (p) => {
  p.origine = 'corrige';
  p.corrige_le = new Date().toISOString();
  devalider();
};

export function setDebut(id, s) {
  const p = trouver(id);
  const { prev } = voisins(p);
  if (s == null || s < 0 || s >= p.fin) return log(`refusé : début ${fmt(s)} ≥ fin de « ${p.titre} »`);
  if (prev && s <= prev.debut) return log(`refusé : début ${fmt(s)} avant le début de « ${prev.titre} »`);
  log(`début de « ${p.titre} » ${fmt(p.debut)} → ${fmt(s)}`);
  // frontière partagée seulement si les deux Passages se touchaient (un trou entre eux reste un trou)
  const collait = prev && Math.abs(prev.fin - p.debut) < 0.01;
  p.debut = s;
  marquer(p);
  if (prev && prev.fin !== s && (collait || prev.fin > s)) {
    log(`↳ fin de « ${prev.titre} » suit : ${fmt(prev.fin)} → ${fmt(s)}`);
    prev.fin = s;
    marquer(prev);
  }
}

export function setFin(id, s) {
  const p = trouver(id);
  const { next } = voisins(p);
  if (s == null || s <= p.debut) return log(`refusé : fin ${fmt(s)} ≤ début de « ${p.titre} »`);
  if (next && s >= next.fin) return log(`refusé : fin ${fmt(s)} après la fin de « ${next.titre} »`);
  log(`fin de « ${p.titre} » ${fmt(p.fin)} → ${fmt(s)}`);
  const collait = next && Math.abs(next.debut - p.fin) < 0.01;
  p.fin = s;
  marquer(p);
  if (next && next.debut !== s && (collait || next.debut < s)) {
    log(`↳ début de « ${next.titre} » suit : ${fmt(next.debut)} → ${fmt(s)}`);
    next.debut = s;
    marquer(next);
  }
}

export function supprimer(id) {
  const p = trouver(id);
  p.supprime = true;
  log(`« ${p.titre} » supprimé (conservé : une relance ne le recrée pas)`);
}

export function restaurer(id) {
  const p = trouver(id);
  p.supprime = false;
  log(`« ${p.titre} » restauré`);
  sansRecouvrement(etat.ep.passages);
}

// Trous : zones entre deux Passages voisins qu'aucun Passage ne couvre (repérage qui a
// manqué un livre, ou Passage supprimé). Le début et la fin de l'émission n'en sont pas.
export const trous = () => {
  const v = visibles();
  const t = [];
  v.forEach((p, k) => {
    if (k + 1 < v.length && v[k + 1].debut - p.fin > 0.5) {
      t.push({ id: `trou-${p.id}`, debut: p.fin, fin: v[k + 1].debut });
    }
  });
  return t;
};

// Glisser-déposer un livre sans Passage (#401).
// - sur un trou, depuis la frise (t absent) : le livre prend tout le trou, en tête ;
// - sur un trou, depuis le texte (t = début de la phrase) : le livre commence à cette phrase,
//   ce qui précède reste un trou ;
// Puis un clic sur le livre placé : tout / première partie / dernière partie (occuper()).
const creer = (livre, debut, fin) => {
  const l = etat.ep.livresSansPassage;
  l.splice(l.indexOf(livre), 1);
  const p = { id: `m${Date.now()}`, titre: livre.titre, auteur: livre.auteur,
    debut, fin, origine: 'corrige', supprime: false, place_main: true };
  etat.ep.passages.push(p);
  etat.choisi = p.id;
  devalider();
  return p;
};

export function deposer(livre, trou, t = null) {
  if (!etat.ep.livresSansPassage.includes(livre)) return;
  const debut = t == null ? trou.debut : t;
  const p = creer(livre, debut, trou.fin);
  log(`« ${livre.titre} » déposé dans le trou ${fmt(trou.debut)}–${fmt(trou.fin)} : ${fmt(debut)}–${fmt(trou.fin)}`);
  return p;
}

// Milieu d'un trou, calé sur le début de la phrase la plus proche.
const milieu = (trou) => {
  const m = (trou.debut + trou.fin) / 2;
  let best = m;
  let ecart = Infinity;
  for (const x of etat.ep.segments) {
    if (x[0] > trou.debut + 0.01 && x[0] < trou.fin - 0.01 && Math.abs(x[0] - m) < ecart) {
      ecart = Math.abs(x[0] - m);
      best = x[0];
    }
  }
  return best;
};

// Espace libre autour d'un Passage placé à la main : de la fin du Passage précédent au début
// du suivant (lui-même et les trous qui le bordent).
const espaceLibre = (p) => {
  const autres = visibles().filter((x) => x.id !== p.id);
  const prev = autres.filter((x) => x.debut < p.debut).pop();
  const next = autres.find((x) => x.debut >= p.debut);
  return { debut: Math.min(prev ? prev.fin : p.debut, p.debut), fin: Math.max(next ? next.debut : p.fin, p.fin) };
};

// Deuxième clic sur un livre placé : 'tout' = tout l'espace libre ; 'tete' = coupé en deux,
// le livre en première partie ; 'fin' = coupé en deux, le livre en dernière partie.
export function occuper(p, mode) {
  const z = espaceLibre(p);
  const m = milieu(z);
  [p.debut, p.fin] = mode === 'tete' ? [z.debut, m] : mode === 'fin' ? [m, z.fin] : [z.debut, z.fin];
  const quoi = mode === 'tete' ? 'première partie' : mode === 'fin' ? 'dernière partie' : 'tout le trou';
  log(`« ${p.titre} » : ${quoi}, ${fmt(p.debut)}–${fmt(p.fin)}`);
  devalider();
}

// Reprendre un livre placé à la main et le remettre dans « À placer » (son trou réapparaît).
export function remettre(p) {
  if (!p.place_main) return;
  const ps = etat.ep.passages;
  ps.splice(ps.indexOf(p), 1);
  etat.ep.livresSansPassage.push({ titre: p.titre, auteur: p.auteur });
  if (etat.choisi === p.id) etat.choisi = null;
  log(`« ${p.titre} » remis à placer`);
  devalider();
}

export function basculerValidation() {
  const id = etat.ep.id;
  if (etat.valides.has(id)) { etat.valides.delete(id); log('validation retirée'); }
  else { etat.valides.add(id); log('✅ Passages validés'); }
}

// --- Lecteur : un seul <audio>, source fixée par la page ---
export const lecteur = reactive({ t: 0, duree: 0, enLecture: false, arret: null });
let audioEl = null;

export function brancherAudio(el) {
  audioEl = el;
  el.addEventListener('timeupdate', () => {
    lecteur.t = el.currentTime;
    if (lecteur.arret != null && el.currentTime >= lecteur.arret) {
      el.pause();
      lecteur.arret = null;
    }
  });
  el.addEventListener('loadedmetadata', () => (lecteur.duree = el.duration));
  el.addEventListener('play', () => (lecteur.enLecture = true));
  el.addEventListener('pause', () => (lecteur.enLecture = false));
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
