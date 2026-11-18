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


# Noms des cookies d'un navigateur connecté depuis que Babelio ne pose plus de
# jstsToken (Issue #367), valeurs factices.
LOGGED_IN_COOKIE_WITHOUT_JSTS = (
    "g_state={}; bbacml=0; disclaimer=1; _ga_XXXXXXXXXX=GS2.1.s1; _ga=GA1.2.3; "
    "_gcl_au=1.1.1; __gads=ID=x; __gpi=UID=y; __eoi=ID=z; p=FR; "
    "g_csrf_token=abc; PHPSESSID=fakesession123; "
    "bbac=00000000000000000000000000000000; id_user=1"
)


def test_accepts_logged_in_cookie_without_jsts_token(client):
    response = client.post(
        "/api/babelio/cookie", json={"cookie": LOGGED_IN_COOKIE_WITHOUT_JSTS}
    )
    assert response.status_code == 200
    assert babelio_service.get_cookie() == LOGGED_IN_COOKIE_WITHOUT_JSTS


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
        # Fenêtre privée non connectée : pas de cookie de session
        "p=FR; disclaimer=1; g_state={}",
        # PHPSESSID vide
        "PHPSESSID=; disclaimer=1",
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
    assert normalize_cookie_header("Cookie: PHPSESSID=abc; p=FR") == (
        "PHPSESSID=abc; p=FR"
    )


def test_missing_session_cookie_tells_to_log_in(client):
    response = client.post("/api/babelio/cookie", json={"cookie": "p=FR; disclaimer=1"})

    assert response.status_code == 400
    assert response.json()["detail"].startswith("PHPSESSID absent : connectez-vous")


def test_empty_cookie_still_clears(client):
    babelio_service.set_cookie("jstsToken=previous")
    response = client.post("/api/babelio/cookie", json={"cookie": ""})
    assert response.status_code == 200
    assert babelio_service.get_cookie() is None


# Un cookie copié sans être connecté au compte Babelio n'a pas d'id_user :
# Babelio lui répond par une page de vérification humaine (403). Il est
# accepté (à garder sous la main s'il passe), mais l'utilisateur est prévenu.
ANONYMOUS_COOKIE = "jstsToken=AbCd%2FeF%2BgH%3D%3D; PHPSESSID=fakesession123; p=FR"


def test_anonymous_cookie_is_accepted_with_a_warning(client):
    response = client.post("/api/babelio/cookie", json={"cookie": ANONYMOUS_COOKIE})

    assert response.status_code == 200
    assert babelio_service.get_cookie() == ANONYMOUS_COOKIE
    assert "Cookie anonyme" in response.json()["warning"]
    assert client.get("/api/babelio/status").json()["cookie_anonymous"] is True


def test_logged_in_cookie_has_no_warning(client):
    response = client.post("/api/babelio/cookie", json={"cookie": FIREFOX_COOKIE})

    assert response.status_code == 200
    assert response.json()["warning"] is None
    assert client.get("/api/babelio/status").json()["cookie_anonymous"] is False


def test_no_cookie_is_neither_anonymous_nor_logged_in(client):
    client.post("/api/babelio/cookie", json={"cookie": ""})

    assert client.get("/api/babelio/status").json()["cookie_anonymous"] is None


def test_stale_id_user_is_not_detected_as_anonymous(client):
    """Limite connue : id_user et bbac restent après une déconnexion.

    Un cookie copié déconnecté sur un navigateur déjà connecté par le passé a
    les mêmes noms qu'un cookie de session connectée ; seules les valeurs de
    bbac et PHPSESSID diffèrent (état côté serveur Babelio). L'avertissement ne
    couvre donc que le cas net (pas d'id_user) : son absence ne prouve rien,
    d'où la consigne de l'aide (être connecté, avatar visible).
    """
    stale = "bbacml=0; disclaimer=1; p=FR; bbac=00ff; id_user=1; PHPSESSID=abc"

    response = client.post("/api/babelio/cookie", json={"cookie": stale})

    assert response.json()["warning"] is None
