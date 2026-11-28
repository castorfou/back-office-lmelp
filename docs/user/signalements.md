# Passages signalés

Un auditeur qui trouve un Passage mal découpé le signale depuis le lecteur, dans lmelp ou
dans lmelp-mobile. Le mainteneur retrouve les signalements dans la page **Passages
signalés** (`/signalements`).

## Signaler un Passage

Dans le lecteur fixé en bas de page, le bouton **⚠️** ouvre :

- un champ **commentaire**, facultatif (500 caractères au plus) ;
- la liste des motifs : **Début trop tôt**, **Fin trop tôt**, **Déborde sur un autre
  livre**, **Mauvais livre**, **Autre**.

Un clic sur un motif envoie le signalement, avec l'instant d'écoute et les bornes du Passage
écouté. Une bulle confirme l'envoi (« ✓ Signalé : Fin trop tôt à 12:40 ») ou en donne la
raison de l'échec. Un clic ailleurs referme le menu.

Le signalement est anonyme : rien sur l'auditeur n'est enregistré. Le ⚠️ n'apparaît pas sur le
Passage d'un titre pas encore validé (sans livre en base).

## Traiter les signalements

La tuile **Passages signalés** du tableau de bord donne le nombre de signalements ouverts ;
elle disparaît quand il n'y en a plus. Elle mène à la page des signalements, qui liste pour
chacun : l'émission, le livre, le motif, l'instant d'écoute, le commentaire, la date, la
source (`web` ou `mobile`) et les bornes écoutées. Quand le Passage a changé depuis, la page
montre aussi ses bornes actuelles.

- **Corriger** ouvre « Correction des passages » sur l'émission, le Passage mis en avant.
  Toute correction à la main de ce Passage clôt ses signalements ouverts.
- **Rejeter**, après confirmation, clôt le signalement sans toucher au Passage.

Un nouveau repérage automatique ne clôt jamais un signalement.
