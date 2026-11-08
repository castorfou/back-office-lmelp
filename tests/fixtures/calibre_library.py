"""Vraie bibliothèque Calibre minimale, sur disque, pour les tests (Issue #327).

Le schéma reprend les tables que lit `CalibreService`, copiées du `metadata.db`
d'une bibliothèque Calibre réelle (structure seule : ni triggers, ni données).
Les triggers Calibre appellent des fonctions SQL propres à Calibre (title_sort,
uuid4…) et ne sont pas nécessaires à la lecture.

Contrairement aux tests qui mockent `sqlite3.connect`, cette bibliothèque permet
d'observer ce qui n'existe qu'avec un vrai fichier : sa date de modification et
son remplacement pendant une lecture.
"""

import os
import sqlite3
from pathlib import Path


SCHEMA = """
CREATE TABLE books ( id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL DEFAULT 'Unknown' COLLATE NOCASE,
    sort TEXT COLLATE NOCASE,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    pubdate TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    series_index REAL NOT NULL DEFAULT 1.0,
    author_sort TEXT COLLATE NOCASE,
    path TEXT NOT NULL DEFAULT "",
    uuid TEXT,
    has_cover BOOL DEFAULT 0,
    last_modified TIMESTAMP NOT NULL DEFAULT "2000-01-01 00:00:00+00:00");
CREATE TABLE authors ( id INTEGER PRIMARY KEY,
    name TEXT NOT NULL COLLATE NOCASE, sort TEXT COLLATE NOCASE,
    link TEXT NOT NULL DEFAULT "", UNIQUE(name));
CREATE TABLE books_authors_link ( id INTEGER PRIMARY KEY,
    book INTEGER NOT NULL, author INTEGER NOT NULL, UNIQUE(book, author));
CREATE TABLE tags ( id INTEGER PRIMARY KEY,
    name TEXT NOT NULL COLLATE NOCASE, link TEXT NOT NULL DEFAULT '', UNIQUE (name));
CREATE TABLE books_tags_link ( id INTEGER PRIMARY KEY,
    book INTEGER NOT NULL, tag INTEGER NOT NULL, UNIQUE(book, tag));
CREATE TABLE custom_columns ( id INTEGER PRIMARY KEY AUTOINCREMENT,
    label TEXT NOT NULL, name TEXT NOT NULL, datatype TEXT NOT NULL,
    mark_for_delete BOOL DEFAULT 0 NOT NULL, editable BOOL DEFAULT 1 NOT NULL,
    display TEXT DEFAULT "{}" NOT NULL, is_multiple BOOL DEFAULT 0 NOT NULL,
    normalized BOOL NOT NULL, UNIQUE(label));
CREATE TABLE comments ( id INTEGER PRIMARY KEY,
    book INTEGER NOT NULL, text TEXT NOT NULL COLLATE NOCASE, UNIQUE(book));
CREATE TABLE identifiers ( id INTEGER PRIMARY KEY, book INTEGER NOT NULL,
    type TEXT NOT NULL DEFAULT "isbn" COLLATE NOCASE,
    val TEXT NOT NULL COLLATE NOCASE, UNIQUE(book, type));
CREATE TABLE languages ( id INTEGER PRIMARY KEY,
    lang_code TEXT NOT NULL COLLATE NOCASE, link TEXT NOT NULL DEFAULT '',
    UNIQUE(lang_code));
CREATE TABLE books_languages_link ( id INTEGER PRIMARY KEY,
    book INTEGER NOT NULL, lang_code INTEGER NOT NULL,
    item_order INTEGER NOT NULL DEFAULT 0, UNIQUE(book, lang_code));
CREATE TABLE publishers ( id INTEGER PRIMARY KEY,
    name TEXT NOT NULL COLLATE NOCASE, sort TEXT COLLATE NOCASE,
    link TEXT NOT NULL DEFAULT '', UNIQUE(name));
CREATE TABLE books_publishers_link ( id INTEGER PRIMARY KEY,
    book INTEGER NOT NULL, publisher INTEGER NOT NULL, UNIQUE(book));
CREATE TABLE ratings ( id INTEGER PRIMARY KEY,
    rating INTEGER CHECK(rating > -1 AND rating < 11),
    link TEXT NOT NULL DEFAULT '', UNIQUE (rating));
CREATE TABLE books_ratings_link ( id INTEGER PRIMARY KEY,
    book INTEGER NOT NULL, rating INTEGER NOT NULL, UNIQUE(book, rating));
CREATE TABLE series ( id INTEGER PRIMARY KEY,
    name TEXT NOT NULL COLLATE NOCASE, sort TEXT COLLATE NOCASE,
    link TEXT NOT NULL DEFAULT '', UNIQUE (name));
CREATE TABLE books_series_link ( id INTEGER PRIMARY KEY,
    book INTEGER NOT NULL, series INTEGER NOT NULL, UNIQUE(book));
INSERT INTO custom_columns (id, label, name, datatype, normalized)
    VALUES (1, 'read', 'Read', 'bool', 0);
CREATE TABLE custom_column_1( id INTEGER PRIMARY KEY AUTOINCREMENT,
    book INTEGER, value BOOL NOT NULL, UNIQUE(book));
INSERT INTO custom_columns (id, label, name, datatype, normalized) VALUES
    (2, 'paper', 'paper', 'bool', 0),
    (3, 'text', 'Commentaire', 'comments', 0),
    (4, 'ko_progfloat', 'KOReader Precise Progress', 'float', 0),
    (5, 'ko_status', 'KOReader Book Status', 'text', 1),
    (7, 'ko_start', 'Date KOReader Started', 'datetime', 0),
    (8, 'ko_finish', 'Date KOReader Finished', 'datetime', 0);
CREATE TABLE custom_column_2( id INTEGER PRIMARY KEY AUTOINCREMENT,
    book INTEGER, value BOOL NOT NULL, UNIQUE(book));
CREATE TABLE custom_column_3( id INTEGER PRIMARY KEY AUTOINCREMENT,
    book INTEGER, value TEXT NOT NULL COLLATE NOCASE, UNIQUE(book));
CREATE TABLE custom_column_4( id INTEGER PRIMARY KEY AUTOINCREMENT,
    book INTEGER, value REAL NOT NULL, UNIQUE(book));
CREATE TABLE custom_column_5( id INTEGER PRIMARY KEY AUTOINCREMENT,
    value TEXT NOT NULL COLLATE NOCASE, link TEXT NOT NULL DEFAULT "",
    UNIQUE(value));
CREATE TABLE books_custom_column_5_link( id INTEGER PRIMARY KEY AUTOINCREMENT,
    book INTEGER NOT NULL, value INTEGER NOT NULL, UNIQUE(book, value));
CREATE TABLE custom_column_7( id INTEGER PRIMARY KEY AUTOINCREMENT,
    book INTEGER, value timestamp NOT NULL, UNIQUE(book));
CREATE TABLE custom_column_8( id INTEGER PRIMARY KEY AUTOINCREMENT,
    book INTEGER, value timestamp NOT NULL, UNIQUE(book));
"""


class CalibreLibrary:
    """Bibliothèque Calibre sur disque, modifiable comme le ferait Calibre."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.db_path = path / "metadata.db"
        with self._connect() as conn:
            conn.executescript(SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def add_book(
        self,
        title: str,
        author: str,
        last_modified: str = "2026-01-01 00:00:00+00:00",
        tags: list[str] | None = None,
        read: bool | None = None,
    ) -> int:
        """Ajoute un livre (format de date de Calibre) et retourne son id."""
        with self._connect() as conn:
            book_id = conn.execute(
                "INSERT INTO books (title, sort, path, last_modified) "
                "VALUES (?, ?, ?, ?)",
                (title, title, f"{author}/{title}", last_modified),
            ).lastrowid
            conn.execute("INSERT OR IGNORE INTO authors (name) VALUES (?)", (author,))
            (author_id,) = conn.execute(
                "SELECT id FROM authors WHERE name = ?", (author,)
            ).fetchone()
            conn.execute(
                "INSERT INTO books_authors_link (book, author) VALUES (?, ?)",
                (book_id, author_id),
            )
            for tag in tags or []:
                conn.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag,))
                (tag_id,) = conn.execute(
                    "SELECT id FROM tags WHERE name = ?", (tag,)
                ).fetchone()
                conn.execute(
                    "INSERT INTO books_tags_link (book, tag) VALUES (?, ?)",
                    (book_id, tag_id),
                )
            if read is not None:
                conn.execute(
                    "INSERT INTO custom_column_1 (book, value) VALUES (?, ?)",
                    (book_id, int(read)),
                )
        assert book_id is not None
        return book_id

    def add_details(
        self,
        book_id: int,
        coauthors: list[str] | None = None,
        publisher: str | None = None,
        series: str | None = None,
        rating: int | None = None,
        isbn: str | None = None,
        comment: str | None = None,
        languages: list[str] | None = None,
        paper: bool | None = None,
        personal_comment: str | None = None,
        ko_progress: float | None = None,
        ko_status: str | None = None,
        ko_start: str | None = None,
        ko_finish: str | None = None,
    ) -> None:
        """Complète un livre avec les métadonnées que lit `CalibreService`."""
        with self._connect() as conn:
            for author in coauthors or []:
                conn.execute(
                    "INSERT OR IGNORE INTO authors (name) VALUES (?)", (author,)
                )
                (author_id,) = conn.execute(
                    "SELECT id FROM authors WHERE name = ?", (author,)
                ).fetchone()
                conn.execute(
                    "INSERT INTO books_authors_link (book, author) VALUES (?, ?)",
                    (book_id, author_id),
                )
            for table, column, value in (
                ("publishers", "publisher", publisher),
                ("series", "series", series),
                ("ratings", "rating", rating),
            ):
                if value is None:
                    continue
                name_col = "rating" if table == "ratings" else "name"
                conn.execute(
                    f"INSERT OR IGNORE INTO {table} ({name_col}) VALUES (?)", (value,)
                )
                (item_id,) = conn.execute(
                    f"SELECT id FROM {table} WHERE {name_col} = ?", (value,)
                ).fetchone()
                conn.execute(
                    f"INSERT INTO books_{table}_link (book, {column}) VALUES (?, ?)",
                    (book_id, item_id),
                )
            if isbn is not None:
                conn.execute(
                    "INSERT INTO identifiers (book, type, val) VALUES (?, 'isbn', ?)",
                    (book_id, isbn),
                )
            if comment is not None:
                conn.execute(
                    "INSERT INTO comments (book, text) VALUES (?, ?)",
                    (book_id, comment),
                )
            for order, lang in enumerate(languages or []):
                conn.execute(
                    "INSERT OR IGNORE INTO languages (lang_code) VALUES (?)", (lang,)
                )
                (lang_id,) = conn.execute(
                    "SELECT id FROM languages WHERE lang_code = ?", (lang,)
                ).fetchone()
                conn.execute(
                    "INSERT INTO books_languages_link (book, lang_code, item_order) "
                    "VALUES (?, ?, ?)",
                    (book_id, lang_id, order),
                )
            custom_values: tuple[tuple[int, str | float | None], ...] = (
                (2, None if paper is None else int(paper)),
                (3, personal_comment),
                (4, ko_progress),
                (7, ko_start),
                (8, ko_finish),
            )
            for col_id, col_value in custom_values:
                if col_value is not None:
                    conn.execute(
                        f"INSERT INTO custom_column_{col_id} (book, value) "
                        "VALUES (?, ?)",
                        (book_id, col_value),
                    )
            if ko_status is not None:
                conn.execute(
                    "INSERT OR IGNORE INTO custom_column_5 (value) VALUES (?)",
                    (ko_status,),
                )
                (status_id,) = conn.execute(
                    "SELECT id FROM custom_column_5 WHERE value = ?", (ko_status,)
                ).fetchone()
                conn.execute(
                    "INSERT INTO books_custom_column_5_link (book, value) "
                    "VALUES (?, ?)",
                    (book_id, status_id),
                )

    def rename_book(self, book_id: int, title: str, last_modified: str) -> None:
        """Modifie le titre d'un livre, comme une édition dans Calibre."""
        with self._connect() as conn:
            conn.execute(
                "UPDATE books SET title = ?, sort = ?, last_modified = ? WHERE id = ?",
                (title, title, last_modified, book_id),
            )

    def set_mtime(self, timestamp: float) -> None:
        """Fixe la date de modification de metadata.db (arrivée d'une synchro)."""
        os.utime(self.db_path, (timestamp, timestamp))
