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

et je relqnce claude qui va detecter ce nouveau service au redemarrage.
