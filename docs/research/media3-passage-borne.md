# Recherche : lire un Passage borné avec Media3

Ticket : castorfou/back-office-lmelp#419 (carte #387). Date de collecte : 2026-11-27.

Rappel du cadrage (#387, #393, #394) : lmelp-mobile lit en ligne un **Passage**, portion
`[debut, fin]` (ms) de l'audio intégral d'un épisode, servi par le conteneur nginx
`lmelp-streaming` à `/audios/<audio_rel_filename>`, derrière le reverse proxy DSM qui
conserve les réponses `206`. Une clé d'écoute unique part en en-tête HTTP ou en `?cle=`.
Pas de cache client. 134 mp3 tous CBR ; 119 m4a dont 4 avec `moov` en fin de fichier.

**Version étudiée** : Media3 **1.11.1** (dernière stable, 2026-09-11 ; 1.12.0-rc01 sortie le
2026-11-25). Les liens de code pointent sur le tag `1.11.1` (commit `8c6678b`). Les numéros de
ligne sont ceux de ce tag.

Abréviations des liens :

- `CMP` = [`ClippingMediaPeriod.java`](https://github.com/androidx/media/blob/1.11.1/libraries/exoplayer/src/main/java/androidx/media3/exoplayer/source/ClippingMediaPeriod.java)
- `CMS` = [`ClippingMediaSource.java`](https://github.com/androidx/media/blob/1.11.1/libraries/exoplayer/src/main/java/androidx/media3/exoplayer/source/ClippingMediaSource.java)
- `PMP` = [`ProgressiveMediaPeriod.java`](https://github.com/androidx/media/blob/1.11.1/libraries/exoplayer/src/main/java/androidx/media3/exoplayer/source/ProgressiveMediaPeriod.java)
- `MP3X` = [`Mp3Extractor.java`](https://github.com/androidx/media/blob/1.11.1/libraries/extractor/src/main/java/androidx/media3/extractor/mp3/Mp3Extractor.java)
- `MP4X` = [`Mp4Extractor.java`](https://github.com/androidx/media/blob/1.11.1/libraries/extractor/src/main/java/androidx/media3/extractor/mp4/Mp4Extractor.java)
- `DHDS` = [`DefaultHttpDataSource.java`](https://github.com/androidx/media/blob/1.11.1/libraries/datasource/src/main/java/androidx/media3/datasource/DefaultHttpDataSource.java)
- `RN` = [`RELEASENOTES.md`](https://github.com/androidx/media/blob/1.11.1/RELEASENOTES.md)

## 1. Lecture bornée : `MediaItem.ClippingConfiguration`

### 1.1 L'API

La documentation officielle
([Media items, « Clipping a media stream »](https://developer.android.com/media/media3/exoplayer/media-items#clipping-a-media-stream))
borne un `MediaItem` ainsi :

```kotlin
val mediaItem = MediaItem.Builder()
    .setUri("https://<hôte>/audios/<audio_rel_filename>")
    .setClippingConfiguration(
        MediaItem.ClippingConfiguration.Builder()
            .setStartPositionMs(passage.debut)
            .setEndPositionMs(passage.fin)
            .build())
    .build()
```

- « Internally, `DefaultMediaSourceFactory` will use a `ClippingMediaSource` to wrap the
  content media source. » Même page, mise en garde : le clipping n'est pris en charge
  « only if you use `DefaultMediaSourceFactory` »
  ([androidx/media#185](https://github.com/androidx/media/issues/185)).
- La position du lecteur est alors **relative au Passage** : `currentPosition` va de 0 à
  `fin - debut`, `duration` vaut `fin - debut` (fenêtre `windowStartUs`/`windowEndUs`
  posée à partir de `config.startPositionUs`/`endPositionUs`, `CMS` l. 455-466). Une barre de
  progression standard montre donc le Passage seul.
- Un départ non nul exige un média seekable, sinon
  `IllegalClippingException(REASON_NOT_SEEKABLE_TO_START)` (`CMS` l. 268-304 ;
  `setAllowUnseekableMedia` existe depuis 1.6.0, `RN` l. 1938). Nos fichiers sont seekables
  (§3).

### 1.2 Comment le démarrage est obtenu (et ce qui circule sur le réseau)

`ClippingMediaSource` ne fait pas de requête particulière : il enveloppe le
`ProgressiveMediaPeriod` normal et lui demande une sélection de pistes à la position
`debut`. Déroulé lu dans le code :

1. **Préparation** : `ProgressiveMediaPeriod` ouvre le fichier à l'octet 0
   (`ExtractingLoadable` construit avec `buildDataSpec(position = 0)`, `PMP` l. 1280-1283) :
   requête **sans en-tête `Range`** (`HttpUtil.buildRangeRequestHeader()` renvoie `null` pour
   `position == 0` et longueur inconnue,
   [`HttpUtil.java` l. 57-69](https://github.com/androidx/media/blob/1.11.1/libraries/datasource/src/main/java/androidx/media3/datasource/HttpUtil.java#L57-L69)).
   L'extracteur y lit l'en-tête (ID3 + première trame mp3, ou `ftyp`/`moov` mp4) et publie
   la table de seek (`SeekMap`).
2. **Seek initial** : à la première sélection de pistes à une position non nulle, un seek est
   obligatoire (`seekRequired = … positionUs != 0`, `PMP` l. 376-378). `seekToUs()` tente
   d'abord de rester dans le tampon, sinon **annule le chargement en cours** et pose
   `pendingResetPositionUs` (`PMP` l. 584-627).
3. **Requête Range directe** : le chargement redémarre à
   `seekMap.getSeekPoints(pendingResetPositionUs).first.position` (`PMP` l. 1060-1078), donc
   `Range: bytes=<octet de debut>-` (ouvert, sans borne de fin, `HttpUtil` l. 61-68).

**Media3 ne télécharge donc pas depuis le début** : il lit l'en-tête du fichier, coupe, puis
saute directement à l'octet du Passage. Coût en plus du Passage : le début de la première
réponse (en-tête + ce que TCP a déjà reçu avant l'annulation).

Attention côté serveur : si une réponse à une requête `Range` revenait en `200` au lieu de
`206`, `DefaultHttpDataSource` **lirait et jetterait** tous les octets jusqu'à la position
(`bytesToSkip = responseCode == 200 && dataSpec.position != 0 ? dataSpec.position : 0`,
`DHDS` l. 417, puis `skipFully()` l. 457). Le `206` vérifié en #393 est donc indispensable.

### 1.3 Précision du démarrage

- Après le seek, l'extracteur repart d'une trame (mp3) ou d'un échantillon (AAC) **au plus
  tard** à `debut`, et la `SampleQueue` jette les échantillons dont l'horodatage précède
  `debut` quand tous les échantillons sont des points de synchronisation
  (`sampleQueue.setStartTimeUs(pendingResetPositionUs)`, `PMP` l. 1074-1076 ;
  [`SampleQueue.java` l. 690-694](https://github.com/androidx/media/blob/1.11.1/libraries/exoplayer/src/main/java/androidx/media3/exoplayer/source/SampleQueue.java#L690-L694)).
- `audio/mpeg` et l'AAC (hors xHE-AAC) sont déclarés « all samples are sync samples »
  ([`MimeTypes.allSamplesAreSyncSamples()` l. 298-338](https://github.com/androidx/media/blob/1.11.1/libraries/common/src/main/java/androidx/media3/common/MimeTypes.java#L298-L338)) :
  pas de pré-roll ni de discontinuité initiale à décoder (`CMP` l. 353-381).
- Granularité : une trame. mp3 : 1152 échantillons, soit ~26 ms à 44,1 kHz ; AAC : 1024
  échantillons, ~23 ms. (Valeurs des formats, pas de Media3.)
- La position octet ↔ temps d'un mp3 CBR est calculée, pas lue (§3.1) : l'écart éventuel
  vient d'un débit déclaré différent du débit réel, nul sur un vrai CBR.

Conclusion : précision **de l'ordre de la trame** (quelques dizaines de ms), très loin de la
tolérance ±10 s du cadrage.

### 1.4 Précision de l'arrêt

- `ClippingMediaPeriod.updateClipping()` transmet `endUs` au `ProgressiveMediaPeriod`
  (`mediaPeriod.setEndPositionUs(endUs)`, `CMP` l. 126-136), qui le pose sur chaque
  `SampleQueue` (`setReadEndTimeUs`, `PMP` l. 642-647) : aucun échantillon au-delà de `fin`
  n'est rendu, la lecture se termine (`Player.STATE_ENDED`).
- Sinon, `ClippingSampleStream.readData()` émet la fin de flux dès qu'un tampon a
  `timeUs >= endUs` (`CMP` l. 446-453).
- Précision : une trame.

### 1.5 Coût réseau en fin de Passage

- La requête est ouverte (`bytes=X-`) : nginx enverrait tout le reste du fichier si on le
  laissait faire.
- Le chargement avance par paliers de `continueLoadingCheckIntervalBytes` = **1 Mio** par
  défaut
  ([`ProgressiveMediaSource.DEFAULT_LOADING_CHECK_INTERVAL_BYTES`](https://github.com/androidx/media/blob/1.11.1/libraries/exoplayer/src/main/java/androidx/media3/exoplayer/source/ProgressiveMediaSource.java#L321)) ;
  entre deux paliers, le thread de chargement se bloque sur `loadCondition` (`PMP`
  l. 1330-1342).
- Une fois toutes les files arrivées à `fin`, `reevaluateBuffer()` marque le chargement
  terminé (`loadingFinished = true`, `PMP` l. 499-504), donc plus de palier suivant. Le code
  porte un `TODO: b/474538573 - Actually cancel ongoing load` : la connexion n'est pas fermée
  activement en 1.11.1.
- Par ailleurs, `DefaultLoadControl` ne charge pas plus de 50 s d'avance
  ([`DEFAULT_MIN_BUFFER_MS`/`DEFAULT_MAX_BUFFER_MS` = 50 000, `DefaultLoadControl.java` l. 64, 76](https://github.com/androidx/media/blob/1.11.1/libraries/exoplayer/src/main/java/androidx/media3/exoplayer/DefaultLoadControl.java#L64)).

Dépassement attendu au-delà de `fin` : **au plus ~1 Mio** (un palier, plus ce que les
tampons TCP ont déjà reçu), soit ~1 min d'un mp3 à 128 kbit/s. Le reste du fichier n'est pas
téléchargé. `player.stop()`/`release()` en fin de lecture ferme la connexion.

### 1.6 Alternatives écartées

- `seekTo(debut)` + `PlayerMessage` ou écouteur de position à `fin` : même coût réseau, mais
  la barre de progression montre l'émission entière et l'arrêt dépend d'un callback ;
  rien à gagner face au clipping.
- `ClippingMediaSource` construit à la main : équivalent à `ClippingConfiguration`, qui le
  crée via `DefaultMediaSourceFactory`.

## 2. Envoyer la clé d'écoute

### 2.1 En-tête HTTP

`HttpDataSource.Factory.setDefaultRequestProperties(Map)` : les propriétés « will be used for
future requests made by HttpDataSources created by the factory, including instances that
have already been created » ; modifier la `Map` après coup n'a aucun effet, il faut rappeler
la méthode
([`HttpDataSource.java` l. 52-61](https://github.com/androidx/media/blob/1.11.1/libraries/datasource/src/main/java/androidx/media3/datasource/HttpDataSource.java#L52-L61)).

`DefaultHttpDataSource.makeConnection()` pose sur **chaque** connexion, dans cet ordre de
priorité croissante : propriétés par défaut, `setRequestProperty()`, en-têtes du `DataSpec` ;
puis `Range`, `User-Agent` et `Accept-Encoding` (`DHDS` l. 617-635 ; javadoc l. 63-64). Toutes
les requêtes d'une lecture (préparation, Range de seek, Range de `moov`) portent donc
l'en-tête.

Branchement, d'après
[Network stacks](https://developer.android.com/media/media3/exoplayer/network-stacks#configuring-exoplayer) :

```kotlin
val http = DefaultHttpDataSource.Factory()
    .setDefaultRequestProperties(mapOf("X-Cle-Ecoute" to cle))  // nom d'en-tête à fixer
val player = ExoPlayer.Builder(context)
    .setMediaSourceFactory(
        DefaultMediaSourceFactory(context)
            .setDataSourceFactory(DefaultDataSource.Factory(context, http)))
    .build()
```

`OkHttpDataSource.Factory` offre la même méthode
([`OkHttpDataSource.java` l. 99](https://github.com/androidx/media/blob/1.11.1/libraries/datasource_okhttp/src/main/java/androidx/media3/datasource/okhttp/OkHttpDataSource.java#L99)).
Rien n'impose OkHttp ici : un seul hôte HTTPS, de l'audio progressif.

Autres en-têtes envoyés par Media3, à laisser passer par nginx :

- `Icy-MetaData: 1` sur toutes les requêtes progressives (`PMP` l. 118, 1377 ;
  [`IcyHeaders.java` l. 35-36](https://github.com/androidx/media/blob/1.11.1/libraries/extractor/src/main/java/androidx/media3/extractor/metadata/icy/IcyHeaders.java#L35-L36)),
  sans effet sur un serveur de fichiers ;
- `If-Range: <ETag>` sur les requêtes suivantes si la première réponse portait un ETag fort
  (`PMP` l. 1376-1384) : nginx sert un ETag fort pour un fichier statique, une `Range`
  reste alors en `206` tant que le fichier ne change pas.

Erreur de clé : une réponse non-2xx (401/403 de nginx) lève
`HttpDataSource.InvalidResponseCodeException` (`DHDS` l. 379-403), remontée en
`PlaybackException` (`ERROR_CODE_IO_BAD_HTTP_STATUS`) via `Player.Listener.onPlayerError`.
C'est le point où l'app peut proposer de rescanner le QR code.

### 2.2 `?cle=`

L'URI du `MediaItem` est réutilisée telle quelle pour chaque requête
(`new DataSpec.Builder().setUri(uri).setPosition(position)`, `PMP` l. 1385-1394) : la query
string part donc aussi dans toutes les Range. Ça marche, mais la clé se retrouve dans l'URL
(journaux d'accès nginx et DSM, `EventLogger`, notifications de session média qui
afficheraient l'URI). L'en-tête l'évite. Choix produit, pas une contrainte Media3.

## 3. Seek via Range

### 3.1 mp3 CBR

- Depuis **1.9.0**, `Mp3Extractor` suppose le CBR **par défaut** quand aucun en-tête de seek
  n'est trouvé (`RN` l. 1081-1089) ; depuis **1.3.0**, un en-tête `Info` (l'équivalent CBR
  de `Xing`) donne aussi un seek CBR (`RN` l. 3267-3270). Dans le code 1.11.1 :
  `computeSeeker()` retombe sur `getConstantBitrateSeeker(input)` sans métadonnée
  (`MP3X` l. 510-527), et un en-tête `Info` passe par `getConstantBitrateSeeker(...)`
  (`MP3X` l. 612-622).
- **Aucun flag à poser** pour nos 134 fichiers CBR : `FLAG_ENABLE_CONSTANT_BITRATE_SEEKING`
  ne sert plus qu'à retomber en CBR quand un `Xing`/`VBRI` est présent mais non seekable
  (`MP3X` l. 549-578), et `_ALWAYS` aux flux de longueur inconnue (`MP3X` l. 94-104).
  `FLAG_ENABLE_INDEX_SEEKING` (scan complet du fichier) est à éviter : « doesn't scale well
  to large MP3 files » ([Troubleshooting](https://developer.android.com/media/media3/exoplayer/troubleshooting#why-is-seeking-inaccurate-in-some-mp3-files)).
- Écart de documentation : les pages
  [Progressive](https://developer.android.com/media/media3/exoplayer/progressive) et
  [Customization](https://developer.android.com/media/media3/exoplayer/customization)
  décrivent encore le seek CBR comme désactivé par défaut ; le code et les release notes
  1.9.0 font foi.
- Calcul : `octet = premièreTrame + temps × débit / 8`, aligné sur la trame précédente
  ([`ConstantBitrateSeekMap.getFramePositionForTimeUs()` l. 212-221](https://github.com/androidx/media/blob/1.11.1/libraries/extractor/src/main/java/androidx/media3/extractor/ConstantBitrateSeekMap.java#L212-L221)).
  Le calcul utilise la longueur du fichier (`input.getLength()`, `MP3X` l. 639-648), connue
  par le `Content-Length` de la première réponse : nginx la fournit.
- Un seek = **une** requête `Range` directe, quel que soit l'endroit du fichier.

### 3.2 m4a avec `moov` en fin de fichier

- `Mp4Extractor` lit les boîtes dans l'ordre. Rencontrant un `mdat` de plus de 256 Kio avant
  le `moov`, il ne le lit pas mais **demande un seek** à la fin du `mdat`
  (`RELOAD_MINIMUM_SEEK_DISTANCE = 256 * 1024`, `MP4X` l. 232 ; `readAtomPayload()`
  l. 559-570 → `RESULT_SEEK`). `ProgressiveMediaPeriod` rouvre alors la source à cette
  position (`PMP` l. 1346-1348 et boucle `load()`) : **une requête `Range` vers la fin du
  fichier**, lecture du `moov` (table d'échantillons exacte), puis le seek du Passage
  (§1.2) relance une `Range` à l'octet de `debut`.
- Le lecteur lit donc bien la fin du fichier d'abord, mais par Range, **sans télécharger le
  `mdat`**. Surcoût face à un fichier faststart : **un aller-retour HTTP** de plus. Le
  `moov` lui-même (table des échantillons, de l'ordre de quelques centaines de Kio pour une
  heure d'AAC) est lu dans les deux cas.
- Le seek dans un m4a utilise la table exacte du `moov` : la précision ne dépend pas de la
  position du `moov`.
- **Réécrire les 4 m4a en faststart n'est pas nécessaire.** C'est un confort (un aller-retour
  de moins au démarrage), à faire seulement si c'est gratuit : par exemple
  `ffmpeg -i in.m4a -c copy -movflags +faststart out.m4a` (option ffmpeg, hors Media3). Une
  réécriture change le fichier, donc son ETag, sans effet sur Media3 (pas de cache).

## 4. Pas de cache client

- Le cache disque de Media3 n'existe que si l'app l'installe : `SimpleCache` +
  `CacheDataSource.Factory` injectés dans `DefaultMediaSourceFactory`
  ([Network stacks, « Caching media »](https://developer.android.com/media/media3/exoplayer/network-stacks#caching-media)).
  Sans eux, `DefaultMediaSourceFactory(context)` utilise un `DefaultDataSource.Factory`
  simple
  ([`DefaultMediaSourceFactory.java` l. 138](https://github.com/androidx/media/blob/1.11.1/libraries/exoplayer/src/main/java/androidx/media3/exoplayer/source/DefaultMediaSourceFactory.java#L138)).
  Les `DataSpec` progressifs portent seulement des drapeaux de cache sans effet sans
  `CacheDataSource` (`PMP` l. 1389-1392).
- Couche HTTP : `DefaultHttpDataSource` s'appuie sur `HttpURLConnection` ; il ne met en
  cache que si l'app a installé un `HttpResponseCache` (comportement Android, pas Media3).
  Avec OkHttp, il faut ne pas donner de `Cache` à l'`OkHttpClient` ; la factory accepte
  aussi `setCacheControl(CacheControl)`
  ([`OkHttpDataSource.java` l. 125-131](https://github.com/androidx/media/blob/1.11.1/libraries/datasource_okhttp/src/main/java/androidx/media3/datasource/okhttp/OkHttpDataSource.java#L125-L131)).
- Reste le tampon mémoire de lecture (`DefaultLoadControl`, 50 s), vidé au `release()`.
- Côté serveur, `Cache-Control: no-store` dans nginx protège en plus contre un cache HTTP
  installé un jour par l'app ou un intermédiaire (décision #394).

## 5. Ce qui en découle pour la spec

1. lmelp-mobile lit un Passage avec `MediaItem` + `ClippingConfiguration(debut, fin)` en
   ms, via `DefaultMediaSourceFactory` ; la barre de lecture affiche `0 … fin - debut`.
2. La clé part en en-tête par `DefaultHttpDataSource.Factory.setDefaultRequestProperties`
   (nom d'en-tête à fixer avec nginx), `?cle=` reste possible. Un 401/403 arrive en
   `onPlayerError` : proposer de rescanner le QR code.
3. Aucun flag d'extracteur : mp3 CBR seek en CBR par défaut (Media3 ≥ 1.9.0) ; m4a
   seek par la table du `moov`. Version plancher : **Media3 1.9.0**.
4. Les 4 m4a avec `moov` en fin restent tels quels (un aller-retour de plus au démarrage).
5. Pas de `CacheDataSource`, pas de `HttpResponseCache`/cache OkHttp ; `Cache-Control:
   no-store` côté nginx.
6. nginx doit répondre `206` à toute `Range` (sinon Media3 télécharge jusqu'à la position)
   et accepter `Icy-MetaData` et `If-Range`.
7. Coût réseau d'un Passage : en-tête du fichier + Passage + au plus ~1 Mio au-delà de `fin`.

## Non vérifié

- Aucun essai sur appareil : tout vient du code et de la documentation. Un test sur un vrai
  téléphone (journal `EventLogger` des requêtes, mesure de l'écart réel à `debut`/`fin`) est
  à prévoir dans l'implémentation.
- Taille réelle des `moov` de nos m4a et coût de la première réponse avant annulation : non
  mesurés.
- Comportement de 1.12.0 (pas encore stable) non relu ; le `TODO b/474538573` peut y avoir
  évolué.
