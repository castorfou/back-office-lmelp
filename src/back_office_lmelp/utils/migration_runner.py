"""Gestionnaire de processus de migration Babelio (Issue #124).

Ce module gère:
- Lancement unique du script de migration
- Streaming de la progression en temps réel
- État global du processus
"""

import asyncio
import logging
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from back_office_lmelp.services.babelio_service import babelio_service


# Import migrate_one_book_and_author from scripts
# Add scripts directory to path temporarily
scripts_path = (
    Path(__file__).parent.parent.parent.parent / "scripts" / "migration_donnees"
)
if str(scripts_path) not in sys.path:
    sys.path.insert(0, str(scripts_path))

try:
    from migrate_url_babelio import (  # type: ignore
        get_all_authors_to_complete,
        migrate_one_book_and_author,
        process_one_author,
    )
finally:
    # Clean up sys.path
    if str(scripts_path) in sys.path:
        sys.path.remove(str(scripts_path))


logger = logging.getLogger(__name__)


def create_book_log(
    titre: str,
    auteur: str,
    livre_status: str,
    auteur_status: str,
    details: list[str],
) -> dict[str, Any]:
    """Crée un log structuré pour un livre traité pendant la migration.

    Args:
        titre: Titre du livre
        auteur: Nom de l'auteur
        livre_status: Statut du livre (success | error | not_found)
        auteur_status: Statut de l'auteur (success | error | not_found | none)
        details: Liste des messages de log détaillés

    Returns:
        Dict structuré avec les informations du livre traité

    Raises:
        ValueError: Si un statut invalide est fourni
    """
    # Validation des statuts
    valid_livre_statuses = {"success", "error", "not_found", "none"}
    valid_auteur_statuses = {"success", "error", "not_found", "none"}

    if livre_status not in valid_livre_statuses:
        raise ValueError(
            f"livre_status must be one of {valid_livre_statuses}, got '{livre_status}'"
        )

    if auteur_status not in valid_auteur_statuses:
        raise ValueError(
            f"auteur_status must be one of {valid_auteur_statuses}, "
            f"got '{auteur_status}'"
        )

    return {
        "titre": titre,
        "auteur": auteur,
        "livre_status": livre_status,
        "auteur_status": auteur_status,
        "details": details,
    }


def parse_book_migration_output(log_lines: list[str]) -> dict[str, Any] | None:
    """Parse les logs bash d'une migration de livre en log structuré.

    Args:
        log_lines: Liste des lignes de log brut du script bash

    Returns:
        Dict structuré avec titre, auteur, statuts et détails, ou None si invalide

    Examples:
        >>> lines = [
        ...     "📚 Livre: Le Petit Prince (Antoine de Saint-Exupéry)",
        ...     "🔍 Recherche Babelio...",
        ...     "✅ Livre mis à jour avec URL Babelio",
        ...     "✅ Auteur mis à jour avec URL Babelio",
        ... ]
        >>> result = parse_book_migration_output(lines)
        >>> result["titre"]
        'Le Petit Prince'
        >>> result["livre_status"]
        'success'
    """
    if not log_lines:
        return None

    # Extraire titre et auteur depuis la première ligne
    # Format attendu: "📚 Livre: {titre} ({auteur})"
    header_pattern = r"📚 Livre: (.+) \((.+)\)"
    header_match = None

    for line in log_lines:
        match = re.match(header_pattern, line)
        if match:
            header_match = match
            break

    if not header_match:
        return None

    titre = header_match.group(1)
    auteur = header_match.group(2)

    # Déterminer le statut du livre
    livre_status = "error"  # Par défaut
    for line in log_lines:
        if "✅ Livre mis à jour" in line:
            livre_status = "success"
            break
        if "❌ Livre non trouvé sur Babelio" in line:
            livre_status = "not_found"
            break

    # Déterminer le statut de l'auteur
    auteur_status = "none"  # Par défaut
    for line in log_lines:
        if "✅ Auteur mis à jour" in line:
            auteur_status = "success"
            break
        if "❌ Auteur non migré" in line or "❌ Auteur non trouvé" in line:
            auteur_status = "error"
            break
        if "⚪ Auteur non traité" in line or "⚪ Pas d'auteur à migrer" in line:
            auteur_status = "none"
            break

    return create_book_log(
        titre=titre,
        auteur=auteur,
        livre_status=livre_status,
        auteur_status=auteur_status,
        details=log_lines,
    )


class MigrationRunner:
    """Singleton pour gérer un seul processus de migration à la fois."""

    _instance: "MigrationRunner | None" = None
    _lock = asyncio.Lock()

    def __new__(cls) -> "MigrationRunner":
        """Ensure singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self) -> None:
        """Initialize the migration runner state."""
        self.process: subprocess.Popen[bytes] | None = None
        self.is_running = False
        self.start_time: datetime | None = None
        self.logs: list[str] = []
        self.book_logs: list[dict[str, Any]] = []  # Logs structurés par livre
        self.books_processed = 0
        self.last_update: datetime | None = None

    @classmethod
    def get_instance(cls) -> "MigrationRunner":
        """Get the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def start_migration(self) -> dict[str, Any]:
        """Start the migration by calling Python function directly.

        Returns:
            Dict with status and message
        """
        async with self._lock:
            if self.is_running:
                return {
                    "status": "already_running",
                    "message": "Migration already in progress",
                    "start_time": self.start_time.isoformat()
                    if self.start_time
                    else None,
                }

            # Start the migration
            try:
                self.is_running = True
                self.start_time = datetime.now(UTC)
                self.logs = []
                self.book_logs = []  # Reset structured logs
                self.books_processed = 0
                self.last_update = datetime.now(UTC)
                self.process = None  # No subprocess anymore

                logger.info(f"Migration started at {self.start_time}")

                # Start background task to run Python migration
                asyncio.create_task(self._run_python_migration())

                return {
                    "status": "started",
                    "message": "Migration started successfully",
                    "start_time": self.start_time.isoformat(),
                }

            except Exception as e:
                self.is_running = False
                logger.error(f"Failed to start migration: {e}")
                return {
                    "status": "error",
                    "message": f"Failed to start migration: {str(e)}",
                }

    async def _run_python_migration(self) -> None:
        """Background task to run migration using Python function directly."""
        try:
            # Issue #304: réutiliser le singleton partagé babelio_service (pas
            # une nouvelle instance) — sinon le cookie/circuit breaker de cette
            # migration seraient invisibles depuis la page Contrôle Babelio
            # (et vice-versa : un cookie corrigé pendant la migration n'aurait
            # aucun effet sur elle).

            # Loop until no more books or stopped
            max_iterations = 1000
            iteration = 0

            while self.is_running and iteration < max_iterations:
                iteration += 1

                try:
                    # Call migrate_one_book_and_author directly
                    result = await migrate_one_book_and_author(
                        babelio_service=babelio_service, dry_run=False
                    )

                    # Check if Phase 1 is complete (no more books)
                    if result is None or result.get("status") == "no_pending_books":
                        logger.info("✅ Phase 1 terminée - no more books to process")
                        # NE PAS mettre is_running = False ici !
                        # La Phase 2 (complétion des auteurs) doit s'exécuter ensuite
                        break

                    # Extract book info from result
                    titre = result.get("titre", "Unknown")
                    auteur = result.get("auteur", "Unknown")

                    # Map result to book_log statuses
                    livre_updated = result.get("livre_updated", False)
                    auteur_updated = result.get("auteur_updated", False)
                    auteur_already_linked = result.get("auteur_already_linked", False)
                    status = result.get("status", "error")

                    # Determine statuses
                    if status == "not_found":
                        livre_status = "not_found"
                    elif livre_updated:
                        livre_status = "success"
                    else:
                        livre_status = "error"

                    if not auteur:
                        auteur_status = "none"
                    elif auteur_updated:
                        auteur_status = "success"
                    elif auteur_already_linked:
                        auteur_status = "none"  # Déjà lié = pas besoin de migrer
                    elif status == "not_found":
                        auteur_status = "none"
                    else:
                        auteur_status = "error" if not auteur_updated else "none"

                    # Create detailed log lines
                    details = [
                        f"📚 Livre: {titre} ({auteur})",
                        f"📊 Status: {status}",
                    ]
                    if livre_updated:
                        details.append("✅ Livre mis à jour avec URL Babelio")
                    else:
                        details.append("❌ Livre non mis à jour")

                    if auteur_updated:
                        details.append("✅ Auteur mis à jour avec URL Babelio")
                    elif auteur_already_linked:
                        details.append("ℹ️  Auteur déjà lié à Babelio")
                    elif auteur:
                        details.append("❌ Auteur non migré")
                    else:
                        details.append("⚪ Pas d'auteur à migrer")

                    # Create book_log entry
                    book_log = create_book_log(
                        titre=titre,
                        auteur=auteur,
                        livre_status=livre_status,
                        auteur_status=auteur_status,
                        details=details,
                    )

                    # Add to book_logs
                    self.book_logs.append(book_log)

                    # Issue #152: Compter les éléments individuels, pas les groupes
                    # Compter le livre si traité
                    items_count = 0
                    if livre_updated or livre_status != "none":
                        items_count += 1
                    # Compter l'auteur si traité (pas si déjà lié)
                    if auteur_updated:
                        items_count += 1

                    self.books_processed += items_count
                    self.last_update = datetime.now(UTC)

                    # Add summary to text logs
                    summary = f"Migration #{iteration}: {titre} - 📚 {livre_status} - 👤 {auteur_status}"
                    self.logs.append(summary)

                    # Keep logs manageable
                    if len(self.logs) > 100:
                        self.logs = self.logs[-100:]

                    logger.info(summary)

                    # Issue #304: ni "blocked_403" (cookie Babelio expiré,
                    # circuit breaker ouvert côté serveur) ni "error"
                    # (timeout/erreur réseau transitoire) ne sont jamais
                    # exclus des runs futurs — volontairement, un échec
                    # technique ne doit pas être confondu avec un vrai
                    # "livre introuvable" (cf. commentaire dans
                    # migrate_url_babelio.py). Mais ceci signifie aussi que,
                    # dans CETTE MÊME run, ce livre sera retrouvé identique à
                    # l'itération suivante et retenté indéfiniment jusqu'à
                    # épuiser max_iterations. Arrêter net dans les deux cas ;
                    # l'utilisateur corrige le cookie (403) ou retente plus
                    # tard (timeout/réseau) puis relance.
                    if status in ("blocked_403", "error"):
                        logger.warning(
                            f"🚫 Échec sur '{titre}' (status={status}) — arrêt de "
                            "la migration pour éviter de boucler sur ce même livre"
                        )
                        break

                    # Small delay between books
                    await asyncio.sleep(1)

                except Exception as e:
                    logger.error(f"Error processing book in iteration {iteration}: {e}")
                    # Continue to next book
                    await asyncio.sleep(1)

            # Phase 2: Compléter les auteurs manquants
            logger.info("🔄 Phase 2: Complétion des auteurs manquants...")
            authors_completed = 0

            # APPROCHE BATCH: Charger TOUS les auteurs sans URL une seule fois
            authors_to_process = await get_all_authors_to_complete()
            total_authors = len(authors_to_process)
            logger.info(f"📋 {total_authors} auteurs à traiter")

            # Itérer sur la liste d'auteurs
            for idx, author_data in enumerate(authors_to_process, start=1):
                if not self.is_running:
                    logger.info("⚠️  Migration arrêtée par l'utilisateur")
                    break

                try:
                    nom_auteur = author_data.get("nom", "Unknown")
                    livres = author_data.get("livres", [])
                    nb_livres = len(livres)

                    logger.info(
                        f"🔄 [{idx}/{total_authors}] Traitement: {nom_auteur} ({nb_livres} livres)"
                    )

                    # Traiter cet auteur (singleton partagé, pas d'instance isolée)
                    author_result = await process_one_author(
                        author_data,
                        dry_run=False,
                        babelio_service=babelio_service,
                    )

                    auteur_updated = author_result.get("auteur_updated", False)
                    raison = author_result.get("raison", "")

                    # Créer un log structuré pour cet auteur
                    # PHASE 2: Afficher l'AUTEUR comme titre principal
                    details = [
                        f"👤 Auteur: {nom_auteur}",
                    ]

                    # Afficher le titre du livre si un seul livre lié
                    if nb_livres == 1:
                        livre_titre = livres[0].get("titre", "Sans titre")
                        details.append(f"📚 1 livre lié: {livre_titre}")
                    elif nb_livres == 0:
                        details.append("📚 Aucun livre lié")
                    else:
                        details.append(f"📚 {nb_livres} livres liés")

                    if auteur_updated:
                        details.append("✅ URL Babelio ajoutée")
                    else:
                        details.append(f"❌ {raison}")

                    # Déterminer le statut
                    if auteur_updated:
                        auteur_status = "success"
                    elif author_result.get("status") == "not_found":
                        auteur_status = "not_found"
                    else:
                        auteur_status = "error"

                    book_log = create_book_log(
                        titre=nom_auteur,  # Phase 2: Auteur comme titre principal
                        auteur="",  # Pas d'auteur secondaire en Phase 2
                        livre_status="none",  # Livre pas modifié en Phase 2
                        auteur_status=auteur_status,
                        details=details,
                    )

                    self.book_logs.append(book_log)

                    # Issue #152: Compter seulement si l'auteur a vraiment été traité
                    if auteur_updated:
                        self.books_processed += 1
                        authors_completed += 1

                    self.last_update = datetime.now(UTC)

                    summary = f"Auteur: {nom_auteur} - {raison}"
                    self.logs.append(summary)
                    logger.info(summary)

                    # Small delay
                    await asyncio.sleep(1)

                except Exception as e:
                    nom_auteur = author_data.get("nom", "Unknown")
                    logger.error(
                        f"Error processing author '{nom_auteur}' at index {idx}: {e}"
                    )
                    await asyncio.sleep(1)

            logger.info(
                f"✅ Phase 2 terminée - {authors_completed} auteurs complétés sur {total_authors} auteurs traités"
            )

            # Issue #304: ne PAS fermer babelio_service — c'est le singleton
            # partagé avec le reste de l'application (page Contrôle Babelio,
            # validation manuelle), pas une instance dédiée à cette migration.

            # Mark as complete
            if self.is_running:
                self.is_running = False
                final_msg = f"✅ Migration completed successfully - {self.books_processed} books processed"
                self.logs.append(final_msg)
                logger.info(final_msg)

        except Exception as e:
            logger.error(f"Fatal error in migration: {e}")
            self.is_running = False
            self.logs.append(f"❌ Migration failed: {str(e)}")

    async def _read_output(self) -> None:
        """Background task to read process output."""
        if self.process is None or self.process.stdout is None:
            return

        try:
            while self.is_running and self.process.poll() is None:
                line = self.process.stdout.readline()
                if line:
                    decoded_line = line.decode("utf-8", errors="replace").strip()
                    if decoded_line:
                        self.logs.append(decoded_line)
                        self.last_update = datetime.now(UTC)

                        # Count processed books
                        if "Migration #" in decoded_line:
                            self.books_processed += 1

                        # Keep logs manageable (last 100 lines)
                        if len(self.logs) > 100:
                            self.logs = self.logs[-100:]

                await asyncio.sleep(0.1)  # Small delay to prevent CPU spinning

            # Process finished
            if self.process is not None:
                return_code = self.process.wait()
                self.is_running = False

                if return_code == 0:
                    final_msg = "✅ Migration completed successfully"
                elif return_code == 2:
                    final_msg = "⚠️ Migration stopped: Babelio unavailable"
                else:
                    final_msg = f"❌ Migration failed with code {return_code}"

                self.logs.append(final_msg)
                logger.info(final_msg)

        except Exception as e:
            logger.error(f"Error reading migration output: {e}")
            self.is_running = False
            self.logs.append(f"❌ Error: {str(e)}")

    def get_status(self) -> dict[str, Any]:
        """Get current migration status.

        Returns:
            Dict with running status, logs, and progress
        """
        return {
            "is_running": self.is_running,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "books_processed": self.books_processed,
            "last_update": self.last_update.isoformat() if self.last_update else None,
            "logs": self.logs[-20:],  # Return last 20 lines
            "total_logs": len(self.logs),
            "book_logs": self.book_logs,  # Logs structurés par livre
        }

    def get_detailed_logs(self) -> list[str]:
        """Get all logs for expanded view.

        Returns:
            List of all log lines
        """
        return self.logs

    async def stop_migration(self) -> dict[str, Any]:
        """Stop the running migration process.

        Returns:
            Dict with status and message
        """
        async with self._lock:
            if not self.is_running:
                return {
                    "status": "not_running",
                    "message": "No migration is currently running",
                }

            try:
                # Plus de subprocess depuis migration Python directe
                # On met juste is_running à False pour arrêter la boucle
                self.is_running = False
                self.logs.append("⚠️ Migration stopped by user")

                return {
                    "status": "stopped",
                    "message": "Migration stopped successfully",
                }

            except Exception as e:
                logger.error(f"Failed to stop migration: {e}")
                return {
                    "status": "error",
                    "message": f"Failed to stop migration: {str(e)}",
                }


# Global instance
migration_runner = MigrationRunner.get_instance()
