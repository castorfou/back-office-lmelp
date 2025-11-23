# Masquage des Épisodes - Back-Office LMELP

## Vue d'ensemble

La fonctionnalité de masquage permet de cacher temporairement des épisodes de l'interface utilisateur sans les supprimer de la base de données. Les épisodes masqués sont automatiquement exclus de toutes les vues publiques et des statistiques.

## Cas d'usage

### Pourquoi masquer un épisode ?

- **Épisodes courts** : Filtrer les épisodes de durée insuffisante (< 10 minutes)
- **Contenu hors sujet** : Masquer les émissions spéciales ou hors format
- **Test et validation** : Exclure temporairement des épisodes en cours de correction
- **Gestion de la qualité** : Cacher les épisodes avec des données incomplètes

### Avantages par rapport à la suppression

✅ **Réversible** : Un épisode masqué peut être rendu visible à tout moment
✅ **Données préservées** : Toutes les métadonnées et corrections restent intactes
✅ **Historique maintenu** : Les références et liens sont conservés
✅ **Audit trail** : Possibilité de suivre les épisodes masqués

## Accès à l'interface

### Depuis le tableau de bord

1. Ouvrez le **Dashboard** (page d'accueil)
2. Localisez la carte **"Masquer des Épisodes"** (icône 🚫)
3. Le badge indique le nombre d'épisodes actuellement masqués
4. Cliquez sur la carte pour accéder à la page de gestion

**Note** : La carte n'apparaît que s'il existe au moins un épisode masqué.

### Navigation directe

URL directe : `/masquer-episodes`

## Interface de gestion

### Vue tableau

L'interface présente tous les épisodes (masqués et visibles) dans un tableau avec :

| Colonne | Description | Triable |
|---------|-------------|---------|
| **Titre** | Titre de l'épisode | ✅ |
| **Durée** | Durée au format `XXh YYmin` ou `XXmin` | ✅ |
| **Date** | Date de publication au format `JJ/MM/AAAA` | ✅ |
| **Visibilité** | Statut visible/masqué avec toggle | ✅ |

### Filtrage et recherche

**Barre de recherche** :
- Placée en haut du tableau
- Recherche dans le titre ET la date
- Filtrage en temps réel (pas besoin d'appuyer sur Entrée)
- Insensible à la casse

**Exemple** :
```
Filtrer par titre ou date...
> "2024-11"           → Tous les épisodes de novembre 2024
> "sylvain tesson"    → Épisodes mentionnant Sylvain Tesson
> "court"             → Épisodes avec "court" dans le titre
```

### Tri des colonnes

**Cliquez sur l'en-tête de colonne** pour trier :
- **Premier clic** : Tri ascendant (A→Z, 0→9, ancien→récent)
- **Deuxième clic** : Tri descendant (Z→A, 9→0, récent→ancien)
- **Indicateur visuel** : Flèche ↑ (ascendant) ou ↓ (descendant)

**Tri par défaut** : Date décroissante (épisodes les plus récents en premier)

**Cas particuliers** :
- **Durée** : Les épisodes sans durée apparaissent en dernier
- **Visibilité** : Tri avec masqués en premier par défaut

## Actions de masquage

### Masquer un épisode

1. **Localisez** l'épisode dans le tableau
2. **Cliquez** sur le bouton **"👁️ Visible"** (bouton grisé)
3. Le bouton devient **"🚫 Masqué"** (fond rouge)
4. L'épisode est **immédiatement masqué** de toutes les vues publiques

**Mise à jour optimiste** : L'interface se met à jour instantanément sans attendre la confirmation du serveur.

### Rendre visible un épisode masqué

1. **Localisez** l'épisode masqué (bouton rouge "🚫 Masqué")
2. **Cliquez** sur le bouton **"🚫 Masqué"**
3. Le bouton redevient **"👁️ Visible"** (bouton grisé)
4. L'épisode est **immédiatement visible** dans toutes les vues publiques

### Indication visuelle

**Épisode visible** :
```
┌─────────────────────────┐
│ 👁️ Visible              │  ← Bouton gris clair
└─────────────────────────┘
```

**Épisode masqué** :
```
┌─────────────────────────┐
│ �� Masqué               │  ← Bouton fond rouge
└─────────────────────────┘
```

## Impact du masquage

### Zones affectées

Les épisodes masqués sont **automatiquement exclus** de :

- ✅ **Liste des épisodes** (page principale)
- ✅ **Statistiques globales** (Dashboard)
  - Total épisodes
  - Avis critiques analysés
  - Statistiques par type
- ✅ **Recherche textuelle** (résultats de recherche)
- ✅ **Extraction Livres/Auteurs** (sélection d'épisodes)
- ✅ **Pages de détail** (auteurs, livres)

### Zones non affectées

Les épisodes masqués restent **accessibles** dans :

- ✅ **Page de masquage** (vue administrative)
- ✅ **Base de données MongoDB** (données préservées)
- ✅ **API backend** avec flag `include_masked=true`

### Statistiques

Le Dashboard affiche :
- **Total épisodes** : Compte uniquement les épisodes **visibles**
- **Épisodes masqués** : Compteur dédié (affiché si > 0)

**Exemple** :
```
📊 STATISTIQUES

Total épisodes        : 215
Épisodes masqués      : 8
Avis critiques        : 142
```

## Workflow recommandé

### Masquage de nouveaux épisodes

```
1. Navigation
   └─> Dashboard → Carte "Masquer des Épisodes"

2. Tri par durée
   └─> Cliquer sur colonne "Durée" (épisodes courts en premier)

3. Filtrage (optionnel)
   └─> Rechercher "court" ou durée spécifique

4. Masquage
   └─> Cliquer boutons "Visible" des épisodes à masquer

5. Vérification
   └─> Dashboard → Vérifier nouveau total d'épisodes
```

### Révision des épisodes masqués

```
1. Accès
   └─> Dashboard → Carte "Masquer des Épisodes"

2. Tri par visibilité
   └─> Cliquer sur colonne "Visibilité" (masqués en premier)

3. Filtrage (optionnel)
   └─> Rechercher par titre ou date

4. Révision
   └─> Examiner chaque épisode masqué
   └─> Décider : maintenir masqué ou rendre visible

5. Action
   └─> Cliquer boutons "Masqué" pour rendre visibles si nécessaire
```

## Bonnes pratiques

### Critères de masquage

✅ **Masquer si** :
- Durée < 10 minutes (épisodes fragmentés ou incomplets)
- Contenu hors format (bandes-annonces, résumés)
- Données incomplètes (transcription manquante)
- Doublon (même contenu publié deux fois)

❌ **Ne PAS masquer si** :
- Simplement besoin de corrections (utiliser l'édition)
- Épisode rare mais valide
- Contenu exceptionnel même si court
- En cas de doute (privilégier la visibilité)

### Gestion régulière

**Fréquence recommandée** : Mensuelle

1. **Tri par date** : Examiner les nouveaux épisodes du mois
2. **Tri par durée** : Vérifier les épisodes courts
3. **Révision** : Revoir les épisodes masqués précédemment
4. **Statistiques** : Vérifier l'impact sur les totaux

### Documentation

Bien que l'application ne conserve pas (encore) de notes sur le masquage, documentez vos décisions :

**Journal de masquage recommandé** :
```
Date       | Épisode ID | Titre             | Raison
-----------|------------|-------------------|------------------
2025-11-23 | 6773e322...| Courts métrages  | Durée 3 min
2025-11-23 | 6773e323...| Bande-annonce    | Hors format
```

## Limitations et contraintes

### Limites actuelles

- ❌ **Pas de masquage groupé** : Chaque épisode doit être masqué individuellement
- ❌ **Pas de filtrage par durée** : Pas de filtre "< X minutes" automatique
- ❌ **Pas d'historique** : Les changements de statut ne sont pas tracés
- ❌ **Pas de commentaires** : Impossible d'annoter la raison du masquage

### Performances

**Tableau optimisé** :
- Charge instantanée pour < 500 épisodes
- Tri et filtrage temps réel performants
- Pas de pagination nécessaire (tous les épisodes visibles)

**Mise à jour** :
- Sauvegarde instantanée (optimistic update)
- Pas de rechargement de page requis
- Confirmation visuelle immédiate

## Dépannage

### Le bouton ne répond pas

**Symptômes** : Click sur le bouton sans effet

**Solutions** :
1. Vérifier la connexion réseau
2. Rafraîchir la page (F5)
3. Vérifier les logs navigateur (F12 → Console)
4. Vérifier que le backend est démarré

### L'épisode ne disparaît pas du Dashboard

**Cause** : Les épisodes masqués ne disparaissent pas de la page de masquage (par design)

**Vérification** :
1. Aller sur la page principale (liste d'épisodes)
2. Vérifier que l'épisode n'apparaît plus
3. Vérifier les statistiques (total décrémenté)

### Les statistiques semblent incorrectes

**Diagnostic** :
1. Compter manuellement les épisodes visibles
2. Comparer avec le total affiché
3. Vérifier le nombre d'épisodes masqués

**Si incohérence** :
- Rafraîchir le Dashboard
- Vérifier les logs backend
- Signaler le problème si persistant

## Référence technique

### Format des durées

```
Secondes | Affichage
---------|----------
45       | 45 s
120      | 2 min
3600     | 1h 00 min
3663     | 1h 01 min
null     | -
```

### Format des dates

```
ISO 8601                  | Affichage
--------------------------|------------
2024-11-10T09:59:39Z     | 10/11/2024
2024-01-05T00:00:00Z     | 05/01/2024
null                      | -
```

### Statuts possibles

| Statut | Champ `masked` | Icône | Couleur |
|--------|----------------|-------|---------|
| Visible | `false` ou absent | 👁️ | Gris |
| Masqué | `true` | 🚫 | Rouge |

## Support

### En cas de problème

1. **Vérifier** la console navigateur (F12)
2. **Consulter** [Troubleshooting](troubleshooting.md)
3. **Signaler** via GitHub Issues si bug persistant

### Évolutions futures

**Fonctionnalités prévues** :
- Masquage groupé par critères (durée, date, type)
- Historique des masquages/démasquages
- Commentaires et annotations
- Export CSV des épisodes masqués
- Règles automatiques de masquage

---

**Voir aussi** :
- [Gestion des épisodes](episodes.md)
- [Interface utilisateur](interface.md)
- [Dépannage](troubleshooting.md)
