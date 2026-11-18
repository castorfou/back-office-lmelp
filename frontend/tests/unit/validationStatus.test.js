import { describe, it, expect } from 'vitest';
import { toRowStatus, isTransientStatus } from '../../src/utils/validationStatus.js';

describe('toRowStatus (Issue #352) : statut de validation → statut de ligne du tableau', () => {
  it.each([
    ['verified', 'verified'],
    ['suggestion', 'suggested'],
    ['corrected', 'suggested'],
    ['not_found', 'not_found'],
    ['blocked_403', 'blocked_403'],
    ['error', 'error'],
  ])('%s → %s', (validationStatus, rowStatus) => {
    expect(toRowStatus(validationStatus)).toBe(rowStatus);
  });

  it('un statut inconnu devient une erreur, jamais un statut enregistrable', () => {
    expect(toRowStatus('weird')).toBe('error');
    expect(toRowStatus(undefined)).toBe('error');
  });
});

describe('isTransientStatus : statuts jamais enregistrés en cache', () => {
  it('blocked_403 et error sont transitoires', () => {
    expect(isTransientStatus('blocked_403')).toBe(true);
    expect(isTransientStatus('error')).toBe(true);
  });

  it('les statuts du cache ne le sont pas', () => {
    for (const s of ['verified', 'suggested', 'not_found', 'mongo', null]) {
      expect(isTransientStatus(s)).toBe(false);
    }
  });
});
