"""POST /api/babelio/cookie refuse ce qui n'est pas un en-tête Cookie Babelio.

Le cookie se récupère à la main dans les outils de développement de Firefox
(Réseau → requête « / » → En-têtes de requête → Cookie → Copier la valeur).
Copier une autre entrée (User-Agent, Set-Cookie de la réponse, toute la liste
des en-têtes) envoyait au serveur un « cookie » inutilisable : Babelio répondait
403, et ses 403 deviennent un ban IP d'environ 24 h.
"""

import pytest
from fastapi.testclient import TestClient

from back_office_lmelp.app import app
from back_office_lmelp.services.babelio_service import (
    babelio_service,
    normalize_cookie_header,
)


# Même structure qu'un en-tête Cookie réel copié depuis Firefox, valeurs factices.
FIREFOX_COOKIE = (
    'g_state={"i_l":1,"i_ll":1700000000000,"i_e":{"enable_itp_optimization":24},'
    '"i_et":1700000000000,"i_b":"AAAA/bbbb+CCCC"}; bbacml=0; '
    "bbac=00000000000000000000000000000000; id_user=1; disclaimer=1; "
    "_ga_XXXXXXXXXX=GS2.1.s1700000000$o1$g0$t1700000000$j38$l0$h0; "
    "_ga=GA1.2.123.456; jstsToken=AbCd%2FeF%2BgH%3D%3D; PHPSESSID=fakesession123"
)


@pytest.fixture(autouse=True)
def _reset_cookie():
    yield
    babelio_service.set_cookie(None)


@pytest.fixture
def client():
    return TestClient(app)


def test_accepts_cookie_header_copied_from_firefox(client):
    response = client.post("/api/babelio/cookie", json={"cookie": FIREFOX_COOKIE})
    assert response.status_code == 200
    assert babelio_service.get_cookie() == FIREFOX_COOKIE


@pytest.mark.parametrize(
    "pasted",
    [
        # User-Agent copié à la place du Cookie
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:150.0) Gecko/20100101 Firefox/150.0",
        # Set-Cookie de la réponse
        "jstsToken=AbCd; path=/; expires=Sat, 15 Nov 2026 12:00:00 GMT; HttpOnly",
        # Tous les en-têtes de la requête
        "Host: www.babelio.com\nCookie: jstsToken=AbCd; p=FR",
        # Le jeton seul, sans son nom
        "AbCd%2FeF%2BgH%3D%3D",
        # Un cookie sans jstsToken
        "disclaimer=1; p=FR; PHPSESSID=fakesession123",
        # jstsToken vide
        "jstsToken=; disclaimer=1",
    ],
)
def test_rejects_what_is_not_a_babelio_cookie_header(client, pasted):
    babelio_service.set_cookie("jstsToken=previous")

    response = client.post("/api/babelio/cookie", json={"cookie": pasted})

    assert response.status_code == 400
    assert response.json()["detail"]
    # Le cookie précédent n'est pas remplacé par la saisie refusée
    assert babelio_service.get_cookie() == "jstsToken=previous"


def test_strips_cookie_header_name_pasted_by_mistake():
    assert normalize_cookie_header("Cookie: jstsToken=AbCd; p=FR") == (
        "jstsToken=AbCd; p=FR"
    )


def test_empty_cookie_still_clears(client):
    babelio_service.set_cookie("jstsToken=previous")
    response = client.post("/api/babelio/cookie", json={"cookie": ""})
    assert response.status_code == 200
    assert babelio_service.get_cookie() is None
