// PROTOTYPE JETABLE — page « Correction des passages » (wayfinder #398).
// État en mémoire du navigateur (perdu au rechargement), aucune écriture serveur.
// Règles de « Déclenchement du repérage des Passages » (#395) :
// - une correction passe le Passage en `corrige` ;
// - corriger un début recale la fin du Passage `auto` précédent (début + 10 s) ;
// - supprimer = `supprime: true`, conservé ;
// Pas de bouton « Relancer le repérage » (décidé en #398 : un meilleur algorithme
// passera par une reprise des données, pas par un bouton par émission).
import { reactive } from 'vue';

const RECOUVREMENT_S = 10;

// episode_id -> { passages, initial, livresSansPassage, segments, journal }
const parEpisode = {};
export const etat = reactive({ ep: null, valides: new Set() });

export function charger(data) {
  if (!parEpisode[data.episode_id]) {
    parEpisode[data.episode_id] = reactive({
      id: data.episode_id,
      segments: data.segments,
      initial: JSON.parse(JSON.stringify(data.passages)),
      passages: JSON.parse(JSON.stringify(data.passages)),
      livresSansPassage: [...data.livres_sans_passage],
      journal: [],
    });
  }
  etat.ep = parEpisode[data.episode_id];
}

const log = (msg) => etat.ep.journal.unshift(`${new Date().toLocaleTimeString()} — ${msg}`);

export const fmt = (s) => {
  if (s == null || Number.isNaN(s)) return '—';
  const v = Math.max(0, Math.round(s));
  return `${String(Math.floor(v / 60)).padStart(2, '0')}:${String(v % 60).padStart(2, '0')}`;
};

export const visibles = () =>
  (etat.ep?.passages || []).filter((p) => !p.supprime).sort((a, b) => a.debut - b.debut);

const trouver = (id) => etat.ep.passages.find((x) => x.id === id);

const recaler = (p) => {
  const v = visibles();
  const i = v.findIndex((x) => x.id === p.id);
  const prev = i > 0 ? v[i - 1] : null;
  if (prev && prev.origine === 'auto') {
    const ancien = prev.fin;
    prev.fin = p.debut + RECOUVREMENT_S;
    if (ancien !== prev.fin) log(`↳ fin de « ${prev.titre} » recalée ${fmt(ancien)} → ${fmt(prev.fin)}`);
  }
};

const marquer = (p) => {
  p.origine = 'corrige';
  p.corrige_le = new Date().toISOString();
};

export function setDebut(id, s) {
  const p = trouver(id);
  if (s == null || s < 0 || s >= p.fin) return log(`refusé : début ${fmt(s)} ≥ fin de « ${p.titre} »`);
  log(`début de « ${p.titre} » ${fmt(p.debut)} → ${fmt(s)}`);
  p.debut = s;
  marquer(p);
  recaler(p);
}

export function setFin(id, s) {
  const p = trouver(id);
  if (s == null || s <= p.debut) return log(`refusé : fin ${fmt(s)} ≤ début de « ${p.titre} »`);
  log(`fin de « ${p.titre} » ${fmt(p.fin)} → ${fmt(s)}`);
  p.fin = s;
  marquer(p);
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
}

// Question ouverte : placer à la main un livre sans Passage ?
export function placer(livre, debut, fin) {
  const l = etat.ep.livresSansPassage;
  l.splice(l.indexOf(livre), 1);
  const p = { id: `m${Date.now()}`, titre: livre.titre, auteur: livre.auteur,
    debut, fin, origine: 'corrige', supprime: false };
  etat.ep.passages.push(p);
  log(`« ${livre.titre} » placé à la main ${fmt(debut)}–${fmt(fin)}`);
  recaler(p);
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
