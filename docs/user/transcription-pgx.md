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
    pas fiable. Si PGX est injoignable, le pipeline s'arrête avec un message clair invitant
    à l'allumer puis à réessayer.

## Accès à l'interface

### Depuis le tableau de bord

Deux tuiles y mènent :

- **"Épisodes sans transcription"** de la section "Informations générales".
- **"Transcriptions PGX"** de la section "Podcast Masque Et La Plume".

### Navigation directe

URL directe : `/transcription-pgx`

## Vérifier la configuration

La checklist de diagnostic s'exécute **automatiquement** au chargement de la page, avec un
statut 🟢/🔴/⚪ par étape :

1. **Machine joignable** — le port SSH répond.
2. **Authentification SSH (clé dédiée)** — une vraie connexion est testée (pas juste le
   port ouvert). En cas d'échec, le détail SSH réel est inclus dans le message pour en
   identifier la cause précise (voir [Dépannage](#depannage)).
3. **Répertoire audio distant** — le répertoire configuré existe sur PGX.
4. **Répertoire transcriptions distant** — le répertoire configuré existe sur PGX.

Chaque étape court-circuite les suivantes si elle échoue (inutile de tester
l'authentification si injoignable, par exemple). Si des variables d'environnement PGX sont
manquantes (voir `docs/dev/environment-variables.md`), la checklist n'est pas exécutée et un
message liste les variables absentes.

Le bouton **"🔄 Rafraîchir le statut"** relance manuellement la checklist et la liste des
épisodes en attente, sans recharger toute la page (utile après avoir allumé PGX ou déployé
une clé SSH sur `authorized_keys`).

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

## Voir aussi

- `docs/dev/environment-variables.md` — configuration complète des variables `PGX_*`.
- `docs/user/rss-monitoring.md` — page où se trouve la section transcription PGX.
