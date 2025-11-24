# Mémoire Claude Code

Ce dossier contient la mémoire du projet pour Claude Code : décisions, apprentissages et contexte important.

## Organisation

### Format des fichiers
- **Extension** : `.md` (Markdown)
- **Nommage** : `YYMMDD-HHMM-sujet-descriptif.md`
- **Exemple** : `251121-1430-architecture-api-rest.md`

### Contenu suggéré

#### Décisions d'architecture
```markdown
# Architecture API REST

**Date** : 2025-11-21 14:30
**Contexte** : Besoin d'exposer les données via API

## Décision
Utiliser FastAPI plutôt que Flask pour...

## Justification
- Performance async native
- Documentation OpenAPI automatique
- Type hints Python natifs

## Conséquences
- Dépendance ajoutée : fastapi, uvicorn
- Structure projet modifiée
```

#### Solutions techniques
```markdown
# Solution : Performance requêtes DataFrame

**Date** : 2025-11-21
**Problème** : Requêtes pandas trop lentes sur gros datasets

## Solution implémentée
Utilisation de `polars` pour les opérations critiques...

## Performance
- Avant : 45s
- Après : 3s
```

#### Patterns de code
```markdown
# Pattern : Validation données entrée

**Convention** : Toujours utiliser pydantic BaseModel pour valider les données d'entrée API

**Exemple** :
\`\`\`python
from pydantic import BaseModel, validator

class DataInput(BaseModel):
    value: float

    @validator('value')
    def check_positive(cls, v):
        if v <= 0:
            raise ValueError('must be positive')
        return v
\`\`\`
```

#### Contexte métier
```markdown
# Contexte métier : Règles de calcul KPI

**KPI_A** : Se calcule uniquement sur données validées (status='VALID')
**KPI_B** : Exclut les weekends et jours fériés
**Source** : Documentation métier v2.3, section 4.2
```

## Utilisation

### Création manuelle
```bash
# Créer un nouveau fichier de mémoire
touch docs/claude/memory/$(date +%y%m%d-%H%M)-mon-sujet.md
```

### Avec Claude Code
Utilisez la commande `/stocke-memoire` qui crée automatiquement un fichier avec l'horodatage correct.

## Bonnes pratiques

1. **Être concis** : Aller à l'essentiel
2. **Dater** : Toujours inclure la date de la décision/apprentissage
3. **Contextualiser** : Expliquer le "pourquoi" autant que le "quoi"
4. **Liens** : Référencer issues GitHub, PRs, docs externes
5. **Mise à jour** : Ajouter des notes si une décision évolue

## Index (optionnel)

Vous pouvez maintenir un index ici des fichiers de mémoire importants :

- `251121-1430-architecture-api.md` - Choix architecture API REST
- `251121-1500-pattern-validation.md` - Pattern validation données
- ...
