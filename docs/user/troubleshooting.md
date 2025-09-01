# Résolution de problèmes - Back-Office LMELP

## Problèmes courants et solutions

### 🔌 Problèmes de connexion

#### Application inaccessible (localhost:5173 ne répond pas)

**Symptômes :**
- Page blanche ou erreur "Connexion impossible"
- Message "Cette page est inaccessible"
- Temps de chargement infini

**Solutions :**

1. **Vérifiez que le frontend est démarré :**
   ```bash
   # Dans le terminal
   cd frontend
   npm run dev
   ```

2. **Contrôlez l'URL :**
   - URL correcte : `http://localhost:5173`
   - Pas `https://` ni port différent

3. **Vérifiez les ports occupés :**
   - Essayez un autre port si 5173 est occupé
   - Fermez les autres applications utilisant ce port

#### API Backend inaccessible

**Symptômes :**
- Liste d'épisodes vide
- Erreur "Impossible de contacter le serveur"
- Erreur réseau dans la console (F12)

**Solutions :**

1. **Vérifiez que le backend tourne :**
   ```bash
   # Vérifiez dans un autre terminal
   PYTHONPATH=/workspaces/back-office-lmelp/src API_PORT=54322 python -m back_office_lmelp.app
   ```

2. **Testez l'API directement :**
   - Ouvrez : `http://localhost:54322/api/episodes`
   - Vous devez voir du JSON avec les épisodes

3. **Vérifiez les logs backend :**
   - Messages d'erreur dans le terminal backend
   - Erreurs de connexion MongoDB

### 💾 Problèmes de sauvegarde

#### "Erreur de sauvegarde - [object Object]" (RÉSOLU)

**Contexte :** Ce problème a été corrigé dans la version actuelle.

**Cause historique :** Incompatibilité format text/plain entre frontend/backend
**Solution appliquée :** Backend modifié pour lire Request.body() correctement

#### Sauvegarde en cours indéfiniment

**Symptômes :**
- Indicateur "⏳ Sauvegarde en cours..." ne disparaît pas
- Modifications perdues au rechargement

**Solutions :**

1. **Rechargez la page :**
   - F5 ou Ctrl+R
   - Vérifiez si les modifications sont conservées

2. **Vérifiez la connexion réseau :**
   - Console navigateur (F12) → onglet Network
   - Recherchez les erreurs HTTP

3. **Forcez la sauvegarde :**
   - Ctrl+S dans la zone de texte
   - Ou modifiez légèrement le texte pour relancer

#### Modifications perdues

**Symptômes :**
- Texte corrigé disparaît après rechargement
- Retour à la description originale

**Solutions :**

1. **Vérifiez l'indicateur de sauvegarde :**
   - Attendez "✅ Sauvegardé" avant de changer d'épisode

2. **Testez avec un petit texte :**
   - Faites une modification mineure
   - Vérifiez qu'elle se sauvegarde correctement

3. **Contrôlez l'ID d'épisode :**
   - Vérifiez que l'URL contient le bon ID d'épisode

### 🎯 Problèmes de sélection d'épisodes

#### Liste d'épisodes vide

**Symptômes :**
- Menu déroulant vide ou avec message d'erreur
- "Aucun épisode disponible"

**Solutions :**

1. **Vérifiez la base de données MongoDB :**
   ```bash
   # Connectez-vous à MongoDB
   mongosh
   use lmelp
   db.episodes.countDocuments()
   ```

2. **Contrôlez les logs backend :**
   - Messages d'erreur de connexion MongoDB
   - Erreurs de requêtes

3. **Redémarrez les services :**
   ```bash
   # Backend
   Ctrl+C puis API_PORT=54322 python -m back_office_lmelp.app

   # Frontend
   Ctrl+C puis npm run dev
   ```

#### Épisode ne se charge pas après sélection

**Symptômes :**
- Clic sur épisode sans effet
- Zone de détails reste vide

**Solutions :**

1. **Vérifiez l'ID d'épisode :**
   - Console navigateur (F12) → erreurs JavaScript
   - Recherchez les erreurs d'ObjectId MongoDB

2. **Testez un autre épisode :**
   - Vérifiez si le problème est général ou spécifique

3. **Rechargez complètement :**
   - Ctrl+Shift+R (rechargement force)

### 🧠 Problèmes de mémoire

#### Application se ferme brutalement

**Symptômes :**
- Page se recharge automatiquement
- Message "Limite mémoire dépassée"
- Onglet se ferme tout seul

**Explication :**
Les garde-fous mémoire protègent le système en rechargeant/fermant l'application si elle consomme trop de mémoire.

**Solutions :**

1. **Réduisez les onglets ouverts :**
   - Fermez les onglets inutiles
   - Libérez de la mémoire RAM

2. **Redémarrez le navigateur :**
   - Complètement fermer et rouvrir le navigateur
   - Vide le cache mémoire

3. **Travaillez sur des épisodes plus courts :**
   - Évitez les très longues transcriptions
   - Divisez le travail en sessions courtes

#### Alertes mémoire fréquentes

**Symptômes :**
- Messages "⚠️ Attention: utilisation mémoire élevée"
- Performance dégradée

**Solutions :**

1. **Surveillance préventive :**
   - Sauvegardez plus fréquemment
   - Rechargez périodiquement la page

2. **Optimisation navigateur :**
   - Fermez les extensions non nécessaires
   - Utilisez un navigateur avec moins d'onglets

### 🖥️ Problèmes d'interface

#### Interface déformée ou mal affichée

**Symptômes :**
- Éléments qui se chevauchent
- Texte coupé ou illisible
- Boutons non cliquables

**Solutions :**

1. **Vérifiez le zoom du navigateur :**
   - Ctrl+0 pour remettre à 100%
   - Ou ajustez avec Ctrl++ / Ctrl+-

2. **Testez un autre navigateur :**
   - Chrome, Firefox, Safari, Edge
   - Vérifiez la compatibilité

3. **Videz le cache :**
   - Ctrl+Shift+R
   - Ou effacez le cache dans les paramètres

#### Zone de texte non éditable

**Symptômes :**
- Impossible de cliquer dans "Description corrigée"
- Curseur ne s'affiche pas
- Saisie au clavier sans effet

**Solutions :**

1. **Vérifiez la sélection d'épisode :**
   - Un épisode doit être sélectionné pour éditer

2. **Rechargez la page :**
   - F5 pour rafraîchir l'interface

3. **Testez avec un autre épisode :**
   - Le problème peut être spécifique à un épisode

### 📱 Problèmes mobile/responsive

#### Interface difficile à utiliser sur mobile

**Solutions :**

1. **Orientation paysage :**
   - Tournez l'appareil en mode paysage
   - Plus d'espace pour l'édition

2. **Zoom adaptatif :**
   - Pincez pour zoomer sur les zones d'édition
   - Dézoomez pour voir l'ensemble

3. **Navigateur moderne :**
   - Utilisez Chrome ou Firefox mobile
   - Évitez les navigateurs intégrés d'applications

## Diagnostics avancés

### Console du navigateur (F12)

#### Onglet Console
Recherchez ces types d'erreurs :

```javascript
// Erreurs réseau
Failed to fetch
Network Error

// Erreurs JavaScript
TypeError: Cannot read properties
ReferenceError: variable is not defined

// Erreurs API
404 Not Found
500 Internal Server Error
```

#### Onglet Network
Vérifiez les requêtes HTTP :

```
// Requêtes qui échouent
GET /api/episodes → Status: 500 (Rouge)
PUT /api/episodes/123 → Status: 404 (Rouge)

// Requêtes normales
GET /api/episodes → Status: 200 (Vert)
PUT /api/episodes/123 → Status: 200 (Vert)
```

#### Onglet Application
Vérifiez le stockage local :

- localStorage peut contenir des données corrompues
- Effacez si nécessaire : Application > Storage > Clear

### Tests manuels

#### Test API directe

1. **Ouvrez :** `http://localhost:54322/docs`
2. **Testez GET /api/episodes**
3. **Testez GET /api/episodes/{id}**
4. **Testez PUT /api/episodes/{id}**

#### Test de connectivité

```bash
# Test ping du backend
curl http://localhost:54322/api/episodes

# Test avec timeout
curl --max-time 5 http://localhost:54322/api/episodes
```

### Logs détaillés

#### Backend (Python)

Ajoutez plus de logs si nécessaire :

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

#### Frontend (JavaScript)

Activez les logs détaillés dans la console :

```javascript
// Dans la console navigateur
localStorage.debug = '*'
// Puis rechargez la page
```

## Problèmes connus et workarounds

### 1. Port 54321 occupé (Issue #1)

**Problème :** Le port 54321 reste occupé après arrêt du backend
**Workaround :** Utiliser `API_PORT=54322`
**Résolution :** En cours d'investigation

### 2. Configuration ports statique (Issue #2)

**Problème :** Port hardcodé dans la configuration frontend
**Impact :** Nécessite modification manuelle en cas de changement
**Amélioration prévue :** Découverte automatique des ports

### 3. Tests frontend activés (Issue #7 - RÉSOLU)

**Problème précédent :** 26 tests frontend ignorés dans CI/CD
**Résolution :** Tests intégrés dans le pipeline (38 tests total : 12 backend + 26 frontend)
**Status :** ✅ Complètement résolu depuis septembre 2025

## Escalation et support

### Informations à collecter

En cas de problème persistant, rassemblez :

1. **Environnement :**
   - Système d'exploitation
   - Version du navigateur
   - Version de l'application

2. **Logs :**
   - Messages d'erreur console (F12)
   - Logs du terminal backend
   - Logs MongoDB si pertinents

3. **Reproduction :**
   - Étapes pour reproduire le problème
   - Fréquence du problème
   - Épisodes affectés

### Ressources d'aide

- **Issues GitHub :** [Créer une nouvelle issue](https://github.com/castorfou/back-office-lmelp/issues)
- **Documentation technique :** [Guide développeurs](../dev/README.md)
- **Code source :** [Repository GitHub](https://github.com/castorfou/back-office-lmelp)

### Solutions de contournement temporaires

1. **Travail hors ligne :**
   - Copiez le texte dans un éditeur externe
   - Collez-le ensuite quand l'app fonctionne

2. **Sauvegarde manuelle :**
   - Copiez régulièrement votre travail
   - Utilisez Ctrl+S fréquemment

3. **Sessions courtes :**
   - Travaillez par petites sessions
   - Rechargez périodiquement pour éviter les fuites mémoire

---

*Cette documentation de résolution de problèmes évolue en fonction des retours utilisateurs. N'hésitez pas à signaler de nouveaux problèmes pour améliorer cette ressource.*
