/**
 * BiblioValidationService - Service de validation bibliographique
 * Orchestration intelligente entre ground truth (fuzzy search) et Babelio
 */

export class BiblioValidationService {
  constructor(dependencies = {}) {
    this.fuzzySearchService = dependencies.fuzzySearchService;
    this.babelioService = dependencies.babelioService;
    this.localAuthorService = dependencies.localAuthorService;
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

      // Étape 1: Tentative ground truth si episodeId fourni
      let groundTruthResult = null;
      if (episodeId) {
        try {
          groundTruthResult = await this.fuzzySearchService.searchEpisode(
            episodeId,
            { author, title }
          );
          // console.debug('Ground truth result for', { author, title, episodeId }, ':', groundTruthResult);
        } catch (error) {
          // Si ground truth échoue, continue avec Babelio seulement
          console.warn('Ground truth search failed:', error.message);
        }
      }

      // Étape 2: Validation Babelio de l'auteur
      const authorValidation = await this.babelioService.verifyAuthor(author) || { status: 'not_found' };

      // Étape 3: Validation Babelio du livre
      let bookValidation;

      // Cas 1: Auteur avec suggestion (corrected OU verified avec différence)
      if (this._authorHasSuggestion(authorValidation)) {
        // D'abord essayer avec l'auteur original
        bookValidation = await this.babelioService.verifyBook(title, author) || { status: 'not_found' };

        // Si ça échoue, essayer avec l'auteur suggéré
        if (bookValidation.status === 'not_found') {
          bookValidation = await this.babelioService.verifyBook(
            title,
            authorValidation.babelio_suggestion
          ) || { status: 'not_found' };
        }
      } else {
        // Cas 2: Pas de suggestion d'auteur, test avec l'auteur original seulement
        bookValidation = await this.babelioService.verifyBook(title, author) || { status: 'not_found' };
      }

      // Étape 4: Arbitrage et décision finale
      return this._arbitrateResults({
        original,
        groundTruthResult,
        authorValidation,
        bookValidation,
        episodeId
      });

    } catch (error) {
      return {
        status: 'error',
        data: {
          original: { author, title, publisher },
          error: error.message,
          attempts: episodeId ? ['ground_truth', 'babelio'] : ['babelio']
        }
      };
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
    // Cas 1: Ground truth disponible avec matches de qualité - PRIORITAIRE
    const hasGroundTruth = groundTruthResult?.found_suggestions;
    const hasGoodMatches = hasGroundTruth && this._hasGoodGroundTruthMatches(groundTruthResult);

    if (hasGroundTruth && hasGoodMatches) {
      const groundTruthSuggestion = this._extractGroundTruthSuggestion(groundTruthResult);

      // Vérifier la cohérence avec Babelio
      return await this._validateGroundTruthSuggestion(
        original,
        groundTruthSuggestion,
        bookValidation
      );
    }

    // Cas 2: Validation directe - auteur ET livre tous deux vérifiés
    const isDirectValidation = (
      authorValidation?.status === 'verified' &&
      !this._authorHasSuggestion(authorValidation) && // Auteur exact, pas de suggestion
      bookValidation?.status === 'verified' && // Livre doit être vérifié aussi
      (!hasGroundTruth || !hasGoodMatches) // Pas de ground truth ou ground truth pas assez bon
    );

    if (isDirectValidation) {
      return {
        status: 'validated',
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

    // Cas 3: Suggestion Babelio seule
    if (this._hasBabelioSuggestion(authorValidation, bookValidation)) {
      return await this._validateBabelioSuggestion(original, authorValidation, bookValidation);
    }

    // Cas 4: Conflit entre sources ou aucune suggestion fiable
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

    // Cas 5: Aucune source ne trouve de match fiable
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

    const titleMatch = titleMatches?.[0];
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
   * Extrait la suggestion de ground truth
   * @private
   */
  _extractGroundTruthSuggestion(groundTruthResult) {
    // Support des deux formats : API utilise titleMatches, tests utilisent title_matches
    const titleMatches = groundTruthResult.titleMatches || groundTruthResult.title_matches;
    const authorMatchesArray = groundTruthResult.authorMatches || groundTruthResult.author_matches;

    // Format des matches : [["📖 text", score], ...]
    const titleMatch = titleMatches[0][0]; // "📖 Kolkhoze"

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
          return cleaned.length > 0 &&
                 cleaned.length < 12 &&
                 !cleaned.includes(' ') &&
                 /^[A-Z][a-z]+$/.test(cleaned); // Commence par majuscule, que des lettres
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
      title: titleMatch.replace('📖 ', ''), // Enlever le préfixe
      author: reconstructedAuthor
    };
  }

  /**
   * Valide une suggestion de ground truth avec Babelio
   * @private
   */
  async _validateGroundTruthSuggestion(original, groundTruthSuggestion, initialBookValidation) {
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
          status: isIdentical ? 'validated' : 'suggestion',
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

      // Sinon, vérifier que la suggestion ground truth est validée par Babelio
      const groundTruthBookValidation = await this.babelioService.verifyBook(
        groundTruthSuggestion.title,
        groundTruthSuggestion.author
      ) || { status: 'not_found' };

      if (groundTruthBookValidation.status === 'verified') {
        // Vérifier si la suggestion est identique à l'original
        const isIdentical = (
          original.title === groundTruthSuggestion.title &&
          original.author === groundTruthSuggestion.author
        );

        return {
          status: isIdentical ? 'validated' : 'suggestion',
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
    // Si l'auteur a une suggestion (corrected OU verified avec différence), vérifier la cohérence
    if (this._authorHasSuggestion(authorValidation)) {
      // Si bookValidation est "verified", on a déjà testé la cohérence dans validateBiblio
      if (bookValidation?.status === 'verified') {

        const finalAuthor = authorValidation.babelio_suggestion;
        const finalTitle = bookValidation.babelio_suggestion_title || original.title;

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
              authorValidation.confidence_score,
              bookValidation.confidence_score || 1.0
            )
          }
        };
      }

      // Fallback: faire un coherenceCheck si bookValidation n'est pas "verified"
      try {
        const coherenceCheck = await this.babelioService.verifyBook(
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

        // Si le coherenceCheck suggère un autre auteur, utiliser cette suggestion finale
        const finalAuthor = coherenceCheck.babelio_suggestion_author || authorValidation.babelio_suggestion;
        const finalTitle = coherenceCheck.babelio_suggestion_title || original.title;

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
              authorValidation.confidence_score,
              coherenceCheck.confidence_score || 1.0
            )
          }
        };
      } catch (error) {
        // Si la vérification échoue, considérer comme non trouvé
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

    // Suggestion de livre seulement
    if (bookValidation.status === 'corrected') {
      const suggested = {
        title: bookValidation.babelio_suggestion_title,
        author: bookValidation.babelio_suggestion_author || original.author
      };

      return {
        status: 'suggestion',
        data: {
          original,
          suggested,
          corrections: {
            title: original.title !== suggested.title,
            author: original.author !== suggested.author
          },
          source: 'babelio',
          confidence_score: bookValidation.confidence_score
        }
      };
    }

    // Cas fallback - ne devrait pas arriver
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
