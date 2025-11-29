"""
Tests pour CalibreService.

Tests unitaires couvrant toutes les fonctionnalités du service Calibre:
- Vérification de disponibilité
- Récupération des livres (liste, détails)
- Filtres (Lu, bibliothèque virtuelle)
- Statistiques
- Gestion des erreurs

Utilise des mocks pour isoler le service de la base SQLite réelle.
"""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from back_office_lmelp.models.calibre_models import (
    CalibreAuthor,
    CalibreBookList,
    CalibreStatistics,
)
from back_office_lmelp.services.calibre_service import CalibreService


# Fixtures pour créer des données de test réalistes
# (basées sur la structure réelle de Calibre découverte)


@pytest.fixture
def mock_book_row():
    """Crée une ligne SQL simulée pour un livre."""
    # Structure basée sur la vraie table books de Calibre
    row = {
        "id": 3,
        "title": "Le Silence de la mer",
        "sort": "Silence de la mer, Le",
        "isbn": "",  # ISBN est dans table identifiers, pas books
        "timestamp": "2024-01-15 10:30:00",
        "pubdate": "1942-02-01",
        "last_modified": "2024-01-15 10:30:00",
        "path": "Vercors/Le Silence de la mer (3)",
        "uuid": "12345678-1234-1234-1234-123456789012",
        "has_cover": 1,
        "series_index": 1.0,
    }
    # Convertir en sqlite3.Row simulé
    mock_row = MagicMock()
    mock_row.__getitem__ = lambda self, key: row[key]
    mock_row.keys.return_value = row.keys()
    return mock_row


@pytest.fixture
def mock_author_rows():
    """Crée des lignes SQL simulées pour les auteurs."""
    return [
        {"name": "Vercors"},
    ]


@pytest.fixture
def mock_tag_rows():
    """Crée des lignes SQL simulées pour les tags."""
    return [
        {"name": "guillaume"},
        {"name": "roman"},
        {"name": "français"},
    ]


@pytest.fixture
def mock_isbn_row():
    """Crée une ligne SQL simulée pour l'ISBN."""
    return {"val": "978-2-7011-1234-5"}


class TestCalibreServiceInitialization:
    """Tests d'initialisation et de disponibilité du service."""

    @patch("back_office_lmelp.services.calibre_service.settings")
    def test_service_not_available_when_no_library_path(self, mock_settings):
        """Service non disponible si bibliothèque non trouvée."""
        mock_settings.calibre_library_path = None
        mock_settings.calibre_virtual_library_tag = None

        service = CalibreService()

        assert not service.is_available()
        status = service.get_status()
        assert not status.available
        assert "Bibliothèque Calibre non trouvée" in status.error

    @patch("back_office_lmelp.services.calibre_service.settings")
    def test_service_not_available_when_path_does_not_exist(self, mock_settings):
        """Service non disponible si le chemin n'existe pas."""
        mock_settings.calibre_library_path = "/path/does/not/exist"
        mock_settings.calibre_virtual_library_tag = None

        service = CalibreService()

        assert not service.is_available()
        status = service.get_status()
        assert not status.available
        assert "n'existe pas" in status.error

    @patch("back_office_lmelp.services.calibre_service.settings")
    @patch("back_office_lmelp.services.calibre_service.Path")
    def test_service_not_available_when_metadata_db_missing(
        self, mock_path_class, mock_settings
    ):
        """Service non disponible si metadata.db est manquant."""
        mock_settings.calibre_library_path = "/calibre"
        mock_settings.calibre_virtual_library_tag = None

        # Simuler que le dossier existe mais pas metadata.db
        mock_library_path = MagicMock(spec=Path)
        mock_library_path.exists.return_value = True
        mock_library_path.is_dir.return_value = True

        mock_db_path = MagicMock(spec=Path)
        mock_db_path.exists.return_value = False  # metadata.db manquant

        mock_library_path.__truediv__ = lambda self, other: mock_db_path

        mock_path_class.return_value = mock_library_path

        service = CalibreService()

        assert not service.is_available()
        status = service.get_status()
        assert not status.available
        assert "metadata.db" in status.error

    @patch("back_office_lmelp.services.calibre_service.settings")
    @patch("back_office_lmelp.services.calibre_service.Path")
    @patch("back_office_lmelp.services.calibre_service.sqlite3.connect")
    def test_service_available_when_properly_configured(
        self, mock_connect, mock_path_class, mock_settings
    ):
        """Service disponible quand tout est correctement configuré."""
        mock_settings.calibre_library_path = "/calibre"
        mock_settings.calibre_virtual_library_tag = "guillaume"

        # Simuler que tout existe
        mock_library_path = MagicMock(spec=Path)
        mock_library_path.exists.return_value = True
        mock_library_path.is_dir.return_value = True
        mock_library_path.__str__ = lambda self: "/calibre"

        mock_db_path = MagicMock(spec=Path)
        mock_db_path.exists.return_value = True
        mock_db_path.__str__ = lambda self: "/calibre/metadata.db"

        mock_library_path.__truediv__ = lambda self, other: mock_db_path

        mock_path_class.return_value = mock_library_path

        # Simuler connexion SQLite réussie
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = [516]  # Nombre de livres
        mock_cursor.fetchall.return_value = [
            {"id": 1, "label": "read"},
            {"id": 2, "label": "paper"},
        ]
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        service = CalibreService()

        assert service.is_available()
        status = service.get_status()
        assert status.available
        assert status.library_path == "/calibre"
        assert status.virtual_library_tag == "guillaume"


class TestCalibreServiceCountBooks:
    """Tests de comptage des livres."""

    @patch("back_office_lmelp.services.calibre_service.settings")
    @patch("back_office_lmelp.services.calibre_service.Path")
    @patch("back_office_lmelp.services.calibre_service.sqlite3.connect")
    def test_count_all_books(self, mock_connect, mock_path_class, mock_settings):
        """Compte tous les livres sans filtre."""
        # Setup service disponible
        mock_settings.calibre_library_path = "/calibre"
        mock_settings.calibre_virtual_library_tag = None

        mock_library_path = MagicMock(spec=Path)
        mock_library_path.exists.return_value = True
        mock_library_path.is_dir.return_value = True

        mock_db_path = MagicMock(spec=Path)
        mock_db_path.exists.return_value = True
        mock_db_path.__str__ = lambda self: "/calibre/metadata.db"

        mock_library_path.__truediv__ = lambda self, other: mock_db_path
        mock_path_class.return_value = mock_library_path

        # Simuler connexions SQLite
        mock_conn_init = MagicMock()
        mock_cursor_init = MagicMock()
        mock_cursor_init.fetchone.return_value = [943]  # Total books
        mock_cursor_init.fetchall.return_value = []
        mock_conn_init.cursor.return_value = mock_cursor_init

        mock_conn_count = MagicMock()
        mock_cursor_count = MagicMock()
        mock_cursor_count.fetchone.return_value = [943]
        mock_conn_count.cursor.return_value = mock_cursor_count

        # Need one more connection for _load_custom_columns_map
        mock_conn_custom = MagicMock()
        mock_cursor_custom = MagicMock()
        mock_cursor_custom.fetchall.return_value = []
        mock_conn_custom.cursor.return_value = mock_cursor_custom

        mock_connect.side_effect = [mock_conn_init, mock_conn_custom, mock_conn_count]

        service = CalibreService()
        count = service.count_books()

        assert count == 943

    @patch("back_office_lmelp.services.calibre_service.settings")
    @patch("back_office_lmelp.services.calibre_service.Path")
    @patch("back_office_lmelp.services.calibre_service.sqlite3.connect")
    def test_count_books_with_virtual_library_tag(
        self, mock_connect, mock_path_class, mock_settings
    ):
        """Compte les livres filtrés par tag de bibliothèque virtuelle."""
        mock_settings.calibre_library_path = "/calibre"
        mock_settings.calibre_virtual_library_tag = "guillaume"

        mock_library_path = MagicMock(spec=Path)
        mock_library_path.exists.return_value = True
        mock_library_path.is_dir.return_value = True

        mock_db_path = MagicMock(spec=Path)
        mock_db_path.exists.return_value = True
        mock_db_path.__str__ = lambda self: "/calibre/metadata.db"

        mock_library_path.__truediv__ = lambda self, other: mock_db_path
        mock_path_class.return_value = mock_library_path

        # Simuler connexions
        mock_conn_init = MagicMock()
        mock_cursor_init = MagicMock()
        # Premier appel (init): compte avec tag, deuxième (custom cols)
        mock_cursor_init.fetchone.side_effect = [[516], [516]]
        mock_cursor_init.fetchall.return_value = [{"id": 1, "label": "read"}]
        mock_conn_init.cursor.return_value = mock_cursor_init

        mock_conn_count = MagicMock()
        mock_cursor_count = MagicMock()
        mock_cursor_count.fetchone.return_value = [516]  # Books with tag
        mock_conn_count.cursor.return_value = mock_cursor_count

        mock_connect.side_effect = [mock_conn_init, mock_conn_init, mock_conn_count]

        service = CalibreService()
        count = service.count_books()

        assert count == 516

    @patch("back_office_lmelp.services.calibre_service.settings")
    @patch("back_office_lmelp.services.calibre_service.Path")
    @patch("back_office_lmelp.services.calibre_service.sqlite3.connect")
    def test_count_read_books(self, mock_connect, mock_path_class, mock_settings):
        """Compte uniquement les livres lus."""
        mock_settings.calibre_library_path = "/calibre"
        mock_settings.calibre_virtual_library_tag = None

        mock_library_path = MagicMock(spec=Path)
        mock_library_path.exists.return_value = True
        mock_library_path.is_dir.return_value = True

        mock_db_path = MagicMock(spec=Path)
        mock_db_path.exists.return_value = True
        mock_db_path.__str__ = lambda self: "/calibre/metadata.db"

        mock_library_path.__truediv__ = lambda self, other: mock_db_path
        mock_path_class.return_value = mock_library_path

        # Simuler connexions
        mock_conn_init = MagicMock()
        mock_cursor_init = MagicMock()
        mock_cursor_init.fetchone.return_value = [943]
        mock_cursor_init.fetchall.return_value = [{"id": 1, "label": "read"}]
        mock_conn_init.cursor.return_value = mock_cursor_init

        mock_conn_custom = MagicMock()
        mock_cursor_custom = MagicMock()
        mock_cursor_custom.fetchall.return_value = [{"id": 1, "label": "read"}]
        mock_conn_custom.cursor.return_value = mock_cursor_custom

        mock_conn_count = MagicMock()
        mock_cursor_count = MagicMock()
        mock_cursor_count.fetchone.return_value = [299]  # Read books
        mock_conn_count.cursor.return_value = mock_cursor_count

        mock_connect.side_effect = [mock_conn_init, mock_conn_custom, mock_conn_count]

        service = CalibreService()
        count = service.count_books(read_filter=True)

        assert count == 299


class TestCalibreServiceGetBooks:
    """Tests de récupération des livres."""

    def _setup_available_service(
        self, mock_connect, mock_path_class, mock_settings, virtual_tag=None
    ):
        """Helper pour configurer un service disponible."""
        mock_settings.calibre_library_path = "/calibre"
        mock_settings.calibre_virtual_library_tag = virtual_tag

        mock_library_path = MagicMock(spec=Path)
        mock_library_path.exists.return_value = True
        mock_library_path.is_dir.return_value = True

        mock_db_path = MagicMock(spec=Path)
        mock_db_path.exists.return_value = True
        mock_db_path.__str__ = lambda self: "/calibre/metadata.db"

        mock_library_path.__truediv__ = lambda self, other: mock_db_path
        mock_path_class.return_value = mock_library_path

    @patch("back_office_lmelp.services.calibre_service.settings")
    @patch("back_office_lmelp.services.calibre_service.Path")
    @patch("back_office_lmelp.services.calibre_service.sqlite3.connect")
    def test_get_books_returns_paginated_list(
        self, mock_connect, mock_path_class, mock_settings, mock_book_row
    ):
        """Récupère une liste paginée de livres."""
        self._setup_available_service(
            mock_connect, mock_path_class, mock_settings, virtual_tag=None
        )

        # Simuler les connexions
        mock_conn_init = MagicMock()
        mock_cursor_init = MagicMock()
        mock_cursor_init.fetchone.return_value = [943]
        mock_cursor_init.fetchall.return_value = []
        mock_conn_init.cursor.return_value = mock_cursor_init

        # Connexion pour count_books
        mock_conn_count = MagicMock()
        mock_cursor_count = MagicMock()
        mock_cursor_count.fetchone.return_value = [943]
        mock_conn_count.cursor.return_value = mock_cursor_count

        # Connexion pour get_books
        mock_conn_get = MagicMock()
        mock_cursor_get = MagicMock()

        # Retourner mock_book_row pour la requête principale
        mock_cursor_get.fetchall.return_value = [mock_book_row]

        # Simuler les requêtes pour les relations
        def mock_execute_side_effect(query, params=None):
            if "authors" in query:
                mock_cursor_get.fetchall.return_value = [{"name": "Vercors"}]
            elif "tags" in query:
                mock_cursor_get.fetchall.return_value = [{"name": "guillaume"}]
            elif "publishers" in query or "series" in query:
                mock_cursor_get.fetchone.return_value = None
            elif "ratings" in query:
                mock_cursor_get.fetchone.return_value = {"rating": 8}
            elif "identifiers" in query and "isbn" in query:
                mock_cursor_get.fetchone.return_value = {"val": "978-2-7011-1234-5"}
            elif "comments" in query:
                mock_cursor_get.fetchone.return_value = None
            elif "languages" in query:
                mock_cursor_get.fetchall.return_value = [{"lang_code": "fra"}]
            elif "custom_column" in query:
                mock_cursor_get.fetchone.return_value = {"value": 1}
            else:
                # Requête principale get_books
                mock_cursor_get.fetchall.return_value = [mock_book_row]

        mock_cursor_get.execute = Mock(side_effect=mock_execute_side_effect)
        mock_cursor_get.fetchall = Mock(return_value=[mock_book_row])
        mock_conn_get.cursor.return_value = mock_cursor_get

        # Need custom columns connection too
        mock_conn_custom = MagicMock()
        mock_cursor_custom = MagicMock()
        mock_cursor_custom.fetchall.return_value = []
        mock_conn_custom.cursor.return_value = mock_cursor_custom

        mock_connect.side_effect = [
            mock_conn_init,
            mock_conn_custom,
            mock_conn_count,
            mock_conn_get,
        ]

        service = CalibreService()
        result = service.get_books(limit=5, offset=0)

        assert isinstance(result, CalibreBookList)
        assert result.total == 943
        assert result.limit == 5
        assert result.offset == 0
        assert len(result.books) == 1
        assert result.books[0].title == "Le Silence de la mer"

    @patch("back_office_lmelp.services.calibre_service.settings")
    @patch("back_office_lmelp.services.calibre_service.Path")
    @patch("back_office_lmelp.services.calibre_service.sqlite3.connect")
    def test_get_books_raises_error_when_not_available(
        self, mock_connect, mock_path_class, mock_settings
    ):
        """Lève une erreur si le service n'est pas disponible."""
        mock_settings.calibre_library_path = None
        mock_settings.calibre_virtual_library_tag = None

        service = CalibreService()

        with pytest.raises(RuntimeError, match="n'est pas disponible"):
            service.get_books()


class TestCalibreServiceGetBook:
    """Tests de récupération d'un livre par ID."""

    @patch("back_office_lmelp.services.calibre_service.settings")
    @patch("back_office_lmelp.services.calibre_service.Path")
    @patch("back_office_lmelp.services.calibre_service.sqlite3.connect")
    def test_get_book_returns_book_when_found(
        self, mock_connect, mock_path_class, mock_settings, mock_book_row
    ):
        """Retourne le livre quand trouvé."""
        mock_settings.calibre_library_path = "/calibre"
        mock_settings.calibre_virtual_library_tag = None

        mock_library_path = MagicMock(spec=Path)
        mock_library_path.exists.return_value = True
        mock_library_path.is_dir.return_value = True

        mock_db_path = MagicMock(spec=Path)
        mock_db_path.exists.return_value = True
        mock_db_path.__str__ = lambda self: "/calibre/metadata.db"

        mock_library_path.__truediv__ = lambda self, other: mock_db_path
        mock_path_class.return_value = mock_library_path

        # Connexion init
        mock_conn_init = MagicMock()
        mock_cursor_init = MagicMock()
        mock_cursor_init.fetchone.return_value = [943]
        mock_cursor_init.fetchall.return_value = []
        mock_conn_init.cursor.return_value = mock_cursor_init

        # Connexion get_book
        mock_conn_get = MagicMock()
        mock_cursor_get = MagicMock()

        def mock_execute_side_effect(query, params=None):
            if "WHERE id = ?" in query:
                mock_cursor_get.fetchone.return_value = mock_book_row
            elif "authors" in query:
                mock_cursor_get.fetchall.return_value = [{"name": "Vercors"}]
            elif "tags" in query:
                mock_cursor_get.fetchall.return_value = [{"name": "guillaume"}]
            elif "publishers" in query or "series" in query:
                mock_cursor_get.fetchone.return_value = None
            elif "ratings" in query:
                mock_cursor_get.fetchone.return_value = {"rating": 8}
            elif "identifiers" in query and "isbn" in query:
                mock_cursor_get.fetchone.return_value = {"val": "978-2-7011-1234-5"}
            elif "comments" in query:
                mock_cursor_get.fetchone.return_value = None
            elif "languages" in query:
                mock_cursor_get.fetchall.return_value = [{"lang_code": "fra"}]
            elif "custom_column" in query:
                mock_cursor_get.fetchone.return_value = None

        mock_cursor_get.execute = Mock(side_effect=mock_execute_side_effect)
        mock_conn_get.cursor.return_value = mock_cursor_get

        mock_conn_custom = MagicMock()
        mock_cursor_custom = MagicMock()
        mock_cursor_custom.fetchall.return_value = []
        mock_conn_custom.cursor.return_value = mock_cursor_custom

        mock_connect.side_effect = [mock_conn_init, mock_conn_custom, mock_conn_get]

        service = CalibreService()
        book = service.get_book(3)

        assert book is not None
        assert book.id == 3
        assert book.title == "Le Silence de la mer"
        assert book.isbn == "978-2-7011-1234-5"
        assert "Vercors" in book.authors

    @patch("back_office_lmelp.services.calibre_service.settings")
    @patch("back_office_lmelp.services.calibre_service.Path")
    @patch("back_office_lmelp.services.calibre_service.sqlite3.connect")
    def test_get_book_returns_none_when_not_found(
        self, mock_connect, mock_path_class, mock_settings
    ):
        """Retourne None si le livre n'est pas trouvé."""
        mock_settings.calibre_library_path = "/calibre"
        mock_settings.calibre_virtual_library_tag = None

        mock_library_path = MagicMock(spec=Path)
        mock_library_path.exists.return_value = True
        mock_library_path.is_dir.return_value = True

        mock_db_path = MagicMock(spec=Path)
        mock_db_path.exists.return_value = True
        mock_db_path.__str__ = lambda self: "/calibre/metadata.db"

        mock_library_path.__truediv__ = lambda self, other: mock_db_path
        mock_path_class.return_value = mock_library_path

        # Connexion init
        mock_conn_init = MagicMock()
        mock_cursor_init = MagicMock()
        mock_cursor_init.fetchone.return_value = [943]
        mock_cursor_init.fetchall.return_value = []
        mock_conn_init.cursor.return_value = mock_cursor_init

        # Connexion get_book
        mock_conn_get = MagicMock()
        mock_cursor_get = MagicMock()
        mock_cursor_get.fetchone.return_value = None  # Livre non trouvé
        mock_conn_get.cursor.return_value = mock_cursor_get

        mock_conn_custom = MagicMock()
        mock_cursor_custom = MagicMock()
        mock_cursor_custom.fetchall.return_value = []
        mock_conn_custom.cursor.return_value = mock_cursor_custom

        mock_connect.side_effect = [mock_conn_init, mock_conn_custom, mock_conn_get]

        service = CalibreService()
        book = service.get_book(999)

        assert book is None


class TestCalibreServiceGetAuthors:
    """Tests de récupération des auteurs."""

    @patch("back_office_lmelp.services.calibre_service.settings")
    @patch("back_office_lmelp.services.calibre_service.Path")
    @patch("back_office_lmelp.services.calibre_service.sqlite3.connect")
    def test_get_authors_returns_list(
        self, mock_connect, mock_path_class, mock_settings
    ):
        """Retourne la liste des auteurs."""
        mock_settings.calibre_library_path = "/calibre"
        mock_settings.calibre_virtual_library_tag = None

        mock_library_path = MagicMock(spec=Path)
        mock_library_path.exists.return_value = True
        mock_library_path.is_dir.return_value = True

        mock_db_path = MagicMock(spec=Path)
        mock_db_path.exists.return_value = True
        mock_db_path.__str__ = lambda self: "/calibre/metadata.db"

        mock_library_path.__truediv__ = lambda self, other: mock_db_path
        mock_path_class.return_value = mock_library_path

        # Connexion init
        mock_conn_init = MagicMock()
        mock_cursor_init = MagicMock()
        mock_cursor_init.fetchone.return_value = [943]
        mock_cursor_init.fetchall.return_value = []
        mock_conn_init.cursor.return_value = mock_cursor_init

        # Connexion get_authors
        mock_conn_get = MagicMock()
        mock_cursor_get = MagicMock()
        mock_cursor_get.fetchall.return_value = [
            {"id": 1, "name": "Vercors", "sort": "Vercors", "link": None},
            {"id": 2, "name": "Camus, Albert", "sort": "Camus, Albert", "link": None},
        ]
        mock_conn_get.cursor.return_value = mock_cursor_get

        mock_conn_custom = MagicMock()
        mock_cursor_custom = MagicMock()
        mock_cursor_custom.fetchall.return_value = []
        mock_conn_custom.cursor.return_value = mock_cursor_custom

        mock_connect.side_effect = [mock_conn_init, mock_conn_custom, mock_conn_get]

        service = CalibreService()
        authors = service.get_authors(limit=10, offset=0)

        assert len(authors) == 2
        assert all(isinstance(a, CalibreAuthor) for a in authors)
        assert authors[0].name == "Vercors"
        assert authors[1].name == "Camus, Albert"


class TestCalibreServiceGetStatistics:
    """Tests des statistiques."""

    @patch("back_office_lmelp.services.calibre_service.settings")
    @patch("back_office_lmelp.services.calibre_service.Path")
    @patch("back_office_lmelp.services.calibre_service.sqlite3.connect")
    def test_get_statistics_returns_correct_data(
        self, mock_connect, mock_path_class, mock_settings
    ):
        """Retourne les statistiques correctes."""
        mock_settings.calibre_library_path = "/calibre"
        mock_settings.calibre_virtual_library_tag = "guillaume"

        mock_library_path = MagicMock(spec=Path)
        mock_library_path.exists.return_value = True
        mock_library_path.is_dir.return_value = True

        mock_db_path = MagicMock(spec=Path)
        mock_db_path.exists.return_value = True
        mock_db_path.__str__ = lambda self: "/calibre/metadata.db"

        mock_library_path.__truediv__ = lambda self, other: mock_db_path
        mock_path_class.return_value = mock_library_path

        # Connexion init
        mock_conn_init = MagicMock()
        mock_cursor_init = MagicMock()
        mock_cursor_init.fetchone.return_value = (516,)
        mock_cursor_init.fetchall.return_value = [{"id": 1, "label": "read"}]
        mock_conn_init.cursor.return_value = mock_cursor_init

        # Connexion get_statistics
        mock_conn_stats = MagicMock()
        mock_cursor_stats = MagicMock()

        # Simuler les résultats des requêtes de statistiques avec side_effect direct
        mock_cursor_stats.fetchone.side_effect = [
            (516,),  # total_books - using tuples like real SQLite
            (221,),  # books_with_isbn
            (500,),  # books_with_rating
            (516,),  # books_with_tags
            (450,),  # total_authors
            (100,),  # total_tags
            (299,),  # books_read
        ]
        mock_conn_stats.cursor.return_value = mock_cursor_stats

        # Connexion pour _load_custom_columns_map (appelé dans __init__)
        mock_conn_custom_init = MagicMock()
        mock_cursor_custom_init = MagicMock()
        mock_cursor_custom_init.fetchall.return_value = [{"id": 1, "label": "read"}]
        mock_conn_custom_init.cursor.return_value = mock_cursor_custom_init

        mock_connect.side_effect = [
            mock_conn_init,
            mock_conn_custom_init,
            mock_conn_stats,
        ]

        service = CalibreService()
        stats = service.get_statistics()

        assert isinstance(stats, CalibreStatistics)
        assert stats.total_books == 516
        assert stats.books_with_isbn == 221
        assert stats.books_with_rating == 500
        assert stats.books_with_tags == 516
        assert stats.total_authors == 450
        assert stats.total_tags == 100
        assert stats.books_read == 299
