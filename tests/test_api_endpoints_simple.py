"""Tests simplifiés pour les endpoints API du Back-Office LMELP."""

from back_office_lmelp.app import app


class TestSimpleEndpoints:
    """Tests simples pour vérifier que l'app démarre."""

    def test_app_creates_successfully(self):
        """Test que l'app FastAPI se crée sans erreur."""
        assert app is not None
        assert app.title == "Back-office LMELP"

    def test_app_has_cors_middleware(self):
        """Test que l'app a bien le middleware CORS configuré."""
        # Vérifier qu'il y a des middlewares (dont CORS)
        assert len(app.user_middleware) > 0

    def test_app_has_routes(self):
        """Test que l'app a des routes configurées."""
        routes = [route.path for route in app.routes]
        assert "/api/episodes" in routes
        assert "/api/episodes/{episode_id}" in routes
