# Nouveautés Claude Code - Septembre 2025

**Date de l'annonce** : 29 septembre 2025
**Source** : [Enabling Claude Code to work more autonomously](https://anthropic.com/news/enabling-claude-code-to-work-more-autonomously)

## Vue d'ensemble

Cette mise à jour majeure de Claude Code introduit des fonctionnalités permettant un travail plus autonome et une meilleure intégration avec l'environnement de développement.

## Nouvelles fonctionnalités

### 1. Extension VS Code (Beta)

**Description** : Intégration native de Claude Code dans Visual Studio Code.

**Fonctionnalités** :
- **Panel latéral en temps réel** : Visualisation des changements en cours
- **Inline diff visualization** : Voir les modifications directement dans l'éditeur
- **Suivi des modifications** : Historique des changements proposés

**Installation** :
```bash
# Via le marketplace VS Code
# Rechercher "Claude Code" dans Extensions (Ctrl+Shift+X)
```

**Avantages** :
- Meilleure visibilité sur les modifications en cours
- Interface graphique pour gérer les changements
- Intégration fluide avec le workflow VS Code existant

---

### 2. Système de Checkpointing

**Description** : Sauvegarde automatique de l'état du code avant modifications importantes.

**Fonctionnalités** :
- **Sauvegarde automatique** avant chaque modification significative
- **Retour arrière instantané** en cas de problème
- **Options de restauration** :
  - Code uniquement
  - Conversation uniquement
  - Code + Conversation

**Cas d'usage** :
- Expérimenter des changements sans risque
- Revenir rapidement à un état stable
- Sécurité lors de refactoring majeur

**Best practices** :
- Créer un checkpoint manuel avant un refactoring important
- Utiliser les checkpoints pour tester plusieurs approches
- Combiner avec Git pour une protection à double niveau

---

### 3. Expérience Terminal améliorée

**Description** : Améliorations de l'interface en ligne de commande.

**Nouvelles commandes** :
- **`Ctrl+r`** : Historique de prompts consultable (déjà documenté dans [commands.md](../../commands.md#voir-le-detail-de-claude-code))
- **`Ctrl+t`** : Afficher/masquer la todo list (déjà documenté dans [commands.md](../../commands.md#voir-la-todo-de-claude-code))

**Améliorations** :
- Meilleure visibilité des statuts de tâches
- Indicateurs de progression plus clairs
- Gestion améliorée des erreurs

---

### 4. Travail autonome avancé

#### Subagents (Parallélisation)

**Description** : Délégation de tâches complexes à plusieurs agents travaillant en parallèle.

**Cas d'usage** :
- Modifications sur plusieurs composants simultanément
- Tests backend + frontend en parallèle
- Documentation + implémentation en parallèle

**Exemple théorique** :
```
Agent principal
├─ Subagent 1 : Modification backend (FastAPI)
├─ Subagent 2 : Modification frontend (Vue.js)
└─ Subagent 3 : Mise à jour documentation
```

**Avantages** :
- Gain de temps sur tâches complexes
- Meilleure séparation des préoccupations
- Workflow plus efficace

---

#### Hooks (Automatisation)

**Description** : Déclencheurs automatiques d'actions en réponse à certains événements.

**Configuration** : Via `.vscode/settings.json`

**Exemple de configuration pour ce projet** :
```json
{
  "chat.tools.terminal.autoApprove": {
    // Tests backend automatiques après modification
    "pytest -qq --tb=no --disable-warnings": {
      "approve": true,
      "matchCommandLine": true
    },
    // Tests frontend automatiques
    "cd /workspaces/back-office-lmelp/frontend && npm test -- --run": {
      "approve": true,
      "matchCommandLine": true
    },
    // Linting automatique
    "ruff check . --output-format=github": {
      "approve": true,
      "matchCommandLine": true
    }
  }
}
```

**Cas d'usage** :
- Exécuter les tests automatiquement après chaque modification
- Lancer le linting avant chaque commit
- Vérifier la couverture de code systématiquement

**⚠️ Attention** :
- Les hooks approuvés s'exécutent sans confirmation
- Bien réfléchir aux commandes à auto-approuver
- Éviter les commandes destructives (suppression, force push, etc.)

---

#### Tâches en arrière-plan

**Description** : Maintien de processus long-running sans bloquer le workflow principal.

**Cas d'usage pour ce projet** :
- Serveur de développement backend (`python -m back_office_lmelp.app`)
- Serveur frontend (`npm run dev`)
- Tests en watch mode (`npm test -- --watch`)
- Documentation live (`mkdocs serve`)

**Avantages** :
- Surveillance continue sans interruption
- Logs accessibles en temps réel
- Arrêt propre des processus

---

### 5. Claude Sonnet 4.5

**Description** : Nouveau modèle par défaut, plus performant.

**Changement de modèle** :
```bash
# Afficher le modèle actuel
/model

# Changer de modèle (si besoin)
/model sonnet-3.5  # Version précédente
/model sonnet-4.5  # Version actuelle (défaut)
```

**Améliorations** :
- Meilleure compréhension du contexte
- Réponses plus précises
- Performances accrues sur tâches complexes

---

## Impact sur le workflow du projet

### Déjà en place ✅

Ce projet utilise déjà plusieurs pratiques compatibles avec les nouvelles fonctionnalités :

1. **Todo list structurée** (`Ctrl+t`)
2. **Historique de commandes** (`Ctrl+r`)
3. **Workflow TDD rigoureux**
4. **Auto-discovery des services** (Issue #56)
5. **Scripts d'automatisation** (`.claude/get-services-info.sh`)

### À explorer 🔍

1. **Extension VS Code** : À tester sur une prochaine feature
2. **Hooks automatiques** : Configuration personnalisée des tests
3. **Checkpointing** : Sécurité supplémentaire lors de refactoring
4. **Subagents** : Parallélisation sur tâches multi-composants

---

## Recommandations

### Pour commencer

1. **Installer l'extension VS Code** et tester sur une feature simple
2. **Expérimenter les checkpoints** lors du prochain refactoring
3. **Configurer 1-2 hooks** pour les tests les plus fréquents
4. **Observer le comportement** de Sonnet 4.5 vs 3.5

### Configuration minimale recommandée

Ajouter à `.vscode/settings.json` :

```json
{
  "chat.tools.terminal.autoApprove": {
    // Tests rapides backend
    "pytest -qq --tb=no --disable-warnings": {
      "approve": true,
      "matchCommandLine": true
    },
    // Linting
    "ruff check . --output-format=github": {
      "approve": true,
      "matchCommandLine": true
    }
  }
}
```

### Documentation complémentaire

- [Commands.md](../../commands.md) : Commandes fréquentes du projet
- [CLAUDE.md](../../CLAUDE.md) : Guide complet pour Claude Code
- [Development](development.md) : Workflow de développement

---

## Ressources

- [Annonce officielle](https://anthropic.com/news/enabling-claude-code-to-work-more-autonomously)
- [Documentation Claude Code](https://docs.claude.com/en/docs/claude-code)
- [Extension VS Code](https://marketplace.visualstudio.com/) (rechercher "Claude Code")

---

**Date de création** : 30 septembre 2025
**Issue associée** : [#71](https://github.com/castorfou/back-office-lmelp/issues/71)
