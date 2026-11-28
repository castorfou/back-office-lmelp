/**
 * Adresse publique de lmelp-streaming, déduite de celle de lmelp (Issue #427).
 */
import { describe, it, expect } from 'vitest';
import { adresseStreaming } from '../adresseStreaming';

describe('adresseStreaming', () => {
  it('remplace le premier nom « lmelp » par « lmelp-streaming », en https', () => {
    expect(adresseStreaming({ hostname: 'lmelp.ascot63.synology.me' }))
      .toBe('https://lmelp-streaming.ascot63.synology.me');
  });

  it("ne déduit rien d'une adresse qui ne commence pas par « lmelp. »", () => {
    expect(adresseStreaming({ hostname: 'localhost' })).toBeNull();
    expect(adresseStreaming({ hostname: '192.168.50.207' })).toBeNull();
    expect(adresseStreaming({ hostname: 'lmelp-dev.exemple.fr' })).toBeNull();
    expect(adresseStreaming({ hostname: 'lmelp' })).toBeNull();
  });
});
