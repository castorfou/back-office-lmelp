# Issue #347 — Tableau d'avis critiques non rendu (ligne de séparation absente)

## Problème

Page Génération d'Avis Critiques : le résumé de l'épisode du 21/07/2024
(`avis_critiques 6af86cd6b0dd9fa95301bd8f`) s'affichait en texte continu. Ses deux tableaux
n'avaient pas de ligne `|---|...|` sous l'en-tête, et `marked` ne reconnaît pas un tableau sans
elle.

## Cause réelle (trouvée en base, pas dans l'issue)

- Le `summary_phase1` du même document avait bien ses séparateurs : **c'est la Phase 2**
  (correction des noms) qui les a supprimés en compactant les tableaux (`| Auteur|Titre|...`).
- `_validate_markdown_format()` ne vérifiait que la présence d'un `|` (Check 2) : la sortie
  Phase 2 a été acceptée telle quelle.
- Sur 189 `avis_critiques`, un seul avait des tableaux sans séparateur (l'autre « sans
  séparateur » est un placeholder « Réponse de l'IA tronquée » sans tableau). Pas de
  migration : le document a été régénéré depuis l'UI.

## Correction

- `src/back_office_lmelp/utils/markdown_tables.py` : `ensure_table_separators(markdown)`,
  fonction pure et idempotente. L'en-tête est la première ligne d'un bloc de lignes de
  tableau (commençant par `|`, ou séparateur) ; s'il n'est pas suivi d'un séparateur
  (`|---|`, `|:-:|`, `---|---`…), elle insère `|---|` × nombre de colonnes de l'en-tête
  (cellules vides internes comptées).
- `src/back_office_lmelp/services/avis_critiques_generation_service.py` : appliquée **avant
  la validation** dans `generate_summary_phase1()` (après le contrôle `finish_reason`) et dans
  `enhance_summary_phase2()`. La Phase 2 n'est donc pas rejetée (repli sur Phase 1) pour un
  séparateur manquant : ses corrections de noms sont gardées.
- Pas de nouveau check de validation : la réparation précède toujours la validation, il ne
  pourrait jamais échouer.
- Effet de bord : les deux `# type: ignore[no-any-return]` sur `return summary` /
  `return summary_phase2` sont devenus inutiles (la valeur est maintenant un `str` typé),
  supprimés car mypy (`warn_unused_ignores`) les refuse.

## Tests

- Fixture réelle exportée de MongoDB : `tests/fixtures/summary_without_table_separators.py`
  (`SUMMARY_WITHOUT_TABLE_SEPARATORS_20240721`).
- `tests/test_avis_critiques_generation_service.py::TestTableSeparators` : client mocké
  (`_chat_completion`) renvoyant la fixture en Phase 1 et en Phase 2 → chaque en-tête (8 puis
  6 colonnes) suivi d'un séparateur de même largeur ; en Phase 2, le nom corrigé est conservé.
- `tests/test_markdown_tables.py` : insertion, cellules vides, séparateurs existants
  conservés, plusieurs tableaux, idempotence, texte sans tableau.
- `tests/test_avis_extraction_service.py::TestExtractionWithoutTableSeparators` :
  `AvisExtractionService` lisait déjà les tableaux sans séparateur (en-tête reconnu par
  `^\s*\|\s*Auteur\s*\|` en section 1, Auteur+Titre+Éditeur en section 2) ; verrouillé avec
  et sans réparation : 4 livres, 15 avis, 5 coups de cœur.

## Leçon

Avant de corriger un résumé LLM mal formé, comparer `summary` et `summary_phase1` en base :
cela désigne la phase fautive. Une dérive de format purement syntaxique se répare de façon
déterministe avant validation, plutôt que par un rejet qui ferait perdre le travail de la
phase.
