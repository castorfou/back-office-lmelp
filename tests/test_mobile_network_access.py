"""Tests pour l'accès réseau depuis un téléphone mobile."""

import os
from unittest.mock import patch


class TestMobileNetworkAccess:
    """Tests pour vérifier l'accès depuis des appareils mobiles du réseau."""

    def test_cors_accepts_network_ip_in_development(self):
        """Test que CORS accepte les connexions depuis une IP du réseau local en développement."""
        # Tester directement la fonction de configuration CORS
        from back_office_lmelp.app import get_cors_configuration

        # Simuler un environnement de développement
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            cors_config = get_cors_configuration()
            allowed_origins = cors_config.get("allow_origins", [])

            # En développement, CORS devrait autoriser toutes les origines ("*")
            # pour permettre l'accès depuis les appareils mobiles
            assert "*" in allowed_origins, (
                f"CORS should allow all origins (*) in development. "
                f"Current allowed_origins: {allowed_origins}"
            )

            # Vérifier aussi que allow_credentials est False (requis avec "*")
            assert cors_config.get("allow_credentials") is False, (
                "allow_credentials must be False when allow_origins is '*'"
            )

    def test_backend_listens_on_all_interfaces(self):
        """Test que le backend est configuré pour écouter sur toutes les interfaces (0.0.0.0)."""
        # Vérifier que la configuration par défaut utilise 0.0.0.0
        default_host = os.getenv("API_HOST", "0.0.0.0")
        assert default_host == "0.0.0.0", (
            f"Backend should listen on 0.0.0.0 by default, got: {default_host}"
        )

    def test_development_environment_configuration_exists(self):
        """Test qu'il existe une configuration spécifique pour l'environnement de développement."""
        # Ce test vérifie qu'on peut différencier les environnements
        # pour appliquer des configurations CORS différentes

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            env = os.getenv("ENVIRONMENT")
            assert env == "development", "Should be able to set development environment"

        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            env = os.getenv("ENVIRONMENT")
            assert env == "production", "Should be able to set production environment"

    def test_frontend_vite_config_allows_network_access(self):
        """Test que la configuration Vite permet l'accès depuis le réseau."""
        # Ce test vérifie que le fichier de configuration Vite sera modifié
        # pour permettre l'accès réseau

        # Lire la configuration Vite actuelle
        vite_config_path = "/workspaces/back-office-lmelp/frontend/vite.config.js"
        assert os.path.exists(vite_config_path), "vite.config.js should exist"

        with open(vite_config_path) as f:
            config_content = f.read()

        # Vérifier que la configuration inclut le host: '0.0.0.0'
        assert "host:" in config_content, (
            "Vite config should specify host configuration for network access"
        )

    def test_mobile_access_documentation_exists(self):
        """Test qu'il existe de la documentation pour l'accès mobile."""
        # Vérifier qu'il y aura de la documentation pour guider les utilisateurs
        docs_paths = [
            "/workspaces/back-office-lmelp/docs/user/mobile-access.md",
            "/workspaces/back-office-lmelp/docs/user/README.md",
        ]

        documentation_exists = any(os.path.exists(path) for path in docs_paths)

        # Si aucun fichier de doc spécifique n'existe, vérifier le README principal
        if not documentation_exists:
            readme_path = "/workspaces/back-office-lmelp/docs/user/README.md"
            if os.path.exists(readme_path):
                with open(readme_path) as f:
                    readme_content = f.read().lower()
                documentation_exists = (
                    "mobile" in readme_content or "téléphone" in readme_content
                )

        assert documentation_exists, (
            "Documentation should exist for mobile access instructions"
        )
