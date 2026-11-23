# Recherche : servir des Passages sur internet

Ticket : castorfou/back-office-lmelp#389 (carte #387). Ce document rassemble des faits ; il
ne tranche rien. Date de collecte : 2026-11-23.

Rappel du cadrage (#387) : un **Passage** est une portion (quelques minutes) de l'audio
intégral d'un épisode ; il est servi par un **site dédié aux Passages**, seul exposé sur
internet par le reverse proxy DSM ; lmelp (web/PWA) et lmelp-mobile y écoutent en ligne ;
précision visée ±10 s, arrondie vers plus large.

## 1. Faits locaux : comment lmelp est déployé aujourd'hui

### 1.1 Stack et volumes

- La production tourne dans la stack unifiée **docker-lmelp** (un seul
  `docker-compose.yml`) sur un NAS Synology DS 923+ ; ce dépôt ne fait que publier les
  images `ghcr.io/castorfou/lmelp-backend` et `lmelp-frontend`
  ([docs/deployment/docker-setup.md](../deployment/docker-setup.md), « Vue d'ensemble »).
- Dossier audio : `AUDIO_PATH=/volume1/docker/lmelp/audios`
  ([docker-lmelp `.env.nas.example`](https://github.com/castorfou/docker-lmelp/blob/main/.env.nas.example),
  l. 127). Il est monté :
  - dans `backend` sur `/app/audios` (lecture/écriture, `AUDIO_STORAGE_PATH=/app/audios`) ;
  - dans `pap` sur `/audios-lmelp` (pap y dépose les remises) ;
  - **pas** dans `frontend` (nginx) ni dans aucun autre service
  ([docker-lmelp `docker-compose.yml`](https://github.com/castorfou/docker-lmelp/blob/main/docker-compose.yml),
  services `backend` l. 74-78, `pap` l. 221-231, `frontend` l. 134-156).
- Ports hôte publiés : `backend` 8000, `frontend` 8081 (NAS), `pap` 8090, `mongo` 27018
  (même fichier, et `.env.nas.example` l. 96-100). Automatisch appelle le backend
  directement sur l'IP LAN du NAS, port 8000 (`POST /api/rss/sync`)
  ([docker-lmelp `docs/user/migration-nas.md`](https://github.com/castorfou/docker-lmelp/blob/main/docs/user/migration-nas.md),
  étape 10).
- Réseau Docker commun `lmelp-network` ; Watchtower met à jour les conteneurs étiquetés
  (`com.centurylinklabs.watchtower.enable=true`).

### 1.2 Exposition : reverse proxy DSM

- Règle **lmelp** : source HTTPS 443 (HSTS) sur un nom d'hôte DDNS `*.synology.me`,
  destination HTTP `localhost:8081` (le frontend) ; **profil de contrôle d'accès « réseau
  local »** : « l'application n'est pas exposée sur Internet »
  ([docs/deployment/docker-setup.md](../deployment/docker-setup.md), « Reverse proxy DSM » ;
  [docs/deployment/troubleshooting.md](../deployment/troubleshooting.md) : « un échec depuis
  un autre réseau est le comportement attendu »).
- Même schéma pour `pap` (sous-domaine dédié, profil « réseau local »)
  (docker-lmelp `migration-nas.md`, étape 8).
- **Aucune authentification applicative** : ni le backend ni le frontend n'ont de login ; la
  seule barrière est le profil d'accès IP du reverse proxy (constat : aucune route ni
  dépendance d'authentification dans `src/back_office_lmelp/app.py`, aucune directive
  `auth_*` dans `nginx.conf`).

### 1.3 nginx du frontend

[docker/build/frontend/nginx.conf](../../docker/build/frontend/nginx.conf) : sert la SPA
(`try_files … /index.html`), relaie `/api/`, `/docs`, `/openapi.json` vers `backend:8000`
avec résolution dynamique (`resolver 127.0.0.11`, `set $backend`). Pas de location
audio, pas de `limit_req`, pas de `secure_link`. Image `nginx:alpine`
([docker/build/frontend/Dockerfile](../../docker/build/frontend/Dockerfile)), qui ne
contient pas `ffmpeg`. L'image backend n'installe pas `ffmpeg` non plus (seulement
`curl gosu openssh-client`, [docker/build/backend/Dockerfile](../../docker/build/backend/Dockerfile) l. 32).

### 1.4 Les fichiers audio eux-mêmes

- MongoDB (`episodes.audio_rel_filename`, base locale) : **131 `.mp3` et 115 `.m4a`** sur
  246 épisodes. Il faudra servir les deux conteneurs.
- Échantillon local (`data/audios`, 7 fichiers, sonde des en-têtes) :
  - `.m4a` : 68-80 Mo ; 6 sur 7 ont l'atome `moov` **avant** `mdat` (« faststart ») ; **un
    fichier de 2026 a `moov` en fin de fichier** (`ftyp,free,mdat,moov`). Un lecteur doit
    alors lire la fin du fichier (requête Range supplémentaire) avant de jouer.
  - `.mp3` (2026) : 44 Mo, première trame à 128 kbit/s, **sans en-tête Xing/Info/VBRI**.
  - Ordre de grandeur : 128 kbit/s ≈ 16 ko/s ⇒ un Passage de 5 min ≈ 4,8 Mo en mp3 ;
    72 Mo sur ~50 min ≈ 190 kbit/s ⇒ ≈ 7 Mo pour 5 min en m4a.
  - Échantillon non représentatif des 246 épisodes : à mesurer sur le NAS avant de décider.

### 1.5 lmelp-mobile

- Dépôt public `castorfou/lmelp-mobile` : Kotlin, Compose, Room ; `minSdk 26`,
  `targetSdk 35`
  ([app/build.gradle.kts](https://github.com/castorfou/lmelp-mobile/blob/main/app/build.gradle.kts)).
- **Aucune dépendance audio** aujourd'hui : ni `androidx.media3`, ni ExoPlayer dans
  [gradle/libs.versions.toml](https://github.com/castorfou/lmelp-mobile/blob/main/gradle/libs.versions.toml)
  (présents : OkHttp 4.12, Coil, DataStore, `androidx.car.app` 1.4.0). Permission
  `INTERNET` déjà déclarée (AndroidManifest).
- Données : base SQLite `lmelp.db` publiée **en release GitHub publique** `data-v{N}`
  ([README](https://github.com/castorfou/lmelp-mobile/blob/main/README.md)). Conséquence :
  toute valeur mise dans cette base (URL, jeton) est publique. L'APK est lui aussi publié en
  release publique.
- L'app a des écrans Android Auto (`ui/auto/*CarScreen.kt`) via la Car App Library. Cette
  bibliothèque cible les catégories navigation, POI, IoT et météo
  ([developer.android.com/training/cars/apps](https://developer.android.com/training/cars/apps)) :
  l'audio en voiture relèverait de l'architecture « media app » (MediaSession), pas de ces
  écrans. Hors périmètre ici, à noter pour #387.

## 2. Ce qu'acceptent les lecteurs

### 2.1 HTTP Range (RFC 9110)

- « Range requests are an OPTIONAL feature of HTTP » ; un serveur « MAY ignore the Range
  header field », mais « origin servers … ought to support byte ranges when possible »
  ([RFC 9110 §14, §14.2](https://www.rfc-editor.org/rfc/rfc9110.html#name-range-requests)).
- Le serveur annonce le support par `Accept-Ranges: bytes` (§14.3) et répond `206 Partial
  Content` avec `Content-Range` (§14.4, §15.3.7), ou `416` (§15.5.17).
- nginx sert les fichiers statiques avec Range ; `max_ranges` limite le nombre de plages
  (« By default, the number of ranges is not limited. The zero value disables the
  byte-range support completely »)
  ([ngx_http_core_module, max_ranges](https://nginx.org/en/docs/http/ngx_http_core_module.html#max_ranges)).
- Côté Python, `starlette.responses.FileResponse` (0.47.3 dans le venv) pose
  `accept-ranges: bytes`, gère `Range`/`If-Range`, répond 206/416 (source
  `starlette/responses.py` l. 325-405).

### 2.2 `<audio>` HTML

- Le chargement d'un média se fait par plages d'octets choisies par le navigateur
  (« byteRange … implementation-defined ») ; une réponse est acceptée si son statut est 200
  ou 206 avec un `Content-Range` syntaxiquement valide
  ([HTML Living Standard, media elements — « verify a media response », « resource fetch
  algorithm »](https://html.spec.whatwg.org/multipage/media.html)).
- `seekable` couvre tout le fichier « because … the user agent and the server support HTTP
  Range requests » (même page, §4.8.11.9 Seeking).
- La requête média est une « potential-CORS request » : sans attribut `crossorigin`, un
  `<audio>` peut lire un fichier d'une autre origine sans en-têtes CORS (même page, resource
  fetch algorithm). CORS ne devient nécessaire que si la page lit l'audio via `fetch()`/Web
  Audio ou met `crossorigin`.
- **Fragments média** : le W3C définit `#t=début,fin` (npt par défaut, intervalle semi-ouvert
  `[début, fin)`), résolu par le client « without another retrieval action » ; à
  l'affichage, le lecteur devrait « pause at the end of the fragment »
  ([W3C Media Fragments URI 1.0, Recommendation 2012-09-25, §3.1-3.3, §4.2.1,
  §7.2](https://www.w3.org/TR/media-frags/)). MDN documente `#t=[starttime][,endtime]` pour
  `<audio>`/`<video>`
  ([MDN, Audio and video delivery — Specifying playback range](https://developer.mozilla.org/en-US/docs/Web/Media/Guides/Audio_and_video_delivery)).
- Limite normative : la norme HTML ne rend obligatoire que la **position de départ**
  (« If either the media resource or the URL … indicate a particular start time, then set the
  initial playback position to that time … with media formats that support media fragment
  syntax, the fragment can be used to indicate a start position »). L'arrêt à la fin du
  fragment n'y est pas imposé : à vérifier par navigateur, ou à garantir en JS (écoute de
  `timeupdate` puis `pause()` quand `currentTime >= fin`).
- Le fragment n'est jamais envoyé au serveur : avec « intégral + décalage », le serveur sert
  le fichier entier et l'auditeur peut sortir du Passage.

### 2.3 Android Media3 / ExoPlayer

- Pas de Media3 dans l'app aujourd'hui (§1.5). Version courante : Media3 1.11.1
  (2026-09-10, [RELEASENOTES.md](https://github.com/androidx/media/blob/release/RELEASENOTES.md)).
- **Clipping natif** : `MediaItem.ClippingConfiguration.Builder().setStartPositionMs()
  .setEndPositionMs()` ; « `DefaultMediaSourceFactory` will use a `ClippingMediaSource` to
  wrap the content media source »
  ([Media items — Clipping a media stream](https://developer.android.com/media/media3/exoplayer/media-items)).
  Le clipping n'est supporté qu'avec `DefaultMediaSourceFactory` (même page, « Known issue
  #185 »). Une seule URL d'intégral suffit donc pour jouer un Passage borné, et la barre de
  progression montre la durée du Passage.
- **Range** : `DefaultHttpDataSource` envoie `Range: bytes=<position>-[<fin>]`
  (`HttpUtil.buildRangeRequestHeader`,
  [source](https://github.com/androidx/media/blob/release/libraries/datasource/src/main/java/androidx/media3/datasource/HttpUtil.java)).
- **Formats progressifs** : MP4 et M4A « YES » ; MP3 « YES — Some streams only seekable
  using constant bitrate seeking »
  ([Supported formats](https://developer.android.com/media/media3/exoplayer/supported-formats)).
- **Précision du seek MP3** : « Variable bitrate (VBR) MP3 files are fundamentally
  unsuitable for use cases that require exact seeking » ; seek exact possible seulement avec
  `FLAG_ENABLE_INDEX_SEEKING` (scan de tout le fichier, désactivé par défaut) ;
  recommandation : « use a more appropriate container format, such as MP4 »
  ([Troubleshooting — Why is seeking inaccurate in some MP3 files?](https://developer.android.com/media/media3/exoplayer/troubleshooting)).
  `setConstantBitrateSeekingEnabled(true)` active le seek approximatif CBR
  ([Customization — Enabling constant bitrate seeking](https://developer.android.com/media/media3/exoplayer/customization)).
- Source `Mp3Extractor.computeSeeker()` : sans métadonnée ni trame Xing/VBRI, ExoPlayer
  prend **par défaut** un `ConstantBitrateSeeker`
  ([source](https://github.com/androidx/media/blob/release/libraries/extractor/src/main/java/androidx/media3/extractor/mp3/Mp3Extractor.java)).
  Le mp3 échantillonné (CBR 128 kbit/s sans en-tête, §1.4) serait donc seekable, avec une
  précision correcte s'il est vraiment CBR. Un mp3 VBR avec en-tête Xing imprécis peut
  décaler le début, sans doute de quelques secondes (marge ±10 s de #387).
- **En-têtes et jeton** : un `DataSource.Factory` personnalisé peut ajouter un en-tête à
  chaque requête (« your app may authenticate itself by injecting a token as a header »), ou
  un `ResolvingDataSource` peut réécrire l'URI juste avant la requête (signature à la volée)
  (Customization — Customizing server interactions).
- Redirections : ExoPlayer ne suit pas par défaut une redirection HTTPS→HTTP
  (« cross-protocol redirect ») ; le trafic en clair est interdit par défaut à partir de
  `targetSdk 28` (Troubleshooting). Le site des Passages doit donc servir en HTTPS, sans
  redirection vers HTTP.
- Lecture en arrière-plan : service au premier plan plus `setWakeMode` (Troubleshooting —
  « How do I keep audio playing when my app is backgrounded? »).

## 3. Options de service

| | A. Découpe à la volée (ffmpeg) | B. Passages prédécoupés | C. Intégral + décalage |
|---|---|---|---|
| Ce qui part sur internet | le Passage seul | le Passage seul | le fichier intégral (Range) |
| Calcul NAS | à chaque requête (copie de flux) | une fois, à la publication / correction | aucun |
| Stockage | aucun | ≤ taille de l'archive (≈ 246 × 70 Mo ≈ 17 Go au pire, beaucoup moins en pratique) | aucun |
| Seek / Range dans le Passage | délicat (flux généré) sauf mise en cache | natif (fichier statique) | natif |
| Correction manuelle | immédiate | re-découpe du Passage corrigé | immédiate (bornes en base) |
| Web | `<audio src=…>` simple | `<audio src=…>` simple | `#t=` + garde JS pour la fin |
| Android | `MediaItem.fromUri` | `MediaItem.fromUri` | `ClippingConfiguration` |

### A. Découpe à la volée

- `ffmpeg -ss <début> -i <fichier> -t <durée> -c copy` : `-ss` avant `-i` « seeks in this
  input file to position » vers le point de seek précédent ; en copie de flux, le segment
  entre ce point et la position **est conservé** (début légèrement plus tôt, sens « plus
  large » voulu) ; la copie de flux est « very fast and there is no quality loss »
  ([ffmpeg documentation, §3.1 Streamcopy, §5.4 Main options](https://ffmpeg.org/ffmpeg.html)).
  Sans ré-encodage, le coût CPU est faible ; il reste l'I/O et un process par requête.
- Une réponse générée n'a pas de taille connue d'avance : pas de Range simple, donc seek
  limité, sauf à écrire le résultat dans un cache disque (cela revient à B, paresseux).
  Chaque reprise de lecture ou seek peut relancer une découpe.
- Variante nginx sans ffmpeg, **m4a seulement** : `ngx_http_mp4_module` gère les arguments
  `start` et `end` (secondes, `end` depuis 1.5.13) pour `.mp4/.m4v/.m4a` ; sans arguments,
  « the file is sent simply as a static resource »
  ([ngx_http_mp4_module](https://nginx.org/en/docs/http/ngx_http_mp4_module.html)). La doc
  ne décrit pas le cas audio seul : à tester. Rien d'équivalent pour le mp3.
- Ni l'image backend ni l'image frontend ne contiennent ffmpeg (§1.3).

### B. Passages prédécoupés

- Fichiers statiques servis par nginx (Range, cache, `Accept-Ranges` natifs) ; le site
  dédié n'a besoin d'aucun accès au dossier audio intégral, seulement à un dossier
  « passages ».
- Le découpage peut se faire hors du NAS (PGX, qui reçoit déjà les audios) ou dans le
  backend (ffmpeg à ajouter à l'image, cf. la règle de CLAUDE.md sur les binaires système
  dans le Dockerfile).
- Possibilité de normaliser le format (ex. tout en m4a/AAC « faststart ») : cela règle à la
  fois le seek MP3 imprécis (§2.3) et le `moov` en fin de fichier (§1.4). Un ré-encodage
  coûte du CPU, mais une seule fois par Passage.
- Une correction manuelle des bornes (#387, « Not yet specified ») impose de re-découper
  et d'invalider le cache client (URL versionnée).

### C. Intégral + décalage

- Aucun traitement serveur : nginx sert le fichier intégral avec Range ; le client se
  positionne. Web : `#t=début,fin` (départ normatif, fin à garantir en JS, §2.2). Android :
  `ClippingConfiguration` (§2.3).
- Le **fichier intégral** est exposé sur internet : quiconque a l'URL peut tout écouter
  ou tout télécharger (le fragment `#t` n'est pas transmis au serveur). Le site expose alors
  l'archive, pas seulement des Passages.
- Le premier accès lit l'index du conteneur : immédiat pour un m4a faststart, il faut une
  requête de plus en fin de fichier pour un m4a `moov` à la fin, et le seek est approximatif
  pour un mp3 VBR.

## 4. Protection minimale

### 4.1 Ce que DSM offre nativement (reverse proxy)

D'après la page officielle « Login Portal > Advanced »
([Synology KB, DSM 7](https://kb.synology.com/en-global/DSM/help/DSM/AdminCenter/system_login_portal_advanced?version=7)) :

- par règle : protocole, nom d'hôte, port source/destination, **HSTS**, **profil de
  contrôle d'accès** (listes Allow/Deny par IP/CIDR, appliquées de haut en bas, avec une
  règle Deny à ajouter pour activer une liste blanche) ;
- **Custom Header** (raccourci WebSocket) ;
- **Advanced Settings** : timeouts de connexion, d'envoi et de lecture, version HTTP vers la
  cible, page d'erreur de la cible ;
- note : un profil d'accès peut faire échouer le renouvellement Let's Encrypt.

La page ne mentionne **ni authentification, ni limitation de débit**. Le profil d'accès
filtre par IP source, ce qui ne convient pas à des mobiles sur réseau opérateur. Le site
dédié serait donc une règle sans profil restrictif (ou avec une liste Deny), et la
protection serait à faire dans le site lui-même.

### 4.2 Ce que nginx offre (image officielle `nginx:alpine`)

Les paquets officiels nginx (utilisés par l'image Docker `nginx`) sont compilés avec
`--with-http_secure_link_module`, `--with-http_mp4_module`, `--with-http_realip_module`,
`--with-http_auth_request_module`, `--with-http_slice_module`
([nginx/pkg-oss `alpine/Makefile`](https://github.com/nginx/pkg-oss/blob/master/alpine/Makefile),
`BASE_CONFIGURE_ARGS`). `limit_req` fait partie des modules standard. Pas de docker dans le
devcontainer : à confirmer par `nginx -V` sur l'image retenue.

- **Liens signés, avec expiration** : `secure_link $arg_md5,$arg_expires;` et
  `secure_link_md5 "$secure_link_expires$uri$remote_addr secret";` ; `$secure_link` vaut
  `""` (signature fausse → 403), `"0"` (expiré → 410) ou `"1"` ; hash MD5 en base64url
  ([ngx_http_secure_link_module](https://nginx.org/en/docs/http/ngx_http_secure_link_module.html)).
  Le module n'est pas compilé par défaut, mais il l'est dans les paquets officiels (§4.2).
  Lier la signature à `$remote_addr` est fragile : derrière le proxy DSM, `$remote_addr` est
  l'adresse du proxy, sauf avec `realip` ; et l'IP d'un mobile change.
- **Limitation de débit** : `limit_req_zone $binary_remote_addr zone=…:10m rate=1r/s;` et
  `limit_req zone=… burst=5 [nodelay];` (seau percé), refus en 503 par défaut,
  `limit_req_status 429` possible
  ([ngx_http_limit_req_module](https://nginx.org/en/docs/http/ngx_http_limit_req_module.html)).
  Une lecture avec seek émet plusieurs requêtes Range : un `burst` trop bas casse la lecture.
  La clé doit être l'IP réelle du client, donc `realip`
  ([ngx_http_realip_module](https://nginx.org/en/docs/http/ngx_http_realip_module.html))
  avec `set_real_ip_from` vers le proxy DSM. **Non vérifié** : quels en-têtes
  (`X-Forwarded-For`, `X-Real-IP`) le proxy DSM transmet par défaut ; à tester.
- **Accès interne seulement** : `internal;` rend une location inaccessible de l'extérieur,
  sauf via `X-Accel-Redirect` renvoyé par un amont
  ([ngx_http_core_module, internal](https://nginx.org/en/docs/http/ngx_http_core_module.html#internal)).
  Cela permet qu'un petit service valide un jeton puis délègue l'envoi du fichier (avec
  Range) à nginx.
- **Bornage des plages** : `max_ranges 1` refuse les requêtes multi-plages (cf. RFC 9110 §14.2
  sur les plages nombreuses comme signe de déni de service).

### 4.3 Contraintes propres à lmelp

- Le SQLite mobile et l'APK sont **publics** (§1.5). Un identifiant ou un jeton stocké dans
  le SQLite n'est pas secret : il rend une URL *non devinable* (pas d'énumération
  `/episode/1`, `/episode/2`…), pas *privée*.
- Une signature **avec expiration** ne peut pas être figée dans un SQLite publié toutes les
  heures et consulté hors ligne. Il faudrait un émetteur de signatures joignable depuis
  internet (donc exposé lui aussi), ou une signature calculée par l'app avec un secret
  qu'elle embarque (extractible de l'APK public), ou saisi par l'utilisateur (DataStore
  existe déjà dans l'app).
- Le web/PWA lmelp n'est joignable qu'en réseau local (§1.2) : depuis le LAN, le site des
  Passages est atteint par le même nom DDNS, et le profil d'accès ne s'applique qu'à la
  règle lmelp, pas à celle du site des Passages.
- Avec l'option C, la protection doit couvrir tout le fichier intégral ; avec A et B, une
  URL qui fuit ne donne qu'un Passage.
- Le site dédié n'a pas besoin de MongoDB : en B, un dossier de fichiers suffit ; en C, une
  table de correspondance « id opaque → fichier » suffit (fichier statique, ou nom de fichier
  = id opaque).

## 5. Points ouverts à mesurer (pas tranchés ici)

1. Répartition réelle CBR/VBR des 131 mp3 et part des m4a avec `moov` en fin, mesurées sur le
   NAS (`ffprobe`), pas sur l'échantillon local.
2. Le reverse proxy DSM transmet-il `Range` et renvoie-t-il bien les `206` ? Test : `curl -I
   -H 'Range: bytes=0-99'` à travers la règle.
3. En-têtes d'IP client posés par DSM (pour `realip` et `limit_req`).
4. Comportement de `#t=début,fin` en fin de fragment dans Chrome Android (PWA) et Firefox.
5. Comportement de `ngx_http_mp4_module` (`start`/`end`) sur un m4a audio seul.
