"""
Modèles Pydantic pour l'intégration Calibre.

Ces modèles représentent les données extraites de la bibliothèque Calibre
via accès direct SQLite à metadata.db.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CalibreAuthor(BaseModel):  # type: ignore[misc]
    """Représente un auteur dans Calibre."""

    id: int = Field(..., description="ID unique de l'auteur dans Calibre")
    name: str = Field(..., description="Nom complet de l'auteur")
    sort: str | None = Field(None, description="Nom pour le tri (ex: 'Rowling, J.K.')")
    link: str | None = Field(None, description="URL vers la page de l'auteur")


class CalibreBook(BaseModel):  # type: ignore[misc]
    """
    Représente un livre dans Calibre.

    Les données sont extraites de la base SQLite Calibre (metadata.db)
    avec les jointures nécessaires pour reconstituer les relations.
    """

    # Champs de base (table books)
    id: int = Field(..., description="ID unique du livre dans Calibre")
    title: str = Field(..., description="Titre du livre")
    sort: str | None = Field(None, description="Titre pour le tri")
    timestamp: datetime | None = Field(None, description="Date d'ajout dans Calibre")
    pubdate: datetime | None = Field(None, description="Date de publication")
    last_modified: datetime | None = Field(
        None, description="Dernière modification métadonnées"
    )
    path: str | None = Field(None, description="Chemin relatif vers les fichiers")
    uuid: str | None = Field(None, description="UUID unique du livre")
    has_cover: bool = Field(False, description="Présence d'une couverture")

    # Champs ISBN (table books)
    isbn: str | None = Field(None, description="ISBN du livre")

    # Relations (via tables de liaison)
    authors: list[str] = Field(
        default_factory=list, description="Liste des noms d'auteurs"
    )
    tags: list[str] = Field(default_factory=list, description="Liste des tags")
    publisher: str | None = Field(None, description="Éditeur")
    series: str | None = Field(None, description="Nom de la série")
    series_index: float | None = Field(None, description="Position dans la série")

    # Note (via books_ratings_link + ratings)
    # Note: Dans Calibre, les notes sont stockées comme des entiers (0-10)
    # où 0 = pas de note, 2 = 1 étoile, 4 = 2 étoiles, ..., 10 = 5 étoiles
    rating: int | None = Field(
        None, description="Note sur 10 (0=pas de note, 2-10 par pas de 2)"
    )

    # Commentaires/description (table comments)
    comments: str | None = Field(None, description="Commentaires/description du livre")

    # Langues (via books_languages_link + languages)
    languages: list[str] = Field(
        default_factory=list, description="Codes de langue (ex: ['fra', 'eng'])"
    )

    # Colonnes personnalisées (spécifiques à chaque bibliothèque Calibre)
    read: bool | None = Field(
        None,
        description="Marqueur 'Lu' (colonne personnalisée #read)",
        alias="custom_read",
    )
    paper: bool | None = Field(
        None,
        description="Livre au format papier (colonne personnalisée #paper)",
        alias="custom_paper",
    )
    personal_comments: str | None = Field(
        None,
        description="Commentaires personnels (colonne personnalisée #text)",
        alias="custom_text",
    )

    model_config = ConfigDict(
        populate_by_name=True  # Permet d'utiliser les alias ou les noms de champs
    )


class CalibreBookList(BaseModel):  # type: ignore[misc]
    """Liste paginée de livres Calibre."""

    total: int = Field(..., description="Nombre total de livres (avant pagination)")
    offset: int = Field(0, description="Offset de pagination")
    limit: int = Field(100, description="Limite de résultats par page")
    books: list[CalibreBook] = Field(
        default_factory=list, description="Liste des livres"
    )


class CalibreStatus(BaseModel):  # type: ignore[misc]
    """Statut de l'intégration Calibre."""

    available: bool = Field(..., description="Calibre est disponible et accessible")
    library_path: str | None = Field(None, description="Chemin de la bibliothèque")
    total_books: int | None = Field(None, description="Nombre total de livres")
    virtual_library_tag: str | None = Field(
        None, description="Tag de filtre pour bibliothèque virtuelle"
    )
    custom_columns: dict[str, str] = Field(
        default_factory=dict, description="Colonnes personnalisées disponibles"
    )
    error: str | None = Field(None, description="Message d'erreur si non disponible")


class CalibreStatistics(BaseModel):  # type: ignore[misc]
    """Statistiques de la bibliothèque Calibre."""

    total_books: int = Field(..., description="Nombre total de livres")
    books_with_isbn: int = Field(..., description="Livres avec ISBN")
    books_with_rating: int = Field(..., description="Livres avec note")
    books_with_tags: int = Field(..., description="Livres avec tags")
    total_authors: int = Field(..., description="Nombre total d'auteurs")
    total_tags: int = Field(..., description="Nombre total de tags")
    books_read: int | None = Field(None, description="Livres lus (si colonne #read)")
