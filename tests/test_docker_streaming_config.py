"""lmelp-streaming : nginx devant l'audio, derrière la clé d'écoute (ADR 0003).

Deux niveaux :
- assertions statiques sur nginx.conf et le Dockerfile (toujours) ;
- un vrai nginx devant un faux backend (seulement si `nginx` est installé :
  ces tests sont ignorés en CI). Ils vérifient ce qu'une lecture du fichier ne
  peut pas garantir : auth_request, cache des seules clés valides, Range,
  refus quand le backend est injoignable, liste blanche vers le backend.
"""

import http.server
import json
import re
import shutil
import socket
import subprocess
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest


STREAMING_DIR = Path(__file__).parent.parent / "docker" / "build" / "streaming"
NGINX_CONF = (STREAMING_DIR / "nginx.conf").read_text()
DOCKERFILE = (STREAMING_DIR / "Dockerfile").read_text()
WORKFLOW = (
    Path(__file__).parent.parent / ".github" / "workflows" / "docker-publish.yml"
).read_text()


def _locations(content: str) -> dict[str, str]:
    """Sélecteur de chaque bloc `location` → son contenu (sans bloc imbriqué)."""
    return {
        m.group(1).strip(): m.group(2)
        for m in re.finditer(
            r"location\s+([^{]+?)\s*\{((?:[^{}]|\{[^{}]*\})*)\}", content
        )
    }


# ------------------------------------------------------------------ statique
class TestConfigurationStatique:
    def test_seuls_deux_chemins_vont_au_backend(self) -> None:
        vers_backend = {
            loc: re.search(r"proxy_pass\s+([^;]+);", corps).group(1)  # type: ignore[union-attr]
            for loc, corps in _locations(NGINX_CONF).items()
            if "proxy_pass" in corps
        }

        assert vers_backend == {
            "= /_verifier_cle": "http://$backend/api/cle-ecoute/verifier",
            "= /signalements": "http://$backend/api/signalements",
        }

    def test_la_verification_est_interne_et_seule_une_cle_valide_est_en_cache(
        self,
    ) -> None:
        verifier = _locations(NGINX_CONF)["= /_verifier_cle"]

        assert "internal;" in verifier
        assert "proxy_cache_valid 204 60s;" in verifier
        assert re.findall(r"proxy_cache_valid[^;]*;", verifier) == [
            "proxy_cache_valid 204 60s;"
        ]

    def test_audio_et_signalements_exigent_la_cle(self) -> None:
        locations = _locations(NGINX_CONF)

        for loc in ("/audios/", "= /signalements"):
            assert "auth_request /_verifier_cle;" in locations[loc], loc
            assert 'add_header Cache-Control "no-store" always;' in locations[loc]
            assert "limit_req zone=" in locations[loc]

    def test_debit_limite_par_ip_reelle(self) -> None:
        assert "real_ip_header X-Real-IP;" in NGINX_CONF
        assert "set_real_ip_from" in NGINX_CONF
        assert "limit_req_zone $binary_remote_addr" in NGINX_CONF

    def test_la_source_mobile_est_posee_par_nginx(self) -> None:
        signalements = _locations(NGINX_CONF)["= /signalements"]

        assert "proxy_set_header X-Lmelp-Source mobile;" in signalements
        assert 'proxy_set_header X-Lmelp-Cle "";' in signalements

    def test_backend_resolu_a_chaque_requete(self) -> None:
        assert re.search(r"resolver\s+127\.0\.0\.11\b[^;]*valid=", NGINX_CONF)
        assert "set $backend backend:8000;" in NGINX_CONF

    def test_la_cle_ne_va_pas_dans_le_journal(self) -> None:
        format_ = re.search(r"log_format sans_cle([^;]+);", NGINX_CONF)

        assert format_ and "$request " not in format_.group(1)
        assert "$args" not in format_.group(1)
        assert "access_log /var/log/nginx/access.log sans_cle;" in NGINX_CONF

    def test_le_dockerfile_valide_la_configuration(self) -> None:
        assert DOCKERFILE.startswith("#") and "FROM nginx:alpine" in DOCKERFILE
        assert "COPY docker/build/streaming/nginx.conf" in DOCKERFILE
        assert "RUN nginx -t" in DOCKERFILE

    def test_l_image_est_publiee_et_mise_a_jour_sur_le_nas(self) -> None:
        assert "STREAMING_IMAGE_NAME: ghcr.io/castorfou/lmelp-streaming" in WORKFLOW
        assert "file: ./docker/build/streaming/Dockerfile" in WORKFLOW
        assert "${{ env.STREAMING_IMAGE_NAME }}" in re.search(
            r"IMAGES: ([^\n]+)", WORKFLOW
        ).group(1)  # type: ignore[union-attr]


# --------------------------------------------------------------- fonctionnel
NGINX = shutil.which("nginx") or (
    "/usr/sbin/nginx" if Path("/usr/sbin/nginx").exists() else None
)
avec_nginx = pytest.mark.skipif(NGINX is None, reason="nginx non installé (CI)")

CLE = "cle-valide-0123456789"  # pragma: allowlist secret
AUDIO_REL = "2026/episode.m4a"
CONTENU = bytes(range(256)) * 8


def _port_libre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


class FauxBackend(http.server.BaseHTTPRequestHandler):
    """Répond comme le backend : vérification de la clé et signalements."""

    requetes: list[dict[str, Any]] = []

    def _noter(self, corps: bytes = b"") -> None:
        FauxBackend.requetes.append(
            {
                "methode": self.command,
                "chemin": self.path,
                "entetes": dict(self.headers),
                "corps": corps,
            }
        )

    def do_GET(self) -> None:  # noqa: N802
        self._noter()
        if self.path == "/api/cle-ecoute/verifier":
            valide = self.headers.get("X-Lmelp-Cle") == CLE
            self.send_response(204 if valide else 403)
        else:
            self.send_response(200)
        self.end_headers()

    def do_POST(self) -> None:  # noqa: N802
        corps = self.rfile.read(int(self.headers.get("Content-Length") or 0))
        self._noter(corps)
        self.send_response(201)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"statut": "enregistre"}')

    def log_message(self, *args: Any) -> None:
        pass


@pytest.fixture
def streaming(tmp_path: Path) -> Iterator[dict[str, Any]]:
    """Le vrai nginx.conf, adapté pour tourner sans root ni Docker."""
    FauxBackend.requetes = []
    port_backend = _port_libre()
    backend = http.server.ThreadingHTTPServer(("127.0.0.1", port_backend), FauxBackend)
    threading.Thread(target=backend.serve_forever, daemon=True).start()

    audios = tmp_path / "srv" / "audios" / AUDIO_REL
    audios.parent.mkdir(parents=True)
    audios.write_bytes(CONTENU)
    (tmp_path / "cache").mkdir()
    port = _port_libre()
    conf = (
        NGINX_CONF.replace("listen 80;", f"listen 127.0.0.1:{port};")
        .replace("resolver 127.0.0.11 valid=10s ipv6=off;", "")
        .replace(
            "set $backend backend:8000;", f"set $backend 127.0.0.1:{port_backend};"
        )
        .replace("root /srv;", f"root {tmp_path / 'srv'};")
        .replace("/var/cache/nginx/cle", str(tmp_path / "cache"))
        .replace("/var/log/nginx/", f"{tmp_path}/")
    )
    principal = tmp_path / "nginx.conf"
    principal.write_text(
        f"""
pid {tmp_path}/nginx.pid;
error_log {tmp_path}/error.log warn;
events {{}}
http {{
    client_body_temp_path {tmp_path}/body;
    proxy_temp_path {tmp_path}/proxy;
    fastcgi_temp_path {tmp_path}/fastcgi;
    uwsgi_temp_path {tmp_path}/uwsgi;
    scgi_temp_path {tmp_path}/scgi;
    {conf}
}}
"""
    )
    commande = [
        str(NGINX),
        "-c",
        str(principal),
        "-p",
        str(tmp_path),
        "-e",
        f"{tmp_path}/error.log",
    ]
    subprocess.run([*commande, "-t"], check=True, capture_output=True)
    subprocess.run(commande, check=True, capture_output=True)
    for _ in range(50):
        try:
            socket.create_connection(("127.0.0.1", port), timeout=0.1).close()
            break
        except OSError:
            time.sleep(0.05)
    try:
        yield {
            "base": f"http://127.0.0.1:{port}",
            "backend": backend,
            "dossier": tmp_path,
        }
    finally:
        subprocess.run([*commande, "-s", "stop"], capture_output=True)
        backend.shutdown()


def appeler(
    url: str,
    methode: str = "GET",
    entetes: dict[str, str] | None = None,
    corps: bytes | None = None,
) -> tuple[int, dict[str, str], bytes]:
    requete = urllib.request.Request(
        url, data=corps, method=methode, headers=entetes or {}
    )
    try:
        with urllib.request.urlopen(requete, timeout=5) as reponse:
            return reponse.status, dict(reponse.headers), reponse.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()


def verifications() -> int:
    return sum(r["chemin"] == "/api/cle-ecoute/verifier" for r in FauxBackend.requetes)


@avec_nginx
class TestStreamingReel:
    def test_sans_cle_ou_avec_une_fausse_cle_l_audio_est_refuse(self, streaming):
        audio = f"{streaming['base']}/audios/{AUDIO_REL}"

        assert appeler(audio)[0] == 403
        assert appeler(audio, entetes={"X-Lmelp-Cle": "fausse"})[0] == 403

    def test_avec_la_cle_l_audio_est_servi_tel_quel_par_morceaux(self, streaming):
        audio = f"{streaming['base']}/audios/{AUDIO_REL}"

        statut, entetes, corps = appeler(
            audio, entetes={"X-Lmelp-Cle": CLE, "Range": "bytes=100-199"}
        )

        assert statut == 206
        assert corps == CONTENU[100:200]
        assert entetes["Content-Range"] == f"bytes 100-199/{len(CONTENU)}"
        assert entetes["Cache-Control"] == "no-store"

    def test_la_cle_peut_venir_en_parametre(self, streaming):
        statut, _, corps = appeler(f"{streaming['base']}/audios/{AUDIO_REL}?cle={CLE}")

        assert statut == 200
        assert corps == CONTENU

    def test_seule_une_cle_valide_est_gardee_en_cache(self, streaming):
        audio = f"{streaming['base']}/audios/{AUDIO_REL}"

        appeler(audio, entetes={"X-Lmelp-Cle": CLE})
        appeler(audio, entetes={"X-Lmelp-Cle": CLE})
        assert verifications() == 1

        appeler(audio, entetes={"X-Lmelp-Cle": "fausse"})
        appeler(audio, entetes={"X-Lmelp-Cle": "fausse"})
        assert verifications() == 3

    def test_backend_injoignable_vaut_refus_sauf_cle_en_cache(self, streaming):
        audio = f"{streaming['base']}/audios/{AUDIO_REL}"
        appeler(audio, entetes={"X-Lmelp-Cle": CLE})

        streaming["backend"].shutdown()
        streaming["backend"].server_close()

        assert appeler(audio, entetes={"X-Lmelp-Cle": CLE})[0] == 200
        assert appeler(audio, entetes={"X-Lmelp-Cle": "autre-cle"})[0] >= 403

    def test_un_signalement_est_relaye_avec_la_source_mobile(self, streaming):
        corps = json.dumps({"motif": "autre"}).encode()

        statut, _, _ = appeler(
            f"{streaming['base']}/signalements",
            methode="POST",
            corps=corps,
            entetes={
                "X-Lmelp-Cle": CLE,
                "Content-Type": "application/json",
                "X-Lmelp-Source": "web",
                "X-Real-IP": "203.0.113.7",
            },
        )

        assert statut == 201
        [relaye] = [r for r in FauxBackend.requetes if r["methode"] == "POST"]
        assert relaye["chemin"] == "/api/signalements"
        assert relaye["corps"] == corps
        assert relaye["entetes"]["X-Lmelp-Source"] == "mobile"
        assert "X-Lmelp-Cle" not in relaye["entetes"]
        assert "X-Real-IP" not in relaye["entetes"]

    def test_un_signalement_sans_cle_n_atteint_pas_le_backend(self, streaming):
        statut, _, _ = appeler(
            f"{streaming['base']}/signalements", methode="POST", corps=b"{}"
        )

        assert statut == 403
        assert not [r for r in FauxBackend.requetes if r["methode"] == "POST"]

    @pytest.mark.parametrize(
        "chemin",
        [
            "/api/cle-ecoute",
            "/api/cle-ecoute/verifier",
            "/_verifier_cle",
            "/api/episodes",
            "/audios/../etc/passwd",
        ],
    )
    def test_aucun_autre_chemin_n_atteint_le_backend(self, streaming, chemin):
        statut, _, corps = appeler(
            f"{streaming['base']}{chemin}", entetes={"X-Lmelp-Cle": CLE}
        )

        assert statut in (400, 403, 404)
        assert CLE.encode() not in corps
        assert not [
            r for r in FauxBackend.requetes if r["chemin"] != "/api/cle-ecoute/verifier"
        ]

    def test_la_cle_en_parametre_n_apparait_pas_dans_le_journal(self, streaming):
        appeler(f"{streaming['base']}/audios/{AUDIO_REL}?cle={CLE}")

        journal = (streaming["dossier"] / "access.log").read_text()
        assert f"/audios/{AUDIO_REL}" in journal
        assert CLE not in journal
