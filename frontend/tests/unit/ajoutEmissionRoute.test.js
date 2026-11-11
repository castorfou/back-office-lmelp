/**
 * Route de la page « Ajouter une émission » (Issue #334). Fichier séparé de
 * tests/AjoutEmission.test.js : le routeur importe des modules qui utilisent
 * axios.interceptors, incompatibles avec le vi.mock('axios') de ce fichier.
 */

import { describe, it, expect } from 'vitest';
import router from '../../src/router/index.js';

describe('route /ajout-emission', () => {
  it('ouvre la page AjoutEmission avec un titre explicite', () => {
    const route = router.resolve('/ajout-emission');
    expect(route.name).toBe('AjoutEmission');
    expect(route.meta.title).toBe('Ajouter une émission - lmelp');
  });
});
