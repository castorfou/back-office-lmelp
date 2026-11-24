---
status: accepted
---

# lmelp-streaming sert l'audio intégral derrière une clé d'écoute partagée

Écouter un **Passage** depuis lmelp-mobile ou depuis lmelp demande un service joignable
depuis internet, alors que lmelp et lmelp pap restent en « réseau local ». La SQLite et
l'APK de lmelp-mobile sont publiés en release GitHub publique : rien de ce qu'ils
contiennent n'est secret, et un lien signé qui expire ne peut pas y être figé. Les
auditeurs sont un petit cercle (le mainteneur, famille, amis), pas le public de l'APK.

Nous servons donc **le fichier audio intégral de l'épisode, tel quel**, depuis une 3e
application, `lmelp-streaming` : un conteneur `nginx:alpine` dédié, le dossier audios
monté en lecture seule, sans aucune route vers le backend, seule entrée du reverse proxy
DSM au profil « internet ». L'URL est `<base>/audios/<audio_rel_filename>` ; la SQLite
exporte le chemin relatif, la base est réglée côté client. Le **lecteur borne le
Passage** avec `debut`/`fin` (Media3 `ClippingConfiguration`, arrêt en JS sur le web) ;
Range natif, aucun découpage, aucun ffmpeg, aucun cache client (`Cache-Control:
no-store`).

L'accès exige une **clé d'écoute** unique, en en-tête `X-Lmelp-Cle` ou en paramètre
`?cle=` (un `<audio>` ne peut pas envoyer d'en-tête), plus `limit_req` par IP réelle
(`X-Real-IP` posé par DSM). La clé ne figure ni dans l'APK ni dans la SQLite : lmelp,
joignable en réseau local seulement, l'affiche en QR code (`lmelp://ecoute?base=…&cle=…`).

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
