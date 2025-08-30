# mcp mongo

pour que claude code accede comme un grand au contenu de ma base,

je cree le fichier `.mcp.json`

```json
{
  "mcpServers": {
    "MongoDB": {
      "type": "stdio",
      "command": "npx",
      "args": [
        "-y",
        "mongodb-mcp-server",
        "--connectionString",
         "mongodb://localhost:27017/masque_et_la_plume",
        "--readOnly"
      ]
    }
  }
}
```

et je relance claude qui va detecter ce nouveau service au redemarrage.

De facon etrange j'ai du insister pour que claude utilise ce serveur mcp, je crois que je dois explicitement lui dire d'utiliser l'outil mcp MongoDB.

# ajout d'un package

modif dans `pyproject.toml`

puis

```bash
uv sync
```

claude sait comment on fait
