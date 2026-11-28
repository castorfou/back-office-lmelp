/** Motifs d'un signalement de Passage, dans l'ordre du menu du lecteur. */
export const MOTIFS = [
  { valeur: 'debut_trop_tot', libelle: 'Début trop tôt' },
  { valeur: 'fin_trop_tot', libelle: 'Fin trop tôt' },
  { valeur: 'deborde', libelle: 'Déborde sur un autre livre' },
  { valeur: 'mauvais_livre', libelle: 'Mauvais livre' },
  { valeur: 'autre', libelle: 'Autre' },
];

export const libelleMotif = (valeur) =>
  MOTIFS.find((m) => m.valeur === valeur)?.libelle || valeur;
