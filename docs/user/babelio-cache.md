```markdown
# Cache Babelio (utilisateur)

Ce projet utilise un mécanisme de cache au niveau backend pour améliorer les temps de chargement lors de la validation bibliographique via Babelio.

Quand cela vous concerne (utilisateur) :
- Si vous constatez des suggestions qui semblent obsolètes (Babelio a mis à jour ses données), vous pouvez demander à l'administrateur de vider le cache.
- En développement, certaines réponses peuvent provenir du cache et non d'une requête en direct ; cela peut expliquer des différences entre environnements.

Actions simples :
- Pour obtenir des résultats « à jour », demander à l'administrateur :
  - Supprimer le contenu du dossier `data/processed/babelio_cache`
  - Redémarrer le backend

Remarques :
- Le cache aide surtout en développement et sur des flux répétitifs (ex : navigation rapide entre épisodes).
- Ne considérez pas les résultats stockés en cache comme immuables ; ce sont des valeurs de performance.

Variables d'environnement utiles
-- `BABELIO_CACHE_LOG` : active les logs détaillés du cache (HIT/MISS/WROTE). Valeurs reconnues : `1`, `true`.
  - Exemple :

```bash
export BABELIO_CACHE_LOG=1
./scripts/start-dev.sh
```

-- `BABELIO_CACHE_ENABLED` : contrôle si le backend attache le cache au démarrage. Par défaut activé. Mettre `0` ou `false` pour démarrer sans cache.
  - Exemple :

```bash
export BABELIO_CACHE_ENABLED=0
./scripts/start-dev.sh
```

-- `BABELIO_CACHE_DIR` : chemin du dossier de cache (par défaut `data/processed/babelio_cache`).
  - Exemple :

```bash
export BABELIO_CACHE_DIR=/tmp/babelio_cache_dev
./scripts/start-dev.sh
```

Si vous n'êtes pas administrateur ou si vous n'avez pas accès au serveur, demandez à l'équipe technique d'effectuer ces opérations.
```
