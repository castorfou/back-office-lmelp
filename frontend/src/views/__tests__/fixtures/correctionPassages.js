/**
 * Émission courte à la forme exacte de GET /api/episodes/{id}/passages
 * (relevée sur l'émission du 15/11/2026 de la base locale).
 */
export const EPISODE_ID = '6af98629a3c9beafb9dcb702'; // pragma: allowlist secret

export const EMISSIONS = [
  { id: 'm1', date: '2026-11-15T09:12:40', episode_id: EPISODE_ID, episode: { titre: 'CRITIQUE : Le Fondateur…' } },
  { id: 'm2', date: '2026-11-08T09:12:40', episode_id: 'e-sans-segments', episode: { titre: 'Sans Segments' } },
];

const passage = (id, titre, debutMs, finMs, extra = {}) => ({
  id, titre, auteur: `Auteur de ${titre}`, section: 1, livre_id: `l-${id}`,
  episode_id: EPISODE_ID, date: '2026-11-15', debut_ms: debutMs, fin_ms: finMs,
  origine: 'auto', place_main: false, ...extra,
});

// Segments [debut_ms, fin_ms, texte] ; un trou de 300 s entre B et C
export const SEGMENTS = [
  [0, 620, 'Musique'],
  [620, 13460, 'Le masque et la plume'],
  [13460, 60000, 'On commence avec Le Fondateur.'],
  [60000, 120000, 'Arnaud ? Un livre formidable.'],
  [120000, 180000, 'On enchaîne avec Paradisi Gloria.'],
  [180000, 240000, 'Nelly ?'],
  [240000, 400000, 'Le courrier des auditeurs.'],
  [400000, 540000, 'Une lettre de Brest.'],
  [540000, 560000, 'Après ce livre, Rouge Truite.'],
  [560000, 600000, 'Fin.'],
];

export const PASSAGE_A = passage('pa', 'Le Fondateur', 13460, 120000);
export const PASSAGE_B = passage('pb', 'Paradisi Gloria', 120000, 240000);
// moins de 30 s, titre pas encore validé
export const PASSAGE_C = passage('pc', 'Rouge Truite', 540000, 560000, { livre_id: null });

export const LIVRE_A_PLACER = {
  titre: 'Vivre après', auteur: 'Auteur de Vivre après', section: 2,
  livre_id: 'l-vivre', raison: 'non_repere',
};

export function etatEmission(extra = {}) {
  return {
    segments: SEGMENTS,
    a_des_segments: true,
    valide: false,
    passages: [PASSAGE_A, PASSAGE_B, PASSAGE_C],
    supprimes: [],
    sans_passage: [LIVRE_A_PLACER],
    ...extra,
  };
}

/** Les routes de correction renvoient l'état sans les Segments. */
export function sansSegments(etat) {
  return { ...etat, segments: [] };
}
