"""
Service Calibre pour accéder à la bibliothèque via SQLite direct.

Ce service interroge directement la base metadata.db de Calibre en lecture seule,
offrant une abstraction de haut niveau pour le reste de l'application.

Architecture:
- Accès SQLite direct (pas d'API Calibre) pour éviter les problèmes de permissions
- Lecture seule obligatoire (mode=ro)
- Support des bibliothèques virtuelles via filtre sur tags
- Cache applicatif (optionnel, pour optimiser les requêtes fréquentes)

Documentation:
- Structure DB: docs/dev/calibre-db-schema.md
- Script exploration: scripts/explore_calibre.py
"""

import logging
import sqlite3
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..models.calibre_models import (
    CalibreAuthor,
    CalibreBook,
    CalibreBookList,
    CalibreLatestChange,
    CalibreStatistics,
    CalibreStatus,
)
from ..settings import settings


logger = logging.getLogger(__name__)

# Relance de l'ouverture de metadata.db pendant son remplacement (Issue #327)
OPEN_ATTEMPTS = 3
OPEN_RETRY_DELAY_SECONDS = 0.2
# Ids par requête « IN (...) » : sous la limite de variables des vieux SQLite (999)
BATCH_SIZE = 500


class CalibreService:
    """
    Service pour accéder à la bibliothèque Calibre.

    Utilise SQLite direct en lecture seule sur metadata.db.

    Fonctionnalités:
    - Liste des livres (paginée, filtrée)
    - Détails d'un livre
    - Liste des auteurs
    - Statistiques
    - Support bibliothèques virtuelles (filtre tag)
    """

    def __init__(self):
        """Initialise le service Calibre."""
        self._available: bool = False
        self._library_path: Path | None = None
        self._db_path: Path | None = None
        self._virtual_library_tag: str | None = None
        self._custom_columns_map: dict[str, int] = {}
        self._error: str | None = None

        # Vérifier la disponibilité
        self._check_availability()

    def _check_availability(self) -> bool:
        """
        Vérifie si Calibre est disponible et accessible.

        Returns:
            True si disponible, False sinon
        """
        # Vérifier la configuration
        library_path_str = settings.calibre_library_path

        if not library_path_str:
            self._error = "Bibliothèque Calibre non trouvée dans /calibre"
            logger.info("Calibre non configuré (/calibre/metadata.db manquant)")
            return False

        # Vérifier le chemin
        self._library_path = Path(library_path_str)

        if not self._library_path.exists():
            self._error = f"Chemin {library_path_str} n'existe pas"
            logger.warning(f"Calibre non disponible: {self._error}")
            return False

        if not self._library_path.is_dir():
            self._error = f"{library_path_str} n'est pas un dossier"
            logger.warning(f"Calibre non disponible: {self._error}")
            return False

        # Vérifier metadata.db
        self._db_path = self._library_path / "metadata.db"

        if not self._db_path.exists():
            self._error = f"metadata.db introuvable dans {library_path_str}"
            logger.warning(f"Calibre non disponible: {self._error}")
            return False

        # Récupérer le tag de bibliothèque virtuelle (optionnel)
        self._virtual_library_tag = settings.calibre_virtual_library_tag

        if self._virtual_library_tag:
            logger.info(
                f"Bibliothèque virtuelle activée: tag '{self._virtual_library_tag}'"
            )

        # Tester la connexion
        try:
            # Pas _get_connection() : _available n'est pas encore positionné
            conn = self._open_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM books")
            count = cursor.fetchone()[0]
            conn.close()

            logger.info(
                f"✅ Calibre disponible: {count} livres dans {library_path_str}"
            )
            self._available = True

            # Charger le mapping des colonnes personnalisées
            self._load_custom_columns_map()

            return True

        except Exception as e:
            self._error = f"Erreur connexion DB: {str(e)}"
            logger.error(f"Calibre non disponible: {self._error}", exc_info=True)
            return False

    def _get_connection(self) -> sqlite3.Connection:
        """
        Ouvre une connexion SQLite en lecture seule.

        Returns:
            Connexion SQLite configurée

        Raises:
            RuntimeError: Si Calibre n'est pas disponible
        """
        if not self._available or not self._db_path:
            raise RuntimeError("Calibre n'est pas disponible")

        return self._open_connection()

    def _open_connection(self) -> sqlite3.Connection:
        """
        Ouvre metadata.db en lecture seule, en relançant une ouverture ratée.

        La copie servie peut être remplacée par Synology Drive pendant une lecture
        (Issue #327). En lecture seule, SQLite n'échoue qu'à la première requête :
        chaque essai ouvre donc la base ET exécute une requête de contrôle.

        Raises:
            sqlite3.DatabaseError: si la base reste illisible après tous les essais
        """
        for attempt in range(1, OPEN_ATTEMPTS + 1):
            conn = sqlite3.connect(f"file:{self._db_path}?mode=ro", uri=True)
            try:
                conn.execute("SELECT 1 FROM books LIMIT 1").fetchall()
            except sqlite3.DatabaseError as e:
                conn.close()
                if attempt == OPEN_ATTEMPTS:
                    raise
                logger.warning(
                    f"metadata.db illisible (essai {attempt}/{OPEN_ATTEMPTS}): {e}"
                )
                time.sleep(OPEN_RETRY_DELAY_SECONDS)
                continue
            conn.row_factory = sqlite3.Row  # Accès par nom de colonne
            return conn
        raise RuntimeError("unreachable")  # pragma: no cover

    def _load_custom_columns_map(self) -> None:
        """
        Charge le mapping des colonnes personnalisées.

        Construit un dictionnaire {label: id} pour faciliter les requêtes.
        Exemple: {"#read": 2, "#paper": 1, "#text": 3}
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("SELECT id, label FROM custom_columns")
            rows = cursor.fetchall()

            self._custom_columns_map = {row["label"]: row["id"] for row in rows}

            conn.close()

            logger.debug(
                f"Colonnes personnalisées chargées: {self._custom_columns_map}"
            )

        except Exception as e:
            logger.warning(
                f"Impossible de charger les colonnes personnalisées: {e}",
                exc_info=True,
            )
            self._custom_columns_map = {}

    def is_available(self) -> bool:
        """
        Vérifie si le service Calibre est disponible.

        Returns:
            True si disponible, False sinon
        """
        return self._available

    def get_status(self) -> CalibreStatus:
        """
        Retourne le statut du service Calibre.

        Returns:
            Objet CalibreStatus avec les informations de disponibilité
        """
        if not self._available:
            return CalibreStatus(
                available=False,
                error=self._error or "Service non disponible",
            )

        # Compter les livres (avec filtre virtuel si activé)
        try:
            total_books = self.count_books()
        except Exception as e:
            logger.error(f"Erreur comptage livres: {e}", exc_info=True)
            total_books = None

        # Récupérer les colonnes personnalisées
        custom_columns = {}
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT label, name, datatype FROM custom_columns")
            for row in cursor.fetchall():
                custom_columns[row["label"]] = f"{row['name']} ({row['datatype']})"
            conn.close()
        except Exception as e:
            logger.error(
                f"Erreur récupération colonnes personnalisées: {e}", exc_info=True
            )

        mtime = self.get_metadata_mtime()

        return CalibreStatus(
            available=True,
            library_path=str(self._library_path),
            total_books=total_books,
            virtual_library_tag=self._virtual_library_tag,
            custom_columns=custom_columns,
            metadata_updated_at=(
                datetime.fromtimestamp(mtime, tz=UTC) if mtime is not None else None
            ),
            latest_book_change=self._get_latest_book_change(),
        )

    def get_metadata_mtime(self) -> float | None:
        """Date de modification de metadata.db (fraîcheur Calibre), ou None."""
        if not self._db_path:
            return None
        try:
            return self._db_path.stat().st_mtime
        except OSError as e:
            logger.warning(f"Impossible de lire la date de metadata.db: {e}")
            return None

    def _get_latest_book_change(self) -> CalibreLatestChange | None:
        """Livre au last_modified le plus récent (bibliothèque virtuelle incluse)."""
        query = "SELECT b.title, b.last_modified FROM books b"
        params: list[Any] = []
        if self._virtual_library_tag:
            query += """
                JOIN books_tags_link btl ON b.id = btl.book
                JOIN tags t ON btl.tag = t.id
                WHERE t.name = ?
            """
            params.append(self._virtual_library_tag)
        query += " ORDER BY b.last_modified DESC LIMIT 1"

        try:
            conn = self._get_connection()
            try:
                row = conn.execute(query, params).fetchone()
            finally:
                conn.close()
            if row is None:
                return None
            return CalibreLatestChange(
                title=row["title"], last_modified=row["last_modified"]
            )
        except Exception as e:
            logger.error(f"Erreur lecture dernière modification: {e}", exc_info=True)
            return None

    def count_books(self, read_filter: bool | None = None) -> int:
        """
        Compte le nombre de livres.

        Args:
            read_filter: Filtre sur le statut "Lu"
                - None: Tous les livres
                - True: Uniquement les livres lus
                - False: Uniquement les livres non lus

        Returns:
            Nombre de livres

        Raises:
            RuntimeError: Si Calibre n'est pas disponible
        """
        if not self._available:
            raise RuntimeError("Calibre n'est pas disponible")

        conn = self._get_connection()
        cursor = conn.cursor()

        # Requête de base
        query = "SELECT COUNT(DISTINCT b.id) FROM books b"
        conditions = []
        params: list[Any] = []

        # Filtre bibliothèque virtuelle
        if self._virtual_library_tag:
            query += """
                JOIN books_tags_link btl ON b.id = btl.book
                JOIN tags t ON btl.tag = t.id
            """
            conditions.append("t.name = ?")
            params.append(self._virtual_library_tag)

        # Filtre "Lu"
        if read_filter is not None:
            read_col_id = self._custom_columns_map.get("read")
            if read_col_id:
                query += (
                    f" LEFT JOIN custom_column_{read_col_id} ccr ON b.id = ccr.book"
                )
                if read_filter:
                    # Livres lus : ccr.value = 1
                    conditions.append("ccr.value = 1")
                else:
                    # Livres non lus : ccr.value = 0 OU pas d'entrée (NULL)
                    conditions.append("(ccr.value IS NULL OR ccr.value = 0)")

        # Ajouter les conditions
        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        cursor.execute(query, params)
        count = int(cursor.fetchone()[0])
        conn.close()

        return count

    def get_books(
        self,
        limit: int = 100,
        offset: int = 0,
        read_filter: bool | None = None,
        search: str | None = None,
    ) -> CalibreBookList:
        """
        Récupère une liste paginée de livres.

        Args:
            limit: Nombre maximum de résultats
            offset: Décalage pour la pagination
            read_filter: Filtre sur le statut "Lu"
            search: Recherche textuelle (titre, auteur)

        Returns:
            Liste paginée de livres

        Raises:
            RuntimeError: Si Calibre n'est pas disponible
        """
        if not self._available:
            raise RuntimeError("Calibre n'est pas disponible")

        # Compter le total (pour la pagination)
        total = self.count_books(read_filter=read_filter)

        conn = self._get_connection()
        cursor = conn.cursor()

        # Construire la requête
        # Note: On récupère les données de base, les relations seront complétées
        # dans _build_books_from_rows
        query = """
            SELECT DISTINCT
                b.id,
                b.title,
                b.sort,
                b.timestamp,
                b.pubdate,
                b.last_modified,
                b.path,
                b.uuid,
                b.has_cover,
                b.series_index
            FROM books b
        """

        conditions = []
        params: list[Any] = []

        # Filtre bibliothèque virtuelle
        if self._virtual_library_tag:
            query += """
                JOIN books_tags_link btl_filter ON b.id = btl_filter.book
                JOIN tags t_filter ON btl_filter.tag = t_filter.id
            """
            conditions.append("t_filter.name = ?")
            params.append(self._virtual_library_tag)

        # Filtre "Lu"
        if read_filter is not None:
            read_col_id = self._custom_columns_map.get("read")
            if read_col_id:
                query += (
                    f" LEFT JOIN custom_column_{read_col_id} ccr ON b.id = ccr.book"
                )
                if read_filter:
                    # Livres lus : ccr.value = 1
                    conditions.append("ccr.value = 1")
                else:
                    # Livres non lus : ccr.value = 0 OU pas d'entrée (NULL)
                    conditions.append("(ccr.value IS NULL OR ccr.value = 0)")

        # Recherche textuelle (simplifiée pour MVP)
        if search:
            query += """
                LEFT JOIN books_authors_link bal_search ON b.id = bal_search.book
                LEFT JOIN authors a_search ON bal_search.author = a_search.id
            """
            conditions.append("(b.title LIKE ? OR a_search.name LIKE ?)")
            search_pattern = f"%{search}%"
            params.extend([search_pattern, search_pattern])

        # Ajouter les conditions
        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        # Tri et pagination
        query += " ORDER BY b.timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor.execute(query, params)
        rows = cursor.fetchall()

        # Construire les objets CalibreBook
        books = self._build_books_from_rows(rows, conn)

        conn.close()

        return CalibreBookList(
            total=total,
            offset=offset,
            limit=limit,
            books=books,
        )

    def get_book(self, book_id: int) -> CalibreBook | None:
        """
        Récupère un livre par son ID.

        Args:
            book_id: ID du livre dans Calibre

        Returns:
            Livre ou None si non trouvé

        Raises:
            RuntimeError: Si Calibre n'est pas disponible
        """
        if not self._available:
            raise RuntimeError("Calibre n'est pas disponible")

        conn = self._get_connection()
        cursor = conn.cursor()

        # Requête de base
        cursor.execute(
            """
            SELECT
                id, title, sort, timestamp, pubdate, last_modified,
                path, uuid, has_cover, series_index
            FROM books
            WHERE id = ?
        """,
            (book_id,),
        )

        row = cursor.fetchone()

        if not row:
            conn.close()
            return None

        # Construire l'objet complet
        book = self._build_books_from_rows([row], conn)[0]
        conn.close()

        return book

    def get_all_books_summary(self) -> list[dict[str, Any]]:
        """Get a lightweight summary of all books for matching purposes.

        Returns a list of dicts with id, title, authors, read, rating.
        Applies virtual library filter if configured.
        """
        if not self._available:
            return []

        conn = self._get_connection()
        cursor = conn.cursor()

        query = "SELECT b.id, b.title FROM books b"
        params: list[Any] = []

        if self._virtual_library_tag:
            query += """
                JOIN books_tags_link btl_filter ON b.id = btl_filter.book
                JOIN tags t_filter ON btl_filter.tag = t_filter.id
                WHERE t_filter.name = ?
            """
            params.append(self._virtual_library_tag)

        query += " ORDER BY b.title"
        cursor.execute(query, params)
        rows = cursor.fetchall()

        result = []
        for row in rows:
            book_id = row["id"]
            title = row["title"]

            # Get authors
            cursor.execute(
                """SELECT a.name FROM authors a
                   JOIN books_authors_link bal ON a.id = bal.author
                   WHERE bal.book = ?""",
                (book_id,),
            )
            authors = [r["name"] for r in cursor.fetchall()]

            # Get rating
            cursor.execute(
                """SELECT r.rating FROM ratings r
                   JOIN books_ratings_link brl ON r.id = brl.rating
                   WHERE brl.book = ?""",
                (book_id,),
            )
            rating_row = cursor.fetchone()
            rating = rating_row["rating"] if rating_row else None

            # Get read status
            read = None
            read_col_id = self._custom_columns_map.get("read")
            if read_col_id:
                cursor.execute(
                    f"SELECT value FROM custom_column_{read_col_id} WHERE book = ?",
                    (book_id,),
                )
                read_row = cursor.fetchone()
                read = bool(read_row["value"]) if read_row else None

            result.append(
                {
                    "id": book_id,
                    "title": title,
                    "authors": authors,
                    "read": read,
                    "rating": rating,
                }
            )

        conn.close()
        return result

    def get_all_books_with_tags(self) -> list[dict[str, Any]]:
        """Get a summary of all books including tags for matching and corrections.

        Extends get_all_books_summary() with tags data.
        Returns a list of dicts with id, title, authors, read, rating, tags.
        Applies virtual library filter if configured.
        """
        if not self._available:
            return []

        conn = self._get_connection()
        cursor = conn.cursor()

        query = "SELECT b.id, b.title FROM books b"
        params: list[Any] = []

        if self._virtual_library_tag:
            query += """
                JOIN books_tags_link btl_filter ON b.id = btl_filter.book
                JOIN tags t_filter ON btl_filter.tag = t_filter.id
                WHERE t_filter.name = ?
            """
            params.append(self._virtual_library_tag)

        query += " ORDER BY b.title"
        cursor.execute(query, params)
        rows = cursor.fetchall()

        result = []
        for row in rows:
            book_id = row["id"]
            title = row["title"]

            # Get authors
            cursor.execute(
                """SELECT a.name FROM authors a
                   JOIN books_authors_link bal ON a.id = bal.author
                   WHERE bal.book = ?""",
                (book_id,),
            )
            authors = [r["name"] for r in cursor.fetchall()]

            # Get tags
            cursor.execute(
                """SELECT t.name FROM tags t
                   JOIN books_tags_link btl ON t.id = btl.tag
                   WHERE btl.book = ?""",
                (book_id,),
            )
            tags = [r["name"] for r in cursor.fetchall()]

            # Get rating
            cursor.execute(
                """SELECT r.rating FROM ratings r
                   JOIN books_ratings_link brl ON r.id = brl.rating
                   WHERE brl.book = ?""",
                (book_id,),
            )
            rating_row = cursor.fetchone()
            rating = rating_row["rating"] if rating_row else None

            # Get read status
            read = None
            read_col_id = self._custom_columns_map.get("read")
            if read_col_id:
                cursor.execute(
                    f"SELECT value FROM custom_column_{read_col_id} WHERE book = ?",
                    (book_id,),
                )
                read_row = cursor.fetchone()
                read = bool(read_row["value"]) if read_row else None

            # Get KOReader progress (custom column simple: id, book, value)
            ko_progress = None
            ko_progfloat_col_id = self._custom_columns_map.get("ko_progfloat")
            if ko_progfloat_col_id:
                cursor.execute(
                    f"SELECT value FROM custom_column_{ko_progfloat_col_id} "
                    "WHERE book = ?",
                    (book_id,),
                )
                progress_row = cursor.fetchone()
                ko_progress = progress_row["value"] if progress_row else None

            # Get KOReader status (enum column with link table, like tags)
            ko_status = None
            ko_status_col_id = self._custom_columns_map.get("ko_status")
            if ko_status_col_id:
                cursor.execute(
                    f"""SELECT ccv.value
                        FROM books_custom_column_{ko_status_col_id}_link ccl
                        JOIN custom_column_{ko_status_col_id} ccv
                            ON ccl.value = ccv.id
                        WHERE ccl.book = ?""",
                    (book_id,),
                )
                status_row = cursor.fetchone()
                ko_status = status_row["value"] if status_row else None

            # Get KOReader start date
            ko_date_started = None
            ko_start_col_id = self._custom_columns_map.get("ko_start")
            if ko_start_col_id:
                cursor.execute(
                    f"SELECT value FROM custom_column_{ko_start_col_id} WHERE book = ?",
                    (book_id,),
                )
                start_row = cursor.fetchone()
                ko_date_started = start_row["value"] if start_row else None

            # Get KOReader finish date
            ko_date_finished = None
            ko_finish_col_id = self._custom_columns_map.get("ko_finish")
            if ko_finish_col_id:
                cursor.execute(
                    f"SELECT value FROM custom_column_{ko_finish_col_id} "
                    "WHERE book = ?",
                    (book_id,),
                )
                finish_row = cursor.fetchone()
                ko_date_finished = finish_row["value"] if finish_row else None

            result.append(
                {
                    "id": book_id,
                    "title": title,
                    "authors": authors,
                    "tags": tags,
                    "read": read,
                    "rating": rating,
                    "ko_progress": ko_progress,
                    "ko_status": ko_status,
                    "ko_date_started": ko_date_started,
                    "ko_date_finished": ko_date_finished,
                }
            )

        conn.close()
        return result

    def _build_books_from_rows(
        self, rows: list[sqlite3.Row], conn: sqlite3.Connection
    ) -> list[CalibreBook]:
        """
        Construit les objets CalibreBook d'un lot de lignes SQL.

        Les relations (auteurs, tags, éditeur, colonnes personnalisées…) sont
        lues par une requête par relation pour tout le lot, et non par livre :
        le nombre de requêtes ne dépend pas du nombre de livres.

        Args:
            rows: Lignes SQL avec les données de base (table books)
            conn: Connexion active pour les requêtes complémentaires

        Returns:
            Livres complets, dans l'ordre des lignes
        """
        book_ids = [row["id"] for row in rows]

        def values_by_book(query: str) -> dict[int, list[Any]]:
            """Exécute `query` (2 colonnes : book, value) sur tout le lot.

            `query` contient un `{ids}` remplacé par les marqueurs du lot,
            découpé en paquets pour rester sous la limite de variables SQLite.
            L'ordre des valeurs d'un livre est celui de la requête.
            """
            grouped: dict[int, list[Any]] = {}
            for start in range(0, len(book_ids), BATCH_SIZE):
                chunk = book_ids[start : start + BATCH_SIZE]
                placeholders = ",".join("?" * len(chunk))
                for book, value in conn.execute(
                    query.format(ids=placeholders), chunk
                ).fetchall():
                    grouped.setdefault(book, []).append(value)
            return grouped

        def first_by_book(query: str) -> dict[int, Any]:
            return {book: values[0] for book, values in values_by_book(query).items()}

        def custom_column(label: str) -> dict[int, Any]:
            col_id = self._custom_columns_map.get(label)
            if not col_id:
                return {}
            return first_by_book(
                f"SELECT book, value FROM custom_column_{col_id} "
                "WHERE book IN ({ids}) ORDER BY id"
            )

        authors = values_by_book(
            """SELECT bal.book, a.name FROM authors a
               JOIN books_authors_link bal ON a.id = bal.author
               WHERE bal.book IN ({ids}) ORDER BY bal.id"""
        )
        tags = values_by_book(
            """SELECT btl.book, t.name FROM tags t
               JOIN books_tags_link btl ON t.id = btl.tag
               WHERE btl.book IN ({ids}) ORDER BY t.name"""
        )
        publishers = first_by_book(
            """SELECT bpl.book, p.name FROM publishers p
               JOIN books_publishers_link bpl ON p.id = bpl.publisher
               WHERE bpl.book IN ({ids}) ORDER BY bpl.id"""
        )
        series = first_by_book(
            """SELECT bsl.book, s.name FROM series s
               JOIN books_series_link bsl ON s.id = bsl.series
               WHERE bsl.book IN ({ids}) ORDER BY bsl.id"""
        )
        ratings = first_by_book(
            """SELECT brl.book, r.rating FROM ratings r
               JOIN books_ratings_link brl ON r.id = brl.rating
               WHERE brl.book IN ({ids}) ORDER BY brl.id"""
        )
        # ISBN : dans la table identifiers uniquement
        isbns = first_by_book(
            """SELECT book, val FROM identifiers
               WHERE type = 'isbn' AND book IN ({ids}) ORDER BY id"""
        )
        comments = first_by_book(
            "SELECT book, text FROM comments WHERE book IN ({ids}) ORDER BY id"
        )
        languages = values_by_book(
            """SELECT bll.book, l.lang_code FROM languages l
               JOIN books_languages_link bll ON l.id = bll.lang_code
               WHERE bll.book IN ({ids}) ORDER BY bll.item_order, bll.id"""
        )

        reads = custom_column("read")
        papers = custom_column("paper")
        personal_comments = custom_column("text")
        ko_progresses = custom_column("ko_progfloat")
        ko_starts = custom_column("ko_start")
        ko_finishes = custom_column("ko_finish")

        # KOReader status : colonne énumérée avec table de lien, comme les tags
        ko_statuses: dict[int, Any] = {}
        ko_status_col_id = self._custom_columns_map.get("ko_status")
        if ko_status_col_id:
            ko_statuses = first_by_book(
                f"""SELECT ccl.book, ccv.value
                    FROM books_custom_column_{ko_status_col_id}_link ccl
                    JOIN custom_column_{ko_status_col_id} ccv ON ccl.value = ccv.id
                    WHERE ccl.book IN ({{ids}}) ORDER BY ccl.id"""
            )

        def as_bool(values: dict[int, Any], book_id: int) -> bool | None:
            return bool(values[book_id]) if book_id in values else None

        return [
            CalibreBook(
                id=row["id"],
                title=row["title"],
                sort=row["sort"],
                isbn=isbns.get(row["id"]),
                timestamp=row["timestamp"],
                pubdate=row["pubdate"],
                last_modified=row["last_modified"],
                path=row["path"],
                uuid=row["uuid"],
                has_cover=bool(row["has_cover"]),
                series_index=row["series_index"],
                authors=authors.get(row["id"], []),
                tags=tags.get(row["id"], []),
                publisher=publishers.get(row["id"]),
                series=series.get(row["id"]),
                rating=ratings.get(row["id"]),
                comments=comments.get(row["id"]),
                languages=languages.get(row["id"], []),
                read=as_bool(reads, row["id"]),
                paper=as_bool(papers, row["id"]),
                personal_comments=personal_comments.get(row["id"]),
                ko_progress=ko_progresses.get(row["id"]),
                ko_status=ko_statuses.get(row["id"]),
                ko_date_started=ko_starts.get(row["id"]),
                ko_date_finished=ko_finishes.get(row["id"]),
            )
            for row in rows
        ]

    def get_authors(self, limit: int = 100, offset: int = 0) -> list[CalibreAuthor]:
        """
        Récupère la liste des auteurs.

        Args:
            limit: Nombre maximum de résultats
            offset: Décalage pour la pagination

        Returns:
            Liste d'auteurs

        Raises:
            RuntimeError: Si Calibre n'est pas disponible
        """
        if not self._available:
            raise RuntimeError("Calibre n'est pas disponible")

        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id, name, sort, link
            FROM authors
            ORDER BY sort
            LIMIT ? OFFSET ?
        """,
            (limit, offset),
        )

        authors = [
            CalibreAuthor(
                id=row["id"],
                name=row["name"],
                sort=row["sort"],
                link=row["link"] or None,
            )
            for row in cursor.fetchall()
        ]

        conn.close()
        return authors

    def get_statistics(self) -> CalibreStatistics:
        """
        Calcule les statistiques de la bibliothèque.

        Returns:
            Statistiques Calibre

        Raises:
            RuntimeError: Si Calibre n'est pas disponible
        """
        if not self._available:
            raise RuntimeError("Calibre n'est pas disponible")

        conn = self._get_connection()
        cursor = conn.cursor()

        # Base query pour appliquer le filtre bibliothèque virtuelle
        base_filter = ""
        params: list[Any] = []

        if self._virtual_library_tag:
            base_filter = """
                AND EXISTS (
                    SELECT 1 FROM books_tags_link btl
                    JOIN tags t ON btl.tag = t.id
                    WHERE btl.book = b.id AND t.name = ?
                )
            """
            params = [self._virtual_library_tag]

        # Total de livres
        cursor.execute(f"SELECT COUNT(*) FROM books b WHERE 1=1 {base_filter}", params)
        total_books = cursor.fetchone()[0]

        # Livres avec ISBN (dans table identifiers, pas books.isbn)
        cursor.execute(
            f"""
            SELECT COUNT(DISTINCT b.id) FROM books b
            JOIN identifiers i ON b.id = i.book
            WHERE i.type = 'isbn' {base_filter}
        """,
            params,
        )
        books_with_isbn = cursor.fetchone()[0]

        # Livres avec note
        cursor.execute(
            f"""
            SELECT COUNT(DISTINCT b.id) FROM books b
            JOIN books_ratings_link brl ON b.id = brl.book
            WHERE 1=1 {base_filter}
        """,
            params,
        )
        books_with_rating = cursor.fetchone()[0]

        # Livres avec tags
        cursor.execute(
            f"""
            SELECT COUNT(DISTINCT b.id) FROM books b
            JOIN books_tags_link btl ON b.id = btl.book
            WHERE 1=1 {base_filter}
        """,
            params,
        )
        books_with_tags = cursor.fetchone()[0]

        # Total d'auteurs
        cursor.execute("SELECT COUNT(*) FROM authors")
        total_authors = cursor.fetchone()[0]

        # Total de tags
        cursor.execute("SELECT COUNT(*) FROM tags")
        total_tags = cursor.fetchone()[0]

        # Livres lus (si colonne read existe)
        books_read = None
        read_col_id = self._custom_columns_map.get("read")
        if read_col_id:
            cursor.execute(
                f"""
                SELECT COUNT(DISTINCT b.id) FROM books b
                JOIN custom_column_{read_col_id} ccr ON b.id = ccr.book
                WHERE ccr.value = 1 {base_filter}
            """,
                params,
            )
            books_read = cursor.fetchone()[0]

        conn.close()

        return CalibreStatistics(
            total_books=total_books,
            books_with_isbn=books_with_isbn,
            books_with_rating=books_with_rating,
            books_with_tags=books_with_tags,
            total_authors=total_authors,
            total_tags=total_tags,
            books_read=books_read,
        )


# Instance globale du service (singleton)
calibre_service = CalibreService()
