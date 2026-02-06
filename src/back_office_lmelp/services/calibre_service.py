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
from pathlib import Path
from typing import Any

from ..models.calibre_models import (
    CalibreAuthor,
    CalibreBook,
    CalibreBookList,
    CalibreStatistics,
    CalibreStatus,
)
from ..settings import settings


logger = logging.getLogger(__name__)


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
            # Connexion directe sans passer par _get_connection (éviter récursion)
            conn = sqlite3.connect(f"file:{self._db_path}?mode=ro", uri=True)
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

        # Connexion en lecture seule (URI mode)
        conn = sqlite3.connect(f"file:{self._db_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row  # Accès par nom de colonne
        return conn

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

        return CalibreStatus(
            available=True,
            library_path=str(self._library_path),
            total_books=total_books,
            virtual_library_tag=self._virtual_library_tag,
            custom_columns=custom_columns,
        )

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
        # dans _build_book_from_row
        query = """
            SELECT DISTINCT
                b.id,
                b.title,
                b.sort,
                b.isbn,
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
        books = [self._build_book_from_row(row, conn) for row in rows]

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
                id, title, sort, isbn, timestamp, pubdate, last_modified,
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
        book = self._build_book_from_row(row, conn)
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

    def _build_book_from_row(
        self, row: sqlite3.Row, conn: sqlite3.Connection
    ) -> CalibreBook:
        """
        Construit un objet CalibreBook à partir d'une ligne SQL.

        Cette méthode complète les données de base avec les relations
        (auteurs, tags, etc.) via des requêtes supplémentaires.

        Args:
            row: Ligne SQL avec les données de base
            conn: Connexion active pour les requêtes complémentaires

        Returns:
            Objet CalibreBook complet
        """
        book_id = row["id"]
        cursor = conn.cursor()

        # Auteurs
        cursor.execute(
            """
            SELECT a.name
            FROM authors a
            JOIN books_authors_link bal ON a.id = bal.author
            WHERE bal.book = ?
            ORDER BY bal.id
        """,
            (book_id,),
        )
        authors = [r["name"] for r in cursor.fetchall()]

        # Tags
        cursor.execute(
            """
            SELECT t.name
            FROM tags t
            JOIN books_tags_link btl ON t.id = btl.tag
            WHERE btl.book = ?
            ORDER BY t.name
        """,
            (book_id,),
        )
        tags = [r["name"] for r in cursor.fetchall()]

        # Éditeur
        cursor.execute(
            """
            SELECT p.name
            FROM publishers p
            JOIN books_publishers_link bpl ON p.id = bpl.publisher
            WHERE bpl.book = ?
        """,
            (book_id,),
        )
        publisher_row = cursor.fetchone()
        publisher = publisher_row["name"] if publisher_row else None

        # Série
        cursor.execute(
            """
            SELECT s.name
            FROM series s
            JOIN books_series_link bsl ON s.id = bsl.series
            WHERE bsl.book = ?
        """,
            (book_id,),
        )
        series_row = cursor.fetchone()
        series = series_row["name"] if series_row else None

        # Note
        cursor.execute(
            """
            SELECT r.rating
            FROM ratings r
            JOIN books_ratings_link brl ON r.id = brl.rating
            WHERE brl.book = ?
        """,
            (book_id,),
        )
        rating_row = cursor.fetchone()
        rating = rating_row["rating"] if rating_row else None

        # ISBN (dans la table identifiers, pas books.isbn)
        cursor.execute(
            """
            SELECT val FROM identifiers
            WHERE book = ? AND type = 'isbn'
            LIMIT 1
        """,
            (book_id,),
        )
        isbn_row = cursor.fetchone()
        isbn = isbn_row["val"] if isbn_row else (row["isbn"] or None)

        # Commentaires
        cursor.execute("SELECT text FROM comments WHERE book = ?", (book_id,))
        comments_row = cursor.fetchone()
        comments = comments_row["text"] if comments_row else None

        # Langues
        cursor.execute(
            """
            SELECT l.lang_code
            FROM languages l
            JOIN books_languages_link bll ON l.id = bll.lang_code
            WHERE bll.book = ?
        """,
            (book_id,),
        )
        languages = [r["lang_code"] for r in cursor.fetchall()]

        # Colonnes personnalisées
        read = None
        paper = None
        personal_comments = None

        read_col_id = self._custom_columns_map.get("read")
        if read_col_id:
            cursor.execute(
                f"SELECT value FROM custom_column_{read_col_id} WHERE book = ?",
                (book_id,),
            )
            read_row = cursor.fetchone()
            read = bool(read_row["value"]) if read_row else None

        paper_col_id = self._custom_columns_map.get("paper")
        if paper_col_id:
            cursor.execute(
                f"SELECT value FROM custom_column_{paper_col_id} WHERE book = ?",
                (book_id,),
            )
            paper_row = cursor.fetchone()
            paper = bool(paper_row["value"]) if paper_row else None

        text_col_id = self._custom_columns_map.get("text")
        if text_col_id:
            cursor.execute(
                f"SELECT value FROM custom_column_{text_col_id} WHERE book = ?",
                (book_id,),
            )
            text_row = cursor.fetchone()
            personal_comments = text_row["value"] if text_row else None

        # Construire l'objet
        return CalibreBook(
            id=row["id"],
            title=row["title"],
            sort=row["sort"],
            isbn=isbn,
            timestamp=row["timestamp"],
            pubdate=row["pubdate"],
            last_modified=row["last_modified"],
            path=row["path"],
            uuid=row["uuid"],
            has_cover=bool(row["has_cover"]),
            series_index=row["series_index"],
            authors=authors,
            tags=tags,
            publisher=publisher,
            series=series,
            rating=rating,
            comments=comments,
            languages=languages,
            read=read,
            paper=paper,
            personal_comments=personal_comments,
        )

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
