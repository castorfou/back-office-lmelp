/**
 * Tests unitaires pour la dérivation dynamique de l'URL du front-office lmelp
 * Issue #265: URL hardcodée sur localhost:8501, cassée en prod (NAS/reverse proxy)
 */

import { describe, it, expect } from 'vitest';
import { getLmelpFrontOfficeUrl } from '../../src/utils/lmelpFrontOfficeUrl.js';

describe('getLmelpFrontOfficeUrl', () => {
  it('pointe vers localhost:8501 quand le hostname est localhost', () => {
    expect(getLmelpFrontOfficeUrl('localhost')).toBe('http://localhost:8501/');
  });

  it('pointe vers 127.0.0.1:8501 quand le hostname est 127.0.0.1', () => {
    expect(getLmelpFrontOfficeUrl('127.0.0.1')).toBe('http://127.0.0.1:8501/');
  });

  it('pointe vers la même IP en port 8501 quand le hostname est une IP brute', () => {
    expect(getLmelpFrontOfficeUrl('192.168.50.207')).toBe('http://192.168.50.207:8501/');
  });

  it('retire le suffixe -bo du premier label pour un nom de domaine', () => {
    expect(getLmelpFrontOfficeUrl('lmelp-bo.ascot63.synology.me')).toBe(
      'https://lmelp.ascot63.synology.me/'
    );
  });

  it('applique la règle -bo de façon générique, pas seulement pour ascot63', () => {
    expect(getLmelpFrontOfficeUrl('foo-bo.example.com')).toBe('https://foo.example.com/');
  });

  it('retombe sur le comportement par défaut si le domaine ne contient pas -bo', () => {
    expect(getLmelpFrontOfficeUrl('some-other-host.com')).toBe('http://localhost:8501/');
  });

  it('retombe sur le comportement par défaut pour un hostname vide', () => {
    expect(getLmelpFrontOfficeUrl('')).toBe('http://localhost:8501/');
  });

  it('ajoute le path optionnel pour localhost', () => {
    expect(getLmelpFrontOfficeUrl('localhost', 'avis_critiques')).toBe(
      'http://localhost:8501/avis_critiques'
    );
  });

  it('ajoute le path optionnel pour une IP', () => {
    expect(getLmelpFrontOfficeUrl('192.168.50.207', 'avis_critiques')).toBe(
      'http://192.168.50.207:8501/avis_critiques'
    );
  });

  it('ajoute le path optionnel pour un nom de domaine -bo', () => {
    expect(getLmelpFrontOfficeUrl('lmelp-bo.ascot63.synology.me', 'avis_critiques')).toBe(
      'https://lmelp.ascot63.synology.me/avis_critiques'
    );
  });
});
