/**
 * Route de la page « Remises pap » (Issue #378). Fichier séparé de
 * tests/RemisesPap.test.js : le routeur importe des modules qui utilisent
 * axios.interceptors, incompatibles avec le vi.mock('axios') de ce fichier.
 */

import { describe, it, expect } from 'vitest';
import router from '../../src/router/index.js';

describe('route /remises-pap', () => {
  it('ouvre la page RemisesPap avec un titre explicite', () => {
    const route = router.resolve('/remises-pap');
    expect(route.name).toBe('RemisesPap');
    expect(route.meta.title).toBe('Remises pap - lmelp');
  });
});
