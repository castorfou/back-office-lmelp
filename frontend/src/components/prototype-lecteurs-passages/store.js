// PROTOTYPE JETABLE (#418) — lecteurs de Passage, jamais fusionné.
// Un seul <audio> pour toute l'appli : l'intégral servi derrière la clé
// d'écoute (?cle=), borné en JS de debut à fin, coupe nette (#417).
import { reactive } from 'vue';
import axios from 'axios';

export const VARIANTES = {
  A: 'Bouton dans la ligne',
  B: 'Lecteur en bas de page',
  C: 'Section Passages + frise',
};

export const etat = reactive({
  charge: false,
  donnees: null, // { base, base_publique, cle, emissions: [...] }
  passage: null, // Passage en cours (avec emission)
  liste: [], // Passages du contexte (suivant / enchaînement)
  modeFin: 'stop', // 'stop' | 'proposer' | 'enchainer'
  statut: 'arret', // arret | chargement | lecture | pause | fini | erreur
  position: 0, // secondes dans l'audio intégral
  erreur: null,
  suivant: null, // Passage proposé à la fin (mode « proposer »)
  panne: false, // simule une clé refusée
  journal: [],
});

const audio = new Audio();
audio.preload = 'none';
let raf = null;
let seekEnAttente = null;

function log(msg) {
  const t = new Date().toLocaleTimeString('fr-FR');
  etat.journal.unshift(`${t} ${msg}`);
  etat.journal.splice(30);
}

export async function charger() {
  if (etat.charge) return;
  const { data } = await axios.get('/api/prototype-lecteurs/tout');
  for (const e of data.emissions) {
    for (const p of e.passages) p.emission = e;
    for (const p of e.sans_passage) p.emission = e;
  }
  etat.donnees = data;
  etat.charge = true;
}

export function emissionParDate(date) {
  return etat.donnees?.emissions.find((e) => e.date === (date || '').slice(0, 10));
}

export function passagesDuLivre(livreId) {
  if (!etat.donnees) return [];
  return etat.donnees.emissions.flatMap((e) => e.passages.filter((p) => p.livre_id === livreId));
}

export function sansPassageDuLivre(livreId) {
  if (!etat.donnees) return [];
  return etat.donnees.emissions.flatMap((e) => e.sans_passage.filter((p) => p.livre_id === livreId));
}

/** Passage d'un livre dans une émission, ou { absent: raison } */
export function passageDe(livreId, date) {
  const e = emissionParDate(date);
  if (!e) return { absent: 'pas_de_segments' };
  const p = e.passages.find((x) => x.livre_id === livreId);
  if (p) return p;
  const s = e.sans_passage.find((x) => x.livre_id === livreId);
  return { absent: s ? s.raison : 'non_repere' };
}

function url(p) {
  const d = etat.donnees;
  const cle = etat.panne ? 'mauvaise-cle' : d.cle;
  return `${d.base}/audios/${p.emission.audio_rel_filename}?cle=${cle}`;
}

function boucle() {
  const p = etat.passage;
  if (!p) return;
  etat.position = audio.currentTime;
  if (etat.statut === 'lecture' && audio.currentTime >= p.fin) {
    audio.pause();
    etat.position = p.fin;
    finDePassage();
    return;
  }
  raf = requestAnimationFrame(boucle);
}

function finDePassage() {
  const i = etat.liste.indexOf(etat.passage);
  const suivant = i >= 0 ? etat.liste[i + 1] : null;
  log(`fin de « ${etat.passage.titre} » (${fmt(etat.passage.fin)})`);
  if (etat.modeFin === 'enchainer' && suivant) {
    jouer(suivant, { liste: etat.liste, modeFin: 'enchainer' });
    return;
  }
  etat.statut = 'fini';
  etat.suivant = etat.modeFin === 'proposer' ? suivant : null;
}

/** Lance un Passage, depuis son début ou depuis `depuis` (secondes intégral) */
export function jouer(p, { liste = [], modeFin = 'stop', depuis = null } = {}) {
  etat.erreur = null;
  etat.suivant = null;
  etat.liste = liste;
  etat.modeFin = modeFin;
  const cible = depuis ?? p.debut;
  const src = url(p);
  etat.passage = p;
  etat.position = cible;
  if (audio.src.endsWith(src) && audio.readyState >= 1) {
    audio.currentTime = cible;
  } else {
    etat.statut = 'chargement';
    seekEnAttente = cible;
    audio.src = src;
    audio.load();
  }
  audio.play().then(
    () => {
      etat.statut = 'lecture';
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(boucle);
    },
    () => {},
  );
  log(`▶ « ${p.titre} » ${p.emission.date} ${fmt(cible)}→${fmt(p.fin)}`);
}

audio.addEventListener('loadedmetadata', () => {
  if (seekEnAttente != null) {
    audio.currentTime = seekEnAttente;
    seekEnAttente = null;
  }
});
// Un <audio> ne dit pas pourquoi il échoue (403 et codec absent donnent le
// même code) : on redemande un octet pour connaître la réponse du serveur.
audio.addEventListener('error', async () => {
  etat.statut = 'erreur';
  const src = audio.currentSrc || audio.src;
  let message;
  try {
    const r = await fetch(src, { headers: { Range: 'bytes=0-0' } });
    if (r.status === 403) message = "Audio refusé : la clé d'écoute n'est plus valable";
    else if (r.ok) message = `Ce navigateur ne sait pas lire ce format audio (${src.split('?')[0].split('.').pop()})`;
    else message = `Audio indisponible (lmelp-streaming répond ${r.status})`;
  } catch {
    message = 'Audio injoignable : lmelp-streaming ne répond pas';
  }
  etat.erreur = message;
  log(`✖ ${message} [code média ${audio.error?.code}]`);
});

export function pause() {
  audio.pause();
  etat.statut = 'pause';
  cancelAnimationFrame(raf);
  log('⏸ pause');
}

export function reprendre() {
  const p = etat.passage;
  if (!p) return;
  if (etat.statut === 'fini') return jouer(p, { liste: etat.liste, modeFin: etat.modeFin });
  audio.play().then(() => {
    etat.statut = 'lecture';
    raf = requestAnimationFrame(boucle);
  });
}

export function basculer(p, opts) {
  if (etat.passage === p && etat.statut === 'lecture') return pause();
  if (etat.passage === p && etat.statut === 'pause') return reprendre();
  return jouer(p, opts);
}

/** Déplacement borné au Passage */
export function aller(t) {
  const p = etat.passage;
  if (!p) return;
  const borne = Math.min(Math.max(t, p.debut), p.fin - 0.05);
  audio.currentTime = borne;
  etat.position = borne;
  if (etat.statut === 'fini') {
    etat.statut = 'pause';
    etat.suivant = null;
  }
}

export function sauter(d) {
  aller(etat.position + d);
}

export function arreter() {
  audio.pause();
  cancelAnimationFrame(raf);
  if (etat.passage) log('■ arrêt');
  etat.passage = null;
  etat.statut = 'arret';
  etat.suivant = null;
}

export function signaler(motif) {
  const p = etat.passage;
  if (!p) return;
  log(`⚠️ signalement (stub) « ${p.titre} » : ${motif} à ${fmt(etat.position)}`);
}

export function enCours(p) {
  return etat.passage === p && etat.statut !== 'arret';
}

export function fmt(s) {
  if (s == null) return '–';
  const t = Math.max(0, Math.floor(s));
  const h = Math.floor(t / 3600);
  const m = Math.floor((t % 3600) / 60);
  const sec = String(t % 60).padStart(2, '0');
  return h ? `${h}:${String(m).padStart(2, '0')}:${sec}` : `${m}:${sec}`;
}

export function duree(p) {
  return fmt(p.fin - p.debut);
}

export const MOTIFS = [
  'coupé trop tôt au début',
  'coupé trop tôt à la fin',
  'déborde sur un autre livre',
  'mauvais livre',
  'autre',
];

export function segmentEnCours(p, t) {
  const segs = p?.emission?.segments || [];
  let lo = 0;
  let hi = segs.length - 1;
  let trouve = null;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    if (segs[mid][0] <= t) {
      trouve = segs[mid];
      lo = mid + 1;
    } else hi = mid - 1;
  }
  return trouve;
}

export function premieresPhrases(p, n = 2) {
  const segs = p?.emission?.segments || [];
  return segs
    .filter((s) => s[0] >= p.debut && s[0] < p.fin)
    .slice(0, n)
    .map((s) => s[2])
    .join(' ');
}

export const COULEURS = ['#4e79a7', '#f28e2b', '#59a14f', '#e15759', '#76b7b2', '#edc948', '#b07aa1', '#ff9da7', '#9c755f'];
