## montage à chaud d'un dossier

si on ne veut pas modifier et rebuild le devcontainer

vérifier le nom du container devcontainer, ici `upbeat_shamir`


```bash
# depuis le host

# 1) Recuperer l'ID du conteneur devcontainer
CTR=$(docker ps --format '{{.ID}} {{.Names}}' | grep -i upbeat_shamir | awk '{print $1}' | head -1)

# 2) Recuperer le MergedDir (rootfs visible du conteneur)
MERGED=$(docker inspect -f '{{.GraphDriver.Data.MergedDir}}' "$CTR")

echo "CTR=$CTR"
echo "MERGED=$MERGED"

# 3) Creer le point de montage dans la rootfs du conteneur
sudo mkdir -p "$MERGED/mnt/hot-test"

# 4) Monter le dossier host a chaud
sudo mount --bind /home/guillaume/hf-models "$MERGED/mnt/hot-test"

# 5) Verifier depuis le conteneur
docker exec "$CTR" ls -la /mnt/hot-test | head
```
