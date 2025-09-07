# Extraction LLM des Livres et Auteurs

La nouvelle fonctionnalité d'extraction automatique permet d'identifier et de cataloguer les livres, auteurs et éditeurs mentionnés dans les avis critiques du Masque et la Plume grâce à l'intelligence artificielle.

## Accès à la fonctionnalité

1. **Navigation** : Cliquez sur "Livres et Auteurs" dans le menu principal
2. **URL directe** : `/livres-auteurs`

## Vue d'ensemble

### Informations affichées

Pour chaque livre extrait, vous verrez :

- **Titre du livre** et nom de l'auteur
- **Éditeur** de publication
- **Note moyenne** calculée à partir des critiques
- **Nombre de critiques** reçues
- **Coups de cœur** (noms des critiques ayant donné un coup de cœur)
- **Épisode source** avec titre et date d'origine

### Statistiques de synthèse

En haut de page, un tableau de bord présente :
- Nombre total de livres extraits
- Nombre d'auteurs différents identifiés
- Nombre d'épisodes sources analysés
- Note moyenne globale de tous les livres

## Recherche et filtrage

### Barre de recherche
Utilisez la barre de recherche pour filtrer par :
- Titre de livre
- Nom d'auteur
- Nom d'éditeur
- Titre d'épisode

La recherche est instantanée et insensible à la casse.

### Options de tri

Plusieurs options de tri sont disponibles :
- **Note décroissante** (par défaut) : du mieux noté au moins bien noté
- **Note croissante** : du moins bien noté au mieux noté
- **Auteur A→Z** : tri alphabétique par nom d'auteur
- **Auteur Z→A** : tri alphabétique inverse par nom d'auteur
- **Date décroissante** : épisodes les plus récents en premier
- **Date croissante** : épisodes les plus anciens en premier

## Comprendre les données

### Source des données
Les livres sont extraits automatiquement des résumés d'épisodes du Masque et la Plume à l'aide d'un modèle d'intelligence artificielle (Azure OpenAI). Seuls les livres du tableau "LIVRES DISCUTÉS AU PROGRAMME" sont extractés.

### Notes et critiques
- **Note moyenne** : Moyenne des notes attribuées par les critiques (sur une échelle généralement de 0 à 10)
- **Nombre de critiques** : Nombre total de critiques ayant évalué ce livre dans l'épisode
- **Coups de cœur** : Liste des critiques ayant particulièrement apprécié le livre

### Fiabilité des données
L'extraction étant automatisée, des erreurs peuvent occasionnellement survenir :
- Titres ou noms d'auteurs légèrement modifiés
- Attribution incorrecte d'éditeurs
- Notes mal interprétées

En cas de données manifestement erronées, contactez l'administrateur.

## Cas d'usage typiques

### Recherche par auteur
Pour voir tous les livres d'un auteur spécifique :
1. Tapez le nom de l'auteur dans la barre de recherche
2. Les résultats se filtrent automatiquement

### Découverte de livres bien notés
1. Utilisez le tri "Note décroissante" (activé par défaut)
2. Les livres avec les meilleures notes apparaissent en premier

### Suivi chronologique
1. Utilisez le tri "Date décroissante" pour voir les dernières découvertes
2. Ou "Date croissante" pour un parcours historique

### Analyse d'un épisode
1. Recherchez le titre de l'épisode ou sa date
2. Vous verrez tous les livres discutés dans cet épisode

## Limitations actuelles

- **Extraction automatique** : Parfois imparfaite, peut nécessiter des corrections manuelles
- **Données historiques** : Seuls les épisodes avec avis critiques analysés sont inclus
- **Babelio non intégré** : Les enrichissements prévus (couvertures, résumés) ne sont pas encore disponibles

## Évolutions prévues

Cette fonctionnalité évoluera avec :
- **Intégration Babelio** : Ajout d'images de couverture, résumés détaillés, et données complémentaires
- **Correction manuelle** : Interface d'administration pour corriger les erreurs d'extraction
- **Export de données** : Possibilité d'exporter les listes en CSV ou autres formats
- **Statistiques avancées** : Analyse des tendances, auteurs les plus mentionnés, etc.
