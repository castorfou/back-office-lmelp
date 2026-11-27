# Issue #406 — Corriger les problèmes de données

Le tableau de bord de prod affichait 1 émission avec problème, 1 critique manquant et 1
doublon. L'émission avec problème (28/06/2015, deux livres sur une ligne de coups de cœur)
relève de #408. Les deux autres sont corrigés ici, avec leur prévention, et le travail a
élargi le périmètre à la gestion du cookie Babelio sur trois pages et à un test qui effaçait
le fichier de découverte des services de dev.

## 1. Critique manquant : remarque du LLM prise pour un nom

- Cas réel : émission du 29/11/2015, section 2, colonne Critique =
  `(Déjà dans le programme principal, ne pas dupliquer)`.
- `AvisExtractionService` ignorait déjà ces lignes depuis #405, mais pas
  `critiques_extraction_service.extract_critiques_from_summary()`, qui alimente le compteur
  « Critiques manquants » et la page Identification des critiques.
- Correctif `src/back_office_lmelp/services/critiques_extraction_service.py:75` : cellule
  Critique entre parenthèses ignorée, et découpage par position avec
  `AvisExtractionService._split_table_row()` (la colonne Critique passe de l'index 4 à 3,
  la barre de bord étant retirée).
- Mesure sur la base de dev (191 résumés) : 1 seul changement, une autre remarque du LLM
  `(Animateur, nom non précisé)` (06/09/2026). La mesure sur la prod n'a pas pu être refaite
  (NAS injoignable depuis le réseau de l'appart).
- Test : `tests/test_critiques_extraction_remarque_llm.py`.

## 2. Doublon d'auteurs : URL Babelio posée après création par le nom

- Cas réel : « Patrick J. Rogers » (créé le 27/11/2025, nom erroné) et « Patrick Roegiers »
  (créé le 25/11/2026 pour *L'autre Simenon*), même URL `…/auteur/Patrick-Roegiers/6213`.
- Cause : `MongoDBService.create_author_if_not_exists(nom)` ne dédoublonne que par égalité
  stricte du nom ; l'URL auteur n'est connue qu'ensuite (`_enrich_livre_from_babelio_page`)
  et était posée sans vérifier qu'un autre auteur l'avait déjà.
- Correctif `src/back_office_lmelp/app.py:1922` : `_merge_if_author_url_taken(author_id, url)`,
  appelé juste après la pose de l'URL sur les deux chemins qui l'écrivent :
  l'enrichissement après validation (`app.py:1917`) et l'application d'un rafraîchissement
  manuel `POST /api/livres/{id}/apply-refresh` (`app.py:2873`). Recherche d'un autre auteur
  par URL insensible à la casse (regex ancrée + `re.escape`), puis réutilisation telle quelle
  de `duplicate_books_service.merge_duplicate_authors()` (garde le plus ancien, nom officiel
  Babelio, livres rattachés, doublon supprimé). Aucune seconde logique de fusion.
- Garde-fou `src/back_office_lmelp/services/duplicate_books_service.py:582` : si
  `fetch_author_name_from_url()` renvoie `None` (page sans h1, erreur de lecture), la fusion
  garde le nom de l'auteur primaire au lieu d'écrire `nom: None`. Un 403 lève
  `BabelioBlockedError` avant toute écriture.
- Tests sur mongomock (vraies requêtes, vrais types) : `tests/test_author_url_collision_merge.py`.
  Le singleton Babelio y est pris par `vars(app_module)["babelio_service"]` :
  `test_babelio_service.py` recharge le module, l'importer directement pourrait donner un
  autre objet, et ruff (B009) réécrit un `getattr` littéral en accès direct, refusé par mypy
  (attribut non réexporté).
- `tests/test_livre_refresh_babelio.py` : le mock de `mongodb_service` doit renvoyer
  `auteurs_collection.find_one = None` (pas de collision), sinon un `MagicMock` passe pour un
  auteur trouvé. Le code de prod teste `existing is None`, il ne s'adapte pas aux mocks.
- Validé en local sur le vrai Babelio : fusion depuis la page Doublons, puis « Ré-extraire »
  de *L'autre Simenon* porté par un auteur « P. Roegiers » sans URL → fusion automatique
  (log `👥 Auteur … fusionné avec …`).

## 3. Cookie Babelio sur les pages qui lisent Babelio à la demande

- Déclencheur : en prod, « Fusionner » sur la page Gestion des doublons a renvoyé
  `Babelio 403 scraping` (pas de cookie sur cette page ; un 403 peut tourner au ban IP ~24 h,
  pas de ban cette fois).
- Recensement des endpoints qui lisent Babelio et des pages qui les appellent : il restait
  aussi la fiche livre (« ↻ Ré-extraire », `refresh-babelio`) et la page Recherche Babelio
  (`/babelio-test`, `verify-babelio`).
- Mixin commun `frontend/src/utils/babelioCookieGuard.js` (`babelioCookieGuardMixin`,
  `BABELIO_UNREACHABLE`) : `babelioServiceStatus`, `babelioCookieState`,
  `babelioCookieActive`, `loadBabelioServiceStatus()`, `probeBabelio()` (même règle que
  `LivresAuteurs.vue` : une sonde en erreur ne bloque pas).
- Le mixin n'a **pas** de `mounted` : un hook de mixin s'exécute avant celui de la page, et
  l'appel au statut consommait les `mockResolvedValueOnce` des tests d'intégration prévus pour
  les données de la page. Chaque page appelle `loadBabelioServiceStatus()` après ses propres
  chargements (le contenu d'abord).
- Pages : `frontend/src/views/DuplicateBooks.vue` (boutons Fusionner et Tout fusionner
  désactivés sans cookie actif, sonde avant chaque fusion, statut rechargé après un échec,
  « Tout fusionner » s'arrête au premier échec), `frontend/src/views/LivreDetail.vue`
  (Ré-extraire), `frontend/src/views/BabelioTest.vue` (trois recherches).
- Tests : `frontend/src/views/__tests__/{DuplicateBooks,LivreDetail,BabelioTest}.babelioCookie.spec.js` ;
  tests existants ajustés à la sonde (`LivreDetailRefresh.spec.js`, une réponse en plus) et au
  cookie requis (`tests/integration/BabelioTest.test.js`, statut actif mocké).

## 4. Un test effaçait le vrai `.dev-ports.json`

- Symptôme : les services de dev tournaient mais le fichier de découverte avait disparu
  (déjà arrivé auparavant).
- Diagnostic par boucle : fichier témoin à la racine, puis chaque fichier de test suspect
  lancé seul → `tests/test_server_shutdown.py::test_signal_handler_shuts_down_gracefully`.
  Il appelait le vrai `signal_handler()`, qui nettoie `Path.cwd() / ".dev-ports.json"`,
  soit le fichier des services en cours quand pytest tourne depuis la racine du repo.
- Correctif : le test patche `PortDiscovery.get_unified_port_file_path` vers `tmp_path` et
  vérifie que ce fichier-là est nettoyé.
- Garde-fou `tests/conftest.py:24` (`_protect_real_dev_ports_file`, autouse) : compare le vrai
  fichier avant/après chaque test ; s'il a changé, le remet en place et fait échouer le test
  en le nommant. Suite complète lancée avec un témoin : aucun autre test fautif.

## Données de prod (après déploiement, détaillé dans #408)

- Fusionner le groupe `Patrick-Roegiers/6213` depuis Gestion des doublons, cookie frais collé.
- Le compteur « Critiques manquants » retombe à 0 avec le code, sans action sur les données.

## Points de méthode

- Diagnostic de prod en lecture seule : l'URL publique de l'appli renvoie la page de connexion
  Synology, l'API n'est pas joignable ; requêtes directes sur le Mongo de prod
  (`192.168.50.207:27018`, réseau maison uniquement).
- Données de test locales recréées à l'identique de la prod (mêmes `_id`, dates, URL) dans le
  Mongo de dev (`localhost:27018`), sans écraser l'existant.
- Groupe « Jean-Michel Ribettes » / « Michel Jean » (même URL `Michel-Jean/149380`) présent
  seulement dans la base de dev : probable mauvaise association Babelio, ne pas fusionner.
