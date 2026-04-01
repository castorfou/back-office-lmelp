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
