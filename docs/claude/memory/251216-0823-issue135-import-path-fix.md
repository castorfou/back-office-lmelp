# Issue #135 - Fix Import Path in migrate_url_babelio.py

**Date**: 2025-12-16
**Issue**: [#135 - Bug: impossible de lancer la liaison auto babelio](https://github.com/castorfou/back-office-lmelp/issues/135)
**Statut**: Résolu

## Symptôme

Erreur `No module named 'migrate_url_babelio'` lors du clic sur le bouton "Lancer la liaison automatique" dans l'interface frontend.

## Analyse Racine

Le fichier `scripts/migration_donnees/migrate_url_babelio.py:30` calculait incorrectement le chemin vers le répertoire `src` :

```python
# Code incorrect (ligne 30)
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
```

**Problème** : Ce code produisait le chemin **incorrect** :
- Devcontainer : `/workspaces/back-office-lmelp/scripts/src` ❌
- Docker : `/app/scripts/src` ❌

Au lieu du chemin **attendu** :
- Devcontainer : `/workspaces/back-office-lmelp/src` ✅
- Docker : `/app/src` ✅

### Pourquoi ça marchait parfois ?

L'import fonctionnait quand :
1. Le package était installé en mode éditable (`uv pip install -e .`)
2. La variable `PYTHONPATH=/workspaces/back-office-lmelp/src` était définie
3. L'environnement virtuel ajoutait automatiquement le bon chemin

**Mais ça échouait dans certaines conditions** :
- Premier démarrage sans réinstallation du package
- Environnements où `PYTHONPATH` n'était pas propagé correctement
- Après redémarrage de services longue durée (cache Python)

### Différence entre Devcontainer et Docker Production

**Devcontainer** (`.devcontainer/devcontainer.json:16`) :
- `PYTHONPATH` défini explicitement : `"PYTHONPATH": "/workspaces/back-office-lmelp/src"`
- Package installé en mode éditable par `postCreateCommand.sh`

**Dockerfile Production** (`docker/build/backend/Dockerfile:37`) :
- `ENV PYTHONPATH=/app/src`
- `uv sync --frozen --no-dev` (PAS d'installation éditable)
- Le code source est simplement copié dans `/app/src/`

Le problème était que le script comptait uniquement sur `PYTHONPATH`, mais le calcul de chemin incorrect aurait pu causer des problèmes dans des environnements variés.

## Solution

Correction du calcul du chemin en ajoutant un niveau de `parent` supplémentaire :

```python
# Code corrigé (ligne 32)
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
```

Cette correction fonctionne dans **tous les environnements** :

| Environnement | Script Path | Calcul Corrigé | Résultat |
|---------------|-------------|----------------|----------|
| Devcontainer | `/workspaces/back-office-lmelp/scripts/migration_donnees/migrate_url_babelio.py` | `parent.parent.parent / "src"` | `/workspaces/back-office-lmelp/src` ✅ |
| Docker | `/app/scripts/migration_donnees/migrate_url_babelio.py` | `parent.parent.parent / "src"` | `/app/src` ✅ |

## Fichiers Modifiés

- `scripts/migration_donnees/migrate_url_babelio.py:30-32` - Correction du calcul du chemin

## Tests de Validation

1. ✅ **Import direct** : Le module peut être importé sans erreur
2. ✅ **Sans PYTHONPATH** : L'import fonctionne même si `PYTHONPATH` n'est pas défini
3. ✅ **Suite de tests complète** : 729 tests passés, 22 skipped
4. ✅ **Linting et formatage** : Ruff check et format OK
5. ✅ **Test utilisateur** : Bouton "Lancer la liaison automatique" fonctionne en local

## Leçons Apprises

### 1. Calculs de Chemins Relatifs

Quand un script calcule des chemins relatifs avec `Path(__file__).parent`, toujours vérifier :
- Où le script est situé dans la structure
- Combien de niveaux `parent` sont nécessaires pour atteindre la racine
- Que la structure est identique entre tous les environnements (dev, Docker, CI/CD)

**Méthode de vérification** :
```python
from pathlib import Path
script_path = Path(__file__)
print(f"Script: {script_path}")
print(f"parent: {script_path.parent}")
print(f"parent.parent: {script_path.parent.parent}")
print(f"parent.parent.parent: {script_path.parent.parent.parent}")
```

### 2. Installation du Package en Mode Éditable vs Production

**Mode éditable** (`uv pip install -e .`) :
- Ajoute automatiquement `src/` à `sys.path`
- Idéal pour le développement
- Cache certains problèmes de chemins

**Mode production** (`uv sync --frozen --no-dev`) :
- N'installe pas le package en mode éditable
- Compte uniquement sur `PYTHONPATH` ou calculs de chemins explicites
- Révèle les problèmes de chemins cachés en développement

### 3. Robustesse des Imports

**Pattern à éviter** :
```python
# Dépend de PYTHONPATH ou installation éditable
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))  # ❌ Fragile
```

**Pattern recommandé** :
```python
# Calcul explicite du chemin absolu vers src/
src_path = Path(__file__).resolve().parent.parent.parent / "src"
if src_path.exists():
    sys.path.insert(0, str(src_path))
else:
    raise ImportError(f"Cannot find src directory at {src_path}")
```

Ou mieux encore : **Ne pas modifier `sys.path` dans les scripts** et utiliser :
- `PYTHONPATH` dans les variables d'environnement
- Installation correcte du package
- Imports relatifs quand approprié

### 4. Tests d'Import dans Différents Environnements

Pour un script critique utilisé par le backend, toujours tester :

1. **Sans PYTHONPATH** :
   ```bash
   env -u PYTHONPATH python3 -c "from migrate_url_babelio import ..."
   ```

2. **Avec sys.path nettoyé** :
   ```python
   sys.path = [p for p in sys.path if 'project' not in p]
   ```

3. **Simulation Docker** :
   - Vérifier que `parent.parent.parent` pointe vers `/app/src` (pas `/app/scripts/src`)

### 5. Debug d'Erreurs Intermittentes

Quand une erreur "fonctionne parfois" :
- ✅ Vérifier les variables d'environnement (`PYTHONPATH`)
- ✅ Vérifier si package installé en mode éditable
- ✅ Vérifier `sys.path` au moment de l'échec
- ✅ Tester dans un environnement "propre" (nouveau container)
- ✅ Comparer environnements qui marchent vs qui échouent

## Commandes Utiles

```bash
# Vérifier que l'import fonctionne
python3 -c "
import sys
from pathlib import Path
scripts_path = Path('/workspaces/back-office-lmelp/scripts/migration_donnees')
sys.path.insert(0, str(scripts_path))
from migrate_url_babelio import get_all_authors_to_complete
print('✅ Import réussi')
"

# Tester sans PYTHONPATH
env -u PYTHONPATH python3 -c "..."

# Vérifier sys.path actuel
python3 -c "import sys; [print(p) for p in sys.path if 'back-office' in p]"
```

## Références

- Issue #135 : https://github.com/castorfou/back-office-lmelp/issues/135
- Commentaire d'analyse : https://github.com/castorfou/back-office-lmelp/issues/135#issuecomment-3653731046
- Code corrigé : `scripts/migration_donnees/migrate_url_babelio.py:30-32`
