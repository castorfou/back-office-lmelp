## login / pull

```bash
# connexion au registre GitHub (ghcr.io)
echo "$GITHUB_TOKEN" | docker login ghcr.io -u <utilisateur> --password-stdin
# Le token doit avoir le droit read:packages (write:packages pour pousser)

# pull d'une image
docker pull ghcr.io/astral-sh/uv:python3.11-bookworm-slim
```

## ps

```bash
# liste les containers actifs
docker ps
```

## run

```bash
docker run -d \
    --name mon-conteneur \
    --env-file ~/.mon-conteneur.env \
    -v ~/donnees:/data \
    ghcr.io/astral-sh/uv:python3.11-bookworm-slim \
    sleep infinity # (1)
```

1.  `sleep infinity` garde le conteneur actif : on y entre ensuite avec `docker exec`.

## stop / start

```bash
# stop
docker stop mon-conteneur

# start
docker start mon-conteneur
```

## rm

```bash
docker rm mon-conteneur

# forcé si démarré
docker rm -f mon-conteneur
```

## logs

## exec
