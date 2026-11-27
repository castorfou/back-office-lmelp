# Relancer la transcription d'un épisode (boucle Whisper)

But : remplacer la transcription d'un épisode que Whisper a gâchée en partant en boucle
(la même phrase répétée chaque seconde jusqu'à la fin de l'audio), puis régénérer son
résumé et ses avis.

Symptôme typique : dans *Génération d'avis critiques*, la section 2 (coups de cœur) est
vide ou sans notes, et la page *Émission* ne rapproche aucun avis de ces livres. La fin
de la transcription montre une ligne répétée des centaines de fois.

La boucle n'est pas due à une coupure de PGX : le modèle `large-v3` se sert du texte déjà
produit comme contexte et peut s'y enfermer. Relancer à l'identique redonne souvent la
même boucle. On relance donc le fichier **à la main avec `-mc 0`** (aucun contexte
texte), puis on laisse le pipeline lmelp rapatrier le résultat.

Pourquoi il ne suffit pas de relancer depuis l'appli : le pipeline réutilise d'abord
une transcription déjà présente, à côté de l'audio sur le NAS ou dans le répertoire
`transcriptions` de PGX. Il faut neutraliser ces deux copies et vider le champ
`transcription` en base pour que l'épisode redevienne « en attente ».

---

## 0. Repères de l'épisode

Remplir une fois, les commandes suivantes s'en servent.

| Variable | Où la trouver | Épisode du 28 juin 2015 |
|---|---|---|
| `EPISODE_ID` | `_id` de l'épisode en base | `6b061fd73a756aaf913fe936` |
| `YEAR` | année de diffusion | `2015` |
| `STEM` | `audio_rel_filename` sans dossier ni extension | `14007-28.06.2015-ITEMA_20771833-2015F4007S0179-27` |

```bash
EPISODE_ID=6b061fd73a756aaf913fe936
YEAR=2015
STEM=14007-28.06.2015-ITEMA_20771833-2015F4007S0179-27
```

Repères machines :

| Élément | Valeur |
|---|---|
| PGX | `f279814@192.168.1.73`, conteneur Whisper `whisper-arm64` |
| Données Whisper sur PGX | `~/git/whisper-docker/docker/data/{audios,transcriptions,logs}/$YEAR/` |
| Mêmes données vues du conteneur | `/data/{audios,transcriptions}/$YEAR/` |
| Backend sur le NAS | conteneur `lmelp-backoffice-backend`, audios sous `/app/audios/$YEAR/` |
| MongoDB de prod | `mongodb://192.168.50.207:27018`, base `masque_et_la_plume` |

---

## 1. Confirmer la boucle — sur PGX

```bash
cd ~/git/whisper-docker/docker/data
tail -3 transcriptions/$YEAR/$STEM.txt
grep -n -m1 -B3 "$(tail -1 transcriptions/$YEAR/$STEM.txt)" logs/$YEAR/$STEM.log
```

La première commande montre la phrase répétée. La seconde donne l'horodatage audio où
la boucle démarre (00:34:14 pour le 28 juin 2015). Le log se termine normalement
(`total time = …`, `Transcription completed`) : Whisper n'a pas été interrompu.

Vérifier aussi que l'audio converti est toujours là, sinon voir la note en fin de page :

```bash
ls -l audios/$YEAR/$STEM.mp3
```

## 2. Mettre la transcription en boucle de côté — sur PGX

```bash
cd ~/git/whisper-docker/docker/data
mv transcriptions/$YEAR/$STEM.txt transcriptions/$YEAR/$STEM.txt.boucle
```

Le fichier est conservé pour comparaison ; le répertoire est ouvert en écriture, `sudo`
n'est pas nécessaire.

## 3. Retranscrire sans contexte texte — sur PGX

```bash
docker exec whisper-arm64 /app/build/bin/whisper-cli \
  -f /data/audios/$YEAR/$STEM.mp3 \
  -m /data/models/ggml-large-v3.bin \
  -l fr -mc 0 \
  -otxt -of /data/transcriptions/$YEAR/$STEM \
  > /tmp/$STEM.retranscription.log 2>&1
```

Compter environ 7 minutes pour une émission d'une heure. Ensuite :

```bash
cd ~/git/whisper-docker/docker/data
wc -c transcriptions/$YEAR/$STEM.txt transcriptions/$YEAR/$STEM.txt.boucle
sort transcriptions/$YEAR/$STEM.txt | uniq -c | sort -rn | head -3
tail -20 transcriptions/$YEAR/$STEM.txt
```

Attendu : aucune ligne répétée des dizaines de fois, et une fin de texte qui correspond
à la fin de l'émission (coups de cœur, générique). Si la boucle revient, relancer
l'étape 3 en ajoutant `-sns` (suppression des tokens non vocaux) ou `-et 2.8`.

## 4. Neutraliser la copie locale — sur le NAS

Le pipeline lit en priorité un `.txt` posé à côté de l'audio dans le volume du backend.

```bash
docker exec lmelp-backoffice-backend sh -c "ls -l /app/audios/$YEAR/$STEM.*"
```

S'il y a un `$STEM.txt` :

```bash
docker exec lmelp-backoffice-backend \
  mv /app/audios/$YEAR/$STEM.txt /app/audios/$YEAR/$STEM.txt.boucle
```

## 5. Remettre l'épisode en attente de transcription — base de prod

Depuis une machine du réseau maison :

```bash
mongosh "mongodb://192.168.50.207:27018/masque_et_la_plume" --quiet --eval "
  db.episodes.updateOne(
    { _id: ObjectId('$EPISODE_ID') },
    { \$unset: { transcription: '' } }
  )"
```

Attendu : `matchedCount: 1, modifiedCount: 1`. L'ancienne transcription reste lisible
dans `$STEM.txt.boucle` sur PGX.

## 6. Rapatrier la nouvelle transcription — dans l'appli

1. Ouvrir **Transcription PGX** (`/transcription-pgx`), cliquer **🔄 Rafraîchir le
   statut** : la checklist est verte et l'épisode figure dans la liste en attente.
2. Cliquer **▶️ Lancer la transcription des épisodes en attente**.
3. Le journal affiche `transcription déjà présente sur PGX, rapatriement…` : le fichier
   de l'étape 3 est récupéré en quelques secondes, sans renvoi d'audio ni recalcul.

Si le journal affiche plutôt `mp3 déjà sur PGX sans transcription, relance…`, le
`.txt` de l'étape 3 n'est pas au bon endroit : le pipeline relance alors Whisper avec ses
options habituelles, et la boucle peut revenir. Vérifier le chemin de l'étape 3.

## 7. Régénérer le résumé — dans l'appli

1. **Génération d'avis critiques** → choisir l'épisode → **🔄 Régénérer**.
2. Vérifier que la section 2 (coups de cœur) a des lignes, avec critique, note et
   commentaire.

Enregistrer un nouveau résumé vide le cache Livres et Auteurs de l'épisode.

## 8. Revalider les livres et ré-extraire les avis — dans l'appli

1. **Livres et Auteurs** → l'épisode : refaire la validation Babelio, puis mettre les
   livres en base.
2. **Émissions** → l'émission du jour → **🔄 Ré-extraire** les avis.
3. Vérifier que les coups de cœur apparaissent, rapprochés de leurs livres, avec leur
   note.

---

## Note : l'audio converti n'est plus sur PGX

Si `audios/$YEAR/$STEM.mp3` manque à l'étape 1, sauter les étapes 2 et 3 et faire les
étapes 4 à 8 : le pipeline renvoie l'audio et le fait transcrire avec les options
habituelles du service. Si la boucle revient, mettre de côté le nouveau `.txt` (étape 2)
une fois l'audio arrivé sur PGX, puis reprendre à l'étape 3.
