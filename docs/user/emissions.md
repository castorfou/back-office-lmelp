# Page Émissions

## Vue d'ensemble

La page **Émissions** présente une vue structurée des émissions du Masque et la Plume, avec l'affichage des livres discutés, des critiques présents, et du résumé détaillé de chaque émission.

## Accès à la page

Depuis le **Dashboard**, cliquez sur la carte **"Émissions"** dans la section "Fonctions disponibles".

L'URL directe est :
```
http://localhost:5173/emissions
```

## Interface

### Sélecteur d'émissions

En haut de page, un menu déroulant permet de sélectionner l'émission à consulter :

```
┌─────────────────────────────────────┐
│ [21/12/2024 - Titre de l'émission ▼]│
└─────────────────────────────────────┘
```

- Les émissions sont **triées par date décroissante** (plus récente en premier)
- Format d'affichage : `DD/MM/YYYY - Titre de l'émission`
- Cliquez sur l'entrée pour ouvrir la liste complète

### Navigation entre émissions

Deux boutons permettent de naviguer rapidement :

- **← Précédent** : Émission plus ancienne
- **Suivant →** : Émission plus récente

**Raccourcis clavier** :
- `←` (Flèche gauche) : Émission précédente
- `→` (Flèche droite) : Émission suivante

### Détails de l'épisode (accordéon)

Un bloc repliable affiche le titre et la description de l'épisode source :

```
▶ Détails de l'épisode (titre et description)
```

Cliquez sur le bloc pour l'ouvrir et voir :

- **Logo RadioFrance** : Cliquable pour accéder à la page de l'épisode
- **Titre** : Titre complet de l'épisode
- **Description** : Description détaillée de l'émission

Le logo RadioFrance est récupéré automatiquement en arrière-plan si disponible.

### Informations de l'émission

La section principale affiche :

#### 📅 Date de diffusion
Format : `DD/MM/YYYY à HH:MM`

#### ⏱️ Durée
Format : `MM min SS sec`

#### 🎙️ Animateur
Nom de l'animateur principal de l'émission

#### 📚 Livres discutés

Liste des livres présentés durant l'émission, avec pour chaque livre :

- **Auteur** (cliquable) → Redirige vers la page détail de l'auteur
- **Titre** (cliquable) → Redirige vers la page détail du livre
- **Éditeur**

Format d'affichage :
```
• Auteur - Titre (Éditeur)
```

#### 👥 Critiques présents

Liste des critiques participant à l'émission :

```
• Nom du critique
```

L'animateur est identifié automatiquement parmi les critiques.

#### 📝 Résumé de l'émission

Affichage formaté du résumé complet de l'émission au format Markdown, incluant :

- Les livres discutés au programme
- Les coups de cœur des critiques
- Les avis détaillés pour chaque livre

Le contenu Markdown est rendu avec mise en forme (titres, listes, gras, italique).

## Navigation dans les détails

### Liens cliquables

Les éléments suivants sont cliquables et redirigent vers leurs pages détails :

- **Noms d'auteurs** → `/auteur/:id`
- **Titres de livres** → `/livre/:id`
- **Logo RadioFrance** → Page de l'épisode sur le site RadioFrance (nouvel onglet)

### URL avec date

Chaque émission possède une URL unique basée sur sa date :

```
/emissions/YYYYMMDD
```

Exemple : `/emissions/20241221` pour l'émission du 21 décembre 2024

Cette URL peut être :
- **Copiée** pour partager un lien direct
- **Mise en favoris** pour accès rapide
- **Utilisée dans le navigateur** pour navigation arrière/avant

## États de chargement

### Chargement initial

Au chargement de la page :
```
Chargement des émissions...
```

### Chargement des détails

Lors de la sélection d'une émission :
```
Chargement des détails de l'émission...
```

### Aucune émission disponible

Si aucune émission n'est trouvée :
```
Aucune émission disponible.
```

### Erreur de chargement

En cas d'erreur, un message explicite s'affiche avec le détail du problème.

## Auto-conversion

Au premier chargement de la page, si aucune émission n'existe en base de données, le système déclenche automatiquement une **conversion des épisodes en émissions**.

Ce processus :
1. Récupère tous les avis critiques existants
2. Crée une émission pour chaque épisode ayant un avis critique
3. Détecte automatiquement l'animateur de chaque émission
4. Ignore les épisodes masqués (`masked=true`)

L'opération est transparente et ne nécessite aucune intervention de l'utilisateur.

## Conseils d'utilisation

### Navigation efficace

- Utilisez les **raccourcis clavier** (← →) pour naviguer rapidement
- Le **sélecteur** permet un accès direct à n'importe quelle émission
- Les **URL avec date** permettent de revenir directement à une émission spécifique

### Exploration des contenus

1. **Consultez le résumé** pour avoir une vue d'ensemble de l'émission
2. **Cliquez sur les auteurs** pour découvrir leurs autres œuvres discutées
3. **Cliquez sur les livres** pour voir dans quels autres épisodes ils sont mentionnés
4. **Utilisez le logo RadioFrance** pour écouter l'émission complète

### Lien avec la validation bibliographique

Depuis la page détail d'un livre, vous pouvez :
- Voir dans quelles émissions le livre a été discuté
- Cliquer sur un épisode pour accéder à la validation bibliographique avec l'épisode pré-sélectionné

## Données techniques

### Structure d'une émission

Chaque émission contient :

- **Référence à l'épisode** : Lien vers l'épisode source
- **Référence à l'avis critique** : Lien vers le résumé markdown
- **Date** : Date de diffusion
- **Durée** : Durée en secondes
- **Animateur** : ID du critique animateur
- **Liste des avis** : Références aux avis individuels (fonctionnalité future)

### Collections MongoDB utilisées

- `emissions` : Collection principale des émissions structurées
- `episodes` : Episodes sources
- `avis_critiques` : Résumés des émissions
- `livres` : Livres discutés
- `auteurs` : Auteurs des livres
- `critiques` : Critiques participant aux émissions

## Limitations actuelles

- Les **pastilles de statut** ne sont pas affichées dans le sélecteur (en attente de définition de leur signification pour les émissions)
- La **liste des avis individuels** (`avis_ids`) n'est pas encore remplie (fonctionnalité future nécessitant le parsing structuré des résumés)

## Support et aide

### Résolution de problèmes

Si l'URL RadioFrance ne s'affiche pas :
- Le fetch est effectué en arrière-plan de manière non bloquante
- Si l'URL n'est pas disponible dans la base, elle sera récupérée automatiquement
- En cas d'échec, un message apparaît dans la console navigateur (F12)

Pour les autres problèmes, consultez le [Guide de résolution de problèmes](troubleshooting.md).

### Ressources complémentaires

- **[Pages de détail](detail-pages.md)** : Guide des pages Auteur et Livre
- **[Extraction Livres et Auteurs](livres-auteurs-extraction.md)** : Validation bibliographique
- **[Guide de l'interface](interface.md)** : Vue d'ensemble de l'application

---

*Page mise à jour pour la version actuelle du Back-Office LMELP.*
