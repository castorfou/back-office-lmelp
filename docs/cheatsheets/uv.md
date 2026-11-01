## emplacement du venv

Le venv actif est `/tmp/venv` (`echo $VIRTUAL_ENV`). Il est recréé à chaque rebuild depuis `uv.lock`, et au démarrage s'il manque : déclarez chaque package avec `uv add --active`, sinon il disparaît au rebuild suivant. La recréation installe `uv.lock` sans le modifier : après une modification à la main de `pyproject.toml`, lancez `uv lock` et commitez `uv.lock`.

## installation package

```bash
uv add --active pandas # (1)
```

1.  le `--active` est essentiel pour utiliser l'env actif, sinon creation d'un nouveau venv
