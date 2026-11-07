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
| **📚** | Possession : statut Calibre, ou lien de téléchargement |

### Badge de note

Les notes sont affichées avec un code couleur :

- **Vert foncé** (9-10) : Excellent
- **Vert clair** (7-8.9) : Bon
- **Jaune** (5-6.9) : Moyen
- **Rouge** (< 5) : Faible

### Colonne 📚 (possession / téléchargement)

La même colonne figure dans [Mes Recommandations](recommandation-livres.md#le-tableau-de-resultats).

Livre présent dans la bibliothèque Calibre :

- **✓ Lu** : Le livre a été marqué comme lu
- **◯** : Le livre est dans Calibre mais pas encore lu
- **X/10** : Note Calibre (affichée uniquement pour les livres lus)

Le symbole ✓ Lu / ◯ est cliquable : il ouvre la page Calibre avec le titre pré-rempli dans la recherche.

Livre absent de Calibre : l'**icône Anna's Archive** lance la recherche du livre (titre + auteur) dans un nouvel onglet.

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

Le rapprochement entre les livres du palmarès (MongoDB) et la bibliothèque Calibre utilise la normalisation `normalize_for_matching()` :

- Insensible à la casse (majuscules/minuscules)
- Insensible aux accents (é → e, ô → o, etc.)
- Conversion des ligatures (œ → oe, æ → ae)
- Normalisation des tirets (cadratin → simple) et apostrophes (typographique → simple)

Le palmarès utilise un index titre normalisé → livre Calibre pour un lookup rapide. Pour un matching plus complet (incluant containment et validation auteur), voir la page [Corrections Calibre](calibre-integration.md#corrections-calibre).
