# Système de Tests avec Fixtures Capturées 🧪

## Principe général

**Problème** : Comment tester une logique complexe (BiblioValidationService) avec de vraies données d'API sans duplication de code ?

**Solution** : Capturer les appels API réels depuis l'interface utilisateur pour alimenter automatiquement les tests avec des données authentiques.

## Philosophie

### 🎯 Tests avec vraies données
- Les tests utilisent des **mocks alimentés par de vraies réponses API**
- Pas de données factices → détection automatique des incohérences
- Les fixtures sont **auto-générées** depuis l'interface utilisateur

### 🔄 Workflow évolutif
1. **Définir** les cas de test dans `biblio-validation-cases.yml`
2. **Capturer** les vraies données via l'interface `/livres-auteurs`
3. **Exécuter** les tests qui révèlent automatiquement les problèmes
4. **Corriger** la logique ou les fixtures selon les résultats

## Architecture des fixtures

### 📂 Structure des fichiers
```
frontend/tests/fixtures/
├── biblio-validation-cases.yml    # Cas de test end-to-end (manuel)
├── babelio-author-cases.yml       # Réponses API auteurs (auto-généré)
├── babelio-book-cases.yml         # Réponses API livres (auto-généré)
└── fuzzy-search-cases.yml         # Réponses API fuzzy search (auto-généré)
```

### 🎭 Deux types de fixtures

#### 1. **Cas de test end-to-end** (manuel)
- **Fichier** : `biblio-validation-cases.yml`
- **Contenu** : Input + résultat attendu de la validation complète
- **Gestion** : Ajouté/modifié **manuellement** par les développeurs
- **Purpose** : Définir les scenarios à tester

#### 2. **Données d'API** (auto-généré)
- **Fichiers** : `babelio-*.yml`, `fuzzy-search-*.yml`
- **Contenu** : Vraies réponses API capturées
- **Gestion** : Généré **automatiquement** via l'interface
- **Purpose** : Alimenter les mocks avec de vraies données

## Étapes pratiques pour les développeurs

### 📝 1. Définir un nouveau cas de test

Éditer manuellement `frontend/tests/fixtures/biblio-validation-cases.yml` :

```yaml
cases:
- input:
    author: "Nouveau Auteur"
    title: "Nouveau Livre"
    publisher: "Éditeur"
    episodeId: "episode-id-123"
  output:
    status: "suggestion"  # ou "verified" ou "not_found"
    suggested_author: "Auteur Corrigé"
    suggested_title: "Titre Corrigé"
    corrections:
      author: true
      title: false
```

### 🎯 2. Capturer les vraies données API

1. **Lancer l'interface** : `npm run dev`
2. **Aller sur** `/livres-auteurs`
3. **Sélectionner l'épisode** correspondant à votre cas
4. **Cliquer sur le bouton** `🔄 YAML` de la ligne voulue
5. **Vérifier dans la console** : `✅ Fixtures updated: {...}`

**Résultat** : Les fichiers `babelio-*.yml` et `fuzzy-search-*.yml` sont automatiquement enrichis avec les vraies réponses API.

### 🧪 3. Lancer les tests

```bash
npm test -- --run BiblioValidation
```

**Interprétation des résultats** :
- ✅ **Test passe** → La logique est cohérente avec les données capturées
- ❌ **Test échoue** → Incohérence détectée entre logique et fixture

### 🔧 4. Corriger les problèmes détectés

Deux possibilités selon le contexte :

#### Option A : Corriger la logique métier
Si le test révèle un bug dans `BiblioValidationService.js`

#### Option B : Corriger la fixture
Si le résultat attendu dans `biblio-validation-cases.yml` était incorrect

## Choix de conception

### 🎭 Pourquoi deux types de fixtures ?

#### **Fixtures end-to-end** (manuel)
- **Avantage** : Contrôle total sur les scenarios de test
- **Inconvénient** : Maintenance manuelle nécessaire
- **Usage** : Définir "ce qui devrait arriver"

#### **Fixtures d'API** (auto-généré)
- **Avantage** : Toujours synchronisé avec la réalité de l'API
- **Inconvénient** : Pas de contrôle sur le contenu
- **Usage** : Alimenter les mocks avec de vraies données

### 🧠 Pourquoi cette approche de test ?

#### **Problème des mocks traditionnels**
```javascript
// ❌ Approche classique = données factices
mockBabelioService.verifyAuthor.mockResolvedValue({
  status: 'verified',  // <- Inventé par le développeur
  original: 'Test'     // <- Peut ne pas refléter la réalité
});
```

#### **Solution avec fixtures capturées**
```javascript
// ✅ Notre approche = vraies données
const authorFixture = findFixtureByAuthor('Emmanuel Carrère');
mockBabelioService.verifyAuthor.mockResolvedValue(authorFixture.output);
// ↑ Données réelles capturées depuis l'API Babelio
```

### ⚡ Avantages de cette méthode

1. **Détection automatique d'incohérences** : Les tests révèlent les problèmes sans effort
2. **Données toujours à jour** : Un clic → fixtures synchronisées avec l'API
3. **Tests réalistes** : Pas de données fictives qui cachent les vrais problèmes
4. **Maintenance réduite** : Pas besoin de maintenir manuellement les réponses d'API

## Commandes essentielles

```bash
# Lancer tous les tests de validation biblio
npm test -- --run BiblioValidation

# Lancer uniquement les tests avec vraies données
npm test -- --run "Captured Cases with Real Data"

# Lancer l'interface pour capturer
npm run dev

# Vérifier les fixtures générées
ls frontend/tests/fixtures/
```
