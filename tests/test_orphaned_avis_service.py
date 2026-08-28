"""
Tests pour le service de détection et nettoyage des avis orphelins.

Approche TDD incrémentale (Issue #271):
1. Test d'intégration de haut niveau (business problem: compter les orphelins)
2. Tests de listing détaillé
"""

from unittest.mock import Mock

import pytest

from back_office_lmelp.services.orphaned_avis_service import OrphanedAvisService


# IDs de test factices (24 hex chars, format ObjectId valide mais non réels)
AVIS_ID = "696d46f0e738dcd14c128589"  # pragma: allowlist secret
LIVRE_OID_ORPHELIN = "6a8b17df16a04bd8be0446af"  # pragma: allowlist secret
EMISSION_OID = "694fea91e46eedc769bcd996"  # pragma: allowlist secret

PROMESSE_AVIS_ID = "6a8b18a416a04bd8be0446c8"  # pragma: allowlist secret
PROMESSE_LIVRE_OID_ORPHELIN = "6a8b180916a04bd8be0446b0"  # pragma: allowlist secret
PROMESSE_EMISSION_OID = "694fea91e46eedc769bcd99c"  # pragma: allowlist secret
PROMESSE_LIVRE_ID_SURVIVANT = "69496a1cfcfa88e53d6abe3b"  # pragma: allowlist secret

ALASKA_AVIS_ID = "6a8b18a416a04bd8be0446c4"  # pragma: allowlist secret
ALASKA_LIVRE_ID_SURVIVANT = "694918984c7793c317f9f79f"  # pragma: allowlist secret


@pytest.fixture
def mock_mongodb_service():
    """Mock du MongoDB service avec collections avis et livres"""
    mock_service = Mock()
    mock_service.avis_collection = Mock()
    mock_service.livres_collection = Mock()
    mock_service.livres_collection.find.return_value = []
    return mock_service


@pytest.fixture
def orphaned_avis_service(mock_mongodb_service):
    """Instance du service avec mock"""
    return OrphanedAvisService(mongodb_service=mock_mongodb_service)


class TestGetOrphanedStatistics:
    """
    Tests pour le comptage des avis orphelins.

    Business Problem (Issue #271):
        Un avis est orphelin si son livre_oid (String) ne correspond
        à aucun document livres._id (ObjectId) existant — typiquement
        après une fusion de doublons qui n'a pas repointé un avis.
    """

    @pytest.mark.asyncio
    async def test_get_orphaned_avis_statistics_should_count_avis_with_missing_livre(
        self, orphaned_avis_service, mock_mongodb_service
    ):
        """Test TDD RED: doit compter les avis orphelins via aggregate."""
        mock_mongodb_service.avis_collection.aggregate.return_value = iter(
            [{"count": 5}]
        )

        stats = await orphaned_avis_service.get_orphaned_statistics()

        assert stats == {"orphaned_count": 5}

    @pytest.mark.asyncio
    async def test_get_orphaned_avis_statistics_should_return_zero_when_no_orphans(
        self, orphaned_avis_service, mock_mongodb_service
    ):
        """Test TDD RED: doit retourner 0 si aucun résultat d'agrégation."""
        mock_mongodb_service.avis_collection.aggregate.return_value = iter([])

        stats = await orphaned_avis_service.get_orphaned_statistics()

        assert stats == {"orphaned_count": 0}


class TestListOrphanedAvis:
    """
    Tests pour le listing détaillé des avis orphelins (page de nettoyage).
    """

    @pytest.mark.asyncio
    async def test_list_orphaned_avis_should_return_context_fields(
        self, orphaned_avis_service, mock_mongodb_service
    ):
        """Test TDD RED: doit retourner les champs utiles à l'affichage manuel."""
        mock_mongodb_service.avis_collection.aggregate.return_value = iter(
            [
                {
                    "_id": AVIS_ID,
                    "livre_oid": LIVRE_OID_ORPHELIN,
                    "livre_titre_extrait": "L'Affaire Alaska Sanders",
                    "auteur_nom_extrait": "Joël Dicker",
                    "critique_nom_extrait": "Elisabeth Philippe",
                    "emission_oid": EMISSION_OID,
                    "commentaire": "Un thriller efficace",
                    "note": 8,
                }
            ]
        )

        orphaned = await orphaned_avis_service.list_orphaned_avis()

        assert len(orphaned) == 1
        assert orphaned[0]["id"] == AVIS_ID
        assert orphaned[0]["livre_oid"] == LIVRE_OID_ORPHELIN
        assert orphaned[0]["livre_titre_extrait"] == "L'Affaire Alaska Sanders"
        assert orphaned[0]["auteur_nom_extrait"] == "Joël Dicker"
        assert orphaned[0]["critique_nom_extrait"] == "Elisabeth Philippe"
        assert orphaned[0]["commentaire"] == "Un thriller efficace"
        assert orphaned[0]["note"] == 8

    @pytest.mark.asyncio
    async def test_list_orphaned_avis_should_return_empty_list_when_no_orphans(
        self, orphaned_avis_service, mock_mongodb_service
    ):
        """Test TDD RED: doit retourner une liste vide si aucun orphelin."""
        mock_mongodb_service.avis_collection.aggregate.return_value = iter([])

        orphaned = await orphaned_avis_service.list_orphaned_avis()

        assert orphaned == []


class TestSuggestExistingBook:
    """
    Tests pour la suggestion automatique de livre existant (Issue #271 - Partie 3bis).

    Business Problem:
        Après une fusion de doublons, le livre correspondant à un avis
        orphelin existe presque toujours encore en base sous un autre _id.
        Supprimer l'avis dans ce cas détruit une vraie donnée et désynchronise
        avis vs livres.episodes pour l'émission (incident constaté en test manuel:
        l'avis "La Promesse" a été supprimé alors que le livre existait toujours,
        créant un faux badge "Émission avec problème").

    Solution:
        list_orphaned_avis() doit détecter, pour chaque avis orphelin, si un
        livre correspondant existe (matching par titre normalisé), et exposer
        suggested_livre_id / suggested_livre_titre pour piloter l'UI (masquer
        Supprimer, proposer un repointage direct).
    """

    @pytest.mark.asyncio
    async def test_list_orphaned_avis_should_suggest_existing_book_by_matching_title(
        self, orphaned_avis_service, mock_mongodb_service
    ):
        """Test TDD RED: doit suggérer le livre existant trouvé par titre."""
        mock_mongodb_service.avis_collection.aggregate.return_value = iter(
            [
                {
                    "_id": PROMESSE_AVIS_ID,
                    "livre_oid": PROMESSE_LIVRE_OID_ORPHELIN,
                    "livre_titre_extrait": "La Promesse",
                    "auteur_nom_extrait": "Damon Galgut",
                    "critique_nom_extrait": "Olivia de Lamberterie",
                    "emission_oid": PROMESSE_EMISSION_OID,
                    "commentaire": "Très beau.",
                    "note": 9,
                }
            ]
        )
        mock_mongodb_service.livres_collection.find.return_value = [
            {"_id": PROMESSE_LIVRE_ID_SURVIVANT, "titre": "La Promesse"},
        ]

        orphaned = await orphaned_avis_service.list_orphaned_avis()

        assert orphaned[0]["suggested_livre_id"] == PROMESSE_LIVRE_ID_SURVIVANT
        assert orphaned[0]["suggested_livre_titre"] == "La Promesse"

    @pytest.mark.asyncio
    async def test_list_orphaned_avis_should_not_suggest_when_no_matching_book(
        self, orphaned_avis_service, mock_mongodb_service
    ):
        """Test TDD RED: aucun livre correspondant -> suggestion à None."""
        mock_mongodb_service.avis_collection.aggregate.return_value = iter(
            [
                {
                    "_id": ALASKA_AVIS_ID,
                    "livre_oid": LIVRE_OID_ORPHELIN,
                    "livre_titre_extrait": "Un livre totalement disparu",
                    "auteur_nom_extrait": "Auteur Inconnu",
                    "critique_nom_extrait": "Nelly Kapriélian",
                    "emission_oid": PROMESSE_EMISSION_OID,
                    "commentaire": "...",
                    "note": 4,
                }
            ]
        )
        mock_mongodb_service.livres_collection.find.return_value = [
            {"_id": PROMESSE_LIVRE_ID_SURVIVANT, "titre": "La Promesse"},
        ]

        orphaned = await orphaned_avis_service.list_orphaned_avis()

        assert orphaned[0]["suggested_livre_id"] is None
        assert orphaned[0]["suggested_livre_titre"] is None

    @pytest.mark.asyncio
    async def test_list_orphaned_avis_should_match_titles_case_and_accent_insensitively(
        self, orphaned_avis_service, mock_mongodb_service
    ):
        """Test TDD RED: le matching doit ignorer casse et accents (normalize_for_matching)."""
        mock_mongodb_service.avis_collection.aggregate.return_value = iter(
            [
                {
                    "_id": ALASKA_AVIS_ID,
                    "livre_oid": LIVRE_OID_ORPHELIN,
                    "livre_titre_extrait": "l'affaire alaska sanders",
                    "auteur_nom_extrait": "Joël Dicker",
                    "critique_nom_extrait": "Nelly Kapriélian",
                    "emission_oid": PROMESSE_EMISSION_OID,
                    "commentaire": "...",
                    "note": 4,
                }
            ]
        )
        mock_mongodb_service.livres_collection.find.return_value = [
            {"_id": ALASKA_LIVRE_ID_SURVIVANT, "titre": "L'Affaire Alaska Sanders"},
        ]

        orphaned = await orphaned_avis_service.list_orphaned_avis()

        assert orphaned[0]["suggested_livre_id"] == ALASKA_LIVRE_ID_SURVIVANT
