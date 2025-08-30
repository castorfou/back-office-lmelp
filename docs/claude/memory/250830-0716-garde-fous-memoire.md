# Mémoire de session - Garde-fous mémoire
**Date:** 2025-08-30 07:16
**Contexte:** Continuation de session après implémentation des garde-fous mémoire

## Situation initiale
L'utilisateur avait un problème de mémoire qui causait des crashes Linux avec des processus tués par le système. Il demandait des garde-fous mémoire pour éviter ces crashes.

## Travail réalisé

### 1. Backend - Garde-fous mémoire FastAPI
- **Fichier créé:** `src/back_office_lmelp/utils/memory_guard.py`
- **Classe MemoryGuard** avec psutil pour monitoring RSS
- **Limite par défaut:** 500MB avec seuil d'alerte à 80% (400MB)
- **Intégration** dans tous les endpoints API (`/api/episodes`, `/api/episodes/{id}`, PUT)
- **Arrêt d'urgence** automatique si limite dépassée
- **Avertissements** dans les logs si seuil dépassé

### 2. Frontend - Garde-fous mémoire Vue.js
- **Fichier créé:** `frontend/src/utils/memoryGuard.js`
- **Surveillance automatique** avec `performance.memory` API
- **Limite par défaut:** 100MB, vérifications toutes les 5s
- **Intégration** dans `main.js` et `EpisodeEditor.vue`
- **Arrêt d'urgence** avec rechargement de page si limite dépassée
- **Page de test:** `frontend/test_memory_guard.html` pour validation

### 3. Gestion robuste du cycle de vie
**Problème identifié:** Processus zombies occupant les ports après crash
**Solutions implémentées:**
- `try/finally` dans le lifespan FastAPI pour garantir la fermeture MongoDB
- Gestionnaires de signaux (SIGINT/SIGTERM) pour arrêt propre
- Nettoyage forcé avec `contextlib.suppress(Exception)`
- Configuration uvicorn optimisée

### 4. Configuration et dépendances
- **Ajout:** `psutil>=5.9.0` et `types-psutil` pour MyPy
- **Configuration Ruff:** Migration vers `[tool.ruff.lint]`
- **Configuration MyPy:** Ajout de `psutil.*` aux imports ignorés
- **Port API:** Changé de 8001 vers 54321 (problèmes de ports occupés)

## Commits créés
1. `340e0be` - feat: Ajout dépendances pour garde-fous mémoire
2. `968a2c0` - feat: Garde-fous mémoire et gestion robuste du cycle de vie
3. `6b53ac0` - feat: Garde-fous mémoire frontend Vue.js
4. `d1b8259` - docs: Mise à jour documentation garde-fous mémoire

**Push réussi** sur `origin/main`

## Problème résolu - Conception logicielle
Le problème original des processus zombies qui occupaient les ports est maintenant résolu grâce à:
- Gestion d'exceptions robuste dans le lifespan
- Gestionnaires de signaux pour arrêt propre
- Nettoyage forcé des ressources en cas d'erreur
- Configuration uvicorn optimisée

## Configuration finale
- **Backend:** Port 54321 (`API_PORT=54321`)
- **Frontend:** Proxy vers `localhost:54321`
- **Mémoire backend:** Limite 500MB
- **Mémoire frontend:** Limite 100MB

## Prêt pour test
L'utilisateur peut maintenant lancer:
```bash
# Backend
uv run python -m back_office_lmelp.app

# Frontend
cd frontend && npm run dev
```

Le système est maintenant protégé contre les fuites mémoire et les processus zombies.
