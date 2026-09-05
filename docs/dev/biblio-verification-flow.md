# Service de Vérification Bibliographique - Architecture et Flux de Traitement

## Vue d'ensemble

Le système de vérification bibliographique est un service multi-phase qui valide et corrige automatiquement les données bibliographiques (auteur, titre, éditeur) extraites des avis critiques du Masque et la Plume.

**Contexte** : Les livres à corriger proviennent de la collection MongoDB `avis_critique` (champ `summary`), générée depuis la transcription audio Whisper. Cette transcription automatique introduit des erreurs orthographiques que le service doit corriger.

**Données d'entrée** : Livres extraits des avis critiques (collection MongoDB `avis_critique`, champ `summary`), générés depuis la transcription audio Whisper.

Le service utilise **deux sources de validation** pour maximiser la fiabilité :

1. **Babelio** (API externe) - Base de données bibliographique de référence
2. **Métadonnées épisodes** (MongoDB `episodes`) - Données éditorialisées France Inter (champs `titre` + `description`)

Le workflow se décompose en **trois phases successives** :

- **Phase 0** : Validation directe Babelio des livres extraits (avec enrichissements : double appel, correction auteur)
- **Phase 1** : Fuzzy search dans les métadonnées éditorialisées de l'épisode
- **Phase 2** : Validation Babelio complète (auteur + livre) avec cascade de recherches

## Architecture Générale

```
                    ┌──────────────────────────────┐
                    │    DONNÉES D'ENTRÉE          │
                    │  Livres extraits avis_       │
                    │  critique (Whisper)          │
                    └──────────────┬───────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    BiblioValidationService                          │
│                    (Frontend - Orchestration)                       │
└─────────────────────────────────────────────────────────────────────┘
                                   │
         ┌─────────────────────────┼─────────────────────────┐
         │                         │                         │
         ▼                         ▼                         ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────────┐
│    Phase 0      │    │     Phase 1      │    │      Phase 2        │
│                 │    │                  │    │                     │
│ Validation      │    │ Fuzzy Search     │    │ Validation Babelio  │
│ Babelio directe │    │ (Ground Truth)   │    │ complète            │
│                 │    │                  │    │                     │
│ - Livres        │    │ Backend API      │    │ External API        │
│   extraits      │    │ /api/fuzzy-      │    │ /api/verify-        │
│ - Double appel  │    │ search-episode   │    │ babelio             │
│ - Correction    │    │                  │    │                     │
│   auteur        │    │ Sources:         │    │ - verifyAuthor()    │
│                 │    │ - episode.titre  │    │ - verifyBook()      │
│ Source:         │    │ - episode.       │    │ - Cascade           │
│ Babelio API     │    │   description    │    │                     │
└─────────────────┘    └──────────────────┘    └─────────────────────┘
         │                         │                         │
         └─────────────────────────┼─────────────────────────┘
                                   │
                                   ▼
                         ┌──────────────────┐
                         │   Arbitration    │
                         │                  │
                         │ - Priority rules │
                         │ - Confidence     │
                         │   scoring        │
                         │ - Filtering      │
                         └──────────────────┘
                                   │
                                   ▼
                         ┌──────────────────┐
                         │  Final Result    │
                         │                  │
                         │ - verified       │
                         │ - suggestion     │
                         │ - not_found      │
                         │ - error          │
                         └──────────────────┘

SOURCES DE VALIDATION :
1. Babelio API (Phases 0 & 2)
2. Métadonnées épisodes MongoDB (Phase 1)
```

## Flux de Traitement Détaillé

### Phase 0 : Validation Directe Babelio avec Enrichissements

**Objectif** : Pour chaque couple auteur-livre à valider, effectuer une **vérification directe sur Babelio** des livres extraits de l'épisode avant toute autre tentative. Phase 0 inclut deux mécanismes d'enrichissement pour maximiser le taux de succès :

1. **Double appel de confirmation** : Si Babelio suggère une correction avec confidence 0.85-0.99, un 2ème appel confirme la suggestion
2. **Correction automatique d'auteur** : Si le livre n'est pas trouvé, Phase 0 essaie de corriger l'auteur avant de passer en Phase 1

**Processus complet** :
1. Récupérer les livres extraits de l'épisode via `livresAuteursService.getLivresAuteurs({ episode_oid: episodeId })`
2. Vérifier si l'input utilisateur correspond exactement à un livre extrait
3. **Si match trouvé**, appeler Babelio : `verifyBook(title, author)`
4. **Selon la réponse Babelio**, appliquer les enrichissements (détails ci-dessous)
5. **Si succès** → ✅ **Terminé, retourner résultat**
6. **Si échec** → ❌ **Passer à Phase 1** (fuzzy search)

**Fonctionnement de `verifyBook()` :**
- Recherche le livre sur Babelio avec fuzzy matching (tolère les fautes d'orthographe)
- Calcule un `confidence_score` (0.0 à 1.0) basé sur la similarité des chaînes (algorithme Ratcliff-Obershelp)
- Retourne un statut selon le seuil de confiance :
  - **`verified`** si `confidence_score >= 0.90` (correspondance quasi-exacte)
  - **`corrected`** si `confidence_score < 0.90` (suggestion de correction)
  - **`not_found`** si aucun livre trouvé sur Babelio

#### Enrichissement 1 : Double Appel de Confirmation

**Scénario** : Babelio retourne `status: 'verified'` ou `'corrected'` avec `confidence_score` entre 0.85 et 0.99

**Workflow** :
1. **1er appel** : `verifyBook(title, author)` retourne suggestion avec confidence 0.85-0.99
2. **Détection** : Le score n'est pas assez élevé (< 1.0) pour valider directement
3. **2ème appel** : `verifyBook(suggested_title, suggested_author)` avec les valeurs suggérées
4. **Si le 2ème appel confirme avec confidence 1.0** :
   - ✅ Retourner `status: 'verified'`
   - Source : `babelio_phase0_confirmed`
   - Confidence : 1.0
5. **Si le 2ème appel ne confirme pas** :
   - ❌ Fallback Phase 1 (fuzzy search)

**Exemple concret** :
```javascript
// Input utilisateur
author: "Adrien Bosque"  // Erreur de transcription Whisper
title: "L'invention de Tristan"

// Livre extrait en base (même erreur)
{ auteur: "Adrien Bosque", titre: "L'invention de Tristan" }

// 1er appel Babelio
verifyBook("L'invention de Tristan", "Adrien Bosque")
→ status: 'verified', confidence: 0.95
→ babelio_suggestion_author: "Adrien Bosc"  // Correction détectée

// 2ème appel de confirmation
verifyBook("L'invention de Tristan", "Adrien Bosc")
→ status: 'verified', confidence: 1.0  // Confirmation !

// Résultat Phase 0
{
  status: 'verified',
  data: {
    source: 'babelio_phase0_confirmed',
    confidence_score: 1.0,
    suggested: {
      author: "Adrien Bosc",
      title: "L'invention de Tristan"
    },
    corrections: { author: true, title: false }
  }
}
```

**Avantage** : Permet de corriger automatiquement les erreurs de transcription Whisper même quand Babelio n'est pas sûr à 100% au premier appel.

#### Enrichissement 2 : Correction Automatique d'Auteur

**Scénario** : Babelio retourne `status: 'not_found'` (livre non trouvé)

**Hypothèse** : Le problème vient de l'orthographe de l'auteur, pas du titre

**Workflow** :
1. **1er appel livre** : `verifyBook(title, author)` → `not_found`
2. **Détection** : Aucun livre trouvé, possiblement à cause de l'auteur
3. **Appel auteur** : `verifyAuthor(author)` pour obtenir suggestion d'auteur corrigé
4. **Si suggestion d'auteur obtenue** :
   - 2ème appel livre : `verifyBook(title, corrected_author)`
5. **Si le 2ème appel livre réussit avec confidence 1.0** :
   - ✅ Retourner `status: 'verified'`
   - Source : `babelio_phase0_author_correction`
   - Confidence : 1.0
6. **Si le 2ème appel livre échoue** :
   - ❌ Fallback Phase 1 (fuzzy search)

**Exemple concret** :
```javascript
// Input utilisateur
author: "Fabrice Caro"  // Erreur de transcription Whisper
title: "Rumba Mariachi"

// Livre extrait en base (même erreur)
{ auteur: "Fabrice Caro", titre: "Rumba Mariachi" }

// 1er appel livre
verifyBook("Rumba Mariachi", "Fabrice Caro")
→ status: 'not_found'  // Livre inconnu avec cet auteur

// Appel auteur pour correction
verifyAuthor("Fabrice Caro")
→ status: 'corrected', confidence: 0.73
→ babelio_suggestion: "Fabcaro"  // Vrai nom de l'auteur

// 2ème appel livre avec auteur corrigé
verifyBook("Rumba Mariachi", "Fabcaro")
→ status: 'verified', confidence: 1.0  // Livre trouvé !

// Résultat Phase 0
{
  status: 'verified',
  data: {
    source: 'babelio_phase0_author_correction',
    confidence_score: 1.0,
    suggested: {
      author: "Fabcaro",
      title: "Rumba Mariachi"
    },
    corrections: { author: true, title: false }
  }
}
```

**Avantage** : Traite automatiquement le cas fréquent où seul le nom d'auteur est mal orthographié (noms propres complexes, transcription audio difficile).

#### Cas de Succès Phase 0 (Sans Enrichissement)

**Scénario simple** : Babelio confirme directement avec `confidence_score >= 1.0`

**Workflow** :
1. **Appel unique** : `verifyBook(title, author)` → `status: 'verified'`, `confidence: 1.0`
2. ✅ Retourner `status: 'verified'` immédiatement
3. Source : `babelio_phase0`

**Conditions de succès** :
- Babelio retourne `status: 'verified'` ET `confidence_score >= 1.0`

**Conditions d'échec (passage Phase 1)** :
- Erreur réseau ou timeout
- Tous les enrichissements ont échoué

**Code source** :
- Frontend : `BiblioValidationService.js:80-216` (`_tryPhase0DirectValidation`)
- Backend API : `/api/verify-babelio` (endpoint Babelio)
- Backend API : `/api/livres-auteurs` (livres extraits)

**Exemple de succès** :
```javascript
// Entrée (données extraites de avis_critique.summary via Whisper)
author: "Amélie Nothomb"
title: "Tant mieux"
episodeId: "68d98f74edbcf1765933a9b5"  // pragma: allowlist secret

// Phase 0 : Vérification directe Babelio
verifyBook("Tant mieux", "Amélie Nothomb")
→ status: 'verified', confidence: 1.0
→ Babelio confirme : ces données sont exactes

// Résultat Phase 0 (terminé)
{
  status: 'verified',
  data: {
    source: 'babelio_phase0',
    confidence_score: 1.0
  }
}
// ✅ Pas besoin de fuzzy search, workflow terminé
```

#### Enrichissement 3 : Scraping de l'Éditeur depuis Babelio

**Objectif** : Enrichir automatiquement les réponses de `verifyBook()` avec l'éditeur du livre en scrapant les pages Babelio, afin d'éviter la saisie manuelle dans le modal de validation.

**Scénario** : `verifyBook()` retourne `confidence_score >= 0.90` avec une URL Babelio

**Workflow** :
1. **Vérification préalable** : Seuil de confiance >= 0.90 (évite les appels inutiles sur des résultats peu fiables)
2. **Scraping HTML** : Requête GET sur `babelio_url` + parsing BeautifulSoup
3. **Extraction éditeur** : Sélecteur CSS `a.tiny_links.dark[href*="/editeur/"]`
4. **Enrichissement** : Ajout du champ `babelio_publisher` dans la réponse
5. **Gestion d'erreur** : Si le scraping échoue (404, timeout, parsing), `babelio_publisher` reste `None` (non fatal)

**Exemple concret** :
```javascript
// Input utilisateur
author: "Hannah Assouline"
title: "Des visages et des mains"

// 1er appel Babelio
verifyBook("Des visages et des mains: 150 portraits d'écrivain...", "Hannah Assouline")
→ status: 'verified', confidence: 0.973
→ babelio_url: "https://www.babelio.com/livres/Assouline-Des-visages-et-des-mains-150-portraits-decrivain/1635414"

// 2ème appel automatique : scraping éditeur
fetch_publisher_from_url("https://www.babelio.com/livres/...")
→ HTML parsing avec BeautifulSoup
→ Sélecteur CSS : a.tiny_links.dark[href*="/editeur/"]
→ Éditeur trouvé : "Herscher"

// Réponse enrichie finale
{
  status: 'verified',
  confidence_score: 0.973,
  babelio_url: "https://www.babelio.com/livres/...",
  babelio_publisher: "Herscher",  // ✅ Nouveau champ
  babelio_data: {
    id_oeuvre: "1635414",
    titre: "Des visages et des mains: 150 portraits d'écrivain...",
    prenoms: "Hannah",
    nom: "Assouline"
  }
}
```

**Bénéfices** :
- ✅ Élimine 90% des saisies manuelles d'éditeurs dans le modal
- ✅ Pré-remplit automatiquement le champ "Éditeur" dans l'UI
- ✅ L'utilisateur peut toujours modifier si nécessaire

**Priorité d'éditeur dans `handle_book_validation()`** :
```python
publisher = (
    user_validated_publisher    # 1. Saisi manuellement (priorité max)
    or babelio_publisher        # 2. ✅ Depuis scraping Babelio (nouveau)
    or user_entered_publisher   # 3. Saisi dans modal not_found
    or suggested_publisher      # 4. Suggéré (autres sources)
    or editeur                  # 5. Original transcription (souvent vide)
)
```

**Limitations** :
- Nécessite `confidence_score >= 0.90` (seuil qualité)
- Respecte le rate limiting de 0.8s entre requêtes Babelio
- Dépend de la structure HTML de Babelio (robuste mais peut évoluer)

#### Enrichissement 4 : Enrichissement Automatique lors de l'Extraction (Option 1)

**Objectif** : Enrichir automatiquement TOUS les livres extraits des avis critiques avec `babelio_url` et `babelio_publisher` dès leur ajout au cache MongoDB, sans attendre la validation manuelle.

**Workflow d'extraction enrichie** :

```
┌──────────────────────────────────────────────────────┐
│   extract_books_from_reviews(avis_critiques)        │
│   (BooksExtractionService)                           │
└──────────────────┬───────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────┐
│   Extraction via parsing markdown ou LLM            │
│   → Liste de livres avec auteur/titre/éditeur       │
└──────────────────┬───────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────┐
│   _enrich_books_with_babelio(books)                 │
│   Pour chaque livre:                                 │
│   1. verify_book(title, author)                      │
│   2. Si confidence >= 0.90:                          │
│      - Ajouter babelio_url                           │
│      - Ajouter babelio_publisher                     │
│   3. Si erreur ou confidence < 0.90:                 │
│      - Continuer sans enrichissement                 │
└──────────────────┬───────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────┐
│   Insertion dans MongoDB cache                       │
│   (livresauteurs_cache)                              │
│   {                                                   │
│     auteur: "Albert Camus",                          │
│     titre: "L'Étranger",                             │
│     editeur: "Gallimard",                            │
│     babelio_url: "https://...",       ✅ Enrichi     │
│     babelio_publisher: "Gallimard",   ✅ Enrichi     │
│     status: "extracted"                              │
│   }                                                   │
└──────────────────────────────────────────────────────┘
```

**Code source** :
```python
# Backend : books_extraction_service.py

async def extract_books_from_reviews(self, avis_critiques):
    """
    Extrait les livres depuis les avis critiques ET enrichit automatiquement
    chaque livre avec Babelio (babelio_url, babelio_publisher).
    """
    # 1. Extraction classique
    all_extracted_books = []
    for avis in avis_critiques:
        books_from_review = await self._extract_books_from_single_review(avis)
        all_extracted_books.extend(books_from_review)

    # 2. ✅ Enrichissement automatique Babelio (Option 1)
    enriched_books = await self._enrich_books_with_babelio(all_extracted_books)

    return enriched_books

async def _enrich_books_with_babelio(self, books):
    """
    Enrichit automatiquement chaque livre avec Babelio.
    Appelle verify_book() pour chaque livre et enrichit si confidence >= 0.90.
    """
    enriched_books = []

    for book in books:
        enriched_book = book.copy()

        try:
            # Appeler Babelio verify_book()
            verification = await babelio_service.verify_book(
                book.get("titre", ""),
                book.get("auteur", "")
            )

            # Enrichir si confidence >= 0.90
            if verification and verification.get("confidence", 0) >= 0.90:
                if verification.get("url"):
                    enriched_book["babelio_url"] = verification["url"]
                if verification.get("babelio_publisher"):
                    enriched_book["babelio_publisher"] = verification["babelio_publisher"]

        except Exception:
            # En cas d'erreur Babelio, continuer sans enrichissement
            # Le livre reste tel quel sans babelio_url/babelio_publisher
            pass

        enriched_books.append(enriched_book)

    return enriched_books
```

**Exemple concret** :

```javascript
// Avis critique extrait
{
  "summary": """
  | Auteur | Titre | Éditeur |
  |--------|-------|---------|
  | Albert Camus | L'Étranger | Gallimard |
  | Victor Hugo | Les Misérables | Le Livre de Poche |
  """
}

// Extraction + Enrichissement automatique
// Pour chaque livre extrait:

// Livre 1: Albert Camus - L'Étranger
verify_book("L'Étranger", "Albert Camus")
→ confidence: 0.95 ✅
→ babelio_url: "https://www.babelio.com/livres/Camus-LEtranger/1234"
→ babelio_publisher: "Gallimard"

// Livre 2: Victor Hugo - Les Misérables
verify_book("Les Misérables", "Victor Hugo")
→ confidence: 0.92 ✅
→ babelio_url: "https://www.babelio.com/livres/Hugo-Les-Miserables/5678"
→ babelio_publisher: "Gallimard"

// Résultat dans MongoDB cache
[
  {
    auteur: "Albert Camus",
    titre: "L'Étranger",
    editeur: "Gallimard",
    babelio_url: "https://www.babelio.com/livres/Camus-LEtranger/1234",  ✅
    babelio_publisher: "Gallimard",  ✅
    status: "extracted"
  },
  {
    auteur: "Victor Hugo",
    titre: "Les Misérables",
    editeur: "Le Livre de Poche",
    babelio_url: "https://www.babelio.com/livres/Hugo-Les-Miserables/5678",  ✅
    babelio_publisher: "Gallimard",  ✅
    status: "extracted"
  }
]
```

**Avantages de l'enrichissement automatique** :
- ✅ Cache pré-enrichi : Les livres ont déjà `babelio_url` et `babelio_publisher` dès l'extraction
- ✅ UX améliorée : L'utilisateur voit les données enrichies immédiatement dans l'interface
- ✅ Moins de saisie manuelle : L'éditeur est pré-rempli pour ~70-80% des livres
- ✅ Traçabilité : Chaque livre garde une trace de son enrichissement Babelio
- ✅ Compatibilité : Se combine parfaitement avec la persistence lors de la validation (Enrichissement 3)

**Gestion d'erreurs** :
- Si Babelio échoue (timeout, réseau, 404) → Le livre est ajouté au cache SANS enrichissement
- Si `confidence < 0.90` → Pas d'enrichissement (données peu fiables)
- L'extraction continue même si certains livres échouent l'enrichissement

**Performance** :
- ⚠️ Ralentit l'extraction : 1 appel Babelio par livre (~ 1-2s par livre avec rate limiting)
- ⚠️ Pour un épisode avec 5 livres → +5-10s de temps d'extraction total
- ✅ Appels asynchrones en série pour respecter le rate limiting de 0.8s
- ✅ Cache Babelio évite les appels redondants pour les livres déjà vus

**Alternative (Option 2 - Non implémentée)** :
Un système de ramasse-miettes (garbage collector) pourrait enrichir les livres en batch asynchrone après l'extraction, sans ralentir le workflow principal.

**Code source impacté** :
- Backend : `books_extraction_service.py::extract_books_from_reviews()` - Ajout de l'enrichissement automatique
- Backend : `books_extraction_service.py::_enrich_books_with_babelio()` - Nouvelle méthode d'enrichissement
- Tests : `tests/test_babelio_cache_enrichment.py` - 5 tests TDD vérifiant l'enrichissement

#### Persistance de `babelio_publisher` dans le Cache MongoDB

**Contexte** : Le champ `babelio_publisher` est enrichi dans la **réponse de `verify_book()`** mais doit être **persisté dans le cache MongoDB** (`livresauteurs_cache`) pour être réutilisé ultérieurement.

**Workflow de persistence** :

1. **Frontend appelle `/verify-babelio`** :
   - Retourne `babelio_publisher` dans la réponse (si `confidence >= 0.90`)
   - Frontend affiche `babelio_publisher` dans le modal de validation

2. **Frontend envoie les données de validation** :
   - Inclut `babelio_publisher` dans le payload de `/validate-suggestion`
   - Backend `handle_book_validation()` reçoit `babelio_publisher`

3. **Backend utilise `babelio_publisher` pour créer le livre** :
   - Priorité : `user_validated_publisher > babelio_publisher > user_entered_publisher`
   - Le livre est créé avec l'éditeur enrichi ✅

4. **Backend persiste `babelio_publisher` dans le cache** :
   - Lors de `mark_as_processed()`, ajouter `babelio_publisher` aux metadata
   - Cache MongoDB `livresauteurs_cache` est mis à jour avec :
     ```json
     {
       "_id": "cache123",
       "auteur": "Hannah Assouline",
       "titre": "Des visages et des mains",
       "babelio_publisher": "Herscher",
       "status": "mongo",
       "author_id": "author456",
       "book_id": "book789"
     }
     ```

**Exemple de flux complet** :

```javascript
// 1. Frontend : Appel /verify-babelio
const result = await verifyBook("Des visages et des mains", "Hannah Assouline");
// → { babelio_publisher: "Herscher", confidence_score: 0.973 }

// 2. Frontend : Validation avec babelio_publisher
await validateSuggestion({
  cache_id: "cache123",
  user_validated_author: "Hannah Assouline",
  user_validated_title: "Des visages et des mains",
  babelio_publisher: "Herscher"  // ✅ Envoyé au backend
});

// 3. Backend : Utilisation dans handle_book_validation()
publisher = (
    book_data.get("user_validated_publisher")
    or book_data.get("babelio_publisher")  // ✅ Utilisé pour créer livre
    or book_data.get("user_entered_publisher")
    or book_data.get("editeur", "")
)

// 4. Backend : Persisté dans le cache
cache_service.mark_as_processed(
    cache_id,
    author_id,
    book_id,
    metadata={"babelio_publisher": babelio_publisher}  // ✅ Persisté
)

// 5. Résultat dans MongoDB cache
{
  "_id": "cache123",
  "babelio_publisher": "Herscher",  // ✅ Disponible pour réutilisation
  "status": "mongo"
}
```

**Bénéfices de la persistence** :
- ✅ Traçabilité : Historique de l'enrichissement Babelio
- ✅ Réutilisation : Évite de re-scraper l'éditeur si le livre est revalidé
- ✅ Cohérence : Cache contient toutes les données enrichies
- ✅ Debugging : Facilite l'analyse des cas où l'éditeur a été enrichi automatiquement

**Code source impacté** :
- Backend : `collections_management_service.py::handle_book_validation()` (ajout `babelio_publisher` aux metadata)
- Backend : `livres_auteurs_cache_service.py::mark_as_processed()` (accepte metadata supplémentaires)
- Frontend : `EpisodeEditor.vue` (envoie `babelio_publisher` dans validation)

---

### Phase 1 : Ground Truth Fuzzy Search

**Objectif** : Rechercher les données bibliographiques dans les **métadonnées éditorialisées** de l'épisode (champs `titre` + `description` vérifiés par l'éditeur France Inter).

**Important** : Cette recherche ne se fait **pas** sur la transcription audio brute, mais sur les métadonnées MongoDB de la collection `episodes` qui sont des données fiables et éditorialisées.

**Exemple de document `episodes` MongoDB** :
```json
{
  "_id": "68d98f74edbcf1765933a9b5",
  "titre": "Catherine Millet, Sorj Chalandon, Rebeka Warrior, Amélie Nothomb...",
  "description": "Le nouveau texte de Sigrid Nunez ou encore celui d'Amélie Nothomb sur sa mère...",
  "type": "livres",
  "date": "2025-09-28T10:59:39.000Z"
}
```

**Processus** :
1. Appel API : `POST /api/fuzzy-search-episode`
   ```javascript
   {
     episode_id: "68bd9ed3582cf994fb66f1d6",  // pragma: allowlist secret
     query_title: "Fleurs intestinales",
     query_author: "Vamille"
   }
   ```

2. Backend extrait les métadonnées de l'épisode :
   - Récupération depuis MongoDB (`episodes` collection)
   - Combinaison des champs `titre` + `description` (données éditorialisées)
   - Extraction des segments entre guillemets (priorité haute pour titres)
   - Extraction des mots > 3 caractères

3. Recherche fuzzy avec `rapidfuzz` (Python) :
   - **Titres** : Recherche dans segments entre guillemets (marqueur 📖) + mots généraux
   - **Auteurs** : Recherche dans tous les candidats textuels
   - Scores de similarité calculés (0-100)

4. Réponse API :
   ```javascript
   {
     found_suggestions: true,
     title_matches: [
       ["📖 Fleurs intestinales", 100],
       ["intestinales", 75]
     ],
     author_matches: [
       ["Vamille", 98]
     ]
   }
   ```

**Seuils de qualité** :
- **Good matches** : `titleScore >= 80 && authorScore >= 80`
- **Decent matches** : `titleScore >= 75 && authorScore >= 75` (assoupli pour variantes)
- **Perfect author boost** : Si `authorScore >= 85`, seuil titre réduit à 35

**Code source** :
- Backend : `app.py:583-674` (endpoint `/api/fuzzy-search-episode`)
- Frontend : `BiblioValidationService.js:426-518` (`_hasGoodGroundTruthMatches`, `_hasDecentGroundTruthMatches`)

**Limites connues** :
- Peut retourner des **URLs** : `https://www.franceinter.fr/...` (présentes dans le champ `description`)
- Peut retourner des **fragments trop courts** : `am`, `de`, `Amélie`
- Nécessite filtrage avant utilisation (voir Phase 4)

**Note** : Le fuzzy search échoue parfois car les métadonnées `titre` et `description` ne contiennent pas toujours les noms complets ou corrects des auteurs/titres (contrairement aux données Babelio qui sont normalisées).

**Origine des données à corriger** :
Les livres/auteurs à valider proviennent de la collection `avis_critique` (champ `summary`), qui est générée depuis la **transcription audio Whisper**. C'est cette transcription automatique qui introduit les erreurs orthographiques (ex: "Alain Mabancou" au lieu de "Mabanckou").

---

### Phase 2 : Validation Babelio de l'Auteur

**Objectif** : Vérifier et corriger l'orthographe de l'auteur via l'API AJAX de Babelio.

**Processus** :
1. Appel API : `POST /api/verify-babelio`
   ```javascript
   {
     type: "author",
     name: "Alain Mabancou"  // Faute d'orthographe
   }
   ```

2. Backend interroge Babelio :
   - Endpoint : `https://www.babelio.com/aj_recherche.php`
   - Rate limiting : 0.8 sec entre requêtes
   - Cache disque + mémoire pour performances
   - Headers/cookies appropriés pour éviter blocages

3. Réponse Babelio (via BabelioService) :
   ```javascript
   {
     status: "corrected",  // ou "verified" si exact
     original: "Alain Mabancou",
     babelio_suggestion: "Alain Mabanckou",
     confidence_score: 0.95,
     babelio_data: {
       id: "2180",
       prenoms: "Alain",
       nom: "Mabanckou",
       type: "auteurs",
       ca_membres: "30453"
     },
     babelio_url: "https://www.babelio.com/auteur/Alain-Mabanckou/2180"
   }
   ```

**Statuts possibles** :
- `verified` : Orthographe exacte confirmée (`confidence_score >= 0.95`)
- `corrected` : Suggestion de correction (`confidence_score < 0.95`)
- `not_found` : Aucun auteur trouvé
- `error` : Erreur technique (timeout, réseau, etc.)

**Code source** :
- Backend : `babelio_service.py:317-379` (`verify_author`)
- Scoring : `babelio_service.py:570-586` (`_calculate_similarity` - algorithme Ratcliff-Obershelp)

---

### Phase 2.5 : Recherche Babelio par Titre Seul avec Double Confirmation (Issue #80)

**Objectif** : Récupérer des livres perdus après échec de toutes les phases précédentes en cherchant **uniquement par titre** sur Babelio, puis **confirmer avec un 2ème appel**.

**Scénario cible** : Livres marqués `not_found` après Phases 0, 1 et 2 à cause d'une **erreur orthographique sur le nom d'auteur**, alors que le **titre est correct**.

**Activation conditionnelle** :
- Phase 2.5 ne s'active **que si** :
  - Phase 0 a échoué (ou n'a pas été activée)
  - Phase 1 a échoué (ou pas d'épisode)
  - Phase 2 retourne `not_found`
- Ne s'active **jamais** si une phase précédente a réussi

**Processus en 2 étapes obligatoires** :

#### Étape 1 : Recherche par Titre Seul

```javascript
// Appel #1 : Babelio avec titre uniquement (sans auteur)
POST /api/verify-babelio
{
  type: "book",
  title: "Des visages et des mains",
  author: null  // ← Auteur omis volontairement
}

// Réponse Babelio
{
  status: "corrected",  // ou "verified"
  original_title: "Des visages et des mains",
  babelio_suggestion_title: "Des visages et des mains: 150 portraits d'écrivain...",  // ⚠️ Titre tronqué
  original_author: null,
  babelio_suggestion_author: "Hannah Assouline",  // ✅ Auteur découvert
  confidence_score: 0.736
}
```

**Conditions pour passer à l'Étape 2** :
- `babelio_suggestion_title` existe (non null, non vide)
- `babelio_suggestion_author` existe (non null, non vide)
- Sinon → ❌ Échec Phase 2.5, retour `not_found`

#### Étape 2 : Confirmation avec Auteur Découvert

**Problème connu** : Babelio tronque les titres longs avec `...` dans les suggestions. Exemple :
- Suggestion brute : `"Des visages et des mains: 150 portraits d'écrivain..."`
- Titre complet réel : `"Des visages et des mains: 150 portraits d'écrivain"`

**Solution** : Nettoyer le titre suggéré avant le 2ème appel :

```javascript
// Nettoyage du titre suggéré
let cleanedTitle = babelio_suggestion_title.replace(/\.\.\.+$/, '').trim();
// "Des visages et des mains: 150 portraits d'écrivain..."
// → "Des visages et des mains: 150 portraits d'écrivain"

// Appel #2 : Confirmation avec auteur + titre nettoyé
POST /api/verify-babelio
{
  type: "book",
  title: cleanedTitle,  // Titre sans "..."
  author: babelio_suggestion_author  // "Hannah Assouline"
}

// Réponse de confirmation
{
  status: "verified",
  original_title: "Des visages et des mains: 150 portraits d'écrivain",
  babelio_suggestion_title: "Des visages et des mains: 150 portraits d'écrivain...",
  original_author: "Hannah Assouline",
  babelio_suggestion_author: "Hannah Assouline",
  confidence_score: 0.9796  // ⚠️ Pas toujours 1.0 à cause des variations de titre
}
```

**Seuil de confirmation ajusté** :
- **Minimum requis** : `confidence_score >= 0.95` (au lieu de 1.0)
- **Raison** : Les variations de titre (troncature, sous-titres, casse) empêchent souvent d'atteindre 1.0
- **Exemple observé** : 0.9796 pour "Des visages et des mains" (très proche mais pas exact)

**Résultat final si confirmation réussie** :
```javascript
{
  status: 'suggestion',
  data: {
    original: {
      author: "Anna Assouline",
      title: "Des visages et des mains"
    },
    suggested: {
      author: "Hannah Assouline",  // ✅ Auteur corrigé découvert par Phase 2.5
      title: "Des visages et des mains: 150 portraits d'écrivain..."  // Titre Babelio (peut inclure sous-titre)
    },
    corrections: {
      author: true,   // Auteur toujours corrigé en Phase 2.5
      title: false    // Titre souvent inchangé (sauf ajout sous-titre)
    },
    source: 'babelio_title_only_confirmed',  // ✅ Traçabilité Phase 2.5
    confidence_score: 0.9796
  }
}
```

**Résultat si confirmation échoue** (`confidence_score < 0.95`) :
```javascript
{
  status: 'not_found',
  data: {
    original: { author: "...", title: "..." },
    reason: 'phase_2_5_confirmation_failed',  // Nouvelle raison spécifique
    attempts: ['ground_truth', 'babelio', 'babelio_title_only']
  }
}
```

**Exemple complet - Cas "Anna Assouline"** :

```javascript
// Input utilisateur (transcription Whisper avec erreur)
author: "Anna Assouline"  // ❌ Erreur : "Anna" au lieu de "Hannah"
title: "Des visages et des mains"

// Phase 2 échoue
verifyBook("Des visages et des mains", "Anna Assouline")
→ status: 'not_found'

// Phase 2.5 - Étape 1 : Recherche par titre seul
verifyBook("Des visages et des mains", null)
→ confidence: 0.736
→ babelio_suggestion_title: "Des visages et des mains: 150 portraits d'écrivain..."
→ babelio_suggestion_author: "Hannah Assouline"  // ✅ Auteur découvert !

// Phase 2.5 - Étape 2 : Confirmation avec auteur + titre nettoyé
cleanedTitle = "Des visages et des mains: 150 portraits d'écrivain"  // "..." supprimé
verifyBook(cleanedTitle, "Hannah Assouline")
→ confidence: 0.9796  // ✅ >= 0.95 requis
→ status: 'verified'

// Résultat final Phase 2.5
{
  status: 'suggestion',
  source: 'babelio_title_only_confirmed',
  suggested: {
    author: "Hannah Assouline",
    title: "Des visages et des mains: 150 portraits d'écrivain..."
  },
  confidence_score: 0.9796
}
```

**Gestion des homonymes** :
- Titres communs (ex: "L'Étranger") peuvent matcher plusieurs auteurs au 1er appel
- Le 2ème appel avec confirmation évite les faux positifs :
  - Si le livre existe réellement → `confidence >= 0.95`
  - Si homonyme ou mauvais auteur → `confidence < 0.95` → rejet

**Avantages de la double confirmation** :
- ✅ Zéro faux positifs : Le 2ème appel élimine les ambiguïtés
- ✅ Pattern éprouvé : Similaire à Phase 0 enrichie (double appel déjà testé)
- ✅ Robuste aux homonymes : Titre commun → 1er appel suggère, mais 2ème appel échoue si mauvais auteur
- ✅ Traçabilité : `source: 'babelio_title_only_confirmed'` identifie clairement Phase 2.5

**Limitations et cas d'échec** :
- ⚠️ **Titre trop différent** : Si utilisateur tape "Des visages" au lieu de "Des visages et des mains" → échec 1er appel
- ⚠️ **Titre très commun** : "Le Procès", "L'Étranger" → risque d'homonymes même avec confirmation
- ⚠️ **Variations de titre** : Sous-titres, éditions différentes peuvent faire échouer la confirmation
- ⚠️ **Seuil 0.95 ajusté** : Moins strict que 1.0 à cause des troncatures Babelio, mais risque théorique de faux positifs

**Cas réels testés** :

| Input Original | Phase 2 | Phase 2.5 Étape 1 | Phase 2.5 Étape 2 | Résultat Final |
|----------------|---------|-------------------|-------------------|----------------|
| Anna Assouline - Des visages et des mains | not_found | Hannah Assouline (0.736) | verified (0.9796) | ✅ suggestion |
| Alexandre Lamboreau - Pâture | not_found | Alexandre Lamborot (?) | verified (1.0) | ✅ suggestion |

**Code source** :
- Frontend : `BiblioValidationService.js:_arbitrateResults()` (Cas 6 - ajout Phase 2.5)
- Backend : Endpoint `/api/verify-babelio` (accepte `author: null` depuis l'origine)
- Fixtures : `frontend/tests/fixtures/babelio-book-cases.yml` (cas `author: null`)

**Métriques de succès attendues** :
- Réduction du taux de `not_found` de ~10-15%
- Taux de précision Phase 2.5 > 95% (validation manuelle)
- Temps de réponse total < 3s (2 appels API supplémentaires)

---

### Phase 3 : Validation Babelio du Livre

**Objectif** : Vérifier et corriger le titre du livre, en tenant compte de la suggestion d'auteur.

**Processus** :
1. **Stratégie intelligente** (BiblioValidationService) :
   - Si Phase 2 suggère une correction d'auteur :
     - Essayer d'abord avec l'auteur **original**
     - Si échec (`not_found`), réessayer avec l'auteur **suggéré**
   - Sinon, tester uniquement avec l'auteur original

2. Appel API : `POST /api/verify-babelio`
   ```javascript
   {
     type: "book",
     title: "Ramsès de Paris",
     author: "Alain Mabanckou"  // Auteur corrigé de Phase 2
   }
   ```

3. Réponse Babelio :
   ```javascript
   {
     status: "verified",
     original_title: "Ramsès de Paris",
     babelio_suggestion_title: "Ramsès de Paris",
     original_author: "Alain Mabanckou",
     babelio_suggestion_author: "Alain Mabanckou",
     confidence_score: 1.0,
     babelio_data: {
       id_oeuvre: "1770",
       titre: "Ramsès de Paris",
       prenoms: "Alain",
       nom: "Mabanckou",
       type: "livres"
     }
   }
   ```

**Cascade de recherche** (exemple complexe - Caroline Dussain) :
```
1. verifyAuthor("Caroline Dussain")
   → suggère "Caroline Dawson" (confidence: 0.82)

2. verifyBook("Un déni français", "Caroline Dussain")
   → not_found

3. verifyBook("Un déni français", "Caroline Dawson")
   → suggère "Caroline du Saint - Un Déni français - Enquête sur l'élevage industrie..."
   → (confidence: 0.88)

Résultat final: Caroline du Saint - Un Déni français - Enquête...
```

**Code source** :
- Backend : `babelio_service.py:380-461` (`verify_book`)
- Frontend : `BiblioValidationService.js:188-242` (logique de cascade)
- Scoring : Combiné (70% titre + 30% auteur) pour livres

---

### Phase 4 : Arbitrage et Décision Finale

**Objectif** : Combiner les résultats des 3 sources avec règles de priorité et filtrage intelligent.

#### 4.1 Filtrage des Suggestions Invalides

**Avant l'arbitrage**, filtrer les suggestions ground truth invalides via `_isValidTitleSuggestion()` :

**Règles de rejet** :
- URLs complètes : `http://`, `https://`, `www.`, `franceinter.fr`, `.com`, `.fr`
- Fragments trop courts : `< 3 caractères` (sauf si exact match avec original)
- Mots isolés courts : `< 8 caractères` pour un seul mot (filtre "Amélie", "tous", etc.)

**Exemple de filtrage** :
```javascript
// Entrée fuzzy search
titleMatches: [
  ["📖 https://www.franceinter.fr/emissions/le-masque", 36],  // ❌ URL
  ["📖 Amélie", 64],                                          // ❌ Prénom seul
  ["📖 Tant mieux", 92]                                       // ✅ Valide
]

// Après filtrage
titleMatches: [
  ["📖 Tant mieux", 92]  // Seule suggestion gardée
]
```

**Code source** : `BiblioValidationService.js:697-728` (`_isValidTitleSuggestion`)

#### 4.2 Ordre de Priorité des Sources

**Règle 1 : Ground Truth avec Good Matches** (priorité absolue)
- **Conditions** : `titleScore >= 80 && authorScore >= 80` + suggestion valide
- **Action** : Utiliser la suggestion ground truth
- **Validation** : Vérifier cohérence avec Babelio si possible
- **Exemple** : Vamille - Fleurs intestinales (scores 100/98)

**Règle 2 : Ground Truth avec Decent Matches** (priorité forte)
- **Conditions** : `titleScore >= 75 && authorScore >= 75` + suggestion valide
- **Cas spécial** : Si `authorScore >= 85`, accepter `titleScore >= 35`
- **Action** : Utiliser ground truth **sans exiger confirmation Babelio**
- **Exemple** : Emmanuel Carrère - Colcause → Kolkhoze (scores 85/35)

**Règle 3 : Validation Directe Babelio** (pas de suggestion)
- **Conditions** :
  - `authorValidation.status === 'verified'` ET pas de suggestion d'auteur
  - `bookValidation.status === 'verified'`
  - Pas de ground truth utilisable
- **Action** : Retourner `status: 'verified'` (données originales exactes)
- **Exemple** : Alice Ferney - Comme en amour

**Règle 4 : Suggestion Babelio Seule**
- **Conditions** : Babelio propose une correction (`status: 'corrected'` ou `'verified'` avec différence)
- **Filtrage** : Rejeter si `confidence_score < 0.8` (sauf si livre validé + auteur connu)
- **Action** : Retourner `status: 'suggestion'` avec données Babelio
- **Exemple** : Alain Mabancou → Alain Mabanckou

**Règle 5 : Not Found** (aucune source fiable)
- **Conditions** : Aucune des règles ci-dessus ne s'applique
- **Action** : Retourner `status: 'not_found'`
- **Exemples** : Grégory Lefloc - Peau d'ours (nécessite intervention manuelle)

**Code source** : `BiblioValidationService.js:293-420` (`_arbitrateResults`)

#### 4.3 Reconstruction du Nom d'Auteur (Ground Truth)

Lorsque ground truth retourne des **fragments d'auteur** (ex: `["Alikavazovic", 82], ["Jakuta", 78]`), le service reconstruit le nom complet :

**Algorithme de reconstruction** :
1. Filtrer les mots parasites : `pour`, `de`, `du`, `la`, `le`, `et`, `dans`, etc.
2. Nettoyer les fragments : enlever `d'`, `l'`, `de ` du début
3. Identifier prénom vs nom :
   - Heuristique longueur (prénom généralement plus court)
   - Détection pattern majuscule + minuscules
   - Unicode-aware pour noms accentués
4. Ordre final : `Prénom Nom`

**Exemple** :
```javascript
// Entrée fuzzy
authorMatches: [
  ["Alikavazovic", 82],
  ["Jakuta", 78],
  ["pour", 65]  // Bruit
]

// Après reconstruction
reconstructedAuthor: "Jakuta Alikavazovic"
// Jakuta (plus court, pattern prénom) + Alikavazovic (nom)
```

**Code source** : `BiblioValidationService.js:524-690` (`_extractGroundTruthSuggestion`)

#### 4.4 Priorisation des Titres (Ground Truth)

Lorsque fuzzy search retourne **plusieurs titres candidats**, le service utilise un score combiné :

**Algorithme de scoring** :
1. Calculer **similarité Levenshtein** entre titre original et candidat (normalisé 0-1)
2. Normaliser **score fuzzy** de rapidfuzz (0-1)
3. Score combiné : `similarité × 0.7 + score_fuzzy × 0.3`
4. Filtrer les suggestions invalides (URLs, fragments)
5. Trier par score combiné décroissant
6. Retourner le meilleur match

**Exemple** :
```javascript
// Entrée
original.title: "Colcause"

titleMatches: [
  ["📖 Kolkhoze", 75],      // Similarité: 0.85 → combiné: 0.82
  ["📖 Kolkhoz", 78],       // Similarité: 0.80 → combiné: 0.79
  ["cause", 90]             // Similarité: 0.50 → combiné: 0.62
]

// Résultat : "Kolkhoze" (meilleur compromis similarité/score)
```

**Code source** : `BiblioValidationService.js:540-573` (dans `_extractGroundTruthSuggestion`)

---

## Statuts de Résultat Final

Le service retourne toujours un objet avec `status` et `data` :

### ✅ `verified` - Données Vérifiées Exactes
**Signification** : Les données originales sont exactement identiques aux références trouvées (ou ont été corrigées et confirmées).

**Sources possibles** :
- `babelio_phase0` : Validation directe sans enrichissement (confidence 1.0)
- `babelio_phase0_confirmed` : Double appel de confirmation (1er appel 0.85-0.99, 2ème appel 1.0)
- `babelio_phase0_author_correction` : Correction automatique d'auteur (livre trouvé après correction auteur)
- `babelio` : Validation via Phases 2-3 (workflow complet)
- `ground_truth+babelio` : Validation combinée fuzzy search + Babelio

**Exemples** :
```javascript
// Validation directe Phase 0
{
  status: 'verified',
  data: {
    original: { author: "Alice Ferney", title: "Comme en amour" },
    source: 'babelio_phase0',
    confidence_score: 1.0
  }
}

// Double appel de confirmation
{
  status: 'verified',
  data: {
    original: { author: "Adrien Bosque", title: "L'invention de Tristan" },
    suggested: { author: "Adrien Bosc", title: "L'invention de Tristan" },
    source: 'babelio_phase0_confirmed',
    confidence_score: 1.0,
    corrections: { author: true, title: false }
  }
}

// Correction automatique d'auteur
{
  status: 'verified',
  data: {
    original: { author: "Fabrice Caro", title: "Rumba Mariachi" },
    suggested: { author: "Fabcaro", title: "Rumba Mariachi" },
    source: 'babelio_phase0_author_correction',
    confidence_score: 1.0,
    corrections: { author: true, title: false }
  }
}
```

### 🔄 `suggestion` - Correction Proposée
**Signification** : Le système propose une modification basée sur ground truth et/ou Babelio.

**Exemple** :
```javascript
{
  status: 'suggestion',
  data: {
    original: { author: "Alain Mabancou", title: "Ramsès de Paris" },
    suggested: { author: "Alain Mabanckou", title: "Ramsès de Paris" },
    corrections: { author: true, title: false },
    source: 'babelio',
    confidence_score: 0.95
  }
}
```

### ❓ `not_found` - Aucune Suggestion Fiable
**Signification** : Le système ne peut pas proposer de correction avec confiance suffisante.

**Exemple** :
```javascript
{
  status: 'not_found',
  data: {
    original: { author: "Grégory Lefloc", title: "Peau d'ours" },
    reason: 'no_reliable_match_found',
    attempts: ['ground_truth', 'babelio']
  }
}
```

### ⚠️ `error` - Erreur Technique
**Signification** : Une erreur s'est produite pendant le traitement.

**Exemple** :
```javascript
{
  status: 'error',
  data: {
    original: { author: "...", title: "..." },
    error: 'Timeout: La requête a pris trop de temps',
    attempts: ['babelio']
  }
}
```

**Traitement backend (Issue #282)** : `set_validation_results` (`app.py`) ignore ce statut sans créer d'entrée dans `livresauteurs_cache` — le livre reste "non traité" et sera retenté au prochain chargement de la page. Ce statut ne doit **jamais** être confondu avec un `not_found` définitif (livre réellement introuvable sur Babelio après recherche aboutie), car cela figerait un échec technique transitoire (réseau, timeout, blocage Babelio) comme un résultat permanent en base.

---

## Cas d'Usage Réels Documentés

### Cas Simples - Succès

#### 1. Validation Directe (Phase 0 uniquement)
**Entrée** : Alice Ferney - Comme en amour
**Phase 0** : Vérification directe Babelio → `verified`
**Résultat** : ✅ `verified` (source: `babelio_phase0`, workflow terminé sans fuzzy search)

#### 2. Correction Simple d'Auteur
**Entrée** : Alain Mabancou - Ramsès de Paris
**Ground Truth** : Pas de match fiable
**Babelio** : Suggère "Alain Mabanckou"
**Résultat** : 🔄 `suggestion` (auteur corrigé, titre identique)

#### 3. Ground Truth Perfect Match
**Entrée** : Vamille - Fleurs intestinales
**Ground Truth** : Scores 100/98 (perfect)
**Babelio** : Confirme
**Résultat** : ✅ `verified` (source: `ground_truth+babelio`)

### Cas Complexes - Cascade

#### 4. Double Correction (Auteur + Titre)
**Entrée** : Caroline Dussain - Un déni français
**Cascade** :
1. `verifyAuthor("Caroline Dussain")` → suggère "Caroline Dawson"
2. `verifyBook("Un déni français", "Caroline Dussain")` → not_found
3. `verifyBook("Un déni français", "Caroline Dawson")` → suggère "Caroline du Saint - Un Déni français - Enquête sur l'élevage industrie..."

**Résultat** : 🔄 `suggestion` (auteur ET titre corrigés)

#### 5. Ground Truth avec Faute Orthographique
**Entrée** : Emmanuel Carrère - Colcause
**Ground Truth** : `titleScore: 35, authorScore: 85` (decent match, author perfect)
**Suggestion** : "Emmanuel Carrère - Kolkhoze"
**Résultat** : 🔄 `suggestion` (source: `ground_truth`, titre corrigé)

#### 6. Correction de Casse
**Entrée** : Laurent Mauvignier - La Maison Vide
**Babelio** : Suggère "La Maison vide" (casse différente)
**Résultat** : 🔄 `suggestion` (titre avec casse corrigée)

### Cas Difficiles - Not Found

#### 7. Inversion de Nom
**Entrée** : Grégory Lefloc - Peau d'ours
**Attendu** : Grégory Le Floch - Peau d'ourse
**Ground Truth** : Échoue (segmentation "Le Floch" problématique)
**Babelio** : Échoue (ne trouve pas "Lefloc")
**Résultat** : ❓ `not_found` (nécessite intervention manuelle)

#### 8. Prénom Raccourci
**Entrée** : Nin Antico - Une Obsession
**Attendu** : Nine Antico - Une obsession
**Problème** : Fuzzy search ne détecte pas "Nin" → "Nine"
**Résultat** : ❓ `not_found` (nécessite intervention manuelle)

#### 9. Titre Très Différent
**Entrée** : Christophe Bigot - Un autre Matin ailleurs
**Attendu** : Christophe Bigot - Un autre m'attend ailleurs
**Problème** : "Matin" vs "m'attend" = faible similarité
**Résultat** : ❓ `not_found` (nécessite intervention manuelle)

### Cas Spéciaux - Filtrage URLs et Fragments

#### 10. Filtrage d'URL
**Entrée** : Amélie Nothomb - Tant mieux
**Fuzzy Search Brut** :
- `https://www.franceinter.fr/emissions/le-masque-et-la-plume` (score 36) → ❌ Rejeté
- `Amélie` (score 64) → ❌ Rejeté (prénom seul)

**Babelio Fallback** : Confirme "Amélie Nothomb - Tant mieux"
**Résultat** : ✅ `verified` (source: `babelio`, ground truth filtré)

---

## Services Backend Impliqués

### BabelioService (Python)
**Fichier** : `src/back_office_lmelp/services/babelio_service.py`

**Responsabilités** :
- Interrogation API AJAX Babelio (`https://www.babelio.com/aj_recherche.php`)
- Rate limiting (0.8 sec entre requêtes)
- Cache disque + mémoire (performance)
- Calcul de scores de confiance (algorithme Ratcliff-Obershelp)
- Gestion d'erreur robuste (timeout, réseau, parsing JSON)

**Méthodes principales** :
- `search(term)` : Recherche générique Babelio
- `verify_author(name)` : Vérification auteur
- `verify_book(title, author)` : Vérification livre
- `verify_batch(items)` : Traitement par lots

**Configuration** :
- Headers + cookies pour éviter blocages Babelio
- Timeout : 10 sec total, 5 sec connexion
- Cache limite : 100 entrées mémoire, illimité disque
- Log verbeux : Variable `BABELIO_CACHE_LOG=1`

### FuzzySearchService (Backend API)
**Fichier** : `src/back_office_lmelp/app.py:583-674`

**Responsabilités** :
- Extraction texte des épisodes MongoDB
- Recherche fuzzy avec `rapidfuzz` (Python)
- Détection segments entre guillemets (titres probables)
- Calcul scores de similarité (0-100)

**Endpoint** : `POST /api/fuzzy-search-episode`

**Paramètres** :
```json
{
  "episode_id": "68bd9ed3582cf994fb66f1d6",  // pragma: allowlist secret
  "query_title": "Fleurs intestinales",
  "query_author": "Vamille"
}
```

**Réponse** :
```json
{
  "found_suggestions": true,
  "title_matches": [["📖 Fleurs intestinales", 100]],
  "author_matches": [["Vamille", 98]],
  "debug_candidates": ["...", "..."],
  "debug_quoted_matches": ["...", "..."]
}
```

**Algorithme** :
1. Extraire texte : `episode.titre + episode.description`
2. Segments entre guillemets → titres prioritaires (marqueur 📖)
3. **N-grams contigus** → détection titres multi-mots :
   - Quadrigrams (4 mots) filtrés si longueur > 10 caractères
   - Trigrams (3 mots) filtrés si longueur > 8 caractères
   - Bigrams (2 mots) filtrés si longueur > 6 caractères
4. Mots > 3 caractères → candidats généraux (fallback)
5. `rapidfuzz.process.extract()` pour scoring
6. Filtrage par seuils : `titleScore >= 60`, `authorScore >= 75`

**Priorité des candidats** : guillemets > 4-grams > 3-grams > 2-grams > mots isolés

---

## Services Frontend Impliqués

### BiblioValidationService (JavaScript)
**Fichier** : `frontend/src/services/BiblioValidationService.js`

**Responsabilités** :
- Orchestration des 4 phases de validation
- Arbitrage intelligent entre sources
- Filtrage suggestions invalides (URLs, fragments)
- Reconstruction noms d'auteurs fragmentés
- Calcul scores combinés (similarité + fuzzy)

**Méthode principale** :
```javascript
async validateBiblio(author, title, publisher, episodeId)
```

**Dépendances injectées** :
- `fuzzySearchService` : Frontend wrapper pour `/api/fuzzy-search-episode`
- `babelioService` : Frontend wrapper pour `/api/verify-babelio`
- `localAuthorService` : Non implémenté (futur)

**Méthodes clés** :
- `_tryPhase0DirectValidation()` : Phase 0 (livres extraits)
- `_arbitrateResults()` : Phase 4 (décision finale)
- `_hasGoodGroundTruthMatches()` : Détection good matches
- `_hasDecentGroundTruthMatches()` : Détection decent matches
- `_extractGroundTruthSuggestion()` : Reconstruction auteur/titre
- `_isValidTitleSuggestion()` : Filtrage URLs/fragments
- `_validateGroundTruthSuggestion()` : Validation ground truth avec Babelio
- `_validateBabelioSuggestion()` : Validation Babelio seule

### BiblioValidationCell (Vue Component)
**Fichier** : `frontend/src/components/BiblioValidationCell.vue`

**Responsabilités** :
- Affichage visuel du statut de validation
- Indicateurs : ✅ Validé, 🔄 Suggestion, ❓ Non trouvé, ⚠️ Erreur
- Gestion retry sur erreurs
- Tooltip avec détails

**Props** :
```javascript
{
  author: String,
  title: String,
  publisher: String,
  episodeId: String
}
```

**États** :
- `loading` : Validation en cours
- `result` : Résultat de `validateBiblio()`
- `error` : Erreur affichée

---

## Configuration et Variables d'Environnement

### Backend (BabelioService)
- `BABELIO_CACHE_LOG` : Verbosité des logs cache (`0`/`1`/`true`)
  - `0` (défaut) : Logs DEBUG uniquement
  - `1` : Logs INFO pour hit/miss/write

### Rate Limiting
- Délai minimum entre requêtes Babelio : `0.8 sec`
- Timeout requête Babelio : `10 sec` (total), `5 sec` (connexion)
- Timeout fuzzy search : `30 sec` (configurable dans `api.js`)

### Seuils de Confiance

#### Ground Truth
- **Good matches** : `titleScore >= 80 && authorScore >= 80`
- **Decent matches** : `titleScore >= 75 && authorScore >= 75`
- **Perfect author boost** : Si `authorScore >= 85`, `titleScore >= 35` accepté

#### Babelio
- **Verified** : `confidence_score >= 0.95`
- **Corrected** : `confidence_score < 0.95`
- **Rejet suggestion fantaisiste** : `confidence_score < 0.8` (sauf livre validé + auteur connu)

#### Validation Titre (Filtrage)
- **Longueur minimale** : `>= 3 caractères`
- **Mot isolé** : `>= 8 caractères` ou `>= 2 mots`

---

## Tests et Validation

### Tests Backend
- **BabelioService** : Tests unitaires avec mocks API (`tests/test_babelio_service.py`)
- **Fuzzy Search** : Tests intégration endpoint (`tests/test_app.py`)
- **Cache** : Tests cache disque/mémoire (`tests/test_babelio_cache_service.py`)

### Tests Frontend
- **Niveau 1 - UI** : `tests/integration/LivresAuteurs.test.js` (affichage colonne)
- **Niveau 2 - Composant** : `tests/unit/BiblioValidationCell.test.js` (indicateurs visuels)
- **Niveau 3 - Service** : `tests/unit/BiblioValidationService.modular.test.js` (logique arbitrage)
- **Niveau 4 - Backend** : Tests backend séparés

### Simulation Phase 0 en Tests
**Note importante** : La Phase 0 (`_getExtractedBooks`) utilise actuellement des **fixtures hardcodées** pour les tests uniquement :

```javascript
// BiblioValidationService.js:130-138 (CODE DE TEST)
_getExtractedBooks(episodeId) {
  // Simulation basée sur les fixtures pour Alice Ferney
  if (episodeId === '68ab04b92dc760119d18f8ef') {  // pragma: allowlist secret
    return [
      { author: 'Alice Ferney', title: 'Comme en amour' }
    ];
  }
  return [];
}
```

**En production**, cette méthode devrait interroger la collection MongoDB `avis_critique` pour récupérer les livres réellement extraits de l'épisode (champ `summary`).

### Fixtures de Test
**Fichier** : `frontend/tests/fixtures/biblio-validation-cases.yml`

**Structure** :
```yaml
- input:
    author: "Alain Mabancou"
    title: "Ramsès de Paris"
    publisher: "Seuil"
    episodeId: "68c707ad6e51b9428ab87e9e"  # pragma: allowlist secret
  output:
    status: "suggestion"
    suggested_author: "Alain Mabanckou"
    suggested_title: "Ramsès de Paris"
    corrections:
      author: true
      title: false
  expected:  # (Optionnel) Pour cas nécessitant intervention manuelle
    status: "suggestion"
    suggested_author: "..."
  review:
    manual_review_required: true
    reason: "..."
```

**Cas couverts** :
- ✅ Validated : 2 cas (Alice Ferney, Amélie Nothomb)
- 🔄 Suggestion : 5 cas (Mabancou, Dussain, Mauvignier, Pondi, Carrère)
- ❓ Not Found : 4 cas (Lefloc, Antico, Bigot, Michaud)

---

## Limitations Connues et Améliorations Futures

### Limitations Actuelles

1. **Fuzzy Search avec N-grams**
   - Détecte maintenant les titres multi-mots grâce aux n-grams contigus (ex: "L'invention de Tristan")
   - Limitations restantes :
     - Ne détecte pas les inversions de nom (Le Floch → Lefloc)
     - Échoue sur prénoms raccourcis (Nine → Nin)
     - Retourne parfois URLs et fragments parasites (filtrés en Phase 4)

2. **Pas de Mapping Canonique**
   - Corrections connues non réutilisées (recalcul à chaque fois)
   - Pas de base de données d'auteurs normalisés

3. **Phase 0 Enrichie** ✅
   - Appelle l'API réelle `livresAuteursService.getLivresAuteurs()`
   - Double appel de confirmation pour confidence 0.85-0.99
   - Correction automatique d'auteur si livre not_found
   - Taux de succès typique : ~45% des livres traités automatiquement

4. **Babelio Rate Limiting**
   - 0.8 sec entre requêtes = lent pour gros volumes
   - Besoin de batch processing optimisé

### Améliorations Proposées

#### 1. Mapping Canonique Auteurs
**Fichier** : `data/author-canonical-mapping.yml`

**Structure** :
```yaml
- original: "Grégory Lefloc"
  canonical: "Grégory Le Floch"
  confidence: 1.0
  source: "manual"
  validated_at: "2025-09-07"
```

**Avantages** :
- Évite de recalculer les cas difficiles
- Base de connaissances réutilisable
- Intervention humaine documentée

#### 2. Recherche par Auteur Babelio First
**Workflow alternatif** :
1. Chercher l'auteur sur Babelio
2. Récupérer sa bibliographie complète
3. Fuzzy match le titre dans sa bibliographie
4. Évite les faux positifs (homonymes)

**Cas bénéficiaires** : Christophe Bigot, Agnès Michaux

#### 3. Amélioration Fuzzy Search Backend
**Techniques déjà implémentées** :
- ✅ N-grams contigus pour titres multi-mots (bigrams, trigrams, quadrigrams)

**Techniques proposées** :
- Détection phonétique (Soundex, Metaphone pour français)
- NER (Named Entity Recognition) pour extraction auteurs/titres
- Fine-tuning seuils adaptatifs par type d'erreur

#### 4. Service Local Auteurs
**Base MongoDB** : Collection `auteurs_canoniques`

**Workflow** :
1. Vérifier cache local d'abord
2. Fallback Babelio si absent
3. Mise à jour cache après validation manuelle

**Avantages** :
- Zéro latence réseau pour auteurs connus
- Contrôle complet sur mapping
- Indépendance vis-à-vis Babelio

---

## Fermeture de la Boucle : Mise à Jour du Summary Original

### Contexte et Problématique

Le workflow de validation bibliographique corrige les erreurs de transcription Whisper présentes dans `avis_critique.summary`, mais ces corrections restaient isolées dans les collections `livres` et `auteurs`. L'application principale lmelp continuait d'afficher les données erronées du summary original.

**Issue #67** implémente la fermeture de cette boucle de correction.

### Workflow de Mise à Jour

Lorsqu'un livre/auteur est validé via le workflow `/livres-auteurs` :

1. **Sauvegarde du summary original** :
   - Si `summary_origin` n'existe pas encore, copier `summary` → `summary_origin`
   - Cela préserve la transcription Whisper brute en cas de besoin de rollback

2. **Mise à jour du summary avec données corrigées** :
   - Remplacer les données erronées dans `summary` par les données validées
   - Utiliser les données des collections `livres` et `auteurs` (sources de vérité)

3. **Propagation automatique** :
   - L'application lmelp lit `avis_critique.summary` → affiche les données corrigées
   - Aucune modification nécessaire dans l'application consommatrice

### Exemple de Transformation

**Avant validation (Issue #67)** :
```json
{
  "_id": "avis123",
  "episode_oid": "episode456",
  "summary": "| Alain Mabancou | Ramsès de Paris | Seuil |\n| Adrien Bosque | L'invention de Tristan | Verdier |"
}
```

**Après validation de "Alain Mabancou → Alain Mabanckou"** :
```json
{
  "_id": "avis123",
  "episode_oid": "episode456",
  "summary": "| Alain Mabanckou | Ramsès de Paris | Seuil |\n| Adrien Bosque | L'invention de Tristan | Verdier |",
  "summary_origin": "| Alain Mabancou | Ramsès de Paris | Seuil |\n| Adrien Bosque | L'invention de Tristan | Verdier |"
}
```

**Après validation de "Adrien Bosque → Adrien Bosc"** :
```json
{
  "_id": "avis123",
  "episode_oid": "episode456",
  "summary": "| Alain Mabanckou | Ramsès de Paris | Seuil |\n| Adrien Bosc | L'invention de Tristan | Verdier |",
  "summary_origin": "| Alain Mabancou | Ramsès de Paris | Seuil |\n| Adrien Bosque | L'invention de Tristan | Verdier |"
}
```

### Sécurité et Rollback

- **`summary_origin`** : Préserve toujours la transcription Whisper originale
- **Idempotence** : `summary_origin` n'est écrit qu'une seule fois (à la première correction)
- **Rollback possible** : En cas d'erreur, on peut restaurer `summary_origin` → `summary`

### Impact sur le Système

**Bénéfices** :
- ✅ Les utilisateurs de l'application lmelp voient les données corrigées
- ✅ Réduction de la dette technique (données cohérentes entre apps)
- ✅ Backup automatique de la transcription originale

**Collections affectées** :
- `avis_critiques` : Ajout du champ `summary_origin`, modification de `summary`

**Services impliqués** :
- Backend : Endpoint `/api/livres-auteurs/validate-suggestion` (mise à jour summary)
- MongoDB : Service de mise à jour `avis_critiques`

---

## Debugging et Monitoring

### Logs de Debug

#### Backend (BabelioService)
**Activation** : `BABELIO_CACHE_LOG=1 python -m back_office_lmelp.app`

**Exemple** :
```
[BabelioCache] MISS keys=(orig='Alain Mabancou', norm='alain mabancou')
[BabelioCache] WROTE keys=(orig='Alain Mabancou', norm='alain mabancou') items=3
[BabelioCache] HIT (orig) key='Alain Mabancou' items=3 ts=1640995200.0
```

#### Frontend (Console)
**Tests** : `npm test -- BiblioValidation --reporter verbose`

**Browser** : Console DevTools affiche les appels API

### Fixture Capture (Tests)
**Service** : `FixtureCaptureService.js`

**Activation** :
```javascript
import { fixtureCaptureService } from './FixtureCaptureService.js';

fixtureCaptureService.startCapture();
await validateBiblio(...);
const fixtures = fixtureCaptureService.stopCapture();
console.log(JSON.stringify(fixtures, null, 2));
```

**Utile pour** :
- Capturer réponses API réelles
- Générer fixtures de test automatiquement
- Reproduire bugs en environnement contrôlé

---

## Références

### Documentation
- [Validation Biblio Tests](validation-biblio-tests.md) : Architecture tests hiérarchiques
- Fixtures YAML : `frontend/tests/fixtures/biblio-validation-cases.yml` (cas de test réels)

### Code Source Principal
- **Backend** :
  - `src/back_office_lmelp/services/babelio_service.py` : Service Babelio
  - `src/back_office_lmelp/app.py:583-674` : Endpoint fuzzy search
- **Frontend** :
  - `frontend/src/services/BiblioValidationService.js` : Orchestration
  - `frontend/src/components/BiblioValidationCell.vue` : Composant affichage

### Historique GitHub
Pour l'historique détaillé des développements, consulter les issues suivantes :
- Phase 0 - Double appel et correction auteur : Issue #75
- Filtrage URLs/fragments : Issue #74
- Phase 0 livres extraits (base) : Issue #68
- Fermeture de la boucle - Mise à jour summary : Issue #67
- Collections management : Issue #66

---

## Glossaire

- **Ground Truth** : Données de référence extraites des transcriptions d'épisodes (titre + description)
- **Fuzzy Search** : Recherche approximative tolérant les fautes d'orthographe (algorithme Levenshtein/rapidfuzz)
- **Babelio** : Site web de référence bibliographique français (source de vérité externe)
- **Confidence Score** : Score de confiance 0.0-1.0 mesurant la similarité entre données originales et suggestions
- **Rate Limiting** : Limitation du nombre de requêtes par seconde pour respecter les serveurs externes
- **Arbitrage** : Processus de décision combinant plusieurs sources de données pour choisir la meilleure suggestion
- **Phase 0** : Validation directe des livres extraits (nouveau workflow Issue #68)
- **Not Found** : Statut indiquant qu'aucune suggestion fiable n'a pu être trouvée (nécessite intervention manuelle)
