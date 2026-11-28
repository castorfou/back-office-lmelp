# Configuration mobile

Les Passages audio s'écoutent aussi dans **lmelp-mobile**, depuis internet. L'audio y est servi
par **lmelp-streaming**, qui exige une **clé d'écoute** : un secret partagé par le cercle des
auditeurs. La page **Configuration mobile** (`/configuration-mobile`, tableau de bord →
« Application mobile ») remet cette clé par QR code et permet de la changer.

## Donner l'accès à un auditeur

1. Dans lmelp-mobile, ouvrir **Réglages › Écoute des passages**.
2. Toucher **Scanner le QR code** et viser le code affiché par la page.
3. Les Passages s'écoutent alors depuis la fiche livre et la fiche émission, en ligne.

Le QR code contient le lien `lmelp://ecoute?base=…&cle=…` :

- **base** : l'adresse publique de lmelp-streaming, déduite de l'adresse par laquelle la page
  est ouverte (`lmelp.<domaine>` → `https://lmelp-streaming.<domaine>`). Ouverte par une autre
  adresse (`localhost`, adresse IP), la page n'affiche pas de QR code et l'explique ;
- **cle** : la clé d'écoute.

La **saisie manuelle** donne les mêmes informations : l'adresse, la clé (masquée, bouton
« Afficher ») et un bouton « Copier le lien ».

La page indique depuis quand la clé est en service, et combien de fois elle a changé.

## Invalider le QR code

À faire si le QR code ou la clé a circulé hors du cercle des auditeurs. **« Invalider et
générer un nouveau QR code »**, après confirmation, crée une nouvelle clé :

- l'ancienne est refusée aussitôt par lmelp-streaming (à sa minute de cache près), sans
  période de grâce ;
- chaque auditeur doit scanner le nouveau code ;
- l'écoute dans lmelp (réseau local) n'est pas concernée : elle n'utilise pas la clé.

Les anciennes clés ne sont gardées nulle part ; seules les dates des changements le sont.

## Création de la clé

La clé est créée automatiquement au premier démarrage du backend. Aucune variable
d'environnement n'est à régler.
