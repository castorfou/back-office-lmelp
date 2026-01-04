# Logs de Debug - Variables d'Environnement

## Vue d'ensemble

Le back-office LMELP propose des variables d'environnement pour activer des logs de debug détaillés. Ces logs sont utiles pour diagnostiquer des problèmes de génération de contenu, de matching avec Babelio, ou d'autres opérations complexes.

**Important :** Les logs de debug sont **désactivés par défaut** en production pour éviter la pollution des logs et préserver les performances.

## Variables disponibles

### `AVIS_CRITIQUES_DEBUG_LOG`

Active les logs de debug pour la génération d'avis critiques avec le LLM (Azure OpenAI).

**Quand l'utiliser :**
- Diagnostic d'échecs de génération de summary
- Comprendre pourquoi la validation échoue
- Analyser les réponses brutes du LLM

**Ce qui est loggé :**
- Paramètres de la requête LLM (prompt, temperature, max_tokens)
- Sortie brute du LLM avant validation (écrite dans `/tmp/avis_critiques_debug/`)
- Détails des erreurs de validation avec aperçu du contenu
- Résultats de chaque phase (Phase 1 : génération, Phase 2 : correction)

**Fichiers de debug créés :**
```
/tmp/avis_critiques_debug/
├── phase1_raw_20260104_153045.md          # Sortie brute Phase 1
├── phase2_raw_20260104_153102.md          # Sortie brute Phase 2
└── validation_failed_<episode_id>_<timestamp>.md  # Summary rejeté
```

**Exemple de log :**
```
================================================================================
📄 PHASE 1 - RAW LLM OUTPUT (BEFORE VALIDATION)
   📁 Fichier debug: /tmp/avis_critiques_debug/phase1_raw_20260104_153045.md
   Length: 2847 characters
   Has header: True
   Has tables: True
================================================================================
```

### `BABELIO_DEBUG_LOG`

Active les logs de debug pour les opérations de vérification et matching avec Babelio.

**Quand l'utiliser :**
- Comprendre pourquoi un livre n'est pas trouvé sur Babelio
- Analyser les scores de similarité du matching auteur/titre
- Débugger les problèmes de scraping ou de parsing HTML

**Ce qui est loggé :**
- Termes de recherche envoyés à Babelio
- Scores de similarité pour chaque candidat
- Décisions de fallback (recherche par auteur seul, etc.)
- Résultats de scraping et parsing HTML
- URLs visitées et réponses HTTP

**Exemple de log :**
```
🔍 [DEBUG] verify_book: search_term='Le Masque et la Plume Emmanuel Carrère'
🔍 [DEBUG] _find_best_book_match: 5 livre(s) candidat(s)
🔍 [DEBUG] Candidat 1: 'Le Royaume' - Score titre: 0.42, Score auteur: 0.95
🔍 [DEBUG] Candidat 2: 'Limonov' - Score titre: 0.18, Score auteur: 0.95
🔍 [DEBUG] Meilleur match sélectionné: 'Le Royaume' (score combiné: 0.68)
```

### `BABELIO_CACHE_LOG`

Active les logs détaillés du système de cache disque pour Babelio.

**Quand l'utiliser :**
- Vérifier que le cache fonctionne correctement
- Comprendre les hits/miss de cache
- Analyser les performances du cache

**Ce qui est loggé :**
- Hits de cache (URL déjà en cache)
- Miss de cache (nouvelle requête HTTP)
- Taille du cache
- Opérations d'expiration

**⚠️ Avertissement :** Les résultats stockés en cache peuvent varier d'une exécution à l'autre. Utilisez avec prudence lors du développement.

## Activation en mode développement

### Méthode 1 : Via `scripts/start-dev.sh` (recommandée)

Les variables de debug sont **automatiquement activées** lorsque vous utilisez le script de démarrage :

```bash
./scripts/start-dev.sh
```

Le script exporte automatiquement :
```bash
export BABELIO_DEBUG_LOG=1
export AVIS_CRITIQUES_DEBUG_LOG=1
```

### Méthode 2 : Activation manuelle dans le terminal

```bash
# Activer toutes les variables de debug
export AVIS_CRITIQUES_DEBUG_LOG=1
export BABELIO_DEBUG_LOG=1
export BABELIO_CACHE_LOG=1

# Démarrer le backend
PYTHONPATH=/workspaces/back-office-lmelp/src python -m back_office_lmelp.app
```

### Méthode 3 : Activation pour une seule commande

```bash
# Debug activé uniquement pour cette session
AVIS_CRITIQUES_DEBUG_LOG=1 BABELIO_DEBUG_LOG=1 \
  PYTHONPATH=/workspaces/back-office-lmelp/src python -m back_office_lmelp.app
```

## Activation en production (Docker/Portainer)

### Option 1 : Via fichier `.env` (recommandée)

Dans votre installation docker-lmelp, éditez le fichier `.env` :

```bash
# Logs de debug (optionnel - désactivé par défaut)
AVIS_CRITIQUES_DEBUG_LOG=1
BABELIO_DEBUG_LOG=1
```

Puis redémarrez le conteneur backend :

```bash
docker compose restart backend
```

### Option 2 : Via Portainer (interface web)

1. **Accédez à Portainer** (généralement `http://votre-serveur:9000`)
2. **Sélectionnez votre stack** `lmelp`
3. **Cliquez sur le conteneur** `lmelp-backoffice-backend`
4. **Duplicate/Edit** → Section `Environment variables`
5. **Ajoutez les variables :**
   ```
   AVIS_CRITIQUES_DEBUG_LOG=1
   BABELIO_DEBUG_LOG=1
   ```
6. **Deploy the stack** ou **Recreate** le conteneur

### Option 3 : Via docker-compose.yml (modification du stack)

Éditez directement `docker-compose.yml` dans votre installation docker-lmelp :

```yaml
services:
  backend:
    image: ghcr.io/castorfou/lmelp-backend:latest
    environment:
      # ... existing variables ...
      - AVIS_CRITIQUES_DEBUG_LOG=${AVIS_CRITIQUES_DEBUG_LOG:-0}
      - BABELIO_DEBUG_LOG=${BABELIO_DEBUG_LOG:-0}
      - BABELIO_CACHE_LOG=${BABELIO_CACHE_LOG:-0}
```

Puis recréez le stack :

```bash
docker compose up -d --force-recreate backend
```

**Note :** Cette modification nécessite une mise à jour du projet docker-lmelp. Voir [Issue correspondante](https://github.com/castorfou/docker-lmelp/issues).

## Accès aux fichiers de debug en production

### Logs dans les conteneurs Docker

Les fichiers de debug sont écrits dans `/tmp/avis_critiques_debug/` **à l'intérieur du conteneur**.

**Pour y accéder :**

```bash
# Lister les fichiers de debug
docker exec lmelp-backoffice-backend ls -lh /tmp/avis_critiques_debug/

# Afficher un fichier spécifique
docker exec lmelp-backoffice-backend cat /tmp/avis_critiques_debug/phase1_raw_20260104_153045.md

# Copier les fichiers vers l'hôte
docker cp lmelp-backoffice-backend:/tmp/avis_critiques_debug/ ./debug_logs/
```

### Persistance des logs (optionnel)

Pour conserver les logs entre redémarrages du conteneur, ajoutez un volume dans `docker-compose.yml` :

```yaml
services:
  backend:
    volumes:
      - ${CALIBRE_HOST_PATH:-/dev/null}:/calibre:ro
      - ./data/debug_logs:/tmp/avis_critiques_debug  # Nouvelle ligne
```

Les logs seront alors disponibles dans `./data/debug_logs/` sur l'hôte.

## Désactivation des logs de debug

### En développement

```bash
# Méthode 1 : Supprimer les exports
unset AVIS_CRITIQUES_DEBUG_LOG
unset BABELIO_DEBUG_LOG

# Méthode 2 : Les définir à 0
export AVIS_CRITIQUES_DEBUG_LOG=0
export BABELIO_DEBUG_LOG=0
```

### En production (Docker)

**Option 1 :** Commentez ou supprimez les variables dans `.env` :

```bash
# AVIS_CRITIQUES_DEBUG_LOG=1  # Commenté
# BABELIO_DEBUG_LOG=1         # Commenté
```

**Option 2 :** Définissez-les explicitement à `0` :

```bash
AVIS_CRITIQUES_DEBUG_LOG=0
BABELIO_DEBUG_LOG=0
```

Puis redémarrez le conteneur.

## Bonnes pratiques

### Utilisation recommandée

✅ **Activer en développement** : Toujours actif via `start-dev.sh` pour faciliter le diagnostic
✅ **Activer temporairement en production** : Seulement lors d'investigation d'un problème spécifique
✅ **Nettoyer les fichiers de debug** : Supprimer `/tmp/avis_critiques_debug/` régulièrement
✅ **Partager les logs** : Inclure les fichiers de debug dans les rapports de bugs

### À éviter

❌ **Ne pas activer en permanence en production** : Impact sur les performances et taille des logs
❌ **Ne pas commiter `.env` avec debug=1** : Risque de pollution des logs en production
❌ **Ne pas confondre avec les logs applicatifs** : Les logs de debug sont distincts des logs standards

## Exemples d'utilisation

### Diagnostiquer un échec de génération de summary

1. **Activer le debug :**
   ```bash
   export AVIS_CRITIQUES_DEBUG_LOG=1
   ```

2. **Reproduire le problème :** Générer le summary pour l'épisode problématique

3. **Consulter les logs :**
   ```bash
   cat /tmp/avis_critiques_debug/phase1_raw_*.md
   ```

4. **Analyser :**
   - Le LLM génère-t-il du contenu ?
   - Le contenu est-il valide ?
   - Quelle validation échoue ?

### Comprendre un problème de matching Babelio

1. **Activer le debug :**
   ```bash
   export BABELIO_DEBUG_LOG=1
   ```

2. **Lancer la vérification :** Utiliser la fonction "Vérifier avec Babelio"

3. **Analyser les logs du terminal :**
   - Scores de similarité trop faibles ?
   - Mauvais terme de recherche ?
   - Fallback utilisé ?

## Troubleshooting

### Les logs de debug n'apparaissent pas

**Vérifications :**

1. **Variable d'environnement définie ?**
   ```bash
   echo $AVIS_CRITIQUES_DEBUG_LOG
   # Doit afficher: 1 ou true
   ```

2. **Backend redémarré après définition de la variable ?**
   - Les variables d'environnement sont lues au démarrage uniquement

3. **Niveau de log configuré ?**
   - Par défaut, les logs INFO sont affichés
   - Vérifier la configuration du logger

### Fichiers de debug absents dans `/tmp/avis_critiques_debug/`

**Causes possibles :**

1. **Permissions du répertoire `/tmp/`** : Le processus backend doit pouvoir créer des fichiers
2. **Conteneur redémarré** : Les fichiers dans `/tmp/` sont volatiles
3. **Aucune génération n'a été lancée** : Les fichiers sont créés uniquement lors de génération

**Solution :** Vérifier les permissions et utiliser un volume persistant si nécessaire.

## Ressources complémentaires

- **Guide développeur :** [Documentation technique](../dev/claude-ai-guide.md)
- **Stratégie de debug logging :** [CLAUDE.md](../../CLAUDE.md#debug-logging-strategy)
- **Variables d'environnement backend :** [environment-variables.md](../dev/environment-variables.md)

---

*Documentation mise à jour pour la version actuelle du back-office LMELP. Les variables de debug sont un outil de diagnostic, pas une fonctionnalité de production.*
