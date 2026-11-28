# Correction des passages

Un **Passage** est la portion de l'audio d'une émission où les critiques parlent d'un livre.
Les Passages sont repérés automatiquement à partir de la transcription horodatée (les
**Segments**) et du résumé de l'émission. La page **Correction des passages**
(`/correction-passages`, tableau de bord → « Correction de la base ») sert à vérifier et
corriger leurs bornes.

## Choisir une émission

Le sélecteur liste toutes les émissions, avec une pastille :

| Pastille | Signification |
|---|---|
| 🟢 | Passages validés |
| 🟠 | Passages à vérifier |
| 🔴 | Pas de Segments horodatés : rien à corriger tant que l'émission n'est pas retranscrite |

Les boutons **Précédent** et **Suivant** passent d'une émission à l'autre. La page s'ouvre sur
la première émission qui a des Segments.

## Lire la page

- **Lecteur** : lecture/pause, sauts de −60, −30, −10, +10, +30 et +60 s, position dans
  l'émission. Ouvrir la page arrête le lecteur fixé en bas des autres pages.
- **Frise** (en haut) : les Passages de l'émission, dans l'ordre. Un clic sur un Passage amène
  le texte à son début. Les **trous** (hachurés) sont des zones qu'aucun Passage ne couvre ; le
  bouton ▶ d'un trou l'écoute. Un trou de plus de 2 min est encadré en orange : un livre manque
  probablement.
- **Cartes** (à gauche) : une par Passage, avec son titre, sa durée, son origine (« repéré
  auto » ou « corrigé »), son début ⇤ et sa fin ⇥.
  - 🎧 écoute les 15 premières ou dernières secondes, ▶ écoute tout le Passage ;
  - ⚠️ signale un Passage de moins de 30 s ;
  - ↗ ouvre la fiche du livre ; un titre en italique marqué « à valider » est le titre du
    résumé d'un livre pas encore validé, sans fiche.
- **Transcription** (à droite) : chaque Segment avec son heure, les bandeaux de début et de
  fin de chaque Passage, et le Segment en cours de lecture surligné. Un clic sur un Segment
  lance la lecture à cet endroit.

## Corriger

Chaque correction est enregistrée aussitôt. Elle passe les Passages touchés en « corrigé » :
le repérage automatique ne les modifiera plus. Elle retire aussi la validation de l'émission
(🟢 → 🟠). Une correction refusée n'a aucun effet ; sa raison est écrite dans le **journal des
actions**, sous la page.

### Déplacer une borne

Cliquer 📍 à côté du début ou de la fin d'une carte, puis cliquer le Segment où le livre
commence ou finit. La borne prend l'heure exacte du Segment (son début pour un début de
Passage, sa fin pour une fin).

Deux Passages qui se touchent partagent leur frontière : déplacer le début d'un Passage
déplace la fin du précédent, et inversement. Un trou entre deux Passages reste un trou.

### Supprimer et restaurer

🗑 supprime un Passage qui n'en est pas un, après confirmation. La suppression est conservée :
un nouveau repérage ne le recrée pas. Le Passage apparaît sous les cartes avec un bouton
**Restaurer**.

### Placer un livre manquant

La liste **À placer** reprend les livres du résumé que le repérage n'a pas trouvés. Glisser un
livre :

- sur un trou de la frise : il prend tout le trou ;
- sur une phrase d'un trou dans la transcription : il commence à cette phrase et va jusqu'à
  la fin du trou.

Un livre placé à la main est marqué ✋ sur la frise. Un clic dessus ouvre son menu :
**Tout le trou**, **Première partie**, **Dernière partie** (coupure à la phrase la plus
proche du milieu), ou **Remettre à placer**. On peut aussi le glisser de la frise vers la
liste « À placer ».

Un trou peut rester vide : le sommaire, le courrier ou le générique n'appartiennent à aucun
livre.

## Valider

**✅ Valider les Passages** marque l'émission comme vérifiée (🟢). Un second clic retire la
validation. Toute correction ultérieure la retire aussi.
