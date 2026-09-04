# Issue #276 — Playwright MCP ne fonctionne plus dans certaines sessions (sandbox)

## Contexte

Playwright MCP fonctionnait dans l'issue #269 (devcontainer VS Code local) mais échouait systématiquement à lancer Chrome dans d'autres sessions (cloud/CI plus restreintes), utilisées lors du traitement des issues #273 et #274, avec l'erreur :

```
Failed to move to new namespace: PID namespaces supported, Network namespace supported, but failed: errno = Operation not permitted
Zygote process exited prematurely with exit code 1
```

## Diagnostic

- `unshare --pid --fork echo ok` échoue aussi avec `Operation not permitted` dans les sessions affectées — la session n'a pas la permission de créer un PID namespace, nécessaire au lancement sandboxé natif de Chrome par `@playwright/mcp`.
- Reproduit et confirmé dans la session de traitement de cette issue : `mcp__playwright__browser_navigate` échouait avec exactement la même erreur zygote avant le fix.
- Un test isolé avec `playwright-core` (lancement direct de `/opt/google/chrome/chrome` via `chromium.launch()`) réussissait sans `--no-sandbox`, contrairement à `@playwright/mcp` — la différence vient des flags/mode CDP spécifiques utilisés par `@playwright/mcp` (`--remote-debugging-pipe`, `--user-data-dir` custom) qui déclenchent le chemin de code activant le sandboxing zygote de Chrome, alors qu'un lancement `playwright-core` simplifié ne l'active pas de la même façon. Ce test isolé n'était donc pas représentatif — la validation définitive a nécessité de tester le vrai outil `mcp__playwright__*`.

## Solution

`@playwright/mcp` expose un flag CLI **`--no-sandbox`** (visible via `npx -y @playwright/mcp@latest --help`), non documenté jusqu'ici dans le projet. Ajouté aux `args` du serveur `playwright` dans `.mcp.json` :

```json
"playwright": {
  "type": "stdio",
  "command": "npx",
  "args": ["-y", "@playwright/mcp@latest", "--headless", "--no-sandbox"]
}
```

Le flag est ajouté **inconditionnellement** (pas de détection dynamique de l'environnement) — il fonctionne aussi bien dans le devcontainer local (où le sandbox natif était disponible) que dans les sessions restreintes.

## Validation

Après **redémarrage de la session Claude Code** (nécessaire pour recharger `.mcp.json` — un changement de config MCP n'est pas pris en compte à chaud), `mcp__playwright__browser_navigate` a été testé avec succès sur `http://localhost:5173` : plus d'erreur zygote/namespace, navigation et snapshot DOM opérationnels.

## Analyse de risque sécurité

`--no-sandbox` désactive une couche de défense en profondeur contre l'évasion de sandbox par du contenu web malveillant. Jugé acceptable car :
- Le navigateur ne visite que le frontend local du projet (`http://localhost:5173`), pas de navigation web arbitraire non maîtrisée en usage normal.
- La session Claude Code s'exécute déjà dans un environnement conteneurisé/restreint (devcontainer ou sandbox cloud) — le sandbox Chrome est redondant ici, pas la seule barrière.
- Pratique standard pour Chrome headless en CI/conteneurs (utilisée par les images Docker CI officielles Playwright/Puppeteer).

## Fichiers modifiés

- `.mcp.json` — ajout du flag `--no-sandbox` aux args du serveur `playwright`.
- `docs/dev/playwright-mcp.md` — nouvelle section "Sandbox Chrome et sessions restreintes" documentant le diagnostic, la solution et l'analyse de risque ; mise à jour du bloc de config affiché.

## Apprentissage clé pour sessions futures

Avant de conclure que Playwright MCP est cassé ou de sauter la vérification visuelle exigée par `CLAUDE.md` pour les changements UI : tester `unshare --pid --fork echo ok`. Si ça échoue, le flag `--no-sandbox` (déjà en place dans `.mcp.json` depuis cette issue) doit suffire après un redémarrage de session — pas besoin du contournement Chrome CLI manuel documenté précédemment (mémoire `playwright_mcp_sandbox_limitation.md`), qui reste une solution de secours si `--no-sandbox` s'avérait insuffisant dans un environnement encore plus restrictif.
