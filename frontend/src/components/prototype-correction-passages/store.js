// PROTOTYPE JETABLE — wayfinder « Interface de correction des Passages » (#398).
// État en mémoire, aucune écriture serveur. Règles reprises de
// « Déclenchement du repérage des Passages » (#395) :
// - une correction passe le Passage en `corrige` ;
// - corriger un début recale la fin du Passage `auto` précédent (début + 10 s) ;
// - supprimer = `supprime: true`, conservé ;
// - relancer : les `auto` sont recalculés (ici : remis aux valeurs du repérage),
//   `corrige` et `supprime` restent.
import { reactive, ref } from 'vue';
import temoin from './temoin-15-11-2026.json';

const RECOUVREMENT_S = 10;

const initial = () => JSON.parse(JSON.stringify(temoin.passages));

export const episode = temoin.episode;
export const segments = temoin.segments;
export const passages = reactive(initial());
export const livresSansPassage = reactive([...temoin.livres_sans_passage]);
export const journal = ref([]);

const log = (msg) => journal.value.unshift(`${new Date().toLocaleTimeString()} — ${msg}`);

export const fmt = (s) => {
  if (s == null || Number.isNaN(s)) return '—';
  const v = Math.max(0, Math.round(s));
  return `${String(Math.floor(v / 60)).padStart(2, '0')}:${String(v % 60).padStart(2, '0')}`;
};

export const parse = (txt) => {
  const m = String(txt).trim().match(/^(\d+):(\d{1,2})$/);
  if (m) return Number(m[1]) * 60 + Number(m[2]);
  const n = Number(txt);
  return Number.isFinite(n) ? Math.round(n) : null;
};

export const visibles = () =>
  passages.filter((p) => !p.supprime).sort((a, b) => a.debut - b.debut);

const precedent = (p) => {
  const v = visibles();
  const i = v.findIndex((x) => x.id === p.id);
  return i > 0 ? v[i - 1] : null;
};

const recaler = (p) => {
  const prev = precedent(p);
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
  const p = passages.find((x) => x.id === id);
  if (s == null || s < 0 || s >= p.fin) return log(`refusé : début ${fmt(s)} ≥ fin de « ${p.titre} »`);
  log(`début de « ${p.titre} » ${fmt(p.debut)} → ${fmt(s)} (relance du repérage)`);
  p.debut = s;
  marquer(p);
  recaler(p);
}

export function setFin(id, s) {
  const p = passages.find((x) => x.id === id);
  if (s == null || s <= p.debut) return log(`refusé : fin ${fmt(s)} ≤ début de « ${p.titre} »`);
  log(`fin de « ${p.titre} » ${fmt(p.fin)} → ${fmt(s)} (relance du repérage)`);
  p.fin = s;
  marquer(p);
}

export function supprimer(id) {
  const p = passages.find((x) => x.id === id);
  p.supprime = true;
  log(`« ${p.titre} » supprimé (conservé : une relance ne le recrée pas)`);
}

export function restaurer(id) {
  const p = passages.find((x) => x.id === id);
  p.supprime = false;
  log(`« ${p.titre} » restauré`);
}

// Question ouverte du prototype : placer à la main un livre sans Passage ?
// (#395 : jamais de Passage approximatif *automatique* ; un Passage manuel
// serait `corrige`.)
export function placer(livreOid, debut, fin) {
  const i = livresSansPassage.findIndex((l) => l.livre_oid === livreOid);
  const l = livresSansPassage[i];
  livresSansPassage.splice(i, 1);
  const p = { id: `m${Date.now()}`, livre_oid: l.livre_oid, titre: l.titre, auteur: l.auteur,
    debut, fin, origine: 'corrige', supprime: false, ecoute: null };
  passages.push(p);
  log(`« ${l.titre} » placé à la main ${fmt(debut)}–${fmt(fin)}`);
  recaler(p);
}

export function relancer() {
  const ref0 = initial();
  for (const p of passages) {
    if (p.origine !== 'auto') continue;
    const r = ref0.find((x) => x.id === p.id);
    if (r) { p.debut = r.debut; p.fin = r.fin; }
  }
  for (const p of passages.filter((x) => x.origine === 'corrige' && !x.supprime)) recaler(p);
  log('🔄 repérage relancé : Passages auto recalculés, corrections et suppressions conservées');
}

export function reinitialiser() {
  passages.splice(0, passages.length, ...initial());
  livresSansPassage.splice(0, livresSansPassage.length, ...temoin.livres_sans_passage);
  journal.value = [];
}

// --- Lecteur partagé : un seul <audio>, fichier choisi sur la machine ---
export const lecteur = reactive({ src: null, nom: null, t: 0, enLecture: false, arret: null });
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
  el.addEventListener('play', () => (lecteur.enLecture = true));
  el.addEventListener('pause', () => (lecteur.enLecture = false));
}

export function choisirFichier(file) {
  if (lecteur.src) URL.revokeObjectURL(lecteur.src);
  lecteur.src = URL.createObjectURL(file);
  lecteur.nom = file.name;
}

export function jouer(de, jusqua = null) {
  if (!audioEl || !lecteur.src) return log('choisir d\'abord le fichier audio de l\'épisode');
  audioEl.currentTime = Math.max(0, de);
  lecteur.arret = jusqua;
  audioEl.play();
}

export function pause() { audioEl?.pause(); }

export const position = () => Math.round(lecteur.t);
