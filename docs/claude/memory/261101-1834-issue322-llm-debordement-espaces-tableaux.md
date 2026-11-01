# Issue #322 - Débordement d'espaces du LLM en génération d'avis critiques

**Date** : 2026-11-01
**Issue** : [#322](https://github.com/castorfou/back-office-lmelp/issues/322)
**Branche** : `322-llm-génération-davis-critiques-echoue`

## Problème

La génération de l'épisode du 01/11/2026 (`6ae7497087efd8d343531f86`) échouait à chaque
tentative : réponse de ~1 019 294 caractères, rejetée par `_validate_markdown_format`,
erreur 500.

## Cause

Le LLM (`gpt-4.1-2025-04-14`) aligne les colonnes du tableau, puis écrit 1 019 136 espaces
d'affilée dans la ligne d'en-tête (ligne 3), jusqu'à `max_tokens=8000`
(`finish_reason=length`, environ 127 caractères/token).

- Reproduit 2 fois sur 2 sur la transcription réelle : ce n'est pas aléatoire.
- La transcription est saine (français, 50 977 caractères, sans répétition). Le cas du
  16/10/2016 (#181) avait la même signature et avait été attribué à une transcription
  contaminée : la transcription n'est donc pas la seule explication possible.
- Le retry renvoyait la même requête à `temperature=0.1` et reproduisait l'échec.

## Correctif

Fichier : `src/back_office_lmelp/services/avis_critiques_generation_service.py`

- `TABLE_FORMAT_RULE` : consigne anti-alignement dans les prompts Phase 1 et Phase 2.
- `finish_reason == "length"` : `ValueError` en Phase 1, repli sur Phase 1 en Phase 2.
- `_describe_llm_output()` : taille, plus longue suite d'espaces et sa ligne, dans l'erreur
  et les logs, sans mode debug.
- `PHASE1_ATTEMPT_TEMPERATURES = (0.1, 0.3)` : le retry change la température.
- `MAX_OUTPUT_TOKENS = 8000` conservé : le plus long des 186 résumés locaux fait 7 528
  caractères.

Tests : classe `TestTruncatedLlmResponse` dans
`tests/test_avis_critiques_generation_service.py`, mocks construits avec le vrai type
`ChatCompletion` du SDK OpenAI.

## Mesures (10 appels Azure, Phase 1)

| Variante | Appels | Résultat | Avis extraits |
|---|---|---|---|
| Code d'origine | 2 | `length`, 1 Mo | aucun |
| Consigne | 3 | `stop`, ~5 700 caractères | 24 |
| Consigne + température 0.3 | 1 | `stop`, 5 987 caractères | 24 |
| Consigne + température 0.3 + `frequency_penalty` 0.5 | 2 | `stop` | 11 et 14 |
| `frequency_penalty` 0.5 seul | 1 | `stop`, 1 016 espaces restants | non mesuré |
| Témoin épisode du 06/09/2026 | 1 | `stop` | 29 (25 pour le résumé stocké) |

Test utilisateur complet en local après restauration d'un dump de prod : Phases 1 et 2 en
21 s, noms corrigés par la Phase 2, 24 avis extraits.

## Apprentissages

- **Lire `finish_reason`** : une réponse coupée reste souvent du markdown bien formé.
- **Ne pas supprimer les espaces après coup** : le débordement survient avant les lignes
  du tableau, il n'y a rien à récupérer.
- **Mesurer contre le consommateur aval, pas seulement la validation** :
  `frequency_penalty` arrête le débordement et passe `_validate_markdown_format`, mais
  produit `**Nom** :` ou `**Nom:**`, que `_parse_section1_critic_entry` ne reconnaît pas.
  Environ la moitié des avis disparaissent sans erreur.
- **Un stub vide donne un faux vert** : `"" in prompt` est toujours vrai. Tester le texte
  attendu, pas la constante.
- **`pytest` charge `.env`** : `skip_if_no_azure` ne saute pas en local et
  `test_generate_summary_episode_2017_04_09_should_succeed` fait un vrai appel Azure.
- **La transcription d'un épisode s'obtient sans dump** : `GET /api/episodes/{id}`.
  `curl -o` écrit aussi le corps d'un 404 : un `ID` vide écrase le fichier de sortie.

## Risques restants

- `_validate_markdown_format` ne vérifie pas le format `**Nom**:` : une dérive de format
  passe la validation et l'extraction perd ces avis sans erreur.
- La consigne réduit le risque de débordement sans le supprimer. Le rejet par
  `finish_reason` garantit alors une erreur explicite plutôt qu'un résumé tronqué.
- La Phase 2 peut retirer tous les espaces autour des `|` (`|Auteur|Titre|`) : sans effet,
  les lecteurs nettoient les cellules avec `strip()`.
