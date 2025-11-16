# Issue #103 - Fix CORS Error (URL Relative vs Absolute)

**Date**: 2025-11-16
**Issue**: [#103 - Erreur de chargement des détails d'un livre (CORS/Network Error)](https://github.com/castorfou/back-office-lmelp/issues/103)
**Branch**: `103-erreur-de-chargement-des-détails-dun-livre-corsnetwork-error`

## 🐛 Problème

Lors de la navigation vers la page de détail d'un livre ou d'un auteur, une erreur réseau empêchait le chargement :

```
Cross-Origin Request Blocked: The Same Origin Policy disallows reading the remote
resource at http://localhost:54321/api/livre/{id}.
(Reason: CORS request did not succeed). Status code: (null).
```

## 🔍 Cause racine

**Deux approches incompatibles pour accéder au backend** :

1. **Proxy Vite (fonctionnel)** :
   - Configuré dans `vite.config.js`
   - Découverte automatique du port backend via `.dev-ports.json`
   - Redirige les requêtes `/api/*` vers le backend
   - ✅ Utilisé par la majorité des composants

2. **Appels directs (problématique)** :
   - Dans `LivreDetail.vue` et `AuteurDetail.vue`
   - Tentaient d'accéder directement à `http://localhost:54321/api/...`
   - Utilisaient `window.BACKEND_URL` (jamais défini)
   - Fallback sur le port hardcodé 54321
   - ❌ **Bypassaient le proxy Vite** → erreur CORS

## ✅ Solution

**Utiliser le proxy Vite** en remplaçant les URL absolues par des chemins relatifs :

```javascript
// ❌ Avant (bypass le proxy)
const backendUrl = window.BACKEND_URL || 'http://localhost:54321';
const response = await axios.get(`${backendUrl}/api/livre/${livreId}`);

// ✅ Après (utilise le proxy)
const response = await axios.get(`/api/livre/${livreId}`);
```

## 📝 Modifications

### Code modifié

1. **[frontend/src/views/LivreDetail.vue:131-132](../../frontend/src/views/LivreDetail.vue#L131-L132)**
   - Suppression de la variable `backendUrl`
   - Utilisation d'URL relative `/api/livre/${livreId}`
   - Commentaire explicatif avec référence à l'issue

2. **[frontend/src/views/AuteurDetail.vue:101-102](../../frontend/src/views/AuteurDetail.vue#L101-L102)**
   - Suppression de la variable `backendUrl`
   - Utilisation d'URL relative `/api/auteur/${auteurId}`
   - Commentaire explicatif avec référence à l'issue

### Tests ajoutés (TDD)

3. **[frontend/tests/integration/LivreDetail.test.js:272-290](../../frontend/tests/integration/LivreDetail.test.js#L272-L290)**
   - Nouveau test : `should use relative URL to leverage Vite proxy (Issue #103)`
   - Vérifie que l'URL appelée est exactement `/api/livre/{id}`
   - Vérifie l'absence de `http://` et `localhost`

4. **[frontend/tests/integration/AuteurDetail.test.js:245-263](../../frontend/tests/integration/AuteurDetail.test.js#L245-L263)**
   - Nouveau test : `should use relative URL to leverage Vite proxy (Issue #103)`
   - Vérifie que l'URL appelée est exactement `/api/auteur/{id}`
   - Vérifie l'absence de `http://` et `localhost`

## 🧪 Approche TDD complète

1. ✅ **RED** : Écriture de tests qui échouent
   - Tests vérifient l'utilisation d'URL relatives
   - Échec attendu : `http://localhost:54321/api/...` != `/api/...`

2. ✅ **GREEN** : Implémentation de la correction
   - Suppression des URL absolues
   - Utilisation d'URL relatives

3. ✅ **Vérification** :
   - Tous les tests passent (304 tests frontend)
   - Test manuel confirmé par l'utilisateur

## 💡 Points clés à retenir

### 1. Proxy Vite pour le développement

**Pourquoi** : Évite les problèmes CORS en développement

**Comment** :
```javascript
// vite.config.js
proxy: {
  '/api': {
    target: getBackendTarget(), // Auto-découverte du port
    changeOrigin: true
  }
}
```

**Usage** : Toujours utiliser des chemins relatifs `/api/*` dans les composants Vue

### 2. Pattern URL relative vs absolue

| Type | Exemple | Utilisation | Proxy Vite |
|------|---------|-------------|------------|
| **Relative** | `/api/livre/123` | ✅ Développement | ✅ Oui |
| **Absolute** | `http://localhost:54321/api/livre/123` | ❌ Bypass proxy | ❌ Non |

### 3. Variables d'environnement inutilisées

- `window.BACKEND_URL` n'était jamais défini
- Le fallback hardcodé `54321` ne correspondait pas au port réel
- **Leçon** : Ne pas inventer de variables d'environnement sans les définir réellement

### 4. Tests pour vérifier l'architecture

Les tests ne doivent pas seulement vérifier le comportement fonctionnel, mais aussi :
- ✅ L'utilisation correcte des patterns architecturaux (proxy Vite)
- ✅ Les détails d'implémentation importants (URL relatives)

**Exemple** :
```javascript
it('should use relative URL to leverage Vite proxy (Issue #103)', async () => {
  // ...
  const callUrl = axios.get.mock.calls[0][0];
  expect(callUrl).toBe('/api/livre/68e841e6066cb40c25d5d283');
  expect(callUrl).not.toContain('http://');
  expect(callUrl).not.toContain('localhost');
});
```

## 📊 Impact

- ✅ **Fonctionnalité restaurée** : Les pages de détail livre/auteur fonctionnent à nouveau
- ✅ **Cohérence** : Tous les composants utilisent maintenant le proxy Vite
- ✅ **Maintenabilité** : Plus de ports hardcodés dans le code Vue
- ✅ **Tests** : Couverture de test renforcée (2 nouveaux tests d'intégration)

## 🔗 Références

- **Issue GitHub** : [#103](https://github.com/castorfou/back-office-lmelp/issues/103)
- **Documentation Vite** : [Server Proxy Options](https://vitejs.dev/config/server-options.html#server-proxy)
- **Pattern de découverte automatique** : `vite.config.js:10-44` (fonction `getBackendTarget()`)
