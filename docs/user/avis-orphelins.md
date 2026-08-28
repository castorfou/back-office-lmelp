# Nettoyage des Avis Orphelins

## Vue d'ensemble

Un avis est un commentaire individuel d'un critique sur un livre, rattaché à une émission via le champ `livre_oid`. Un avis devient **orphelin** lorsque son `livre_oid` ne correspond plus à aucun livre existant en base — typiquement après une [fusion de doublons de livres](gestion-doublons.md) où un livre a été supprimé.

Depuis la correction du processus de fusion, les avis sont automatiquement repointés vers le livre survivant lors d'une fusion. La page de nettoyage reste disponible pour traiter les avis orphelins créés avant ce correctif, ou tout autre cas résiduel.

## Accès à la fonctionnalité

### Depuis le Dashboard

Sur la page d'accueil, une carte "Avis orphelins" affiche le nombre d'avis orphelins détectés. Cette carte est **masquée automatiquement** quand ce nombre est à 0.

**Navigation :** Cliquer sur la carte pour accéder à la page `/avis-orphelins`.

## Page de Nettoyage

La page liste chaque avis orphelin avec son contexte complet : titre du livre extrait, auteur, critique, commentaire et note.

### Détection automatique d'un livre correspondant

Pour chaque avis orphelin, la page recherche automatiquement un livre existant portant le même titre (comparaison insensible à la casse et aux accents). Deux cas se présentent :

#### Cas 1 — Un livre correspondant est trouvé

C'est le cas le plus fréquent : le livre existe toujours en base, sous un autre identifiant (typiquement après une fusion de doublons antérieure au correctif).

- Un message **"📚 Livre trouvé en base"** s'affiche avec le titre du livre suggéré.
- Le bouton **"Repointer vers ce livre"** permet de corriger l'avis en un clic : son `livre_oid` est mis à jour vers le livre suggéré.
- Le bouton **"Supprimer" est masqué** : supprimer cet avis détruirait une donnée réelle (le commentaire du critique) alors que le livre est toujours discuté dans l'émission. Une suppression dans ce cas désynchroniserait les avis de l'émission par rapport à ses livres réels, provoquant un faux badge "Émission avec problème" sur la page Émissions.

#### Cas 2 — Aucun livre correspondant n'est trouvé

Le livre a été supprimé sans qu'aucun autre livre ne porte le même titre.

- Le bouton **"Repointer vers un autre livre"** reste disponible : il ouvre un champ de recherche pour sélectionner manuellement le livre correct si l'avis a été mal résolu.
- Le bouton **"Supprimer"** est visible : c'est alors l'action pertinente si l'avis ne correspond réellement plus à aucun livre.

### Repointage manuel

Si la suggestion automatique ne convient pas (ou en l'absence de suggestion), le bouton "Repointer vers un autre livre" ouvre un champ de recherche (minimum 3 caractères). Sélectionner un résultat repointe immédiatement l'avis vers ce livre.

### Suppression

La suppression demande une confirmation explicite avant d'être exécutée. Elle n'est proposée que lorsqu'aucun livre correspondant n'a été détecté automatiquement.

## Données Techniques

### Détection d'un avis orphelin

Un avis est considéré orphelin si son `livre_oid` (String) ne correspond à aucun `livres._id` (ObjectId) existant. La jointure utilise `$lookup` avec conversion de type (`$toObjectId`) puisque les deux champs sont de types différents.

### Détection du livre suggéré

Le matching s'effectue sur le titre normalisé (`normalize_for_matching()` : minuscules, sans accents, ligatures et tirets normalisés) entre `avis.livre_titre_extrait` et `livres.titre`. Ce n'est pas une recherche floue : seule une correspondance exacte après normalisation déclenche une suggestion.

### Endpoints API

#### GET `/api/avis/orphaned/statistics`

Retourne le nombre d'avis orphelins.

**Réponse :**
```json
{"orphaned_count": 4}
```

#### GET `/api/avis/orphaned`

Retourne la liste détaillée des avis orphelins, avec suggestion de livre le cas échéant.

**Réponse :**
```json
[
  {
    "id": "id_avis",
    "livre_oid": "id_livre_supprime",
    "livre_titre_extrait": "Titre du livre",
    "auteur_nom_extrait": "Nom de l'auteur",
    "critique_nom_extrait": "Nom du critique",
    "emission_oid": "id_emission",
    "commentaire": "Commentaire du critique...",
    "note": 4,
    "suggested_livre_id": "id_livre_existant",
    "suggested_livre_titre": "Titre du livre"
  }
]
```

`suggested_livre_id` et `suggested_livre_titre` valent `null` quand aucun livre correspondant n'est trouvé.

#### PUT `/api/avis/{avis_id}`

Repointe un avis vers un autre livre (endpoint générique de modification d'avis, réutilisé pour le repointage).

**Requête :**
```json
{"livre_oid": "id_livre_existant"}
```

#### DELETE `/api/avis/{avis_id}`

Supprime définitivement un avis.

## Bonnes Pratiques

1. **Toujours privilégier le repointage à la suppression** quand un livre correspondant existe — la suppression est irréversible et fait perdre un vrai commentaire de critique.
2. **Vérifier la page Émissions après une correction en masse** : le badge "Émission avec problème" révèle un écart entre le nombre de livres cités dans les avis et le nombre de livres liés à l'épisode en base — un signal qu'un repointage ou une suppression a introduit une désynchronisation.
3. **Ne pas supprimer un avis dont le livre semble juste renommé ou déplacé** : vérifier d'abord via la recherche manuelle qu'aucun livre correspondant n'existe réellement avant de conclure à une suppression.

## Voir aussi

- [Gestion des Doublons](gestion-doublons.md) — la fusion de doublons de livres est la cause principale des avis orphelins ; elle repointe désormais automatiquement les avis existants.
