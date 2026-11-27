// PROTOTYPE JETABLE (#423) — écouter le Passage d'un livre pas encore validé
// depuis livres-auteurs, avec la transcription de « Correction des passages ».
// Jamais fusionné. Rien n'est écrit : validations simulées en mémoire.
import { reactive } from 'vue';
import axios from 'axios';
import * as cp from '../prototype-correction-passages/store.js';

export const VARIANTES_LA = {
  A: 'Panneau à droite',
  B: 'Sous la ligne',
  C: 'Section au-dessus du tableau',
};

// Émissions dont les Passages repérés sont dans la fixture du prototype
export const TEMOINS = ['2024-07-21', '2026-11-15', '2026-10-04'];

// Lignes affichées comme « pas encore validées » (en base locale, tout est déjà 🟢)
export const SIMULE_A_VALIDER = {
  '2024-07-21': {
    'quiche ta': { statut: 'not_found', texte: '🔴 Non trouvé sur Babelio' },
  },
  '2026-11-15': {
    'rouge truite': { statut: 'suggested', texte: '🟠 Suggestion Babelio : « Rouges-truites »', suggestion: 'Rouges-truites' },
    'vivre apres': { statut: 'not_found', texte: '🔴 Non trouvé sur Babelio' },
  },
};

export const ecoute = reactive({
  date: null,
  episodeId: null,
  pret: false, // Passages et Segments de l'émission chargés
  ouvert: false, // panneau ou ligne dépliée (variantes A et B)
  ligne: null, // titre normalisé de la ligne dont on écoute le Passage
  cible: null, // { titre, n } : demande au panneau de cibler un livre
  valides: {}, // titre normalisé -> titre validé (simulé)
  journal: [],
});

export const norm = (t) =>
  (t || '')
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/[’']/g, "'")
    .toLowerCase()
    .trim();

export function log(msg) {
  ecoute.journal.unshift(`${new Date().toLocaleTimeString('fr-FR')} ${msg}`);
  ecoute.journal.splice(30);
}

export async function chargerEpisode(episodeId, date) {
  ecoute.date = (date || '').slice(0, 10);
  ecoute.episodeId = episodeId;
  ecoute.pret = false;
  ecoute.ouvert = false;
  ecoute.ligne = null;
  cp.etat.ep = null;
  if (!TEMOINS.includes(ecoute.date)) return;
  const { data } = await axios.get(`/api/prototype-passages/episodes/${episodeId}`, { params: { date: ecoute.date } });
  if (ecoute.episodeId !== episodeId) return;
  cp.charger(data);
  ecoute.pret = true;
}

export const avecTranscription = () => TEMOINS.includes(ecoute.date);

export function passageDe(titre) {
  if (!ecoute.pret) return null;
  return cp.visibles().find((p) => norm(p.titre) === norm(titre)) || null;
}

export function estAPlacer(titre) {
  return !!cp.etat.ep?.livresSansPassage.some((l) => norm(l.titre) === norm(titre));
}

export function simulation(titre) {
  const s = SIMULE_A_VALIDER[ecoute.date]?.[norm(titre)];
  if (!s || ecoute.valides[norm(titre)]) return null;
  return s;
}

export function enLecture(titre) {
  const p = passageDe(titre);
  return !!p && cp.lecteur.enLecture && cp.lecteur.t >= p.debut && cp.lecteur.t < p.fin;
}

/** Clic sur ▶ / ○ d'une ligne */
export function ecouterLigne(titre) {
  const k = norm(titre);
  if (enLecture(titre)) {
    cp.basculerLecture();
    return;
  }
  ecoute.ouvert = true;
  ecoute.ligne = k;
  ecoute.cible = { titre, n: (ecoute.cible?.n || 0) + 1 };
  log(passageDe(titre) ? `▶ « ${titre} »` : `○ « ${titre} » sans Passage : à placer`);
}

export function fermer() {
  cp.basculerLecture && cp.lecteur.enLecture && cp.basculerLecture();
  ecoute.ouvert = false;
  ecoute.ligne = null;
}

export function validerSimule(titre, titreValide) {
  ecoute.valides[norm(titre)] = titreValide;
  log(`✅ « ${titre} » validé (simulé) comme « ${titreValide} » : le Passage garde sa clé « ${titre} » et reçoit le livre`);
}
