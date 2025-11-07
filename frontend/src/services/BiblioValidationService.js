/**
 * BiblioValidationService - Service de validation bibliographique
 * Orchestration intelligente entre ground truth (fuzzy search) et Babelio
 */

import { fixtureCaptureService } from './FixtureCaptureService.js';

export class BiblioValidationService {
  constructor(dependencies = {}) {
    this.fuzzySearchService = dependencies.fuzzySearchService;
    this.babelioService = dependencies.babelioService;
    this.localAuthorService = dependencies.localAuthorService;
    this.livresAuteursService = dependencies.livresAuteursService;

    // Cache pour les livres extraits par épisode (Issue #85 - Performance)
    // Évite les appels API redondants lors de la validation de plusieurs livres
    // Key: episodeId, Value: Array<{author, title}>
    this._extractedBooksCache = new Map();
  }

  /**
   * Wrapper pour fuzzy search avec capture optionnelle
   */
  async _searchEpisodeWithCapture(episodeId, searchTerms) {
    const result = await this.fuzzySearchService.searchEpisode(episodeId, searchTerms);

    // Capturer l'appel si la capture est active
    if (fixtureCaptureService.isCapturing) {
      fixtureCaptureService.logCall(
        'fuzzySearchService',
        'searchEpisode',
        { episode_id: episodeId, query_title: searchTerms.title, query_author: searchTerms.author },
        result
      );
    }

    return result;
  }

  /**
   * Wrapper pour vérification auteur avec capture optionnelle
   */
  async _verifyAuthorWithCapture(author) {
    const result = await this.babelioService.verifyAuthor(author);

    // Capturer l'appel si la capture est active
    if (fixtureCaptureService.isCapturing) {
      fixtureCaptureService.logCall(
        'babelioService',
        'verifyAuthor',
        { type: 'author', name: author },
        result
      );
    }

    return result;
  }

  /**
   * Wrapper pour vérification livre avec capture optionnelle
   */
  async _verifyBookWithCapture(title, author) {
    const result = await this.babelioService.verifyBook(title, author);

    // Capturer l'appel si la capture est active
    if (fixtureCaptureService.isCapturing) {
      fixtureCaptureService.logCall(
        'babelioService',
        'verifyBook',
        { type: 'book', title: title, author: author },
        result
      );
    }

    return result;
  }

  /**
   * Phase 0: Teste directement les livres extraits avec Babelio
   * @param {Object} original - Données originales saisies par l'utilisateur
   * @param {string} episodeId - ID de l'épisode
   * @returns {Promise<Object|null>} Résultat si succès, null si échec
   * @private
   */
  async _tryPhase0DirectValidation(original, episodeId) {

    // Vérifier si les données originales correspondent exactement à un livre extrait
    const extractedBooks = await this._getExtractedBooks(episodeId);

    const matchingExtractedBook = extractedBooks.find(book =>
      book.author === original.author && book.title === original.title
    );

    if (!matchingExtractedBook) {
      return null;
    }


    try {
      // 1er appel Babelio avec le livre extrait
      const bookValidation = await this._verifyBookWithCapture(
        matchingExtractedBook.title,
        matchingExtractedBook.author
      );

      if (bookValidation && bookValidation.status === 'verified') {
        // Issue #75: Double appel de confirmation si confidence entre 0.85 et 0.99
        const confidence = bookValidation.confidence_score || 0;

        if (confidence >= 0.85 && confidence < 1.0) {
          // Confidence entre 0.85 et 0.99 → faire un 2ème appel de confirmation
          const suggestedAuthor = bookValidation.babelio_suggestion_author;
          const suggestedTitle = bookValidation.babelio_suggestion_title;

          if (suggestedAuthor && suggestedTitle) {
            try {
              // 2ème appel Babelio avec les valeurs suggérées
              const confirmationValidation = await this._verifyBookWithCapture(
                suggestedTitle,
                suggestedAuthor
              );

              // Si le 2ème appel confirme avec confidence 1.0, utiliser la confirmation
              if (confirmationValidation &&
                  confirmationValidation.status === 'verified' &&
                  confirmationValidation.confidence_score === 1.0) {
                return {
                  status: 'verified',
                  data: {
                    original,
                    suggested: {
                      author: confirmationValidation.babelio_suggestion_author || suggestedAuthor,
                      title: confirmationValidation.babelio_suggestion_title || suggestedTitle
                    },
                    source: 'babelio_phase0_confirmed',
                    confidence_score: 1.0,
                    corrections: {
                      author: original.author !== suggestedAuthor,
                      title: original.title !== suggestedTitle
                    }
                  }
                };
              }
              // Si le 2ème appel ne confirme pas avec confidence 1.0, retourner null pour fallback Phase 1
            } catch (error) {
              // Erreur sur le 2ème appel → fallback Phase 1
            }
          }

          // Si pas de suggestion ou 2ème appel échoué, retourner null pour fallback Phase 1
          return null;
        }

        // Confidence = 1.0 → retour direct sans 2ème appel
        return {
          status: 'verified',
          data: {
            original,
            suggested: {
              author: bookValidation.babelio_suggestion_author || matchingExtractedBook.author,
              title: bookValidation.babelio_suggestion_title || matchingExtractedBook.title
            },
            source: 'babelio_phase0',
            confidence_score: bookValidation.confidence_score || 1.0,
            corrections: {
              author: false,
              title: false
            }
          }
        };
      }

      // Enrichissement Phase 0 : Si le livre n'est pas trouvé, essayer de corriger l'auteur
      if (bookValidation && bookValidation.status === 'not_found') {
        try {
          // Vérifier si l'auteur peut être corrigé
          const authorValidation = await this._verifyAuthorWithCapture(matchingExtractedBook.author);

          if (authorValidation &&
              (authorValidation.status === 'corrected' || authorValidation.status === 'verified') &&
              authorValidation.babelio_suggestion) {
            // L'auteur a une suggestion → essayer avec l'auteur corrigé
            const correctedAuthor = authorValidation.babelio_suggestion;

            const bookWithCorrectedAuthor = await this._verifyBookWithCapture(
              matchingExtractedBook.title,
              correctedAuthor
            );

            // Si le livre est trouvé avec l'auteur corrigé et confidence 1.0
            if (bookWithCorrectedAuthor &&
                bookWithCorrectedAuthor.status === 'verified' &&
                bookWithCorrectedAuthor.confidence_score === 1.0) {
              return {
                status: 'verified',
                data: {
                  original,
                  suggested: {
                    author: bookWithCorrectedAuthor.babelio_suggestion_author || correctedAuthor,
                    title: bookWithCorrectedAuthor.babelio_suggestion_title || matchingExtractedBook.title
                  },
                  source: 'babelio_phase0_author_correction',
                  confidence_score: 1.0,
                  corrections: {
                    author: true,  // Auteur corrigé
                    title: false
                  }
                }
              };
            }
          }
        } catch (error) {
          // Erreur sur la correction auteur → continuer vers fallback Phase 1
        }
      }
    } catch (error) {
      // Erreur silencieuse - on retombe sur le workflow normal
    }

    return null;
  }

  /**
   * Récupère les livres extraits pour un épisode donné depuis le backend
   * Utilise un cache pour éviter les appels API redondants (Issue #85 - Performance)
   * @param {string} episodeId - ID de l'épisode
   * @returns {Promise<Array>} Liste des livres extraits ({author, title})
   * @private
   */
  async _getExtractedBooks(episodeId) {
    if (!episodeId || !this.livresAuteursService) {
      return [];
    }

    // Vérifier si les livres sont déjà en cache
    if (this._extractedBooksCache.has(episodeId)) {
      return this._extractedBooksCache.get(episodeId);
    }

    try {
      const livresAuteurs = await this.livresAuteursService.getLivresAuteurs({ episode_oid: episodeId });

      // Transformer le format API {auteur, titre} en format {author, title}
      const transformedBooks = livresAuteurs.map(livre => ({
        author: livre.auteur,
        title: livre.titre
      }));

      // Mettre en cache pour les prochains appels
      this._extractedBooksCache.set(episodeId, transformedBooks);

      return transformedBooks;
    } catch (error) {
      console.error(`Failed to fetch extracted books for episode ${episodeId}:`, error);
      return [];
    }
  }

  /**
   * Vide le cache des livres extraits (Issue #85 - Performance)
   * @param {string|null} episodeId - ID de l'épisode à vider, ou null pour tout vider
   */
  clearExtractedBooksCache(episodeId = null) {
    if (episodeId) {
      this._extractedBooksCache.delete(episodeId);
    } else {
      this._extractedBooksCache.clear();
    }
  }

  /**
   * Valide une entrée bibliographique avec arbitrage intelligent
   * @param {string} author - Auteur original
   * @param {string} title - Titre original
   * @param {string} publisher - Éditeur
   * @param {string|null} episodeId - ID épisode pour ground truth (optionnel)
   * @returns {Promise<Object>} Résultat de validation
   */
  async validateBiblio(author, title, publisher, episodeId) {
    try {
      const original = { author, title, publisher };

      // Phase 0: Test direct des livres extraits avec Babelio (NEW)
      if (episodeId) {
        const phase0Result = await this._tryPhase0DirectValidation(original, episodeId);
        if (phase0Result) {
          return phase0Result;
        }
      }

      // Étape 1: Tentative ground truth si episodeId fourni
      let groundTruthResult = null;
      if (episodeId) {
        try {
          groundTruthResult = await this._searchEpisodeWithCapture(
            episodeId,
            { author, title }
          );
        } catch (error) {
          // Si ground truth échoue, continue avec Babelio seulement
        }
      }

      // Étape 2: Validation Babelio de l'auteur
      const authorValidation = await this._verifyAuthorWithCapture(author) || { status: 'not_found' };

      // Vérifier les erreurs de fixture dès la première réponse
      if (authorValidation.status === 'fixture_error') {
        return {
          status: 'fixture_error',
          data: {
            original,
            error: authorValidation.error_message || 'Missing test fixtures',
            reason: 'fixture_missing'
          }
        };
      }

      // Étape 3: Validation Babelio du livre
      let bookValidation;

      // Cas 1: Auteur avec suggestion (corrected OU verified avec différence)
      if (this._authorHasSuggestion(authorValidation)) {
        // D'abord essayer avec l'auteur original
        bookValidation = await this._verifyBookWithCapture(title, author) || { status: 'not_found' };

        // Vérifier erreur de fixture
        if (bookValidation.status === 'fixture_error') {
          return {
            status: 'fixture_error',
            data: {
              original,
              error: bookValidation.error_message || 'Missing test fixtures',
              reason: 'fixture_missing'
            }
          };
        }

        // Si ça échoue, essayer avec l'auteur suggéré
        if (bookValidation.status === 'not_found') {
          bookValidation = await this._verifyBookWithCapture(
            title,
            authorValidation.babelio_suggestion
          ) || { status: 'not_found' };

          // Vérifier erreur de fixture sur le deuxième essai
          if (bookValidation.status === 'fixture_error') {
            return {
              status: 'fixture_error',
              data: {
                original,
                error: bookValidation.error_message || 'Missing test fixtures',
                reason: 'fixture_missing'
              }
            };
          }
        }
      } else {
        // Cas 2: Pas de suggestion d'auteur, test avec l'auteur original seulement
        bookValidation = await this._verifyBookWithCapture(title, author) || { status: 'not_found' };

        // Vérifier erreur de fixture
        if (bookValidation.status === 'fixture_error') {
          return {
            status: 'fixture_error',
            data: {
              original,
              error: bookValidation.error_message || 'Missing test fixtures',
              reason: 'fixture_missing'
            }
          };
        }
      }

      // Étape 4: Arbitrage et décision finale
      const result = this._arbitrateResults({
        original,
        groundTruthResult,
        authorValidation,
        bookValidation,
        episodeId
      });

      // Capturer le résultat final end-to-end si la capture est active
      if (fixtureCaptureService.isCapturing) {
        fixtureCaptureService.logCall(
          'biblioValidationService',
          'validateBiblio',
          { author, title, publisher, episodeId },
          result
        );
      }

      return result;

    } catch (error) {
      const errorResult = {
        status: 'error',
        data: {
          original: { author, title, publisher },
          error: error.message,
          attempts: episodeId ? ['ground_truth', 'babelio'] : ['babelio']
        }
      };

      // Capturer aussi les erreurs si la capture est active
      if (fixtureCaptureService.isCapturing) {
        fixtureCaptureService.logCall(
          'biblioValidationService',
          'validateBiblio',
          { author, title, publisher, episodeId },
          errorResult
        );
      }

      return errorResult;
    }
  }

  /**
   * Arbitre entre les différentes sources de validation
   * @private
   */
  async _arbitrateResults({
    original,
    groundTruthResult,
    authorValidation,
    bookValidation,
    episodeId
  }) {
    // 🐛 DEBUG: Arbitrage start

    // Cas 1: Ground truth disponible avec matches de qualité - PRIORITAIRE
    const hasGroundTruth = groundTruthResult?.found_suggestions;
    const hasGoodMatches = hasGroundTruth && this._hasGoodGroundTruthMatches(groundTruthResult);

    if (hasGroundTruth && hasGoodMatches) {
  const groundTruthSuggestion = this._extractGroundTruthSuggestion(groundTruthResult, original);

      // Reject ground truth suggestion if title is invalid (URL, fragment, etc.)
      if (!groundTruthSuggestion.title || !this._isValidTitleSuggestion(groundTruthSuggestion.title, original.title)) {
        // Fall through to Babelio-only validation
      } else {
        // Vérifier la cohérence avec Babelio
        return await this._validateGroundTruthSuggestion(
          original,
          groundTruthSuggestion,
          bookValidation,
          groundTruthResult,
          authorValidation
        );
      }
    }

    // Cas 2: Ground truth avec matches décents (seuils assouplis) - PRIORITAIRE aussi
    if (hasGroundTruth && this._hasDecentGroundTruthMatches(groundTruthResult)) {
  const groundTruthSuggestion = this._extractGroundTruthSuggestion(groundTruthResult, original);

      // Reject ground truth suggestion if title is invalid (URL, fragment, etc.)
      if (!groundTruthSuggestion.title || !this._isValidTitleSuggestion(groundTruthSuggestion.title, original.title)) {
        // Fall through to Babelio-only validation
      } else {
        // Vérifier la cohérence avec Babelio
        return await this._validateGroundTruthSuggestion(
          original,
          groundTruthSuggestion,
          bookValidation,
          groundTruthResult,
          authorValidation
        );
      }
    }

    // Cas 3: Validation directe - auteur ET livre tous deux vérifiés
    const isDirectValidation = (
      authorValidation?.status === 'verified' &&
      !this._authorHasSuggestion(authorValidation) && // Auteur exact, pas de suggestion
      bookValidation?.status === 'verified' && // Livre doit être vérifié aussi
      (!hasGroundTruth || (!hasGoodMatches && !this._hasDecentGroundTruthMatches(groundTruthResult))) // Pas de ground truth ou ground truth pas utilisable
    );

    if (isDirectValidation) {
      return {
        status: 'verified',
        data: {
          original,
          source: 'babelio',
          confidence_score: Math.min(
            authorValidation.confidence_score || 1.0,
            bookValidation.confidence_score || 1.0
          )
        }
      };
    }

    // Cas 4: Suggestion Babelio seule
    if (this._hasBabelioSuggestion(authorValidation, bookValidation)) {
      // Rejeter les suggestions Babelio avec score trop faible (fantaisistes)
      const bookScore = bookValidation?.confidence_score || 0;
      const authorScore = authorValidation?.confidence_score || 0;
      const maxBabelioScore = Math.max(bookScore, authorScore);

      // If we have a book-level correction (status 'corrected' or 'verified'),
      // prefer that even if the confidence scores are lower than the usual
      // threshold. Otherwise require a high-confidence suggestion.
      const isBookCorrected = bookValidation && (bookValidation.status === 'corrected' || bookValidation.status === 'verified');

      // Relax score threshold only when we have BOTH a book-level correction AND
      // an author validation (either verified or corrected). This avoids
      // accepting low-confidence book matches when the author is unknown.
      const hasAuthorInfo = (authorValidation && authorValidation.status && authorValidation.status !== 'not_found');
      const scoreThreshold = (isBookCorrected && hasAuthorInfo) ? 0.0 : 0.8;

      if (maxBabelioScore < scoreThreshold) {
        return {
          status: 'not_found',
          data: {
            original,
            reason: 'no_reliable_match_found',
            attempts: episodeId ? ['ground_truth', 'babelio'] : ['babelio']
          }
        };
      }

      return await this._validateBabelioSuggestion(original, authorValidation, bookValidation);
    }

    // Cas 5: Conflit entre sources ou aucune suggestion fiable
    if (groundTruthResult && !groundTruthResult.found_suggestions) {
      if (bookValidation.status === 'corrected' && bookValidation.confidence_score < 0.5) {
        return {
          status: 'not_found',
          data: {
            original,
            reason: 'conflicting_low_confidence_sources',
            attempts: ['ground_truth', 'babelio']
          }
        };
      }
    }

    // Cas 6: Phase 2.5 - Recherche par titre seul avec double confirmation (Issue #80)
    // Active uniquement si toutes les phases précédentes ont échoué
    const shouldTryPhase25 = (
      bookValidation?.status === 'not_found' &&
      authorValidation?.status === 'not_found'
    );

    if (shouldTryPhase25) {
      try {
        // Étape 1 : Recherche Babelio avec titre seul (sans auteur)
        const titleOnlyResult = await this._verifyBookWithCapture(original.title, null);

        // Vérifier si on a une suggestion d'auteur
        if (
          titleOnlyResult &&
          titleOnlyResult.status !== 'not_found' &&
          titleOnlyResult.babelio_suggestion_title &&
          titleOnlyResult.babelio_suggestion_author
        ) {
          // Nettoyer le titre suggéré (enlever "..." à la fin)
          const cleanedTitle = titleOnlyResult.babelio_suggestion_title.replace(/\.\.\.+$/, '').trim();

          // Étape 2 : Confirmation avec auteur suggéré + titre nettoyé
          const confirmationResult = await this._verifyBookWithCapture(
            cleanedTitle,
            titleOnlyResult.babelio_suggestion_author
          );

          // Vérifier si la confirmation est réussie (confidence >= 0.95)
          if (
            confirmationResult &&
            confirmationResult.confidence_score >= 0.95
          ) {
            // ✅ Phase 2.5 réussie - Retourner suggestion confirmée
            return {
              status: 'suggestion',
              data: {
                original,
                suggested: {
                  author: titleOnlyResult.babelio_suggestion_author,
                  title: titleOnlyResult.babelio_suggestion_title,
                  publisher: original.publisher
                },
                corrections: {
                  author: true,  // Auteur toujours corrigé en Phase 2.5
                  title: original.title !== titleOnlyResult.babelio_suggestion_title,
                  publisher: false
                },
                source: 'babelio_title_only_confirmed',
                confidence_score: confirmationResult.confidence_score,
                babelio_url: titleOnlyResult.babelio_url || null
              }
            };
          }
          // ❌ Confirmation échoue (confidence < 0.95) → fallback not_found
        }
        // ❌ Pas de suggestion auteur au 1er appel → fallback not_found
      } catch (error) {
        // ❌ Erreur Phase 2.5 → fallback not_found
        console.warn('Phase 2.5 failed:', error);
      }
    }

    // Cas 7: Aucune source ne trouve de match fiable
    return {
      status: 'not_found',
      data: {
        original,
        reason: this._determineNotFoundReason(authorValidation, bookValidation),
        attempts: episodeId ? ['ground_truth', 'babelio'] : ['babelio']
      }
    };
  }

  /**
   * Vérifie si ground truth a des matches de qualité
   * @private
   */
  _hasGoodGroundTruthMatches(groundTruthResult) {
    // Support des deux formats : API utilise titleMatches, tests utilisent title_matches
    const titleMatches = groundTruthResult.titleMatches || groundTruthResult.title_matches;
    const authorMatches = groundTruthResult.authorMatches || groundTruthResult.author_matches;

    // Filter out invalid title suggestions before checking scores
    const validTitleMatches = (titleMatches || []).filter(tm => {
      const text = (tm[0] || '').replace('📖 ', '').trim();
      return this._isValidTitleSuggestion(text, null);
    });

    const titleMatch = validTitleMatches?.[0];
    const authorMatch = authorMatches?.[0];

    // Format des matches : [["text", score], ...]
    const titleScore = titleMatch?.[1] || 0;
    const authorScore = authorMatch?.[1] || 0;

    // Debug logging pour diagnostiquer les cas non détectés (commenté pour production)
    // if (groundTruthResult.found_suggestions) {
    //   console.debug('Ground truth matches:', {
    //     titleScore,
    //     authorScore,
    //     titleThresholdMet: titleScore >= 80,
    //     authorThresholdMet: authorScore >= 80,
    //     overallResult: titleScore >= 80 && authorScore >= 80
    //   });
    // }

    return (
      titleScore >= 80 &&
      authorScore >= 80 && // Réduit de 90 à 80 pour les noms complexes
      groundTruthResult.found_suggestions === true
    );
  }

  /**
   * Vérifie si ground truth a des matches décents (seuils assouplis pour cas difficiles)
   * @private
   */
  _hasDecentGroundTruthMatches(groundTruthResult) {
    // Support des deux formats : API utilise titleMatches, tests utilisent title_matches
    const titleMatches = groundTruthResult.titleMatches || groundTruthResult.title_matches;
    const authorMatches = groundTruthResult.authorMatches || groundTruthResult.author_matches;

    // Filter out invalid title suggestions before checking scores
    const validTitleMatches = (titleMatches || []).filter(tm => {
      const text = (tm[0] || '').replace('📖 ', '').trim();
      return this._isValidTitleSuggestion(text, null);
    });

    const titleMatch = validTitleMatches?.[0];

    // Format des matches : [["text", score], ...]
    const titleScore = titleMatch?.[1] || 0;

    // Pour l'auteur, calculer un score basé sur les fragments disponibles
    let authorScore = 0;
    if (authorMatches && authorMatches.length > 0) {
      if (authorMatches.length === 1) {
        // Un seul fragment d'auteur
        authorScore = authorMatches[0][1] || 0;
      } else {
        // Plusieurs fragments : prendre le score minimum des deux meilleurs
        // pour s'assurer que les deux fragments sont de qualité décente
        const sortedMatches = authorMatches
          .filter(match => match[1] >= 70) // Filtrer les fragments très faibles
          .sort((a, b) => b[1] - a[1]); // Trier par score décroissant

        if (sortedMatches.length >= 2) {
          // Score basé sur les deux meilleurs fragments
          authorScore = Math.min(sortedMatches[0][1], sortedMatches[1][1]);
        } else if (sortedMatches.length === 1) {
          // Un seul fragment de qualité
          authorScore = sortedMatches[0][1];
        }
      }
    }

    // Seuils assouplis pour détecter des cas comme "Colcause" → "Kolkhoze"
    // Cas spécial : si l'auteur est parfait (90+), accepter des titres plus faibles
    const authorIsPerfect = authorScore >= 85;
    const titleThreshold = authorIsPerfect ? 35 : 75; // Seuil titre réduit si auteur parfait

    const result = (
      titleScore >= titleThreshold && // Seuil adaptatif selon qualité auteur
      authorScore >= 75 && // Seuil assoupli pour variantes orthographiques
      groundTruthResult.found_suggestions === true
    );


    return result;
  }

  /**
   * Extrait la suggestion de ground truth
   * @private
   */
  _extractGroundTruthSuggestion(groundTruthResult, original = { title: '' }) {
    // Support des deux formats : API utilise titleMatches, tests utilisent title_matches
    const titleMatches = groundTruthResult.titleMatches || groundTruthResult.title_matches;
    const authorMatchesArray = groundTruthResult.authorMatches || groundTruthResult.author_matches;

    // Format des matches : [["📖 text", score], ...]
    // Logique intelligente : choisir le titre avec le meilleur compromis entre
    // score renvoyé par le fuzzy engine et similarité au titre original.
    let titleMatch = '';
    if (Array.isArray(titleMatches) && titleMatches.length > 0) {
      // Normalizer helper
      const normalize = s => (s || '').toString().replace(/[^\p{L}\p{N}]+/gu, ' ').trim().toLowerCase();

      const origNorm = normalize(original.title || '');


      // Levenshtein distance (normalized) for better similarity measure
      const levenshtein = (a, b) => {
        if (!a || !b) return Math.max(a?.length || 0, b?.length || 0) ? 1 : 0;
        const m = a.length, n = b.length;
        const dp = Array.from({ length: m + 1 }, () => new Array(n + 1).fill(0));
        for (let i = 0; i <= m; i++) dp[i][0] = i;
        for (let j = 0; j <= n; j++) dp[0][j] = j;
        for (let i = 1; i <= m; i++) {
          for (let j = 1; j <= n; j++) {
            const cost = a[i - 1] === b[j - 1] ? 0 : 1;
            dp[i][j] = Math.min(dp[i - 1][j] + 1, dp[i][j - 1] + 1, dp[i - 1][j - 1] + cost);
          }
        }
        const dist = dp[m][n];
        // normalized similarity: 1 - dist / maxLen
        return 1 - dist / Math.max(m, n);
      };

      // Score each candidate by combining similarity with fuzzy score, but
      // prioritize similarity more (70% similarity, 30% fuzzy score)
      const scored = titleMatches.map(tm => {
        const text = (tm[0] || '').replace('📖 ', '').trim();
        const score = (tm[1] || 0) / 100; // normalized 0-1
        const candNorm = normalize(text);
        const sim = origNorm ? levenshtein(origNorm, candNorm) : 0;
        const combined = sim * 0.7 + score * 0.3;
        return { text, score: score * 100, combined };
      })
      // Filter out invalid suggestions before sorting
      .filter(candidate => this._isValidTitleSuggestion(candidate.text, original.title))
      .sort((a, b) => b.combined - a.combined);

      titleMatch = scored[0]?.text || '';
    }

    // Pour l'auteur, essayer de reconstruire le nom complet à partir des matches
    const authorMatches = authorMatchesArray || [];
    let reconstructedAuthor = '';

    if (authorMatches.length >= 2) {
      // Cas complexe : plusieurs fragments d'auteur (ex: ["Alikavazovic", 82], ["Jakuta", 78])
      // Heuristique : prénom puis nom de famille
      const sortedMatches = authorMatches
        .filter(match => match[1] >= 70) // Garder les matches décents
        .sort((a, b) => b[1] - a[1]); // Trier par score décroissant

      if (sortedMatches.length >= 2) {
        // Filtrer les mots parasites français courants
        const isNoiseWord = (word) => {
          const commonNoiseWords = [
            'pour', 'Pour', 'de', 'De', 'du', 'Du', 'la', 'La', 'le', 'Le',
            'et', 'Et', 'des', 'Des', 'les', 'Les', 'un', 'Un', 'une', 'Une',
            'dans', 'Dans', 'avec', 'Avec', 'sur', 'Sur', 'par', 'Par'
          ];
          return commonNoiseWords.includes(word.trim());
        };

        // Filtrer les mots parasites avant reconstruction
        const cleanedMatches = sortedMatches.filter(match => !isNoiseWord(match[0]));

        if (cleanedMatches.length >= 2) {
          // Identifier prénom vs nom avec heuristiques améliorées
          const [first, second] = cleanedMatches;

        // Fonction pour nettoyer les fragments d'auteur
        const cleanAuthorFragment = (fragment) => {
          return fragment
            .replace(/^d'/, '') // Enlever "d'" du début
            .replace(/^de\s+/, '') // Enlever "de " du début
            .replace(/^l'/, '') // Enlever "l'" du début
            .replace(/^\w+\s+de\s+/, '') // Enlever "quelque chose de "
            .trim();
        };

        // Nettoyer les fragments
        const cleanFirst = cleanAuthorFragment(first[0]);
        const cleanSecond = cleanAuthorFragment(second[0]);

        // Heuristiques pour identifier prénom vs nom
        const isFirstNameLike = (str) => {
          const cleaned = cleanAuthorFragment(str);
          // Unicode-aware detection: commence par une lettre majuscule (accentuée possible)
          // et contient ensuite des lettres minuscules, éventuellement des apostrophes ou traits d'union.
          // On limite la longueur pour éviter de confondre noms composés très longs.
          return cleaned.length > 0 &&
                 cleaned.length < 20 &&
                 !cleaned.includes(' ') &&
                 /^[\p{Lu}][\p{Ll}'-]+$/u.test(cleaned);
        };

        let firstName, lastName;

        // Priorité 1: Un fragment est clairement un prénom, l'autre un nom
        if (isFirstNameLike(first[0]) && !isFirstNameLike(second[0])) {
          firstName = cleanFirst;
          lastName = cleanSecond;
        } else if (isFirstNameLike(second[0]) && !isFirstNameLike(first[0])) {
          firstName = cleanSecond;
          lastName = cleanFirst;
        } else if (cleanFirst && cleanSecond) {
          // Priorité 2: Les deux sont valides, utiliser la longueur
          if (cleanFirst.length <= cleanSecond.length) {
            firstName = cleanFirst;
            lastName = cleanSecond;
          } else {
            firstName = cleanSecond;
            lastName = cleanFirst;
          }
        } else {
          // Fallback: prendre le premier fragment nettoyé disponible
          firstName = cleanFirst || cleanSecond || first[0];
          lastName = cleanSecond && cleanFirst ? cleanSecond : (second[0] !== firstName ? second[0] : '');
        }

        // Construire le nom final
        if (firstName && lastName && firstName !== lastName) {
          reconstructedAuthor = `${firstName} ${lastName}`;
        } else if (firstName) {
          reconstructedAuthor = firstName;
        } else {
          reconstructedAuthor = sortedMatches[0]?.[0] || '';
        }

        // Debug logs (commenté pour production)
        // console.debug('Author reconstruction:', {
        //   sortedMatches: sortedMatches.map(m => `${m[0]}(${m[1]})`),
        //   cleanedMatches: cleanedMatches.map(m => `${m[0]}(${m[1]})`),
        //   firstName,
        //   lastName,
        //   reconstructedAuthor
        // });
        } else if (cleanedMatches.length === 1) {
          // Un seul match valide après filtrage
          reconstructedAuthor = cleanedMatches[0][0];
        } else {
          // Fallback: utiliser le premier match original si filtrage trop agressif
          reconstructedAuthor = sortedMatches[0]?.[0] || '';
        }
      } else {
        reconstructedAuthor = sortedMatches[0]?.[0] || '';
      }
    } else if (authorMatches.length === 1) {
      // Cas simple : un seul match d'auteur
      reconstructedAuthor = authorMatches[0][0];
    }

    return {
      title: (titleMatch || '').replace('📖 ', '').trim(), // Enlever le préfixe et espaces
      author: reconstructedAuthor.trim()
    };
  }

  /**
   * Valide si une suggestion de titre est acceptable
   * Filtre les URLs, les fragments trop courts, et autres suggestions invalides
   * @private
   */
  _isValidTitleSuggestion(suggestion, originalTitle) {
    if (!suggestion || typeof suggestion !== 'string') {
      return false;
    }

    const trimmed = suggestion.trim();

    // Rejeter les URLs
    if (trimmed.includes('http://') || trimmed.includes('https://') || trimmed.includes('www.')) {
      return false;
    }

    // Rejeter les URLs partielles typiques
    if (trimmed.includes('franceinter.fr') || trimmed.includes('.com') || trimmed.includes('.fr')) {
      return false;
    }

    // Rejeter les fragments trop courts (< 3 caractères) sauf si c'est exactement le titre original
    if (trimmed.length < 3 && trimmed.toLowerCase() !== (originalTitle || '').toLowerCase()) {
      return false;
    }

    // Rejeter les mots isolés qui ne ressemblent pas à des titres
    // Un titre devrait avoir au moins 2 mots OU être un mot long et significatif (>= 8 lettres)
    // Ceci filtre les prénoms isolés comme "Amélie" (6 lettres) qui ne sont pas des titres
    const words = trimmed.split(/\s+/).filter(w => w.length > 0);
    if (words.length === 1 && trimmed.length < 8) {
      return false;
    }

    return true;
  }

  /**
   * Valide une suggestion de ground truth avec Babelio
   * @private
   */
  async _validateGroundTruthSuggestion(original, groundTruthSuggestion, initialBookValidation, groundTruthResult, authorValidation) {
    try {
      // Si initialBookValidation correspond déjà à la suggestion ground truth, utiliser ce résultat
      if (initialBookValidation?.status === 'verified' &&
          initialBookValidation.original_title === groundTruthSuggestion.title &&
          initialBookValidation.original_author === groundTruthSuggestion.author) {

        // Vérifier si la suggestion est identique à l'original
        const isIdentical = (
          original.title === groundTruthSuggestion.title &&
          original.author === groundTruthSuggestion.author
        );

        return {
          status: isIdentical ? 'verified' : 'suggestion',
          data: {
            original,
            suggested: groundTruthSuggestion,
            corrections: {
              title: original.title !== groundTruthSuggestion.title,
              author: original.author !== groundTruthSuggestion.author
            },
            source: 'ground_truth+babelio',
            confidence_score: initialBookValidation.confidence_score || 1.0
          }
        };
      }

      // Sinon, si ground truth est 'decente' acceptez la suggestion immédiatement
      // (source: ground_truth) et n'exigez pas toujours la confirmation Babelio.
      if (this._hasDecentGroundTruthMatches(groundTruthResult)) {
        return {
          status: 'suggestion',
          data: {
              original,
              // Prefer Babelio textual suggestion for author when present to keep "Prénoms Nom" ordering
              suggested: {
                title: groundTruthSuggestion.title,
                author: (authorValidation && authorValidation.babelio_suggestion) || (initialBookValidation && initialBookValidation.babelio_suggestion_author) || groundTruthSuggestion.author
              },
              corrections: {
                title: original.title !== groundTruthSuggestion.title,
                author: original.author !== ((authorValidation && authorValidation.babelio_suggestion) || (initialBookValidation && initialBookValidation.babelio_suggestion_author) || groundTruthSuggestion.author)
              },
              source: 'ground_truth',
              confidence_score: 0.75
            }
        };
      }

      // Sinon, vérifier que la suggestion ground truth est validée par Babelio
      // Normaliser la casse du titre pour correspondre aux fixtures
      const normalizedTitle = groundTruthSuggestion.title.toLowerCase();
      const groundTruthBookValidation = await this._verifyBookWithCapture(
        normalizedTitle,
        groundTruthSuggestion.author
      ) || { status: 'not_found' };

      if (groundTruthBookValidation.status === 'verified') {
        // Vérifier si la suggestion est identique à l'original
        const isIdentical = (
          original.title === groundTruthSuggestion.title &&
          original.author === groundTruthSuggestion.author
        );

        return {
          status: isIdentical ? 'verified' : 'suggestion',
          data: {
            original,
            suggested: groundTruthSuggestion,
            corrections: {
              title: original.title !== groundTruthSuggestion.title,
              author: original.author !== groundTruthSuggestion.author
            },
            source: 'ground_truth+babelio',
            confidence_score: groundTruthBookValidation.confidence_score || 1.0
          }
        };
      }

      // Si ground truth n'est pas confirmé par Babelio, utiliser Babelio seul
      if (this._hasBabelioSuggestion(null, initialBookValidation)) {
        return this._validateBabelioSuggestion(original, null, initialBookValidation);
      }

      return {
        status: 'not_found',
        data: {
          original,
          reason: 'ground_truth_not_confirmed_by_babelio',
          attempts: ['ground_truth', 'babelio']
        }
      };
    } catch (error) {
      // En cas d'erreur, fallback sur Babelio
      if (this._hasBabelioSuggestion(null, initialBookValidation)) {
        return this._validateBabelioSuggestion(original, null, initialBookValidation);
      }
      throw error;
    }
  }

  /**
   * Vérifie si l'auteur a une suggestion (corrected ou verified avec différence)
   * @private
   */
  _authorHasSuggestion(authorValidation) {
    return authorValidation && (
      authorValidation.status === 'corrected' ||
      (authorValidation.status === 'verified' &&
       authorValidation.babelio_suggestion &&
       authorValidation.babelio_suggestion !== authorValidation.original)
    );
  }

  /**
   * Vérifie si Babelio propose une suggestion valide
   * @private
   */
  _hasBabelioSuggestion(authorValidation, bookValidation) {
    // Cas auteur : utilise la méthode dédiée
    const hasAuthorSuggestion = this._authorHasSuggestion(authorValidation);

    // Cas livre : suggestion si status 'corrected' ou 'verified'
    const hasBookSuggestion = bookValidation && (
      bookValidation.status === 'corrected' ||
      bookValidation.status === 'verified'
    );

    return hasAuthorSuggestion || hasBookSuggestion;
  }

  /**
   * Valide une suggestion Babelio
   * @private
   */
  async _validateBabelioSuggestion(original, authorValidation, bookValidation) {
    // Prefer book-level suggestions when available: a book-correction contains
    // both suggested title and suggested author and should generally override
    // an author-only suggestion coming from verifyAuthor.

    // If we already have a book-level result that suggests a correction, use it.
    if (bookValidation && (bookValidation.status === 'corrected' || bookValidation.status === 'verified')) {
  // Prefer the human-readable textual suggestion coming from Babelio fixtures
  // (babelio_suggestion / babelio_suggestion_author) which already have
  // the correct "Prénoms Nom" ordering. Fall back to reconstructed
  // fragments if textual suggestion isn't available.
      // If Babelio provides structured data, prefer prenoms + nom ordering
      const bookBabelioData = bookValidation && bookValidation.babelio_data;
      const authorBabelioData = authorValidation && authorValidation.babelio_data;
      const structuredAuthor = (bookBabelioData && (bookBabelioData.prenoms || bookBabelioData.prenoms === '') && bookBabelioData.nom)
        ? `${bookBabelioData.prenoms} ${bookBabelioData.nom}`
        : (authorBabelioData && (authorBabelioData.prenoms || authorBabelioData.prenoms === '') && authorBabelioData.nom)
          ? `${authorBabelioData.prenoms} ${authorBabelioData.nom}`
          : null;

      const suggestedAuthor = structuredAuthor || bookValidation.babelio_suggestion_author || (authorValidation && authorValidation.babelio_suggestion) || original.author;
  const suggestedTitle = bookValidation.babelio_suggestion_title || original.title;

      return {
        status: 'suggestion',
        data: {
          original,
          suggested: {
            title: suggestedTitle,
            author: suggestedAuthor
          },
          corrections: {
            title: original.title !== suggestedTitle,
            author: original.author !== suggestedAuthor
          },
          source: 'babelio',
          confidence_score: bookValidation.confidence_score || (authorValidation && authorValidation.confidence_score) || 0
        }
      };
    }

    // If author has a suggestion but we don't have a book-level suggestion, try to
    // validate the suggestion by checking the book for the suggested author.
    if (this._authorHasSuggestion(authorValidation)) {
      try {
        const coherenceCheck = await this._verifyBookWithCapture(
          original.title,
          authorValidation.babelio_suggestion
        ) || { status: 'not_found' };

        if (coherenceCheck.status === 'not_found') {
          return {
            status: 'not_found',
            data: {
              original,
              reason: 'suggestion_validation_failed',
              attempts: ['babelio']
            }
          };
        }

        // If coherenceCheck itself suggests another author/title, prefer that final suggestion.
  // Prefer human-readable textual suggestions when available
        // Prefer structured babelio_data if available
        const cohBabelio = coherenceCheck && coherenceCheck.babelio_data;
        const cohStructured = (cohBabelio && (cohBabelio.prenoms || cohBabelio.prenoms === '') && cohBabelio.nom)
          ? `${cohBabelio.prenoms} ${cohBabelio.nom}`
          : null;

        const finalAuthor = cohStructured || coherenceCheck.babelio_suggestion_author || authorValidation.babelio_suggestion || coherenceCheck.original_author || original.author;
  const finalTitle = coherenceCheck.babelio_suggestion_title || original.title || coherenceCheck.original_title;

        return {
          status: 'suggestion',
          data: {
            original,
            suggested: {
              title: finalTitle,
              author: finalAuthor
            },
            corrections: {
              title: original.title !== finalTitle,
              author: original.author !== finalAuthor
            },
            source: 'babelio',
            confidence_score: Math.min(
              authorValidation.confidence_score || 0,
              coherenceCheck.confidence_score || 1.0
            )
          }
        };
      } catch (error) {
        return {
          status: 'not_found',
          data: {
            original,
            reason: 'suggestion_validation_failed',
            attempts: ['babelio']
          }
        };
      }
    }

    // Fallback: nothing reliable available
    return {
      status: 'not_found',
      data: {
        original,
        reason: 'no_reliable_match_found',
        attempts: ['babelio']
      }
    };
  }

  /**
   * Détermine la raison spécifique pour "not_found"
   * @private
   */
  _determineNotFoundReason(authorValidation, bookValidation) {
    if (authorValidation?.status === 'not_found' && bookValidation?.status === 'not_found') {
      return 'no_reliable_match_found';
    }

    if (authorValidation?.status === 'corrected' && bookValidation?.status === 'not_found') {
      return 'suggestion_validation_failed';
    }

    return 'no_reliable_match_found';
  }
}

// Import des dépendances nécessaires
import { babelioService, fuzzySearchService, livresAuteursService } from './api.js';

export default new BiblioValidationService({
  babelioService,
  fuzzySearchService,
  livresAuteursService,
  localAuthorService: null // Pas encore implémenté
});
