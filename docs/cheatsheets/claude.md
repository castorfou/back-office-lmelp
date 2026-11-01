## lancement avec un modele local

Le pré-requis est d'avoir un modele servi sur le port 11434

Par exemple avec le modele `Qwen3.5-9B`

```bash
ANTHROPIC_BASE_URL=http://localhost:11434 \
ANTHROPIC_AUTH_TOKEN=dummy \
ANTHROPIC_DEFAULT_OPUS_MODEL=Qwen3.5-9B \
ANTHROPIC_DEFAULT_SONNET_MODEL=Qwen3.5-9B \
ANTHROPIC_DEFAULT_HAIKU_MODEL=Qwen3.5-9B \
claude
```

!!! note "pas de '/' dans le nom du modèle"
    claude code ne supporte pas un `/` dans le nom du modele

## lancer le tunnel SSH

avec un modele servi sur le port 8000 sur CARIS

```bash
ssh -L 0.0.0.0:11434:localhost:8000 f279814@CARISSEXPLOREI40 -N
```

## passage à la ligne dans claude code

Se fait avec `Alt-Entrée`

## skills Matt Pocock

Le plugin [mattpocock-skills](https://github.com/mattpocock/skills) est activé dans `.claude/settings.json` :

```json
{
  "enabledPlugins": {
    "mattpocock-skills@claude-plugins-official": true
  }
}
```

Ce réglage active le plugin pour le dépôt mais ne le télécharge pas : chaque utilisateur doit l'installer une fois sur sa machine. Dans VS Code : `/plugins` → onglet **Plugins** → rechercher `mattpocock-skills` → **Install** → **Install for this project**.

### configuration

Les skills d'ingénierie lisent leur configuration dans `docs/agents/` (suivi des issues, labels de triage, documentation du domaine), référencée par la section `## Agent skills` du `CLAUDE.md`.

Cette configuration est déjà pré-remplie par PyFoundry : issues dans GitHub (`castorfou/back-office-lmelp`), labels par défaut, contexte unique. Pour la changer, modifie `docs/agents/*.md` ou relance :

```text
/setup-matt-pocock-skills
```

### skills principaux

| Skill | Usage |
|-------|-------|
| `/grill-me`, `/grill-with-docs` | Claude pose des questions pour clarifier un besoin avant de coder |
| `/to-spec`, `/to-tickets` | transformer une discussion en spécification, puis en issues |
| `/tdd` | boucle RED → GREEN → REFACTOR |
| `/triage` | trier les issues GitHub à l'aide des labels |
| `/diagnosing-bugs` | enquêter méthodiquement sur un bug |

## Connexion dans un devcontainer PyFoundry

Dans un devcontainer PyFoundry, `~/.claude` est partagé par tous les devcontainers (dossier `~/.config/claude-devcontainers` sur l'hôte), et `CLAUDE_CONFIG_DIR` y place aussi `.claude.json`. On se connecte une seule fois pour tous les projets, et la connexion survit aux rebuilds. Les conversations et la mémoire restent propres à chaque projet, car Claude Code les range par chemin (`/workspaces/<projet>`).
