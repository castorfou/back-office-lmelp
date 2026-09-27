/**
 * Nom et icônes de l'application (Issue #315) : l'app s'appelle « lmelp »
 * et la PWA déclare des icônes maskable pour remplir le cercle du launcher
 * Android.
 */

import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';
import router from '../../src/router/index.js';

const publicDir = path.resolve(process.cwd(), 'public');
const manifest = JSON.parse(
  fs.readFileSync(path.join(publicDir, 'site.webmanifest'), 'utf8')
);

describe('site.webmanifest', () => {
  it('nomme la PWA « lmelp »', () => {
    expect(manifest.name).toBe('lmelp');
    expect(manifest.short_name).toBe('lmelp');
  });

  it.each(['192x192', '512x512'])(
    'déclare une icône %s en purpose "any" et une en purpose "maskable"',
    (sizes) => {
      const purposes = manifest.icons
        .filter((icon) => icon.sizes === sizes)
        .map((icon) => icon.purpose);
      expect(purposes).toContain('any');
      expect(purposes).toContain('maskable');
    }
  );

  it('ne référence que des icônes présentes dans public/', () => {
    for (const icon of manifest.icons) {
      expect(fs.existsSync(path.join(publicDir, icon.src))).toBe(true);
    }
  });
});

describe("titre de l'application", () => {
  it('index.html a pour titre « lmelp »', () => {
    const html = fs.readFileSync(path.resolve(process.cwd(), 'index.html'), 'utf8');
    expect(html).toContain('<title>lmelp</title>');
  });

  it('tous les titres de page du router se terminent par « - lmelp »', () => {
    const titles = router
      .getRoutes()
      .map((route) => route.meta.title)
      .filter(Boolean);
    expect(titles.length).toBeGreaterThan(0);
    for (const title of titles) {
      expect(title).toMatch(/ - lmelp$/);
    }
  });
});
