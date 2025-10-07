# Extraction des Livres et Auteurs

La fonctionnalité d'extraction permet d'identifier et de cataloguer les livres, auteurs et éditeurs mentionnés dans les avis critiques du Masque et la Plume en analysant les tableaux markdown structurés des résumés d'épisodes.

## Accès à la fonctionnalité

1. **Navigation** : Cliquez sur "Livres et Auteurs" dans le menu principal
2. **URL directe** : `/livres-auteurs`

## Vue d'ensemble

### Informations affichées

La page présente un tableau avec quatre colonnes :

- **Auteur** : Nom de l'auteur du livre
- **Titre** : Titre du livre
- **Éditeur** : Maison d'édition (peut être vide si non mentionné)
- **Validation Babelio** : Vérification automatique des données via l'API Babelio

### Statistiques simplifiées

En haut de page, vous trouverez deux types de compteurs :

#### Nombre de livres extraits
Un compteur indique le nombre total de livres extraits de l'épisode sélectionné.

#### Statistiques de validation (livres au programme)
Pour les livres au programme (livres discutés + coups de cœur), un compteur détaillé affiche leur statut de validation :

**Format** : `— au programme : X traités, Y suggested, Z not found`

- **Traités** : Livres déjà sauvegardés dans MongoDB (statut `mongo`)
- **Suggested** : Livres avec suggestions Babelio en attente de validation
- **Not found** : Livres non trouvés sur Babelio, nécessitant une saisie manuelle

**Exemple** : `10 livre(s) extrait(s) — au programme : 6 traités, 2 suggested, 2 not found`

Cet affichage permet de suivre rapidement la progression du traitement des livres d'un épisode.

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

## Validation Babelio

### Vue d'ensemble
Chaque ligne du tableau dispose d'une colonne "Validation Babelio" qui vérifie automatiquement l'orthographe et l'exactitude des informations d'auteur en temps réel via l'API de Babelio.com.

### Indicateurs visuels

La validation affiche différents statuts :

- **✅ Validé** : Les données correspondent parfaitement à la base Babelio
- **🔄 Suggestion** : Babelio propose une correction (ex: "Michel Houellebeck" → "Michel Houellebecq")
- **❓ Non trouvé** : Aucune correspondance trouvée sur Babelio
- **⚠️ Erreur** : Problème technique (possibilité de réessayer avec le bouton ↻)
- **⏳ Vérification...** : Validation en cours

### Fonctionnement automatique

- **Validation immédiate** : Dès l'affichage du tableau, chaque auteur est vérifié
- **Rate limiting** : Respect de la limite de 1 requête/seconde vers Babelio
- **Suggestions** : Affichage des corrections proposées à côté des données originales
- **Retry** : Possibilité de relancer une vérification en cas d'erreur

### Cas d'usage

- **Détection d'erreurs** : Identifier rapidement les fautes de transcription Whisper
- **Correction automatique** : Voir les suggestions de correction orthographique
- **Validation qualité** : S'assurer de la fiabilité des données extraites

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

## Gestion des Collections (Nouveauté - Issue #66)

### Vue d'ensemble

Le système de gestion des collections automatise la création et la maintenance des collections `auteurs` et `livres` dans MongoDB à partir des livres extraits et validés via Babelio.

### Fonctionnalités principales

#### Statistiques en temps réel
La page affiche des compteurs automatiquement mis à jour :
- **Épisodes non traités** : Nombre d'épisodes avec avis critiques non encore analysés
- **Couples en base** : Livres/auteurs déjà présents dans les collections MongoDB
- **Avis critiques analysés** : Nombre d'avis critiques distincts ayant été traités et analysés
- **Couples suggérés non en base** : Livres avec corrections Babelio proposées, en attente de validation manuelle
- **Couples non trouvés non en base** : Livres non trouvés sur Babelio, nécessitant une saisie manuelle

#### Traitement automatique des livres validés
Un bouton "Traiter automatiquement les livres validés" permet de :
- Créer automatiquement les auteurs et livres validés par Babelio dans les collections MongoDB
- Maintenir les références croisées entre collections
- Éviter les doublons grâce à la vérification existence avant création
- Marquer automatiquement les livres traités avec le statut "mongo" (en base)

#### Validation manuelle des suggestions
Pour les livres avec corrections proposées par Babelio :
- Interface de validation permettant d'accepter ou modifier les suggestions
- Sauvegarde des données corrigées dans les collections MongoDB
- Mise à jour du statut de validation

#### Ajout manuel des livres non trouvés
Pour les livres non identifiés par Babelio :
- Formulaire de saisie manuelle des informations (auteur, titre, éditeur)
- Création forcée dans les collections avec marquage spécial
- Traçabilité des ajouts manuels

### Architecture technique

#### Collections MongoDB créées
- **`auteurs`** : Collection dédiée aux auteurs avec références vers leurs livres
- **`livres`** : Collection dédiée aux livres avec références vers épisodes et avis critiques

#### Intégration avec les données existantes
- Liaison avec la collection `episodes` existante
- Liaison avec la collection `avis_critiques` existante
- Maintien de la cohérence référentielle

#### Modèles de données

**Auteur** :
```json
{
  "_id": "ObjectId",
  "nom": "Michel Houellebecq",
  "livres": ["ObjectId_livre_1", "ObjectId_livre_2"],
  "created_at": "2024-01-01T10:00:00Z",
  "updated_at": "2024-01-01T10:00:00Z"
}
```

**Livre** :
```json
{
  "_id": "ObjectId",
  "titre": "Les Particules élémentaires",
  "auteur_id": "ObjectId_auteur",
  "editeur": "Flammarion",
  "episodes": ["ObjectId_episode_1"],
  "avis_critiques": ["ObjectId_avis_1", "ObjectId_avis_2"],
  "created_at": "2024-01-01T10:00:00Z",
  "updated_at": "2024-01-01T10:00:00Z"
}
```

### Utilisation recommandée

#### Workflow de traitement des livres
1. **Extraction** : Utiliser la fonctionnalité d'extraction pour identifier les livres d'un épisode
2. **Validation Babelio** : Attendre la validation automatique via l'API Babelio
3. **Traitement automatique** : Cliquer sur "Traiter automatiquement" pour les livres vérifiés
4. **Validation manuelle** : Traiter individuellement les suggestions Babelio
5. **Saisie manuelle** : Compléter les informations des livres non trouvés

#### Bonnes pratiques
- Traiter régulièrement les livres vérifiés pour maintenir les collections à jour
- Vérifier les suggestions Babelio avant validation pour assurer la qualité
- Documenter les raisons des ajouts manuels pour traçabilité
- Surveiller les statistiques pour identifier les épisodes nécessitant traitement

### Évolutions prévues

Les prochaines améliorations incluront :
- **Vue globale** : Affichage de tous les livres de tous les épisodes
- **✅ Sauvegarde corrections** : Intégration des corrections Babelio dans MongoDB (IMPLÉMENTÉ)
- **✅ Interface d'administration** : Validation manuelle des extractions (IMPLÉMENTÉ)
- **Enrichissement** : Ajout d'images de couverture, résumés détaillés, et métadonnées
- **Export de données** : Possibilité d'exporter les listes en CSV ou autres formats
- **Tableau de bord** : Interface de monitoring des collections et statistiques avancées
