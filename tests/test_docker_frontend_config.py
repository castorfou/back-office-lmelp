"""Tests statiques sur la configuration nginx du frontend (Issue #318).

Vérifie que nginx re-résout le nom ``backend`` à chaque requête via le DNS
interne de Docker, au lieu de figer son IP au démarrage : sans cela, une
recréation du conteneur backend (Watchtower, reboot NAS) qui change son IP
provoque des 502 jusqu'au redémarrage du frontend.

Approche statique (assertions texte sur nginx.conf/Dockerfile), pas de build
Docker réel — même pattern que test_docker_backend_config.py.
"""

import re
from pathlib import Path


FRONTEND_DIR = Path(__file__).parent.parent / "docker" / "build" / "frontend"
NGINX_CONF_PATH = FRONTEND_DIR / "nginx.conf"
DOCKERFILE_PATH = FRONTEND_DIR / "Dockerfile"


def _proxy_pass_by_location(content: str) -> dict[str, str]:
    """Associe chaque bloc ``location`` à la valeur de son ``proxy_pass``.

    La clé reprend le sélecteur tel qu'écrit (ex: ``"/api/"``, ``"= /api"``).
    """
    result = {}
    for match in re.finditer(r"location\s+([^{]+?)\s*\{([^{}]*)\}", content):
        proxy_pass = re.search(r"proxy_pass\s+([^;]+);", match.group(2))
        if proxy_pass:
            result[match.group(1)] = proxy_pass.group(1)
    return result


class TestNginxDynamicBackendResolution:
    def test_declares_docker_embedded_dns_resolver(self):
        """Le DNS Docker (127.0.0.11) est déclaré avec un cache court."""
        content = NGINX_CONF_PATH.read_text()

        assert re.search(r"^\s*resolver\s+127\.0\.0\.11\b[^;]*valid=", content, re.M), (
            "resolver 127.0.0.11 (avec valid=) absent : nginx fige l'IP du backend"
        )

    def test_backend_address_is_held_in_a_variable(self):
        """L'adresse du backend passe par une variable, forçant la résolution
        à l'exécution plutôt qu'au chargement de la conf."""
        content = NGINX_CONF_PATH.read_text()

        assert "set $backend backend:8000;" in content

    def test_no_proxy_pass_uses_a_hardcoded_hostname(self):
        """Aucun proxy_pass ne cible un nom d'hôte en dur (résolu une seule fois)."""
        proxy_passes = _proxy_pass_by_location(NGINX_CONF_PATH.read_text())

        assert proxy_passes, "aucun proxy_pass trouvé dans nginx.conf"
        hardcoded = {
            loc: target
            for loc, target in proxy_passes.items()
            if not target.startswith("http://$backend")
        }
        assert not hardcoded, f"proxy_pass avec hôte en dur : {hardcoded}"

    def test_proxied_paths_are_forwarded_unchanged(self):
        """Avec une variable, un chemin dans proxy_pass remplace TOUTE l'URI :
        les locations préfixées n'en ont donc pas, pour transmettre l'URI
        d'origine (``/api/livres?x=1`` → ``/api/livres?x=1``). Seul
        ``= /api`` (exact) est réécrit vers la racine du backend."""
        proxy_passes = _proxy_pass_by_location(NGINX_CONF_PATH.read_text())

        assert proxy_passes.get("/api/") == "http://$backend"
        assert proxy_passes.get("/docs") == "http://$backend"
        assert proxy_passes.get("/openapi.json") == "http://$backend"
        assert proxy_passes.get("= /api") == "http://$backend/"


class TestFrontendDockerfile:
    def test_dockerfile_validates_nginx_config_at_build(self):
        """``nginx -t`` au build : valide la syntaxe, et échouerait sur un
        ``proxy_pass`` à hôte en dur (``backend`` non résolvable hors stack)."""
        content = DOCKERFILE_PATH.read_text()

        assert re.search(r"^RUN nginx -t\b", content, re.M), "RUN nginx -t absent"
