# Correction automatique des résumés d'épisodes

## Qu'est-ce que la correction automatique ?

Lorsque vous consultez la page **Livres & Auteurs** d'un épisode, le système vérifie automatiquement si les résumés (summaries) des avis critiques contiennent des erreurs et les corrige progressivement en arrière-plan.

## Comment ça fonctionne ?

### Détection automatique

Le système compare les données extraites par OCR avec les données validées par Babelio :

- **Données OCR** : auteur et titre extraits automatiquement (peuvent contenir des erreurs)
- **Données Babelio** : auteur et titre validés lors de la vérification bibliographique (Phase 0)

### Correction progressive

Lorsque vous visitez un épisode, le système :

1. ✅ **Vérifie** tous les livres déjà enregistrés dans la base de données
2. 🔍 **Détecte** les différences entre OCR et Babelio
3. 🔧 **Corrige** automatiquement les résumés si nécessaire
4. 💾 **Sauvegarde** une copie du résumé original

### Exemples de corrections

| Situation | Résultat |
|-----------|----------|
| **OCR** : "Sybille Grimbert" → **Babelio** : "Sibylle Grimbert" | ✅ Résumé corrigé automatiquement |
| **OCR** : "Simone Emonet" → **Babelio** : "Simone Émonet" | ✅ Accent ajouté automatiquement |
| **OCR** : "Amélie Nothomb" → **Babelio** : "Amélie Nothomb" | ℹ️ Aucune correction nécessaire |

## Quand la correction s'applique-t-elle ?

### ✅ Livres concernés

La correction automatique s'applique uniquement aux livres qui :

- Sont **déjà enregistrés** dans la base de données (`status: mongo`)
- Ont été **validés par Babelio** (ont des suggestions Phase 0)
- N'ont **pas encore été corrigés** (flag `summary_corrected: false`)

### ⏱️ Moment de déclenchement

La correction se déclenche **automatiquement** lorsque vous :

- Accédez à la page **Livres & Auteurs** d'un épisode
- Rechargez la page d'un épisode

Aucune action manuelle n'est requise de votre part.

## Indicateurs visuels

### Logs de traitement

Si des corrections sont apportées, vous verrez un message dans les logs système :

```
🧹 Cleanup épisode [ID]: X summaries corrigés
```

### Aucun impact utilisateur

La correction est **totalement transparente** :
- Aucune interruption du flux de travail
- Aucune confirmation requise
- Processus rapide et non bloquant

## Sauvegarde des données

### Protection du résumé original

Lors de la **première correction** d'un résumé :

- Le système sauvegarde automatiquement le résumé original dans `summary_origin`
- Vous pouvez toujours consulter la version originale si nécessaire
- Les corrections ultérieures préservent cette sauvegarde

### Idempotence

Le système est **idempotent** :
- Chaque livre n'est corrigé **qu'une seule fois**
- Les visites ultérieures ne retraitent pas les livres déjà corrigés
- Flag `summary_corrected: true` empêche les corrections multiples

## Cas d'usage typiques

### Scénario 1 : Nouvel épisode

1. Vous extrayez les livres d'un épisode
2. Le système vérifie avec Babelio (Phase 0)
3. Les livres sont enregistrés avec les données Babelio
4. Vous accédez à la page Livres & Auteurs
5. ✅ Le système corrige automatiquement les résumés si nécessaire

### Scénario 2 : Épisode ancien

1. Vous consultez un épisode traité il y a plusieurs semaines
2. Certains livres ont des résumés non corrigés
3. Vous ouvrez la page Livres & Auteurs
4. ✅ Le système détecte et corrige les résumés restants

### Scénario 3 : Réouverture d'un épisode

1. Vous rouvrez un épisode déjà visité
2. Les résumés ont déjà été corrigés (`summary_corrected: true`)
3. ℹ️ Aucun retraitement nécessaire
4. Affichage instantané

## Questions fréquentes

### Dois-je faire quelque chose pour activer la correction ?

**Non**. La correction est entièrement automatique et s'active lors de la consultation des épisodes.

### Puis-je voir quelles corrections ont été faites ?

Oui, consultez les logs système pendant la visite de la page. Le nombre de corrections est affiché.

### Que se passe-t-il si je recharge la page plusieurs fois ?

La correction ne s'applique **qu'une seule fois** par livre. Les rechargements ultérieurs n'ont aucun effet.

### Les résumés originaux sont-ils perdus ?

Non, le système sauvegarde automatiquement le résumé original dans `summary_origin` lors de la première correction.

### Puis-je désactiver la correction automatique ?

Non, cette fonctionnalité est intégrée au système et s'exécute automatiquement pour garantir la cohérence des données.

### Combien de temps prend la correction ?

La correction est **quasi-instantanée** (quelques millisecondes par livre). Vous ne remarquerez aucun ralentissement.

## Nettoyage automatique des espaces

### Correction des espaces parasites

Lors de la saisie ou de la validation des informations bibliographiques, le système supprime automatiquement les espaces en début et fin de champ. Cette fonctionnalité évite les problèmes de doublons et améliore la qualité des données.

**Champs concernés** :
- Auteur (OCR, suggestions Babelio, saisie manuelle)
- Titre (OCR, suggestions Babelio, saisie manuelle)
- Éditeur (OCR, saisie manuelle)

**Exemples de nettoyage** :

| Saisie utilisateur | Valeur enregistrée |
|--------------------|-------------------|
| `"  Albert Camus  "` | `"Albert Camus"` |
| `"L'Étranger "` | `"L'Étranger"` |
| `" Simone Émonet"` | `"Simone Émonet"` |

**Aucune action requise** : Le nettoyage est totalement transparent et s'applique automatiquement à chaque validation.

---

## Identification visuelle des épisodes traités

### Préfixe `*` dans la liste des épisodes

Dans le sélecteur d'épisodes de la page **Livres & Auteurs**, les épisodes déjà traités sont identifiés par un préfixe `*` :

**Exemple d'affichage** :
```
* 12/01/2025 - Les nouvelles pages du polar
  05/01/2025 - Littérature contemporaine
* 28/09/2024 - Spécial rentrée littéraire
```

**Signification** :
- **`*` présent** : L'épisode a déjà été consulté et contient des livres enregistrés
- **Pas de `*`** : L'épisode n'a pas encore été traité

**Utilité** :
- Repérer rapidement les épisodes déjà traités
- Éviter de retraiter un épisode déjà validé
- Navigation plus efficace dans l'historique

---

## Actualisation automatique des données

### Rechargement sans Ctrl+F5

En mode développement, l'application désactive automatiquement le cache du navigateur. Vous pouvez recharger la page avec un simple **F5** après un redémarrage du backend ou du frontend.

**Avantages** :
- Pas besoin de **Ctrl+F5** (vidage de cache forcé)
- Changements visibles immédiatement après redémarrage des services
- Expérience de développement plus fluide

**Note** : Cette fonctionnalité est active uniquement en mode développement. En production, le cache fonctionne normalement pour optimiser les performances.

---

## Références techniques

Pour plus de détails techniques sur le fonctionnement interne, consultez :

- [Documentation développeur - Ramasse-miettes](../dev/summary-garbage-collector.md)
- [Flux de vérification bibliographique](../dev/biblio-verification-flow.md)
- [Traitement des données bibliographiques](../dev/bibliographic-data-processing.md)
