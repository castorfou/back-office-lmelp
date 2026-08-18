# Fix Conteneur backend tourne en root - Issue #258

**Date:** 2026-08-18 13:00
**Issue:** #258 - Le conteneur backend tourne en root (fichiers de cache Babelio créés root:root)
**Branch:** 258-le-conteneur-backend-tourne-en-root-fichiers-de-cache-babelio-créés-rootroot
**État:** Implémenté et validé en conditions réelles (build+run côté host par l'utilisateur), commit pas encore effectué (workflow fix-issue en cours)

## Problème Initial

Le conteneur `backend` (image `ghcr.io/castorfou/lmelp-backend`) ne définissait aucun utilisateur non-root dans `docker/build/backend/Dockerfile`. Le process tournait en root, donc tout fichier écrit sur le volume bind-monté `${BABELIO_CACHE_HOST_PATH:-/tmp/lmelp-cache}:/cache` héritait de `root:root` côté hôte — gênant pour la gestion depuis File Station sur un NAS Synology (contexte : investigation castorfou/docker-lmelp#47).

Décision utilisateur explicite : reproduire **exactement** la solution déjà validée sur le repo sœur `lmelp` (issue castorfou/lmelp#105, PR #106) — convention `PUID`/`PGID`, mécanisme `gosu`.

## Solution Implémentée

### 1. `docker/build/backend/Dockerfile`

- Installation de `gosu` dans le stage runtime.
- `ARG APP_UID=1000` / `ARG APP_GID=1000` (défauts baked-in), création de l'utilisateur `appuser` via `groupadd`/`useradd`.
- `ENV HOME=/home/appuser`.
- **Pas de directive `USER` statique** — le remap dynamique se fait dans l'entrypoint (test dédié pour verrouiller ce choix d'archi).
- `COPY` d'un nouveau `docker/build/backend/entrypoint.sh`, `ENTRYPOINT` pointe dessus, `CMD` devient les arguments passés.
- `RUN chown -R appuser:appuser /app` (voir bug découvert ci-dessous — nécessaire pour deux raisons distinctes).

### 2. `docker/build/backend/entrypoint.sh` (nouveau, ce repo n'en avait pas)

Bloc de setup exécuté uniquement à la première passe (`if [ "$(id -u)" = "0" ]; then ... fi`) :
- Lecture `PUID`/`PGID` avec défaut 1000/1000.
- `usermod`/`groupmod` si différent de l'UID/GID baked-in de `appuser`.
- `chown -R "$PUID:$PGID" /cache` **inconditionnel** à chaque démarrage (migration transparente des fichiers `root:root` préexistants).
- `chown -R "$PUID:$PGID" /app` **conditionnel** (seulement si PUID/PGID diffère du défaut baked-in) — nécessaire quand l'UID cible réel (ex: 1027 sur NAS) diffère du défaut 1000 figé au build.
- `exec gosu appuser "$0" "$@"` pour dropper les privilèges et relancer le script (qui va alors dans le `else` final : `exec "$@"`).

### 3. `docker-compose.yml` / `.env.template` / `deployment/README.md` / `docs/deployment/docker-setup.md`

Ajout et documentation de `PUID`/`PGID` (défaut 1000/1000, comment trouver les siens avec `id -u`/`id -g`), section troubleshooting sur la reprise automatique des fichiers `root:root` existants au redémarrage, section "Utilisateur non-root (backend)" dans l'architecture Docker.

## Tests Ajoutés

**Nouveau fichier** `tests/test_docker_backend_config.py` (aucun test Docker n'existait dans ce repo — pattern inspiré de `lmelp/tests/integration/test_streamlit_config.py::TestDockerfile`, approche statique sur le contenu des fichiers, pas de build Docker réel dans les tests automatisés).

13 tests répartis en `TestDockerfile` (7) et `TestDockerEntrypoint` (6) :
- Dockerfile : `gosu` installé, `ARG APP_UID`/`APP_GID` déclarés, `useradd` référence ces args, `ENV HOME` positionné, pas de `USER` statique, `ENTRYPOINT`/`entrypoint.sh` référencé, `/app` chowné à `appuser`.
- entrypoint.sh : lecture `PUID`/`PGID` avec défauts, `usermod`/`groupmod`, `chown` sur `/cache`, `chown` sur `/app` (remap conditionnel), `gosu appuser`.

**Résultats** : 13/13 tests passent. Suite complète backend : 1452 passed, 24 skipped, 0 échec (644.79s). `pre-commit run --files <fichiers modifiés>` clean (ruff lint+format, detect-secrets, etc.). `mypy src/` : Success, aucune régression. `mkdocs build --strict` : succès (4.31s), seuls des `INFO` préexistants sans rapport avec ce fix.

## Deux bugs trouvés et corrigés pendant la validation utilisateur (build+run réel côté host)

Docker n'étant pas disponible dans ce devcontainer, l'utilisateur a validé en buildant/lançant l'image sur son host (même limitation que sur `lmelp`#105). Deux bugs concrets ont été trouvés par ce test réel — les tests statiques ne pouvaient pas les détecter :

### Bug 1 — `/app/src` illisible par `appuser` (permissions du host de build)

Premier crash : `ImportError: cannot import name 'EnrichedLoggingMiddleware' from 'back_office_lmelp.middleware' (unknown location)`. Le message `unknown location` est le signal caractéristique d'un **namespace package vide** (PEP 420) — Python n'a pas trouvé de fichier `__init__.py` réel, mais a quand même reconnu `middleware` comme un espace de noms parce qu'un répertoire de ce nom existe dans un chemin de `sys.path`.

Cause racine : `COPY` dans Docker **préserve les permissions Unix des fichiers source**. Sur le host de build de l'utilisateur, `src/back_office_lmelp/middleware/` avait des permissions `drwx------` (700, propriétaire `guillaume`) — probablement dû à un `umask` restrictif local. Une fois copié dans l'image (possédé par `root` après le `COPY`), ce répertoire restait `700`, donc illisible par quiconque d'autre — y compris `appuser`. Tournant auparavant en root (avant ce fix), le bug était invisible : root peut tout lire quelles que soient les permissions.

Diagnostic fait par bisection stricte de commandes `docker run --entrypoint ...` :
- `docker run --entrypoint python <image> -c "import back_office_lmelp.app"` → **succès** (root, bypass l'entrypoint).
- `docker run <image> python -c "import back_office_lmelp.app"` (passe par `ENTRYPOINT` donc par `gosu`/`appuser`) → **échec**, même erreur.
- `docker run <image> ls -la /app/src/back_office_lmelp/middleware/` → `Permission denied` — preuve directe.

**Fix** : `RUN chown -R appuser:appuser /app` après tous les `COPY` dans le Dockerfile — élimine le problème à la racine (peu importe les permissions du host de build) au lieu d'un `chmod -R a+rX` plus fragile.

### Bug 2 — `/app/.dev-ports.json` non-inscriptible par `appuser`

Après le fix du bug 1, le serveur démarrait mais crashait ensuite avec `PermissionError: [Errno 13] Permission denied: '/app/.dev-ports.json'`, dans `src/back_office_lmelp/utils/port_discovery.py:168` (`write_unified_port_info`). L'application écrit ce fichier de port-discovery dans son répertoire de travail (`os.getcwd()` = `/app`, `WORKDIR`) à chaque démarrage.

Le `chown -R appuser:appuser /app` du bug 1 corrige ce cas quand `PUID`/`PGID` correspond au défaut baked-in (1000/1000) — mais **pas** quand l'UID réel cible diffère (ex: 1027 sur le NAS), puisque ce chown se fait au *build* avec l'UID par défaut, pas à l'exécution avec le `PUID` réel.

**Fix** : dans `entrypoint.sh`, ajout d'un second `chown -R "$PUID:$PGID" /app` **conditionnel** (seulement quand `PUID`/`PGID` diffère du défaut baked-in de `appuser`) — même logique de remap déjà utilisée pour `usermod`/`groupmod`. Contrairement à `/cache` (chown systématique, car sa propriété au démarrage est inconnue — bind mount hôte), `/app` n'a besoin d'être re-chowné que si le remap UID/GID a effectivement eu lieu.

## Validation réelle côté host (par l'utilisateur)

Docker non disponible dans le devcontainer (même limitation que `lmelp`#105) — build et run faits sur le host :

1. `docker top test-backend` → process `python -m back_office_lmelp.app` tourne sous `guillau+` (UID hôte réel, pas root) — confirmation du drop de privilèges.
2. `docker logs test-backend` → démarrage propre, uvicorn actif sur le port.
3. `ls -la /tmp/test-cache` → répertoire `guillaume:guillaume`, pas root.
4. Test de migration : fichier `root:root` injecté manuellement dans `/cache` (`docker exec -u root ... touch ... chown root:root`), puis `docker restart` → fichier devient `guillaume:guillaume` automatiquement. Migration confirmée fonctionnelle.

## Apprentissages Clés

### `ImportError: ... (unknown location)` = signal de namespace package vide, pas de fichier manquant

Quand Python affiche `unknown location` dans une `ImportError` pour un sous-module qui *existe* sur le filesystem (vérifié par ailleurs), c'est le signe qu'il l'a résolu comme un PEP 420 namespace package (un répertoire sans `__init__.py` accessible), pas comme un vrai module. Cause quasi-certaine : permissions insuffisantes sur le fichier `__init__.py` réel, ou sur un répertoire parent, empêchant l'utilisateur courant de le voir — même si le répertoire lui-même est listable.

### `COPY` Docker préserve les permissions Unix du host de build — risque silencieux avec un remap non-root

Un `Dockerfile` qui build en root ne révèle jamais un problème de permissions sur les fichiers source copiés (`COPY src/ /app/src/`), quelles que soient les permissions d'origine sur le host de build, puisque root peut tout lire. Ce risque devient actif uniquement en ajoutant un utilisateur non-root — piège classique lors d'une migration root→non-root d'une image déjà en production. **Toujours forcer les permissions cibles explicitement** (`chown`/`chmod`) après les étapes `COPY`, plutôt que de compter sur les permissions héritées du host de build, qui varient selon l'`umask` local de chaque développeur.

### Chown au build (UID par défaut) vs chown à l'exécution (PUID réel) — deux cas distincts à traiter séparément

Un répertoire applicatif qui n'a pas besoin d'exister *avant* le remap UID/GID (typiquement `/app`, présent dans l'image dès le build) peut être chowné une fois pour toutes au build avec l'UID par défaut — mais ce chown devient obsolète si l'UID réel (`PUID`) diffère de ce défaut à l'exécution. Il faut alors un second `chown` conditionnel dans l'entrypoint, déclenché par la même condition que le remap `usermod`/`groupmod` (`PUID != CURRENT_UID`). Ne pas confondre avec `/cache` : un volume bind-monté dont la propriété initiale est totalement inconnue au build (dépend de l'hôte), qui nécessite un `chown` **inconditionnel** à chaque démarrage plutôt qu'un chown conditionnel basé sur l'UID de `appuser`.

### `docker top` plutôt que `docker exec ... id` pour vérifier l'UID réel d'un process (rappel du pattern lmelp#105)

`docker exec` démarre un nouveau process avec l'utilisateur par défaut de l'image (root ici, faute de `USER` statique), donc ne reflète pas l'UID sous lequel tourne le process principal après `gosu`. `docker top <container>` interroge la table de process du host et affiche l'UID réel — le bon outil pour vérifier un drop de privilège dynamique.

### Bisection par `docker run --entrypoint` pour isoler un bug entre code applicatif et infrastructure de démarrage

Face à une erreur qui semble être un bug de code (`ImportError`) mais qui n'apparaît que dans un contexte de conteneur précis, la bisection par variantes de `docker run` (avec/sans `--entrypoint python` pour bypasser `gosu`, `ls` au lieu de `python` pour inspecter directement les permissions) permet d'isoler rapidement si la cause est le code source, l'environnement (`env`), ou les permissions filesystem — sans avoir besoin de modifier et rebuilder l'image à chaque itération de diagnostic.

## Fichiers Modifiés (à committer)

1. `docker/build/backend/Dockerfile`
2. `docker/build/backend/entrypoint.sh` (nouveau)
3. `docker/deployment/docker-compose.yml`
4. `docker/deployment/.env.template`
5. `docker/deployment/README.md`
6. `docs/deployment/docker-setup.md`
7. `tests/test_docker_backend_config.py` (nouveau)
