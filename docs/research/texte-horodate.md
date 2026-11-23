# Recherche : obtenir un texte horodaté des épisodes

Ticket : #388 (carte #387, « Écouter les critiques parler d'un livre »). Date : 23/11/2026.

Question : comment obtenir, pour chacun des 246 épisodes (~42-48 min d'audio français),
une transcription horodatée (par segment, idéalement par mot) qui situe un Passage à
±10 s ?

Ce document rassemble des faits. Il ne tranche pas.

## En bref

1. **La chaîne PGX calcule déjà les horodatages et les jette.** `whisper-cli`
   (whisper.cpp) découpe l'audio en segments horodatés ; l'option `--output-txt` écrit
   seulement le texte de chaque segment, une ligne par segment. Ajouter `-oj`
   (`--output-json`) ou `-osrt` à l'appel produit les mêmes segments avec leurs
   horodatages, sans coût GPU supplémentaire. Le dépôt `whisper_docker` qui fait cet
   appel n'est pas public : c'est là qu'il faut ajouter l'option.
2. **Des segments suffisent pour ±10 s.** Sur les 19 transcriptions déjà faites par
   PGX, un segment dure en moyenne ~2 s (2 895 s pour 1 509 lignes). Les mots horodatés
   ne sont pas nécessaires pour cette précision.
3. **L'archive doit être retranscrite.** 223 des 242 transcriptions en base sont d'un
   seul tenant (ancienne chaîne Hugging Face de lmelp) : aucun découpage exploitable.
   Retranscrire sur PGX coûte environ 4-5 min par épisode (mesuré), soit **~18-20 h de
   PGX pour les 246 épisodes**.
4. **L'alignement forcé du texte existant est possible mais n'apporte rien ici.**
   Il garde le texte actuel (déjà utilisé par les avis critiques), mais demande une
   nouvelle pile logicielle sur PGX (arm64), alors que la retranscription réutilise la
   chaîne qui marche déjà.
5. **WhisperX et faster-whisper sont peu adaptés à PGX** (Linux aarch64) : WhisperX
   installe PyTorch CPU sur aarch64, et CTranslate2 doit y être compilé depuis les
   sources pour utiliser CUDA.
6. **Format à stocker** : une liste de segments `[début_ms, fin_ms, texte]`, ~100-150 Ko
   par épisode en JSON, ~30-40 Mo pour l'archive.

## 1. Ce que fait la chaîne PGX aujourd'hui

### Côté lmelp (code local)

- `pgx_service.requeue_pgx_audio()` lance
  `docker exec '<PGX_WHISPER_CONTAINER>' python3 -m whisper_docker.queue_manager enqueue '<chemin>'`
  (`src/back_office_lmelp/services/pgx_service.py`). Le conteneur s'appelle
  `whisper-arm64` par défaut (`settings.pgx_whisper_container`), ses audios sont sous
  `/data/audios` (`settings.pgx_container_audio_root`).
- En temps normal, aucun `enqueue` : l'écriture du `.mp3` dans
  `PGX_REMOTE_AUDIO_ROOT/<année>/` crée le job (watcher `close_write`,
  `docs/dev/pgx-transcription.md`, section « Relance d'un mp3 orphelin »).
- Le runner attend puis rapatrie **un seul fichier** :
  `<PGX_REMOTE_TRANSCRIPTION_ROOT>/<année>/<stem>.txt`
  (`src/back_office_lmelp/utils/pgx_transcription_runner.py`), copié à côté de l'audio
  local et écrit tel quel dans `episodes.transcription`.
- Le binaire appelé par `whisper_docker` est `whisper-cli`
  (`docs/claude/memory/261101-1754-issue320-relance-mp3-orphelin-pgx.md` : plantage de
  `whisper-cli`, fonction `transcribe_audio()` de `scripts/process_audio.py`).
- Durée mesurée : « attente (~3-4 min chacun) » sur 2 épisodes
  (`docs/dev/pgx-transcription.md`), « transcription en 4 min 46 » pour l'épisode du
  01/11/26 (mémoire #320). Soit **~10× le temps réel**.

### Le dépôt `whisper_docker`

- Introuvable sur GitHub : `gh repo list castorfou` (60 dépôts) et
  `gh search code whisper_docker --owner castorfou` ne renvoient aucun dépôt
  `whisper_docker` ou `whisper-docker`, ni public ni privé visible par ce compte. Il vit
  sans doute seulement sur PGX. **Ses options exactes d'appel de `whisper-cli` n'ont donc
  pas pu être lues** ; à vérifier sur PGX (`scripts/process_audio.py`).
- Son ancêtre est public : `castorfou/lmelp`, `scripts/whisper.cpp/whisper.sh`, qui
  lance `ghcr.io/ggml-org/whisper.cpp:main-cuda` avec
  `--model /models/ggml-large-v3.bin --language fr --output-txt --output-file …`
  ([source](https://github.com/castorfou/lmelp/blob/main/scripts/whisper.cpp/whisper.sh)).
  Hypothèse raisonnable : `whisper_docker` fait le même appel (large-v3, `--output-txt`).

### Ce que contient la base (MongoDB local, 23/11/2026)

| Transcriptions | Nombre | Lignes en moyenne | Durée moyenne (`duree`) | Mots en moyenne |
|---|---|---|---|---|
| découpées en lignes (PGX, whisper.cpp) | 19 (2016-2026) | 1 509 | 2 895 s | 9 012 |
| d'un seul tenant | 223 (1958-2025) | 1 | 2 514 s | 7 833 |

Les 223 transcriptions d'un seul tenant viennent de l'ancienne chaîne de lmelp :
`extract_whisper()` / `extract_whisper_long()` (`nbs/whisper.py`), pipeline
`transformers` avec `openai/whisper-large-v3-turbo`, morceaux de 30 s, texte concaténé
([source](https://github.com/castorfou/lmelp/blob/main/nbs/whisper.py)). Elles n'ont
gardé aucun horodatage.

## 2. Ce que sait produire `whisper-cli` (whisper.cpp)

Source : `examples/cli/cli.cpp` et `README.md` de
[ggml-org/whisper.cpp](https://github.com/ggml-org/whisper.cpp) (dernière version
v1.9.6).

- `-otxt` écrit `whisper_full_get_segment_text()` de chaque segment suivi d'un saut de
  ligne, **sans** ses bornes `t0`/`t1` (`output_txt()`, cli.cpp). Les segments et leurs
  horodatages sont calculés dans tous les cas ; seul l'écrivain change.
- Sorties disponibles, cumulables dans le même appel : `-otxt`, `-ovtt`, `-osrt`,
  `-olrc`, `-ocsv`, `-oj` (`--output-json`), `-ojf` (`--output-json-full`).
- JSON (`-oj`) : par segment, `timestamps.from/to` (chaîne `HH:MM:SS,mmm`) et
  `offsets.from/to` (millisecondes), plus `text` (`times_o`, cli.cpp).
- JSON complet (`-ojf`) : ajoute par segment la liste des `tokens`, chacun avec son
  texte, ses `offsets`, `id`, probabilité `p` et `t_dtw`. `-ojf` active
  `token_timestamps` (`wparams.token_timestamps = params.output_wts ||
  params.output_jsn_full || params.max_len > 0`).
- Mots horodatés : section « Word-level timestamp (experimental) » du README,
  `-ml 1` (`--max-len 1`) produit un segment par mot ; `-sow` coupe sur les mots plutôt
  que sur les jetons.
- Horodatage par jeton plus fin : `-dtw large.v3` (DTW sur les têtes d'attention,
  préréglages jusqu'à `large.v3.turbo`), marqué `[EXPERIMENTAL]` dans `whisper.h`.
- VAD Silero intégrée : `--vad -vm <modèle>` (README, section « Voice Activity
  Detection »). Utile pour éviter des segments qui débordent sur les silences ou la
  musique.

**Pour activer les segments horodatés** : ajouter `-oj` (ou `-osrt`) à l'appel de
`whisper-cli` dans `whisper_docker`, en gardant `-otxt` pour ne rien changer au `.txt`
que lmelp rapatrie déjà. Le fichier produit (`<stem>.json` à côté du `.txt`) serait
rapatrié par un second `scp`.

## 3. Alternatives

### 3.1 openai/whisper (référence)

- `transcribe(..., word_timestamps=True)` ajoute les mots horodatés par DTW sur
  l'attention croisée (`whisper/timing.py`, `add_word_timestamps`) ; sorties
  `txt, vtt, srt, tsv, json, jsonl` (`--output_format`, `whisper/transcribe.py`)
  ([source](https://github.com/openai/whisper)).
- Plus lent que whisper.cpp : 2 min 23 s contre 1 min 05 s pour 13 min d'audio
  (large-v2, fp16, beam 5, RTX 3070 Ti), tableau du README de faster-whisper
  ([source](https://github.com/SYSTRAN/faster-whisper#benchmark)).

### 3.2 faster-whisper

- Même modèle via CTranslate2 ; `word_timestamps=True`, `vad_filter=True`, et
  `BatchedInferencePipeline` (README).
- Banc d'essai du README (13 min, large-v2, RTX 3070 Ti) : 1 min 03 s fp16, **17 s avec
  `batch_size=8`**, soit ~45× le temps réel.
  ([source](https://github.com/SYSTRAN/faster-whisper))
- **Limite PGX** : PGX tourne sur arm64 (conteneur `whisper-arm64`). Les roues
  CTranslate2 existent pour Linux AArch64
  ([doc d'installation](https://github.com/OpenNMT/CTranslate2/blob/master/docs/installation.md)),
  mais l'issue
  [OpenNMT/CTranslate2#2088](https://github.com/OpenNMT/CTranslate2/issues/2088)
  montre que CUDA sur aarch64 (Jetson Orin, **NVIDIA GB10**) passe par une compilation
  depuis les sources (« built from source »), la roue PyPI n'étant utilisée qu'en CPU
  sur aarch64. La même issue signale une fuite de mémoire hôte de ~6,8 Ko par appel sur
  aarch64 + CUDA (négligeable pour 246 appels, gênant pour un service résident).

### 3.3 WhisperX

- faster-whisper par lots + alignement forcé wav2vec2 pour des mots horodatés précis ;
  « 70x realtime with large-v2 », « <8GB gpu memory »
  ([README](https://github.com/m-bain/whisperX), papier Bain et al., Interspeech 2023,
  [arXiv:2303.00747](https://arxiv.org/abs/2303.00747)). Version v3.8.6.
- Modèle d'alignement français par défaut : `VOXPOPULI_ASR_BASE_10K_FR`
  (torchaudio), ou son équivalent Hugging Face `facebook/wav2vec2-base-10k-voxpopuli-fr`
  quand torchaudio manque (`whisperx/alignment.py`).
- Limites (README) : les mots sans caractère connu du modèle d'alignement (nombres
  écrits en chiffres, « 2014. ») restent **sans horodatage** ; la parole superposée est
  mal gérée (fréquente dans un débat de critiques).
- **Limite PGX** : `pyproject.toml` de WhisperX prend `torch` sur l'index
  `pytorch-cpu` pour toute plate-forme non x86_64 hors macOS, exclut `torchcodec` et
  `triton` sur Linux aarch64. Une installation standard sur PGX tournerait donc en CPU ;
  il faudrait une image PyTorch CUDA aarch64 et CTranslate2 compilé (voir 3.2).
- WhisperX sait aussi aligner seul : `whisperx.align(segments, model, metadata, audio,
  device)` prend des segments **déjà horodatés** et les affine au mot. Il ne sait pas
  aligner un texte brut sans horodatage d'une heure.

### 3.4 Alignement forcé du texte existant

Intérêt : garder exactement le texte en base, sur lequel les avis critiques ont été
générés. Mais 223 de ces textes sont d'un seul tenant, sur ~42 min.

- **ctc-forced-aligner** ([MahmoudAshraf97/ctc-forced-aligner](https://github.com/MahmoudAshraf97/ctc-forced-aligner)) :
  modèles CTC Hugging Face (Wav2Vec2, HuBERT, MMS, 1 130 langues dont le français),
  granularité phrase, mot ou caractère, GPU, sortie JSON, « 5X less memory » que l'API
  torchaudio. Conçu pour aligner un long texte sur un long audio.
- **torchaudio `forced_align`** : TorchAudio est en maintenance depuis la 2.9 (« APIs
  deprecated in version 2.8 have been removed in 2.9 »,
  [doc](https://docs.pytorch.org/audio/main/torchaudio.html)) ; la page de
  `forced_align` ne porte pas d'avertissement de dépréciation, mais pas de roue
  torchaudio pour Linux aarch64 (commentaire de `whisperx/alignment.py`). À éviter sur
  PGX.
- **aeneas** ([readbeyond/aeneas](https://github.com/readbeyond/aeneas)) : synthèse
  vocale eSpeak + DTW sur MFCC, français (« FRA ») confirmé, granularité libre,
  « robust against misspelled/mispronounced words ». Testé sous Python 2.7 et 3.5,
  dernier commit le 13/05/2020 : non maintenu. Le README prévient qu'il n'a pas été
  conçu pour l'alignement au mot.
- **Montreal Forced Aligner** : modèles acoustiques français `french_mfa` v2.0.0,
  v2.0.0a et v3.0.0, CC BY 4.0
  ([liste](https://mfa-models.readthedocs.io/en/latest/acoustic/French/index.html)) ;
  basé sur Kaldi, pensé pour des corpus d'énoncés courts transcrits avec un dictionnaire
  de prononciation ([guide](https://montreal-forced-aligner.readthedocs.io/en/latest/user_guide/index.html)).
  Pour un fichier de 42 min d'un seul tenant, il faudrait d'abord le découper
  (inférence, la doc consultée n'en parle pas). Les noms propres hors dictionnaire
  (auteurs, titres) demandent une génération de prononciations (G2P).

Inconvénient commun : le texte existant contient des erreurs Whisper (noms propres,
homophones, voir `docs/claude/memory/250914-1921-babelio-integration-complete.md`).
L'aligneur doit les « traverser » ; les aligneurs CTC le font en insérant des jetons
`<star>`, au prix de zones mal calées.

### 3.5 Comparaison

| Voie | Granularité | Texte obtenu | Travail sur PGX | Temps pour 246 épisodes |
|---|---|---|---|---|
| whisper.cpp + `-oj` (chaîne actuelle) | segment (~2 s), mot avec `-ml 1`/`-ojf` | nouveau (large-v3) | une option dans `whisper_docker` | ~18-20 h (mesuré : 4-5 min/épisode) |
| faster-whisper par lots | segment, mot | nouveau | nouvelle image, CTranslate2 compilé pour aarch64 | ~4 h si ~45× (banc RTX 3070 Ti, non mesuré sur PGX) |
| WhisperX | mot (wav2vec2 fr) | nouveau | idem + PyTorch CUDA aarch64 | comparable à faster-whisper + alignement |
| Alignement CTC du texte existant | mot, phrase | inchangé | nouvelle image PyTorch CUDA aarch64 | non mesuré |
| aeneas / MFA | phrase, mot | inchangé | pile ancienne (aeneas) ou Kaldi (MFA) | non mesuré |

## 4. Volume des données

Estimations à partir des moyennes PGX (1 509 segments, 9 012 mots, 52 600 caractères
par épisode) :

| Format | Par épisode | Archive (246) |
|---|---|---|
| texte seul (actuel) | ~50 Ko | ~12 Mo |
| segments `[début_ms, fin_ms, texte]` en JSON | ~100-150 Ko | ~25-40 Mo |
| `-oj` brut de whisper.cpp (deux horodatages par segment, clés verbeuses) | ~250 Ko | ~60 Mo |
| mots `[début_ms, fin_ms, mot]` | ~250-350 Ko | ~60-90 Mo |
| `-ojf` brut (chaque jeton avec `p`, `id`, `t_dtw`) | ~1-2 Mo | ~250-500 Mo |

Un document MongoDB est limité à 16 Mo : même les mots tiennent dans le document
épisode, mais une collection à part (un document par épisode) évite de charger
l'horodatage à chaque lecture d'épisode.

## 5. Format recommandé à stocker

- **Segments**, pas mots : ~2 s par segment donne 5× la marge des ±10 s, et le Passage
  s'arrondit de toute façon vers plus large.
- Millisecondes entières depuis le début du fichier audio servi (`audio_rel_filename`) :
  ce sont les `offsets` de whisper.cpp, sans conversion de chaîne.
- Forme compacte, par épisode :

```json
{
  "episode_id": "…",
  "source": "whisper.cpp large-v3",
  "audio_rel_filename": "2026/xxx.mp3",
  "segments": [[0, 2140, "France Inter, le masque et la plume."], [2140, 5320, "…"]]
}
```

- Garder le nom du modèle et du fichier audio : l'horodatage ne vaut que pour cet audio
  précis (un `.m4a` converti, une autre version du fichier décalerait tout).
- Le `.txt` actuel se reconstruit en joignant les textes des segments par `\n` : un seul
  passage PGX peut alimenter les deux.
- SRT/VTT sont des formats d'affichage (horodatage en chaîne) : faciles à générer depuis
  ces segments si un lecteur en a besoin, inutiles à stocker.

## Questions ouvertes (hors faits)

- Lire `scripts/process_audio.py` de `whisper_docker` sur PGX pour confirmer le modèle
  et les options réellement passés à `whisper-cli`.
- Retranscrire l'archive change le texte des 223 anciens épisodes : faut-il remplacer
  `episodes.transcription`, ou stocker le texte horodaté à part et garder l'ancien texte
  (sur lequel les résumés ont été générés) ?
- Les vieux enregistrements (dès 1958, pap) : qualité audio et dérive des segments à
  vérifier sur quelques épisodes.
