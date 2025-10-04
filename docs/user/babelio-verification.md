# Guide Utilisateur - Validation Bibliographique

## Vue d'ensemble

La validation bibliographique vérifie automatiquement l'orthographe des auteurs et titres de livres extraits des avis critiques en utilisant la base de données Babelio.com.

## Accès à la fonctionnalité

**Navigation** : Menu principal → **Livres et Auteurs**

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

## En cas de problème

1. **Erreur de connexion** : Vérifiez votre connexion internet, puis cliquez sur Retry
2. **Résultats incorrects** : Signalez via GitHub Issues avec exemple précis (auteur + titre)
3. **Performance lente** : Normal avec beaucoup de livres (rate limiting Babelio)

## Documentation technique

Pour comprendre le fonctionnement détaillé du système de validation :

📖 **Développeurs** : Consultez [biblio-verification-flow.md](../dev/biblio-verification-flow.md)

📖 **Tests** : Consultez [validation-biblio-tests.md](../dev/validation-biblio-tests.md)
