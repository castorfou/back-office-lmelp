"""Test TDD pour la migration des avis existants - Enrichissement éditeur (Issue #185).

PROBLÈME IDENTIFIÉ:
- Les avis créés AVANT le fix d'enrichissement éditeur n'ont pas le champ 'editeur'
- Ils contiennent seulement 'editeur_extrait' (depuis le summary)
- Résultat: Le frontend affiche des éditeurs avec fautes de frappe

EXEMPLE RÉEL (Émission 20/10/2024):
- Avis pour "Aimez Gil" de Shane Haddad
- MongoDB livre contient: "editeur": "POL" (correct)
- Avis contient: "editeur_extrait": "POL", mais PAS "editeur"
- Frontend affiche: "POL" au lieu de "P.O.L"

Ce test vérifie qu'une migration peut enrichir les avis existants.
"""

from unittest.mock import MagicMock, patch

from bson import ObjectId


class TestAvisEditeurMigration:
    """Tests pour la migration d'enrichissement éditeur des avis existants."""

    def test_should_enrich_existing_avis_with_editeur_from_mongodb(self):
        """
        Test RED: Les avis existants doivent être enrichis avec l'éditeur depuis MongoDB.

        Scénario:
        1. Un avis existe avec livre_oid mais sans champ 'editeur'
        2. La migration retrouve le livre dans MongoDB
        3. La migration ajoute le champ 'editeur' à l'avis

        CAS RÉEL: Émission 20/10/2024 - "Aimez Gil" de Shane Haddad
        """
        # Mock MongoDB service
        mock_mongodb = MagicMock()

        # Mock avis existant (SANS champ editeur)
        avis_id = ObjectId("697275b726be8082e936e5f6")  # pragma: allowlist secret
        livre_id = ObjectId("68e971607f7c718a5b6200e3")  # pragma: allowlist secret

        existing_avis = {
            "_id": avis_id,
            "emission_oid": "694fea91e46eedc769bcd9d0",  # pragma: allowlist secret
            "livre_oid": str(livre_id),
            "critique_oid": "694eb72b3696842476c793cd",  # pragma: allowlist secret
            "livre_titre_extrait": "Aimer Gilles",
            "auteur_nom_extrait": "Shane Haddad",
            "editeur_extrait": "POL",  # Depuis summary
            # ❌ PAS de champ "editeur" (créé avant le fix)
            "commentaire": "Magnifiquement rendu, très beau",
            "note": 9.0,
            "section": "programme",
            "match_phase": 3,
        }

        # Mock livre MongoDB avec éditeur correct
        livre_mongodb = {
            "_id": livre_id,
            "titre": "Aimez Gil",
            "auteur_id": ObjectId(
                "68e971607f7c718a5b6200e2"  # pragma: allowlist secret
            ),  # noqa: E501
            "editeur": "P.O.L",  # ✅ Éditeur correct (avec points)
            "url_babelio": "https://www.babelio.com/livres/Haddad-Aimez-Gil/1639991",
        }

        # Mock collections
        mock_avis_collection = MagicMock()
        mock_livres_collection = MagicMock()

        # Setup: find retourne l'avis sans editeur
        mock_avis_collection.find.return_value = [existing_avis]

        # Setup: find_one retourne le livre MongoDB
        mock_livres_collection.find_one.return_value = livre_mongodb

        # Setup: update_one retourne un résultat avec modified_count=1
        mock_update_result = MagicMock()
        mock_update_result.modified_count = 1
        mock_avis_collection.update_one.return_value = mock_update_result

        def get_collection_side_effect(name):
            if name == "avis":
                return mock_avis_collection
            elif name == "livres":
                return mock_livres_collection
            return MagicMock()

        mock_mongodb.get_collection.side_effect = get_collection_side_effect

        # EXECUTE: Appliquer la migration
        from back_office_lmelp.utils.migrate_enrich_avis_editeur import (
            migrate_enrich_avis_with_editeur,
        )

        with patch(
            "back_office_lmelp.utils.migrate_enrich_avis_editeur.MongoDBService",
            return_value=mock_mongodb,
        ):
            updated_count = migrate_enrich_avis_with_editeur()

        # ASSERT: 1 avis doit avoir été mis à jour
        assert updated_count == 1, f"Attendu 1 avis mis à jour, obtenu {updated_count}"

        # ASSERT: update_one a été appelé avec le bon editeur
        mock_avis_collection.update_one.assert_called_once()
        call_args = mock_avis_collection.update_one.call_args

        # Vérifier le filtre (avis_id)
        filter_arg = call_args[0][0]
        assert filter_arg == {"_id": avis_id}

        # Vérifier le update ($set avec editeur)
        update_arg = call_args[0][1]
        assert "$set" in update_arg
        assert "editeur" in update_arg["$set"]
        assert update_arg["$set"]["editeur"] == "P.O.L"

    def test_should_skip_avis_without_livre_oid(self):
        """
        Test: Les avis sans livre_oid ne doivent PAS être mis à jour.

        Si livre_oid=None, il n'y a pas de livre MongoDB associé,
        donc impossible d'enrichir avec l'éditeur.
        """
        # Mock MongoDB service
        mock_mongodb = MagicMock()

        # Mock avis sans livre_oid
        avis_id = ObjectId("697275b726be8082e936e5ff")  # pragma: allowlist secret
        existing_avis = {
            "_id": avis_id,
            "emission_oid": "694fea91e46eedc769bcd9d0",  # pragma: allowlist secret
            "livre_oid": None,  # ❌ Pas de match
            "editeur_extrait": "Éditeur Inconnu",
            "commentaire": "Commentaire",
            "note": 7.0,
            "section": "programme",
        }

        # Mock collections
        mock_avis_collection = MagicMock()
        mock_livres_collection = MagicMock()

        # Setup: find retourne l'avis sans livre_oid
        mock_avis_collection.find.return_value = [existing_avis]

        def get_collection_side_effect(name):
            if name == "avis":
                return mock_avis_collection
            elif name == "livres":
                return mock_livres_collection
            return MagicMock()

        mock_mongodb.get_collection.side_effect = get_collection_side_effect

        # EXECUTE: Appliquer la migration
        from back_office_lmelp.utils.migrate_enrich_avis_editeur import (
            migrate_enrich_avis_with_editeur,
        )

        with patch(
            "back_office_lmelp.utils.migrate_enrich_avis_editeur.MongoDBService",
            return_value=mock_mongodb,
        ):
            updated_count = migrate_enrich_avis_with_editeur()

        # ASSERT: 0 avis mis à jour (skip)
        assert updated_count == 0, f"Attendu 0 avis mis à jour, obtenu {updated_count}"

        # ASSERT: update_one ne doit PAS être appelé
        mock_avis_collection.update_one.assert_not_called()

    def test_should_skip_avis_already_with_editeur(self):
        """
        Test: Les avis avec le champ 'editeur' déjà présent ne doivent PAS être mis à jour.

        Idempotence de la migration: ne pas re-enrichir les avis déjà corrects.
        """
        # Mock MongoDB service
        mock_mongodb = MagicMock()

        # Mock avis AVEC editeur déjà présent (non utilisé car la requête filtre déjà)
        # Note: La requête MongoDB avec {"editeur": {"$exists": False}} ne retourne
        # PAS les avis avec editeur déjà présent, donc ce test vérifie que la
        # migration ne fait rien quand la requête retourne une liste vide.

        # Mock collections
        mock_avis_collection = MagicMock()
        mock_livres_collection = MagicMock()

        # Setup: find retourne une liste VIDE (la requête filtre editeur: {$exists: false})
        # Un avis avec editeur déjà présent ne doit PAS être retourné par la requête
        mock_avis_collection.find.return_value = []

        def get_collection_side_effect(name):
            if name == "avis":
                return mock_avis_collection
            elif name == "livres":
                return mock_livres_collection
            return MagicMock()

        mock_mongodb.get_collection.side_effect = get_collection_side_effect

        # EXECUTE: Appliquer la migration
        from back_office_lmelp.utils.migrate_enrich_avis_editeur import (
            migrate_enrich_avis_with_editeur,
        )

        with patch(
            "back_office_lmelp.utils.migrate_enrich_avis_editeur.MongoDBService",
            return_value=mock_mongodb,
        ):
            updated_count = migrate_enrich_avis_with_editeur()

        # ASSERT: 0 avis mis à jour (skip car déjà enrichi)
        assert updated_count == 0, f"Attendu 0 avis mis à jour, obtenu {updated_count}"

        # ASSERT: update_one ne doit PAS être appelé
        mock_avis_collection.update_one.assert_not_called()
