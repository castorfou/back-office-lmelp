/**
 * Construit l'objet book_data à envoyer au backend lors de la validation
 *
 * CONTEXTE (Issue #85):
 * Cette fonction extrait la logique qui était inline dans autoValidateAndSendResults()
 * (LivresAuteurs.vue lignes 1192-1208).
 *
 * PROBLÈME RÉSOLU:
 * L'ancienne implémentation oubliait de transmettre babelio_url et babelio_publisher
 * même si ces champs étaient présents dans le livre enrichi automatiquement.
 *
 * FLUX DE DONNÉES:
 * Backend → enrichit automatiquement (confidence >= 0.90) → ajoute babelio_*
 * Backend → retourne via API → Frontend reçoit book avec babelio_*
 * Frontend → valide → DOIT retransmettre babelio_* au backend
 * Backend → persiste en MongoDB
 *
 * @param {Object} book - Livre original avec tous les champs (y compris babelio_*)
 * @param {Object} validationResult - Résultat de la validation Babelio
 * @param {string} status - Statut de validation ('verified', 'corrected', 'not_found')
 * @returns {Object} Données formatées pour l'API backend
 */
export function buildBookDataForBackend(book, validationResult, status) {
  // TODO Issue #85: Implémenter la logique correcte
  // Pour l'instant, version minimale qui reproduit le BUG
  const bookForBackend = {
    auteur: book.auteur,
    titre: book.titre,
    editeur: book.editeur || '',
    programme: book.programme || false,
    validation_status: status
  };

  // Ajouter les suggestions si disponibles
  if (validationResult.data?.suggested?.author) {
    bookForBackend.suggested_author = validationResult.data.suggested.author;
  }
  if (validationResult.data?.suggested?.title) {
    bookForBackend.suggested_title = validationResult.data.suggested.title;
  }

  // Issue #85: Transmettre les enrichissements Babelio si disponibles
  // Ces champs sont ajoutés automatiquement par le backend lors de l'extraction
  // quand confidence >= 0.90 (Phase 0 ou Phase 2.5)
  if (book.babelio_url) {
    bookForBackend.babelio_url = book.babelio_url;
  }
  if (book.babelio_publisher) {
    bookForBackend.babelio_publisher = book.babelio_publisher;
  }

  return bookForBackend;
}
