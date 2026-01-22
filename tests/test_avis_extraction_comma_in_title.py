"""Test TDD pour l'extraction d'avis avec virgules dans le titre (Issue #185).

PROBLÈME RÉEL: Émission du 03/08/2025
- 10 livres dans MongoDB
- Seulement 9 livres extraits dans la collection avis
- Livre manquant: "Harlem, Jamaïque, Marseille" (contient des virgules)

Ce test vérifie que les titres avec virgules sont correctement extraits.
"""

from unittest.mock import MagicMock

from bson import ObjectId


class TestAvisExtractionCommaInTitle:
    """Tests pour l'extraction d'avis avec virgules dans les titres."""

    def setup_method(self):
        """Setup pour chaque test."""
        from back_office_lmelp.services.avis_extraction_service import (
            AvisExtractionService,
        )

        self.extraction_service = AvisExtractionService()

        # Mock mongodb_service
        self.mock_mongodb = MagicMock()
        self.extraction_service.mongodb_service = self.mock_mongodb

    def test_should_extract_book_with_commas_in_title_from_section2(self):
        """
        Test RED: Extraire un livre avec virgules dans le titre depuis Section 2.

        CAS RÉEL: "Harlem, Jamaïque, Marseille" de Claude McKay
        Ce livre apparaît uniquement dans Section 2 (Coups de cœur) avec 2 virgules
        dans le titre, ce qui peut casser le parsing du tableau markdown.
        """
        # Données réelles de l'émission du 03/08/2025
        emission_id = str(ObjectId("694fea91e46eedc769bcd9be"))

        # Summary markdown réel (extrait Section 2)
        summary_section2 = """## 2. COUPS DE CŒUR DES CRITIQUES du 03 août 2025


| Auteur | Titre | Éditeur | Critique | Note | Commentaire |
|--------|-------|---------|----------|------|-------------|
| Tobi Dahmen | Columbusstraße | Robinson | Jean-Marc Proust | <span style="background-color: #4CAF50; color: white; padding: 2px 6px; border-radius: 3px; font-weight: bold;">8.5</span> | "Documentaire et beau roman graphique." |
| Sarah Schmidt | Le bleu est la couleur la plus rare | Rivage | Alice Develay | <span style="background-color: #4CAF50; color: white; padding: 2px 6px; border-radius: 3px; font-weight: bold;">8.5</span> | "Éblouissant, magnifique, bouleversant." |
| Claude McKay | Harlem, Jamaïque, Marseille | Les Cahiers | Hubert Arthus | <span style="background-color: #4CAF50; color: white; padding: 2px 6px; border-radius: 3px; font-weight: bold;">8.5</span> | "Auteur à découvrir, littérature interlope." |
| Alexandre Lamborot | Pâture | La TES | Laurent Chalumeau | <span style="background-color: #4CAF50; color: white; padding: 2px 6px; border-radius: 3px; font-weight: bold;">8.5</span> | "Talent en éclosion, excitant." |
| Michel Hazanavicius | Carnets d'Ukraine | Alari | Jérôme Garcin | <span style="background-color: #4CAF50; color: white; padding: 2px 6px; border-radius: 3px; font-weight: bold;">8.5</span> | "Sentiment d'immédiateté, poignant." |"""

        # Mock avis collection pour save
        mock_avis_collection = MagicMock()

        def get_collection_side_effect(name):
            """Route vers la bonne collection mockée."""
            collections = {
                "avis": mock_avis_collection,
            }
            return collections.get(name, MagicMock())

        self.mock_mongodb.get_collection.side_effect = get_collection_side_effect
        self.mock_mongodb.avis_collection = mock_avis_collection

        # EXECUTE: Extraire depuis Section 2 uniquement
        avis_list = self.extraction_service._extract_section2_avis(
            summary_section2, emission_id
        )

        # ASSERT: Le livre avec virgules DOIT être extrait
        assert len(avis_list) == 5, f"Attendu 5 avis, obtenu {len(avis_list)}"

        # Vérifier que "Harlem, Jamaïque, Marseille" est bien dans la liste
        harlem_avis = [
            avis
            for avis in avis_list
            if avis["livre_titre_extrait"] == "Harlem, Jamaïque, Marseille"
        ]
        assert len(harlem_avis) == 1, (
            f"Attendu 1 avis pour 'Harlem, Jamaïque, Marseille', obtenu {len(harlem_avis)}"
        )

        # Vérifier les détails de l'avis extrait
        avis = harlem_avis[0]
        assert avis["auteur_nom_extrait"] == "Claude McKay"
        assert avis["livre_titre_extrait"] == "Harlem, Jamaïque, Marseille"
        assert avis["editeur_extrait"] == "Les Cahiers"
        assert avis["critique_nom_extrait"] == "Hubert Arthus"
        assert avis["commentaire"] == "Auteur à découvrir, littérature interlope."
        assert avis["section"] == "coup_de_coeur"

    def test_should_match_book_with_commas_to_mongodb(self):
        """
        Test RED: Matcher un livre avec virgules dans le titre vers MongoDB.

        Vérifie que le matching fonctionne même avec des virgules dans le titre.
        """
        _episode_id = str(ObjectId("68a3911df8b628e552fdf11f"))

        # Avis brut extrait
        avis_brut = {
            "livre_titre_extrait": "Harlem, Jamaïque, Marseille",
            "auteur_nom_extrait": "Claude McKay",
            "editeur_extrait": "Les Cahiers",
            "critique_nom_extrait": "Hubert Arthus",
            "commentaire": "Auteur à découvrir, littérature interlope.",
            "note": 8.5,
            "section": "coup_de_coeur",
        }

        # Mock livre dans MongoDB
        livre_harlem_id = ObjectId("68e4760a50074bf855329d47")
        livres = [
            {
                "_id": livre_harlem_id,
                "titre": "Harlem, Jamaïque, Marseille",
                "auteur_nom": "Claude McKay",
                "auteur_id": ObjectId("68e4760a50074bf855329d46"),
                "editeur": "Les Cahiers",
            }
        ]

        # Mock critique
        critique_arthus_id = ObjectId("694f281ef76354d46485c4d6")
        critiques = [
            {
                "_id": critique_arthus_id,
                "nom": "Hubert Arthus",
                "variantes": ["Hubert Arthus"],
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

        assert resolved["livre_oid"] == str(livre_harlem_id), (
            f"Livre non matché! livre_oid={resolved.get('livre_oid')}"
        )
        assert resolved["critique_oid"] == str(critique_arthus_id), (
            f"Critique non matché! critique_oid={resolved.get('critique_oid')}"
        )
        # match_phase peut être un int (1, 2, 3, 4) ou string ("phase1", "phase2", etc.)
        assert resolved.get("match_phase") in [
            1,
            2,
            3,
            4,
            "phase1",
            "phase2",
            "phase3",
            "phase4",
        ], f"Match phase invalide: {resolved.get('match_phase')}"
