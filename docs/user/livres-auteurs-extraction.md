# Extraction des Livres et Auteurs

La fonctionnalité d'extraction permet d'identifier et de cataloguer les livres, auteurs et éditeurs mentionnés dans les avis critiques du Masque et la Plume en analysant les tableaux markdown structurés des résumés d'épisodes.

## Accès à la fonctionnalité

1. **Navigation** : Cliquez sur "Livres et Auteurs" dans le menu principal
2. **URL directe** : `/livres-auteurs`

## Vue d'ensemble

### Informations affichées

La page présente un tableau simple avec trois colonnes :

- **Auteur** : Nom de l'auteur du livre
- **Titre** : Titre du livre
- **Éditeur** : Maison d'édition (peut être vide si non mentionné)

### Statistiques simplifiées

En haut de page, un compteur indique simplement le nombre de livres extraits de l'épisode sélectionné.

## Navigation et fonctionnalités

### Sélection d'épisode
Commencez par choisir un épisode dans la liste déroulante "Choisir un épisode avec avis critiques". Seuls les épisodes ayant des avis critiques analysés sont disponibles.

### Tri du tableau
Cliquez sur les en-têtes de colonnes pour trier :
- **Auteur** : tri alphabétique des noms d'auteurs
- **Titre** : tri alphabétique des titres de livres
- **Éditeur** : tri alphabétique des éditeurs

Le tri bascule entre croissant (↑) et décroissant (↓) à chaque clic.

### Recherche
Utilisez la barre de recherche pour filtrer instantanément par :
- Nom d'auteur
- Titre de livre
- Nom d'éditeur

La recherche est instantanée et insensible à la casse.

## Source et fiabilité des données

### Extraction des tableaux markdown
Les livres sont extraits automatiquement en analysant les tableaux markdown des résumés d'épisodes stockés dans la base de données. L'extraction parse deux sections :

1. **"LIVRES DISCUTÉS AU PROGRAMME"** : Livres principaux de l'émission
2. **"COUPS DE CŒUR DES CRITIQUES"** : Recommandations des critiques

### Fiabilité
L'extraction étant basée sur l'analyse de tableaux structurés, elle est généralement fiable mais peut présenter des limites :
- Dépendance à la structure markdown correcte
- Éditeurs parfois non mentionnés dans les tableaux d'origine
- Variations possibles dans la présentation des noms

En cas de données manifestement erronées, contactez l'administrateur.

## Cas d'usage typiques

### Explorer les livres d'un épisode
1. Sélectionnez un épisode dans la liste déroulante
2. Le tableau affiche tous les livres mentionnés dans cet épisode (programme + coups de cœur)

### Recherche par auteur
1. Sélectionnez d'abord un épisode
2. Tapez le nom de l'auteur dans la barre de recherche
3. Les résultats se filtrent automatiquement

### Tri et organisation
1. Cliquez sur "Auteur" pour trier alphabétiquement par nom d'auteur
2. Cliquez sur "Titre" pour trier par titre de livre
3. Cliquez sur "Éditeur" pour regrouper par maison d'édition

## Limitations actuelles

- **Par épisode** : Il faut sélectionner un épisode à la fois pour voir ses livres
- **Données disponibles** : Seuls les épisodes avec avis critiques analysés sont inclus
- **Informations limitées** : Affichage simple auteur/titre/éditeur uniquement
- **Éditeurs manquants** : Certains livres peuvent ne pas avoir d'éditeur mentionné

## Évolutions prévues

Cette fonctionnalité évoluera avec :
- **Vue globale** : Affichage de tous les livres de tous les épisodes
- **Intégration Babelio** : Vérification et correction orthographique via l'API Babelio
- **Enrichissement** : Ajout d'images de couverture, résumés détaillés, et métadonnées
- **Export de données** : Possibilité d'exporter les listes en CSV ou autres formats
- **Interface d'administration** : Correction manuelle et validation des extractions
