/**
 * Aucun appel du frontend ne joint un cookie Babelio : le serveur est la seule
 * source du cookie (il le date à la réception et refuse un cookie périmé).
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';

const post = vi.fn();

vi.mock('axios', () => {
  const instance = {
    post: (...args) => post(...args),
    get: vi.fn(),
    interceptors: { request: { use: vi.fn() }, response: { use: vi.fn() } },
  };
  return { default: { create: () => instance } };
});

const { babelioService } = await import('../../src/services/api.js');

describe('babelioService - aucun cookie du navigateur', () => {
  beforeEach(() => {
    post.mockReset();
    post.mockResolvedValue({ data: {} });
    localStorage.setItem('babelio_cookies', 'jstsToken=old; p=FR');
  });

  afterEach(() => {
    localStorage.removeItem('babelio_cookies');
  });

  it('verifyAuthor n\'envoie pas babelio_cookies', async () => {
    await babelioService.verifyAuthor('Annie Ernaux');
    expect(post.mock.calls[0][1]).not.toHaveProperty('babelio_cookies');
  });

  it('verifyBook n\'envoie pas babelio_cookies', async () => {
    await babelioService.verifyBook('Les Années', 'Annie Ernaux');
    expect(post.mock.calls[0][1]).not.toHaveProperty('babelio_cookies');
  });
});

function listSourceFiles(dir) {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) return name === '__tests__' ? [] : listSourceFiles(path);
    return /\.(vue|js)$/.test(name) ? [path] : [];
  });
}

describe('sources frontend', () => {
  it('aucune requête ne porte de champ babelio_cookies', () => {
    const srcDir = join(__dirname, '../../src');
    const offenders = listSourceFiles(srcDir).filter((file) =>
      /babelio_cookies\s*:/.test(readFileSync(file, 'utf-8'))
    );
    expect(offenders).toEqual([]);
  });
});
