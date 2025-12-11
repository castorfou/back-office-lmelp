# Guide Utilisateur - Intégration Babelio

## Vue d'ensemble

L'intégration Babelio enrichit automatiquement la base de données avec des liens vers les fiches Babelio des livres et auteurs. Le système vérifie l'orthographe, valide les données bibliographiques, et maintient à jour les URLs Babelio pour faciliter l'accès aux informations détaillées.

## Accès aux fonctionnalités

### Validation bibliographique
**Navigation** : Menu principal → **Livres et Auteurs**

### Gestion de la migration Babelio
**Navigation** : Menu principal → **Gestion Babelio** ou accès direct via `/babelio-migration`

## Comprendre les indicateurs de validation

Dans le tableau des livres, la colonne **"Validation Biblio"** affiche l'un des indicateurs suivants :

### ✅ Validé
**Signification** : Les données sont correctes et confirmées par Babelio.

**Action** : Aucune, les informations sont fiables.

### 🔄 Suggestion
**Signification** : Le système propose une correction orthographique.

**Exemples** :
- "Alain Mabancou" → "Alain Mabanckou" (correction auteur)
- "Tant mieu" → "Tant mieux" (correction titre)

**Action** : Cliquez sur l'indicateur pour voir les détails de la suggestion (original → corrigé).

### ❓ Non trouvé
**Signification** : Aucune correspondance fiable n'a été trouvée sur Babelio.

**Raisons possibles** :
- Faute d'orthographe importante
- Livre récent non encore référencé
- Inversion de nom (ex: "Le Floch" → "Lefloc")

**Action** : Vérification manuelle nécessaire. Consultez directement [Babelio.com](https://www.babelio.com) pour confirmation.

### ⚠️ Erreur
**Signification** : Problème technique lors de la vérification.

**Action** : Cliquez sur le bouton **Retry** pour relancer la validation.

## Comment fonctionne la validation ?

Le système combine **plusieurs sources** pour maximiser la fiabilité :

1. **Vérification directe Babelio** : Test rapide si les données sont exactes
2. **Recherche dans les métadonnées d'épisode** : Recherche fuzzy dans titre/description de l'épisode
3. **Validation croisée auteur + titre** : Vérification que l'auteur correspond bien au livre

**Priorité** : Les données de l'épisode (vérifiées par l'éditeur France Inter) sont prioritaires sur les corrections Babelio quand elles sont fiables.

## Enrichissement automatique de l'éditeur

Lors de l'extraction des livres depuis les avis critiques, le système enrichit automatiquement les données avec l'information d'éditeur provenant de Babelio.

### Fonctionnement

**Extraction automatique** :
- Lorsqu'un livre est validé avec un score de confiance ≥ 0.90
- Le système récupère automatiquement le nom de l'éditeur depuis la page Babelio
- L'information est ajoutée au livre dans le cache

**Mise à jour des avis critiques** :
- Lorsqu'une correction d'auteur ou de titre est validée
- Le résumé de l'avis critique est automatiquement mis à jour
- L'éditeur Babelio remplace l'éditeur original si disponible

**Enrichissement différé** :
- Si un livre possède une URL Babelio mais pas d'éditeur
- Le système récupère automatiquement l'éditeur lors du prochain chargement
- Cette information est mise en cache pour éviter les requêtes répétées

### Avantages

- ✅ **Données complètes** : Éditeur automatiquement renseigné pour ~90% des livres
- ✅ **Réduction saisie manuelle** : Moins de champs à compléter manuellement
- ✅ **Qualité des données** : Source Babelio fiable et à jour
- ✅ **Performance** : Cache intelligent évite les requêtes redondantes

## Cas d'usage typiques

### Utilisateur final (consultation)
1. Sélectionnez un épisode dans la liste déroulante
2. Consultez le tableau des livres avec validation automatique
3. Identifiez rapidement les erreurs orthographiques (🔄)

### Correcteur d'épreuves (validation qualité)
1. Parcourez les épisodes récents
2. Vérifiez les suggestions (🔄) pour confirmer les corrections
3. Traitez manuellement les cas "Non trouvé" (❓)

### Enrichissement de données
1. Utilisez les suggestions validées pour mettre à jour la base de données
2. Récupérez les liens Babelio pour métadonnées supplémentaires (couverture, notes)

## Limitations connues

- **Rate limiting** : 1 requête/seconde vers Babelio (validation peut prendre quelques secondes)
- **Cas difficiles** : Inversions de nom, segmentation incorrecte nécessitent intervention manuelle
- **Dépendance externe** : Nécessite connexion internet pour interroger Babelio

## Migration automatique des URLs Babelio

### Objectif

Le système de migration enrichit automatiquement la base de données avec les URLs Babelio manquantes pour les livres et auteurs existants.

### Fonctionnement

**Phase 1 - Livres sans URL** :
- Recherche automatique sur Babelio par titre et auteur
- Validation de la correspondance avec normalisation du texte
- Extraction de l'URL auteur depuis la page livre
- Mise à jour automatique des champs `url_babelio`

**Phase 2 - Auteurs sans URL** :
- Détection des auteurs dont les livres ont une URL mais pas l'auteur
- Scraping de l'URL auteur depuis les pages livres existantes
- Complétion automatique des URLs manquantes

### Interface de gestion (`/babelio-migration`)

L'interface permet de gérer la migration et de traiter les cas problématiques :

**Statistiques** :
- Nombre total de livres et auteurs
- Taux de complétion des URLs Babelio
- Progression en temps réel

**Actions disponibles** :
- **Démarrer/Arrêter la migration** : Lancement des phases 1 et 2
- **Logs de progression** : Suivi détaillé livre par livre
- **Gestion des cas problématiques** : Traitement manuel des cas non résolus automatiquement

### Cas problématiques

Certains livres ou auteurs nécessitent un traitement manuel :

**Raisons fréquentes** :
- Titre trouvé sur Babelio ne correspond pas exactement
- Livre absent de Babelio (`babelio_not_found: true`)
- Auteur dont tous les livres sont absents de Babelio

**Actions manuelles** :
- **Accepter la suggestion** : Valider l'URL proposée malgré la différence de titre
- **Marquer comme non trouvé** : Confirmer l'absence sur Babelio
- **Supprimer du suivi** : Retirer des cas problématiques après traitement

### Affichage des liens Babelio

Les liens Babelio sont affichés sur les pages de détail :

**Pages livre** (`/livre/{id}`) :
- Icône Babelio 80x80px cliquable
- Lien direct vers la fiche Babelio du livre
- Design avec effet hover (couleur brand #FBB91E)

**Pages auteur** (`/auteur/{id}`) :
- Icône Babelio 80x80px cliquable
- Lien direct vers la fiche Babelio de l'auteur
- Layout cohérent avec les liens RadioFrance

### Normalisation intelligente

Le système normalise automatiquement les textes pour améliorer la correspondance :

**Transformations appliquées** :
- Ligatures : œ → oe, æ → ae
- Apostrophes typographiques : ' → '
- Suppression de la ponctuation
- Conversion en minuscules

**Stratégie de secours** :
- Recherche titre + auteur en priorité
- Si échec → Recherche auteur seul
- Scraping de l'URL depuis la page résultat

### Rate limiting

Le système respecte les limitations de Babelio :

- **Délai entre requêtes** : 5 secondes
- **Gestion gracieuse** : Arrêt automatique si Babelio indisponible
- **Reprise possible** : La migration peut être relancée à tout moment

## En cas de problème

1. **Erreur de connexion** : Vérifiez votre connexion internet, puis cliquez sur Retry
2. **Résultats incorrects** : Signalez via GitHub Issues avec exemple précis (auteur + titre)
3. **Performance lente** : Normal avec beaucoup de livres (rate limiting Babelio 5 sec/requête)
4. **Migration bloquée** : Consultez les logs de progression pour identifier le problème
5. **Babelio indisponible** : La migration s'arrête automatiquement, relancez plus tard

## Documentation technique

Pour comprendre le fonctionnement détaillé du système de validation :

📖 **Développeurs** : Consultez [biblio-verification-flow.md](../dev/biblio-verification-flow.md)

📖 **Tests** : Consultez [validation-biblio-tests.md](../dev/validation-biblio-tests.md)
