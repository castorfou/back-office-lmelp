# Issue #274 — Tri "Dernières lectures" sur la page Bibliothèque Calibre

## Contexte

La page Bibliothèque Calibre (`frontend/src/views/CalibreLibrary.vue`, route `/calibre`) proposait 5 tris (Derniers ajoutés, Titre A→Z/Z→A, Auteur A→Z/Z→A) mais aucun ne reflétait l'activité de lecture réelle (via KOReader). L'utilisateur voulait un tri "Dernières lectures" qui remonte en tête les livres en cours et récemment terminés.

## Piège évité : mauvaise interprétation initiale de la règle métier

Ma première implémentation ne considérait que les livres "en cours" (progress < 100%) comme prioritaires, avec tout le reste (y compris les livres terminés) retombant sur le tri "date d'ajout". Résultat testé par l'utilisateur : "quand je clique sur Dernières lectures, j'ai le même contenu que Derniers ajoutés" — dans ses données réelles, un seul livre était "en cours", et c'était déjà le plus récent ajout, donc aucune différence visible.

**La vraie règle** (précisée par l'utilisateur après ce retour) : "Dernières lectures" ne veut pas dire "livres en cours de lecture" mais **tri par date de fin de lecture**, avec une exception pour les livres sans date de fin mais avec une date de début (= en cours, à faire remonter avant tout le reste) :

1. **En cours** : `ko_date_started` présent ET `ko_date_finished` absent → triés par date de début décroissante.
2. **Terminés** : `ko_date_finished` présent → triés par date de fin décroissante (c'est le cœur du sens "Dernières lectures").
3. **Jamais synchronisés** : ni l'un ni l'autre → triés par date d'ajout Calibre décroissante (comportement de "Derniers ajoutés").

Le tri est aussi devenu le **tri par défaut** au chargement de la page (`sortBy: 'recent-reads'` dans `data()`), pas seulement une option à activer manuellement — point également corrigé après un second retour utilisateur ("il faut que le Tri Dernières lectures soit activé").

**Leçon générale** : quand une règle de tri/filtre semble "ne rien changer" à l'usage réel, ne pas conclure trop vite que le jeu de données est juste peu discriminant — reformuler la question à l'utilisateur sur le *nom* et l'*intention* de la fonctionnalité avant de valider l'implémentation contre les vraies données. Ici la première explication ("un seul livre en cours, coïncidence avec le plus récent ajout") était une fausse piste qui masquait une mauvaise compréhension de la règle elle-même.

## Découverte technique : champs KOReader absents de `get_books()`/`get_book()`

L'issue #273 avait ajouté `ko_progress`/`ko_status`/`ko_date_started`/`ko_date_finished` uniquement dans `CalibreService.get_all_books_with_tags()` (utilisée par le matching OnKindle). La page Bibliothèque Calibre charge ses livres via `get_books()` → `_build_book_from_row()` → modèle Pydantic `CalibreBook`, un chemin de données différent qui n'avait pas ces champs. Ajoutés :

- `src/back_office_lmelp/models/calibre_models.py` — 4 nouveaux champs optionnels sur `CalibreBook`.
- `src/back_office_lmelp/services/calibre_service.py` — même bloc de requêtes SQL que #273 (voir [[260902-2028-issue273-onkindle-koreader-progress]] pour le détail du pattern `ko_status` en jointure à liaison) ajouté dans `_build_book_from_row()`, qui alimente à la fois `get_books()` (pagination) et `get_book()` (détail).

## Tests

- Backend : nouveau test `test_get_book_exposes_koreader_fields` dans `tests/test_calibre_service.py::TestCalibreServiceGetBook`, suivant le pattern `execute_side_effect` déjà en place. Aucune régression sur les tests existants (le mock `_custom_columns_map` vide dans les autres tests fait que les nouveaux blocs `if ko_progfloat_col_id:` ne s'exécutent simplement pas).
- Frontend : **découverte tardive** qu'un fichier de test existait déjà pour ce composant sous `frontend/tests/unit/CalibreLibrary.test.js` (convention différente de `frontend/src/views/__tests__/*.spec.js` utilisée par les composants plus récents comme OnKindle) — non trouvé par un simple `find -iname "*CalibreLibrary*"` dans `src/views/__tests__/` au premier passage. Un fichier `.spec.js` séparé avait été créé par erreur puis supprimé pour intégrer les nouveaux tests dans le fichier existant. **Leçon** : avant de créer un nouveau fichier de test pour un composant, chercher plus largement que le dossier `__tests__` conventionnel (`find frontend -iname "*ComponentName*"` sur tout `frontend/`, pas juste `src/views/__tests__/`) — certains composants plus anciens ont leurs tests sous `frontend/tests/unit/`.

## Documentation mise à jour

- `docs/user/calibre-integration.md` : mention du tri "Dernières lectures" comme tri par défaut, avec l'explication des 3 groupes.

## Issues de suivi créées (à traiter plus tard)

- **#276** — Playwright MCP ne fonctionne plus dans certaines sessions Claude Code (sandbox sans PID namespace disponible) : investiguer si `@playwright/mcp` peut être configuré avec `--no-sandbox`, ou documenter officiellement le contournement Chrome CLI direct (déjà utilisé pour vérifier visuellement #273 et #274 — voir mémoire système `playwright_mcp_sandbox_limitation`).
- **#277** — Rendre les tuiles de `/calibre` cliquables vers la fiche livre LMELP quand un matching MongoDB existe (réutiliser `CalibreMatchingService`, exposer `mongo_livre_id` sur `/api/calibre/books` comme déjà fait sur `/api/calibre/onkindle`).

## Fichiers modifiés

- `src/back_office_lmelp/models/calibre_models.py`
- `src/back_office_lmelp/services/calibre_service.py`
- `frontend/src/views/CalibreLibrary.vue`
- `tests/test_calibre_service.py`
- `frontend/tests/unit/CalibreLibrary.test.js`
- `docs/user/calibre-integration.md`
