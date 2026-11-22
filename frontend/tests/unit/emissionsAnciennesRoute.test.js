/**
 * Route de la page « Émissions anciennes » (intégration des remises pap).
 * Fichier séparé de tests/RemisesPap.test.js : le routeur importe des modules
 * qui utilisent axios.interceptors, incompatibles avec le vi.mock('axios') de
 * ce fichier.
 */

import { describe, it, expect } from 'vitest';
import router from '../../src/router/index.js';

describe('route /emissions-anciennes', () => {
  it('ouvre la page RemisesPap avec un titre explicite', () => {
    const route = router.resolve('/emissions-anciennes');
    expect(route.name).toBe('RemisesPap');
    expect(route.meta.title).toBe('Émissions anciennes - lmelp');
  });
});
