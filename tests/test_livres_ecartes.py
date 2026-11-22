"""Registre des titres écartés d'un résumé (Issue #380).

`avis_critiques.livres_ecartes` liste les titres du résumé qui ne désignent pas
un livre. Les deux extractions (avis, livres du cache) n'en produisent rien.
"""

from datetime import datetime
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient


if TYPE_CHECKING:
    from back_office_lmelp.services.mongodb_service import MongoDBService


# Format réel d'un résumé (tableaux Section 1 et Section 2), avec une ligne de
# coup de cœur qui désigne une collection entière et non un livre.
SUMMARY_AVEC_COLLECTION = """## 1. LIVRES DISCUTÉS AU PROGRAMME du 24 avril 2016

| Auteur | Titre | Éditeur | Avis détaillés des critiques | Note moyenne | Nb critiques | Coup de cœur | Chef d'œuvre |
|--------|-------|---------|------------------------------|--------------|-------------|-------------|-------------|
| Neige Sinno | La Realidad | P.O.L | **Elisabeth Philippe**: Exceptionnel, réflexion profonde sur la littérature. Note: 10 <br>**Arnaud Viviant**: Magnifique, écriture absodique. Note: 9 | <span style="background-color: #8BC34A; color: white; padding: 2px 6px; border-radius: 3px; font-weight: bold;">9.5</span> | 2 | Elisabeth Philippe | |

## 2. COUPS DE CŒUR DES CRITIQUES du 24 avril 2016

| Auteur | Titre | Éditeur | Critique | Note | Commentaire |
|--------|-------|---------|----------|------|-------------|
| Saskia Vogel | Permission | Éditions de La Croisée | Elisabeth Philippe | <span style="background-color: #00C851; color: white; padding: 2px 6px; border-radius: 3px; font-weight: bold;">9.0</span> | Profond, doux, poétique |
| Collectif | Divers titres à l'École des loisirs | L'École des loisirs | Arnaud Viviant | <span style="background-color: #00C851; color: white; padding: 2px 6px; border-radius: 3px; font-weight: bold;">9.0</span> | Toute la collection jeunesse |"""

TITRE_ECARTE = "Divers titres à l'École des loisirs"


def _livres_ecartes(titre: str = TITRE_ECARTE) -> list[dict]:
    return [
        {"titre": titre, "auteur": "Collectif", "ecarte_le": datetime(2026, 11, 22)}
    ]


class TestExtractAvisIgnoresEcartes:
    """POST /api/avis/extract/{emission_id} ne crée aucun avis pour un titre écarté."""

    def setup_method(self):
        self.mock_mongodb = MagicMock()
        self.patcher = patch("back_office_lmelp.app.mongodb_service", self.mock_mongodb)
        self.patcher.start()
        from back_office_lmelp.app import app

        self.client = TestClient(app)

    def teardown_method(self):
        self.patcher.stop()

    def _setup_emission(self, livres_ecartes: list[dict] | None) -> ObjectId:
        emission_id = ObjectId()
        avis_critique: dict = {"_id": ObjectId(), "summary": SUMMARY_AVEC_COLLECTION}
        if livres_ecartes is not None:
            avis_critique["livres_ecartes"] = livres_ecartes
        self.mock_mongodb.emissions_collection.find_one.return_value = {
            "_id": emission_id,
            "episode_id": ObjectId(),
            "avis_critique_id": avis_critique["_id"],
        }
        self.mock_mongodb.avis_critiques_collection.find_one.return_value = (
            avis_critique
        )
        self.mock_mongodb.get_collection.return_value.find.return_value = []
        self.mock_mongodb.critiques_collection.find.return_value = []
        self.mock_mongodb.delete_avis_by_emission.return_value = 3
        self.mock_mongodb.save_avis_batch.side_effect = lambda docs: [
            str(ObjectId()) for _ in docs
        ]
        return emission_id

    def _saved_titles(self) -> set[str]:
        saved = self.mock_mongodb.save_avis_batch.call_args[0][0]
        return {doc["livre_titre_extrait"] for doc in saved}

    def test_titre_ecarte_ne_produit_aucun_avis(self):
        emission_id = self._setup_emission(_livres_ecartes())

        response = self.client.post(f"/api/avis/extract/{emission_id}")

        assert response.status_code == 200
        assert self._saved_titles() == {"La Realidad", "Permission"}

    def test_sans_registre_le_titre_produit_un_avis(self):
        emission_id = self._setup_emission(None)

        response = self.client.post(f"/api/avis/extract/{emission_id}")

        assert response.status_code == 200
        assert TITRE_ECARTE in self._saved_titles()

    def test_comparaison_insensible_casse_accents_apostrophe(self):
        emission_id = self._setup_emission(
            _livres_ecartes("divers titres a l’ecole des loisirs")
        )

        response = self.client.post(f"/api/avis/extract/{emission_id}")

        assert response.status_code == 200
        assert TITRE_ECARTE not in self._saved_titles()


class TestIsTitreEcarte:
    """Comparaison d'un titre au registre, via normalize_for_matching."""

    def test_titre_present(self):
        from back_office_lmelp.utils.livres_ecartes import is_titre_ecarte

        assert is_titre_ecarte(TITRE_ECARTE, _livres_ecartes()) is True

    def test_variante_typographique(self):
        from back_office_lmelp.utils.livres_ecartes import is_titre_ecarte

        assert is_titre_ecarte("DIVERS TITRES À L’ÉCOLE DES LOISIRS", _livres_ecartes())

    def test_titre_proche_non_ecarte(self):
        """Pas de matching approximatif : un vrai livre ne doit pas être écarté."""
        from back_office_lmelp.utils.livres_ecartes import is_titre_ecarte

        assert is_titre_ecarte("Divers titres", _livres_ecartes()) is False

    def test_registre_absent(self):
        from back_office_lmelp.utils.livres_ecartes import is_titre_ecarte

        assert is_titre_ecarte(TITRE_ECARTE, None) is False
        assert is_titre_ecarte(TITRE_ECARTE, []) is False


class TestExtractAvisAllEcartes:
    """Si tous les titres sont écartés, les anciens avis sont quand même supprimés."""

    def setup_method(self):
        self.mock_mongodb = MagicMock()
        self.patcher = patch("back_office_lmelp.app.mongodb_service", self.mock_mongodb)
        self.patcher.start()
        from back_office_lmelp.app import app

        self.client = TestClient(app)

    def teardown_method(self):
        self.patcher.stop()

    def test_anciens_avis_supprimes(self):
        emission_id = ObjectId()
        avis_critique_id = ObjectId()
        self.mock_mongodb.emissions_collection.find_one.return_value = {
            "_id": emission_id,
            "episode_id": ObjectId(),
            "avis_critique_id": avis_critique_id,
        }
        self.mock_mongodb.avis_critiques_collection.find_one.return_value = {
            "_id": avis_critique_id,
            "summary": SUMMARY_AVEC_COLLECTION,
            "livres_ecartes": [
                {"titre": t, "auteur": "", "ecarte_le": datetime(2026, 11, 22)}
                for t in ("La Realidad", "Permission", TITRE_ECARTE)
            ],
        }
        self.mock_mongodb.delete_avis_by_emission.return_value = 4

        response = self.client.post(f"/api/avis/extract/{emission_id}")

        assert response.status_code == 200
        assert response.json()["extracted_count"] == 0
        assert response.json()["deleted_count"] == 4
        self.mock_mongodb.delete_avis_by_emission.assert_called_once_with(
            str(emission_id)
        )


class TestExtractBooksIgnoresEcartes:
    """Les livres du cache (extraction depuis le résumé) excluent les titres écartés."""

    def _avis_critique(self, livres_ecartes: list[dict] | None) -> dict:
        doc: dict = {
            "_id": ObjectId(),
            "episode_oid": "678ccfe5a414f22988778307",  # pragma: allowlist secret
            "episode_title": "Le masque et la plume livres",
            "episode_date": "2016-04-24",
            "summary": SUMMARY_AVEC_COLLECTION,
        }
        if livres_ecartes is not None:
            doc["livres_ecartes"] = livres_ecartes
        return doc

    async def _extract_titles(self, avis_critique: dict) -> set[str]:
        from back_office_lmelp.services.books_extraction_service import (
            BooksExtractionService,
        )

        service = BooksExtractionService()
        service.client = None  # parsing des tableaux, sans LLM
        books = await service.extract_books_from_reviews([avis_critique])
        return {book["titre"] for book in books}

    @pytest.mark.asyncio
    async def test_titre_ecarte_absent(self):
        titles = await self._extract_titles(self._avis_critique(_livres_ecartes()))

        assert titles == {"La Realidad", "Permission"}

    @pytest.mark.asyncio
    async def test_sans_registre_titre_present(self):
        titles = await self._extract_titles(self._avis_critique(None))

        assert TITRE_ECARTE in titles


class TestMongoDBServiceRegistre:
    """add_livre_ecarte / remove_livre_ecarte sur avis_critiques."""

    def _service(self, doc: dict | None) -> "MongoDBService":
        from back_office_lmelp.services.mongodb_service import MongoDBService

        service = MongoDBService()
        service.avis_critiques_collection = MagicMock()
        service.avis_critiques_collection.find_one.return_value = doc
        return service

    def test_add_enregistre_titre_auteur_date(self):
        avis_critique_id = ObjectId()
        service = self._service({"_id": avis_critique_id})

        result = service.add_livre_ecarte(avis_critique_id, TITRE_ECARTE, "Collectif")

        assert result is not None
        assert [(e["titre"], e["auteur"]) for e in result] == [
            (TITRE_ECARTE, "Collectif")
        ]
        assert isinstance(result[0]["ecarte_le"], datetime)
        service.avis_critiques_collection.update_one.assert_called_once_with(
            {"_id": avis_critique_id}, {"$set": {"livres_ecartes": result}}
        )

    def test_add_idempotent_sur_titre_normalise(self):
        avis_critique_id = ObjectId()
        service = self._service(
            {"_id": avis_critique_id, "livres_ecartes": _livres_ecartes()}
        )

        result = service.add_livre_ecarte(
            avis_critique_id, "divers titres a l'ecole des loisirs", "Collectif"
        )

        assert result == _livres_ecartes()
        service.avis_critiques_collection.update_one.assert_not_called()

    def test_add_accepte_un_id_str(self):
        avis_critique_id = ObjectId()
        service = self._service({"_id": avis_critique_id})

        service.add_livre_ecarte(str(avis_critique_id), TITRE_ECARTE, "")

        service.avis_critiques_collection.find_one.assert_called_once_with(
            {"_id": avis_critique_id}
        )

    def test_add_avis_critique_absent(self):
        service = self._service(None)

        assert service.add_livre_ecarte(ObjectId(), TITRE_ECARTE, "") is None

    def test_remove_retire_titre_normalise(self):
        avis_critique_id = ObjectId()
        autre = {"titre": "Autre", "auteur": "", "ecarte_le": datetime(2026, 1, 1)}
        service = self._service(
            {"_id": avis_critique_id, "livres_ecartes": [*_livres_ecartes(), autre]}
        )

        result = service.remove_livre_ecarte(
            avis_critique_id, "DIVERS TITRES À L'ÉCOLE DES LOISIRS"
        )

        assert result == [autre]
        service.avis_critiques_collection.update_one.assert_called_once_with(
            {"_id": avis_critique_id}, {"$set": {"livres_ecartes": [autre]}}
        )

    def test_remove_avis_critique_absent(self):
        service = self._service(None)

        assert service.remove_livre_ecarte(ObjectId(), TITRE_ECARTE) is None


class TestDeleteCacheEntryRegistersEcarte:
    """« Supprimer » (validation Babelio) écarte durablement le titre."""

    def setup_method(self):
        self.mock_mongodb = MagicMock()
        self.mock_cache = MagicMock()
        self.patchers = [
            patch("back_office_lmelp.app.mongodb_service", self.mock_mongodb),
            patch(
                "back_office_lmelp.app.livres_auteurs_cache_service", self.mock_cache
            ),
        ]
        for p in self.patchers:
            p.start()
        from back_office_lmelp.app import app

        self.client = TestClient(app)

    def teardown_method(self):
        for p in self.patchers:
            p.stop()

    def test_supprimer_ajoute_le_titre_du_resume_au_registre(self):
        cache_id = ObjectId()
        avis_critique_id = ObjectId()
        # Structure réelle d'une entrée livresauteurs_cache (create_cache_entry)
        self.mock_cache.delete_cache_entry.return_value = {
            "_id": cache_id,
            "avis_critique_id": avis_critique_id,
            "episode_oid": "678ccfe5a414f22988778307",  # pragma: allowlist secret
            "auteur": "Collectif",
            "titre": TITRE_ECARTE,
            "suggested_title": "Divers titres",
            "editeur": "L'École des loisirs",
            "programme": False,
            "status": "not_found",
            "created_at": datetime(2026, 11, 1),
            "updated_at": datetime(2026, 11, 1),
        }

        response = self.client.delete(f"/api/livres-auteurs/cache/{cache_id}")

        assert response.status_code == 200
        assert response.json()["deleted"] is True
        self.mock_mongodb.add_livre_ecarte.assert_called_once_with(
            avis_critique_id, TITRE_ECARTE, "Collectif"
        )

    def test_entree_absente_404_sans_registre(self):
        self.mock_cache.delete_cache_entry.return_value = None

        response = self.client.delete(f"/api/livres-auteurs/cache/{ObjectId()}")

        assert response.status_code == 404
        self.mock_mongodb.add_livre_ecarte.assert_not_called()


class TestEmissionLivresEcartesEndpoints:
    """POST/DELETE /api/emissions/{emission_id}/livres-ecartes (page Émissions)."""

    def setup_method(self):
        self.mock_mongodb = MagicMock()
        self.mock_cache = MagicMock()
        self.patchers = [
            patch("back_office_lmelp.app.mongodb_service", self.mock_mongodb),
            patch(
                "back_office_lmelp.app.livres_auteurs_cache_service", self.mock_cache
            ),
        ]
        for p in self.patchers:
            p.start()
        from back_office_lmelp.app import app

        self.client = TestClient(app)
        self.emission_id = ObjectId()
        self.episode_id = ObjectId()
        self.avis_critique_id = ObjectId()
        self.mock_mongodb.emissions_collection.find_one.return_value = {
            "_id": self.emission_id,
            "episode_id": self.episode_id,
            "avis_critique_id": str(self.avis_critique_id),
        }

    def teardown_method(self):
        for p in self.patchers:
            p.stop()

    def _url(self) -> str:
        return f"/api/emissions/{self.emission_id}/livres-ecartes"

    def test_ignorer_enregistre_et_retire_le_cache_non_valide(self):
        self.mock_mongodb.add_livre_ecarte.return_value = _livres_ecartes()

        response = self.client.post(
            self._url(), json={"titre": TITRE_ECARTE, "auteur": "Collectif"}
        )

        assert response.status_code == 200
        assert response.json() == {
            "livres_ecartes": [
                {
                    "titre": TITRE_ECARTE,
                    "auteur": "Collectif",
                    "ecarte_le": "2026-11-22T00:00:00",
                }
            ]
        }
        self.mock_mongodb.add_livre_ecarte.assert_called_once_with(
            str(self.avis_critique_id), TITRE_ECARTE, "Collectif"
        )
        self.mock_cache.delete_unvalidated_entries_by_title.assert_called_once_with(
            str(self.episode_id), TITRE_ECARTE
        )

    def test_ignorer_titre_vide_422(self):
        response = self.client.post(self._url(), json={"titre": "  ", "auteur": ""})

        assert response.status_code == 422
        self.mock_mongodb.add_livre_ecarte.assert_not_called()

    def test_ignorer_emission_absente_404(self):
        self.mock_mongodb.emissions_collection.find_one.return_value = None

        response = self.client.post(self._url(), json={"titre": TITRE_ECARTE})

        assert response.status_code == 404

    def test_ignorer_emission_sans_avis_critique_404(self):
        self.mock_mongodb.emissions_collection.find_one.return_value = {
            "_id": self.emission_id,
            "episode_id": self.episode_id,
        }

        response = self.client.post(self._url(), json={"titre": TITRE_ECARTE})

        assert response.status_code == 404

    def test_retablir_retire_du_registre(self):
        self.mock_mongodb.remove_livre_ecarte.return_value = []

        response = self.client.delete(self._url(), params={"titre": TITRE_ECARTE})

        assert response.status_code == 200
        assert response.json() == {"livres_ecartes": []}
        self.mock_mongodb.remove_livre_ecarte.assert_called_once_with(
            str(self.avis_critique_id), TITRE_ECARTE
        )

    def test_retablir_avis_critique_absent_404(self):
        self.mock_mongodb.remove_livre_ecarte.return_value = None

        response = self.client.delete(self._url(), params={"titre": TITRE_ECARTE})

        assert response.status_code == 404


class TestGetAvisByEmissionExposesEcartes:
    """GET /api/avis/by-emission/{id} renvoie le registre pour la page Émissions."""

    def setup_method(self):
        self.mock_mongodb = MagicMock()
        self.patcher = patch("back_office_lmelp.app.mongodb_service", self.mock_mongodb)
        self.patcher.start()
        from back_office_lmelp.app import app

        self.client = TestClient(app)

    def teardown_method(self):
        self.patcher.stop()

    def _get(self, summary: str, livres_ecartes: list[dict]) -> list[dict]:
        emission_id = ObjectId()
        avis_critique_id = ObjectId()
        self.mock_mongodb.get_avis_by_emission.return_value = []
        self.mock_mongodb.critiques_collection.find.return_value = []
        self.mock_mongodb.emissions_collection.find_one.return_value = {
            "_id": emission_id,
            "episode_id": ObjectId(),
            "avis_critique_id": str(avis_critique_id),
        }
        self.mock_mongodb.livres_collection.count_documents.return_value = 0
        self.mock_mongodb.livres_collection.find.return_value = []
        self.mock_mongodb.avis_critiques_collection.find_one.return_value = {
            "_id": avis_critique_id,
            "summary": summary,
            "livres_ecartes": livres_ecartes,
        }

        response = self.client.get(f"/api/avis/by-emission/{emission_id}")

        assert response.status_code == 200
        result: list[dict] = response.json()["livres_ecartes"]
        return result

    def test_livres_ecartes_dans_la_reponse(self):
        assert self._get(SUMMARY_AVEC_COLLECTION, _livres_ecartes()) == [
            {
                "titre": TITRE_ECARTE,
                "auteur": "Collectif",
                "ecarte_le": "2026-11-22T00:00:00",
                "absent_du_resume": False,
            }
        ]

    def test_titre_absent_du_resume_actuel(self):
        """Résumé régénéré : le titre écarté n'y figure plus (cas du 24/04/2016)."""
        summary = SUMMARY_AVEC_COLLECTION.replace(
            TITRE_ECARTE, "Tous les livres publiés à L'école des loisirs (jeunesse)"
        )

        result = self._get(summary, _livres_ecartes())

        assert result[0]["absent_du_resume"] is True

    def test_titre_present_sans_avis_lisible(self):
        """Une ligne du tableau sans avis exploitable compte comme présente."""
        summary = SUMMARY_AVEC_COLLECTION.replace(
            "| Neige Sinno | La Realidad | P.O.L | **Elisabeth Philippe**: "
            "Exceptionnel, réflexion profonde sur la littérature. Note: 10 <br>"
            "**Arnaud Viviant**: Magnifique, écriture absodique. Note: 9 |",
            "| Neige Sinno | La Realidad | P.O.L | Discussion générale |",
        )
        assert "Discussion générale" in summary

        result = self._get(summary, _livres_ecartes("La Realidad"))

        assert result[0]["absent_du_resume"] is False


class TestDeleteUnvalidatedEntriesByTitle:
    """Le cache perd les entrées non validées d'un titre écarté depuis Émissions."""

    def test_supprime_seulement_les_entrees_du_titre(self):
        from back_office_lmelp.services.livres_auteurs_cache_service import (
            LivresAuteursCacheService,
        )

        episode_oid = "678ccfe5a414f22988778307"  # pragma: allowlist secret
        entree_ecartee = {"_id": ObjectId(), "titre": TITRE_ECARTE}
        autre = {"_id": ObjectId(), "titre": "Permission"}
        with patch(
            "back_office_lmelp.services.livres_auteurs_cache_service.mongodb_service"
        ) as mock_mongodb:
            collection = mock_mongodb.get_collection.return_value
            collection.find.return_value = [entree_ecartee, autre]
            collection.delete_many.return_value.deleted_count = 1

            deleted = LivresAuteursCacheService().delete_unvalidated_entries_by_title(
                episode_oid, "divers titres a l'ecole des loisirs"
            )

        assert deleted == 1
        collection.find.assert_called_once_with(
            {"episode_oid": episode_oid, "status": {"$ne": "mongo"}}
        )
        collection.delete_many.assert_called_once_with(
            {"_id": {"$in": [entree_ecartee["_id"]]}}
        )


class TestEcarterLivreDepuisValidationBabelio:
    """POST /api/livres-auteurs/ecarter : « Supprimer » d'un livre pas encore en cache.

    Un livre tout juste extrait du résumé (cache vide ou rafraîchi) n'a pas de
    cache_id : on l'écarte par épisode et par titre.
    """

    def setup_method(self):
        self.mock_mongodb = MagicMock()
        self.mock_cache = MagicMock()
        self.patchers = [
            patch("back_office_lmelp.app.mongodb_service", self.mock_mongodb),
            patch(
                "back_office_lmelp.app.livres_auteurs_cache_service", self.mock_cache
            ),
        ]
        for p in self.patchers:
            p.start()
        from back_office_lmelp.app import app

        self.client = TestClient(app)
        self.episode_oid = "6b0311fde1982eca85db03ab"  # pragma: allowlist secret
        self.avis_critique_id = ObjectId()

    def teardown_method(self):
        for p in self.patchers:
            p.stop()

    def test_ecarte_le_titre_et_retire_le_cache_non_valide(self):
        self.mock_mongodb.get_critical_reviews_by_episode_oid.return_value = [
            {
                "_id": self.avis_critique_id,
                "episode_oid": self.episode_oid,
                "summary": SUMMARY_AVEC_COLLECTION,
            }
        ]
        self.mock_mongodb.add_livre_ecarte.return_value = _livres_ecartes()

        response = self.client.post(
            "/api/livres-auteurs/ecarter",
            json={
                "episode_oid": self.episode_oid,
                "titre": TITRE_ECARTE,
                "auteur": "Collectif",
            },
        )

        assert response.status_code == 200
        assert response.json()["livres_ecartes"][0]["titre"] == TITRE_ECARTE
        self.mock_mongodb.add_livre_ecarte.assert_called_once_with(
            self.avis_critique_id, TITRE_ECARTE, "Collectif"
        )
        self.mock_cache.delete_unvalidated_entries_by_title.assert_called_once_with(
            self.episode_oid, TITRE_ECARTE
        )

    def test_episode_sans_avis_critique_404(self):
        self.mock_mongodb.get_critical_reviews_by_episode_oid.return_value = []

        response = self.client.post(
            "/api/livres-auteurs/ecarter",
            json={"episode_oid": self.episode_oid, "titre": TITRE_ECARTE},
        )

        assert response.status_code == 404
        self.mock_mongodb.add_livre_ecarte.assert_not_called()

    def test_titre_vide_422(self):
        response = self.client.post(
            "/api/livres-auteurs/ecarter",
            json={"episode_oid": self.episode_oid, "titre": " "},
        )

        assert response.status_code == 422
