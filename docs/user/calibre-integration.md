# Intégration Calibre - Vision et fonctionnalités

## Vue d'ensemble

L'intégration Calibre permet de connecter votre bibliothèque personnelle Calibre avec les données du Masque et la Plume. Cette fonctionnalité vous permet de croiser vos lectures et appréciations personnelles avec les critiques littéraires de l'émission.

## Architecture des données

### Sources de données multiples

L'application travaille avec trois sources de données complémentaires :

```
┌──────────────────────────────────────────────────────────┐
│                    Back-Office LMELP                     │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  ┌────────────┐    ┌────────────┐    ┌────────────┐     │
│  │  MongoDB   │    │  Calibre   │    │  Babelio   │     │
│  │            │    │            │    │            │     │
│  │ • Episodes │    │ • Livres   │    │ • Méta-    │     │
│  │ • Livres   │    │ • Auteurs  │    │   données  │     │
│  │ • Critiques│    │ • Notes    │    │ • Nettoyage│     │
│  │            │    │ • Tags     │    │   données  │     │
│  └────────────┘    └────────────┘    └────────────┘     │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### Rôle de chaque source

- **MongoDB** : Base principale contenant les données du Masque et la Plume (épisodes, livres critiqués, avis des critiques)
- **Calibre** : Votre bibliothèque personnelle avec vos lectures, notes et appréciations
- **Babelio** : Service externe pour enrichir et normaliser les métadonnées bibliographiques

## Fonctionnement actuel

### Accès direct en lecture seule

Calibre est traité comme une **seconde source de données** indépendante :

- Interrogation directe de `metadata.db` via SQLite
- Affichage des livres avec infinite scroll
- Visualisation de vos notes et appréciations
- Recherche temps réel avec highlighting en jaune
- Filtres par statut de lecture (Tous / Lus / Non lus)
- Tri flexible (date d'ajout, titre, auteur)
- Support bibliothèques virtuelles (filtre par tag Calibre)

**Avantages** :
- Pas de duplication de données
- Source de vérité unique (Calibre)
- Accès lecture seule sécurisé
- Déploiement simple via Docker

**Caractéristiques** :
- Pas de synchronisation avec MongoDB
- Interface dédiée `/calibre` accessible depuis le dashboard
- Fonctionne en parallèle de MongoDB sans interférence

### Évolution future : Synchronisation vers MongoDB

À terme, les données Calibre seront **rapatriées vers MongoDB** :

```
Calibre → Nettoyage Babelio → MongoDB
   ↓            ↓                ↓
Lecture    Normalisation    Corrélation
continue   métadonnées      avec LMELP
```

**Processus de synchronisation** :

1. **Extraction** : Lecture périodique de la base Calibre
2. **Nettoyage** : Appels Babelio pour normaliser les métadonnées (ISBN, auteurs, titres)
3. **Enrichissement** : Ajout des informations manquantes
4. **Liaison** : Correspondance avec les livres MongoDB (critiques LMELP)
5. **Import** : Stockage dans MongoDB avec marqueur de source

**Défis techniques** :

- **Évolution continue** : La base Calibre change avec vos lectures
- **Synchronisation incrémentielle** : Détecter uniquement les nouveautés
- **Résolution de conflits** : Gérer les livres présents dans les deux sources
- **Qualité des données** : Normaliser les noms d'auteurs et titres

### Évolution future : Comparaison et analyse

Une fois les données synchronisées, fonctionnalités planifiées :

- **Comparaison d'appréciations** : Vos notes vs notes des critiques LMELP
- **Analyse de corrélation** : Statistiques sur vos convergences/divergences
- **Recommandations** : Livres critiqués au Masque que vous n'avez pas lus
- **Graphiques** : Visualisation de vos préférences vs celles des critiques

## Fonctionnalités disponibles

### Accès conditionnel

L'intégration Calibre n'est active que si :

1. ✅ Le volume Docker est monté sur `/calibre`
2. ✅ Base de données Calibre (`metadata.db`) accessible dans ce dossier
3. ✅ Bibliothèque Calibre valide et lisible

Si ces conditions ne sont pas remplies, la fonctionnalité reste invisible dans l'interface.

### Page Calibre

Nouvelle page accessible depuis l'accueil :

```
┌─────────────────────────────────────┐
│      Fonctions disponibles          │
│                                     │
│ ┌─────────────┐ ┌─────────────┐     │
│ │📝 Episode - │ │🔍 Recherche │     │
│ │  Modification│ │  avancée    │     │
│ └─────────────┘ └─────────────┘     │
│                                     │
│ ┌─────────────┐                     │
│ │📚 Accès     │                     │
│ │  Calibre    │  ← Nouvelle entrée  │
│ │    [→]      │                     │
│ └─────────────┘                     │
└─────────────────────────────────────┘
```

**Informations affichées** :

- **Titre** : Titre du livre (termes de recherche surlignés en jaune)
- **Auteur(s)** : Auteur(s) du livre (termes de recherche surlignés en jaune)
- **Éditeur** : Maison d'édition
- **ISBN** : Numéro ISBN
- **Note** : Votre appréciation (sur 5 étoiles)
- **Tags** : Mots-clés Calibre
- **Statut de lecture** : Lu/Non lu (colonne personnalisée #read)

**Fonctionnalités interactives** :

- **Recherche temps réel** : Filtrage par titre ou auteur (minimum 3 caractères)
  - Highlighting automatique des termes recherchés en jaune
  - Insensible aux accents (ex: "celine" trouve "Céline")
- **Filtres de statut** : Tous / Lus / Non lus
- **Tri dynamique** :
  - Derniers ajoutés (défaut)
  - Titre A→Z / Z→A
  - Auteur A→Z / Z→A
- **Infinite scroll** : Chargement progressif de 50 livres à la fois
- **Statistiques** : Total livres, livres lus, pourcentage de lecture

### Tags Calibre sur la page Livre

Sur la page de détail d'un livre (`/livre/{id}`), des tags Calibre sont calculés dynamiquement et affichés comme badges violets à côté du compteur d'émissions. Ces tags suivent la convention de nommage Calibre pour le projet lmelp :

```
┌─────────────────────────────────────────────────────────────┐
│  📖 La Deuxième Vie                                         │
│  ✍️ Philippe Sollers                                       │
│  📅 1 émission  guillaume  lmelp_240324  lmelp_arnaud_…  📋│
└─────────────────────────────────────────────────────────────┘
```

**Types de tags** :

| Tag | Format | Source | Exemple |
|-----|--------|--------|---------|
| Bibliothèque virtuelle | `CALIBRE_VIRTUAL_LIBRARY_TAG` | Calibre | `guillaume` |
| Date d'émission | `lmelp_yyMMdd` | Collection `avis` + `emissions` | `lmelp_240324` |
| Critique coup de cœur | `lmelp_prenom_nom` | Collection `avis` (section coup_de_coeur) | `lmelp_arnaud_viviant` |

**Ordre d'affichage** : tag bibliothèque virtuelle → tags notables (`babelio`, `lu`, `onkindle` si présents) → dates chronologiques → critiques alphabétiques.

**Bouton copie** : Le bouton 📋 copie tous les tags séparés par des virgules dans le presse-papier (ex: `guillaume, lmelp_240324, lmelp_arnaud_viviant`). Ces tags peuvent être collés directement dans Calibre pour taguer un livre.

**Dégradation gracieuse** : Le tag de bibliothèque virtuelle est affiché dès que des tags `lmelp_*` existent, que le livre soit ou non dans Calibre. L'utilisateur dispose ainsi de tous les tags prêts à copier-coller. Si le livre n'a aucun avis, aucun tag n'est affiché.

### Corrections Calibre

La page **Corrections Calibre** (`/calibre-corrections`) identifie les différences entre les données MongoDB et Calibre pour les livres matchés, et propose les corrections à appliquer dans Calibre.

**Accès** : Depuis le Dashboard, cliquez sur la carte **"Corrections Calibre"**.

#### Matching MongoDB-Calibre

L'algorithme de matching utilise 3 niveaux successifs :

| Niveau | Méthode | Description |
|--------|---------|-------------|
| **Exact** | Titre normalisé identique | Accents, ligatures, tirets, apostrophes normalisés |
| **Containment** | Un titre contient l'autre | Gère les sous-titres, tomes, prix (min 4 caractères) |
| **Validation auteur** | Comparaison tolérante des noms | Pour les cas où plusieurs candidats sont trouvés par containment |

La normalisation (`normalize_for_matching()`) applique : minuscules, suppression des accents, conversion des ligatures (œ→oe, æ→ae), normalisation des tirets et apostrophes typographiques.

#### Sections de corrections

La page affiche 3 catégories de corrections, chacune dans une section dépliable :

1. **Corrections auteurs** : Livres dont le nom d'auteur diffère entre MongoDB et Calibre (formats différents, orthographe, pipe Calibre vs naturel MongoDB).

2. **Corrections titres** : Livres dont le titre diffère après matching (sous-titres, tomes, casse). Seuls les livres matchés par containment ou validation auteur sont concernés.

3. **Tags `lmelp_*` manquants** : Livres matchés dont les tags `lmelp_` attendus ne sont pas tous présents dans Calibre. Pour chaque livre, un bouton **📋 Copier** fournit la liste complète des tags à coller dans Calibre, dans l'ordre : tag bibliothèque virtuelle → tags notables (`babelio`, `lu`, `onkindle`) → tags `lmelp_*`.

#### Cache et rafraîchissement

Les données de matching sont mises en cache pendant 5 minutes. Un bouton **"Rafraîchir"** permet d'invalider le cache manuellement après avoir appliqué des corrections dans Calibre.

### Page OnKindle

La page **OnKindle** (`/onkindle`) affiche tous les livres Calibre portant le tag `onkindle`, enrichis avec les données MongoDB quand une correspondance est trouvée.

**Accès** : Depuis le Dashboard, cliquez sur la carte **"OnKindle"**.

**Informations affichées** :

| Colonne | Description |
|---------|-------------|
| **Auteur** | Lien vers la fiche auteur si trouvé dans MongoDB, texte sinon |
| **Titre** | Lien vers la fiche livre si trouvé dans MongoDB, texte sinon |
| **Note** | Note moyenne des critiques LMELP (badge coloré), si disponible |
| **Reco** | Score de recommandation personnalisé (algorithme SVD, badge coloré), si disponible |
| **Babelio** | Icône cliquable vers la fiche Babelio, si disponible |

**Fonctionnalités** :

- **Tri par colonnes** : Cliquez sur Auteur, Titre, Note ou Reco pour trier. Le tri est accent-insensitif ("À prendre" s'affiche avant "Zola").
- **Tri par défaut** : Score de recommandation décroissant — répond à la question « quel livre de ma liseuse ai-je le plus de chances d'aimer ? »
- **Persistance du tri** : Le tri choisi est mémorisé dans l'URL (`?sort=score&dir=desc`) et restauré au rechargement de la page.
- **Enrichissement MongoDB** : Les livres Calibre matchés avec MongoDB affichent leur note LMELP et leur lien Babelio.
- **Score Reco** : Calculé par l'algorithme de collaborative filtering SVD (voir page Recommandations). Le score se charge en arrière-plan (~10 secondes) ; la table s'affiche immédiatement avec `-` dans la colonne Reco pendant le calcul.
- **Dégradation gracieuse** : Si Calibre n'est pas disponible, un message explicite est affiché. Si l'API de recommandations échoue, `-` est affiché pour tous les scores sans bloquer la page.

**Correspondance Calibre-MongoDB** :

L'algorithme de matching utilise la normalisation des titres (`normalize_for_matching()`), insensible aux accents, ligatures, tirets et apostrophes typographiques. Un livre Calibre sans correspondance MongoDB s'affiche quand même (titre et auteur en texte simple, sans note ni lien).

### Recherche avancée étendue

Dans la page de **recherche avancée**, nouveau champ :

```
┌──────────────────────────────────────┐
│         Recherche Avancée            │
├──────────────────────────────────────┤
│  Source de données :                 │
│  ☐ MongoDB (LMELP)                  │
│  ☐ Calibre                          │  ← Nouvelle option
│  ☐ Les deux                         │
├──────────────────────────────────────┤
│  Auteur : [____________]            │
│  Livre  : [____________]            │
│                                      │
│         [Rechercher]                 │
└──────────────────────────────────────┘
```

**Comportement** :

- Recherche simultanée dans MongoDB et/ou Calibre
- Résultats groupés par source
- Indication visuelle de l'origine des données

**Note** : La recherche simple (barre de recherche générale) reste limitée à MongoDB pour des raisons de performance.

## Configuration

### Montage du volume

L'application détecte automatiquement la bibliothèque Calibre si elle est montée dans le dossier `/calibre`.

```bash
# Docker (docker-compose.yml)
volumes:
  - /home/guillaume/Calibre Library:/calibre:ro
```

### Validation au démarrage

Au démarrage, l'application :

1. Vérifie l'existence du dossier `/calibre` et du fichier `metadata.db`
2. Teste l'accès à la base Calibre
3. Valide la structure de la bibliothèque
4. Active/désactive l'intégration en conséquence

### Logs

```
[INFO] Calibre integration: ENABLED
[INFO] Calibre library path: /home/guillaume/Calibre Library
[INFO] Calibre books found: 342
```

ou

```
[WARNING] Calibre integration: DISABLED
[WARNING] Calibre library not found in /calibre
```

## Métadonnées Calibre utilisées

### Champs standard

- `title` : Titre du livre
- `authors` : Auteur(s)
- `isbn` : ISBN pour liaison Babelio
- `tags` : Catégories/mots-clés
- `publisher` : Éditeur
- `pubdate` : Date de publication

### Champs personnalisés (si définis)

- `#read` : Marqueur "Lu" (booléen)
- `#rating` : Note personnelle (1-5 étoiles)
- `#date_read` : Date de fin de lecture
- `#review` : Commentaire personnel

**Note** : Les noms de colonnes personnalisées Calibre sont précédés de `#`. L'application s'adapte automatiquement à votre configuration Calibre.

## Cas d'usage

### Retrouver un livre critiqué au LMELP dans votre bibliothèque

1. Page **Recherche avancée**
2. Saisir auteur ou titre
3. Cocher "Les deux sources"
4. Comparer : livre présent dans LMELP ET dans votre Calibre ?

### Voir vos livres non encore critiqués

1. Page **Accès Calibre**
2. Exporter la liste
3. Croiser avec les livres MongoDB (feature future)

### Comparer vos appréciations avec celles des critiques

**Fonctionnalité planifiée** (nécessite synchronisation MongoDB) :

1. Rechercher un livre présent dans les deux sources
2. Voir votre note Calibre à côté des notes LMELP
3. Analyser les convergences/divergences

## Considérations techniques

### Performance

- **Calibre comme source secondaire** : Pas d'impact sur les requêtes MongoDB existantes
- **Cache applicatif** : Métadonnées Calibre mises en cache pour réduire les accès disque
- **Lazy loading** : Chargement des données Calibre uniquement quand nécessaire

### Sécurité

- **Lecture seule** : Aucune modification de la base Calibre
- **Isolation** : Calibre et MongoDB restent indépendants
- **Validation** : Vérification des chemins et permissions au démarrage

### Maintenance

- **Évolution Calibre** : Détection automatique des changements
- **Logs détaillés** : Traçabilité des opérations Calibre
- **Gestion d'erreurs** : Désactivation gracieuse si Calibre inaccessible

## Fonctionnalités planifiées

### Synchronisation vers MongoDB

- Service de synchronisation Calibre → MongoDB
- Appels Babelio pour nettoyage métadonnées
- Détection des nouveaux livres (sync incrémentielle)
- Interface de gestion de la synchronisation
- Logs et monitoring sync

### Analyse et comparaison

- Comparaison notes personnelles vs critiques LMELP
- Statistiques de corrélation
- Graphiques de divergence
- Recommandations basées sur profil
- Export des analyses

## Questions fréquentes

### Puis-je utiliser plusieurs bibliothèques Calibre ?

Non, actuellement l'application ne supporte qu'une seule bibliothèque Calibre par instance.

### Les modifications dans Calibre sont-elles immédiatement visibles ?

Actuellement, un rechargement de la page est nécessaire pour voir les changements. La synchronisation automatique pourra être ajoutée ultérieurement.

### Que se passe-t-il si Calibre n'est pas accessible ?

L'intégration Calibre est simplement désactivée. Les fonctionnalités MongoDB continuent de fonctionner normalement.

### Calibre doit-il être installé sur le serveur ?

Non, seule la **bibliothèque Calibre** (le dossier contenant `metadata.db`) doit être accessible. Calibre Desktop n'a pas besoin d'être installé.

L'application utilise SQLite (built-in Python) pour lire directement `metadata.db` sans nécessiter l'installation de Calibre.

### Comment activer Calibre en production (Docker) ?

Voir le guide complet de [Configuration Calibre en Production](../deployment/calibre-setup.md).

**En résumé** :

1. Définir `CALIBRE_HOST_PATH` dans le fichier `.env` (chemin de votre bibliothèque Calibre sur l'hôte)
2. Optionnel : Définir `CALIBRE_VIRTUAL_LIBRARY_TAG` pour filtrer par tag (ex: "guillaume")
3. Redéployer la stack Docker via Portainer

**Exemple .env** :
```bash
CALIBRE_HOST_PATH=/volume1/books/Calibre Library
CALIBRE_VIRTUAL_LIBRARY_TAG=guillaume
```

Le volume est monté en **lecture seule** (`:ro`) pour éviter toute modification de votre bibliothèque.

### Puis-je modifier mes notes Calibre depuis back-office-lmelp ?

Non, l'accès est en lecture seule. Cette fonctionnalité pourra être ajoutée ultérieurement selon les besoins.

---

*Cette documentation décrit la vision complète de l'intégration Calibre. Pour le détail technique de l'implémentation, consultez la [documentation développeur](../dev/calibre-integration.md).*
