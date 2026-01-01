# Génération LLM d'avis critiques

## Vue d'ensemble

La fonctionnalité de génération LLM crée automatiquement des résumés structurés des avis critiques depuis les transcriptions Whisper des épisodes. Le processus se déroule en deux phases distinctes pour garantir la qualité et la précision des informations.

## Accès à la fonctionnalité

1. Accédez à la page **Génération d'Avis Critiques** depuis le menu
2. Une liste déroulante affiche tous les épisodes disponibles
3. Sélectionnez un épisode pour voir ou générer son résumé

## Sélecteur d'épisodes

### Badges de statut

Chaque épisode affiche un badge indiquant son état :

- **🟢 Vert** : Avis critiques déjà générés et sauvegardés
- **⚪ Gris** : Aucun avis critique encore généré (transcription disponible)

### Navigation

Trois moyens de navigation sont disponibles :

1. **Liste déroulante** : Sélection directe d'un épisode
2. **Bouton ◀️ Précédent** : Remonte dans la liste (épisodes plus récents)
3. **Bouton Suivant ▶️** : Descend dans la liste (épisodes plus anciens)

**Blocage pendant génération** : Les boutons de navigation sont désactivés pendant la génération LLM pour éviter la perte de données.

### Statistiques affichées

En haut du sélecteur, le compteur affiche :

```
Choisir un épisode (170 disponibles: 🟢 129 / ⚪ 41)
```

- **Total disponibles** : Nombre d'épisodes non masqués avec transcription
- **🟢 Nombre** : Episodes avec résumé déjà généré
- **⚪ Nombre** : Episodes sans résumé (à générer)

### Légende

Une légende explicative est affichée sous le sélecteur :

- **🟢 X** : Épisodes avec avis critique généré
- **⚪ Y** : Épisodes SANS avis critique (avec transcription disponible)
- **Total affiché** : X+Y épisodes non masqués avec transcription

## Génération du résumé

### Bouton Générer

**Quand** : Episode sans résumé (badge ⚪)

**Texte** : "🚀 Générer le summary"

**Action** :
1. Déclenche génération LLM en 2 phases
2. Affiche progression avec spinner
3. Affiche résumé final si succès

### Bouton Régénérer

**Quand** : Episode avec résumé existant (badge 🟢)

**Texte** : "🔄 Régénérer"

**Action** :
1. Relance génération complète (écrase résumé existant)
2. Même processus que "Générer"
3. Utile si génération précédente incomplète

**Utilisation** : Cliquez pour corriger un résumé malformé ou vide

## Processus de génération (2 phases)

### Phase 1 - Extraction brute

**Durée** : 10-20 secondes

**Source** : Transcription Whisper de l'épisode

**Informations extraites** :
- Liste des livres discutés avec auteurs et titres
- Avis des critiques pour chaque livre
- Coups de cœur des critiques
- Date de l'émission au format français (ex: "dimanche 1 octobre 2017")

**Indication visuelle** : "Phase 1: Extraction depuis transcription..." avec spinner

### Phase 2 - Correction orthographique

**Durée** : 5-10 secondes

**Source** : Contenu de la page RadioFrance de l'épisode

**Corrections appliquées** :
- Orthographe des noms d'auteurs (ex: "Houllebeck" → "Michel Houellebecq")
- Orthographe des titres de livres
- Préservation de la structure markdown de la Phase 1

**Indication visuelle** : "Phase 2: Correction via page RadioFrance..." avec spinner

## Affichage du résumé

### Résumé corrigé (Phase 2)

Le système affiche **uniquement le résumé final** (Phase 2 corrigée) :

**Format** : Markdown rendu en HTML avec mise en forme

**Structure** :
```markdown
## 1. LIVRES DISCUTÉS

- **"Titre du livre"** par Auteur (Éditeur)
  - Avis de Critique 1: ...
  - Avis de Critique 2: ...

## 2. COUPS DE CŒUR DES CRITIQUES

- Critique: "Titre du livre" par Auteur
```

**Date de l'émission** : Formatée en français en haut du résumé

### Alertes et avertissements

#### Alerte résumé vide

**Quand** : La génération retourne un résumé vide

**Message** : "⚠️ La génération a échoué (summary vide). Cliquez sur 'Régénérer' pour relancer."

**Couleur** : Fond jaune (alerte warning)

**Action** : Cliquez sur "Régénérer" pour nouvelle tentative

#### Avertissements LLM

**Quand** : La génération retourne des warnings

**Affichage** : Section "⚠️ Avertissements" sous le résumé

**Contenu** : Liste des warnings retournés par l'API

## Validation du résumé

Le système applique 5 critères de validation automatique :

### 1. Résumé non vide

Le résumé doit contenir du texte (pas uniquement des espaces).

### 2. Longueur raisonnable

Le résumé ne doit pas dépasser 50 000 caractères (détecte tables malformées).

### 3. Pas d'espaces excessifs

Le résumé ne doit pas contenir 100+ espaces consécutifs (détecte bugs LLM).

### 4. Section "LIVRES DISCUTÉS" présente

Structure requise pour extraction ultérieure des livres.

### 5. Section "COUPS DE CŒUR" présente

Garantit que la génération est complète (pas d'interruption prématurée).

**Validation automatique** : Appliquée côté backend avant sauvegarde

**Résultat échec** : HTTP 400 avec message d'erreur explicite

## Format des dates

Les dates d'émission sont formatées en français :

**Entrée** : `2017-10-01` (format ISO depuis MongoDB)

**Sortie** : `dimanche 1 octobre 2017` (format lisible)

**Mapping automatique** :
- Jours de la semaine : lundi, mardi, mercredi, etc.
- Mois : janvier, février, mars, etc.

## Cas d'usage

### Scénario 1 : Premier résumé d'un épisode

1. Sélectionnez un épisode avec badge ⚪ (sans résumé)
2. Cliquez sur "🚀 Générer le summary"
3. Patientez 15-30 secondes (2 phases)
4. Consultez le résumé corrigé affiché
5. Badge passe automatiquement de ⚪ → 🟢

### Scénario 2 : Consultation d'un résumé existant

1. Sélectionnez un épisode avec badge 🟢 (avec résumé)
2. Le résumé s'affiche automatiquement
3. Consultez le contenu structuré en markdown
4. Aucune action supplémentaire requise

### Scénario 3 : Régénération après échec

1. Episode a résumé vide ou malformé
2. Alerte warning "⚠️ La génération a échoué"
3. Cliquez sur "🔄 Régénérer"
4. Nouvelle génération complète lancée
5. Résumé valide affiché si succès

### Scénario 4 : Navigation entre épisodes

1. Consultez un épisode (résumé affiché)
2. Cliquez sur "Suivant ▶️" pour épisode plus ancien
3. Nouveau résumé chargé automatiquement
4. Répétez pour parcourir l'historique

**Note** : Navigation bloquée pendant génération LLM

## Configuration requise

### Variables d'environnement

Azure OpenAI doit être configuré dans `.env` :

```bash
AZURE_OPENAI_API_KEY=your_key_here
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_VERSION=2025-03-01-preview
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o
```

**Sans configuration** : Génération LLM indisponible (erreur HTTP 500)

## Gestion des erreurs

### Erreurs réseau

**Symptôme** : Message d'erreur HTTP en rouge

**Causes possibles** :
- Backend inaccessible
- Timeout réseau
- Azure OpenAI indisponible

**Solution** : Vérifiez que le backend fonctionne et réessayez

### Timeout LLM

**Symptôme** : Génération échoue après ~30 secondes

**Cause** : Azure OpenAI ne répond pas à temps

**Solution** : Cliquez sur "Régénérer" pour nouvelle tentative (retry automatique inclus)

### Résumé vide

**Symptôme** : Alerte warning "génération a échoué (summary vide)"

**Causes possibles** :
- Transcription vide ou invalide
- Erreur temporaire LLM
- Timeout pendant génération

**Solution** : Cliquez sur "Régénérer" (généralement réussit au 2ème essai)

### Validation échouée

**Symptôme** : HTTP 400 avec message détaillé

**Exemples** :
- "Section 'LIVRES DISCUTÉS' manquante"
- "Résumé anormalement long (malformé)"
- "Trop d'espaces consécutifs (bug LLM)"

**Solution** : Cliquez sur "Régénérer" pour génération propre

## Questions fréquentes

### Pourquoi deux phases au lieu d'une seule ?

**Raison** : Séparation des responsabilités

- **Phase 1** : Extraction informations (source: transcription Whisper)
- **Phase 2** : Correction orthographique (source: page RadioFrance)

**Avantages** :
- Meilleure qualité (noms corrigés via source fiable)
- Traçabilité des corrections
- Robustesse (chaque phase peut être optimisée indépendamment)

### Combien de temps prend la génération ?

**Durée totale** : 15-30 secondes

**Détail** :
- Phase 1 : 10-20 secondes (extraction depuis transcription)
- Phase 2 : 5-10 secondes (correction via page RadioFrance)
- Délai réseau : 2-5 secondes

**Facteurs influençant** : Longueur transcription, charge serveur Azure

### Puis-je modifier le résumé généré ?

**Non**. Le système ne permet que :
- Génération automatique (2 phases)
- Consultation du résumé affiché
- Régénération si insatisfait du résultat

**Modification manuelle** : Non supportée dans cette version

### Le résumé est-il sauvegardé automatiquement ?

**Oui**. Dès que la génération réussit et passe les 5 validations :

1. Résumé Phase 2 sauvegardé dans MongoDB (`avis_critiques.summary`)
2. Badge épisode passe de ⚪ → 🟢
3. Résumé disponible immédiatement lors des prochaines consultations

**Pas de bouton "Sauvegarder"** : Sauvegarde automatique après validation

### Que faire si le résumé semble incomplet ?

**Vérifications** :
1. Consultez les avertissements (section "⚠️" si présente)
2. Vérifiez que les 2 sections sont présentes ("LIVRES DISCUTÉS" + "COUPS DE CŒUR")
3. Comparez le nombre de livres avec la transcription originale

**Action** : Cliquez sur "🔄 Régénérer" pour nouvelle génération

### Les épisodes masqués sont-ils inclus ?

**Non**. La liste affiche uniquement :
- Épisodes **non masqués**
- Épisodes **avec transcription disponible**

**Impact** : Episodes masqués (via page Masquage) n'apparaissent pas dans le sélecteur

### Puis-je voir la Phase 1 (avant correction) ?

**Non actuellement**. L'interface affiche uniquement le résumé final (Phase 2).

**Raison** : Simplification de l'interface utilisateur

**Alternative développeur** : Consulter les logs backend pour voir résultat Phase 1

## Références techniques

Pour plus de détails techniques sur le fonctionnement interne :

- [Service de génération LLM](../dev/llm-generation-service.md) (à créer)
- [Validation des résumés](../dev/summary-validation.md) (à créer)
- [Intégration Azure OpenAI](../dev/azure-openai-integration.md) (à créer)
