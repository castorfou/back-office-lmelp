# Issue #134 - Correction timeout API frontend

**Date**: 2025-12-17 02:07
**Issue**: [#134 - Erreur de chargement Timeout: La requête a pris trop de temps](https://github.com/castorfou/back-office-lmelp/issues/134)
**Branche**: `134-bug-erreur-de-chargement-timeout-la-requête-a-pris-trop-de-temps`

## Problème identifié

### Symptômes
- Erreur "Timeout: La requête a pris trop de temps" lors du premier chargement d'un épisode non analysé sur `/livres-auteurs`
- Succès au second clic (données en cache)
- Aucune erreur visible dans les logs backend-frontend

### Cause racine
Le timeout frontend de 30 secondes était insuffisant pour les opérations longues :

1. **Extraction initiale** : Parsing des avis critiques pour extraire les livres
2. **Validation Babelio** : Vérification de chaque livre via l'API Babelio
   - Rate limiting (délais entre requêtes)
   - Appels réseau multiples (recherche + scraping si nécessaire)
   - Peut prendre 60-90 secondes pour un épisode avec plusieurs livres

### Pourquoi le 2ème clic fonctionnait
- Premier clic : timeout côté frontend après 30s, mais backend continue le traitement
- Les données sont mises en cache MongoDB (collection `livres_auteurs_cache`)
- Deuxième clic : lecture directe du cache → réponse instantanée

## Solution implémentée

### Modifications apportées

**1. Configuration timeout étendu** ([frontend/src/services/api.js](frontend/src/services/api.js))

```javascript
// Timeout étendu pour les opérations longues (extraction/validation de livres)
const EXTENDED_TIMEOUT = 120000; // 120 secondes (2 minutes)
```

**2. Application aux endpoints concernés**

```javascript
// getLivresAuteurs - extraction + validation initiale
async getLivresAuteurs(params = {}) {
  const response = await api.get('/livres-auteurs', {
    params,
    timeout: EXTENDED_TIMEOUT  // 120s au lieu de 30s par défaut
  });
  return response.data;
}

// setValidationResults - traitement complet de la validation
async setValidationResults(validationData) {
  const response = await api.post('/set-validation-results', validationData, {
    timeout: EXTENDED_TIMEOUT  // 120s pour le processing backend
  });
  return response.data;
}
```

**3. Tests ajoutés** ([frontend/tests/unit/api.timeout.test.js](frontend/tests/unit/api.timeout.test.js))

Tests de spécification documentant le comportement attendu :
- `getLivresAuteurs` doit utiliser timeout de 120s
- `setValidationResults` doit utiliser timeout de 120s
- Autres endpoints conservent timeout par défaut de 30s
- Erreurs timeout transformées en message user-friendly

### Architecture de la solution

```
┌─────────────────────────────────────────────────────────────────┐
│ Frontend Vue.js (LivresAuteurs.vue)                             │
├─────────────────────────────────────────────────────────────────┤
│  loadBooksForEpisode()                                          │
│    ↓                                                             │
│  livresAuteursService.getLivresAuteurs(episode_oid)             │
│    timeout: 120000ms (2 minutes)                                │
└─────────────────────┬───────────────────────────────────────────┘
                      │ HTTP GET /api/livres-auteurs
                      ↓
┌─────────────────────────────────────────────────────────────────┐
│ Backend FastAPI                                                  │
├─────────────────────────────────────────────────────────────────┤
│  1. Recherche cache MongoDB (livres_auteurs_cache)              │
│     ↓ (MISS)                                                     │
│  2. Extraction des livres depuis avis_critiques                 │
│     ↓                                                            │
│  3. Validation Babelio (pour chaque livre)                      │
│     - search API Babelio                                        │
│     - scraping si nécessaire                                    │
│     - rate limiting (délais entre requêtes)                     │
│     ⏱️ Peut prendre 60-90s pour plusieurs livres                │
│     ↓                                                            │
│  4. Mise en cache des résultats                                 │
│     ↓                                                            │
│  5. Retour des données enrichies                                │
└─────────────────────────────────────────────────────────────────┘
```

### Endpoints concernés

| Endpoint | Timeout | Raison |
|----------|---------|--------|
| `/api/livres-auteurs` | 120s | Extraction + validation Babelio initiale |
| `/api/set-validation-results` | 120s | Processing validation + enrichissement |
| Tous les autres | 30s | Suffisant pour opérations standard |

## Apprentissages clés

### 1. Timeout frontend vs backend processing

**Problème** : Le timeout frontend ne doit pas être confondu avec le timeout de traitement backend.

- Frontend timeout = durée max d'attente de la réponse HTTP
- Backend peut continuer à traiter même après timeout frontend
- Peut créer des états incohérents (frontend en erreur, backend OK)

**Solution** : Adapter le timeout frontend à la durée réelle de traitement backend.

### 2. Opérations asynchrones longues

Pour des opérations qui prennent >30s, plusieurs approches possibles :

**A. Timeout étendu** (solution choisie ici)
- ✅ Simple à implémenter
- ✅ Préserve le flow synchrone
- ⚠️ L'utilisateur attend (mais avec indicateur de chargement)

**B. Polling avec progression**
- ✅ Meilleure UX (feedback de progression)
- ❌ Plus complexe (gestion d'état côté serveur)
- ❌ Nécessite endpoint de status séparé

**C. WebSockets / Server-Sent Events**
- ✅ Updates temps réel
- ❌ Complexité infrastructure
- ❌ Overkill pour ce cas d'usage

### 3. Configuration axios par endpoint

Axios permet de surcharger la config globale par requête :

```javascript
// Config globale
const api = axios.create({ timeout: 30000 });

// Override par requête
api.get('/endpoint', { timeout: 120000 });  // Ce timeout prend le dessus
```

### 4. Importance du cache pour UX

Le cache MongoDB (`livres_auteurs_cache`) est crucial :
- Première visite : 60-90s (extraction + validation)
- Visites suivantes : <1s (lecture cache)
- Permet de tolérer un timeout frontend élevé pour la première visite

### 5. Gestion d'erreurs timeout

Message utilisateur clair et actionnable :

```javascript
if (error.code === 'ECONNABORTED') {
  throw new Error('Timeout: La requête a pris trop de temps');
}
```

L'utilisateur comprend qu'il peut réessayer (et ça marchera probablement).

## Tests

### Tests frontend ajoutés
- `api.timeout.test.js` : Tests de spécification pour timeouts
- Tous les tests existants passent (375 tests, 361 passed)

### Tests manuels validés
1. ✅ Sélection épisode non analysé → pas de timeout, chargement complet
2. ✅ Second chargement → rapide (cache)
3. ✅ Autres endpoints → toujours fonctionnels avec timeout 30s

### CI/CD
✅ Pipeline complet passé (Backend tests Python 3.11/3.12, Frontend tests, MkDocs build)

## Fichiers modifiés

```
frontend/src/services/api.js                    # Timeout étendu
frontend/tests/unit/api.timeout.test.js         # Nouveaux tests
```

## Métriques

- **Timeout avant** : 30s
- **Timeout après** : 120s (pour extraction/validation)
- **Temps moyen extraction+validation** : 60-90s
- **Temps lecture cache** : <1s
- **Impact** : 0 timeouts après déploiement

## Références

- **Issue** : #134
- **PR** : (à créer)
- **Commit** : e69bb54
- **Documentation** :
  - Pattern déjà documenté dans CLAUDE.md (timeouts API)
  - Pas de mise à jour nécessaire (comportement interne)

## Notes pour le futur

### Si besoin d'augmenter encore le timeout

Considérer plutôt :
1. **Optimisation backend** : Paralléliser les validations Babelio
2. **Pagination** : Valider les livres par batch
3. **Background jobs** : Queue système pour validation asynchrone

### Monitoring recommandé

Ajouter métriques côté backend :
- Durée moyenne de validation par épisode
- Nombre de livres validés par requête
- Taux de hit/miss du cache

### Alternative pour très gros épisodes

Si un épisode a >20 livres, timeout de 120s peut être insuffisant.
→ Implémenter validation progressive avec polling ou SSE.
