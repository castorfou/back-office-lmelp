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

## Ré-extraction manuelle depuis Babelio

La page détail d'un livre affiche un bouton orange **↻ Ré-extraire** (visible uniquement si le livre possède une URL Babelio) permettant de rafraîchir les données du livre.

### Données rafraîchies

- **Titre** : Titre complet depuis Babelio
- **Éditeur** : Nom de l'éditeur, stocké via la collection `editeurs` dédiée (avec recherche accent/case insensitive)
- **Auteur** : Nom et URL Babelio de l'auteur

### Fonctionnement

1. Cliquer sur le bouton **↻ Ré-extraire** (animation de rotation pendant le chargement)
2. Le système scrape les données fraîches depuis Babelio (~20 secondes)
3. Si des différences sont détectées, elles sont appliquées automatiquement
4. Une notification toast confirme le résultat :
     - **Vert** : Modifications appliquées avec succès
     - **Bleu** : Données déjà à jour (aucune modification nécessaire)
     - **Rouge** : Erreur lors de l'extraction

### Gestion des éditeurs

Lors du rafraîchissement, l'éditeur extrait est référencé dans la collection `editeurs` :

- Si l'éditeur existe déjà (recherche insensible aux accents et à la casse), son identifiant est réutilisé
- Sinon, un nouvel éditeur est créé automatiquement
- Le livre est mis à jour avec la référence `editeur_id` au lieu d'un simple champ texte

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

## Récupération automatique des couvertures

### Objectif

Le système récupère automatiquement les URLs de couvertures des livres depuis Babelio et les stocke dans le champ `url_cover` de la collection `livres`. Une fois récupérée, la couverture est affichée automatiquement dans la fiche détail du livre (`/livre/{id}`).

### Pré-requis : cookie Babelio

Le scraping de couvertures nécessite un cookie Babelio valide pour passer la protection anti-bot. Ce cookie est fourni par le navigateur, pas le serveur.

**Obtenir le cookie Babelio :**
1. Ouvrez [babelio.com](https://www.babelio.com) dans votre navigateur
2. Appuyez sur **F12** → onglet **Réseau** (Network)
3. Rechargez la page (F5)
4. Cliquez sur la première requête vers `babelio.com`
5. Dans l'onglet **En-têtes** → **En-têtes de la requête** → copiez la valeur du champ **Cookie**
6. Collez cette valeur dans la zone de texte de la section Couvertures

Le cookie est stocké temporairement dans le `sessionStorage` du navigateur et effacé à la fermeture de l'onglet.

### Lancer la migration des couvertures

Dans `/babelio-migration`, section **Couvertures** :

1. Collez votre cookie Babelio dans la zone prévue
2. Cliquez sur **Lancer la liaison des couvertures**
3. Le système traite les livres un par un, avec un délai de 5 secondes entre chaque requête
4. Les résultats s'affichent en temps réel :
   - ✅ Couverture récupérée avec succès
   - ⚠️ Redirection Babelio détectée (titre de page différent du titre attendu)
   - ❌ Erreur

### Statistiques des couvertures

| Indicateur | Signification |
|------------|--------------|
| **Liés à Babelio** | Livres ayant une URL Babelio (base de travail) |
| **Liés avec succès** | Livres avec `url_cover` récupérée |
| **À traiter manuellement** | Cas de redirection Babelio détectés |
| **En attente** | Livres restant à traiter |

### Cas à traiter manuellement (redirections Babelio)

Babelio redirige parfois une URL obsolète vers un livre différent. Lorsque cela se produit, le système détecte la redirection et affiche le cas dans la section **"À traiter manuellement"**.

**Pour chaque cas :**
- Le titre de la page Babelio réellement retournée est affiché
- Un champ URL est pré-rempli avec la couverture trouvée sur la mauvaise page (peut tout de même convenir si c'est la bonne couverture)
- **Sauvegarder** : accepte l'URL proposée (ou une URL modifiée manuellement)
- **Ignorer** : marque le cas comme traité sans sauvegarder de couverture

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
