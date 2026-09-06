# Gestion des épisodes - Back-Office LMELP

## Vue d'ensemble

La gestion des épisodes est la fonctionnalité centrale du Back-Office LMELP. Elle vous permet de consulter, modifier et améliorer les titres et descriptions des épisodes de podcast de manière intuitive et efficace.

## Ajout d'un nouvel épisode

Un épisode peut être ajouté à la base de deux façons :

- **Automatiquement** via la synchronisation du flux RSS (voir `docs/user/rss-monitoring.md`) — détecte les nouveaux épisodes "livres" de plus de 15 minutes et télécharge leur fichier audio.
- Le workflow de correction (titre, description, structuration) décrit ci-dessous s'applique de la même façon, quelle que soit l'origine de l'épisode.

## Cycle de vie d'un épisode

### 1. État initial (Non corrigé)

```
📥 Épisode importé
├── Titre automatique généré
├── Description automatique générée
├── Transcription automatique créée
├── Métadonnées extraites
└── Status: aucun champ *_origin (épisode non modifié)
```

### 2. État en cours de modification

```
✏️ Épisode en édition
├── Titre: version en cours d'édition
├── Titre_origin: version originale automatiquement sauvegardée
├── Description: version en cours d'édition
├── Description_origin: version originale automatiquement sauvegardée
├── Sauvegarde automatique active
└── Status: présence des champs *_origin indique les modifications
```

### 3. État finalisé

```
✅ Épisode corrigé
├── Titre: version corrigée finalisée (affichage principal)
├── Titre_origin: version originale préservée
├── Description: version corrigée finalisée (affichage principal)
├── Description_origin: version originale préservée
├── Historique des modifications (futur)
└── Status: champs *_origin présents, versions corrigées dans champs principaux
```

## Comment fonctionnent les corrections

### Logique de sauvegarde des modifications

Lorsque vous modifiez un titre ou une description pour la première fois :

1. **Votre version corrigée** remplace directement le contenu affiché
2. **La version originale** est automatiquement sauvegardée dans un champ de sauvegarde
3. **Les autres applications** (moteur de recherche, site principal) voient automatiquement votre version corrigée

### Avantages de cette approche

✅ **Automatique** : Vos corrections sont immédiatement visibles partout
✅ **Sécurisé** : L'original est toujours préservé
✅ **Simple** : Une seule version à maintenir (la vôtre)
✅ **Réversible** : Possibilité de revenir à l'original si nécessaire

### Comportement lors des modifications

**Première correction :**
```
Avant : titre = "Titre avec fautes"
Après : titre = "Titre corrigé"
        titre_origin = "Titre avec fautes" (automatique)
```

**Corrections suivantes :**
```
Avant : titre = "Titre corrigé"
        titre_origin = "Titre avec fautes"
Après : titre = "Titre encore mieux corrigé"
        titre_origin = "Titre avec fautes" (préservé)
```

## Types d'épisodes

L'application gère plusieurs catégories d'émissions :

### 📚 Livres

**Caractéristiques :**
- Critiques littéraires
- Nouveautés éditoriales
- Interviews d'auteurs
- Chroniques de lecture

**Exemple de contenu :**
```
Titre: "Les nouveaux livres de Simon Chevrier, Sylvain Tesson, Gaël Octavia"
Type: livres
Description originale: "durée : 00:51:36 - Le Masque et la Plume - par : Laurent Goumarre - Un critique littéraire..."

Description corrigée suggérée:
"durée : 00:51:36 - Le Masque et la Plume - par : Laurent Goumarre
Chronique littéraire présentée par Laurent Goumarre avec :
- Simon Chevrier : Nouveau roman
- Sylvain Tesson : Dernière publication
- Gaël Octavia : Récit contemporain"
```

### 🎬 Cinéma

**Caractéristiques :**
- Critiques de films récents
- Analyses cinématographiques
- Interviews de réalisateurs
- Actualité des festivals

**Bonnes pratiques de correction :**
- Séparer les différents films abordés
- Clarifier les noms des réalisateurs
- Distinguer critiques et actualités

### 🎵 Musique

**Caractéristiques :**
- Nouveaux albums
- Concerts et festivals
- Interviews d'artistes
- Chroniques musicales

**Éléments à structurer :**
- Noms des artistes/groupes
- Titres des albums
- Genres musicaux
- Événements mentionnés

### 🎭 Spectacles

**Caractéristiques :**
- Théâtre contemporain et classique
- Danse et ballet
- Arts du cirque
- Performances artistiques

**Points d'attention :**
- Noms des compagnies
- Lieux de représentation
- Metteurs en scène/chorégraphes
- Dates de programmation

## Techniques de correction

### Problèmes courants de transcription automatique

#### 1. Ponctuation manquante

**Avant :**
```
Laurent Goumarre Un critique littéraire et productrice chez France Inter littéraire Hubert Artus Journaliste et chroniqueur Guillaume Gault
```

**Après :**
```
Laurent Goumarre - Un critique littéraire et productrice chez France Inter.
Littéraire, Hubert Artus : Journaliste et chroniqueur.
Guillaume Gault
```

#### 2. Noms mal interprétés

**Avant :**
```
Simon chevrier sylvain tesson gaël octavia
```

**Après :**
```
Simon Chevrier, Sylvain Tesson, Gaël Octavia
```

#### 3. Structure confuse

**Avant :**
```
durée : 00:51:36 - Le Masque et la Plume - par : Laurent Goumarre - Un critique littéraire et productrice chez France Inter, littéraire, Hubert Artus : Journaliste et chroniqueur Guillaume Gault
```

**Après :**
```
durée : 00:51:36 - Le Masque et la Plume - par : Laurent Goumarre

Chronique littéraire présentée par Laurent Goumarre.
Invités :
- Critique littéraire et productrice chez France Inter
- Hubert Artus : Journaliste et chroniqueur
- Guillaume Gault
```

### Méthodes de restructuration

#### 1. Approche par sections

```
[En-tête]
durée : MM:SS - Nom de l'émission - par : Présentateur

[Contenu principal]
Description du sujet principal

[Invités/Intervenants]
- Nom : Fonction
- Nom : Fonction

[Œuvres/Sujets abordés]
- Titre 1 : Description
- Titre 2 : Description
```

#### 2. Approche narrative

```
durée : MM:SS - Nom de l'émission - par : Présentateur

Dans cette émission, [Présentateur] reçoit [invités] pour parler de [sujet principal].
Au programme : [liste des sujets abordés].

[Détails supplémentaires si nécessaire]
```

#### 3. Approche liste structurée

```
📺 Émission : [Nom]
👤 Présentateur : [Nom]
⏱️ Durée : [MM:SS]

📋 Au programme :
• [Sujet 1]
• [Sujet 2]
• [Sujet 3]

👥 Invités :
• [Nom] - [Fonction]
• [Nom] - [Fonction]
```

## Workflow de correction recommandé

### Phase 1 : Analyse (2-3 minutes)

1. **Lecture** du titre original
2. **Lecture complète** de la description originale
3. **Consultation** de la transcription si nécessaire
4. **Écoute rapide** de l'épisode si des clarifications sont nécessaires
5. **Identification** des éléments clés :
   - Titre principal et sujets abordés
   - Présentateur principal
   - Invités et leurs fonctions
   - Sujets/œuvres abordés
   - Structure de l'émission

### Phase 2 : Correction du titre (1-2 minutes)

1. **Amélioration** du titre si nécessaire :
   - Correction des fautes d'orthographe
   - Clarification des noms propres
   - Amélioration de la lisibilité
   - Ajout d'informations manquantes importantes
2. **Sauvegarde automatique** avec debounce de 2 secondes

### Phase 3 : Structuration de la description (5-7 minutes)

1. **Conservation** des informations essentielles (durée, émission, présentateur)
2. **Réorganisation** en sections logiques
3. **Correction** de l'orthographe et de la ponctuation
4. **Clarification** des noms propres et titres
5. **Ajout** de passages à la ligne pour la lisibilité

### Phase 4 : Finalisation (1-2 minutes)

1. **Relecture** complète du titre et de la description corrigés
2. **Vérification** de la cohérence avec l'original
3. **Contrôle qualité** :
   - Orthographe correcte
   - Ponctuation appropriée
   - Structure claire
   - Informations préservées
4. **Confirmation** de la sauvegarde automatique

## Bonnes pratiques par type de contenu

### Émissions littéraires

✅ **À faire :**
- Mettre en évidence les titres d'œuvres
- Clarifier les noms d'auteurs
- Distinguer les genres littéraires
- Séparer les différents livres présentés

❌ **À éviter :**
- Mélanger les œuvres et leurs auteurs
- Omettre les éditeurs quand mentionnés
- Négliger la chronologie de présentation

### Émissions cinéma

✅ **À faire :**
- Séparer les films par paragraphes
- Préciser réalisateurs et acteurs principaux
- Indiquer les dates de sortie si mentionnées
- Distinguer films français et étrangers

❌ **À éviter :**
- Confondre acteurs et réalisateurs
- Mélanger films récents et classiques
- Omettre les festivals mentionnés

### Émissions musicales

✅ **À faire :**
- Clarifier artistes/groupes vs albums
- Préciser les genres musicaux
- Séparer les concerts des sorties d'albums
- Mentionner les labels si pertinent

❌ **À éviter :**
- Confondre noms d'artistes similaires
- Omettre les featuring importants
- Négliger les lieux de concert

## Fonctionnalités avancées

### Recherche dans la transcription

La transcription complète vous aide à :

1. **Retrouver** des passages spécifiques
2. **Vérifier** l'orthographe des noms propres
3. **Comprendre** le contexte des mentions
4. **Identifier** des éléments omis dans la description

**Astuce :** Utilisez Ctrl+F dans votre navigateur pour rechercher dans la transcription

### Utilisation des métadonnées

Les métadonnées fournissent un contexte utile :

- **Date** : Pour situer dans l'actualité
- **Durée** : Pour estimer la densité du contenu
- **URL** : Pour écouter des passages si nécessaire
- **Type** : Pour adapter le style de correction

### Gestion de l'historique (futur)

Fonctionnalités prévues :
- Historique des versions
- Comparaison avant/après
- Commentaires sur les corrections
- Attribution des modifications

## Cas d'usage spéciaux

### Épisodes très longs (> 1 heure)

**Stratégie :**
1. Identifier les grandes sections
2. Créer une table des matières
3. Résumer par thème principal
4. Conserver les détails importants

### Épisodes multi-sujets

**Approche :**
```
durée : XX:XX - [Émission] - par : [Présentateur]

Au programme de cette émission :

1️⃣ [Sujet 1] (XX:XX)
Description du premier sujet...

2️⃣ [Sujet 2] (XX:XX)
Description du deuxième sujet...

3️⃣ [Sujet 3] (XX:XX)
Description du troisième sujet...
```

### Épisodes avec invités multiples

**Format recommandé :**
```
durée : XX:XX - [Émission] - par : [Présentateur]

[Description du thème principal]

Invités :
👤 [Nom] - [Fonction/Expertise]
   • [Contribution spécifique]

👤 [Nom] - [Fonction/Expertise]
   • [Contribution spécifique]
```

## Métriques de qualité

### Indicateurs d'une bonne correction

✅ **Structure claire :**
- Informations essentielles en premier
- Sections logiquement organisées
- Transitions fluides entre les éléments

✅ **Précision :**
- Noms propres correctement orthographiés
- Titres d'œuvres fidèles
- Fonctions et rôles précis

✅ **Lisibilité :**
- Passages à la ligne appropriés
- Ponctuation cohérente
- Longueur de paragraphes équilibrée

✅ **Complétude :**
- Informations importantes préservées
- Contexte suffisant pour la compréhension
- Détails pertinents maintenus

### Contrôles qualité

Avant de considérer la correction terminée :

1. ✅ La structure est-elle logique ?
2. ✅ Les noms sont-ils correctement orthographiés ?
3. ✅ L'information originale est-elle préservée ?
4. ✅ Le texte est-il facile à lire ?
5. ✅ Les éléments importants sont-ils mis en évidence ?

## Support et ressources

### En cas de doute

1. **Consultez** la transcription complète
2. **Écoutez** l'extrait audio via l'URL
3. **Recherchez** les noms propres sur Internet
4. **Gardez** la structure originale si incertain

### Ressources externes

- **Site de l'émission** pour vérifier les informations
- **Bases de données** musicales/littéraires/cinéma
- **Moteurs de recherche** pour l'orthographe des noms
- **Archives** des émissions précédentes pour la cohérence
