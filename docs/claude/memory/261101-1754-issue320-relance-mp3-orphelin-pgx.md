# Issue #320 : relance d'un mp3 orphelin sur PGX

## Symptôme

Épisode du 01/11/26 en échec dans lmelp : `Timeout: transcription non disponible sur PGX
après 1800.0s`. Un renvoi manuel à 16:56 n'a rien changé.

## Cause (constatée sur PGX, en lecture seule)

1. Conversion m4a → mp3 réussie (Job 31, mp3 complet).
2. `whisper-cli` plante en 0,4 s à l'initialisation : `CUDA error: out of memory`
   (`cudaSetDeviceFlags`). Le conteneur `qwen38-flash` partage le GPU avec une réservation
   de 103 Gio sur 121. C'est un suspect probable, pas une cause prouvée : les deux ont déjà
   cohabité le 04/10. Le test bout en bout a réussi avec `qwen38-flash` arrêté.
3. `transcribe_audio()` de whisper-docker (`scripts/process_audio.py`) avale
   `CalledProcessError` : le job passe `completed`, log « Transcription terminée », sans
   `.txt`. Le symptôme côté lmelp est donc un timeout, pas une erreur.
4. Renvoi du m4a : `convert_m4a_to_mp3()` voit le mp3 existant et sort, aucun `close_write`
   sur le mp3, donc aucun job. **Tout renvoi est un no-op tant que le mp3 reste sur PGX.**

## Correctif (back-office-lmelp)

Avant l'envoi, `PgxTranscriptionRunner._has_orphan_mp3()` détecte audio non-mp3, mp3 présent
sur PGX et `.txt` absent. Dans ce cas, `pgx_service.requeue_pgx_audio()` lance
`docker exec <conteneur> python3 -m whisper_docker.queue_manager enqueue <chemin>` au lieu
de renvoyer l'audio. La boucle du runner, l'attente et le rapatriement ne changent pas.

- `src/back_office_lmelp/services/pgx_service.py` : `remote_file_exists()`,
  `requeue_pgx_audio()`. « déjà en queue » dans la sortie n'est pas une erreur.
- `src/back_office_lmelp/utils/pgx_transcription_runner.py` : `_has_orphan_mp3()`.
- `src/back_office_lmelp/settings.py` : `PGX_WHISPER_CONTAINER` (défaut `whisper-arm64`),
  `PGX_CONTAINER_AUDIO_ROOT` (défaut `/data/audios`).

## Points non évidents

- `enqueue` et non `retry <job_id>` : `retry` vise les jobs `failed`, or le job planté est
  `completed` et `list-failed` ne le voit pas.
- Le chemin passé à `enqueue` est celui du conteneur (`/data/audios/...`), pas celui de
  l'hôte PGX (`PGX_REMOTE_AUDIO_ROOT`).
- L'utilisateur SSH doit pouvoir lancer `docker` sur PGX.
- Audio déjà en `.mp3` exclu : son renvoi déclenche `close_write`, donc un job.
- Le shell distant de PGX est zsh : `==` dans un `echo` non quoté et `--include=*` y
  échouent lors d'un diagnostic manuel par ssh.
- Le Mongo local du devcontainer peut être en retard sur la prod : pour un test bout en bout
  d'un épisode récent, il faut insérer l'épisode à la main (audio local inutile en cas de
  relance).

## Test bout en bout

Exécuté avec l'utilisateur le 01/11/26, GPU libéré : log `mp3 déjà sur PGX sans
transcription, relance…`, transcription en 4 min 46, 50 977 caractères écrits en base.

## Reste à faire hors de ce dépôt

Dans whisper-docker : ne plus avaler `CalledProcessError` dans `transcribe_audio()` (le job
passerait `failed`, avec les retries de `mark_failed`), et décider du partage du GPU avec
`qwen38-flash`. Tant que ce n'est pas fait, un plantage whisper reste vu par lmelp comme un
timeout, puis se rattrape au déclenchement suivant grâce à la relance.
