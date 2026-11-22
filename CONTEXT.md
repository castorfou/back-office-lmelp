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
audio (par le flux RSS, par un ajout depuis sa page radiofrance.fr ou par l'intégration
d'une remise), en attente ou non de transcription.
_Avoid_: émission (tant que les avis critiques ne sont pas générés)

**Remise**:
Un enregistrement que lmelp-pap met à la disposition de lmelp : il en copie l'audio dans le
dossier audio de lmelp et en écrit la fiche. pap décrit l'émission (titre, date de première
diffusion, durée, description, empreinte de l'audio) ; lmelp décide de l'épisode qu'elle
devient. pap garantit qu'une remise n'est pas une émission déjà présente dans lmelp :
lmelp ne recherche pas les doublons à l'intégration. Une remise ne se retire pas.
_Avoid_: émission pap, fiche pap (comme synonyme), import

**Remise livrée**:
Une remise dont le fichier audio est présent dans le dossier audio de lmelp ; une remise
dont le fichier manque n'est pas livrée et ne peut pas être intégrée.
_Avoid_: remise reçue, remise disponible

**Intégration**:
Le geste explicite, remise par remise, qui fait d'une remise livrée un épisode de lmelp.
_Avoid_: import, synchronisation pap

**Émission**:
Un épisode dont les avis critiques ont été générés : il apparaît alors dans la page
Émissions, avec ses livres et ses critiques.
_Avoid_: épisode (une fois structuré)

**PGX**:
La station GPU personnelle qui transcrit les épisodes ; elle se déplace entre la maison
d'été et les quartiers d'hiver, et lmelp doit la joindre où qu'elle soit.
_Avoid_: serveur de transcription, machine locale

**Identité de PGX**:
La clé d'hôte SSH de PGX : c'est elle, et elle seule, qui permet de reconnaître PGX ; une
machine qui présente une autre clé n'est pas PGX, quelle que soit son adresse.
_Avoid_: IP de PGX, PGX_HOST

**Adresse de PGX**:
L'adresse IP où PGX est joignable à un moment donné (réseau de la maison d'été ou VPN du
NAS) ; elle change avec les déplacements et les connexions VPN, et ne prouve jamais
l'identité de PGX.
_Avoid_: hôte PGX, IP PGX (comme synonyme d'identité)

**Séquence**:
Un extrait de quelques minutes d'une émission, consacré à un seul livre, publié séparément
sur radiofrance.fr ; ce n'est jamais un épisode.
_Avoid_: clip, extrait audio

### Babelio

**Validation Babelio**:
Le geste explicite qui confronte, un par un, les livres d'une émission à Babelio et donne
à chacun un résultat (vérifié, suggestion, introuvable, bloqué, erreur) ; c'est la seule
occasion où lmelp interroge Babelio pour une émission.
_Avoid_: enrichissement Babelio (ce n'est plus une étape distincte)

**Cookie Babelio**:
Le cookie de session copié depuis un navigateur connecté à Babelio, sans lequel lmelp
n'envoie aucune requête ; il est actif pendant une durée limitée après son enregistrement,
puis expiré.
_Avoid_: jstsToken (jeton facultatif, ce n'est pas le cookie), cookie navigateur

**Pause de validation**:
L'arrêt temporaire d'une validation Babelio quand le cookie Babelio expire en cours de
route : aucun livre n'est traité tant qu'un cookie actif n'est pas enregistré, puis la
validation reprend au livre interrompu. Un vrai refus de Babelio n'est jamais une pause.
_Avoid_: suspension, blocage (réservé au refus de Babelio)
