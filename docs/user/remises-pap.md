# Remises pap - lmelp

## Vue d'ensemble

[lmelp-pap](https://github.com/castorfou/lmelp-pap) retrouve des émissions anciennes du
Masque et la Plume (1955-2016). Pour chacune, il copie l'audio dans le dossier audio de
lmelp et écrit une fiche dans la collection `pap_remises` : c'est une **remise**. Une
remise dont le fichier audio est présent est **livrée**.

Une remise livrée n'est pas encore un épisode de lmelp. La page **Remises pap** permet de
l'**intégrer**, remise par remise : elle devient un épisode, en attente de transcription,
puis la suite est la même que pour un épisode du flux RSS (notification, transcription
PGX, Génération Avis Critiques…).

lmelp-pap écarte en amont les émissions déjà présentes dans lmelp : l'intégration ne
cherche pas de doublon avec les épisodes venus du flux RSS ou de la page
[Ajouter une émission](ajout-emission.md).

## Accès à l'interface

### Depuis le tableau de bord

La tuile **Remises à intégrer** de la section « Informations générales » affiche le nombre
de remises livrées pas encore intégrées. Cliquez dessus pour ouvrir la page. Elle
disparaît quand il n'y a plus rien à intégrer.

### Navigation directe

URL directe : `/remises-pap`

## La liste

La page liste les remises livrées pas encore intégrées, **des plus récentes aux plus
anciennes**. Pour chacune :

- son titre ;
- sa date de première diffusion et sa durée (absente si pap ne la connaît pas) ;
- un lien vers sa page radiofrance.fr, quand elle existe ;
- un extrait de sa description (survolez-le pour la lire en entier).

Une remise dont le fichier audio manque n'apparaît pas : elle ne peut pas être intégrée.
Une remise déjà intégrée n'apparaît plus, même si son épisode a été masqué depuis.

## Intégrer une remise

Cliquez sur **Intégrer** sur la ligne de la remise. Le bouton reste désactivé pendant
l'intégration (quelques secondes : l'empreinte du fichier audio est vérifiée).

L'épisode créé reprend le titre, la date, la durée, la description, l'URL et le fichier
audio de la remise, ainsi que sa page radiofrance.fr. Il garde la trace de sa remise
(`source: "pap"`, `pap_remise_id`). Le fichier audio n'est ni renommé ni déplacé.

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

Un refus s'affiche sur la ligne de la remise, qui reste dans la liste :

| Message | Cause |
|---------|-------|
| Remise inconnue | La fiche n'existe plus dans `pap_remises`. |
| Remise déjà intégrée | La remise a déjà été intégrée (double clic, autre onglet). Rechargez la page. |
| Fichier audio absent du dossier audio de lmelp | Le fichier a disparu depuis l'affichage de la liste. |
| Empreinte SHA-256 du fichier audio différente de celle de la remise | La copie est incomplète ou corrompue : elle n'est jamais transcrite. À reprendre côté pap. |

## Voir aussi

- [Compteurs et statistiques](compteurs-et-statistiques.md) : tuile « Remises à intégrer »
- [Transcription PGX](transcription-pgx.md) : étape suivante
- [Ajouter une émission](ajout-emission.md) : autre voie d'entrée d'une émission ancienne
