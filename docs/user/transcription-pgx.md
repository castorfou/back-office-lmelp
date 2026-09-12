# Transcription automatisée via PGX

back-office-lmelp transcrit les épisodes audio en s'appuyant sur une station GPU dédiée
sur le réseau local (surnommée **PGX**). Un service de transcription tourne en permanence
sur cette station : il surveille un répertoire, transcrit automatiquement tout fichier
audio qui y est déposé, et écrit le résultat dans un répertoire de sortie.

La page dédiée **Transcription PGX** (`/transcription-pgx`) affiche l'état de PGX et
permet de déclencher la transcription de tous les épisodes en attente en une seule
action. Elle est accessible depuis la section **"Podcast Masque Et La Plume"** du
tableau de bord, aux côtés de la tuile "Monitoring Downloads" (synchronisation RSS) —
deux fonctionnalités liées mais indépendantes, chacune avec sa propre page.

## Ce que fait une transcription

Pour chaque épisode sans transcription, dans l'ordre :

1. Si une transcription a déjà été produite lors d'un run précédent et se trouve encore
   sur le disque local (à côté du fichier audio), elle est réutilisée directement — aucun
   nouvel envoi vers PGX n'est nécessaire pour cet épisode.
2. Sinon : vérification que PGX est joignable sur le réseau, envoi du fichier audio par
   `scp`, attente de la transcription générée par le service PGX, puis rapatriement du
   fichier de transcription.
3. Intégration du texte en base MongoDB.

Le bouton **"▶️ Lancer la transcription des épisodes en attente"** est **désactivé** tant
que la checklist de diagnostic n'est pas entièrement verte (machine joignable,
authentification SSH, répertoires distants) ou qu'aucun épisode n'est en attente — un
message invite alors à corriger la configuration avant de réessayer, plutôt que de laisser
échouer une transcription vouée à l'échec.

Le traitement porte sur **tous** les épisodes en attente en une seule fois, traités les uns
après les autres (une seule machine PGX, pas de traitement en parallèle). La progression
s'affiche en temps réel : épisode en cours, logs détaillés par étape, résultat final
(succès/échec par épisode).

!!! info "Un échec sur un épisode n'arrête pas les autres"
    Si un épisode échoue (timeout, erreur de transfert), le traitement passe au suivant de
    la file plutôt que d'abandonner l'ensemble — sauf si PGX elle-même est injoignable dès
    le départ, auquel cas toute la file s'arrête immédiatement (un nouvel essai réseau par
    épisode ne résoudrait rien).

!!! info "Pas de réveil automatique"
    PGX doit être **allumée manuellement** avant de lancer une transcription. Le pipeline ne
    tente aucun réveil à distance (Wake-on-LAN) : sur une machine Wi-Fi uniquement avec la
    mise en veille système désactivée pour des raisons de stabilité GPU, ce mécanisme n'est
    pas fiable. Depuis un déclenchement manuel (bouton), le pipeline s'arrête immédiatement
    avec un message clair invitant à l'allumer puis à réessayer — depuis un déclenchement
    externe automatisé, voir "Déclenchement automatique et historique" ci-dessous.

## Accès à l'interface

### Depuis le tableau de bord

Deux tuiles y mènent :

- **"Épisodes sans transcription"** de la section "Informations générales".
- **"Transcriptions PGX"** de la section "Podcast Masque Et La Plume".

### Navigation directe

URL directe : `/transcription-pgx`

## Vérifier la configuration

La checklist de diagnostic s'exécute **automatiquement** au chargement de la page, avec un
statut 🟢/🔴/⚪ par étape, et reste **toujours visible** — y compris quand la configuration
PGX est incomplète :

1. **Machine joignable** — le port SSH répond.
2. **Authentification SSH (clé dédiée)** — une vraie connexion est testée (pas juste le
   port ouvert). En cas d'échec, le détail SSH réel est inclus dans le message pour en
   identifier la cause précise (voir [Dépannage](#depannage)).
3. **Répertoire audio distant** — le répertoire configuré existe sur PGX.
4. **Répertoire transcriptions distant** — le répertoire configuré existe sur PGX.

Chaque étape court-circuite les suivantes si elle échoue (inutile de tester
l'authentification si injoignable, par exemple). Si des variables d'environnement PGX sont
manquantes (voir `docs/dev/environment-variables.md`), aucun appel réseau n'est tenté : les 4
étapes s'affichent en statut ⚪ (non exécuté) et un message au-dessus liste les variables
absentes.

Le bouton **"🔄 Rafraîchir le statut"** relance manuellement la checklist, la clé SSH et la
liste des épisodes en attente, sans recharger toute la page (utile après avoir allumé PGX ou
déployé une clé SSH sur `authorized_keys`).

## Clé SSH dédiée

Dès que `PGX_SSH_KEY_PATH` est configuré (voir `docs/dev/environment-variables.md`), la page
affiche :

- La **clé publique** générée automatiquement au premier démarrage (idempotent : la même
  clé est réutilisée à chaque redémarrage tant que le fichier existe à cet emplacement — sur
  un volume Docker persistant en production, elle ne change donc jamais après le premier
  déploiement).
- La **commande à exécuter sur PGX** pour l'autoriser :
  ```bash
  echo '<clé publique>' >> ~/.ssh/authorized_keys
  ```

Cette section reste visible même si le reste de la configuration (`PGX_HOST`, `PGX_USER`,
répertoires distants) est encore incomplet — la clé doit pouvoir être déployée sur PGX en
amont, avant que les autres variables ne soient renseignées.

## Déclenchement automatique et historique

En plus du bouton manuel, la transcription peut être déclenchée par un outil
d'automatisation externe (n8n/Automatisch), par exemple une fois par jour ou à la
détection d'un nouvel épisode via le flux RSS déjà en place. Ce déclenchement
externe se distingue du bouton par un comportement plus tolérant à une PGX éteinte :

!!! tip "Retry automatique si PGX est éteinte"
    Si PGX est injoignable au moment d'un déclenchement externe, le backend ne
    reste **pas bloqué en échec** : il réessaie automatiquement, toutes les heures,
    pendant 24h maximum — sans qu'il soit nécessaire de redéclencher manuellement.
    Une notification (si les notifications ntfy.sh sont configurées) prévient dès
    le premier échec, pour savoir qu'il faut allumer PGX — pas de rappel répété
    ensuite tant que PGX reste éteinte. Chaque épisode transcrit avec succès (ou en
    échec) envoie ensuite sa propre notification, avec son titre, comme pour les
    nouveaux épisodes détectés sur le flux RSS.

Une nouvelle section **"📋 Historique des transcriptions"**, sous le panneau de
progression, liste tous les cycles — qu'ils aient été déclenchés manuellement
(bouton) ou automatiquement — avec leur date (heure de fin, ou heure de début tant
que le cycle n'est pas terminé), leur mode de déclenchement, leur statut
(`success`/`error`/`pgx`), et le nombre d'épisodes traités. Cliquer sur une ligne
déroule le détail : épisodes traités (succès/échec) et, le cas échéant, l'heure de
démarrage, un résumé des tentatives de retry ("repris après N tentative(s)" ou
"toujours injoignable"), et le détail de chaque tentative.

Un cycle qui attend PGX (statut `pgx`) apparaît **dès sa première tentative
ratée** — pas seulement une fois terminé — pour rester visible même si l'attente
dure plusieurs heures. La liste et le détail ouvert se rafraîchissent
automatiquement pendant qu'un cycle est en cours, et au clic sur "🔄 Rafraîchir".

Si un cycle est en attente d'une prochaine tentative de retry, un bandeau
⏳ apparaît dans le panneau de progression, indiquant l'heure approximative de la
prochaine tentative.

## Dépannage {#depannage}

### "PGX injoignable"

- Vérifiez que PGX est bien sous tension et sur le réseau — aucun réveil automatique n'est
  tenté, elle doit être allumée manuellement au préalable.
- Consultez la checklist de diagnostic sur `/transcription-pgx` pour un état rapide.

### "Authentification SSH (clé dédiée)" échoue malgré une clé bien déployée

Le message affiché pour cette étape inclut le **détail SSH réel** (stderr de la tentative
de connexion), utile pour distinguer une clé effectivement absente d'`authorized_keys`
d'une tout autre cause :

- `Permissions ... are too open` / `UNPROTECTED PRIVATE KEY FILE!` : la clé privée pointée
  par `PGX_SSH_KEY_PATH` a des permissions trop ouvertes (ex: `777` au lieu de `600`) — ssh
  l'ignore alors silencieusement et retombe sur une authentification par mot de passe, qui
  échoue.
- `Host key verification failed` / avertissement de clé d'hôte : la clé d'hôte de PGX a
  changé (réinstallation, reconfiguration de `sshd`), ou `PGX_HOST` était configuré avec un
  nom `.local` qui a résolu vers une IP différente entre deux connexions — utilisez
  toujours une IP directe (voir `docs/dev/environment-variables.md`).
- Un stderr vide malgré l'échec (aucun détail complémentaire) : le message générique reste
  alors le seul indice — vérifiez bien le contenu d'`authorized_keys` sur PGX dans ce cas
  précis.

### Échec de l'envoi ou du rapatriement du fichier (`scp`)

- Vérifiez que la clé privée SSH configurée est valide et lisible par le processus backend.
- Vérifiez que la clé publique correspondante est bien dans le `authorized_keys` du compte
  configuré sur PGX.
- Vérifiez que les répertoires distants audio/transcriptions existent bien sur PGX et sont
  accessibles en écriture/lecture par l'utilisateur SSH configuré.

### Timeout en attente de la transcription

- Vérifiez que le service de transcription tourne bien sur PGX et surveille effectivement
  le répertoire audio configuré.
- Pour un épisode particulièrement long, augmentez `PGX_TRANSCRIPTION_TIMEOUT_S` (voir
  `docs/dev/environment-variables.md`).

### Erreur `[Errno 2] No such file or directory` dans les logs backend

Toutes les étapes de diagnostic échouent avec cette erreur (et non un message d'échec
d'authentification ou de joignabilité). Cela signifie que les commandes système `ssh`/`scp`
ne sont pas installées dans l'environnement d'exécution du backend — pas un problème de
configuration PGX. En déploiement Docker, vérifiez que l'image du service `backend` inclut
bien le paquet `openssh-client` (voir `docs/dev/environment-variables.md` et la
documentation `docker-lmelp` du service `backend`).

## Voir aussi

- `docs/dev/environment-variables.md` — configuration complète des variables `PGX_*`.
- `docs/dev/pgx-transcription.md` — documentation développeur (architecture, patterns).
- `docs/dev/automatisch-pgx-transcription.md` — configuration du déclenchement externe
  via Automatisch, sur le modèle de la synchronisation RSS.
