# Issue #411 — Un livre déjà en base n'est plus recréé sous un titre Babelio plus complet

## Problème

Reprise de l'émission du 28/06/2015 (#408) : la revalidation dans Livres et Auteurs a créé
une seconde fiche « Quand vous viendrez me voir aux Antipodes : Lettres à Pierre Boncenne »
à côté de « Quand vous viendrez me voir aux antipodes », avec la **même URL Babelio**
(`…/Leys-Quand-vous-viendrez-me-voir-aux-Antipodes--Lettre/720681`) et le même auteur. La page
Émissions affichait « Livres cités (10) ≠ Livres liés (11) ». Corrigé en prod par la fusion de
Gestion des doublons (onglet Livres).

Cause : `MongoDBService.create_book_if_not_exists()` ne cherchait un livre existant que par
titre normalisé + auteur (`normalize_for_matching`, #267). Un titre Babelio plus complet
(sous-titre, « : Lettres à … ») ne correspondait plus. C'est le pendant côté livres du doublon
d'auteurs corrigé par #406 (`_merge_if_author_url_taken()`).

## Correctif

`src/back_office_lmelp/services/mongodb_service.py` :

- `create_book_if_not_exists()` (`:2123`) : si `book_data` porte une `url_babelio`, recherche
  d'abord un livre qui a déjà cette URL (`:2144`, regex ancrée + `re.escape`, option `i`, comme
  la détection des doublons). S'il existe, il est réutilisé ; sinon recherche par titre comme
  avant. Sans URL : comportement inchangé.
- `_reuse_existing_book()` (`:2076`) : bloc « livre existant trouvé » extrait et partagé par les
  deux recherches (`$addToSet` épisodes / avis_critiques, migration `editeur_id`). Il ne touche
  pas au titre : chaque appelant décide (le chemin `verified` de `set-validation-results`
  renomme déjà avec le titre Babelio validé, la validation manuelle garde le titre existant).
- Sur correspondance par URL, la référence du livre est ajoutée à **l'auteur du livre
  existant**, pas à l'auteur passé : ce dernier peut être un doublon créé par son nom, que
  l'enrichissement fusionnera ensuite (#406).

Appelants qui passent une URL : chemin `verified` de `set-validation-results` (`app.py`) et
`handle_book_validation()` (`collections_management_service.py`). `auto_process_verified_books()`
n'en passe pas.

## Tests

`tests/test_create_book_dedup_by_url.py`, sur un `MongoDBService` branché sur mongomock
(épisodes en String comme en base) : cas réel du 28/06/2015, URL de casse différente, auteur
passé doublon (référence gardée sur l'auteur du livre), sans URL → nouveau livre. Les 110 tests
existants qui touchent `create_book_if_not_exists` restent verts.

## Test utilisateur (dev)

Les émissions du 21/01/2018 et du 29/03/2026 (#408) étaient déjà dans le Mongo de dev (base
restaurée depuis la prod) avec leur ligne regroupée. Régénération, revalidation, ré-extraction :
**0 groupe de livres en doublon par URL**.

## Constats en marge (hors #411)

- **« X suivi de Y » = un seul volume** : au 21/01/2018, *La chanson de Madame Rosenfeld / J'ai
  tué Barbara* est un seul livre Babelio (« J'ai tué Barbara suivi de La Chanson de Madame
  Rosenfelt »). La règle « un livre = une ligne » (#405) l'a séparé à tort. Traitement : valider
  la suggestion sur une ligne, « 🗑️ Supprimer » l'autre (titre écarté durablement, #380). Si les
  deux lignes sont validées, #411 évite la seconde fiche, mais deux avis du même critique
  pointent alors le même livre. Pas d'issue ouverte (cas rare, corrigé en un clic).
- **URL Babelio absente d'une suggestion vérité terrain** : *L'enfant perdue (L'Amie
  prodigieuse, vol. 4)* → suggestion « L’enfant perdue » (`source: 'ground_truth'`) sans URL,
  car `_babelioUrlIfSameTitle()` (`frontend/src/services/BiblioValidationService.js`, règle de
  #341 contre les homonymes) exige l'égalité stricte avec le titre Babelio « L'amie
  prodigieuse, tome 4 : L'enfant perdue ». Issue #412 ouverte (accepter l'URL quand l'auteur
  correspond et que le titre Babelio finit par « : *titre suggéré* »). Contournement : coller
  l'URL dans la modale.
