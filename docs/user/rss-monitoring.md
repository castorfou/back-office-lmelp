# Monitoring RSS Le Masque et la Plume - Back-Office LMELP

## Vue d'ensemble

Cette page automatise la détection et le téléchargement des nouveaux épisodes de l'émission "Le Masque et la Plume" (France Inter), en scrutant le flux RSS officiel. Elle remplace l'étape manuelle qui consistait à cliquer sur "🔄 Rafraîchir Episodes" dans le frontoffice `lmelp`.

## Ce que fait une synchronisation

Chaque synchronisation :

1. Récupère le flux RSS et ne retient que les épisodes non encore traités, publiés après le dernier épisode connu.
2. Ne garde que les épisodes durant plus de 15 minutes (filtre les sous-parties/clips œuvre par œuvre).
3. Classifie chaque épisode candidat en "livres", "films" ou "théâtre" (analyse automatique du titre et de la description).
4. Pour les épisodes "livres" uniquement : télécharge le fichier audio et crée l'entrée épisode dans la base de données.
5. Envoie une notification (si configurée) pour chaque épisode traité, qu'il soit retenu ou non.
6. Enregistre le résultat de la synchronisation dans l'historique de cette page.

## Accès à l'interface

### Depuis le tableau de bord

1. Ouvrez le **Dashboard** (page d'accueil)
2. Localisez la section **"RSS Masque Et La Plume"**
3. Cliquez sur la tuile **"Monitoring Downloads"**

### Navigation directe

URL directe : `/rss-monitoring`

## Déclenchement d'une synchronisation

Cliquez sur le bouton **"🔄 Rafraîchir Episodes"** pour lancer une synchronisation immédiate. Le résultat s'affiche juste en dessous du bouton (statut et nombre d'épisodes traités), et le nouveau run apparaît en tête de l'historique.

Une synchronisation peut aussi être déclenchée automatiquement par un système externe (ex: un workflow d'automatisation détectant un nouvel épisode sur le flux RSS) — voir la documentation de déploiement pour la configuration correspondante.

## Historique des synchronisations

Le tableau liste chaque synchronisation effectuée, la plus récente en premier, avec :

- **Date** : horodatage du déclenchement
- **Déclenchement** : `manual` (bouton de cette page) ou `api` (appel automatisé externe)
- **Statut** : `success`, `partial_error` (une erreur ponctuelle sur un épisode) ou `error` (échec global, ex: flux RSS injoignable)
- **Épisodes** : nombre d'épisodes traités durant ce run

Cliquez sur une ligne pour afficher le détail des épisodes traités durant ce run, chacun préfixé par sa date de diffusion (`dd/mm/yy`) et son résultat :

| Résultat | Signification |
|----------|----------------|
| **downloaded** | Épisode "livres" téléchargé et ajouté à la base |
| **skipped_not_book** | Épisode détecté mais non retenu (film, théâtre) |
| **already_exists** | Épisode déjà présent en base, ignoré |
| **error** | Une erreur est survenue pour cet épisode spécifique |

## Notifications

Si configurées (voir `docs/dev/environment-variables.md`), des notifications sont envoyées via [ntfy.sh](https://ntfy.sh) pour chaque épisode traité — qu'il soit téléchargé ou détecté mais non retenu. Le titre de la notification inclut toujours la date de diffusion de l'épisode concerné.

## Voir aussi

- `docs/dev/rss-sync.md` (détail technique du service de synchronisation)
