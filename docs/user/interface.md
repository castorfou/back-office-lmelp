# Guide de l'interface - lmelp

## Vue d'ensemble

L'interface de lmelp est conçue pour être simple et efficace. Elle se compose de deux sections principales qui s'affichent de manière responsive selon la taille de votre écran.

## Anatomie de l'interface

### Header (En-tête)

```
┌─────────────────────────────────────────────────────────────┐
│  🎧 lmelp                                                  │
│  ─────────────────────────────────────────────────────────  │
│                                                             │
│  🔍 Rechercher...                                          │
│  [Rechercher auteurs, livres, épisodes...          ]      │
│                                                             │
│  Sélectionnez un épisode :                                  │
│  [Choisir un épisode                               ▼]      │
└─────────────────────────────────────────────────────────────┘
```

#### Éléments de l'en-tête

- **Logo/Titre** : Identification de l'application
- **Moteur de recherche** : Zone de recherche textuelle multi-collections (voir section dédiée)
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
- **Contenu** : Titres complets des épisodes avec indicateurs de statut
- **Tri** : Chronologique (plus récents en premier)
- **Hauteur** : Affiche environ 8 épisodes simultanément avec défilement

#### Indicateurs visuels de statut

Chaque épisode dans la liste affiche une pastille de couleur indiquant son statut :

- **🟢 Pastille verte** : Épisode traité - tous les livres ont été validés et intégrés dans les collections MongoDB
- **⚪ Pastille grise** : Épisode non traité - aucun livre n'a encore été analysé ou intégré
- **🔴 Pastille rouge** : Épisode avec problèmes - certains livres ont des données incomplètes nécessitant une révision manuelle

#### Utilisation
1. **Cliquez** sur le menu déroulant
2. **Faites défiler** la liste si nécessaire (environ 8 épisodes visibles)
3. **Sélectionnez** l'épisode souhaité
4. **Confirmez** en cliquant sur votre choix

La liste se centre automatiquement sur l'épisode sélectionné lors de la ré-ouverture du menu déroulant.

#### États visuels
- **Inactif** : Bordure grise, texte placeholder
- **Ouvert** : Bordure bleue, liste déroulante visible
- **Sélectionné** : Titre de l'épisode affiché avec sa pastille de statut
- **Option survolée** : Fond gris clair (#f5f5f5)
- **Option sélectionnée** : Fond bleu clair (#e8edff)

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

---

## Moteur de recherche textuelle

**✨ NOUVEAU** - Recherche multi-collections (Issues #49 + #68)

### Vue d'ensemble

Le moteur de recherche permet de trouver rapidement du contenu dans toutes les collections MongoDB : auteurs, livres, épisodes et éditeurs.

### Apparence et positionnement

```
┌─────────────────────────────────────────────────────────────┐
│  🔍 Rechercher...                                          │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ camus                                       [×]        │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
│  📚 AUTEURS (1)                                            │
│  • Albert Camus                                            │
│                                                             │
│  📖 LIVRES (3/15)                                          │
│  • Albert Camus - L'Étranger                               │
│  • Albert Camus - La Peste                                 │
│  • Albert Camus - Le Mythe de Sisyphe                      │
│                                                             │
│  🎙️ ÉPISODES (5/23)                                       │
│  • Épisode sur Camus (2025-08-03)                         │
│    ...discussion sur Albert Camus et son œuvre majeure... │
│                                                             │
│  🏢 ÉDITEURS (2)                                           │
│  • Gallimard                                               │
│  • Éditions de Minuit                                      │
└─────────────────────────────────────────────────────────────┘
```

### Caractéristiques

#### Zone de saisie
- **Type** : Input text avec debouncing (300ms)
- **Placeholder** : "Rechercher auteurs, livres, épisodes..."
- **Minimum** : 3 caractères pour déclencher la recherche
- **Icône** : 🔍 (loupe) à gauche
- **Bouton clear** : × (croix) pour effacer rapidement
- **Raccourci** : ESC pour effacer la recherche

#### États visuels

**Inactif** :
```
┌─────────────────────────────────────────┐
│ 🔍 Rechercher...                    │
└─────────────────────────────────────────┘
```

**En saisie (< 3 caractères)** :
```
┌─────────────────────────────────────────┐
│ 🔍 ca|                           [×]    │
└─────────────────────────────────────────┘
(Pas de résultats affichés)
```

**Recherche active (≥ 3 caractères)** :
```
┌─────────────────────────────────────────┐
│ 🔍 camus|                        [×]    │
└─────────────────────────────────────────┘
⏳ Recherche en cours...
```

**Résultats affichés** :
```
┌─────────────────────────────────────────┐
│ 🔍 camus                         [×]    │
└─────────────────────────────────────────┘
Résultats organisés par catégorie ↓
```

### Catégories de résultats

#### 📚 AUTEURS
- **Format d'affichage** : Nom complet de l'auteur
- **Exemple** : "Albert Camus"
- **Compteur** : `(N)` où N = nombre de résultats
- **Action au clic** : (À implémenter) Afficher les livres de l'auteur

#### 📖 LIVRES
- **Format d'affichage** : "Auteur - Titre" (Issue #68)
- **Exemple** : "Catherine Millet - Simone Emonet"
- **Compteur** : `(N/M)` où N = affichés, M = total
- **Surlignage** : Terme recherché en jaune
- **Métadonnées** : Éditeur affiché en gris
- **Action au clic** : (À implémenter) Afficher les épisodes du livre

#### 🎙️ ÉPISODES
- **Format d'affichage** : Titre + Date + Contexte
- **Exemple** : "Épisode sur Camus (2025-08-03)"
- **Contexte** : 10 mots avant/après le terme trouvé
- **Compteur** : `(N/M)` où N = affichés, M = total
- **Surlignage** : Terme recherché en jaune
- **Action au clic** : Charge l'épisode dans l'éditeur

#### 🏢 ÉDITEURS
- **Format d'affichage** : Nom de l'éditeur
- **Exemple** : "Gallimard"
- **Compteur** : `(N)` où N = nombre de résultats
- **Action au clic** : (À implémenter) Afficher les livres de l'éditeur

### Fonctionnalités

#### Debouncing intelligent
- **Délai** : 300ms après la dernière frappe
- **Avantage** : Évite les requêtes excessives au serveur
- **Indicateur** : Spinner pendant l'attente

#### Surlignage des résultats
- **Style** : Fond jaune (#fff3cd), texte foncé (#856404)
- **Gras** : Texte surligné en gras (font-weight: 700)
- **Arrondi** : Coins légèrement arrondis (3px)
- **Exemple** : "Albert **Camus**" (Camus surligné)

#### Extraction de contexte (épisodes)
- **Méthode** : 10 mots avant et après le terme trouvé
- **Ellipses** : "..." si contexte tronqué
- **Exemple** : "...discussion sur Albert Camus et son œuvre..."

#### Compteurs intelligents
- **Format simple** : `(3)` = 3 résultats
- **Format avec total** : `(5/23)` = 5 affichés sur 23 totaux
- **Indication** : Aide à comprendre si plus de résultats existent

#### Effacement rapide
- **Bouton [×]** : Clic pour effacer la recherche
- **Touche ESC** : Raccourci clavier pour effacer
- **Résultat** : Champ vide + résultats cachés

### Messages d'état

#### Pas de résultats
```
┌─────────────────────────────────────────┐
│ 🔍 aucunresultat             [×]        │
└─────────────────────────────────────────┘
Aucun résultat trouvé pour "aucunresultat"
```

#### Erreur réseau
```
┌─────────────────────────────────────────┐
│ 🔍 camus                     [×]        │
└─────────────────────────────────────────┘
❌ Erreur lors de la recherche. Réessayez.
```

#### Recherche trop courte
```
┌─────────────────────────────────────────┐
│ 🔍 ca|                       [×]        │
└─────────────────────────────────────────┘
(Aucun message - recherche non déclenchée)
```

### Workflow utilisateur

#### Recherche simple
1. **Cliquer** dans la zone de recherche
2. **Taper** au moins 3 caractères
3. **Attendre** 300ms (debounce automatique)
4. **Visualiser** les résultats organisés par catégorie
5. **Cliquer** sur un résultat pour l'ouvrir
6. **Effacer** avec [×] ou ESC pour nouvelle recherche

#### Recherche itérative
1. **Taper** un terme large (ex: "camus")
2. **Affiner** en ajoutant des mots (ex: "camus étranger")
3. **Réduire** le nombre de résultats progressivement
4. **Trouver** exactement ce qui est recherché

### Performance et optimisation

#### Limite par défaut
- **Résultats affichés** : 10 par catégorie
- **Total possible** : Illimité (compteur indique le total)
- **Requête backend** : `limit=10` par défaut

#### Cache et réactivité
- **Pas de cache** : Chaque recherche interroge le serveur
- **Temps réponse** : Généralement < 500ms
- **Indicateur** : Spinner si > 200ms

### Accessibilité

#### Navigation clavier
- **Tab** : Accéder à la zone de recherche
- **Entrée** : Forcer la recherche (bypass debounce)
- **ESC** : Effacer la recherche
- **Flèches** : (À implémenter) Naviguer dans les résultats

#### Lecteurs d'écran
- **Label** : "Rechercher auteurs, livres, épisodes"
- **ARIA** : `role="search"` sur la zone
- **Statut** : Annonce du nombre de résultats

### Cas d'usage

#### Trouver un auteur
```
Utilisateur tape : "houelle"
Résultats :
📚 AUTEURS (1)
• Michel Houellebecq
```

#### Trouver un livre
```
Utilisateur tape : "simone"
Résultats :
📖 LIVRES (1)
• Catherine Millet - Simone Emonet
```

#### Trouver un épisode
```
Utilisateur tape : "littérature française"
Résultats :
🎙️ ÉPISODES (3/12)
• Les nouveaux livres de... (2025-08-03)
  ...chronique de littérature française...
```

### Améliorations futures

- [ ] Navigation clavier dans les résultats (flèches haut/bas)
- [ ] Actions au clic pour auteurs et éditeurs
- [ ] Filtres par catégorie (auteurs uniquement, etc.)
- [ ] Historique des recherches
- [ ] Suggestions de recherche (autocomplétion)
- [ ] Export des résultats
- [ ] Recherche avancée avec opérateurs booléens

### Notes techniques

**Implémentation** :
- **Backend** : Endpoint `/api/search` (GET)
- **Frontend** : Composant `TextSearchEngine.vue`
- **Tests** : 11 tests frontend + 31 tests backend
- **Documentation** : Issues #49 (base) + #68 (extension)

**Collections interrogées** :
1. `auteurs` - Recherche sur `nom`
2. `livres` - Recherche sur `titre` et `editeur`
3. `episodes` - Recherche sur `titre`, `description`, `transcription`
4. `avis_critiques` - Recherche d'éditeurs
