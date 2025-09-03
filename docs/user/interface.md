# Guide de l'interface - Back-Office LMELP

## Vue d'ensemble

L'interface du Back-Office LMELP est conçue pour être simple et efficace. Elle se compose de deux sections principales qui s'affichent de manière responsive selon la taille de votre écran.

## Anatomie de l'interface

### Header (En-tête)

```
┌─────────────────────────────────────────────────────────────┐
│  🎧 Back-Office LMELP                                      │
│  ─────────────────────────────────────────────────────────  │
│                                                             │
│  Sélectionnez un épisode :                                  │
│  [Choisir un épisode                               ▼]      │
└─────────────────────────────────────────────────────────────┘
```

#### Éléments de l'en-tête

- **Logo/Titre** : Identification de l'application
- **Sélecteur d'épisodes** : Menu déroulant pour choisir l'épisode à modifier

### Zone principale (Episode Editor)

```
┌─────────────────────────────────────────────────────────────┐
│  📝 Détails de l'épisode                                   │
│  ═══════════════════════════════════════════════════════════ │
│                                                             │
│  🏷️ Titre:                                                  │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ Les nouveaux livres de Simon Chevrier, Sylvain Tesson  │ │
│  │ [Zone éditable avec curseur]                           │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                             │
│  Date: 2025-08-03T10:59:59.000+00:00                      │
│  Type: livres                        Durée: 00:51:36       │
│                                                             │
│  URL: https://proxycast.radiofrance.fr/...                 │
│  Fichier: 2025/14007-03.08.2025-ITEMA_24209925...         │
│                                                             │
│  ───────────────────────────────────────────────────────── │
│                                                             │
│  📄 Description originale                                   │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ durée : 00:51:36 - Le Masque et la Plume - par :       │ │
│  │ Laurent Goumarre - Un critique littéraire et           │ │
│  │ productrice chez France Inter, littéraire, Hubert      │ │
│  │ Artus : Journaliste et chroniqueur Guillaume Gault     │ │
│  │ [Zone en lecture seule]                                │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                             │
│  ✏️ Description corrigée                                    │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ durée : 00:51:36 - Le Masque et la Plume - par :       │ │
│  │ Laurent Goumarre -                                      │ │
│  │                                                         │ │
│  │ Chronique littéraire et productrice chez France Inter, │ │
│  │ littéraire, Hubert Artus : Journaliste et chroniqueur  │ │
│  │ Guillaume Gault                                         │ │
│  │ [Zone éditable avec curseur actif]                     │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                             │
│  💾 Sauvegardé                                             │
│                                                             │
│  📝 Transcription                                          │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ France Inter Le masque et la plume Un tour du monde    │ │
│  │ sur des stacks, une chronique littéraire de Laurent... │ │
│  │ [Transcription complète en lecture seule]              │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Composants détaillés

### 1. Sélecteur d'épisodes

#### Apparence
- **Type** : Menu déroulant (dropdown)
- **Placeholder** : "Choisir un épisode"
- **Contenu** : Titres complets des épisodes
- **Tri** : Chronologique (plus récents en premier)

#### Utilisation
1. **Cliquez** sur le menu déroulant
2. **Faites défiler** la liste si nécessaire
3. **Sélectionnez** l'épisode souhaité
4. **Confirmez** en cliquant sur votre choix

#### États visuels
- **Inactif** : Bordure grise, texte placeholder
- **Ouvert** : Bordure bleue, liste déroulante visible
- **Sélectionné** : Titre de l'épisode affiché

### 2. Métadonnées de l'épisode

#### Informations affichées

| Champ | Format | Exemple | Description |
|-------|--------|---------|-------------|
| **Titre** | Texte libre éditable | "Les nouveaux livres de Simon Chevrier..." | Titre complet de l'épisode (modifiable) |
| **Date** | ISO 8601 | "2025-08-03T10:59:59.000+00:00" | Date/heure de diffusion |
| **Type** | Catégorie | "livres" | Type d'émission |
| **Durée** | MM:SS | "00:51:36" | Durée totale de l'épisode |
| **URL** | Lien | "https://proxycast.radiofrance.fr/..." | Lien vers l'audio original |
| **Fichier** | Chemin | "2025/14007-03.08.2025-ITEMA..." | Nom du fichier audio |

#### Style visuel
- **Titre** : Police grande, gras
- **Métadonnées** : Police normale, gris foncé
- **Liens** : Couleur bleue, soulignés au survol

### 3. Description originale

#### Caractéristiques
- **Zone** : Textarea en lecture seule
- **Fond** : Gris clair (#f5f5f5)
- **Bordure** : Fine, gris clair
- **Curseur** : Non éditable (interdit)
- **Défilement** : Vertical si contenu long

#### Contenu type
```
durée : 00:51:36 - Le Masque et la Plume - par : Laurent Goumarre - Un
critique littéraire et productrice chez France Inter, littéraire, Hubert
Artus : Journaliste et chroniqueur Guillaume Gault
```

### 4. Éditeur de titre

#### Caractéristiques
- **Type** : Input text éditable
- **Fond** : Blanc
- **Bordure** : Bleue quand active, grise sinon
- **Curseur** : Clignotant quand sélectionné
- **Largeur** : Pleine largeur
- **Sauvegarde** : Automatique avec debounce de 2 secondes

#### États d'interaction

**État normal :**
```
┌─────────────────────────────────────┐
│ Les nouveaux livres de Simon...     │
│ [Titre éditable]                   │
└─────────────────────────────────────┘
```

**État focus :**
```
┌═════════════════════════════════════┐  ← Bordure bleue épaisse
║ Les nouveaux livres de Simon...     ║
║ [Curseur actif]                    ║
└═════════════════════════════════════┘
```

#### Fonctionnalités d'édition

- **Saisie libre** : Tout caractère accepté (ligne unique)
- **Sélection de texte** : Clic-glisser ou Shift+flèches
- **Copier/coller** : Ctrl+C / Ctrl+V
- **Annuler/refaire** : Ctrl+Z / Ctrl+Y
- **Sauvegarde automatique** : Après 2 secondes d'inactivité

### 5. Description corrigée

#### Caractéristiques
- **Zone** : Textarea éditable
- **Fond** : Blanc
- **Bordure** : Bleue quand active, grise sinon
- **Curseur** : Clignotant quand sélectionnée
- **Auto-resize** : S'adapte au contenu

#### États d'interaction

**État normal :**
```
┌─────────────────────────────────────┐
│ Description corrigée...             │
│ [Curseur clignotant]               │
└─────────────────────────────────────┘
```

**État focus :**
```
┌═════════════════════════════════════┐  ← Bordure bleue épaisse
║ Description corrigée...             ║
║ [Curseur actif]                    ║
└═════════════════════════════════════┘
```

#### Fonctionnalités d'édition

- **Saisie libre** : Tout caractère accepté
- **Passages à la ligne** : Entrée pour nouvelle ligne
- **Sélection de texte** : Clic-glisser ou Shift+flèches
- **Copier/coller** : Ctrl+C / Ctrl+V
- **Annuler/refaire** : Ctrl+Z / Ctrl+Y

### 6. Indicateur de sauvegarde

#### États possibles

**💾 Sauvegardé**
- **Couleur** : Vert
- **Icône** : Disquette
- **Signification** : Modifications enregistrées

**⏳ Sauvegarde en cours...**
- **Couleur** : Orange/jaune
- **Icône** : Sablier
- **Signification** : Envoi vers le serveur

**❌ Erreur de sauvegarde**
- **Couleur** : Rouge
- **Icône** : Croix
- **Signification** : Échec de l'enregistrement

#### Logique de sauvegarde

```
Utilisateur tape → Délai 1 seconde → Sauvegarde automatique
                     ↓
          "Sauvegarde en cours..."
                     ↓
         Succès: "Sauvegardé" / Échec: "Erreur"
```

### 7. Zone de transcription

#### Caractéristiques
- **Type** : Zone de texte étendue
- **Mode** : Lecture seule
- **Style** : Fond très clair, texte petit
- **Défilement** : Vertical avec scrollbar
- **Hauteur** : Limitée avec overflow

#### Utilisation
- **Référence** pour comprendre le contenu audio
- **Aide** pour corriger la description
- **Source** d'informations détaillées non résumées

## Responsive design

### Écran large (> 1024px)

```
┌─────────────────────┬─────────────────────┐
│                     │                     │
│   Sélecteur        │    Métadonnées     │
│                     │                     │
├─────────────────────┼─────────────────────┤
│                     │                     │
│   Description      │    Description      │
│   originale        │    corrigée         │
│                     │                     │
├─────────────────────┴─────────────────────┤
│                                           │
│            Transcription                  │
│                                           │
└───────────────────────────────────────────┘
```

### Écran moyen (768px - 1024px)

```
┌───────────────────────────────────────────┐
│              Sélecteur                    │
├───────────────────────────────────────────┤
│              Métadonnées                  │
├───────────────────────────────────────────┤
│           Description originale           │
├───────────────────────────────────────────┤
│           Description corrigée            │
├───────────────────────────────────────────┤
│             Transcription                 │
└───────────────────────────────────────────┘
```

### Écran mobile (< 768px)

```
┌─────────────────────┐
│     Sélecteur       │
├─────────────────────┤
│    Métadonnées      │
│     (compactes)     │
├─────────────────────┤
│   Description       │
│    originale        │
├─────────────────────┤
│   Description       │
│    corrigée         │
├─────────────────────┤
│   Transcription     │
│    (réduite)        │
└─────────────────────┘
```

## Couleurs et thème

### Palette de couleurs

| Usage | Couleur | Code | Exemple |
|-------|---------|------|---------|
| **Primaire** | Bleu | #007bff | Bordures actives, liens |
| **Succès** | Vert | #28a745 | Sauvegarde réussie |
| **Attention** | Orange | #ffc107 | Sauvegarde en cours |
| **Erreur** | Rouge | #dc3545 | Erreurs de sauvegarde |
| **Gris clair** | #f8f9fa | Fonds inactifs |
| **Gris foncé** | #6c757d | Textes secondaires |
| **Noir** | #212529 | Textes principaux |

### Typographie

- **Famille** : -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto
- **Taille base** : 14px
- **Taille titre** : 18px (bold)
- **Taille métadonnées** : 12px
- **Interligne** : 1.4

## Animations et transitions

### Effets visuels

- **Focus** : Transition bordure 0.2s
- **Sauvegarde** : Fade in/out de l'indicateur
- **Dropdown** : Ouverture/fermeture fluide
- **Hover** : Survol des liens et boutons

### Performance

- **Pas d'animations** lors de la saisie
- **Debounce** sur la sauvegarde (1 seconde)
- **Optimisation** des re-renders Vue.js

## Accessibilité

### Conformité

- **Labels** : Tous les champs ont des labels appropriés
- **Contraste** : Respect des ratios WCAG 2.1 AA
- **Navigation clavier** : Tab/Shift+Tab fonctionnent
- **Lecteurs d'écran** : Attributs ARIA présents

### Raccourcis clavier

| Combinaison | Action |
|-------------|--------|
| **Tab** | Navigation entre les champs |
| **Entrée** | Ouvrir/fermer le sélecteur |
| **Flèches** | Navigation dans le dropdown |
| **Échap** | Fermer le dropdown |
| **Ctrl+S** | Forcer la sauvegarde |

## Cas d'usage d'interface

### Nouveau visiteur

1. **Arrivée** → Page avec sélecteur vide
2. **Clic sélecteur** → Liste des épisodes apparaît
3. **Choix épisode** → Interface complète s'affiche
4. **Lecture description** → Comprend le contenu
5. **Édition** → Commence les corrections
6. **Sauvegarde** → Confirmation visuelle

### Utilisateur expérimenté

1. **Arrivée** → Sélection rapide d'épisode
2. **Édition directe** → Modifications expertes
3. **Navigation rapide** → Changement d'épisode fréquent
4. **Workflow optimisé** → Utilisation des raccourcis

### Cas d'erreur

1. **Serveur inaccessible** → Message d'erreur réseau
2. **Sauvegarde échouée** → Indicateur rouge avec retry
3. **Épisode inexistant** → Message "Épisode introuvable"
4. **Connexion perdue** → Notification de reconnexion
