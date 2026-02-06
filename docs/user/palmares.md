# Palmarès des livres

## Vue d'ensemble

La page **Palmarès** affiche le classement de tous les livres par note moyenne décroissante. Seuls les livres ayant reçu au minimum 2 avis critiques apparaissent dans le classement. L'intégration Calibre permet de voir le statut de lecture et la note personnelle pour chaque livre.

## Accès à la page

Depuis le **Dashboard**, cliquez sur la carte **"Palmarès"** (2e carte après Émissions).

L'URL directe est :
```
http://localhost:5173/palmares
```

## Interface

### Tableau principal

Le tableau présente les colonnes suivantes :

| Colonne | Description |
|---------|-------------|
| **#** | Rang dans le classement |
| **Livre** | Titre du livre (lien cliquable vers la page détail) |
| **Auteur** | Nom de l'auteur (lien cliquable vers la page détail) |
| **Note** | Note moyenne avec badge coloré |
| **Avis** | Nombre d'avis critiques |
| **Calibre** | Statut de lecture et note Calibre |
| **Liens** | Liens vers Calibre et Anna's Archive |

### Badge de note

Les notes sont affichées avec un code couleur :

- **Vert foncé** (9-10) : Excellent
- **Vert clair** (7-8.9) : Bon
- **Jaune** (5-6.9) : Moyen
- **Rouge** (< 5) : Faible

### Colonne Calibre

Pour chaque livre présent dans la bibliothèque Calibre :

- **✓ Lu** : Le livre a été marqué comme lu
- **◯** : Le livre est dans Calibre mais pas encore lu
- **X/10** : Note Calibre (affichée uniquement pour les livres lus)
- **—** : Le livre n'est pas dans la bibliothèque Calibre

### Liens rapides

Chaque ligne propose deux liens :

- **Icône Calibre** : Ouvre la page Calibre avec le titre pré-rempli dans la recherche
- **Icône Anna's Archive** : Recherche le livre sur Anna's Archive (titre + auteur)

## Filtres interactifs

Trois filtres sous forme de **pills cliquables** sont disponibles en haut de page :

| Filtre | Actif (par défaut) | Inactif |
|--------|-------------------|---------|
| **Lus** | Affiche les livres lus dans Calibre | Masque les livres lus |
| **Non lus** | Affiche les livres non lus | Masque les livres non lus et hors Calibre |
| **Dans Calibre** | Affiche les livres présents dans Calibre | Masque les livres Calibre |

- Tous les filtres sont **actifs par défaut** (tous les livres visibles)
- Cliquez sur un filtre pour le désactiver/réactiver
- Le compteur "X livres classés" se met à jour dynamiquement
- Les sélections de filtres sont **persistées dans le navigateur** (localStorage) et survivent au rechargement de la page

## Chargement progressif

Le palmarès utilise un **infinite scroll** : les livres sont chargés par pages de 30. En faisant défiler vers le bas, les pages suivantes se chargent automatiquement.

## Matching Calibre

Le rapprochement entre les livres du palmarès (MongoDB) et la bibliothèque Calibre se fait par **normalisation du titre** :

- Insensible à la casse (majuscules/minuscules)
- Insensible aux accents (é → e, ô → o, etc.)
- Normalisation Unicode NFKD

Ce matching est approximatif ; certains livres peuvent ne pas être reconnus si le titre diffère significativement entre les deux sources.
