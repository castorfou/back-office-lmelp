
Retour par Claude

  1. Le serveur MCP MongoDB est fonctionnel - je peux maintenant explorer la base masque_et_la_plume avec ses 8 collections
  2. Le projet LMELP est un système de recommandation littéraire basé sur l'affinité avec les critiques du Masque et la Plume
  3. Le back-office est nécessaire pour nettoyer et structurer les données MongoDB existantes
  4. Les priorités sont claires : nettoyer les transcriptions et extraire toutes les entités (livres, auteurs, éditeurs, critiques,
  avis)

  Maintenant que le serveur MCP est opérationnel, nous pouvons progresser sur la création de l'interface moderne pour gérer cette base
  de données. La prochaine étape serait d'explorer plus en détail le contenu des collections pour mieux comprendre la structure et les
  besoins de nettoyage.

## ⚠️ Point Critique : Hiérarchie de Fiabilité des Données

**Données FIABLES** (source France Inter) :
- `episodes.titre` et `episodes.description` - Texte surveillé et solide

**Données SUSPECTES** (source Whisper sur MP3) :
- `episodes.transcription` - Erreurs possibles sur noms propres (auteurs, critiques)
- `avis_critiques` - Générés depuis transcriptions potentiellement erronées

## 🔧 Stratégie de Nettoyage

**Approche retenue** : Extraire entités erronées → Corriger entités → Stocker propre
- Partir de la transcription légèrement erronée
- Extraire les auteurs (avec erreurs type "Neige Sinnault")
- Corriger les auteurs extraits
- Stocker les auteurs propres en base
- Optionnellement corriger après coup la transcription (→ collection `emissions`)
