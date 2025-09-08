# Système de Fallback LLM - Guide Utilisateur

## Vue d'ensemble

Le système d'extraction des livres et auteurs utilise une approche hybride avec un mécanisme de fallback pour garantir le fonctionnement même sans configuration Azure OpenAI.

## Fonctionnement du Système

### Mode Principal : Azure OpenAI
Lorsque Azure OpenAI est configuré avec les variables d'environnement appropriées :
- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_DEPLOYMENT_NAME`

L'application utilise un modèle LLM (Large Language Model) pour analyser intelligemment les résumés d'émissions et extraire automatiquement :
- Les titres de livres
- Les noms d'auteurs
- Les éditeurs
- Les notes moyennes
- Les coups de cœur des critiques

### Mode Fallback : Parsing Local
**Quand Azure OpenAI n'est PAS configuré** ou **en cas d'erreur de connexion**, l'application bascule automatiquement en mode fallback.

#### Qu'est-ce que le Fallback ?
Le fallback est un **parser de texte local** qui :

1. **Analyse directement les résumés** stockés dans MongoDB (collection `avis_critiques`)
2. **Cherche les tableaux markdown** structurés comme celui-ci :
   ```markdown
   ## 1. LIVRES DISCUTÉS AU PROGRAMME

   | Auteur | Titre | Éditeur | Avis des critiques | Note moyenne | Nb critiques | Coups de cœur |
   |--------|-------|---------|-------------------|--------------|--------------|---------------|
   | Marcel Proust | À la recherche du temps perdu | Gallimard | Positif | 4.2 | 5 | Jean, Marie |
   ```

3. **Extrait ligne par ligne** les informations bibliographiques sans faire appel à un service externe

#### Avantages du Fallback
- ✅ **Fonctionnement garanti** même sans configuration Azure
- ✅ **Pas de coût** d'API externe
- ✅ **Traitement local** des données
- ✅ **Confidentialité** préservée

#### Limitations du Fallback
- ⚠️ **Plus lent** que l'IA (traitement séquentiel)
- ⚠️ **Moins flexible** (dépend de la structure markdown exacte)
- ⚠️ **Peut générer des timeouts** sur de gros volumes

## Gestion des Timeouts

### Pourquoi des timeouts ?
Le mode fallback traite **chaque avis critique individuellement** et peut prendre du temps sur de gros volumes de données. L'API frontend a un timeout de 10 secondes par défaut, ce qui peut être insuffisant.

### Solutions
1. **Configuration Azure OpenAI** (recommandée) : L'IA traite plus rapidement
2. **Limitation des résultats** : Utiliser le paramètre `limit` dans l'URL
3. **Patience** : Le fallback finit toujours par aboutir

## Configuration Recommandée

### Pour un Usage de Production
```bash
# Variables d'environnement à définir
export AZURE_OPENAI_ENDPOINT="https://votre-endpoint.openai.azure.com/"
export AZURE_OPENAI_API_KEY="votre-clé-api"  # pragma: allowlist secret
export AZURE_OPENAI_DEPLOYMENT_NAME="gpt-4"
export AZURE_OPENAI_API_VERSION="2024-02-01"
```

### Pour un Usage de Développement/Test
Aucune configuration requise - le fallback fonctionne automatiquement.

## Dépannage

### "Timeout: La requête a pris trop de temps"
- **Cause** : Le fallback traite un grand volume d'avis critiques
- **Solution temporaire** : Réessayer ou utiliser `?limit=10` dans l'URL
- **Solution permanente** : Configurer Azure OpenAI

### Page vide sans erreur
- **Cause** : Aucun avis critique dans la base ou format inattendu
- **Vérification** : Consulter les logs serveur pour plus de détails

### Données incomplètes
- **Cause** : Structure markdown non standard dans les résumés
- **Solution** : Le fallback extrait ce qu'il peut, l'IA serait plus robuste

## Surveillance

L'application indique automatiquement quel mode est utilisé :
- **Mode Azure OpenAI** : Extraction rapide et intelligente
- **Mode Fallback** : Message dans les logs : "Mode démo/développement : parsing local"

La bascule entre les modes est **transparente** pour l'utilisateur final.
