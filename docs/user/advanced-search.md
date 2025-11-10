# Recherche Avancée

La fonctionnalité de recherche avancée permet de rechercher efficacement des contenus dans toutes les collections de la base de données avec des filtres interactifs et une pagination complète.

## Accès à la recherche avancée

### Depuis le Dashboard

Sur la page d'accueil, cliquez sur la carte **"Recherche avancée"** dans la section "Fonctions disponibles".

### Navigation

- **URL directe** : http://localhost:5173/search
- **Depuis le Dashboard** : Cliquez sur "Recherche avancée"
- **Retour au Dashboard** : Cliquez sur "🏠 Accueil"

## Vue d'ensemble de l'interface

```
┌─────────────────────────────────────────────────────────────┐
│ 🏠 Accueil    Recherche avancée                             │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    Recherche avancée                         │
│                                                              │
│  [ Rechercher dans les épisodes, auteurs, livres... ]  [🔍] │
│                                                              │
│  Filtrer par catégorie :                                     │
│  ☑ Épisodes  ☑ Auteurs  ☑ Livres  ☑ Éditeurs               │
│                                                              │
│  Résultats par page : [10 ▼]                                │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  📺 Épisodes (15 résultats)                                 │
│  ─────────────────────────────────────────────────────────  │
│  • Épisode 1 sur Albert Camus (03/08/2025)                  │
│    Contexte : ...discussion sur Albert Camus et son œuvre...│
│  • Épisode 2 sur La Peste (10/08/2025)                      │
│    Contexte : ...analyse de La Peste de Camus...            │
│                                                              │
│  < Précédent  [1] 2 3  Suivant >                            │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  ✍️ Auteurs (1 résultat)                                    │
│  ─────────────────────────────────────────────────────────  │
│  • Albert Camus (3 livres)                                   │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  📚 Livres (2 résultats)                                    │
│  ─────────────────────────────────────────────────────────  │
│  • L'Étranger - Albert Camus (Gallimard)                    │
│  • La Peste - Albert Camus (Gallimard)                       │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  🏢 Éditeurs (1 résultat)                                   │
│  ─────────────────────────────────────────────────────────  │
│  • Gallimard                                                 │
└─────────────────────────────────────────────────────────────┘
```

## Utilisation pas à pas

### 1. Effectuer une recherche

#### Saisie du terme de recherche

1. **Tapez** votre terme de recherche dans la barre de recherche
2. **Minimum 3 caractères** requis
3. **Appuyez sur Entrée** ou cliquez sur l'icône de recherche 🔍

📋 *La recherche est insensible à la casse : "CAMUS", "camus" et "Camus" donneront les mêmes résultats*

#### Exemples de recherches

```
Recherche d'auteur :
"camus" → Trouve Albert Camus et ses livres

Recherche de livre :
"étranger" → Trouve "L'Étranger" et épisodes mentionnant le livre

Recherche d'éditeur :
"gallimard" → Trouve l'éditeur et tous les livres publiés

Recherche dans épisodes :
"littérature" → Trouve tous les épisodes discutant de littérature
```

### 2. Filtrer les résultats

#### Filtres par catégorie

Utilisez les cases à cocher pour affiner votre recherche :

- **☑ Épisodes** : Recherche dans les titres, descriptions et transcriptions
- **☑ Auteurs** : Recherche dans les noms d'auteurs
- **☑ Livres** : Recherche dans les titres de livres
- **☑ Éditeurs** : Recherche dans les noms d'éditeurs

**Par défaut** : Toutes les catégories sont sélectionnées.

#### Comment filtrer

1. **Décochez** les catégories que vous ne voulez pas voir
2. **Cliquez sur "Rechercher"** pour actualiser les résultats
3. **Recochez** pour réafficher les catégories

💡 *Astuce : Pour rechercher uniquement des auteurs, décochez toutes les catégories sauf "Auteurs"*

### 3. Naviguer dans les résultats

#### Pagination

Pour les catégories avec de nombreux résultats :

- **Boutons de navigation** : "< Précédent" et "Suivant >"
- **Numéros de page** : Cliquez directement sur un numéro
- **Page courante** : Affichée en surbrillance
- **Indicateur total** : "Page 1 sur 5" au-dessus des résultats

#### Résultats par page

Ajustez le nombre de résultats affichés par page :

1. **Cliquez** sur le sélecteur "Résultats par page"
2. **Choisissez** : 10, 20, 50 ou 100 résultats
3. **Pagination automatique** : Mise à jour instantanée

📊 *Recommandation : Utilisez 10 résultats pour un aperçu rapide, 50-100 pour une analyse exhaustive*

### 4. Comprendre les résultats

#### Structure des résultats

Chaque catégorie affiche ses résultats dans un bloc distinct :

**📺 Épisodes**
- **Titre** de l'épisode
- **Date** de diffusion (format JJ/MM/AAAA)
- **Contexte de recherche** : Extrait avec 10 mots avant/après le terme
- **Compteur total** : Nombre total de résultats trouvés

**✍️ Auteurs**
- **Nom** de l'auteur
- **Nombre de livres** en base de données
- **Compteur total** : Nombre d'auteurs trouvés

**📚 Livres**
- **Titre** du livre
- **Nom de l'auteur** (format "Titre - Auteur")
- **Éditeur** entre parenthèses
- **Compteur total** : Nombre de livres trouvés

**🏢 Éditeurs**
- **Nom** de l'éditeur
- **Compteur total** : Nombre d'éditeurs uniques trouvés

#### Contexte de recherche pour les épisodes

Le contexte montre où le terme de recherche apparaît dans l'épisode :

```
Exemple pour la recherche "camus" :
"...discussion sur Albert Camus et son œuvre majeure L'Étranger qui..."
                    ↑
             Terme trouvé
```

- **10 mots avant** le terme de recherche
- **Le terme de recherche** lui-même
- **10 mots après** le terme

## Fonctionnalités avancées

### Compteurs totaux vs résultats affichés

La recherche affiche deux informations distinctes :

- **Résultats affichés** : Nombre de résultats sur la page courante (limité par "Résultats par page")
- **Total des résultats** : Nombre total de résultats trouvés dans la base de données

**Exemple** :
```
📺 Épisodes (15 résultats au total)
Page 1 sur 2 | Affichage de 10 résultats

→ Vous voyez 10 résultats ici
→ 15 résultats existent au total (5 sur la page 2)
```

### Recherche dans plusieurs sources

La recherche éditeurs combine plusieurs sources de données :

1. **Collection éditeurs** : Éditeurs créés manuellement
2. **Livres avec éditeur** : Éditeurs extraits des livres
3. **Déduplication automatique** : Chaque éditeur n'apparaît qu'une seule fois

**Résultat** : Vous voyez tous les éditeurs uniques, qu'ils soient dans la collection dédiée ou extraits des métadonnées de livres.

### Cas particuliers

#### Recherche sans résultats

Si aucun résultat n'est trouvé :

```
Aucun résultat trouvé pour "terme"

Suggestions :
- Vérifiez l'orthographe
- Essayez des termes plus généraux
- Utilisez moins de filtres
```

#### Recherche avec terme trop court

Si le terme de recherche contient moins de 3 caractères :

```
❌ Erreur
Le terme de recherche doit contenir au moins 3 caractères.
```

💡 *Exemple : "ca" ne fonctionne pas, mais "cam" ou "camus" fonctionnent*

## Conseils d'utilisation

### Bonnes pratiques

✅ **À faire :**
- Utiliser des termes de recherche spécifiques (3+ caractères)
- Filtrer par catégorie pour des résultats ciblés
- Ajuster "Résultats par page" selon vos besoins
- Utiliser la pagination pour explorer tous les résultats
- Vérifier le compteur total pour évaluer l'étendue des résultats

❌ **À éviter :**
- Rechercher avec moins de 3 caractères
- Ignorer les filtres si vous cherchez une catégorie précise
- Oublier de consulter les pages suivantes

### Optimisation du workflow

1. **Recherche large d'abord** : Laissez tous les filtres activés
2. **Analysez les compteurs** : Identifiez où se trouvent la plupart des résultats
3. **Filtrez par catégorie** : Décochez les catégories non pertinentes
4. **Ajustez la pagination** : Augmentez à 50-100 si beaucoup de résultats
5. **Explorez les pages** : Parcourez toutes les pages pour une vue exhaustive

### Cas d'usage courants

#### Trouver tous les livres d'un auteur

```
1. Recherchez le nom de l'auteur (ex: "camus")
2. Décochez toutes les catégories sauf "Livres"
3. Ajustez "Résultats par page" à 100
4. Parcourez tous les résultats
```

#### Trouver les épisodes mentionnant un sujet

```
1. Recherchez le sujet (ex: "existentialisme")
2. Décochez toutes les catégories sauf "Épisodes"
3. Lisez les contextes de recherche pour vérifier la pertinence
4. Cliquez sur les épisodes pertinents pour écouter/lire la transcription
```

#### Vérifier les livres d'un éditeur

```
1. Recherchez le nom de l'éditeur (ex: "gallimard")
2. Gardez "Éditeurs" et "Livres" cochés
3. Décochez "Auteurs" et "Épisodes"
4. Consultez la liste complète des livres publiés
```

## Limitations connues

### Recherche par accents

**Comportement actuel** :
- La recherche est **sensible aux accents**
- "carre" ne trouve **pas** "Carrère"
- "carrere" ne trouve **pas** "Carrère"

**Workaround** :
- Essayez plusieurs variantes orthographiques
- Utilisez des termes sans accents si possible

**Futur** : L'implémentation d'une recherche insensible aux accents est prévue (nécessite des collations MongoDB avancées ou normalisation Unicode).

### Performance avec grands résultats

- Les recherches retournant **>1000 résultats** peuvent être lentes
- La pagination se fait côté serveur pour optimiser les performances
- Utilisez les filtres pour réduire le nombre de résultats

## Support et aide

### Ressources disponibles

- **[Guide utilisateur principal](README.md)** : Vue d'ensemble de l'application
- **[Gestion des épisodes](episodes.md)** : Modification des épisodes trouvés
- **[Résolution de problèmes](troubleshooting.md)** : Solutions aux problèmes courants

### Contact support

En cas de problème avec la recherche :

1. **Vérifiez** que le serveur backend fonctionne
2. **Rechargez** la page (F5 ou Ctrl+R)
3. **Consultez** les logs de la console navigateur (F12)
4. **Contactez** l'équipe technique avec les détails de l'erreur

---

*Cette fonctionnalité est disponible depuis la version actuelle du Back-Office LMELP. Pour les développeurs, consultez la [documentation API](../dev/api.md#advanced-search-api).*
