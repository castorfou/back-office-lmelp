"""Tests TDD pour les modèles Author et Book (Issue #66)."""

from datetime import datetime

from bson import ObjectId

from back_office_lmelp.models.author import Author
from back_office_lmelp.models.book import Book


class TestAuthorModel:
    """Tests pour le modèle Author."""

    def test_author_model_exists_and_can_be_imported(self):
        """Test que le modèle Author existe et peut être importé."""
        # Ce test échouera initialement - nous devons créer le modèle
        assert Author is not None

    def test_author_creation_from_dict(self):
        """Test création d'un auteur à partir d'un dictionnaire."""
        author_data = {
            "_id": ObjectId("64f1234567890abcdef12345"),  # pragma: allowlist secret
            "nom": "Michel Houellebecq",
            "livres": [
                ObjectId("64f1234567890abcdef22222")  # pragma: allowlist secret
            ],  # pragma: allowlist secret
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        author = Author(author_data)

        assert author.id == str(author_data["_id"])
        assert author.nom == "Michel Houellebecq"
        assert isinstance(author.livres, list)
        assert len(author.livres) == 1
        assert isinstance(author.created_at, datetime)
        assert isinstance(author.updated_at, datetime)

    def test_author_to_dict(self):
        """Test conversion d'un auteur en dictionnaire."""
        author_data = {
            "_id": ObjectId("64f1234567890abcdef12345"),  # pragma: allowlist secret
            "nom": "Emmanuel Carrère",
            "livres": [],
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        author = Author(author_data)
        result_dict = author.to_dict()

        assert isinstance(result_dict, dict)
        assert "id" in result_dict
        assert "nom" in result_dict
        assert "livres" in result_dict
        assert "created_at" in result_dict
        assert "updated_at" in result_dict
        assert result_dict["nom"] == "Emmanuel Carrère"

    def test_author_for_mongodb_insert(self):
        """Test préparation d'un auteur pour insertion MongoDB."""
        author_data = {
            "nom": "Nouveau Auteur",
            "livres": [],
        }

        author = Author.for_mongodb_insert(author_data)

        assert isinstance(author, dict)
        assert "nom" in author
        assert "livres" in author
        assert "created_at" in author
        assert "updated_at" in author
        assert isinstance(author["created_at"], datetime)
        assert isinstance(author["updated_at"], datetime)

    def test_author_creation_with_url_babelio(self):
        """Test création d'un auteur avec URL Babelio (Issue #124)."""
        author_data = {
            "_id": ObjectId("64f1234567890abcdef12345"),  # pragma: allowlist secret
            "nom": "Catherine Millet",
            "url_babelio": "https://www.babelio.com/auteur/Catherine-Millet/7743",
            "livres": [],
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        author = Author(author_data)

        assert (
            author.url_babelio == "https://www.babelio.com/auteur/Catherine-Millet/7743"
        )

    def test_author_to_dict_includes_url_babelio(self):
        """Test que to_dict() inclut l'URL Babelio (Issue #124)."""
        author_data = {
            "_id": ObjectId("64f1234567890abcdef12345"),  # pragma: allowlist secret
            "nom": "Catherine Millet",
            "url_babelio": "https://www.babelio.com/auteur/Catherine-Millet/7743",
            "livres": [],
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        author = Author(author_data)
        result_dict = author.to_dict()

        assert "url_babelio" in result_dict
        assert (
            result_dict["url_babelio"]
            == "https://www.babelio.com/auteur/Catherine-Millet/7743"
        )

    def test_author_for_mongodb_insert_with_url_babelio(self):
        """Test insertion MongoDB avec URL Babelio (Issue #124)."""
        author_data = {
            "nom": "Nouveau Auteur",
            "url_babelio": "https://www.babelio.com/auteur/Nouveau-Auteur/12345",
            "livres": [],
        }

        author = Author.for_mongodb_insert(author_data)

        assert "url_babelio" in author
        assert (
            author["url_babelio"]
            == "https://www.babelio.com/auteur/Nouveau-Auteur/12345"
        )

    def test_author_without_url_babelio_defaults_to_none(self):
        """Test qu'un auteur sans URL Babelio a None par défaut (Issue #124)."""
        author_data = {
            "_id": ObjectId("64f1234567890abcdef12345"),  # pragma: allowlist secret
            "nom": "Auteur Sans URL",
            "livres": [],
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        author = Author(author_data)

        assert hasattr(author, "url_babelio")
        assert author.url_babelio is None


class TestBookModel:
    """Tests pour le modèle Book."""

    def test_book_model_exists_and_can_be_imported(self):
        """Test que le modèle Book existe et peut être importé."""
        # Ce test échouera initialement - nous devons créer le modèle
        assert Book is not None

    def test_book_creation_from_dict(self):
        """Test création d'un livre à partir d'un dictionnaire."""
        book_data = {
            "_id": ObjectId("64f1234567890abcdef22222"),  # pragma: allowlist secret
            "titre": "Les Particules élémentaires",
            "auteur_id": ObjectId(
                "64f1234567890abcdef12345"  # pragma: allowlist secret
            ),  # pragma: allowlist secret
            "editeur": "Flammarion",
            "episodes": [
                ObjectId("64f1234567890abcdef33333")  # pragma: allowlist secret
            ],  # pragma: allowlist secret
            "avis_critiques": [
                ObjectId("64f1234567890abcdef44444")  # pragma: allowlist secret
            ],  # pragma: allowlist secret
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        book = Book(book_data)

        assert book.id == str(book_data["_id"])
        assert book.titre == "Les Particules élémentaires"
        assert book.auteur_id == str(book_data["auteur_id"])
        assert book.editeur == "Flammarion"
        assert isinstance(book.episodes, list)
        assert isinstance(book.avis_critiques, list)
        assert isinstance(book.created_at, datetime)
        assert isinstance(book.updated_at, datetime)

    def test_book_to_dict(self):
        """Test conversion d'un livre en dictionnaire."""
        book_data = {
            "_id": ObjectId("64f1234567890abcdef22222"),  # pragma: allowlist secret
            "titre": "Kolkhoze",
            "auteur_id": ObjectId(
                "64f1234567890abcdef12345"  # pragma: allowlist secret
            ),  # pragma: allowlist secret
            "editeur": "POL",
            "episodes": [],
            "avis_critiques": [],
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        book = Book(book_data)
        result_dict = book.to_dict()

        assert isinstance(result_dict, dict)
        assert "id" in result_dict
        assert "titre" in result_dict
        assert "auteur_id" in result_dict
        assert "editeur" in result_dict
        assert "episodes" in result_dict
        assert "avis_critiques" in result_dict
        assert "created_at" in result_dict
        assert "updated_at" in result_dict
        assert result_dict["titre"] == "Kolkhoze"

    def test_book_for_mongodb_insert(self):
        """Test préparation d'un livre pour insertion MongoDB."""
        book_data = {
            "titre": "Nouveau Livre",
            "auteur_id": ObjectId(
                "64f1234567890abcdef12345"  # pragma: allowlist secret
            ),  # pragma: allowlist secret
            "editeur": "Nouvel Éditeur",
            "episodes": [],
            "avis_critiques": [],
        }

        book = Book.for_mongodb_insert(book_data)

        assert isinstance(book, dict)
        assert "titre" in book
        assert "auteur_id" in book
        assert "editeur" in book
        assert "episodes" in book
        assert "avis_critiques" in book
        assert "created_at" in book
        assert "updated_at" in book
        assert isinstance(book["created_at"], datetime)
        assert isinstance(book["updated_at"], datetime)

    def test_book_add_episode_reference(self):
        """Test ajout d'une référence d'épisode à un livre."""
        book_data = {
            "_id": ObjectId("64f1234567890abcdef22222"),  # pragma: allowlist secret
            "titre": "Test Book",
            "auteur_id": ObjectId(
                "64f1234567890abcdef12345"  # pragma: allowlist secret
            ),  # pragma: allowlist secret
            "editeur": "Test Publisher",
            "episodes": [],
            "avis_critiques": [],
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        book = Book(book_data)
        episode_id = ObjectId("64f1234567890abcdef33333")  # pragma: allowlist secret

        book.add_episode_reference(episode_id)

        assert str(episode_id) in book.episodes
        assert len(book.episodes) == 1

    def test_book_add_avis_critique_reference(self):
        """Test ajout d'une référence d'avis critique à un livre."""
        book_data = {
            "_id": ObjectId("64f1234567890abcdef22222"),  # pragma: allowlist secret
            "titre": "Test Book",
            "auteur_id": ObjectId(
                "64f1234567890abcdef12345"  # pragma: allowlist secret
            ),  # pragma: allowlist secret
            "editeur": "Test Publisher",
            "episodes": [],
            "avis_critiques": [],
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        book = Book(book_data)
        avis_id = ObjectId("64f1234567890abcdef44444")  # pragma: allowlist secret

        book.add_avis_critique_reference(avis_id)

        assert str(avis_id) in book.avis_critiques
        assert len(book.avis_critiques) == 1

    def test_book_creation_with_url_babelio(self):
        """Test création d'un livre avec URL Babelio (Issue #124)."""
        book_data = {
            "_id": ObjectId("64f1234567890abcdef22222"),  # pragma: allowlist secret
            "titre": "Simone Émonet",
            "auteur_id": ObjectId(  # pragma: allowlist secret
                "64f1234567890abcdef12345"  # pragma: allowlist secret
            ),
            "editeur": "Flammarion",
            "url_babelio": "https://www.babelio.com/livres/Millet-Simone-monet/1870367",
            "episodes": [],
            "avis_critiques": [],
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        book = Book(book_data)

        assert (
            book.url_babelio
            == "https://www.babelio.com/livres/Millet-Simone-monet/1870367"
        )

    def test_book_to_dict_includes_url_babelio(self):
        """Test que to_dict() inclut l'URL Babelio (Issue #124)."""
        book_data = {
            "_id": ObjectId("64f1234567890abcdef22222"),  # pragma: allowlist secret
            "titre": "Simone Émonet",
            "auteur_id": ObjectId(  # pragma: allowlist secret
                "64f1234567890abcdef12345"  # pragma: allowlist secret
            ),
            "editeur": "Flammarion",
            "url_babelio": "https://www.babelio.com/livres/Millet-Simone-monet/1870367",
            "episodes": [],
            "avis_critiques": [],
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        book = Book(book_data)
        result_dict = book.to_dict()

        assert "url_babelio" in result_dict
        assert (
            result_dict["url_babelio"]
            == "https://www.babelio.com/livres/Millet-Simone-monet/1870367"
        )

    def test_book_for_mongodb_insert_with_url_babelio(self):
        """Test insertion MongoDB avec URL Babelio (Issue #124)."""
        book_data = {
            "titre": "Nouveau Livre",
            "auteur_id": ObjectId(  # pragma: allowlist secret
                "64f1234567890abcdef12345"  # pragma: allowlist secret
            ),
            "editeur": "Nouvel Éditeur",
            "url_babelio": "https://www.babelio.com/livres/Auteur-Titre/123456",
            "episodes": [],
            "avis_critiques": [],
        }

        book = Book.for_mongodb_insert(book_data)

        assert "url_babelio" in book
        assert (
            book["url_babelio"] == "https://www.babelio.com/livres/Auteur-Titre/123456"
        )

    def test_book_without_url_babelio_defaults_to_none(self):
        """Test qu'un livre sans URL Babelio a None par défaut (Issue #124)."""
        book_data = {
            "_id": ObjectId("64f1234567890abcdef22222"),  # pragma: allowlist secret
            "titre": "Livre Sans URL",
            "auteur_id": ObjectId(  # pragma: allowlist secret
                "64f1234567890abcdef12345"  # pragma: allowlist secret
            ),
            "editeur": "Éditeur",
            "episodes": [],
            "avis_critiques": [],
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        book = Book(book_data)

        assert hasattr(book, "url_babelio")
        assert book.url_babelio is None
