"""Tests TDD pour le retour complet de migrate_one_book_and_author() (Issue #124 - Phase 12.2).

Ce module teste que migrate_one_book_and_author() retourne TOUJOURS titre, auteur et status
pour que MigrationRunner puisse afficher les vrais noms au lieu de "Unknown - Unknown".
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bson import ObjectId


class TestMigrateUrlBabelioCompleteReturn:
    """Tests pour la valeur de retour complète de migrate_one_book_and_author()."""

    @pytest.mark.asyncio
    async def test_should_return_titre_auteur_status_when_not_found(self):
        """Test TDD: migrate_one_book_and_author() doit retourner titre, auteur, status.

        Problème business réel:
        - Frontend affiche "Unknown - Unknown" au lieu du vrai titre/auteur
        - Cause: La fonction retourne seulement book_updated/author_updated
        - Solution: Retourner aussi titre, auteur, status pour l'affichage

        Scénario:
        1. Livre trouvé en MongoDB mais not_found sur Babelio
        2. migrate_one_book_and_author() doit retourner titre, auteur, status
        3. MigrationRunner pourra afficher "Le Petit Prince - Antoine de Saint-Exupéry"
        """
        # Arrange - Mock MongoDB
        livre_id = ObjectId()
        auteur_id = ObjectId()

        mock_livres_collection = MagicMock()
        mock_auteurs_collection = MagicMock()
        mock_prob_collection = MagicMock()

        mock_livres_collection.find_one.return_value = {
            "_id": livre_id,
            "titre": "Le Petit Prince",
            "auteur_id": auteur_id,
        }

        mock_auteurs_collection.find_one.return_value = {
            "_id": auteur_id,
            "nom": "Antoine de Saint-Exupéry",
        }

        mock_prob_collection.find.return_value = []
        mock_prob_collection.insert_one = MagicMock()

        def get_collection_side_effect(name):
            collections = {
                "livres": mock_livres_collection,
                "auteurs": mock_auteurs_collection,
                "babelio_problematic_cases": mock_prob_collection,
            }
            return collections.get(name, MagicMock())

        with patch(
            "scripts.migration_donnees.migrate_url_babelio.mongodb_service.get_collection"
        ) as mock_get_collection:
            mock_get_collection.side_effect = get_collection_side_effect

            # Mock BabelioService - retourne not_found
            mock_babelio = AsyncMock()
            mock_babelio.verify_book.return_value = {"status": "not_found"}

            from scripts.migration_donnees.migrate_url_babelio import (
                migrate_one_book_and_author,
            )

            # Act
            result = await migrate_one_book_and_author(
                babelio_service=mock_babelio, dry_run=False
            )

            # Assert - DOIT contenir titre, auteur, status
            assert result is not None, "Doit retourner un dict"
            assert "titre" in result, "Doit contenir 'titre' pour l'affichage frontend"
            assert "auteur" in result, (
                "Doit contenir 'auteur' pour l'affichage frontend"
            )
            assert "status" in result, (
                "Doit contenir 'status' pour l'affichage frontend"
            )

            # Vérifier les valeurs
            assert result["titre"] == "Le Petit Prince"
            assert result["auteur"] == "Antoine de Saint-Exupéry"
            assert result["status"] == "not_found"
            assert result["livre_updated"] is False
            assert result["auteur_updated"] is False

            # Garde-fou (Issue #304): un vrai not_found doit continuer à être
            # loggé dans babelio_problematic_cases
            mock_prob_collection.insert_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_not_log_problematic_case_when_status_is_blocked_403(self):
        """Test TDD (Issue #304): un blocage 403 ne doit PAS être loggé comme problématique.

        Problème business réel:
        - Babelio bloque une requête (cookie jstsToken expiré) → status='blocked_403'
        - Le script traitait ce cas exactement comme un vrai 'not_found' et
          l'insérait dans babelio_problematic_cases
        - Conséquence: le livre est exclu DÉFINITIVEMENT des runs futurs
          (load_problematic_book_ids()), même après correction du cookie
        - Un blocage 403 est transitoire, pas un problème de données du livre
        """
        # Arrange - Mock MongoDB
        livre_id = ObjectId()
        auteur_id = ObjectId()

        mock_livres_collection = MagicMock()
        mock_auteurs_collection = MagicMock()
        mock_prob_collection = MagicMock()

        mock_livres_collection.find_one.return_value = {
            "_id": livre_id,
            "titre": "Un Livre Bloqué",
            "auteur_id": auteur_id,
        }

        mock_auteurs_collection.find_one.return_value = {
            "_id": auteur_id,
            "nom": "Un Auteur",
        }

        mock_prob_collection.find.return_value = []
        mock_prob_collection.insert_one = MagicMock()

        def get_collection_side_effect(name):
            collections = {
                "livres": mock_livres_collection,
                "auteurs": mock_auteurs_collection,
                "babelio_problematic_cases": mock_prob_collection,
            }
            return collections.get(name, MagicMock())

        with patch(
            "scripts.migration_donnees.migrate_url_babelio.mongodb_service.get_collection"
        ) as mock_get_collection:
            mock_get_collection.side_effect = get_collection_side_effect

            # Mock BabelioService - retourne blocked_403 (cookie expiré)
            mock_babelio = AsyncMock()
            mock_babelio.verify_book.return_value = {
                "status": "blocked_403",
                "error_message": "Babelio a bloqué la requête (403).",
            }

            from scripts.migration_donnees.migrate_url_babelio import (
                migrate_one_book_and_author,
            )

            # Act
            result = await migrate_one_book_and_author(
                babelio_service=mock_babelio, dry_run=False
            )

            # Assert - le statut réel est bien retourné...
            assert result["status"] == "blocked_403"
            # ...mais AUCUNE entrée problématique ne doit être créée
            mock_prob_collection.insert_one.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_return_titre_auteur_status_when_success(self):
        """Test TDD: Retourner aussi titre/auteur/status quand la migration réussit."""
        # Arrange
        livre_id = ObjectId()
        auteur_id = ObjectId()

        mock_livres_collection = MagicMock()
        mock_auteurs_collection = MagicMock()
        mock_prob_collection = MagicMock()

        mock_livres_collection.find_one.return_value = {
            "_id": livre_id,
            "titre": "1984",
            "auteur_id": auteur_id,
        }

        mock_auteurs_collection.find_one.return_value = {
            "_id": auteur_id,
            "nom": "George Orwell",
        }

        mock_prob_collection.find.return_value = []

        # Mock update operations
        mock_livres_collection.update_one.return_value = MagicMock(matched_count=1)
        mock_auteurs_collection.update_one.return_value = MagicMock(matched_count=1)

        def get_collection_side_effect(name):
            collections = {
                "livres": mock_livres_collection,
                "auteurs": mock_auteurs_collection,
                "babelio_problematic_cases": mock_prob_collection,
            }
            return collections.get(name, MagicMock())

        with (
            patch(
                "scripts.migration_donnees.migrate_url_babelio.mongodb_service.get_collection"
            ) as mock_get_collection,
            patch(
                "scripts.migration_donnees.migrate_url_babelio.scrape_title_from_page"
            ) as mock_scrape,
            patch(
                "scripts.migration_donnees.migrate_url_babelio.normalize_title"
            ) as mock_normalize,
            patch(
                "scripts.migration_donnees.migrate_url_babelio.wait_rate_limit"
            ) as mock_wait,
        ):
            mock_get_collection.side_effect = get_collection_side_effect

            # Mock wait_rate_limit (async function)
            async def mock_wait_async():
                pass

            mock_wait.side_effect = mock_wait_async

            # Mock scrape_title_from_page (async function) pour retourner le titre exact
            async def mock_scrape_async(*args, **kwargs):
                return "1984"

            mock_scrape.side_effect = mock_scrape_async

            # Mock normalize_title pour retourner la même valeur
            mock_normalize.side_effect = lambda x: x

            # Mock BabelioService - retourne verified avec URL
            mock_babelio = AsyncMock()
            mock_babelio.verify_book.return_value = {
                "status": "verified",
                "babelio_url": "https://www.babelio.com/livres/Orwell-1984/1234",
                "babelio_author_url": "https://www.babelio.com/auteur/George-Orwell/5678",
            }

            # Mock HTTP 200 pour les deux URLs (livre + auteur)
            mock_response_livre = MagicMock()
            mock_response_livre.status = 200
            mock_response_livre.__aenter__ = AsyncMock(return_value=mock_response_livre)
            mock_response_livre.__aexit__ = AsyncMock(return_value=None)

            mock_response_auteur = MagicMock()
            mock_response_auteur.status = 200
            mock_response_auteur.__aenter__ = AsyncMock(
                return_value=mock_response_auteur
            )
            mock_response_auteur.__aexit__ = AsyncMock(return_value=None)

            mock_session = MagicMock()
            mock_session.get.side_effect = [mock_response_livre, mock_response_auteur]

            mock_babelio._get_session = AsyncMock(return_value=mock_session)

            from scripts.migration_donnees.migrate_url_babelio import (
                migrate_one_book_and_author,
            )

            # Act
            result = await migrate_one_book_and_author(
                babelio_service=mock_babelio, dry_run=False
            )

            # Assert
            assert result is not None
            assert "titre" in result
            assert "auteur" in result
            assert "status" in result

            assert result["titre"] == "1984"
            assert result["auteur"] == "George Orwell"
            assert result["status"] == "verified"
            assert result["livre_updated"] is True
            assert result["auteur_updated"] is True

    @pytest.mark.asyncio
    async def test_should_return_blocked_403_when_url_check_returns_403(self):
        """Test TDD (Issue #304): un 403 sur la vérification HTTP directe de l'URL
        livre (après un verify_book() réussi) doit remonter status='blocked_403',
        PAS 'error' générique.

        Bug racine (round 2): la vérification HTTP directe de l'URL livre
        doit passer par babelio_service._fetch_page() — le gateway centralisé
        qui applique les BONS headers de page ET le cookie jstsToken — au
        lieu d'un appel brut session.get() (session créée avec des headers
        d'API AJAX, sans le cookie anti-bot). _fetch_page() lève
        BabelioBlockedError sur 403 (et gère lui-même l'ouverture du circuit
        breaker), donc le code appelant doit catcher cette exception plutôt
        que de lire response.status.
        """
        from back_office_lmelp.services.babelio_service import BabelioBlockedError

        # Arrange
        livre_id = ObjectId()
        auteur_id = ObjectId()

        mock_livres_collection = MagicMock()
        mock_auteurs_collection = MagicMock()
        mock_prob_collection = MagicMock()

        mock_livres_collection.find_one.return_value = {
            "_id": livre_id,
            "titre": "1984",
            "auteur_id": auteur_id,
        }

        mock_auteurs_collection.find_one.return_value = {
            "_id": auteur_id,
            "nom": "George Orwell",
        }

        mock_prob_collection.find.return_value = []
        mock_prob_collection.insert_one = MagicMock()

        def get_collection_side_effect(name):
            collections = {
                "livres": mock_livres_collection,
                "auteurs": mock_auteurs_collection,
                "babelio_problematic_cases": mock_prob_collection,
            }
            return collections.get(name, MagicMock())

        with (
            patch(
                "scripts.migration_donnees.migrate_url_babelio.mongodb_service.get_collection"
            ) as mock_get_collection,
            patch(
                "scripts.migration_donnees.migrate_url_babelio.wait_rate_limit"
            ) as mock_wait,
        ):
            mock_get_collection.side_effect = get_collection_side_effect

            async def mock_wait_async():
                pass

            mock_wait.side_effect = mock_wait_async

            # Mock BabelioService.verify_book() - retourne verified avec URL
            mock_babelio = AsyncMock()
            mock_babelio.verify_book.return_value = {
                "status": "verified",
                "babelio_url": "https://www.babelio.com/livres/Orwell-1984/1234",
                "babelio_author_url": None,
            }
            mock_babelio._circuit_open = False

            # _fetch_page() lève BabelioBlockedError sur 403 (et ouvre déjà
            # le circuit breaker lui-même en interne)
            def raise_blocked(*_args, **_kwargs):
                mock_babelio._circuit_open = True
                raise BabelioBlockedError("Babelio 403")

            mock_babelio._fetch_page = AsyncMock(side_effect=raise_blocked)

            from scripts.migration_donnees.migrate_url_babelio import (
                migrate_one_book_and_author,
            )

            # Act
            result = await migrate_one_book_and_author(
                babelio_service=mock_babelio, dry_run=False
            )

            # Assert
            assert result["status"] == "blocked_403"
            # Un 403 est transitoire — ne doit PAS être loggé comme cas problématique
            mock_prob_collection.insert_one.assert_not_called()
            assert mock_babelio._circuit_open is True

    @pytest.mark.asyncio
    async def test_should_pass_stored_cookie_to_url_check_via_fetch_page(self):
        """Test TDD (Issue #304): la vérification HTTP directe de l'URL livre
        doit utiliser babelio_service._fetch_page(url), PAS un appel brut
        session.get(url) — pour hériter des bons headers de page ET du
        cookie jstsToken stocké côté serveur.

        Bug racine réel observé: verify_book()/fetch_author_url_from_page()
        (qui passent par _fetch_page) réussissent avec le cookie fourni,
        mais la vérification HTTP suivante échouait en 403 car elle utilisait
        session.get() directement — une session créée avec des headers
        d'API AJAX (Content-Type: application/json, X-Requested-With:
        XMLHttpRequest) et SANS le cookie jstsToken, que Babelio détecte et
        bloque alors que la requête précédente (même page, bons headers +
        cookie) avait réussi.
        """
        livre_id = ObjectId()
        auteur_id = ObjectId()

        mock_livres_collection = MagicMock()
        mock_auteurs_collection = MagicMock()
        mock_prob_collection = MagicMock()

        mock_livres_collection.find_one.return_value = {
            "_id": livre_id,
            "titre": "1984",
            "auteur_id": auteur_id,
        }
        mock_auteurs_collection.find_one.return_value = {
            "_id": auteur_id,
            "nom": "George Orwell",
        }
        mock_prob_collection.find.return_value = []

        def get_collection_side_effect(name):
            collections = {
                "livres": mock_livres_collection,
                "auteurs": mock_auteurs_collection,
                "babelio_problematic_cases": mock_prob_collection,
            }
            return collections.get(name, MagicMock())

        with (
            patch(
                "scripts.migration_donnees.migrate_url_babelio.mongodb_service.get_collection"
            ) as mock_get_collection,
            patch(
                "scripts.migration_donnees.migrate_url_babelio.wait_rate_limit"
            ) as mock_wait,
        ):
            mock_get_collection.side_effect = get_collection_side_effect

            async def mock_wait_async():
                pass

            mock_wait.side_effect = mock_wait_async

            mock_babelio = AsyncMock()
            mock_babelio.verify_book.return_value = {
                "status": "verified",
                "babelio_url": "https://www.babelio.com/livres/Orwell-1984/1234",
                "babelio_author_url": None,
            }
            mock_babelio._circuit_open = False
            mock_babelio._fetch_page = AsyncMock(
                return_value="<html><h1>1984</h1></html>"
            )

            from scripts.migration_donnees.migrate_url_babelio import (
                migrate_one_book_and_author,
            )

            await migrate_one_book_and_author(
                babelio_service=mock_babelio, dry_run=False
            )

            # La vérification HTTP directe doit passer par _fetch_page(url),
            # pas par un appel brut session.get() sans cookie
            mock_babelio._fetch_page.assert_any_call(
                "https://www.babelio.com/livres/Orwell-1984/1234"
            )

    @pytest.mark.asyncio
    async def test_should_pass_stored_cookie_to_author_url_check_via_fetch_page(self):
        """Test TDD (Issue #304): la vérification HTTP directe de l'URL AUTEUR
        doit aussi utiliser babelio_service._fetch_page(url), pas un appel
        brut session.get(url) — même bug que pour l'URL livre, sur le même
        site de vérification mais pour l'auteur.
        """
        livre_id = ObjectId()
        auteur_id = ObjectId()

        mock_livres_collection = MagicMock()
        mock_auteurs_collection = MagicMock()
        mock_prob_collection = MagicMock()

        mock_livres_collection.find_one.return_value = {
            "_id": livre_id,
            "titre": "1984",
            "auteur_id": auteur_id,
        }
        mock_auteurs_collection.find_one.return_value = {
            "_id": auteur_id,
            "nom": "George Orwell",
            # Pas d'url_babelio existante -> déclenche la vérification
        }
        mock_prob_collection.find.return_value = []
        mock_livres_collection.update_one.return_value = MagicMock(matched_count=1)
        mock_auteurs_collection.update_one.return_value = MagicMock(matched_count=1)

        def get_collection_side_effect(name):
            collections = {
                "livres": mock_livres_collection,
                "auteurs": mock_auteurs_collection,
                "babelio_problematic_cases": mock_prob_collection,
            }
            return collections.get(name, MagicMock())

        with (
            patch(
                "scripts.migration_donnees.migrate_url_babelio.mongodb_service.get_collection"
            ) as mock_get_collection,
            patch(
                "scripts.migration_donnees.migrate_url_babelio.scrape_title_from_page"
            ) as mock_scrape,
            patch(
                "scripts.migration_donnees.migrate_url_babelio.normalize_title"
            ) as mock_normalize,
            patch(
                "scripts.migration_donnees.migrate_url_babelio.wait_rate_limit"
            ) as mock_wait,
        ):
            mock_get_collection.side_effect = get_collection_side_effect

            async def mock_wait_async():
                pass

            mock_wait.side_effect = mock_wait_async

            async def mock_scrape_async(*args, **kwargs):
                return "1984"

            mock_scrape.side_effect = mock_scrape_async
            mock_normalize.side_effect = lambda x: x

            mock_babelio = AsyncMock()
            mock_babelio.verify_book.return_value = {
                "status": "verified",
                "babelio_url": "https://www.babelio.com/livres/Orwell-1984/1234",
                "babelio_author_url": "https://www.babelio.com/auteur/George-Orwell/5678",
            }
            mock_babelio._fetch_page = AsyncMock(
                return_value="<html><h1>1984</h1></html>"
            )

            from scripts.migration_donnees.migrate_url_babelio import (
                migrate_one_book_and_author,
            )

            await migrate_one_book_and_author(
                babelio_service=mock_babelio, dry_run=False
            )

            mock_babelio._fetch_page.assert_any_call(
                "https://www.babelio.com/auteur/George-Orwell/5678"
            )

    @pytest.mark.asyncio
    async def test_should_return_titre_auteur_status_when_http_error(self):
        """Test TDD: Retourner titre/auteur/status même en cas d'erreur HTTP.

        Problème business réel:
        - Avant: Quand Babelio était indisponible, le frontend affichait "Unknown - Unknown"
        - Après: Même en cas d'erreur, afficher "Le Petit Prince - Antoine de Saint-Exupéry"
        - Raison: L'utilisateur doit savoir quel livre était en cours de traitement

        Scénario:
        1. MongoDB trouve un livre
        2. BabelioService.verify_book() lève une exception (timeout/réseau)
        3. migrate_one_book_and_author() doit retourner titre, auteur, status="error"
        """
        # Arrange
        livre_id = ObjectId()
        auteur_id = ObjectId()

        mock_livres_collection = MagicMock()
        mock_auteurs_collection = MagicMock()
        mock_prob_collection = MagicMock()

        mock_livres_collection.find_one.return_value = {
            "_id": livre_id,
            "titre": "Le Petit Prince",
            "auteur_id": auteur_id,
        }

        mock_auteurs_collection.find_one.return_value = {
            "_id": auteur_id,
            "nom": "Antoine de Saint-Exupéry",
        }

        mock_prob_collection.find.return_value = []

        def get_collection_side_effect(name):
            collections = {
                "livres": mock_livres_collection,
                "auteurs": mock_auteurs_collection,
                "babelio_problematic_cases": mock_prob_collection,
            }
            return collections.get(name, MagicMock())

        with patch(
            "scripts.migration_donnees.migrate_url_babelio.mongodb_service.get_collection"
        ) as mock_get_collection:
            mock_get_collection.side_effect = get_collection_side_effect

            # Mock BabelioService.verify_book() - lève une exception HTTP
            mock_babelio = AsyncMock()
            mock_babelio.verify_book.side_effect = Exception("Connection timeout")

            from scripts.migration_donnees.migrate_url_babelio import (
                migrate_one_book_and_author,
            )

            # Act
            result = await migrate_one_book_and_author(
                babelio_service=mock_babelio, dry_run=False
            )

            # Assert - DOIT contenir titre, auteur, status même en cas d'erreur
            assert result is not None
            assert "titre" in result, "Doit contenir 'titre' même en cas d'erreur HTTP"
            assert "auteur" in result, (
                "Doit contenir 'auteur' même en cas d'erreur HTTP"
            )
            assert "status" in result, (
                "Doit contenir 'status' même en cas d'erreur HTTP"
            )

            # Vérifier les valeurs
            assert result["titre"] == "Le Petit Prince"
            assert result["auteur"] == "Antoine de Saint-Exupéry"
            assert result["status"] == "error"
            assert result["livre_updated"] is False
            assert result["auteur_updated"] is False
