# Guide utilisateur - Back-Office LMELP

## Bienvenue

Le Back-Office LMELP est une application web simple et intuitive pour consulter et modifier les descriptions des épisodes de podcast. Cette interface vous permet de corriger et améliorer les descriptions générées automatiquement.

## Accès à l'application

### URL d'accès

L'application est accessible via le frontend sur le port standard :
```
http://localhost:5173
```

Le backend utilise maintenant une **sélection automatique de port** pour éviter les conflits :
- **Port par défaut** : 54321 (si disponible)
- **Ports alternatifs** : 54322-54350 (sélection automatique si 54321 occupé)
- **Découverte automatique** : Le frontend trouve automatiquement le bon port

### Démarrage simplifié

**Plus de configuration manuelle de ports !** Le système fonctionne automatiquement :

1. **Démarrer le backend** : Se lance automatiquement sur un port libre
2. **Démarrer le frontend** : Trouve automatiquement le backend
3. **Accéder à l'application** : Toujours sur http://localhost:5173

### Prérequis
- Navigateur web moderne (Chrome, Firefox, Safari, Edge)
- Connexion réseau locale au serveur
- **Aucune configuration de port nécessaire** (gestion automatique)

## Vue d'ensemble de l'interface

L'interface se compose de deux parties principales :

```
┌─────────────────────────────────────┐
│           Sélecteur d'épisodes      │
│  [Dropdown: Choisir un épisode ▼]  │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│         Détails de l'épisode        │
│                                     │
│  Titre: Les nouveaux livres de...   │
│  Date: 2025-08-03                   │
│  Type: livres                       │
│  Durée: 51:36                       │
│                                     │
│  Description originale:             │
│  ┌─────────────────────────────────┐ │
│  │ [Texte en lecture seule]       │ │
│  └─────────────────────────────────┘ │
│                                     │
│  Description corrigée:              │
│  ┌─────────────────────────────────┐ │
│  │ [Zone d'édition]               │ │
│  │                                │ │
│  └─────────────────────────────────┘ │
│                                     │
│  💾 Sauvegardé automatiquement      │
└─────────────────────────────────────┘
```

## Utilisation pas à pas

### 1. Sélectionner un épisode

1. **Ouvrez** le sélecteur d'épisodes en haut de la page
2. **Parcourez** la liste des épisodes disponibles
3. **Cliquez** sur l'épisode que vous souhaitez modifier

📋 *La liste affiche le titre complet de chaque épisode avec la date*

### 2. Consulter les informations

Une fois l'épisode sélectionné, vous verrez :

- **Titre complet** de l'épisode
- **Date de diffusion**
- **Type d'émission** (livres, cinéma, musique, etc.)
- **Durée** au format MM:SS
- **URL** de l'épisode original
- **Transcription** complète (si disponible)

### 3. Modifier la description

#### Description originale
- Zone **en lecture seule**
- Contient la description automatique générée
- Sert de référence pour vos corrections

#### Description corrigée
- Zone **éditable** où vous pouvez saisir vos modifications
- **Sauvegarde automatique** dès que vous arrêtez de taper
- **Indicateur visuel** de l'état de sauvegarde

#### Comment modifier

1. **Cliquez** dans la zone "Description corrigée"
2. **Tapez** votre version améliorée
3. **Formatez** le texte (passages à la ligne, ponctuation)
4. **Attendez** la confirmation de sauvegarde automatique

## Fonctionnalités avancées

### Sauvegarde automatique

L'application sauvegarde automatiquement vos modifications :

- ⏳ **"Sauvegarde en cours..."** : Vos changements sont en train d'être enregistrés
- ✅ **"Sauvegardé"** : Vos modifications sont confirmées
- ❌ **"Erreur de sauvegarde"** : Un problème est survenu (voir [Résolution des problèmes](troubleshooting.md))

### Formatage du texte

Vous pouvez utiliser :
- **Passages à la ligne** : Appuyez sur Entrée
- **Espaces multiples** : Pour l'alignement
- **Tirets** : Pour structurer les listes
- **Signes de ponctuation** : Points, virgules, deux-points

### Protection mémoire

L'application surveille automatiquement l'utilisation mémoire :

- **Surveillance continue** : Monitoring invisible en arrière-plan
- **Alertes préventives** : Avertissements si consommation élevée
- **Protection d'urgence** : Rechargement automatique si nécessaire

🛡️ *Cette protection évite les plantages et garantit une expérience stable*

## Conseils d'utilisation

### Bonnes pratiques

✅ **À faire :**
- Corriger les erreurs de transcription automatique
- Ajouter de la ponctuation pour la lisibilité
- Structurer avec des passages à la ligne
- Conserver les informations importantes (durée, invités)

❌ **À éviter :**
- Supprimer complètement le contenu original
- Ajouter des informations non présentes dans l'audio
- Utiliser des caractères spéciaux complexes

### Optimisation du workflow

1. **Lisez d'abord** la description originale complètement
2. **Écoutez l'extrait** si nécessaire (via l'URL fournie)
3. **Corrigez progressivement** par petites sections
4. **Vérifiez** que la sauvegarde est confirmée avant de passer au suivant

## Types d'épisodes

L'application gère différents types d'émissions :

### 📚 Livres
- Critiques littéraires
- Nouveautés éditoriales
- Interviews d'auteurs

### 🎬 Cinéma
- Critiques de films
- Actualité cinématographique
- Rencontres avec des réalisateurs

### 🎵 Musique
- Nouveaux albums
- Concerts et festivals
- Interviews d'artistes

### 🎭 Spectacles
- Théâtre
- Danse
- Arts vivants

## Données affichées

### Métadonnées techniques

- **Fichier audio** : Nom du fichier source
- **URL** : Lien vers l'épisode en ligne
- **Durée** : Temps total en secondes et format lisible
- **Date** : Date de diffusion originale

### Contenu éditorial

- **Titre** : Titre complet de l'émission
- **Description** : Résumé automatique à corriger
- **Transcription** : Texte intégral généré automatiquement

## Navigation

### Changement d'épisode

Pour passer à un autre épisode :

1. **Utilisez le sélecteur** en haut de page
2. **Choisissez** un nouvel épisode
3. **Confirmez** que vos modifications précédentes sont sauvegardées

⚠️ *Les modifications non sauvegardées peuvent être perdues*

### Rechargement de page

En cas de problème :

1. **Rechargez** la page (F5 ou Ctrl+R)
2. **Vérifiez** que le serveur backend fonctionne
3. **Sélectionnez** de nouveau votre épisode

## Support et aide

### Ressources disponibles

- **[Guide de l'interface](interface.md)** : Détails sur chaque élément
- **[Gestion des épisodes](episodes.md)** : Fonctionnalités avancées
- **[Résolution de problèmes](troubleshooting.md)** : Solutions aux problèmes courants

### Contact support

En cas de problème persistant :

1. **Consultez** le guide de résolution de problèmes
2. **Vérifiez** les logs de la console navigateur (F12)
3. **Contactez** l'équipe technique avec les détails de l'erreur

---

*Cette documentation correspond à la version actuelle du Back-Office LMELP. Pour les développeurs, consultez la [documentation technique](../dev/README.md).*
