/**
 * Correspondance entre les statuts renvoyés par la validation Babelio
 * (BiblioValidationService.validateBiblio) et ceux d'une ligne du tableau
 * Livres et Auteurs (book.status, lu par BiblioValidationCell).
 *
 * Les lignes parlent le vocabulaire du cache livresauteurs_cache
 * (verified / suggested / not_found / mongo), plus deux statuts transitoires,
 * blocked_403 et error, que le backend n'enregistre jamais.
 */

const VALIDATION_TO_ROW = {
  verified: 'verified',
  suggestion: 'suggested',
  corrected: 'suggested',
  not_found: 'not_found',
  blocked_403: 'blocked_403',
  error: 'error',
};

const TRANSIENT_STATUSES = new Set(['blocked_403', 'error']);

export function toRowStatus(validationStatus) {
  return VALIDATION_TO_ROW[validationStatus] || 'error';
}

export function isTransientStatus(rowStatus) {
  return TRANSIENT_STATUSES.has(rowStatus);
}
