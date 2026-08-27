# Playwright MCP

Le serveur MCP Playwright donne à Claude Code la capacité de naviguer et d'observer l'interface graphique du frontend (Vue.js) : ouverture de pages, captures d'écran, inspection du DOM rendu. Il sert notamment à vérifier visuellement les correctifs UI (mise en page, responsive) sans intervention manuelle.

## Configuration

Le serveur est déclaré dans `.mcp.json` à la racine du projet :

```json
"playwright": {
  "type": "stdio",
  "command": "npx",
  "args": ["-y", "@playwright/mcp@latest", "--headless"]
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

Ce point n'est pas traité par cette configuration ; le mode headless est retenu comme solution fiable et portable. Une éventuelle solution de partage visuel (VNC, extension navigateur connectée à une instance headed) resterait à investiguer séparément si le besoin se confirme.

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
