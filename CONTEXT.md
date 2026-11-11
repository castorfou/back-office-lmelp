# lmelp

Application de consultation et d'administration des données du Masque et la Plume
(émissions, livres, critiques, avis), croisées avec la bibliothèque Calibre personnelle.

## Language

### Bibliothèque Calibre

**Bibliothèque source**:
La bibliothèque Calibre de référence, sur le PC où Calibre est utilisé : c'est là que toute
modification (lecture, note, tags) est d'abord enregistrée.
_Avoid_: base locale, Calibre local

**Copie Drive**:
La copie de la bibliothèque source tenue à jour sur le NAS par Synology Drive, dans le
dossier de sauvegarde du laptop.
_Avoid_: base NAS, backup Calibre

**Bibliothèque CWA**:
La copie de la bibliothèque appartenant à Calibre-Web-Automated, qui peut y écrire et
dont dépend la synchronisation de lecture KOReader.
_Avoid_: base NAS, books

**Copie servie**:
La copie Calibre que lmelp lit pour afficher les données Calibre, quelle qu'elle soit
(aujourd'hui la bibliothèque CWA).
_Avoid_: base NAS, réplique, base serveur

**Synchronisation Drive**:
Le transport continu de la bibliothèque source vers la copie Drive.
_Avoid_: synchro Calibre, synchro PC → NAS

**Synchronisation nocturne**:
La recopie quotidienne de la copie Drive vers la bibliothèque CWA, CWA étant arrêté pendant
la copie.
_Avoid_: rsync, nightly sync, synchro Calibre

**Synchronisation liseuse → Calibre**:
Le report dans la bibliothèque source de l'état tenu par la liseuse (progression, statut lu).
_Avoid_: synchro KOReader, synchro Calibre

**Fraîcheur Calibre**:
L'âge de la copie servie, c'est-à-dire le temps écoulé depuis sa dernière mise à jour.
_Avoid_: dernière synchro, date de synchro

**Délai de mise à disposition**:
Le temps entre l'enregistrement d'une modification dans la bibliothèque source et son
affichage dans lmelp.
_Avoid_: latence, retard de synchro

### Émissions du Masque et la Plume

**Épisode**:
Un enregistrement du Masque et la Plume consacré aux livres, entré dans la base avec son
audio (par le flux RSS ou par un ajout depuis sa page radiofrance.fr), en attente ou non de
transcription.
_Avoid_: émission (tant que les avis critiques ne sont pas générés)

**Émission**:
Un épisode dont les avis critiques ont été générés : il apparaît alors dans la page
Émissions, avec ses livres et ses critiques.
_Avoid_: épisode (une fois structuré)

**Séquence**:
Un extrait de quelques minutes d'une émission, consacré à un seul livre, publié séparément
sur radiofrance.fr ; ce n'est jamais un épisode.
_Avoid_: clip, extrait audio
