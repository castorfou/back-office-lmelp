"""Tests pour la recherche insensible aux accents (Issue #92)."""


class TestAccentInsensitiveRegex:
    """Tests pour la fonction create_accent_insensitive_regex."""

    def test_simple_word_without_accents(self):
        """
        GIVEN: Un mot simple sans accents 'test'
        WHEN: create_accent_insensitive_regex est appelé
        THEN: Retourne un regex qui matche les variantes accentuées de chaque lettre
        """
        from back_office_lmelp.utils.text_utils import create_accent_insensitive_regex

        result = create_accent_insensitive_regex("test")
        assert "t" in result
        assert "[eèéêëēĕėęě]" in result  # 'e' devient un charset avec variantes

    def test_word_with_accents(self):
        """
        GIVEN: Un mot avec accents 'café'
        WHEN: create_accent_insensitive_regex est appelé
        THEN: Retourne un regex qui normalise les accents
        """
        from back_office_lmelp.utils.text_utils import create_accent_insensitive_regex

        result = create_accent_insensitive_regex("café")
        # 'café' devrait être traité comme 'cafe' puis transformé en regex
        assert "[cç]" in result
        assert "[aàâäáãåāăą]" in result
        assert "[eèéêëēĕėęě]" in result

    def test_matches_carrere_without_accent(self):
        """
        GIVEN: Le terme de recherche 'carrere' (sans accent)
        WHEN: On génère le regex et on teste avec 'Emmanuel Carrère' (avec accent è)
        THEN: Le regex doit matcher
        """
        import re

        from back_office_lmelp.utils.text_utils import create_accent_insensitive_regex

        regex_pattern = create_accent_insensitive_regex("carrere")
        pattern = re.compile(regex_pattern, re.IGNORECASE)

        # Doit matcher différentes variantes
        assert pattern.search("Emmanuel Carrère") is not None
        assert pattern.search("Carrère") is not None
        assert pattern.search("CARRÈRE") is not None
        assert pattern.search("carrere") is not None

    def test_matches_emonet_without_accent(self):
        """
        GIVEN: Le terme de recherche 'emonet' (sans accent)
        WHEN: On génère le regex et on teste avec 'Simone Émonet' (avec accent É)
        THEN: Le regex doit matcher
        """
        import re

        from back_office_lmelp.utils.text_utils import create_accent_insensitive_regex

        regex_pattern = create_accent_insensitive_regex("emonet")
        pattern = re.compile(regex_pattern, re.IGNORECASE)

        assert pattern.search("Simone Émonet") is not None
        assert pattern.search("Émonet") is not None
        assert pattern.search("emonet") is not None

    def test_matches_etranger(self):
        """
        GIVEN: Le terme 'etranger' (sans accent)
        WHEN: On teste avec "L'Étranger" (avec accent É)
        THEN: Le regex doit matcher
        """
        import re

        from back_office_lmelp.utils.text_utils import create_accent_insensitive_regex

        regex_pattern = create_accent_insensitive_regex("etranger")
        pattern = re.compile(regex_pattern, re.IGNORECASE)

        assert pattern.search("L'Étranger") is not None
        assert pattern.search("Étranger") is not None
        assert pattern.search("etranger") is not None

    def test_empty_string(self):
        """
        GIVEN: Une chaîne vide
        WHEN: create_accent_insensitive_regex est appelé
        THEN: Retourne une chaîne vide
        """
        from back_office_lmelp.utils.text_utils import create_accent_insensitive_regex

        result = create_accent_insensitive_regex("")
        assert result == ""

    def test_special_characters_preserved(self):
        """
        GIVEN: Une chaîne avec caractères spéciaux "l'ami"
        WHEN: create_accent_insensitive_regex est appelé
        THEN: Les caractères spéciaux sont préservés
        """
        from back_office_lmelp.utils.text_utils import create_accent_insensitive_regex

        result = create_accent_insensitive_regex("l'ami")
        assert "'" in result  # L'apostrophe doit être préservée

    def test_francois_variations(self):
        """
        GIVEN: Le terme 'francois' (sans accent)
        WHEN: On teste avec différentes variantes accentuées
        THEN: Le regex doit matcher toutes les variantes
        """
        import re

        from back_office_lmelp.utils.text_utils import create_accent_insensitive_regex

        regex_pattern = create_accent_insensitive_regex("francois")
        pattern = re.compile(regex_pattern, re.IGNORECASE)

        assert pattern.search("François") is not None
        assert pattern.search("Francois") is not None
        assert pattern.search("FRANÇOIS") is not None


class TestMongoDBServiceAccentInsensitive:
    """Tests d'intégration pour la recherche insensible aux accents dans MongoDB Service."""

    def test_search_auteurs_uses_accent_insensitive_regex(self, mocker):
        """
        GIVEN: Une recherche 'carrere' (sans accent)
        WHEN: search_auteurs est appelé
        THEN: Le regex généré contient les variantes accentuées
        """
        from back_office_lmelp.services.mongodb_service import MongoDBService

        # Mock de la collection MongoDB
        mock_collection = mocker.MagicMock()
        mock_collection.count_documents.return_value = 1
        mock_collection.find.return_value.skip.return_value.limit.return_value = [
            {"_id": "123", "nom": "Emmanuel Carrère"}
        ]

        # Créer une instance du service avec la collection mockée
        service = MongoDBService()
        service.auteurs_collection = mock_collection

        # Appeler search_auteurs avec un terme sans accent
        service.search_auteurs("carrere", limit=10, offset=0)

        # Vérifier que count_documents a été appelé avec un regex insensible aux accents
        call_args = mock_collection.count_documents.call_args
        search_query = call_args[0][0]

        # Le regex doit contenir des charsets pour les variantes accentuées
        assert "$regex" in search_query["nom"]
        regex_pattern = search_query["nom"]["$regex"]
        assert "[cç]" in regex_pattern
        assert "[aàâäáãåāăą]" in regex_pattern
        assert "[eèéêëēĕėęě]" in regex_pattern

    def test_search_livres_uses_accent_insensitive_regex(self, mocker):
        """
        GIVEN: Une recherche 'emonet' (sans accent)
        WHEN: search_livres est appelé
        THEN: Le regex généré contient les variantes accentuées
        """
        from back_office_lmelp.services.mongodb_service import MongoDBService

        # Mock de la collection MongoDB
        mock_livres_collection = mocker.MagicMock()
        mock_livres_collection.count_documents.return_value = 1
        mock_livres_collection.find.return_value.skip.return_value.limit.return_value = [
            {"_id": "456", "titre": "Simone Émonet", "auteur_id": None}
        ]

        # Créer une instance du service avec la collection mockée
        service = MongoDBService()
        service.livres_collection = mock_livres_collection
        service.auteurs_collection = None  # Pas besoin pour ce test

        # Appeler search_livres avec un terme sans accent
        service.search_livres("emonet", limit=10, offset=0)

        # Vérifier que count_documents a été appelé avec un regex insensible aux accents
        call_args = mock_livres_collection.count_documents.call_args
        search_query = call_args[0][0]

        # Le regex doit contenir des charsets pour les variantes accentuées
        assert "$regex" in search_query["titre"]
        regex_pattern = search_query["titre"]["$regex"]
        assert "[eèéêëēĕėęě]" in regex_pattern
        assert "[oòóôöõøōŏő]" in regex_pattern

    def test_search_editeurs_uses_accent_insensitive_regex(self, mocker):
        """
        GIVEN: Une recherche d'éditeur 'flammarion'
        WHEN: search_editeurs est appelé
        THEN: Le regex généré contient les variantes accentuées
        """
        from back_office_lmelp.services.mongodb_service import MongoDBService

        # Mock des collections MongoDB
        mock_editeurs_collection = mocker.MagicMock()
        mock_editeurs_collection.find.return_value.skip.return_value.limit.return_value = [
            {"_id": "789", "nom": "Flammarion"}
        ]

        mock_livres_collection = mocker.MagicMock()
        mock_livres_collection.find.return_value.skip.return_value.limit.return_value = []

        # Créer une instance du service avec les collections mockées
        service = MongoDBService()
        service.editeurs_collection = mock_editeurs_collection
        service.livres_collection = mock_livres_collection

        # Appeler search_editeurs
        service.search_editeurs("flammarion", limit=10, offset=0)

        # Vérifier que find a été appelé avec un regex insensible aux accents
        call_args_editeurs = mock_editeurs_collection.find.call_args
        search_query_editeurs = call_args_editeurs[0][0]

        # Le regex doit contenir des charsets pour les variantes accentuées
        assert "$regex" in search_query_editeurs["nom"]
        regex_pattern = search_query_editeurs["nom"]["$regex"]
        assert "[aàâäáãåāăą]" in regex_pattern


class TestAdvancedSearchEndpointAccentInsensitive:
    """Tests end-to-end pour l'endpoint /api/advanced-search avec recherche insensible aux accents."""

    def test_advanced_search_finds_carrere_without_accent(
        self, client, mock_mongodb_service
    ):
        """
        GIVEN: Base contient "Emmanuel Carrère" (avec è)
        WHEN: Utilisateur cherche 'carrere' (sans accent) via /api/advanced-search
        THEN: Trouve l'auteur "Emmanuel Carrère"
        """
        # Mock de la réponse MongoDB
        mock_mongodb_service.search_auteurs.return_value = {
            "auteurs": [{"_id": "123", "nom": "Emmanuel Carrère"}],
            "total_count": 1,
        }

        response = client.get("/api/advanced-search?q=carrere&entities=auteurs")

        assert response.status_code == 200
        data = response.json()
        assert data["results"]["auteurs_total_count"] == 1
        assert data["results"]["auteurs"][0]["nom"] == "Emmanuel Carrère"

    def test_advanced_search_finds_emonet_without_accent(
        self, client, mock_mongodb_service
    ):
        """
        GIVEN: Base contient livre "Simone Émonet" (avec É)
        WHEN: Utilisateur cherche 'emonet' (sans accent) via /api/advanced-search
        THEN: Trouve le livre
        """
        mock_mongodb_service.search_livres.return_value = {
            "livres": [{"_id": "456", "titre": "Simone Émonet"}],
            "total_count": 1,
        }

        response = client.get("/api/advanced-search?q=emonet&entities=livres")

        assert response.status_code == 200
        data = response.json()
        assert data["results"]["livres_total_count"] == 1
        assert data["results"]["livres"][0]["titre"] == "Simone Émonet"


class TestTypographicCharactersRegex:
    """Tests pour les caractères typographiques (Issue #173)."""

    def test_ligature_oe_should_match_oe_sequence(self):
        """
        GIVEN: Un terme de recherche 'oeuvre' (sans ligature)
        WHEN: create_accent_insensitive_regex est appelé
        THEN: Le regex doit matcher 'œuvre' (avec ligature œ)
        """
        import re

        from back_office_lmelp.utils.text_utils import create_accent_insensitive_regex

        regex_pattern = create_accent_insensitive_regex("oeuvre")
        pattern = re.compile(regex_pattern, re.IGNORECASE)

        # Doit matcher les deux formes
        assert pattern.search("oeuvre") is not None  # Sans ligature
        assert pattern.search("œuvre") is not None  # Avec ligature œ
        assert pattern.search("ŒUVRE") is not None  # Majuscule

    def test_ligature_oe_in_word_should_match(self):
        """
        GIVEN: Recherche 'coeur' (sans ligature)
        WHEN: Regex généré
        THEN: Doit matcher 'cœur' (avec ligature)
        """
        import re

        from back_office_lmelp.utils.text_utils import create_accent_insensitive_regex

        regex_pattern = create_accent_insensitive_regex("coeur")
        pattern = re.compile(regex_pattern, re.IGNORECASE)

        assert pattern.search("coeur") is not None
        assert pattern.search("cœur") is not None
        assert pattern.search("Cœur") is not None

    def test_ligature_ae_should_match_ae_sequence(self):
        """
        GIVEN: Recherche 'aegis' (sans ligature)
        WHEN: Regex généré
        THEN: Doit matcher 'ægis' (avec ligature æ)
        """
        import re

        from back_office_lmelp.utils.text_utils import create_accent_insensitive_regex

        regex_pattern = create_accent_insensitive_regex("aegis")
        pattern = re.compile(regex_pattern, re.IGNORECASE)

        assert pattern.search("aegis") is not None
        assert pattern.search("ægis") is not None
        assert pattern.search("Ægis") is not None

    def test_em_dash_should_match_hyphen(self):
        """
        GIVEN: Recherche 'Marie-Claire' (tiret simple)
        WHEN: Regex généré
        THEN: Doit matcher 'Marie–Claire' (tiret cadratin –)
        """
        import re

        from back_office_lmelp.utils.text_utils import create_accent_insensitive_regex

        regex_pattern = create_accent_insensitive_regex("Marie-Claire")
        pattern = re.compile(regex_pattern, re.IGNORECASE)

        assert pattern.search("Marie-Claire") is not None  # Tiret simple
        assert pattern.search("Marie–Claire") is not None  # Tiret cadratin
        assert pattern.search("marie-claire") is not None  # Lowercase

    def test_typographic_apostrophe_should_match_simple_apostrophe(self):
        """
        GIVEN: Recherche "l'ami" (apostrophe simple)
        WHEN: Regex généré
        THEN: Doit matcher "l'ami" (apostrophe typographique ')
        """
        import re

        from back_office_lmelp.utils.text_utils import create_accent_insensitive_regex

        regex_pattern = create_accent_insensitive_regex("l'ami")
        pattern = re.compile(regex_pattern, re.IGNORECASE)

        assert pattern.search("l'ami") is not None  # Simple
        assert pattern.search("l'ami") is not None  # Typographique
        assert pattern.search("L'AMI") is not None  # Uppercase

    def test_search_without_apostrophe_should_match_with_apostrophe(self):
        """
        GIVEN: Recherche "d Ormesson" (SANS apostrophe)
        WHEN: Regex généré
        THEN: Doit matcher "Jean d' Ormesson" (AVEC apostrophe + espace)
        Issue #173: Cas réel de la base MongoDB
        """
        import re

        from back_office_lmelp.utils.text_utils import create_accent_insensitive_regex

        # Test 1: Recherche "d Ormesson" doit matcher "d' Ormesson"
        regex_pattern = create_accent_insensitive_regex("d Ormesson")
        pattern = re.compile(regex_pattern, re.IGNORECASE)

        assert (
            pattern.search("Jean d' Ormesson") is not None
        )  # Apostrophe simple + espace
        assert (
            pattern.search("Jean d' Ormesson") is not None
        )  # Apostrophe typo + espace
        assert pattern.search("Jean d Ormesson") is not None  # Sans apostrophe

        # Test 2: Recherche "l ami" doit matcher "l'ami"
        regex_pattern2 = create_accent_insensitive_regex("l ami")
        pattern2 = re.compile(regex_pattern2, re.IGNORECASE)

        assert pattern2.search("l'ami") is not None
        assert pattern2.search("l'ami") is not None
        assert pattern2.search("l ami") is not None


class TestMongoDBServiceTypographicCharacters:
    """Tests d'intégration pour caractères typographiques dans MongoDB Service."""

    def test_search_auteurs_finds_oe_ligature(self, mocker):
        """
        GIVEN: Base contient auteur avec 'œ' dans le nom
        WHEN: Utilisateur cherche 'oeuvre' (sans ligature)
        THEN: Le regex généré contient le pattern pour matcher 'œ'
        """
        from back_office_lmelp.services.mongodb_service import MongoDBService

        mock_collection = mocker.MagicMock()
        mock_collection.count_documents.return_value = 1
        mock_collection.find.return_value.skip.return_value.limit.return_value = [
            {"_id": "123", "nom": "L'Œuvre au noir"}
        ]

        service = MongoDBService()
        service.auteurs_collection = mock_collection

        service.search_auteurs("oeuvre", limit=10, offset=0)

        call_args = mock_collection.count_documents.call_args
        search_query = call_args[0][0]

        # Vérifier que le regex contient le pattern pour ligature œ
        regex_pattern = search_query["nom"]["$regex"]
        assert (
            "œ" in regex_pattern or "(?:" in regex_pattern
        )  # Regex avec groupe pour ligature

    def test_search_livres_finds_em_dash(self, mocker):
        """
        GIVEN: Base contient livre avec tiret cadratin "Marie–Claire"
        WHEN: Utilisateur cherche 'Marie-Claire' (tiret simple)
        THEN: Le regex généré contient le pattern pour matcher '–'
        """
        from back_office_lmelp.services.mongodb_service import MongoDBService

        mock_collection = mocker.MagicMock()
        mock_collection.count_documents.return_value = 1
        mock_collection.find.return_value.skip.return_value.limit.return_value = [
            {"_id": "456", "titre": "Marie–Claire", "auteur_id": None}
        ]

        service = MongoDBService()
        service.livres_collection = mock_collection
        service.auteurs_collection = None

        service.search_livres("Marie-Claire", limit=10, offset=0)

        call_args = mock_collection.count_documents.call_args
        search_query = call_args[0][0]

        # Vérifier que le regex contient les deux types de tirets
        regex_pattern = search_query["titre"]["$regex"]
        assert "[-–]" in regex_pattern  # Charset avec tiret simple et cadratin

    def test_search_episodes_should_use_accent_insensitive_regex(self, mocker):
        """
        GIVEN: Base contient épisode avec titre "L'Étranger"
        WHEN: Utilisateur cherche 'etranger' (sans accent)
        THEN: search_episodes utilise create_accent_insensitive_regex (Issue #173)
        """
        from back_office_lmelp.services.mongodb_service import MongoDBService

        mock_collection = mocker.MagicMock()
        mock_collection.count_documents.return_value = 1
        mock_collection.find.return_value.sort.return_value.skip.return_value.limit.return_value = [
            {"_id": "789", "titre": "L'Étranger", "date": "2024-01-01"}
        ]

        service = MongoDBService()
        service.episodes_collection = mock_collection

        service.search_episodes("etranger", limit=10, offset=0)

        call_args = mock_collection.count_documents.call_args
        search_query = call_args[0][0]

        # Vérifier que le regex est insensible aux accents (contient charsets)
        titre_regex = search_query["$or"][0]["titre"]["$regex"]
        assert "[eèéêëēĕėęě]" in titre_regex  # Charset pour 'e' avec variantes
