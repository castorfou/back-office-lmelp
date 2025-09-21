```markdown
# Babelio disk cache (développeur)

Ce document décrit l'implémentation et l'utilisation du cache disque pour les recherches Babelio.

Emplacement
- Par défaut : `data/processed/babelio_cache` (un fichier JSON par clé de recherche).

Comportement
- Le backend installe et attache automatiquement `BabelioCacheService` au service `babelio_service` au démarrage, sauf si `BABELIO_CACHE_ENABLED` est mis à `0`/`false`.
- TTL par défaut : 24 heures (configurable lors de l'instanciation `BabelioCacheService(cache_dir=..., ttl_hours=24)`).
- Le service écrit deux clés pour chaque écriture : la clé originale (terme tel que fourni) et une clé normalisée (`term.strip().lower()`) pour améliorer le taux de hits.

Variables d'environnement utiles
- `BABELIO_CACHE_ENABLED` (par défaut : activé) : définir `0` ou `false` pour démarrer sans cache.
- `BABELIO_CACHE_DIR` : chemin vers le dossier du cache (défaut : `data/processed/babelio_cache`).
- `BABELIO_CACHE_LOG` (par défaut : activé pour dev) : si défini (`1`/`true`), active des logs informatifs (INFO) montrant HIT/MISS/WROTE.

Exemples
```bash
# Activer logs et démarrer
export BABELIO_CACHE_LOG=1
./scripts/start-dev.sh

# Désactiver le cache
export BABELIO_CACHE_ENABLED=0
./scripts/start-dev.sh

# Spécifier un dossier de cache personnalisé
export BABELIO_CACHE_DIR=/tmp/babelio_cache_dev
./scripts/start-dev.sh
```

Logs attendus (exemples)
- `[BabelioCache] HIT (orig) key='Agnès Michaud' items=1 ts=1758460387.9464464`
- `[BabelioCache] MISS keys=(orig='Houllebeck', norm='houllebeck')`
- `[BabelioCache] WROTE keys=(orig='Houllebeck', norm='houllebeck') items=3`

Bonnes pratiques
- Normalisation : pour améliorer la robustesse, normalisez également les entrées avant écriture/lecture (strip, collapse spaces, Unicode NFKC, lowercase).
- Tests : ajoutez des fixtures qui pin (ou nettoient) le dossier `data/processed/babelio_cache` pour rendre les tests reproductibles.
- Nettoyage : un mécanisme `cleanup_expired()` existe dans `BabelioCacheService` pour supprimer les fichiers expirés ; vous pouvez l'appeler périodiquement si nécessaire.

Sécurité et confidentialité
- Le cache stocke uniquement les réponses publiques de Babelio (pas de données utilisateur privées).

Implémentation rapide
- Le service `BabelioCacheService` écrit des fichiers JSON atomic (write to .tmp puis rename) et lit le wrapper `{ "ts": <timestamp>, "data": <results> }`.
- Le service `BabelioService.search()` consulte d'abord le cache (original key puis normalized key), sinon fait la requête réseau et écrit les deux clés en cas de succès.

Voir aussi
- `src/back_office_lmelp/services/babelio_cache_service.py`
- `src/back_office_lmelp/services/babelio_service.py`
- `scripts/start-dev.sh` (message d'information quand `BABELIO_CACHE_LOG` est défini)

```
