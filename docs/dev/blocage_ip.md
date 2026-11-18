# Contourner le blocage IP babelio avec backoffice-lmelp qui tourne en local

## Contexte

Babelio peut bannir temporairement l'IP du réseau domestique.

Une solution qui fonctionne consiste à travailler sur une **copie locale de la base** (i.e. faire tourner l'appli backoffice-lmelp sur le laptop), tout en étant déconnecté du réseau domestique, puis à rapatrier les modifications au retour. Une autre option serait le développement de [#293 - [implémentation] VPN Mullvad + gluetun pour le trafic backend vers Babelio](https://github.com/castorfou/back-office-lmelp/issues/293)

## Savoir si l'IP est bannie

Un ban IP Babelio est un blocage pare-feu : la connexion TCP n'aboutit jamais, sans 403. Pour le constater sans rien envoyer à Babelio, un essai de connexion TCP suffit :

- dans l'application : bouton **🔄 Rafraîchir** de **Contrôle Babelio** (`GET /api/babelio/status?live_check=true`, essai de 5 s) ou `POST /api/babelio/probe` (essai d'1 s). Les deux appellent `BabelioService.probe_reachability()`, qui ouvre une connexion vers `www.babelio.com:443` puis la ferme, sans TLS ni HTTP ;
- à la main, depuis le devcontainer ou le NAS :

```bash
timeout 8 bash -c "</dev/tcp/www.babelio.com/443" && echo OK || echo FAIL
```

L'essai ne peut pas prolonger un ban : une IP bannie est déjà ignorée par le pare-feu, et une IP libre n'envoie qu'une connexion vide, absente des journaux HTTP. Il ne tourne jamais en boucle : à la demande, et avant « Valider avec Babelio » ou la liaison automatique.

**Effets sur le circuit breaker** (`get_circuit_reason()` dans `/api/babelio/status`) :

| Événement | Disjoncteur | Motif (`circuit_reason`) |
|---|---|---|
| Réponse 403 | ouvert | `http_403` |
| Réponse 403 dont la page est « Vérification de sécurité » (`_reason_for_403()`) | ouvert | `captcha` |
| Timeout de connexion d'une requête, ou essai TCP en échec | ouvert | `connect_timeout` |
| Essai TCP réussi | refermé si le motif est `connect_timeout` | `null` |
| Cookie enregistré (`POST /api/babelio/cookie`) | refermé | `null` |

Le motif `captcha` correspond à un cookie copié sans être connecté au compte Babelio : `GET /api/babelio/status` renvoie alors `overall: "captcha"`. `POST /api/babelio/cookie` accepte un cookie sans `id_user` mais renvoie un `warning`, et le statut expose `cookie_anonymous`. Ce contrôle ne voit que le cas d'un navigateur jamais connecté : `id_user` et `bbac` restent dans le navigateur après une déconnexion, et seules les valeurs de `bbac` et `PHPSESSID` distinguent alors une session ouverte, côté serveur Babelio.

Le serveur imite l'empreinte réseau de Firefox (`IMPERSONATE_BROWSER`) mais reprend le User-Agent du navigateur qui envoie `POST /api/babelio/cookie`. Si ce User-Agent n'est pas celui d'un Firefox (`is_firefox_user_agent()` : `Firefox/` et `Gecko/`, sans `Chrome/`), le cookie est accepté mais la réponse porte un `browser_warning`, et le statut expose `cookie_browser_not_firefox`. Sans User-Agent, les requêtes partent avec `DEFAULT_USER_AGENT` (un Firefox) : pas d'avertissement.

Voici les grandes étapes du contournement :

- [Phase 1](#phase-1-dump-restore-vers-le-local-sur-reseau-domestique-avant-de-basculer) — Dump + restore vers le local
    - push la base de prod mongo nas vers la base laptop mongo
- [Phase 2](#phase-2-bascule-reseau-travail-sur-la-base-locale) — Bascule réseau + travail sur la base locale
    - lancer le vpn sur mobile, faire un point d'accès wifi
    - connecter le laptop sur ce réseau, lancer le serveur localement
    - travailler sur babelio
- [Phase 3](#phase-3-rapatriement-retour-sur-reseau-domestique) — Rapatriement
    - se reconnecter sur le réseau domestique
    - push la base laptop mongo vers la base de prod mongo nas

## Les 2 bases MongoDB en présence

| Adresse           | Contenu                                                                   |
| ----------------- | ------------------------------------------------------------------------- |
| `nas923:27018`    | Conteneur Docker `lmelp-mongo` sur le NAS — **base de prod**              |
| `localhost:27018` | Conteneur Docker `lmelp-mongo` sur le laptop — **base locale de travail** |

Les deux conteneurs `lmelp-mongo` (NAS et laptop) existent déjà dans le cadre de la stack lmelp — aucune installation supplémentaire n'est nécessaire, ni MongoDB ni les outils `mongodump`/`mongorestore` (déjà présents sur le laptop).

??? info "Pourquoi pas mongosync ?"
    `mongosync` permet une synchronisation continue entre deux clusters,
    mais nécessite un process serveur dédié tournant en continu et une API
    de supervision — trop lourd à opérer manuellement pour ce besoin ponctuel.
    Un dump/restore complet à chaque sens suffit : le risque de conflit avec
    un autre écrivain externe pendant ces sessions est négligeable.

## Phase 1 — Dump + restore vers le local (sur réseau domestique, avant de basculer)

Vérifier que le conteneur local `lmelp-mongo` est up avant de lancer le
restore (sinon le démarrer avec portainer) :

```bash
docker ps --filter "name=lmelp-mongo" --format "table {{.Names}}\t{{.Status}}"
```

```bash
# Dossier de backups horodaté (copier-coller sans adaptation)
export BACKUP_DIR="/home/guillaume/git/back-office-lmelp/data/processed/mongo-backup-$(date +%Y%m%d-%H%M%S)"

# Dump de la base de prod (NAS) vers ce dossier
mongodump --uri="mongodb://nas923:27018/masque_et_la_plume" --out="$BACKUP_DIR"

# Restore dans le Mongo local du laptop (écrase l'état local précédent)
mongorestore --uri="mongodb://localhost:27018/masque_et_la_plume" --drop "$BACKUP_DIR/masque_et_la_plume"
```

`$BACKUP_DIR` reste défini dans le terminal tant qu'il n'est pas fermé — les
deux commandes peuvent être copiées-collées sans adaptation. Garder le nom
du dossier horodaté permet de retrouver facilement quelle sauvegarde
restaurer si plusieurs cycles sont faits dans la même journée.

## Phase 2 — Bascule réseau + travail sur la base locale

### TEL: activer le point d'accès mobile

- lancer le hotspot

### TEL: VPN sur le mobile

- se déconnecter du wifi domestique
- lancer free mVPN

### ORDI: connecter le laptop sur ce réseau mobile

et tester sur <https://www.mon-ip.com/en/my-ip/> ou https://fr.geoipview.com/

### ORDI: lancer le serveur backoffice depuis vscode

Le `.env` du devcontainer pointe déjà sur `mongodb://localhost:27018/masque_et_la_plume`
(le Mongo Docker local du laptop) — c'est sa configuration normale de travail
au quotidien, rien à changer ici.

```bash
/workspaces/back-office-lmelp/scripts/start-dev.sh --restart
```

!!! info "info du service"
    ```bash
    /workspaces/back-office-lmelp/.claude/get-services-info.sh
    ```

Travailler normalement sur la page Migration Babelio / Contrôle Babelio :
toutes les écritures vont dans le Mongo local du laptop, sans dépendance au
NAS pendant cette phase.

## Phase 3 — Rapatriement (retour sur réseau domestique)

Une fois reconnecté au réseau domestique :

Vérifier que le conteneur local `lmelp-mongo` est toujours up avant le dump
(il a dû tourner pendant toute la phase de travail déconnecté) :

```bash
docker ps --filter "name=lmelp-mongo" --format "table {{.Names}}\t{{.Status}}"
```

```bash
# Dossier de backups horodaté (copier-coller sans adaptation)
export EXPORT_DIR="/home/guillaume/git/back-office-lmelp/data/processed/mongo-local-export-$(date +%Y%m%d-%H%M%S)"

# Dump de la base locale (contient les modifications faites en mode déconnecté)
mongodump --uri="mongodb://localhost:27018/masque_et_la_plume" --out="$EXPORT_DIR"

# Restore vers la base de prod (NAS), écrase avec les modifications locales
mongorestore --uri="mongodb://nas923:27018/masque_et_la_plume" --drop "$EXPORT_DIR/masque_et_la_plume"
```

Le `.env` du devcontainer reste inchangé (`localhost:27018`) puisque c'est
déjà sa valeur normale de travail au quotidien.
