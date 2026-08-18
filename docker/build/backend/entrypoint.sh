#!/bin/bash
# Entrypoint backend — remap dynamique de l'utilisateur non-root vers
# PUID/PGID (Issue #258). L'image est publiée une seule fois sur ghcr.io
# et réutilisée sur des machines différentes (UID 1000 sur laptop, 1027
# sur le NAS) : l'UID/GID doit être configurable à l'exécution, pas figé
# au build (voir aussi castorfou/lmelp#105 pour le même pattern).
set -e

# Le conteneur démarre en root pour pouvoir remapper l'utilisateur non-root
# "appuser" vers l'UID/GID de l'hôte et chowner le volume de cache
# bind-monté en conséquence, avant de dropper les privilèges via gosu. Ce
# bloc ne s'exécute donc qu'à la première passe (root) ; après le
# "exec gosu appuser", "id -u" ne vaut plus 0 et ce bloc est sauté.
if [ "$(id -u)" = "0" ]; then
    PUID=${PUID:-1000}
    PGID=${PGID:-1000}

    CURRENT_UID=$(id -u appuser)
    CURRENT_GID=$(id -g appuser)

    if [ "$PUID" != "$CURRENT_UID" ] || [ "$PGID" != "$CURRENT_GID" ]; then
        groupmod -o -g "$PGID" appuser
        usermod -o -u "$PUID" appuser
    fi

    # chown -R inconditionnel à chaque démarrage : corrige automatiquement
    # les fichiers déjà root:root d'avant ce fix (migration transparente au
    # premier redémarrage du conteneur). Un chown conditionné à la
    # propriété du répertoire racine seul serait trompeur : ce répertoire
    # peut déjà appartenir à PUID:PGID (bind mount créé par l'hôte) alors
    # que des fichiers à l'intérieur sont encore root:root.
    mkdir -p /cache
    chown -R "$PUID:$PGID" /cache

    # /app est chowné à appuser (UID/GID baked-in par défaut) au build,
    # mais quand PUID/PGID diffère du défaut (ex: 1027 sur le NAS), il faut
    # aussi le remapper ici — l'app y écrit un fichier runtime
    # (.dev-ports.json, port discovery).
    if [ "$PUID" != "$CURRENT_UID" ] || [ "$PGID" != "$CURRENT_GID" ]; then
        chown -R "$PUID:$PGID" /app
    fi

    exec gosu appuser "$0" "$@"
fi

exec "$@"
