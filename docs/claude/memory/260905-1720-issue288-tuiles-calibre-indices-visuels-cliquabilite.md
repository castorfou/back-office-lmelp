# Issue #288 — Indices visuels de cliquabilité sur les tuiles Calibre

## Contexte

Suite à l'issue #277 (tuiles cliquables uniquement si `book.mongo_livre_id` existe), rien ne différenciait visuellement une tuile cliquable d'une autre avant de cliquer et de s'en rendre compte.

## Fix n°1 — Liseret bleu au survol (demande initiale)

Cause : dans `frontend/src/views/CalibreLibrary.vue`, `.book-card:hover` (transform + shadow) s'appliquait à **toutes** les tuiles indistinctement, seul `cursor: pointer` différait sur `.book-card.clickable` — imperceptible avant de bouger la souris dessus.

Fix : repris exactement le pattern déjà utilisé sur la page d'accueil (`frontend/src/views/Dashboard.vue:887-896`, classe `.function-card.clickable`), cité par l'utilisateur comme référence :
```css
.book-card.clickable {
  cursor: pointer;
  border: 2px solid transparent;  /* évite un saut de layout au hover */
}
.book-card.clickable:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(0,0,0,0.15);
  border-color: #667eea;
}
```
L'effet hover (transform/shadow) a été retiré de `.book-card:hover` générique — les tuiles non cliquables restent maintenant totalement statiques au survol.

**Vérification** : pas de TDD applicable (CSS pur, classe `clickable` déjà testée en JS depuis #277) — vérifié par mesures DOM directes via Playwright MCP (`getComputedStyle` avant/après hover sur une tuile cliquable et une non cliquable), conformément à la règle CLAUDE.md "Playwright MCP — Vérification visuelle".

## Fix n°2 — Tag date d'émission en rose clair (demande complémentaire, même session)

Demande ajoutée en cours de session : les tags `lmelp_YYMMDD` (date d'émission, ex: `lmelp_260320` — voir `src/back_office_lmelp/services/mongodb_service.py:1224`) sont un bon indicateur (pas garanti à 100%) qu'un livre a été discuté au Masque et la Plume, donc potentiellement cliquable. Demande : fond rose clair au lieu du gris standard pour ce tag spécifique.

**Scope volontairement restreint** (clarifié avec l'utilisateur avant implémentation) : uniquement le tag date, **pas** les tags de critique coup de cœur (`lmelp_prenom_nom`, ex: `lmelp_arnaud_viviant`) ni les autres tags — ces deux formats `lmelp_` coexistent (voir `mongodb_service.py:1208-1240`), il ne fallait pas les confondre.

Implémentation :
- `isLmelpDateTag(tag)` dans `CalibreLibrary.vue` : `/^lmelp_\d{6}$/.test(tag)` — pattern strict qui exclut `lmelp_prenom_nom` (lettres, pas que des chiffres après le préfixe).
- Classe `tag-lmelp-date` posée conditionnellement dans le template sur chaque tag.
- CSS : `background: #fde3ef; color: #b23b6f;` (texte assombri pour garder un bon contraste sur fond rose clair, plutôt que le `#666` gris d'origine).

**TDD suivi** : 4 tests RED→GREEN dans `frontend/tests/unit/CalibreLibrary.test.js` (détection regex sur tag date/critique/normal + classe appliquée uniquement au bon tag).

**Piège de mock rencontré en écrivant le test** : le nouveau bloc de test utilisait un mock `getStatus.mockResolvedValue({ status: 'ok', book_count: 1 })` inventé, différent du format réel attendu par le composant (`{ available: true, library_path, total_books }`, vu dans le bloc de test existant `Clickable tiles (Issue #277)` juste après). Résultat : `findAll('.tag')` retournait un tableau vide (mounted() ne se déroulait pas normalement) — pas d'erreur explicite, juste un DOM vide, jusqu'à debug par `console.log` temporaire. **Leçon** : toujours copier le format de mock d'un bloc de test existant et fonctionnel du même composant plutôt que d'en inventer un, même pour un champ qui semble anodin (cf. règle CLAUDE.md "Create mocks from real API responses").

**Vérification finale** : suite frontend complète GREEN (703 passed, +4 vs avant) + vérification Playwright sur données réelles (`lmelp_260823` en rose `#fde3ef`/`#b23b6f`, `lmelp_arnaud_viviant` et tags normaux restés gris `#f0f0f0`).

## Fichiers modifiés

- `frontend/src/views/CalibreLibrary.vue` — CSS hover scopé + `border: 2px solid transparent`/`border-color: #667eea` ; méthode `isLmelpDateTag()` + classe `tag-lmelp-date` + CSS rose clair
- `frontend/tests/unit/CalibreLibrary.test.js` — 4 nouveaux tests (`Emission date tag styling (Issue #288)`)
