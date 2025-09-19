# Intégration Babelio pour Vérification Orthographique

## Aperçu

Le `BabelioService` permet de vérifier et corriger l'orthographe des auteurs, livres et éditeurs extraits des avis critiques en utilisant l'API AJAX de Babelio.com.

## Architecture Technique

### Endpoint Découvert
- **URL** : `POST https://www.babelio.com/aj_recherche.php`
- **Content-Type** : `application/json`
- **Format Payload** : `{"term": "search_term", "isMobile": false}`

### Headers Requis
```python
{
    "Content-Type": "application/json",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
    "User-Agent": "Mozilla/5.0 ...",
    "Referer": "https://www.babelio.com/recherche.php",
    "Origin": "https://www.babelio.com"
}
```

### Cookies Nécessaires
```python
{
    "p": "FR",              # Pays
    "disclaimer": "1",      # Disclaimer accepté
    "g_state": '{"i_l":0}', # État Google
    "bbacml": "0"           # Cookie marketing
}
```

## Format de Réponse

Babelio retourne un array JSON avec différents types d'objets :

### Auteurs
```json
{
    "id": "2180",
    "prenoms": "Michel",
    "nom": "Houellebecq",
    "type": "auteurs",
    "url": "/auteur/Michel-Houellebecq/2180",
    "ca_oeuvres": "38",
    "ca_membres": "30453"
}
```

### Livres
```json
{
    "id_oeuvre": "1770",
    "titre": "Les particules élémentaires",
    "nom": "Houellebecq",
    "prenoms": "Michel",
    "type": "livres",
    "ca_copies": "12565",
    "ca_note": "3.46",
    "url": "/livres/Houellebecq-Les-particules-elementaires/1770"
}
```

## Usage du Service

### Initialisation
```python
from back_office_lmelp.services.babelio_service import babelio_service

# Le service utilise un pattern singleton avec session HTTP réutilisable
```

### Vérification d'Auteur
```python
result = await babelio_service.verify_author("Michel Houellebecq")

# Résultat :
{
    "status": "verified",              # "verified", "corrected", "not_found", "error"
    "original": "Michel Houellebecq",
    "babelio_suggestion": "Michel Houellebecq",
    "confidence_score": 1.0,           # 0.0 à 1.0
    "babelio_data": {...},             # Données brutes Babelio
    "babelio_url": "https://www.babelio.com/auteur/Michel-Houellebecq/2180",
    "error_message": None
}
```

### Vérification de Livre
```python
result = await babelio_service.verify_book("L'Étranger", "Albert Camus")

# Résultat :
{
    "status": "verified",
    "original_title": "L'Étranger",
    "babelio_suggestion_title": "L'Étranger",
    "original_author": "Albert Camus",
    "babelio_suggestion_author": "Albert Camus",
    "confidence_score": 1.0,
    "babelio_data": {...},
    "babelio_url": "...",
    "error_message": None
}
```

### Traitement en Lot
```python
items = [
    {"type": "author", "name": "Michel Houellebecq"},
    {"type": "book", "title": "L'Étranger", "author": "Albert Camus"},
    {"type": "publisher", "name": "Gallimard"}
]

results = await babelio_service.verify_batch(items)
```

### Fermeture de Session
```python
await babelio_service.close()  # Fermer la session HTTP proprement
```

## Fonctionnalités

### Tolérance aux Fautes d'Orthographe
Babelio tolère automatiquement les fautes d'orthographe courantes :
- `"Houllebeck"` → trouve `"Michel Houellebecq"`
- `"L'Etranger"` → trouve `"L'Étranger"`

### Rate Limiting Respectueux
- **Maximum** : 1 requête par seconde
- **Timeout** : 10 secondes total, 5 secondes connexion
- **Gestion d'erreurs** : Gracieuse avec fallback

### Calcul de Score de Confiance
- **1.0** : Match exact
- **0.95+** : Statut `"verified"`
- **0.8-0.94** : Statut `"corrected"`
- **< 0.8** : Recherche plus de suggestions ou `"not_found"`

## Contraintes et Limitations

### Respect de Babelio
- Rate limiting strict (1 req/sec)
- Headers et cookies appropriés
- User-Agent réaliste
- Pas de scraping intensif

### Gestion d'Erreurs
Le service gère robustement :
- Timeouts réseau
- Erreurs HTTP (500, 404, etc.)
- Parsing JSON invalide
- Connexions fermées

### Types de Recherche
- **Auteurs** : Recherche directe optimisée
- **Livres** : Recherche par titre + auteur
- **Éditeurs** : Utilise la même logique que les auteurs (limitation Babelio)

## Algorithmes

### Similarité de Chaînes
Utilise `difflib.SequenceMatcher` (algorithme Ratcliff-Obershelp) pour calculer la similarité orthographique entre chaînes.

### Sélection du Meilleur Match
- **Auteurs** : Trie par nombre de membres et d'œuvres
- **Livres** : Trie par nombre de copies et note moyenne
- **Filtrage** : Par auteur si fourni pour les livres

## Tests

### Tests Unitaires
```bash
PYTHONPATH=/workspaces/back-office-lmelp/src pytest tests/test_babelio_service.py -v
```

### Tests d'Intégration
Les tests utilisent des mocks pour éviter les appels réseau réels lors des tests automatisés.

## Sécurité

### Données Sensibles
- Pas de stockage de données utilisateur
- Pas de logs des termes de recherche sensibles
- Session HTTP fermée proprement

### Conformité
- Respect des conditions d'utilisation de Babelio
- Pas de contournement de limitations techniques
- Rate limiting conservative

## Performance

### Optimisations
- Session HTTP réutilisable
- Cache des headers/cookies
- Requêtes asynchrones (aiohttp)
- Timeout appropriés

### Métriques Attendues
- **Latence** : 200-500ms par requête
- **Précision** : ~85-90% pour corrections orthographiques courantes
- **Disponibilité** : Dépendante de Babelio.com

## Évolutions Futures

### Améliorations Possibles
- Cache Redis pour éviter requêtes répétées
- Metrics et monitoring des performances
- Support des éditeurs si Babelio expose mieux l'API
- Batch processing optimisé

### Problèmes Techniques Résolus

#### Content-Type Incorrect
**Problème** : Babelio retourne du JSON valide mais avec `Content-Type: text/html; charset=ISO-8859-1` au lieu de `application/json`.

**Solution** : Utilisation de `response.text()` puis `json.loads()` au lieu de `response.json()` pour contourner la validation stricte d'aiohttp.

```python
# Au lieu de :
results = await response.json()  # Échoue à cause du Content-Type

# Utiliser :
text_content = await response.text()
results = json.loads(text_content)  # Fonctionne correctement
```

### Intégration Complète
Le service est maintenant pleinement intégré dans :
- ✅ **L'endpoint `/api/verify-babelio`** (implémenté)
- ✅ **L'interface de test `/babelio-test`** (Vue.js)
- ✅ **Tests automatisés** (7 tests endpoint + 16 tests frontend)
- ✅ **L'interface `/livres-auteurs`** (validation en temps réel)
- 🔄 **Les workflows d'extraction des avis critiques** (intégration future)

### Système de Validation Intelligent BiblioValidationService

Le service `BiblioValidationService.js` fournit une validation bibliographique intelligente à 4 étapes :

#### Architecture Avancée
- **Service composite** : Combine fuzzy search (ground truth), Babelio, et recherche locale
- **Validation en cascade** : 4 étapes progressives pour maximiser la précision
- **Priorisation intelligente** : Ground truth > Babelio > Local search
- **Gestion des fragments** : Reconstruction d'auteurs à partir de fragments épars

#### Algorithme de Validation à 4 Étapes

1. **Étape 1** : Recherche fuzzy dans l'épisode (ground truth)
2. **Étape 2** : Vérification auteur sur Babelio
3. **Étape 3** : Vérification livre avec auteur original
4. **Étape 4** : Vérification livre avec auteur corrigé (si différent)

#### Statuts de Sortie
- **`validated`** : Données confirmées (ground truth + Babelio)
- **`suggestion`** : Correction proposée avec haute confiance
- **`not_found`** : Aucune correspondance fiable trouvée

#### Composant BiblioValidationCell

Le composant `BiblioValidationCell.vue` intègre le service pour la validation en temps réel :

##### Fonctionnalités
- **Validation automatique** : Service `BiblioValidationService` au montage
- **Rate limiting** : Respect strict de la limite 1 req/sec
- **États visuels** : ✅ validé, 🔄 suggestion, ❓ non trouvé, ⚠️ erreur
- **Retry intelligent** : Bouton de nouvelle tentative en cas d'erreur
- **Suggestions détaillées** : Affichage des corrections auteur/titre

##### API Service Frontend
Service `babelioService` dans `api.js` avec méthodes :
- `verifyAuthor(name)` : Vérification d'auteur
- `verifyBook(title, author)` : Vérification de livre
- `verifyPublisher(name)` : Vérification d'éditeur

##### Tests Complets
- **37 tests** pour `BiblioValidationService.modular.test.js` (fixtures YAML)
- **16 tests** pour `BiblioValidationCell.test.js` (composant Vue)
- **4 tests** d'intégration dans `LivresAuteurs.test.js`
- **Couverture end-to-end** : Tous les scénarios de validation
- **Tests de cas réels** : Données issues de /livres-auteurs
