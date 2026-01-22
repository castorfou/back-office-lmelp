"""Test TDD pour l'extraction d'avis avec fautes de frappe (Issue #185).

PROBLÈME RÉEL: Émission du 09/03/2025
- 9 livres dans MongoDB
- 10 avis extraits (erreur de double matching)
- Plusieurs fautes de frappe dans Section 2 (Coups de cœur):
  * "Chris Hoffut" → "Chris Offutt"
  * "La Chaises" → "La chaise"
  * "Jean-Louis Aislin" → "Jean-Louis Ezine"
  * "Pirko Sessio" → "Pirkko Saisio"
  * "Le Livre rouge des ruptures" → "Trilogie de Helsinki : Le livre rouge des ruptures"

Ce test vérifie que les fautes de frappe et titres tronqués sont correctement matchés.
"""

from unittest.mock import MagicMock

from bson import ObjectId


class TestAvisExtractionTyposSection2:
    """Tests pour l'extraction d'avis avec fautes de frappe dans Section 2."""

    def setup_method(self):
        """Setup pour chaque test."""
        from back_office_lmelp.services.avis_extraction_service import (
            AvisExtractionService,
        )

        self.extraction_service = AvisExtractionService()

        # Mock mongodb_service
        self.mock_mongodb = MagicMock()
        self.extraction_service.mongodb_service = self.mock_mongodb

    def test_should_match_typo_author_name_in_section2(self):
        """
        Test RED: Matcher un auteur avec faute de frappe dans Section 2.

        CAS RÉEL: "Chris Hoffut" doit matcher "Chris Offutt"
        """
        _episode_id = str(ObjectId("67cf4660e1eab9ef0cddff91"))

        # Avis brut extrait avec faute de frappe
        avis_brut = {
            "livre_titre_extrait": "La Loi des collines",
            "auteur_nom_extrait": "Chris Hoffut",  # ❌ Faute de frappe
            "editeur_extrait": "Gallmeister",
            "critique_nom_extrait": "Bernard Poirette",
            "commentaire": "Rural noir américain de haute volée",
            "note": 9.0,
            "section": "coup_de_coeur",
        }

        # Mock livre dans MongoDB avec nom correct
        livre_id = ObjectId("68e919a2066cb40c25d5d2e1")
        livres = [
            {
                "_id": livre_id,
                "titre": "La Loi des collines",
                "auteur_nom": "Chris Offutt",  # ✅ Nom correct
                "auteur_id": ObjectId("68e919a2066cb40c25d5d2e0"),
                "editeur": "Galmeister",
            }
        ]

        # Mock critique
        critique_id = ObjectId("694f17665eac26c9eb2852ff")
        critiques = [
            {
                "_id": critique_id,
                "nom": "Bernard Poirette",
                "variantes": ["Bernard Poirette"],
            }
        ]

        # EXECUTE: Résoudre les entités
        resolved_avis = self.extraction_service.resolve_entities(
            [avis_brut], livres, critiques
        )

        # ASSERT: Le livre DOIT être matché malgré la faute
        assert len(resolved_avis) == 1, (
            f"Attendu 1 avis résolu, obtenu {len(resolved_avis)}"
        )
        resolved = resolved_avis[0]

        assert resolved["livre_oid"] == str(livre_id), (
            f"Livre non matché! livre_oid={resolved.get('livre_oid')}"
        )
        assert resolved["critique_oid"] == str(critique_id), (
            f"Critique non matché! critique_oid={resolved.get('critique_oid')}"
        )
        # Le livre DOIT être matché (peu importe la phase)
        # Phase 1 si titre exact, sinon Phase 4 (fuzzy matching)
        assert resolved.get("match_phase") in [
            1,
            2,
            3,
            4,
            "phase1",
            "phase2",
            "phase3",
            "phase4",
        ], f"Livre non matché! match_phase={resolved.get('match_phase')}"

    def test_should_match_title_with_extra_s_in_section2(self):
        """
        Test RED: Matcher un titre avec "s" en trop dans Section 2.

        CAS RÉEL: "La Chaises" doit matcher "La chaise"
        - Titre: "La Chaises" (1 char en trop) vs "La chaise"
        - Auteur: "Jean-Louis Aislin" (faute) vs "Jean-Louis Ezine"

        NI le titre NI l'auteur ne matchent exactement, donc Phase 1-3 échouent.
        Phase 4 (fuzzy) est nécessaire pour détecter la similarité du titre.
        """
        _episode_id = str(ObjectId("67cf4660e1eab9ef0cddff91"))

        # Avis brut extrait avec S en trop
        avis_brut = {
            "livre_titre_extrait": "La Chaises",  # ❌ S en trop (1 char de diff)
            "auteur_nom_extrait": "Jean-Louis Aislin",  # ❌ Aussi faute de frappe
            "editeur_extrait": "Gallimard",
            "critique_nom_extrait": "Arnaud Viviant",
            "commentaire": "Splendeur, sur le violoncelle",
            "note": 9.0,
            "section": "coup_de_coeur",
        }

        # Mock livre dans MongoDB avec nom correct
        livre_id = ObjectId("68e919cd066cb40c25d5d2e3")
        livres = [
            {
                "_id": livre_id,
                "titre": "La chaise",  # ✅ Titre correct (1 char de moins)
                "auteur_nom": "Jean-Louis Ezine",  # ✅ Nom correct (différent)
                "auteur_id": ObjectId("68e919cd066cb40c25d5d2e2"),
                "editeur": "Gallimard",
            }
        ]

        # Mock critique
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

        # ASSERT: Le livre DOIT être matché via Phase 4 (fuzzy matching)
        assert len(resolved_avis) == 1, (
            f"Attendu 1 avis résolu, obtenu {len(resolved_avis)}"
        )
        resolved = resolved_avis[0]

        # Phase 3 (similarité) ou Phase 4 (fuzzy matching) devrait matcher
        assert resolved["livre_oid"] == str(livre_id), (
            f"Livre non matché! livre_oid={resolved.get('livre_oid')}"
        )
        assert resolved.get("match_phase") in [3, 4], (
            f"Expected phase3 ou phase4, got: {resolved.get('match_phase')}"
        )

    def test_should_match_truncated_title_in_section2(self):
        """
        Test RED: Matcher un titre tronqué dans Section 2.

        CAS RÉEL: "Le Livre rouge des ruptures" doit matcher
        "Trilogie de Helsinki : Le livre rouge des ruptures"
        """
        _episode_id = str(ObjectId("67cf4660e1eab9ef0cddff91"))

        # Avis brut extrait avec titre tronqué
        avis_brut = {
            "livre_titre_extrait": "Le Livre rouge des ruptures",  # ❌ Tronqué
            "auteur_nom_extrait": "Pirko Sessio",  # ❌ Faute de frappe
            "editeur_extrait": "Robert Laffont",
            "critique_nom_extrait": "Patricia Martin",
            "commentaire": "Énergie de dingue, enthousiasme inaltéré",
            "note": 9.0,
            "section": "coup_de_coeur",
        }

        # Mock livre dans MongoDB avec titre complet
        livre_id = ObjectId("68e91a2d066cb40c25d5d2e6")
        livres = [
            {
                "_id": livre_id,
                "titre": "Trilogie de Helsinki : Le livre rouge des ruptures",  # ✅ Complet
                "auteur_nom": "Pirkko Saisio",  # ✅ Nom correct
                "auteur_id": ObjectId("68e91a2d066cb40c25d5d2e5"),
                "editeur": "Robert Laffont",
            }
        ]

        # Mock critique
        critique_id = ObjectId("694eb7423696842476c793cf")
        critiques = [
            {
                "_id": critique_id,
                "nom": "Patricia Martin",
                "variantes": ["Patricia Martin"],
            }
        ]

        # EXECUTE: Résoudre les entités
        resolved_avis = self.extraction_service.resolve_entities(
            [avis_brut], livres, critiques
        )

        # ASSERT: Le livre DOIT être matché malgré le titre tronqué
        assert len(resolved_avis) == 1, (
            f"Attendu 1 avis résolu, obtenu {len(resolved_avis)}"
        )
        resolved = resolved_avis[0]

        assert resolved["livre_oid"] == str(livre_id), (
            f"Livre non matché! livre_oid={resolved.get('livre_oid')}"
        )
        # Le livre DOIT être matché (peu importe la phase)
        # Phase 2 (partial) pour titre tronqué ou Phase 4 (fuzzy matching)
        assert resolved.get("match_phase") in [2, 3, 4, "phase2", "phase3", "phase4"], (
            f"Livre non matché! match_phase={resolved.get('match_phase')}"
        )

    def test_should_match_plural_title_in_section1(self):
        """
        Test RED: Matcher un titre au pluriel dans Section 1.

        CAS RÉEL: "Trésors Cachés" doit matcher "Trésor caché"
        """
        _episode_id = str(ObjectId("67cf4660e1eab9ef0cddff91"))

        # Avis brut extrait avec titre au pluriel
        avis_brut = {
            "livre_titre_extrait": "Trésors Cachés",  # ❌ Pluriel avec majuscule
            "auteur_nom_extrait": "Pascal Quignard",
            "editeur_extrait": "Albin Michel",
            "critique_nom_extrait": "Arnaud Viviant",
            "commentaire": "Absolument magnifique, prose poétique",
            "note": 9.0,
            "section": "programme",
        }

        # Mock livre dans MongoDB avec titre au singulier
        livre_id = ObjectId("68e9192d066cb40c25d5d2d9")
        livres = [
            {
                "_id": livre_id,
                "titre": "Trésor caché",  # ✅ Singulier
                "auteur_nom": "Pascal Quignard",
                "auteur_id": ObjectId("68e9192d066cb40c25d5d2d8"),
                "editeur": "Albin Michel",
            }
        ]

        # Mock critique
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

        # ASSERT: Le livre DOIT être matché malgré le pluriel
        assert len(resolved_avis) == 1, (
            f"Attendu 1 avis résolu, obtenu {len(resolved_avis)}"
        )
        resolved = resolved_avis[0]

        assert resolved["livre_oid"] == str(livre_id), (
            f"Livre non matché! livre_oid={resolved.get('livre_oid')}"
        )
        # Phase 3 ou 4 devrait être utilisée
        assert resolved.get("match_phase") in [3, 4, "phase3", "phase4"], (
            f"Expected phase3/phase4, got: {resolved.get('match_phase')}"
        )
