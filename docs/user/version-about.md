# Version et page "À propos"

## Vue d'ensemble

L'application affiche un **numéro de version** basé sur le hash du commit Git déployé. Un footer discret sur le Dashboard permet d'identifier rapidement la version en cours, et une page **"À propos"** présente l'historique complet des modifications.

## Footer de version (Dashboard)

En bas du Dashboard, un lien discret affiche :

```
v. 92e69cf (10/02/26)
```

- **Hash court** : les 7 premiers caractères du commit Git
- **Date** : date du commit au format `JJ/MM/AA`

Au survol, une infobulle indique l'environnement (Docker ou développement) et la date de build.

Cliquez sur ce lien pour accéder à la page "À propos".

## Page "À propos"

Accessible via :

- Le footer du Dashboard (clic sur la version)
- L'URL directe : `http://localhost:5173/about`

### Informations de version

La section supérieure affiche :

| Champ | Description |
|-------|-------------|
| **Commit** | Hash court cliquable vers le commit GitHub |
| **Date du commit** | Date formatée en français |
| **Environnement** | `docker` (production) ou `development` (dev local) |
| **Date de build** | Date de construction de l'image Docker |

### Historique des modifications (Changelog)

Le tableau principal liste tous les commits qui référencent une issue ou une Pull Request (`#XXX`), classés du plus récent au plus ancien.

| Colonne | Description |
|---------|-------------|
| **Hash** | Hash court du commit, cliquable vers GitHub |
| **Date** | Date du commit au format français |
| **Description** | Message du commit avec les numéros `#XXX` rendus cliquables vers les issues GitHub correspondantes |

### Navigation

Un bouton **"Retour"** en haut de page permet de revenir à la page précédente.

## Fonctionnement technique

### En production (Docker)

Les informations de version sont **intégrées à l'image Docker** lors du build CI/CD. Aucun appel à l'API GitHub n'est effectué au runtime. L'image contient deux fichiers JSON pré-générés :

- `build_info.json` : hash, date du commit, date de build
- `changelog.json` : liste des commits avec références issues/PRs

### En développement local

Les informations sont lues directement depuis le dépôt Git local via `git log`. Le changelog est généré dynamiquement à chaque démarrage du backend.

### Version au démarrage

La version est également affichée dans les logs de démarrage du backend :

```
🏷️  Version: 92e69cf (development)
   Commit: https://github.com/castorfou/back-office-lmelp/commit/92e69cf...
```
