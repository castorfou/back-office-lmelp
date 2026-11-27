---
status: accepted
---

# lmelp-streaming sert l'audio intégral derrière une clé d'écoute partagée

Écouter un **Passage** depuis lmelp-mobile demande un service joignable depuis internet,
alors que lmelp et lmelp pap restent en « réseau local ». La SQLite et l'APK de
lmelp-mobile sont publiés en release GitHub publique : rien de ce qu'ils contiennent n'est
secret, et un lien signé qui expire ne peut pas y être figé. Les auditeurs sont un petit
cercle (le mainteneur, famille, amis), pas le public de l'APK.

Nous servons donc **le fichier audio intégral de l'épisode, tel quel**, depuis une 3e
application, `lmelp-streaming` : un conteneur `nginx:alpine` dédié, le dossier audios
monté en lecture seule, seule entrée du reverse proxy DSM au profil « internet ». L'URL est
`<base>/audios/<audio_rel_filename>` ; la SQLite exporte le chemin relatif, la base est
réglée côté client. Le **lecteur borne le Passage** avec `debut`/`fin` (Media3
`ClippingConfiguration`) ; Range natif, aucun découpage, aucun ffmpeg, aucun cache client
(`Cache-Control: no-store`).

lmelp (web) n'utilise pas `lmelp-streaming` : il lit l'audio depuis son propre backend, en
réseau local, sans clé, et borne le Passage en JS.

L'accès exige une **clé d'écoute** unique, en en-tête `X-Lmelp-Cle` ou en paramètre
`?cle=`, plus `limit_req` par IP réelle (`X-Real-IP` posé par DSM). La clé vit dans
MongoDB, générée par le backend au premier démarrage ; elle ne figure ni dans l'APK, ni
dans la SQLite, ni dans une variable d'environnement. `lmelp-streaming` la fait vérifier
au backend par une sous-requête `auth_request` (route `internal`, sur le réseau Docker) et
garde en cache 60 s les réponses « valide » ; un refus n'est pas mis en cache, et un
backend injoignable vaut refus. La page « Configuration mobile » de lmelp, joignable en
réseau local seulement, affiche la clé en QR code (`lmelp://ecoute?base=…&cle=…`) et
permet de l'invalider : une nouvelle clé la remplace, l'ancienne est refusée dès la fin
du cache, sans période de grâce, et chaque auditeur rescanne. Seules les dates des
changements sont gardées, jamais les anciennes clés.

`lmelp-streaming` ne relaie vers le backend que deux chemins, en liste blanche vérifiée
par un test de sa configuration : la vérification de la clé et `POST /signalements`
(signalement d'un Passage mal découpé, lui aussi soumis à la clé). La lecture et
l'invalidation de la clé restent des routes du backend en réseau local.

Conséquence acceptée : une correction manuelle d'un Passage n'atteint lmelp-mobile qu'à la
release suivante de la SQLite (le web lit MongoDB en direct).

## Considered Options

- **Passages prédécoupés** (un fichier par Passage, URL stable par Passage) : écarté. Une
  chaîne de découpe (ffmpeg), une redécoupe à chaque correction et ~10-15 Go dupliqués,
  pour ne pas exposer un intégral que le futur téléchargement d'épisode exposera de toute
  façon.
- **Découpe à la volée** : écarté, ffmpeg exposé sur internet, Range difficile, et un
  service applicatif joignable depuis l'extérieur.
- **Clé par auditeur** : écarté, une liste à gérer pour un petit cercle ; changer la clé
  unique et rescanner le QR suffit.
- **Second `server` dans le nginx du frontend** : écarté, l'entrée internet arriverait sur
  le même process que l'API.
- **URL par identifiant d'épisode** (`/episodes/<oid>`) : écarté, nginx statique ne sait
  pas traduire un id en fichier sans lien symbolique ou `map` à tenir synchronisés.
- **Clé dans une variable d'environnement de nginx** : écarté, un bouton dans lmelp ne
  peut pas la changer.
- **Fichier de clé partagé, nginx rechargé par lmelp** : écarté, recharger un autre
  conteneur demande le socket Docker, c'est-à-dire la main sur tout le NAS.
- **lmelp (web) lit aussi par `lmelp-streaming`** : écarté, la clé finirait dans une URL
  `?cle=` du navigateur alors que lmelp lit déjà l'audio en local.
