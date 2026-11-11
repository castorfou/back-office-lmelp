# Ajouter une émission - lmelp

## Vue d'ensemble

Le flux RSS France Inter ne contient que les épisodes récents. Une émission plus ancienne
absente de lmelp ne peut donc pas arriver par la [synchronisation RSS](rss-monitoring.md).
La page **Ajouter une émission** la récupère à partir de sa page sur radiofrance.fr.

Une fois l'émission ajoutée, la suite est la même que pour un épisode du flux RSS :
notification, transcription PGX, puis les étapes manuelles habituelles (Génération Avis
Critiques, Livres et Auteurs…).

## Accès à l'interface

### Depuis le tableau de bord

1. Ouvrez le **Dashboard** (page d'accueil).
2. Dans la section **Podcast Masque Et La Plume**, cliquez sur la tuile **Ajouter une émission**.

### Navigation directe

URL directe : `/ajout-emission`

## Ajouter une émission

1. Sur radiofrance.fr, ouvrez la page de l'émission dans le podcast *Le Masque et la Plume*.
   Son adresse commence par
   `https://www.radiofrance.fr/franceinter/podcasts/le-masque-et-la-plume/`.
2. Collez cette adresse dans le champ **URL de la page radiofrance.fr**.
3. Cliquez sur **Ajouter l'émission**.

Le titre, la date, la description et le fichier audio complet sont lus sur la page.
L'audio est téléchargé (quelques secondes à une minute), puis l'épisode est ajouté à la
base.

!!! warning "Utiliser la page de l'émission, pas un lien audio"
    radiofrance.fr publie aussi des **séquences** de quelques minutes consacrées à un seul
    livre. Leur lien audio ressemble à celui de l'émission. Partir de la page de
    l'émission garantit de récupérer l'enregistrement complet.

## Résultat

En cas de succès, la page affiche le titre, la date et la durée de l'émission ajoutée,
ainsi que l'état de la transcription :

| Message | Signification |
|---------|---------------|
| **Transcription lancée sur PGX** | La transcription démarre. Si PGX est éteint, un nouvel essai a lieu toutes les heures. |
| **Transcription déjà en cours** | Une transcription tourne déjà ; l'émission sera traitée au prochain cycle. |
| **Transcription non lancée** | La transcription n'a pas pu démarrer ; lancez-la depuis la page [Transcription PGX](transcription-pgx.md). |

Deux liens mènent à la suite du traitement : **Suivre la transcription** et **Génération
Avis Critiques**. L'émission apparaît dans la page Émissions une fois ses avis critiques
générés.

## Notifications

Si les notifications sont configurées, un message
**« Ajout manuel - Nouvel épisode Le Masque et la Plume téléchargé — jj/mm/aa »** est
envoyé via [ntfy.sh](https://ntfy.sh), suivi des notifications habituelles de la
transcription PGX.

## Refus

| Message | Cause |
|---------|-------|
| L'URL doit être une page d'émission Le Masque et la Plume | L'adresse n'est pas une page du podcast sur radiofrance.fr. |
| Audio de N min : c'est une séquence, pas une émission complète | L'audio de la page dure moins de 30 minutes. |
| Une émission existe déjà le jj/mm/aaaa | Un épisode existe déjà à cette date, quel que soit son titre. |
| Page radiofrance.fr inaccessible | La page n'a pas pu être lue (adresse erronée, site indisponible). |
| Téléchargement de l'audio impossible | Le téléchargement a échoué ; relancez l'ajout. |

Si la page affiche une erreur de délai dépassé alors que l'audio était en cours de
téléchargement, relancez simplement l'ajout : un audio déjà téléchargé est réutilisé, et
un épisode déjà ajouté est signalé comme existant.

## Voir aussi

- [Monitoring RSS](rss-monitoring.md) : arrivée automatique des nouveaux épisodes
- [Transcription PGX](transcription-pgx.md) : étape suivante
- `docs/dev/ajout-emission.md` : détail technique
