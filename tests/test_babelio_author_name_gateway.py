"""fetch_author_name_from_url() passe par la passerelle _fetch_page().

Une requête hors passerelle échappe au rythme, au cookie, à l'identité du
navigateur et au circuit breaker : c'est exactement le type de requête qui
fait bannir l'IP par Babelio.
"""

from unittest.mock import AsyncMock, patch

import pytest

import back_office_lmelp.services.babelio_service as babelio_module


AUTHOR_URL = "https://www.babelio.com/auteur/Christian-Thorel/165895"


@pytest.mark.asyncio
async def test_fetch_author_name_goes_through_fetch_page():
    service = babelio_module.BabelioService()
    html = "<html><body><h1>\n  Christian   Thorel\n</h1></body></html>"
    with patch.object(service, "_fetch_page", new=AsyncMock(return_value=html)) as fp:
        name = await service.fetch_author_name_from_url(AUTHOR_URL)

    assert name == "Christian Thorel"
    fp.assert_awaited_once_with(AUTHOR_URL)


@pytest.mark.asyncio
async def test_fetch_author_name_propagates_babelio_block():
    service = babelio_module.BabelioService()
    blocked = babelio_module.BabelioBlockedError("Circuit breaker ouvert")
    with (
        patch.object(service, "_fetch_page", new=AsyncMock(side_effect=blocked)),
        pytest.raises(babelio_module.BabelioBlockedError),
    ):
        await service.fetch_author_name_from_url(AUTHOR_URL)
