"""Valider une suggestion conserve l'URL Babelio du livre (Issue #339).

Données construites depuis le vrai document `livresauteurs_cache` de
« Les Brebis égarées » (épisode du 01/11/2026), suggestion enrichie avec
`babelio_url` mais sans `babelio_publisher`.
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from bson import ObjectId
from fastapi.testclient import TestClient

from back_office_lmelp.app import app
from back_office_lmelp.services.collections_management_service import (
    CollectionsManagementService,
)


BABELIO_URL = "https://www.babelio.com/livres/Cash-Les-Brebis-egarees/2006493"
CACHE_ID = "6af6289c714985e520bd0628"  # pragma: allowlist secret
AVIS_CRITIQUE_ID = "6ae7780230990f4e6e0392e0"  # pragma: allowlist secret
EPISODE_OID = "6ae7497087efd8d343531f86"  # pragma: allowlist secret
AUTHOR_ID = ObjectId("6af62a077de3c738c888a910")  # pragma: allowlist secret
BOOK_ID = ObjectId("6af62a077de3c738c888a912")  # pragma: allowlist secret


def _validation_request(babelio_url: str | None = BABELIO_URL) -> dict[str, Any]:
    """Corps envoyé par LivresAuteurs.vue confirmValidation()."""
    request: dict[str, Any] = {
        "cache_id": CACHE_ID,
        "episode_oid": EPISODE_OID,
        "avis_critique_id": AVIS_CRITIQUE_ID,
        "auteur": "Madeline Cash",
        "titre": "Les Brebis égarées",
        "editeur": "De Noël",
        "user_validated_author": "Madeline Cash",
        "user_validated_title": "Les Brebis égarées",
        "user_validated_publisher": "De Noël",
    }
    if babelio_url:
        request["babelio_url"] = babelio_url
    return request


def _run_handle_book_validation(
    book_data: dict[str, Any],
) -> tuple[dict[str, Any], MagicMock]:
    service = CollectionsManagementService()
    with (
        patch.object(service, "mongodb_service") as mock_mongodb,
        patch(
            "back_office_lmelp.services.livres_auteurs_cache_service.livres_auteurs_cache_service"
        ) as mock_cache_service,
    ):
        mock_mongodb.create_author_if_not_exists.return_value = AUTHOR_ID
        mock_mongodb.create_book_if_not_exists.return_value = BOOK_ID
        mock_mongodb.update_book_validation.return_value = True
        mock_cache_service.is_summary_corrected.return_value = True
        result = service.handle_book_validation(book_data)
    return result, mock_mongodb


class TestHandleBookValidationKeepsBabelioUrl:
    def test_validated_suggestion_creates_book_with_url_babelio(self):
        _, mock_mongodb = _run_handle_book_validation(_validation_request())

        book_info = mock_mongodb.create_book_if_not_exists.call_args[0][0]
        assert book_info.get("url_babelio") == BABELIO_URL

    def test_validated_suggestion_sets_url_babelio_on_existing_book(self):
        """Le livre peut déjà exister (autre épisode) : create_book_if_not_exists
        ne touche pas à url_babelio, il faut le poser explicitement."""
        _, mock_mongodb = _run_handle_book_validation(_validation_request())

        mock_mongodb.update_livre_from_refresh.assert_called_once_with(
            str(BOOK_ID), {"url_babelio": BABELIO_URL}
        )

    def test_validation_without_babelio_url_leaves_book_for_babelio_linking(self):
        _, mock_mongodb = _run_handle_book_validation(
            _validation_request(babelio_url=None)
        )

        book_info = mock_mongodb.create_book_if_not_exists.call_args[0][0]
        assert book_info.get("url_babelio") is None
        mock_mongodb.update_livre_from_refresh.assert_not_called()


COVER_URL = "https://www.babelio.com/couv/CVT_Les-Brebis-egarees_1234.jpg"
AUTHOR_URL = "https://www.babelio.com/auteur/Madeline-Cash/123456"


class TestValidateSuggestionEndpointEnrichesFromBabelioPage:
    """Comme le chemin verified : couverture et URL auteur depuis la page livre
    (déjà en cache disque, aucune requête Babelio supplémentaire)."""

    def _post(
        self, babelio_url: str | None, existing_livre: dict[str, Any] | None = None
    ) -> tuple[Any, MagicMock, MagicMock]:
        client = TestClient(app)
        with (
            patch("back_office_lmelp.app.collections_management_service") as svc,
            patch("back_office_lmelp.app.mongodb_service") as mock_mongodb,
            patch("back_office_lmelp.app.babelio_service") as mock_babelio,
        ):
            svc.handle_book_validation.return_value = {
                "success": True,
                "author_id": str(AUTHOR_ID),
                "book_id": str(BOOK_ID),
            }
            mock_mongodb.get_livre_with_episodes.return_value = existing_livre or {
                "_id": BOOK_ID,
                "titre": "Les Brebis égarées",
                "url_babelio": BABELIO_URL,
            }
            mock_babelio.fetch_cover_url_from_babelio_page = AsyncMock(
                return_value=COVER_URL
            )
            mock_babelio.fetch_author_url_from_page = AsyncMock(return_value=AUTHOR_URL)
            response = client.post(
                "/api/livres-auteurs/validate-suggestion",
                json=_validation_request(babelio_url),
            )
        return response, mock_mongodb, mock_babelio

    def test_stores_cover_and_author_url(self):
        response, mock_mongodb, mock_babelio = self._post(BABELIO_URL)

        assert response.status_code == 200, response.text
        mock_babelio.fetch_cover_url_from_babelio_page.assert_awaited_once_with(
            BABELIO_URL, expected_title="Les Brebis égarées"
        )
        mock_mongodb.update_livre_from_refresh.assert_any_call(
            str(BOOK_ID), {"url_cover": COVER_URL}
        )
        mock_babelio.fetch_author_url_from_page.assert_awaited_once_with(BABELIO_URL)
        mock_mongodb.update_auteur_name_and_url.assert_called_once_with(
            str(AUTHOR_ID), url_babelio=AUTHOR_URL
        )

    def test_keeps_existing_cover(self):
        response, mock_mongodb, mock_babelio = self._post(
            BABELIO_URL,
            existing_livre={"_id": BOOK_ID, "url_cover": "https://exemple/couv.jpg"},
        )

        assert response.status_code == 200, response.text
        mock_babelio.fetch_cover_url_from_babelio_page.assert_not_called()

    def test_no_babelio_request_without_babelio_url(self):
        response, mock_mongodb, mock_babelio = self._post(None)

        assert response.status_code == 200, response.text
        mock_babelio.fetch_cover_url_from_babelio_page.assert_not_called()
        mock_babelio.fetch_author_url_from_page.assert_not_called()
        mock_mongodb.update_auteur_name_and_url.assert_not_called()

    def test_enrichment_failure_does_not_fail_validation(self):
        """Le livre est déjà créé avec url_babelio : un échec de la page
        (ban Babelio, réseau) ne doit pas transformer la validation en 500."""
        client = TestClient(app)
        with (
            patch("back_office_lmelp.app.collections_management_service") as svc,
            patch("back_office_lmelp.app.mongodb_service") as mock_mongodb,
            patch("back_office_lmelp.app.babelio_service") as mock_babelio,
        ):
            svc.handle_book_validation.return_value = {
                "success": True,
                "author_id": str(AUTHOR_ID),
                "book_id": str(BOOK_ID),
            }
            mock_mongodb.get_livre_with_episodes.return_value = {"_id": BOOK_ID}
            mock_babelio.fetch_cover_url_from_babelio_page = AsyncMock(
                side_effect=Exception("Babelio bloqué")
            )
            mock_babelio.fetch_author_url_from_page = AsyncMock(
                side_effect=Exception("Babelio bloqué")
            )
            response = client.post(
                "/api/livres-auteurs/validate-suggestion",
                json=_validation_request(),
            )

        assert response.status_code == 200, response.text
        assert response.json()["success"] is True
