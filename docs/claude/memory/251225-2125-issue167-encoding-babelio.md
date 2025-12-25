# Issue #167: Correction encoding Babelio (ISO-8859-1 déclaré mais Windows-1252 réel)

**Date**: 2025-12-25
**Issue**: #167 - [bug] encoding incorrect lors recuperation donnees babelio
**Branche**: `167-bug-encoding-incorrect-lors-recuperation-donnees-babelio`
**Statut**: Résolu ✅

## Problème

Les caractères spéciaux français (é, è, à, ê, ô, œ, ï, tiret cadratin –) étaient mal décodés lors de la récupération de données depuis Babelio.

### Symptômes observés

- Erreur: `'utf-8' codec can't decode byte 0x96 in position 805: invalid start byte`
- Les caractères spéciaux n'étaient pas préservés correctement
- Le byte `0x96` (tiret cadratin en Windows-1252) causait des erreurs de décodage

## Cause racine

**Mismatch entre encoding déclaré et encoding réel** :

- Babelio **déclare** dans ses en-têtes HTTP: `charset=ISO-8859-1`
- Babelio **utilise réellement**: Windows-1252 (cp1252)

### Différence technique

**ISO-8859-1** (Latin-1) :
- Plage 0x00-0x7F: ASCII standard
- Plage 0x80-0x9F: **caractères de contrôle** (NON IMPRIMABLES)
- Plage 0xA0-0xFF: caractères latins étendus

**Windows-1252** (CP1252) :
- Plage 0x00-0x7F: ASCII standard
- Plage 0x80-0x9F: **caractères imprimables additionnels** (ex: tiret cadratin 0x96, œ, etc.)
- Plage 0xA0-0xFF: caractères latins étendus (identique à ISO-8859-1)

**Conséquence** : Le byte `0x96` est :
- Un tiret cadratin (–) en Windows-1252 ✅
- Un caractère de contrôle invalide en ISO-8859-1 ❌
- Complètement invalide en UTF-8 ❌

## Solution implémentée

### 1. Fichiers modifiés

**`src/back_office_lmelp/services/babelio_service.py`** : 5 emplacements corrigés

Ajout de `encoding='cp1252'` à tous les appels `await response.text()` :

1. **Ligne 280** (recherche AJAX JSON) :
   ```python
   # Utiliser Windows-1252 car Babelio déclare ISO-8859-1 mais utilise
   # des caractères Windows-1252 comme le tiret cadratin (0x96) (Issue #167)
   text_content = await response.text(encoding='cp1252')
   ```

2. **Ligne 703** (scraping titre complet) :
   ```python
   html = await response.text(encoding='cp1252')
   ```

3. **Ligne 770** (scraping éditeur) :
   ```python
   html = await response.text(encoding='cp1252')
   ```

4. **Ligne 1021** (extraction URL auteur) :
   ```python
   html = await response.text(encoding='cp1252')
   ```

5. **Ligne 1118** (extraction nom auteur) :
   ```python
   html = await response.text(encoding='cp1252')
   ```

### 2. Tests créés

**`tests/test_babelio_encoding.py`** (nouveau fichier) : 5 tests avec fixtures RÉELLES

Caractéristiques :
- Utilise des fixtures extraites de **vraies** réponses Babelio (conformément à `CLAUDE.md`)
- Sources de données :
  - API AJAX: `curl -X POST https://www.babelio.com/aj_recherche.php -d '{"term":"Leïla Slimani"}'`
  - Page HTML: `https://www.babelio.com/livres/Slimani-Regardez-nous-danser--Le-Pays-des-autres-2/1853023`

Tests couverts :
1. `test_search_ajax_preserves_special_characters()` - Préservation caractères dans API JSON
2. `test_fetch_full_title_from_html_preserves_special_characters()` - Titre complet avec tiret cadratin
3. `test_fetch_publisher_from_html_preserves_special_characters()` - Éditeur "À vue d'œil" (accent + ligature)
4. `test_fetch_author_url_from_html_preserves_special_characters()` - URL auteur avec "Leïla" (tréma)
5. `test_scrape_author_name_from_html_preserves_special_characters()` - Nom auteur "Leïla Slimani"

Caractères testés :
- `ï` (tréma) dans "Leïla"
- `–` (tiret cadratin 0x96) dans "Regardez-nous danser – Le Pays des autres"
- `À` (accent grave majuscule) dans "À vue d'œil"
- `œ` (ligature) dans "À vue d'œil"
- `é`, `è`, `à` (accents divers)

### 3. Tests existants modifiés

**`tests/test_babelio_newlines_sanitization.py`** :

Modification de `MockResponse.text()` pour accepter le paramètre `encoding` :

```python
async def text(self, encoding=None):
    # Support for encoding parameter added in Issue #167
    return self._html
```

## Approche TDD suivie

1. **RED** : Créer 5 tests avec fixtures réelles → Tests échouent (caractères mal décodés)
2. **Tentative 1** : Essai avec `encoding='utf-8'` → Échec (`byte 0x96` invalide)
3. **Investigation** : Analyse headers HTTP et code source HTML → Découverte Windows-1252
4. **GREEN** : Correction avec `encoding='cp1252'` → Tous les tests passent (763 passed, 23 skipped)
5. **Validation utilisateur** : Test en conditions réelles → Confirmé fonctionnel

## Apprentissages clés

### 1. Ne jamais faire confiance aux headers HTTP déclarés

**Problème** : Les serveurs peuvent déclarer un charset mais en utiliser un autre.

**Babelio déclare** :
```
Content-Type: text/html; charset=ISO-8859-1
```

**Mais utilise réellement** : Windows-1252 (caractères dans 0x80-0x9F)

**Leçon** : Toujours tester avec des données réelles contenant des caractères spéciaux.

### 2. Windows-1252 vs ISO-8859-1 : différence critique

**Confusion fréquente** : Les deux encodings sont identiques SAUF dans la plage 0x80-0x9F.

**Windows-1252** ajoute des caractères imprimables utiles :
- `0x91`, `0x92` : guillemets simples typographiques (', ')
- `0x93`, `0x94` : guillemets doubles typographiques (", ")
- `0x96` : tiret cadratin (–)
- `0x97` : tiret long (—)

**ISO-8859-1** : Ces positions contiennent des caractères de contrôle non imprimables.

**Impact** : Si on décode du Windows-1252 comme de l'ISO-8859-1, on obtient des caractères étranges au lieu des caractères attendus.

### 3. Importance des fixtures RÉELLES dans les tests

**Erreur initiale** : Vouloir inventer des mocks sans vérifier les vraies données.

**Approche correcte** (selon `CLAUDE.md`) :
1. Récupérer les vraies réponses API avec `curl`
2. Copier-coller les structures JSON exactes
3. Utiliser des extraits de vraies pages HTML
4. Tester avec les vrais caractères problématiques

**Avantage** : Les tests détectent les vrais problèmes (byte 0x96, ligatures, etc.) au lieu de passer avec des données inventées.

### 4. Pattern TDD pour problèmes d'encoding

**Workflow efficace** :

1. **Capturer vraies données** :
   ```bash
   curl -X POST https://www.babelio.com/aj_recherche.php -d '{"term":"Leïla Slimani"}'
   curl -s https://www.babelio.com/livres/Slimani-Regardez-nous-danser--Le-Pays-des-autres-2/1853023
   ```

2. **Créer fixtures avec caractères problématiques** :
   - Caractères accentués : é, è, à, ô, ê
   - Ligatures : œ, æ
   - Trémas : ï, ü
   - Ponctuation typographique : –, —, ', ', ", "

3. **Écrire tests RED** avec assertions strictes :
   ```python
   assert title == "Regardez-nous danser – Le Pays des autres, 2"  # Tiret cadratin
   assert publisher == "À vue d'œil"  # Accent grave + ligature
   assert author == "Leïla Slimani"  # Tréma
   ```

4. **Itérer sur encodings** : UTF-8 → ISO-8859-1 → Windows-1252 → GREEN

5. **Valider avec utilisateur** sur vraies données Babelio

### 5. aiohttp response.text() : paramètre encoding critique

**Sans encoding explicite** :
```python
html = await response.text()  # Utilise charset des headers HTTP (ISO-8859-1) → ERREUR
```

**Avec encoding explicite** :
```python
html = await response.text(encoding='cp1252')  # Force Windows-1252 → OK
```

**Documentation aiohttp** : `text(encoding=None)` - Si `None`, utilise le charset des headers HTTP.

**Leçon** : Toujours spécifier l'encoding explicitement quand on sait que les headers sont incorrects.

## Commandes de validation

### Tests backend
```bash
PYTHONPATH=/workspaces/back-office-lmelp/src pytest tests/test_babelio_encoding.py -v
```

Résultat : 5/5 tests passent

### Couverture globale
```bash
PYTHONPATH=/workspaces/back-office-lmelp/src pytest tests/ -v
```

Résultat : 763 passed, 23 skipped

### Linting et formatage
```bash
ruff check . --output-format=github
ruff format .
mypy src/
```

Résultat : Aucune erreur

## Documentation mise à jour

Fichiers concernés :
- `CLAUDE.md` : Pattern déjà documenté ("Create mocks from real API responses")
- Tests : Documentation inline dans `test_babelio_encoding.py` expliquant le problème

## Impact

**Fonctionnalités affectées** :
- Recherche d'auteurs/livres sur Babelio
- Extraction de titres complets
- Extraction de noms d'éditeurs
- Extraction de noms d'auteurs
- Toute opération de scraping Babelio

**Avant** : Caractères mal décodés ou erreurs de décodage
**Après** : Tous les caractères français préservés correctement

## Références

- Issue #167: https://github.com/castorfou/back-office-lmelp/issues/167
- Branche: `167-bug-encoding-incorrect-lors-recuperation-donnees-babelio`
- Page Babelio testée: https://www.babelio.com/livres/Slimani-Regardez-nous-danser--Le-Pays-des-autres-2/1853023
- Différences ISO-8859-1 vs Windows-1252: https://en.wikipedia.org/wiki/Windows-1252
