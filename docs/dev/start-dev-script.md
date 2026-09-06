# Documentation du script `start-dev.sh`

## Vue d'ensemble

Le script `scripts/start-dev.sh` est le point d'entrée principal pour lancer l'environnement de développement complet (backend FastAPI + frontend Vue.js) en une seule commande.

## Usage

```bash
./scripts/start-dev.sh
```

**Arrêt** : `Ctrl+C` pour arrêter proprement les deux services.

## Architecture générale

```
start-dev.sh
├── Nettoyage fichier .dev-ports.json (stale data)
├── Démarrage backend (Python FastAPI)
│   └── Détection port via .dev-ports.json (créé par backend)
├── Démarrage frontend (Vue.js + Vite)
│   └── Détection port (défaut: 5173)
├── Logs des ports détectés
└── Attente signal arrêt (Ctrl+C)
    └── Cleanup propre des processus
```

## Fonctionnalités principales

### 1. **Gestion unifiée des ports** (Port Discovery)

#### Problème résolu
Dans un environnement DevContainer, les ports peuvent changer automatiquement si le port souhaité est déjà utilisé. Il est donc impossible de coder en dur `http://localhost:8000`.

#### Solution implémentée
- Le backend Python écrit automatiquement le fichier `.dev-ports.json` au démarrage avec le port réel utilisé
- Le frontend Vite lit ce fichier pour configurer son proxy API (voir `frontend/vite.config.js`)
- Claude Code peut aussi lire ce fichier pour auto-découvrir les services

#### Format du fichier `.dev-ports.json`
```json
{
  "backend": {
    "port": 54321,
    "host": "0.0.0.0",
    "pid": 12345,
    "started_at": 1764418163.47,
    "url": "http://0.0.0.0:54321"
  },
  "frontend": {
    "port": 5173,
    "host": "0.0.0.0",
    "pid": 12346,
    "started_at": 1764418162.52,
    "url": "http://0.0.0.0:5173"
  }
}
```

#### Choix de conception : Qui écrit le fichier ?

**Principe** : Source de vérité unique pour éviter les race conditions.

**Implémentation** :
- **Seul le backend** écrit `.dev-ports.json` (source de vérité unique)
- Le script bash **lit** le fichier créé par le backend
- Le script attend maximum 15 secondes que le fichier soit créé

**Raison** : Si le backend ET le script écrivaient tous deux le fichier, une race condition pourrait survenir avec des ports incohérents. Le backend étant la source qui connaît réellement son port d'écoute, il est le seul à écrire cette information.

### 2. **Nettoyage des données stales**

#### Problème
Si le fichier `.dev-ports.json` d'une exécution précédente subsiste (après un crash ou un `kill -9`), il contient des ports périmés qui peuvent être lus avant que le nouveau backend ne crée le fichier à jour.

#### Solution
```bash
# Clean up old port discovery file to avoid stale data
if [[ -f "$PROJECT_ROOT/.dev-ports.json" ]]; then
    log "🧹 Nettoyage du fichier de découverte des ports précédent..."
    rm -f "$PROJECT_ROOT/.dev-ports.json"
fi
```

Le fichier est **systématiquement supprimé** avant de lancer les services, garantissant des données fraîches.

### 3. **Détection robuste des ports backend**

#### Fonction `capture_port_from_output()`

**Stratégie pour le backend** :
- Attend que le fichier `.dev-ports.json` soit créé (retry loop de 15s)
- Parse le JSON avec Python pour extraire `port` et `host`
- Retourne `0` même en cas d'échec pour éviter de bloquer le démarrage (grâce à `set -e`)

#### **Piège critique : `set -e` et incrémentation arithmétique**

**Bug découvert** : L'incrémentation `((attempt++))` provoque une erreur silencieuse avec `set -e`.

**Cause** :
- `((attempt++))` retourne la valeur **avant** incrémentation (0 au premier tour)
- Avec `set -e`, bash interprète un retour de 0 dans une expression arithmétique comme un échec
- Le script s'arrête immédiatement sans message d'erreur

**Solution** :
```bash
# ❌ INCORRECT - Fait planter le script avec set -e
((attempt++))

# ✅ CORRECT - Fonctionne avec set -e
attempt=$((attempt + 1))
```

**Symptômes observés** :
- Le script affiche "Attempt 0/15" puis se termine immédiatement
- On ne voit jamais "Attempt 1/15"
- Le backend démarre correctement mais le script rend la main au shell
- Aucun message d'erreur n'est affiché

**Leçon** : Toujours utiliser `var=$((var + 1))` ou `((var += 1))` dans les scripts avec `set -e`, jamais `((var++))`.

```bash
# For backend, wait for unified port discovery file to be created (with retry logic)
if [[ "$service_name" == "BACKEND" ]]; then
    local max_attempts=15  # 15 seconds total
    local attempt=0

    while [[ $attempt -lt $max_attempts ]]; do
        if [[ -f "$PROJECT_ROOT/.dev-ports.json" ]]; then
            local backend_port=$(python3 -c "import json; data=json.load(open('$PROJECT_ROOT/.dev-ports.json')); print(data.get('backend', {}).get('port', ''))" 2>/dev/null)
            local backend_host=$(python3 -c "import json; data=json.load(open('$PROJECT_ROOT/.dev-ports.json')); print(data.get('backend', {}).get('host', ''))" 2>/dev/null)

            if [[ -n "$backend_port" && -n "$backend_host" ]]; then
                eval "${port_var}=$backend_port"
                eval "${host_var}=$backend_host"
                log "Detected $service_name on $backend_host:$backend_port (after ${attempt}s)"
                return 0
            fi
        fi

        sleep 1
        attempt=$((attempt + 1))  # CRITICAL: Use this form with set -e, not ((attempt++))
    done

    warn "Backend port discovery file not found after ${max_attempts}s"
    warn "Backend may still be starting - check logs"
    return 0
fi
```

**Stratégie pour le frontend** :
- Utilise le port par défaut de Vite : `5173`
- Pas de détection dynamique nécessaire (Vite affiche son port dans ses logs)

### 4. **Arrêt propre des processus**

#### Problème : Processus zombies et script bloqué

**Contexte** :
- `npm run dev` lance une **chaîne de processus** : `npm` → `sh` → `node/vite`
- Un simple `kill $FRONTEND_PID` ne tue que le processus parent `npm`
- Les processus enfants (`sh`, `node`) restent en vie → processus zombies
- Le `wait` final du script attend indéfiniment ces processus

#### Solution : Tuer le groupe de processus (PGID)

**Fonction `kill_process_group()`** :
```bash
kill_process_group() {
    local pid=$1
    local name=$2

    # Get process group ID
    local pgid=$(ps -o pgid= -p $pid 2>/dev/null | tr -d ' ')

    if [[ -n $pgid ]]; then
        # Kill entire process group (negative PGID)
        kill -TERM -$pgid 2>/dev/null || true
        log "Signal TERM envoyé au groupe de processus $name (PGID: $pgid)"
    else
        # Fallback to killing just the process
        kill -TERM $pid 2>/dev/null || true
    fi
}
```

**Le `-` devant `$pgid` est crucial** : `kill -TERM -12345` tue tout le groupe de processus 12345.

**Fonction `wait_for_process()`** :
```bash
wait_for_process() {
    local pid=$1
    local name=$2
    local timeout=5
    local elapsed=0

    # Wait max 5 seconds for graceful shutdown
    while kill -0 $pid 2>/dev/null && [[ $elapsed -lt $timeout ]]; do
        sleep 0.5
        elapsed=$((elapsed + 1))
    done

    # Force kill if still running (kill entire process group)
    if kill -0 $pid 2>/dev/null; then
        warn "$name (PID: $pid) ne répond pas - force kill du groupe"
        local pgid=$(ps -o pgid= -p $pid 2>/dev/null | tr -d ' ')
        if [[ -n $pgid ]]; then
            kill -9 -$pgid 2>/dev/null || true
        else
            kill -9 $pid 2>/dev/null || true
        fi
        sleep 0.5
    fi
}
```

**Comportement** :
1. Envoie `SIGTERM` au groupe → arrêt gracieux
2. Attend max 5 secondes
3. Si le processus ne répond pas → `SIGKILL` (force kill) du groupe entier
4. Garantit un arrêt en **maximum 5 secondes**

#### Fonction `cleanup()`

Appelée automatiquement lors de `Ctrl+C`, `SIGTERM`, ou `SIGHUP` (via `trap cleanup SIGINT SIGTERM SIGHUP`) :

```bash
cleanup() {
    log "Arrêt des processus..."

    if [[ -n $BACKEND_PID ]]; then
        log "Arrêt du backend (PID: $BACKEND_PID)"
        kill_process_group $BACKEND_PID "Backend"
        wait_for_process $BACKEND_PID "Backend"
    fi

    if [[ -n $FRONTEND_PID ]]; then
        log "Arrêt du frontend (PID: $FRONTEND_PID)"
        kill_process_group $FRONTEND_PID "Frontend"
        wait_for_process $FRONTEND_PID "Frontend"
    fi

    # Only remove the discovery file once both processes are confirmed dead
    local backend_alive=false
    local frontend_alive=false
    [[ -n $BACKEND_PID ]] && kill -0 $BACKEND_PID 2>/dev/null && backend_alive=true
    [[ -n $FRONTEND_PID ]] && kill -0 $FRONTEND_PID 2>/dev/null && frontend_alive=true

    if [[ -f "$PROJECT_ROOT/.dev-ports.json" ]]; then
        if [[ $backend_alive == true || $frontend_alive == true ]]; then
            warn "Un processus est toujours actif après force-kill - .dev-ports.json conservé pour rester détectable"
        else
            rm -f "$PROJECT_ROOT/.dev-ports.json"
            log "🧹 Unified port discovery file cleaned up"
        fi
    fi

    log "✅ Processus arrêtés proprement"
    exit 0
}
```

#### Pourquoi `SIGHUP` est trappé (Issue #299)

**Problème** : quand `start-dev.sh` est lancé en arrière-plan simple (`./scripts/start-dev.sh &`) depuis un outil dont le shell parent se termine juste après avoir passé la commande (typiquement l'outil Bash de Claude Code), la fin de ce shell parent envoie `SIGHUP` au job resté attaché. Le comportement par défaut de bash pour `SIGHUP` sur un script non interactif est de le tuer **immédiatement, sans exécuter le trap `cleanup()`** — les process backend/frontend qu'il a lui-même backgroundés restent alors orphelins (réattachés à init), invisibles dans `.dev-ports.json` mais toujours actifs sur leurs ports.

**Solution à deux niveaux** :
1. **Prévention** : toujours lancer le script avec `nohup ... & disown` (voir `CLAUDE.md` à la racine du projet) pour que `SIGHUP` n'atteigne jamais le script.
2. **Filet de sécurité** : le trap inclut désormais `SIGHUP`, donc même si le signal arrive malgré tout, `cleanup()` s'exécute et termine proprement backend/frontend au lieu de les laisser orphelins.

**Garde-fou supplémentaire** : la suppression de `.dev-ports.json` dans `cleanup()` est conditionnée à la vérification (`kill -0`) que les deux process sont bien morts après le force-kill. Si l'un d'eux répond encore, le fichier est conservé (avec un avertissement) plutôt que supprimé silencieusement — pour que l'orphelin reste détectable via `.claude/get-services-info.sh` au lieu de disparaître du radar.

### 5. **Gestion des erreurs avec `set -e`**

Le script utilise `set -e` qui arrête l'exécution à la première erreur. Cependant, certaines commandes sont **tolérantes aux erreurs** grâce à `|| true` :

```bash
kill -TERM $BACKEND_PID 2>/dev/null || true
```

**Pourquoi `|| true` ?**
- Si le processus est déjà mort, `kill` retourne un code erreur
- Sans `|| true`, le script s'arrêterait immédiatement (à cause de `set -e`)
- Avec `|| true`, on ignore l'erreur et on continue le cleanup

### 6. **Logging coloré**

Trois niveaux de logs avec couleurs :

```bash
log()   # Vert  - Informations normales
warn()  # Jaune - Avertissements
error() # Rouge - Erreurs
```

Exemple :
```bash
log "Backend démarré (PID: 12345)"
warn "Backend port discovery file not found after 15s"
error "Ce script doit être exécuté depuis la racine du projet"
```

### 7. **Variables d'environnement optionnelles**

#### `BABELIO_CACHE_LOG`

Si définie, active le logging verbeux du cache Babelio :

```bash
export BABELIO_CACHE_LOG=1
./scripts/start-dev.sh
```

Le script affiche alors :
```
[HH:MM:SS] Note: BABELIO_CACHE_LOG is set -> Babelio disk cache logging enabled (INFO).
[HH:MM:SS] WARNING: Les résultats stockés en cache peuvent varier d'une exécution à l'autre; utilisez avec prudence.
```

## Flux d'exécution détaillé

### Au démarrage

```
1. Vérification du répertoire courant (présence de pyproject.toml + frontend/)
2. Vérification des dépendances frontend (node_modules/)
   └─> Si absentes : npm ci
3. Suppression du fichier .dev-ports.json stale
4. Lancement backend FastAPI en arrière-plan
   └─> Stockage du PID dans $BACKEND_PID
5. Détection du port backend (retry 15s)
   └─> Lecture de .dev-ports.json créé par le backend
6. Lancement frontend Vue.js en arrière-plan
   └─> Stockage du PID dans $FRONTEND_PID
7. Détection du port frontend (défaut: 5173)
8. Affichage des ports détectés
9. wait (bloque jusqu'à Ctrl+C ou crash d'un processus)
```

### À l'arrêt (Ctrl+C)

```
1. Signal SIGINT capturé par trap
2. Appel de cleanup()
3. Pour backend et frontend :
   a. kill_process_group() → SIGTERM au groupe
   b. wait_for_process() → Attente 5s max
   c. Si toujours vivant → SIGKILL au groupe
4. Suppression du fichier .dev-ports.json
5. Log "✅ Processus arrêtés proprement"
6. exit 0
```

## Dépannage

### Le script dit "Detected BACKEND on X:Y" mais le port réel est différent

**Cause** : Race condition entre la détection du script et la création du fichier par le backend.

**Solution** : Relancez le script. Le nettoyage automatique du fichier `.dev-ports.json` au démarrage devrait résoudre le problème.

### Le frontend ne peut pas se connecter au backend (proxy error)

**Cause** : Vite a lu le fichier `.dev-ports.json` au démarrage avec un mauvais port et l'a mis en cache.

**Solution** : Arrêtez le script (Ctrl+C) et relancez-le. Vite relira le bon port.

### Ctrl+C ne rend pas la main immédiatement

**Cause** : Un processus ne répond pas au SIGTERM.

**Comportement attendu** : Le script attend max 5 secondes puis force kill. Si cela prend plus de 5s, c'est un bug.

**Vérification** : Regardez les logs, vous devriez voir `WARNING: Backend/Frontend (PID: XXX) ne répond pas - force kill du groupe`.

### Processus zombies après arrêt du script

**Cause** : Le script a été tué avec `kill -9` (SIGKILL) ce qui empêche le cleanup.

**Solution** :
```bash
# Trouver les processus orphelins
ps aux | grep -E "back_office_lmelp|vite"

# Les tuer manuellement
pkill -9 -f "back_office_lmelp"
pkill -9 -f "vite"
```

### `.dev-ports.json` a disparu mais backend/frontend tournent encore (`get-services-info.sh` ne les trouve pas)

**Cause** (Issue #299) : le script a été lancé en arrière-plan simple (`./scripts/start-dev.sh &`, sans `nohup`/`disown`) depuis un outil dont le shell parent s'est terminé juste après (ex: l'outil Bash de Claude Code). La fin de ce shell parent envoie `SIGHUP` au job, tuant le script avant que son trap ne s'exécute (comportement corrigé depuis que `SIGHUP` est trappé — voir plus haut).

**Diagnostic** : `ps aux | grep back_office_lmelp.app` montre un process vivant alors que `.claude/get-services-info.sh` ne trouve rien.

**Prévention** : toujours lancer le script avec `nohup ./scripts/start-dev.sh > /tmp/start-dev.log 2>&1 & disown` (voir `CLAUDE.md` à la racine du projet), jamais un simple `&`.

**Rattrapage si déjà orphelin** : identifier et arrêter manuellement les process (`ps aux | grep -E "back_office_lmelp|vite"`, puis `kill <PID>`, en vérifiant `ps -p <PID>` après coup).

**Prévention** : Toujours arrêter le script avec Ctrl+C (SIGINT) et non `kill -9`.

### Le fichier .dev-ports.json n'est jamais créé

**Cause** : Le backend crash au démarrage avant de créer le fichier.

**Diagnostic** :
```bash
# Lancer le backend manuellement pour voir les erreurs
cd /workspaces/back-office-lmelp
PYTHONPATH=src python -m back_office_lmelp.app
```

**Solution** : Corriger l'erreur de démarrage du backend (souvent : MongoDB non connecté, variable d'environnement manquante, etc.).

## Intégration avec Claude Code

Le fichier `.dev-ports.json` est lu par les scripts d'auto-découverte Claude Code :

- `.claude/get-backend-info.sh --url` → Lit `backend.url`
- `.claude/get-frontend-info.sh --url` → Lit `frontend.url`
- `.claude/get-services-info.sh` → Affiche les deux

Cela permet à Claude Code de construire des commandes `curl` avec le bon port automatiquement :

```bash
bash -c 'BACKEND_URL=$(/workspaces/back-office-lmelp/.claude/get-backend-info.sh --url); curl "$BACKEND_URL/api/stats"'
```

## Améliorations futures possibles

1. **Support de variables d'environnement personnalisées** : Permettre de passer des variables via un fichier `.env.local`
2. **Mode verbose** : `./scripts/start-dev.sh --verbose` pour voir tous les logs des processus
3. **Logs dans des fichiers** : Rediriger stdout/stderr des processus dans `logs/backend.log` et `logs/frontend.log`
4. **Healthcheck automatique** : Vérifier que les services répondent réellement (curl vers `/` et `/api/stats`)
5. **Support multi-environnement** : `./scripts/start-dev.sh --env staging` pour utiliser différentes configurations

## Fichiers liés

- `scripts/start-dev.sh` - Le script principal
- `.dev-ports.json` - Fichier de découverte des ports (généré automatiquement)
- `src/back_office_lmelp/app.py` - Backend FastAPI qui écrit `.dev-ports.json`
- `frontend/vite.config.js` - Configuration Vite qui lit `.dev-ports.json`
- `.claude/get-backend-info.sh` - Script d'auto-découverte pour Claude Code
- `.claude/get-frontend-info.sh` - Script d'auto-découverte pour Claude Code
- `.claude/get-services-info.sh` - Vue d'ensemble des services
