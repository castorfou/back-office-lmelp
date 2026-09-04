# Playwright MCP

Le serveur MCP Playwright donne à Claude Code la capacité de naviguer et d'observer l'interface graphique du frontend (Vue.js) : ouverture de pages, captures d'écran, inspection du DOM rendu. Il sert notamment à vérifier visuellement les correctifs UI (mise en page, responsive) sans intervention manuelle.

## Configuration

Le serveur est déclaré dans `.mcp.json` à la racine du projet :

```json
"playwright": {
  "type": "stdio",
  "command": "npx",
  "args": ["-y", "@playwright/mcp@latest", "--headless", "--no-sandbox"]
}
```

Il est activé pour le projet via `enabledMcpjsonServers` dans `.claude/settings.local.json`.

## Mode headless

Le flag `--headless` est **requis** dans ce devcontainer. Sans lui (mode par défaut, "headed"), le lancement du navigateur échoue avec :

```
Missing X server or $DISPLAY
```

Le devcontainer expose bien des sockets `/tmp/.X11-unix/X*` (visibles via `--network=host` dans `devcontainer.json`), mais aucun `.Xauthority` n'y est monté : toute tentative de connexion à un display est donc rejetée par le serveur X (`Authorization required, but no authorization protocol specified`). En mode headless, Chromium calcule le layout et le rendu CSS exactement comme en mode headed — seule la fenêtre n'est pas affichée — donc les captures d'écran (`browser_take_screenshot`) et les snapshots DOM (`browser_snapshot`) restent fidèles pour valider un correctif visuel.

### Considérations sur le partage visuel

Il n'existe pas, dans `@playwright/mcp`, d'option native pour que l'utilisateur voie en direct la navigation effectuée par Claude Code (pas de mode VNC/streaming intégré). Faire apparaître une fenêtre de navigateur sur le poste de l'utilisateur nécessiterait du X11 forwarding (montage du socket X11 **et** du `.Xauthority` de l'hôte dans le container), ce qui est :

- spécifique à la machine et à la session graphique de chaque contributeur (non reproductible pour un autre poste ou en CI),
- non garanti si l'hôte n'a pas de serveur X actif (ex: Wayland, connexion sans forwarding X).

Ce point n'est pas traité par cette configuration ; le mode headless est retenu comme solution fiable et portable.

**Pourquoi pas de VNC/noVNC ici** : ce pattern existe (ex: projets exposant une app desktop comme AnyLogic via `Xvfb` + `x11vnc` + `noVNC`, où Claude Code et l'utilisateur ouvrent chacun un navigateur sur la même URL `http://localhost:6080/vnc.html` pour regarder le même flux vidéo d'un écran virtuel distant). Il est écarté pour ce projet car :

- **Notre frontend est déjà une page web nativement accessible** (`http://localhost:5173`) — le détour VNC ne sert qu'à rendre "web-visible" une application qui ne l'est pas nativement (cas AnyLogic, app desktop). Ici, il ajouterait une couche sans en retirer un vrai bénéfice.
- **Perte des capacités DOM** : piloter un navigateur affiché dans un canvas VNC (pixels bruts, pas de DOM) empêche `browser_snapshot` (arbre d'accessibilité), `browser_evaluate` (`getBoundingClientRect`, `getComputedStyle`) et les clics par sélecteur/`data-testid` — remplacés par du pilotage en coordonnées x/y, plus lent et fragile. Ce sont justement les capacités utilisées pour vérifier précisément largeur/alignement lors du fix de la tuile Contrôle Babelio (issue #269).
- **Latence ajoutée** par le flux VNC (rendu différé de l'ordre de 100–500 ms par action).

**Partage effectif aujourd'hui** : chaque navigateur (celui de Claude Code en headless, celui de l'utilisateur) est une session indépendante — pas de synchronisation d'état visuel en direct (scroll, focus). Ce qui est réellement partagé, c'est ce qui transite par le serveur : les données MongoDB modifiées via l'API, et le code source rechargé par le HMR de Vite. Pour comparer un rendu, l'utilisateur ouvre `http://localhost:5173` de son côté ; Claude Code partage captures d'écran et mesures DOM dans la conversation.

## Sandbox Chrome et sessions restreintes

Selon l'environnement d'exécution de la session Claude Code (devcontainer VS Code local vs. session cloud/CI plus restreinte), le lancement de Chrome par `@playwright/mcp` peut échouer avec :

```
Failed to move to new namespace: PID namespaces supported, Network namespace supported, but failed: errno = Operation not permitted
Zygote process exited prematurely with exit code 1
```

Cette erreur signifie que la session n'a pas la permission de créer un PID namespace, nécessaire au lancement sandboxé natif de Chrome. Elle est indépendante de la configuration du projet : elle peut être diagnostiquée en testant `unshare --pid --fork echo ok` dans la session — si cette commande échoue aussi avec `Operation not permitted`, Chrome échouera au lancement par `@playwright/mcp` pour la même raison.

**Solution** : le flag `--no-sandbox` (ajouté aux `args` du serveur `playwright` dans `.mcp.json`, voir [Configuration](#configuration)) désactive le sandboxing natif de Chrome et permet le lancement dans ces environnements restreints.

**Analyse de risque** : `--no-sandbox` retire une couche de défense en profondeur contre l'évasion de sandbox par du contenu web malveillant. Jugé acceptable ici car le navigateur ne visite que le frontend local du projet (`http://localhost:5173`), pas de navigation web arbitraire non maîtrisée, et la session Claude Code elle-même s'exécute déjà dans un environnement conteneurisé/restreint. C'est une pratique standard pour faire tourner Chrome headless en CI/conteneurs.

## Prérequis

- Le frontend doit être démarré (`./scripts/start-dev.sh` ou `cd frontend && npm run dev`) pour que Playwright puisse naviguer vers l'URL locale.
- `npx` doit pouvoir télécharger `@playwright/mcp` (accès réseau).
- Le navigateur Chrome doit être installé (`npx playwright install --with-deps chrome`).

## Installation du navigateur (devcontainer)

L'installation de Chrome et des polices d'émojis est automatisée dans `.devcontainer/postCreateCommand.sh` par la fonction `install_playwright_browsers`, exécutée à la création du devcontainer (après `setup_node`, car `npx` nécessite Node.js) :

```bash
install_playwright_browsers() {
    npx -y playwright install --with-deps chrome
    sudo apt-get install -y -qq fonts-noto-color-emoji
}
```

Sans cette étape (ex: devcontainer existant non reconstruit), installer manuellement :

```bash
npx -y playwright install --with-deps chrome
sudo apt-get install -y -qq fonts-noto-color-emoji
```

Le flag `--with-deps` installe aussi les dépendances système (bibliothèques graphiques) via `apt`. Sans `fonts-noto-color-emoji`, les émojis utilisés dans l'UI (icônes de tuiles, barre de recherche) s'affichent comme des glyphes vides dans les captures d'écran Playwright, alors qu'ils sont visibles dans un navigateur de poste classique (police généralement déjà présente sur les OS de bureau).

## Activation

Les serveurs MCP déclarés dans `.mcp.json` sont chargés au démarrage de la session Claude Code. Après avoir ajouté ou modifié la configuration du serveur `playwright` (y compris ses arguments comme `--headless`), redémarrer la session pour que les outils `mcp__playwright__*` reflètent le changement.

## Usage typique

- Naviguer vers une page du frontend (ex: Dashboard) et prendre une capture d'écran pour comparer un rendu avant/après un correctif CSS.
- Inspecter la structure DOM rendue pour valider un comportement de layout (grid, responsive) que les tests unitaires (jsdom) ne peuvent pas vérifier, faute de moteur de rendu CSS réel.
