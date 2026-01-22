"""Test TDD pour l'enrichissement de l'éditeur depuis MongoDB (Issue #185).

PROBLÈME IDENTIFIÉ:
- Les avis résolus contiennent `editeur_extrait` (depuis le summary)
- Mais pas l'éditeur MongoDB officiel (qui est dans la collection livres)
- Résultat: Les avis affichent des éditeurs avec fautes de frappe (ex: "Gallmeister" au lieu de "Galmeister")

Ce test vérifie que les avis résolus sont enrichis avec l'éditeur depuis MongoDB.
"""

from unittest.mock import MagicMock

from bson import ObjectId


class TestAvisEditeurEnrichment:
    """Tests pour l'enrichissement de l'éditeur depuis MongoDB."""

    def setup_method(self):
        """Setup pour chaque test."""
        from back_office_lmelp.services.avis_extraction_service import (
            AvisExtractionService,
        )

        self.extraction_service = AvisExtractionService()

        # Mock mongodb_service
        self.mock_mongodb = MagicMock()
        self.extraction_service.mongodb_service = self.mock_mongodb

    def test_should_enrich_avis_with_editeur_from_mongodb(self):
        """
        Test RED: Les avis résolus doivent contenir l'éditeur depuis MongoDB.

        CAS RÉEL:
        - Summary contient: "editeur_extrait": "Gallmeister" (faute de frappe)
        - MongoDB contient: "editeur": "Galmeister" (correct)
        - Les avis résolus doivent avoir les DEUX champs:
          * editeur_extrait: "Gallmeister" (original du summary, pour traçabilité)
          * editeur: "Galmeister" (depuis MongoDB, pour affichage)
        """
        # Avis brut extrait (avec faute dans l'éditeur)
        avis_brut = {
            "livre_titre_extrait": "La Loi des collines",
            "auteur_nom_extrait": "Chris Offutt",
            "editeur_extrait": "Gallmeister",  # ❌ Faute de frappe
            "critique_nom_extrait": "Bernard Poirette",
            "commentaire": "Rural noir américain de haute volée",
            "note": 9.0,
            "section": "coup_de_coeur",
        }

        # Mock livre dans MongoDB avec éditeur correct
        livre_id = ObjectId("68e919a2066cb40c25d5d2e1")
        auteur_id = ObjectId("68e919a2066cb40c25d5d2e0")
        livres = [
            {
                "_id": livre_id,
                "titre": "La Loi des collines",
                "auteur_nom": "Chris Offutt",
                "auteur_id": auteur_id,
                "editeur": "Galmeister",  # ✅ Éditeur correct
            }
        ]

        # Mock critique
        critique_id = ObjectId("694f17665eac26c9eb2852ff")
        critiques = [
            {
                "_id": critique_id,
                "nom": "Bernard Poirette",
                "variantes": ["Bernard Poiret"],
            }
        ]

        # EXECUTE: Résoudre les entités
        resolved_avis = self.extraction_service.resolve_entities(
            [avis_brut], livres, critiques
        )

        # ASSERT: Le livre DOIT être matché
        assert len(resolved_avis) == 1, (
            f"Attendu 1 avis résolu, obtenu {len(resolved_avis)}"
        )
        resolved = resolved_avis[0]

        assert resolved["livre_oid"] == str(livre_id), (
            f"Livre non matché! livre_oid={resolved.get('livre_oid')}"
        )

        # ASSERT CRITIQUE: L'éditeur MongoDB doit être présent
        assert "editeur" in resolved, (
            "Le champ 'editeur' (depuis MongoDB) est manquant dans l'avis résolu"
        )
        assert resolved["editeur"] == "Galmeister", (
            f"Éditeur MongoDB incorrect: attendu 'Galmeister', "
            f"obtenu '{resolved.get('editeur')}'"
        )

        # ASSERT: L'éditeur extrait doit aussi être présent (traçabilité)
        assert "editeur_extrait" in resolved, (
            "Le champ 'editeur_extrait' (depuis summary) est manquant"
        )
        assert resolved["editeur_extrait"] == "Gallmeister", (
            f"Éditeur extrait incorrect: attendu 'Gallmeister', "
            f"obtenu '{resolved.get('editeur_extrait')}'"
        )

        # ASSERT: L'auteur_oid doit aussi être enrichi (vérification de cohérence)
        assert "auteur_oid" in resolved, (
            "Le champ 'auteur_oid' (depuis MongoDB) est manquant"
        )
        assert resolved["auteur_oid"] == str(auteur_id), (
            f"Auteur OID incorrect: attendu '{auteur_id}', "
            f"obtenu '{resolved.get('auteur_oid')}'"
        )

    def test_should_preserve_editeur_extrait_when_no_match(self):
        """
        Test RED: Si le livre n'est pas matché, garder editeur_extrait seulement.

        Quand livre_oid=None, il n'y a pas de livre MongoDB associé,
        donc pas d'éditeur MongoDB. On garde seulement editeur_extrait.
        """
        # Avis brut qui ne matchera aucun livre
        avis_brut = {
            "livre_titre_extrait": "Livre Inconnu",
            "auteur_nom_extrait": "Auteur Inconnu",
            "editeur_extrait": "Éditeur Inconnu",
            "critique_nom_extrait": "Bernard Poirette",
            "commentaire": "Commentaire",
            "note": 7.0,
            "section": "programme",
        }

        # Mock critique
        critique_id = ObjectId("694f17665eac26c9eb2852ff")
        critiques = [
            {
                "_id": critique_id,
                "nom": "Bernard Poirette",
                "variantes": ["Bernard Poiret"],
            }
        ]

        # Aucun livre dans MongoDB
        livres = []

        # EXECUTE: Résoudre les entités
        resolved_avis = self.extraction_service.resolve_entities(
            [avis_brut], livres, critiques
        )

        # ASSERT
        assert len(resolved_avis) == 1
        resolved = resolved_avis[0]

        # Le livre n'est pas matché
        assert resolved["livre_oid"] is None, (
            f"Le livre ne devrait pas être matché, mais livre_oid={resolved.get('livre_oid')}"
        )

        # L'éditeur extrait doit être présent
        assert "editeur_extrait" in resolved
        assert resolved["editeur_extrait"] == "Éditeur Inconnu"

        # L'éditeur MongoDB ne doit PAS être présent (pas de match)
        assert "editeur" not in resolved or resolved.get("editeur") is None, (
            f"Le champ 'editeur' ne devrait pas être présent quand livre_oid=None, "
            f"obtenu '{resolved.get('editeur')}'"
        )
