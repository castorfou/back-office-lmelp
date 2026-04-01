## login / pull

```bash
# connection artifactory
docker login dcy-docker-snapshot.artifactory.michelin.com
# Entrer votre identifiant Michelin et votre token Artifactory

# pull d'une image
docker pull dcy-docker-snapshot.artifactory.michelin.com/local-llm/hf-models-manager:latest
```

## ps

```bash
# liste les containers actifs
docker ps
```

## run

```bash
docker run -d \
    --name hf-models \
    --env-file ~/.hf-models.env \
    -v ~/hf-models:/models \
    --entrypoint /bin/sh \
    dcy-docker-snapshot.artifactory.michelin.com/local-llm/hf-models-manager:latest \
    -c "umask 0000 && sleep infinity" # (1)
```

1.  L'image intègre un umask 0000 dans l'entrypoint : tous les fichiers créés dans /models sont world-readable/writable (rw-rw-rw-), ce qui garantit l'accès depuis le host même en Docker secure mode (userns-remap).

## stop / start

```bash
# stop
docker stop hf-models

# start
docker start hf-models
```

## rm

```bash
docker rm hf-models

# forcé si démarré
docker rm -f hf-models
```

## logs

## exec
