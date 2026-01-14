# Gestion des Doublons

## Vue d'ensemble

La fonctionnalité de gestion des doublons permet de détecter et fusionner les livres et auteurs en doublon dans la base de données. Un doublon est détecté lorsque plusieurs entrées partagent la même URL Babelio.

## Accès à la fonctionnalité

### Depuis le Dashboard

Sur la page d'accueil (Dashboard), une carte "Doublons" affiche le nombre total de livres et auteurs en doublon détectés.

**Affichage :** Somme des doublons de livres + doublons d'auteurs

**Navigation :** Cliquer sur la carte "Doublons" pour accéder à la page de gestion des doublons.

## Page de Gestion des Doublons

La page `/duplicates` affiche deux sections principales :

### Section Statistiques

Cette section affiche des compteurs détaillés sur les doublons détectés :

#### 📚 Livres en doublon

- **Groupes de doublons** : Nombre de groupes de livres ayant la même URL Babelio
- **Total de livres** : Nombre total de livres en doublon (tous groupes confondus)

#### 👤 Auteurs en doublon

- **Groupes de doublons** : Nombre de groupes d'auteurs ayant la même URL Babelio
- **Total d'auteurs** : Nombre total d'auteurs en doublon (tous groupes confondus)

**Exemple :** Si 3 livres partagent l'URL Babelio A et 2 livres partagent l'URL Babelio B, vous aurez :
- Groupes de doublons : 2
- Total de livres : 5

### Section Groupes de Doublons

Cette section liste tous les groupes de doublons détectés, séparés en onglets :

- **📚 Livres** : Groupes de livres en doublon
- **👤 Auteurs** : Groupes d'auteurs en doublon

Chaque groupe affiche :

- **URL Babelio** : Lien vers la page officielle Babelio
- **Nombre d'entrées** : Combien d'entrées en doublon dans ce groupe
- **Titres/Noms** : Liste des titres (livres) ou noms (auteurs) concernés
- **Bouton "Fusionner ce groupe"** : Pour fusionner manuellement ce groupe
- **Case à cocher "Ignorer"** : Pour exclure ce groupe lors d'une fusion par lot

## Fusion Manuelle d'un Groupe

### Étapes

1. **Identifier le groupe** : Parcourir la liste des groupes de doublons
2. **Vérifier les données** : Cliquer sur l'URL Babelio pour vérifier les données officielles
3. **Fusionner** : Cliquer sur "Fusionner ce groupe"
4. **Résultat** : Un message de succès ou d'erreur s'affiche sous le groupe

### Que se passe-t-il lors d'une fusion ?

#### Pour les livres

1. **Validation** : Vérification que tous les doublons ont le même `auteur_id`
   - ❌ Si les `auteur_id` diffèrent, la fusion est rejetée (erreur affichée)

2. **Scraping Babelio** : Récupération des données officielles depuis l'URL Babelio
   - Titre complet (non tronqué)
   - Éditeur officiel

3. **Sélection livre primaire** : Le livre le plus ancien (`created_at` minimum) est conservé

4. **Fusion des données** :
   - Les épisodes de tous les doublons sont fusionnés (sans doublons)
   - Les avis critiques de tous les doublons sont fusionnés (sans doublons)

5. **Mise à jour** :
   - Le livre primaire reçoit le titre et éditeur officiels
   - Le livre primaire contient tous les épisodes et avis critiques
   - Les doublons sont supprimés de la base de données

6. **Mises à jour en cascade** :
   - Retrait des références aux doublons dans `auteurs.livres`
   - Mise à jour de `livresauteurs_cache` (remplacement des `book_id` doublons par le primaire)

7. **Historique** : Enregistrement dans la collection `duplicate_books_merge_history`

#### Pour les auteurs

Le processus est similaire :

1. **Validation** : Vérification de cohérence des données
2. **Scraping Babelio** : Récupération du nom officiel
3. **Sélection auteur primaire** : L'auteur le plus ancien est conservé
4. **Fusion des données** : Les livres de tous les doublons sont fusionnés
5. **Mise à jour** : L'auteur primaire reçoit le nom officiel et tous les livres
6. **Suppression** : Les doublons sont supprimés
7. **Historique** : Enregistrement dans `duplicate_authors_merge_history`

### Résultats possibles

#### ✅ Succès

Un encadré vert s'affiche avec les détails :

```
✅ Fusion réussie
- Livre/Auteur principal : [ID]
- Livres/Auteurs supprimés : [IDs]
- Épisodes fusionnés : [nombre]
- Avis critiques fusionnés : [nombre]
```

#### ❌ Erreur

Un encadré rouge s'affiche avec le message d'erreur :

**Erreurs courantes :**

- **`auteur_id mismatch`** : Les livres en doublon n'ont pas le même auteur (fusion refusée pour préserver l'intégrité)
- **Échec scraping Babelio** : L'URL Babelio n'a pas pu être consultée (fusion utilise alors les données existantes)
- **Livre/Auteur déjà fusionné** : Ce groupe a déjà été traité

## Fusion par Lot (Batch)

Pour fusionner plusieurs groupes automatiquement :

### Étapes

1. **Sélectionner groupes à ignorer** : Cocher les cases "Ignorer" pour les groupes à exclure
2. **Lancer fusion par lot** :
   - Cliquer sur "Fusionner tous les livres" (onglet Livres)
   - Ou cliquer sur "Fusionner tous les auteurs" (onglet Auteurs)
3. **Suivre progression** : Une barre de progression s'affiche avec le compteur
4. **Consulter résultats** : Les résultats apparaissent sous chaque groupe traité

### Comportement

- **Traitement séquentiel** : Les groupes sont fusionnés un par un
- **Délai entre groupes** : 1 seconde de pause entre chaque fusion (respect de Babelio)
- **Arrêt sur erreur** : Le traitement continue même si un groupe échoue
- **Mise à jour stats** : Les statistiques sont rafraîchies après chaque fusion

### Cas particulier : Rate Limiting

Pour respecter les serveurs externes (Babelio), un délai de 5 secondes est appliqué entre chaque requête de scraping. Cela peut ralentir la fusion par lot, mais protège contre le blocage.

## Dépannage

### Le groupe n'apparaît pas après fusion

**Cause :** Le groupe a été fusionné avec succès et n'est plus considéré comme doublon.

**Action :** Vérifier dans la collection MongoDB `duplicate_books_merge_history` ou `duplicate_authors_merge_history` pour confirmer l'historique.

### Erreur "auteur_id mismatch"

**Cause :** Les livres en doublon ont des auteurs différents (erreur de données).

**Action :**
1. Vérifier manuellement sur Babelio l'auteur correct
2. Corriger manuellement les `auteur_id` dans MongoDB
3. Relancer la fusion

### La fusion échoue toujours pour un groupe

**Cause :** Problème de données (champs manquants, types incorrects, etc.).

**Action :**
1. Consulter les logs backend pour plus de détails
2. Vérifier la structure des documents MongoDB
3. Signaler le problème si la cause n'est pas identifiable

### Les statistiques ne se mettent pas à jour

**Cause :** Cache navigateur ou problème de rechargement.

**Action :**
1. Rafraîchir la page (F5)
2. Vider le cache du navigateur
3. Vérifier que le backend est bien démarré

## Données Techniques

### Collections MongoDB

#### `livres`
- **Champ détection** : `url_babelio` (String)
- **Critère doublon** : Plusieurs livres avec même `url_babelio`
- **Champ de validation** : `auteur_id` (ObjectId ou String)

#### `auteurs`
- **Champ détection** : `url_babelio` (String)
- **Critère doublon** : Plusieurs auteurs avec même `url_babelio`

#### `duplicate_books_merge_history`
- **Contenu** : Historique des fusions de livres
- **Champs** :
  - `url_babelio` : URL Babelio du groupe fusionné
  - `primary_book_id` : ID du livre conservé
  - `deleted_book_ids` : IDs des livres supprimés
  - `episodes_merged` : Nombre d'épisodes fusionnés
  - `avis_critiques_merged` : Nombre d'avis critiques fusionnés
  - `merged_at` : Date et heure de la fusion

#### `duplicate_authors_merge_history`
- **Contenu** : Historique des fusions d'auteurs
- **Champs** : Structure similaire à `duplicate_books_merge_history`

### Endpoints API

#### GET `/api/books/duplicates/statistics`
Retourne les statistiques globales des doublons de livres.

**Réponse :**
```json
{
  "total_groups": 5,
  "total_duplicates": 12
}
```

#### GET `/api/books/duplicates/groups`
Retourne la liste des groupes de doublons de livres.

**Réponse :**
```json
[
  {
    "url_babelio": "https://www.babelio.com/livres/...",
    "count": 3,
    "book_ids": ["id1", "id2", "id3"],
    "titres": ["Titre 1", "Titre 1 v2", "Titre 1 v3"],
    "auteur_ids": ["author1", "author1", "author1"]
  }
]
```

#### POST `/api/books/duplicates/merge`
Fusionne un groupe de doublons de livres.

**Requête :**
```json
{
  "url_babelio": "https://www.babelio.com/livres/...",
  "book_ids": ["id1", "id2", "id3"]
}
```

**Réponse (succès) :**
```json
{
  "status": "success",
  "result": {
    "success": true,
    "primary_book_id": "id1",
    "deleted_book_ids": ["id2", "id3"],
    "episodes_merged": 5,
    "avis_critiques_merged": 3
  }
}
```

**Réponse (erreur) :**
```json
{
  "status": "error",
  "detail": "auteur_id mismatch: Expected ObjectId('aaa'), found ObjectId('bbb')"
}
```

#### POST `/api/books/duplicates/merge/batch`
Lance une fusion par lot avec liste d'exclusion.

**Requête :**
```json
{
  "skip_list": ["https://www.babelio.com/livres/url1", "..."]
}
```

**Réponse :** Flux de données Server-Sent Events (SSE) avec progression en temps réel.

#### Endpoints similaires pour auteurs

Les endpoints suivants existent avec le même schéma :
- `GET /api/authors/duplicates/statistics`
- `GET /api/authors/duplicates/groups`
- `POST /api/authors/duplicates/merge`
- `POST /api/authors/duplicates/merge/batch`

## Bonnes Pratiques

### Avant une fusion

1. **Vérifier sur Babelio** : Toujours consulter l'URL Babelio pour confirmer les données officielles
2. **Vérifier les auteurs** : Pour les livres, s'assurer que tous les doublons ont bien le même auteur
3. **Tester sur un groupe** : Avant une fusion par lot, tester sur un groupe pour valider le processus

### Pendant une fusion par lot

1. **Surveiller les résultats** : Vérifier qu'il n'y a pas trop d'erreurs
2. **Ignorer les cas douteux** : Utiliser la case "Ignorer" pour les groupes nécessitant une vérification manuelle
3. **Ne pas fermer la page** : Attendre la fin du traitement pour garantir la complétion

### Après une fusion

1. **Vérifier les statistiques** : Les compteurs du Dashboard doivent diminuer
2. **Consulter l'historique** : Vérifier dans les collections `*_merge_history`
3. **Tester les pages de détail** : S'assurer que les livres/auteurs fusionnés affichent correctement toutes les données

## Limites Connues

### Co-auteurs

**Limitation actuelle :** Les livres avec co-auteurs ne sont pas bien gérés par la fusion automatique.

**Comportement :** Si un livre a plusieurs auteurs (`auteur_id` est un array), la validation `auteur_id mismatch` peut échouer incorrectement.

**Contournement :** Traiter manuellement les fusions de livres avec co-auteurs en modifiant directement MongoDB.

### Scraping Babelio

**Limitation :** Le scraping peut échouer si :
- La page Babelio a changé de structure
- L'URL est invalide ou introuvable
- Le serveur Babelio est temporairement indisponible

**Fallback :** En cas d'échec, la fusion utilise les données existantes du livre le plus ancien.

### Performance

**Impact :** La fusion par lot peut prendre du temps si :
- Beaucoup de groupes à traiter
- Délais de rate limiting (5 secondes par scraping)
- Nombreux épisodes/avis critiques à fusionner

**Estimation :** Compter environ 10 secondes par groupe (scraping + traitement + délai).
