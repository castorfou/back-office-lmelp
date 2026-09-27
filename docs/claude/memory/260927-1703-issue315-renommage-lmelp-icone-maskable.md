# Issue #315 — Renommer l'app en « lmelp » + icône verte maskable

## Contexte

La PWA back-office (« BO LMELP ») et l'app Android lmelp-mobile avaient la même icône
rose : indistinguables sur l'écran d'accueil. lmelp-mobile est passé au bleu nuit
(castorfou/lmelp-mobile#141). Depuis #302, back-office-lmelp *est* lmelp (Streamlit
décommissionné). Par ailleurs, sans icône `"purpose": "maskable"`, Android affichait un
petit carré rose posé dans un disque blanc.

Décisions utilisateur :
- icône **verte historique** de lmelp, mais en **gardant la base de données** de l'icône
  rose (elle marque le rôle de back-office, qui sert à construire la base) ;
- renommer en « lmelp » **tout ce qui est visible** (frontend + backend).

## Modifications

### Icônes — `scripts/generate_favicons.py`
- Déplacé depuis `frontend/public/scripts/` : tout ce qui est sous `public/` est copié
  tel quel dans le build publié par Vite.
- Deux sources alignées (même composition, 1327×1328) dans `frontend/public/gimp_favicon/` :
  - `favicon.png` (verte) → `extract_foreground()` : détourage masque + plume
    (alpha selon la « verdeur » G − max(R,B), pelage des bords verts et du liseré
    magenta, plus grand composant connexe). Porté de
    `scripts/generate_launcher_icon.py` de lmelp-mobile.
  - `favicon_back-office-lmelp.png` (rose) → `extract_database()` : plus grand composant
    connexe de pixels à G < 60 (carmin + bandes violet foncé ; fond rose et ombre ont
    G > 75), élargi à son **enveloppe convexe** (`scipy.spatial.ConvexHull`).
- `build_motif()` : base de données, puis masque + plume par-dessus ; les trous restants
  (encoche de la plume entre plume et cylindre) sont comblés avec la couleur du pixel de
  base de données le plus proche (`ndimage.distance_transform_edt(..., return_indices=True)`).
- `build_any_icon()` : carré arrondi de la source (son alpha) rempli de vert uni
  `BACKGROUND_COLOR = #0FAE63`, motif par-dessus. L'ombre portée d'origine est
  abandonnée : sa silhouette ne correspondait pas au cylindre (bosses visibles).
- `build_maskable_icon(size)` : fond vert plein bord à bord, motif recentré, rayon
  0,38 × côté (safe zone maskable = disque de rayon 0,4).
- Produits dans `frontend/public/` : favicon-16/32/48, `favicon.ico`,
  `apple-touch-icon.png`, `android-chrome-192x192/512x512.png` (any),
  `maskable-icon-192x192.png` / `maskable-icon-512x512.png`.

### Manifest et nom
- `frontend/public/site.webmanifest` : `name`/`short_name` = `lmelp`, icônes 192/512 en
  `any` + 2 entrées `maskable`, `background_color` vert (splash Android).
- `frontend/index.html` : `<title>lmelp</title>`.
- `frontend/src/router/index.js` : tous les `meta.title` en « X - lmelp », fallback
  `document.title = 'lmelp'`.
- `frontend/src/views/Dashboard.vue` : `<h1>lmelp</h1>`.
- Backend : `FastAPI(title="lmelp")` et `GET /` → `"lmelp API"`
  (`src/back_office_lmelp/app.py`), bannière `🚀 DÉMARRAGE LMELP`
  (`utils/startup_logging.py`), notification d'échec PGX
  (`utils/pgx_transcription_runner.py`).

### Code mort supprimé
`frontend/src/utils/lmelpFrontOfficeUrl.js` (dérivation `xxx-bo.domaine` → `xxx.domaine`
vers le Streamlit 8501, Issue #265) : ses computed `lmelpFrontOfficeUrl` /
`lmelpAvisCritiquesUrl` n'étaient plus utilisés par le template, et servie sur
`lmelp.*` la dérivation serait retombée sur `localhost:8501`. Supprimés avec
`frontend/tests/unit/lmelpFrontOfficeUrl.test.js` et le bloc dédié de
`frontend/tests/integration/Dashboard.test.js`.

## Tests
- `tests/test_generate_favicons.py` : import du script via `importlib` (pas un package).
  `_assert_is_maskable()` : alpha = 255 partout, hors du disque 80 % tout pixel ≈
  `BACKGROUND_COLOR` (tolérance 8), motif présent au centre. `_database_ratio()` : part
  de pixels carmin > 3 %. Appliqués à la fonction **et aux PNG commités** (garde-fou si
  un fichier est remplacé à la main). Premier RED via un stub renvoyant la source
  redimensionnée → échec « transparence », pas `AttributeError`.
- `frontend/tests/unit/appBranding.test.js` : lit `public/site.webmanifest` et
  `index.html` via `fs` ; icônes `any` + `maskable`, fichiers présents, titres du router
  via `router.getRoutes()` qui finissent par « - lmelp ».
- Tests existants adaptés : `test_api_routes.py`, `test_health_endpoint.py`,
  `test_api_endpoints_simple.py`, `Dashboard.test.js`, `EpisodePage.test.js`,
  `HomePage.test.js`.

## Hors code

- Issue créée : [docker-lmelp#71](https://github.com/castorfou/docker-lmelp/issues/71) —
  reverse proxy DSM `lmelp.ascot63.synology.me` → frontend (8081), suppression de
  `lmelp-bo`, retrait du conteneur Streamlit `lmelp-frontoffice` (8501).
- **MongoDB 8.x ne démarre pas sur noyau Linux 6.19 → 7.0.13**
  ([SERVER-121912](https://jira.mongodb.org/browse/SERVER-121912), TCMalloc/rseq) : arrêt
  volontaire au démarrage (`MongoDB cannot start: Linux kernel versions 6.19 and newer…`),
  donc boucle de restart Docker. Poste dev en Ubuntu 26.04 (noyau `7.0.0-34`). Correctif
  local : override `docker-compose.mongo7.yml` (`image: mongo:7.0`,
  `command: ["mongod"]` car `/etc/mongod.conf` n'existe que dans `lmelp-mongo`), lancé par
  `docker compose -p lmelp-stack -f docker-compose.yml -f docker-compose.mongo7.yml up -d mongo`
  (stack « Limited » dans Portainer, non éditable), ancien volume 8.x mis de côté (7.0 ne
  lit pas des fichiers 8.x), `mongorestore --drop` du backup hebdo. Le NAS (DSM 5.x) n'est
  pas concerné.
- Piège devcontainer : `host.docker.internal` n'existe pas, le DNS le complète en
  `host.docker.internal.ascot63.synology.me` → IP du **NAS** (prod), pas l'hôte local.
- PWA Android en dev : pas d'installation possible sur `http://<IP LAN>:5173` (origine non
  sécurisée) — flag `chrome://flags/#unsafely-treat-insecure-origin-as-secure` ou
  `localhost` via port-forwarding adb. Après désinstallation, Chrome peut garder un état
  « installé » périmé (« Ouvrir » au lieu d'« Installer ») ; validation reportée au
  déploiement HTTPS sur le NAS.
