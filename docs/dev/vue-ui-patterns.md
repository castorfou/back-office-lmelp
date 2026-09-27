# Charte graphique et patterns UI Vue.js

Ce document décrit les conventions visuelles et les patterns d'interface utilisateur utilisés dans les composants Vue.js de ce projet.

## Table des matières

- [Structure des composants](#structure-des-composants)
- [Cartes de statistiques](#cartes-de-statistiques)
- [États de chargement des données](#états-de-chargement-des-données)
- [États vides](#états-vides)
- [Boutons d'action](#boutons-daction)
- [Indicateurs de progression](#indicateurs-de-progression)
- [Opérations par lot](#opérations-par-lot)
- [Palette de couleurs](#palette-de-couleurs)

## Structure des composants

Toutes les vues principales suivent une structure cohérente :

```vue
<template>
  <div class="view-container">
    <Navigation />
    <main class="main-content">
      <!-- En-tête de page -->
      <header class="page-header">
        <h1>Titre de la page</h1>
        <p class="page-description">Brève description</p>
      </header>

      <!-- Section statistiques (si applicable) -->
      <section class="statistics-section">
        <!-- Cartes de stats -->
      </section>

      <!-- Contenu principal -->
      <section class="content-section">
        <!-- États : chargement, erreur, vide, ou données -->
      </section>
    </main>
  </div>
</template>
```

## Cartes de statistiques

Les statistiques sont affichées via des patterns de cartes cohérents.

### Cartes de statistiques du Dashboard

Utilisées sur le Dashboard pour les métriques de haut niveau cliquables pour naviguer :

```vue
<div class="stats-grid">
  <div
    class="stat-card clickable-stat"
    @click="navigateTo('/chemin')"
    :title="texteTooltip"
  >
    <div class="stat-value">{{ count !== null ? count : '...' }}</div>
    <div class="stat-label">Libellé</div>
  </div>
</div>
```

**Caractéristiques clés :**
- **Indicateur de chargement** : Afficher `'...'` tant que la donnée est null
- **Cliquable** : Utiliser la classe `clickable-stat` pour le curseur pointer
- **Tooltips** : Fournir du contexte via l'attribut `:title`
- **Grille responsive** : Utiliser `stats-grid` pour un layout 2-4 colonnes

### Cartes de statistiques détaillées

Utilisées sur les pages de fonctionnalités (comme DuplicateBooks) pour des métriques non cliquables :

```vue
<section class="statistics-section">
  <div class="statistics-card">
    <h2>Titre des statistiques</h2>

    <h3 class="stats-section-title">📚 Sous-section</h3>
    <div class="stats-grid">
      <div class="stat-item">
        <span class="stat-label">Nom de la métrique</span>
        <span class="stat-value">{{ value || 0 }}</span>
      </div>
    </div>
  </div>
</section>
```

**Caractéristiques clés :**
- **Titres de section avec emojis** : Hiérarchie visuelle (📚, 👤, etc.)
- **Items labelisés** : Paires `stat-label` + `stat-value`
- **Valeurs par défaut** : Afficher `0` au lieu de null pour une meilleure UX

## États de chargement des données

Toutes les vues implémentent un pattern à trois états pour le chargement des données :

```vue
<template>
  <!-- État de chargement -->
  <div v-if="loading" class="loading">
    Chargement des données...
  </div>

  <!-- État d'erreur -->
  <div v-if="error" class="alert alert-error">
    {{ error }}
  </div>

  <!-- État avec données -->
  <div v-if="!loading && !error && data.length > 0">
    <!-- Affichage des données -->
  </div>

  <!-- État vide -->
  <div v-if="!loading && !error && data.length === 0" class="empty-state">
    <p>Aucune donnée disponible 🎉</p>
  </div>
</template>

<script>
export default {
  data() {
    return {
      loading: true,
      error: null,
      data: []
    };
  },

  async mounted() {
    try {
      this.loading = true;
      this.error = null;
      this.data = await fetchData();
    } catch (err) {
      this.error = `Erreur lors du chargement: ${err.message}`;
    } finally {
      this.loading = false;
    }
  }
}
</script>
```

**Bonnes pratiques :**
- Toujours afficher un état de chargement pendant le fetch
- Afficher des messages d'erreur compréhensibles
- Fournir des états vides avec des messages positifs
- Utiliser des conditions `v-if` dans l'ordre de priorité : loading → error → data → empty

## États vides

Les états vides doivent être encourageants et informatifs :

```vue
<div class="empty-state">
  <p>Aucun doublon détecté (ni auteurs ni livres) ! 🎉</p>
</div>
```

**Recommandations :**
- Utiliser un langage positif quand l'absence est bonne (pas de doublons, pas d'erreurs)
- Inclure un emoji pour l'attrait visuel (optionnel mais courant dans ce projet)
- Garder le message concis (1-2 phrases)
- Centrer le texte pour un meilleur équilibre visuel

## Boutons d'action

Les styles de boutons suivent une hiérarchie sémantique :

### Actions primaires

```vue
<button class="btn btn-primary" @click="actionPrimaire">
  Texte de l'action
</button>
```

**Utilisation :** Action principale de la page (sauvegarder, soumettre, tout fusionner)

### Actions secondaires

```vue
<button class="btn btn-secondary" @click="actionSecondaire">
  Texte de l'action
</button>
```

**Utilisation :** Actions alternatives (annuler, ignorer, voir)

### Actions de fusion/traitement

```vue
<button
  class="btn btn-merge"
  :disabled="estEnTraitement"
  @click="fusionnerItem(item)"
>
  {{ estEnTraitement ? 'Fusion...' : 'Fusionner' }}
</button>
```

**Bonnes pratiques :**
- Afficher un texte dynamique pendant le traitement ("Fusion..." vs "Fusionner")
- Désactiver le bouton pendant les opérations asynchrones (`:disabled="estEnTraitement"`)
- Utiliser des noms de classes sémantiques (`btn-merge` pour les opérations de fusion)

### Boutons d'action large

Pour les actions importantes au niveau de la page :

```vue
<button class="btn btn-primary btn-large">
  {{ estEnCours ? statut : 'Tout fusionner' }}
</button>
```

**Caractéristiques :**
- Padding plus grand (15px vs 10px)
- Police plus grande (1.1rem vs 1rem)
- Centré dans son conteneur

## Indicateurs de progression

Pour les opérations par lot de longue durée :

```vue
<div class="batch-progress">
  <div class="progress-bar">
    <div
      class="progress-fill"
      :style="{ width: progressPercent + '%' }"
    ></div>
  </div>
  <p>{{ current }} / {{ total }} groupes traités</p>
</div>

<script>
computed: {
  progressPercent() {
    if (this.total === 0) return 0;
    return Math.round((this.current / this.total) * 100);
  }
}
</script>
```

**Structure CSS :**
```css
.progress-bar {
  width: 100%;
  height: 20px;
  background: #e9ecef;
  border-radius: 10px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #4CAF50, #45a049);
  transition: width 0.3s ease;
}
```

**Recommandations :**
- Afficher visuellement le remplissage en pourcentage
- Afficher le compteur textuel sous la barre ("5 / 10 groupes traités")
- Utiliser des transitions fluides pour les mises à jour de progression
- Gérer le cas limite total-zéro dans la propriété computed

## Opérations par lot

Pour traiter plusieurs éléments séquentiellement :

```vue
<template>
  <button
    class="btn btn-primary btn-large"
    :disabled="estEnCoursBatchGlobal"
    @click="demarrerFusionBatchGlobale"
  >
    {{ estEnCoursBatchGlobal ? statutBatchGlobal : 'Tout fusionner' }}
  </button>

  <div v-if="estEnCoursBatchGlobal" class="batch-progress">
    <!-- Indicateur de progression -->
  </div>
</template>

<script>
data() {
  return {
    estEnCoursBatchGlobal: false,
    statutBatchGlobal: '',
    progressionBatchGlobal: {
      current: 0,
      total: 0
    }
  };
},

methods: {
  async demarrerFusionBatchGlobale() {
    if (this.estEnCoursBatchGlobal) return;

    this.estEnCoursBatchGlobal = true;
    this.progressionBatchGlobal.current = 0;
    this.progressionBatchGlobal.total = this.items.length;

    for (let i = 0; i < this.items.length; i++) {
      const item = this.items[i];
      this.statutBatchGlobal = `Traitement (${i + 1}/${this.items.length})...`;

      await this.traiterItem(item);
      this.progressionBatchGlobal.current++;

      // Petit délai entre les opérations
      await new Promise(resolve => setTimeout(resolve, 1000));
    }

    // Réinitialisation de l'état
    this.estEnCoursBatchGlobal = false;
    this.statutBatchGlobal = '';
    this.progressionBatchGlobal = { current: 0, total: 0 };
  }
}
</script>
```

**Bonnes pratiques :**
- Protéger contre les exécutions multiples (`if (this.estEnCoursBatchGlobal) return`)
- Mettre à jour le texte de statut avec la position actuelle
- Ajouter des délais entre les opérations (rate limiting, feedback UX)
- Toujours réinitialiser l'état après completion
- Désactiver le bouton pendant le traitement

## Palette de couleurs

### États d'alerte

```css
/* Succès */
.result-success {
  background: #d4edda;
  color: #155724;
  border: 1px solid #c3e6cb;
}

/* Erreur */
.alert-error, .result-error {
  background: #f8d7da;
  color: #721c24;
  border: 1px solid #f5c6cb;
}

/* Info */
.alert-info {
  background: #d1ecf1;
  color: #0c5460;
  border: 1px solid #bee5eb;
}

/* Avertissement */
.alert-warning {
  background: #fff3cd;
  color: #856404;
  border: 1px solid #ffeaa7;
}
```

### Éléments interactifs

```css
/* Action primaire */
.btn-primary {
  background: #007bff;
  color: white;
}

.btn-primary:hover {
  background: #0056b3;
}

.btn-primary:disabled {
  background: #6c757d;
  cursor: not-allowed;
}

/* Stats cliquables */
.clickable-stat {
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
}

.clickable-stat:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}
```

## Chargement des données en parallèle

**CRITIQUE** : Charger toutes les statistiques en parallèle pour un affichage simultané :

```vue
async mounted() {
  // ❌ MAUVAIS - Chargement séquentiel (apparition échelonnée)
  await this.loadStatistics();
  await this.loadCollectionsStatistics();
  await this.loadDuplicateStatistics();

  // ✅ CORRECT - Chargement parallèle (tout apparaît ensemble)
  await Promise.all([
    this.loadStatistics(),
    this.loadCollectionsStatistics(),
    this.loadDuplicateStatistics()
  ]);
}
```

**Pourquoi c'est important :**
- Le chargement séquentiel fait apparaître les compteurs par vagues (mauvaise UX)
- Le chargement parallèle affiche toutes les données simultanément
- L'utilisateur perçoit un temps de chargement plus rapide même si le temps total est similaire

## Propriétés calculées pour statistiques combinées

Quand on affiche des sommes ou des statistiques dérivées :

```vue
<template>
  <div class="stat-value">{{ totalCount !== null ? totalCount : '...' }}</div>
</template>

<script>
data() {
  return {
    compteLivres: null,
    compteAuteurs: null
  };
},

computed: {
  totalCount() {
    // Retourner null si un composant est encore en chargement
    if (this.compteLivres === null || this.compteAuteurs === null) {
      return null;
    }
    return this.compteLivres + this.compteAuteurs;
  }
}
</script>
```

**Bonnes pratiques :**
- Retourner `null` si une des valeurs composantes est `null` (encore en chargement)
- Ne calculer la somme que quand toutes les données sont disponibles
- Afficher l'indicateur de chargement `'...'` quand la valeur calculée est `null`
- Évite d'afficher des sommes partielles incorrectes pendant le chargement

## Intégration de la navigation

Lier les cartes de statistiques aux pages pertinentes :

```vue
<template>
  <div class="stat-card clickable-stat" @click="naviguerVersDoublons">
    <div class="stat-value">{{ compteDoublons }}</div>
    <div class="stat-label">Doublons</div>
  </div>
</template>

<script>
methods: {
  naviguerVersDoublons() {
    this.$router.push('/duplicates');
  }
}
</script>
```

**Configuration du routeur :**

```javascript
// router/index.js
const routes = [
  {
    path: '/duplicates',
    name: 'DuplicateBooks',
    component: DuplicateBooks,
    meta: {
      title: 'Gestion des Doublons - lmelp'
    }
  }
];

// Mise à jour du titre de page lors de la navigation
router.afterEach((to) => {
  document.title = to.meta.title || 'lmelp';
});
```

## Considérations d'accessibilité

- Utiliser du HTML sémantique (`<button>`, `<section>`, `<header>`)
- Fournir des tooltips via l'attribut `:title` pour le contexte
- Assurer un contraste de couleur suffisant (suivre les standards WCAG AA)
- Utiliser l'attribut `:disabled` sur les boutons (pas seulement le style visuel)
- Inclure du texte descriptif pour les lecteurs d'écran

## Design responsive

Les grilles de statistiques se replient élégamment sur mobile :

```css
@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: 1fr; /* Une seule colonne sur mobile */
  }

  .stat-value {
    font-size: 1.5rem; /* Légèrement plus petit sur mobile */
  }
}
```

## Exemples

### Carte de statistiques Dashboard complète

Voir `frontend/src/views/Dashboard.vue:95-102` pour une implémentation complète d'une carte de statistiques cliquable avec compteurs combinés.

### Page de fonctionnalité complète

Voir `frontend/src/views/DuplicateBooks.vue` pour un exemple complet implémentant :
- Sections de statistiques avec sous-sections
- États de chargement/erreur/vide
- Opérations par lot avec progression
- Actions de fusion avec affichage des résultats
- Chargement des données en parallèle
