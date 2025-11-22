# tests backend API episodes

## tous les episodes visibles

curl -s "$(bash -c '/workspaces/back-office-lmelp/.claude/get-backend-info.sh --url')/api/episodes" | jq 'length'

## tous les episodes y compris les invisibles

curl -s "$(bash -c '/workspaces/back-office-lmelp/.claude/get-backend-info.sh --url')/api/episodes/all" | jq 'length'

## masquer l'episode 6773e32258fc5717f3516b9f du 2024-11-10T09:59:39.000+00:00

BACKEND_URL=$(/workspaces/back-office-lmelp/.claude/get-backend-info.sh --url)
curl -X PATCH "$BACKEND_URL/api/episodes/6773e32258fc5717f3516b9f/masked" \
  -H "Content-Type: application/json" \
  -d '{"masked": true}'

## demasquer un episode 6773e32258fc5717f3516b9f

BACKEND_URL=$(/workspaces/back-office-lmelp/.claude/get-backend-info.sh --url)
curl -X PATCH "$BACKEND_URL/api/episodes/6773e32258fc5717f3516b9f/masked" \
  -H "Content-Type: application/json" \
  -d '{"masked": false}'

# discussions sur UX

1. Où placer la fonctionnalité ?
Option A : Nouvelle page dédiée /episodes/manage
➕ Séparation claire : gestion vs consultation
➕ Peut afficher TOUS les épisodes (masqués inclus)
➖ Une page de plus à maintenir
Option B : Intégrer dans EpisodePage.vue existante
➕ Tout au même endroit
➕ Toggle "Afficher masqués" simple
➖ Risque de surcharger l'interface
Option C : Les deux
Page existante : toggle pour afficher masqués
Page dédiée : gestion avancée (tri, filtres, actions groupées)
Ma recommandation : Option B (simple) pour commencer, facile d'évoluer vers C plus tard.
2. Comment visualiser visuellement un épisode masqué ?
Badge "Masqué" ?
Icône (œil barré 🚫👁️) ?
Opacité réduite + grisé ?
Combinaison (icône + opacité) ?
3. Comment masquer/démasquer ?
Bouton toggle sur chaque ligne ?
Click sur l'icône ?
Menu contextuel (clic droit) ?
Modal de confirmation ?
Quelle est votre vision ? Avez-vous des préférences ou contraintes spécifiques ?

Je voudrais ajouter une nouvelle page accessible depuis les Fonctions disponibles (comme la page Livres et Auteurs). Cette page va suivre le template de page que nous n'avons peut-etre jamais decrit explicitement. Ca serait l'occasion de le faire a savoir : un bandeau avec sur la gauche un retour possible vers Accueil, sur la droite le titre de la page. Je peux te fournir un visuel de la page Livres et Auteurs ou tu peux regarder son code.
J'avais imagine un tanleau qui reprend tous les episodes (masques ou non) avec les colonnes suivantes :
- Titre de l'episode
- Duree de l'episode (car je masquerai souvent les episodes courts)
- Date de publication
- Statut (masqué ou visible)
Et le statut masque visible sera un toggle bouton. Peut-etre que le visible aura une opacite reduite, grise (peu visible) et quand je clique ca devient visible et clair que l'episode est desormais masque
Les colonnes sont clickables/triables. (comme dans la page Livres et auteurs) et peut-etre meme filtrable si c'est pas trop une usine a gaz (je commence a taper des caracteres et ca filtre sur les colonnes titre et date)
