"""Test TDD pour détecter les faux matches de titres similaires (Issue #185).

PROBLÈME RÉEL: Émission du 09/03/2025
- "Trésors Cachés" (pluriel) est MAL matché à "La chaise" au lieu de "Trésor caché"
- Résultat: "La Chaises" ne peut plus être matché car "La chaise" est déjà pris

CAUSE: Phase 3 (accent-insensitive) match trop large sans validation de cohérence.
- "Trésors Cachés" matche "La chaise" par regex insensible aux accents/majuscules
- Aucune validation que l'auteur ou l'éditeur correspondent

Ce test vérifie qu'un mauvais match ne doit pas se produire.
"""

from unittest.mock import MagicMock

from bson import ObjectId


class TestAvisExtractionWrongMatchPlural:
    """Tests pour éviter les faux matches entre titres similaires."""

    def setup_method(self):
        """Setup pour chaque test."""
        from back_office_lmelp.services.avis_extraction_service import (
            AvisExtractionService,
        )

        self.extraction_service = AvisExtractionService()

        # Mock mongodb_service
        self.mock_mongodb = MagicMock()
        self.extraction_service.mongodb_service = self.mock_mongodb

    def test_should_not_match_tresors_caches_to_la_chaise(self):
        """
        Test RED: "Trésors Cachés" NE DOIT PAS matcher "La chaise".

        CAS RÉEL: Émission 09/03/2025
        - "Trésors Cachés" de Pascal Quignard doit matcher "Trésor caché"
        - NE DOIT PAS matcher "La chaise" de Jean-Louis Ezine

        PROBLÈME: Actuellement Phase 3 fait un faux match car:
        - Regex insensible aux accents/maj trop permissive
        - Aucune validation auteur/éditeur
        """
        _episode_id = str(ObjectId("67cf4660e1eab9ef0cddff91"))

        # Avis brut "Trésors Cachés" (pluriel avec maj)
        avis_brut = {
            "livre_titre_extrait": "Trésors Cachés",
            "auteur_nom_extrait": "Pascal Quignard",
            "editeur_extrait": "Albin Michel",
            "critique_nom_extrait": "Arnaud Viviant",
            "commentaire": "Absolument magnifique, prose poétique",
            "note": 9.0,
            "section": "programme",
        }

        # Mock DEUX livres : le bon et le mauvais
        livre_tresor_id = ObjectId("68e9192d066cb40c25d5d2d9")
        livre_chaise_id = ObjectId("68e919cd066cb40c25d5d2e3")

        livres = [
            {
                "_id": livre_tresor_id,
                "titre": "Trésor caché",  # ✅ BON match (singulier)
                "auteur_nom": "Pascal Quignard",
                "auteur_id": ObjectId("68e9192d066cb40c25d5d2d8"),
                "editeur": "Albin Michel",
            },
            {
                "_id": livre_chaise_id,
                "titre": "La chaise",  # ❌ MAUVAIS match (titre différent)
                "auteur_nom": "Jean-Louis Ezine",  # ❌ Auteur différent
                "auteur_id": ObjectId("68e919cd066cb40c25d5d2e2"),
                "editeur": "Gallimard",  # ❌ Éditeur différent
            },
        ]

        # Mock critiques
        critique_id = ObjectId("694eb58bffd25d11ce052759")
        critiques = [
            {
                "_id": critique_id,
                "nom": "Arnaud Viviant",
                "variantes": ["Arnaud Viviant"],
            }
        ]

        # EXECUTE: Résoudre les entités
        resolved_avis = self.extraction_service.resolve_entities(
            [avis_brut], livres, critiques
        )

        # ASSERT: Doit matcher "Trésor caché", PAS "La chaise"
        assert len(resolved_avis) == 1
        resolved = resolved_avis[0]

        assert resolved["livre_oid"] == str(livre_tresor_id), (
            f"MAUVAIS MATCH! Attendu livre '{livre_tresor_id}' (Trésor caché), "
            f"obtenu '{resolved.get('livre_oid')}' "
            f"(probablement La chaise = {livre_chaise_id})"
        )

        # Phase 3 devrait matcher (accent-insensitive)
        assert resolved.get("match_phase") in [3, "phase3"], (
            f"Expected phase3, got: {resolved.get('match_phase')}"
        )

    def test_should_match_la_chaises_to_la_chaise_when_not_taken(self):
        """
        Test RED: "La Chaises" doit matcher "La chaise" quand disponible.

        CAS RÉEL: Émission 09/03/2025
        - "La Chaises" (avec S) de Jean-Louis Aislin (faute de frappe)
        - Doit matcher "La chaise" de Jean-Louis Ezine

        ACTUELLEMENT: Non matché car "La chaise" est MAL utilisé par "Trésors Cachés"
        """
        _episode_id = str(ObjectId("67cf4660e1eab9ef0cddff91"))

        # Avis brut "La Chaises" (avec S en trop)
        avis_brut = {
            "livre_titre_extrait": "La Chaises",
            "auteur_nom_extrait": "Jean-Louis Aislin",  # Faute de frappe
            "editeur_extrait": "Gallimard",
            "critique_nom_extrait": "Arnaud Viviant",
            "commentaire": "Splendeur, sur le violoncelle",
            "note": 9.0,
            "section": "coup_de_coeur",
        }

        # Mock UN SEUL livre (pas de confusion possible)
        livre_chaise_id = ObjectId("68e919cd066cb40c25d5d2e3")
        livres = [
            {
                "_id": livre_chaise_id,
                "titre": "La chaise",
                "auteur_nom": "Jean-Louis Ezine",
                "auteur_id": ObjectId("68e919cd066cb40c25d5d2e2"),
                "editeur": "Gallimard",
            }
        ]

        # Mock critiques
        critique_id = ObjectId("694eb58bffd25d11ce052759")
        critiques = [
            {
                "_id": critique_id,
                "nom": "Arnaud Viviant",
                "variantes": ["Arnaud Viviant"],
            }
        ]

        # EXECUTE: Résoudre les entités
        resolved_avis = self.extraction_service.resolve_entities(
            [avis_brut], livres, critiques
        )

        # ASSERT: Doit être matché en Phase 3 (accent-insensitive tolère le S final)
        assert len(resolved_avis) == 1
        resolved = resolved_avis[0]

        assert resolved["livre_oid"] == str(livre_chaise_id), (
            f"Livre non matché! livre_oid={resolved.get('livre_oid')}"
        )

        # Phase 3 devrait fonctionner
        assert resolved.get("match_phase") in [3, "phase3"], (
            f"Expected phase3, got: {resolved.get('match_phase')}"
        )
