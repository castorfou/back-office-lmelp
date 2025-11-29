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

1. ✅ Variable d'environnement `CALIBRE_LIBRARY_PATH` définie
2. ✅ Base de données Calibre accessible au chemin indiqué
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

### Variable d'environnement

```bash
# Développement local
export CALIBRE_LIBRARY_PATH="/home/guillaume/Calibre Library"

# Docker (docker-compose.yml)
environment:
  - CALIBRE_LIBRARY_PATH=/calibre-library

# Docker volume mount
volumes:
  - /home/guillaume/Calibre Library:/calibre-library:ro
```

### Validation au démarrage

Au démarrage, l'application :

1. Vérifie l'existence de `CALIBRE_LIBRARY_PATH`
2. Teste l'accès à la base Calibre (`metadata.db`)
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
[WARNING] CALIBRE_LIBRARY_PATH not set
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
