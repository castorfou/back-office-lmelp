# Émissions anciennes - lmelp

## Vue d'ensemble

[lmelp-pap](https://github.com/castorfou/lmelp-pap) retrouve des émissions anciennes du
Masque et la Plume (1955-2016). Pour chacune, il copie l'audio dans le dossier audio de
lmelp et la décrit dans la collection `pap_remises` (une « remise », dans le code).

Une émission ancienne n'est pas encore un épisode de lmelp. La page **Émissions
anciennes** permet de l'**intégrer**, une par une : elle devient un épisode, en attente
de transcription, puis la suite est la même que pour un épisode du flux RSS
(notification, transcription PGX, Génération Avis Critiques…).

lmelp-pap écarte en amont les émissions déjà présentes dans lmelp : l'intégration ne
cherche pas de doublon avec les épisodes venus du flux RSS ou de la page
[Ajouter une émission](ajout-emission.md).

## Accès à l'interface

### Depuis le tableau de bord

- Section **Podcast Masque Et La Plume** : tuile **Émissions anciennes**, toujours visible.
- Section **Informations générales** : la tuile **Émissions anciennes à intégrer** affiche
  le nombre d'émissions à intégrer et mène à la même page. Elle disparaît quand il n'y a
  plus rien à intégrer.

### Navigation directe

URL directe : `/emissions-anciennes`

## La liste

La page liste les émissions anciennes livrées par lmelp-pap et pas encore intégrées,
**des plus récentes aux plus anciennes**. Pour chacune :

- son titre ;
- sa date de première diffusion et sa durée (absente si lmelp-pap ne la connaît pas) ;
- un lien vers sa page radiofrance.fr, quand elle existe ;
- un extrait de sa description (survolez-le pour la lire en entier).

Une émission dont le fichier audio manque n'apparaît pas : elle ne peut pas être intégrée.
Une émission déjà intégrée n'apparaît plus, même si son épisode a été masqué depuis.

## Intégrer une émission

Cliquez sur **Intégrer** sur sa ligne. Le bouton reste désactivé pendant l'intégration
(quelques secondes : l'empreinte du fichier audio est vérifiée).

L'épisode créé reprend le titre, la date, la durée, la description, l'URL et le fichier
audio fournis par lmelp-pap, ainsi que la page radiofrance.fr. Il garde la trace de sa
provenance (`source: "pap"`, `pap_remise_id`). Le fichier audio n'est ni renommé ni
déplacé.

En cas de succès, la ligne disparaît et un encadré rappelle l'épisode créé et l'état de
la transcription :

| Message | Signification |
|---------|---------------|
| **Transcription lancée sur PGX** | La transcription démarre. Si PGX est éteint, un nouvel essai a lieu toutes les heures. |
| **Transcription déjà en cours** | Une transcription tourne déjà ; l'épisode sera traité au prochain cycle. |
| **Transcription non lancée** | La transcription n'a pas pu démarrer ; lancez-la depuis la page [Transcription PGX](transcription-pgx.md). L'épisode reste intégré, en attente de transcription. |

## Notifications

Si les notifications sont configurées, chaque intégration envoie un message
**« pap - Nouvel épisode Le Masque et la Plume intégré — jj/mm/aa »** via
[ntfy.sh](https://ntfy.sh), suivi des notifications habituelles de la transcription PGX.
Un refus n'envoie pas de notification.

## Refus

Un refus s'affiche sur la ligne de l'émission, qui reste dans la liste :

| Message | Cause |
|---------|-------|
| Émission inconnue de lmelp-pap | Sa fiche n'existe plus dans `pap_remises`. |
| Émission déjà intégrée | Elle a déjà été intégrée (double clic, autre onglet). Rechargez la page. |
| Fichier audio absent du dossier audio de lmelp | Le fichier a disparu depuis l'affichage de la liste. |
| Empreinte SHA-256 du fichier audio différente de celle donnée par lmelp-pap | La copie est incomplète ou corrompue : elle n'est jamais transcrite. À reprendre côté lmelp-pap. |

## Voir aussi

- [Compteurs et statistiques](compteurs-et-statistiques.md) : tuile « Émissions anciennes à intégrer »
- [Transcription PGX](transcription-pgx.md) : étape suivante
- [Ajouter une émission](ajout-emission.md) : autre voie d'entrée d'une émission ancienne
