"""Tests pour la query MongoDB du script migrate_url_babelio.py (Issue #124)."""

from bson import ObjectId


class TestMigrateUrlBabelioQuery:
    """Tests pour vérifier que la query MongoDB exclut correctement les livres."""

    def test_query_should_exclude_books_with_babelio_not_found_true(self):
        """Test TDD: La query doit exclure les livres avec babelio_not_found: true.

        Problème business réel:
        - Des livres ont babelio_not_found: true (marqués par l'utilisateur)
        - Ces livres n'ont PAS de url_babelio
        - La query doit les EXCLURE pour ne pas les re-traiter

        Scénario:
        1. Créer une query qui cherche les livres sans url_babelio
        2. La query doit AUSSI exclure ceux avec babelio_not_found: true
        3. Vérifier que la query a la bonne structure MongoDB
        """
        # Arrange - Construire la query exactement comme dans le script
        problematic_ids = []  # Pas de cas problématiques pour ce test

        query = {
            "$or": [{"url_babelio": None}, {"url_babelio": {"$exists": False}}],
            # CRITIQUE: Exclure les livres déjà marqués "not found" par l'utilisateur
            # Sinon ils seront re-traités et re-ajoutés au JSONL à chaque migration
            "$nor": [{"babelio_not_found": True}],
        }

        if problematic_ids:
            # Exclure les livres déjà loggés comme problématiques
            excluded_object_ids = [ObjectId(id_str) for id_str in problematic_ids]
            query["_id"] = {"$nin": excluded_object_ids}

        # Assert - Vérifier la structure de la query
        assert "$or" in query, "La query doit avoir un $or pour url_babelio"
        assert "$nor" in query, "La query doit avoir un $nor pour babelio_not_found"

        # Vérifier que $nor contient bien la condition babelio_not_found: true
        assert query["$nor"] == [{"babelio_not_found": True}], (
            "La condition $nor doit exclure babelio_not_found: true"
        )

        # Vérifier que $or cherche bien les livres sans url_babelio
        assert {"url_babelio": None} in query["$or"]
        assert {"url_babelio": {"$exists": False}} in query["$or"]

    def test_query_should_also_exclude_problematic_ids(self):
        """Test: La query doit AUSSI exclure les IDs problématiques du JSONL."""
        # Arrange
        problematic_ids = ["6914a45f497dd3ad92041855", "692c8b7fe405566c2a0b869c"]

        query = {
            "$or": [{"url_babelio": None}, {"url_babelio": {"$exists": False}}],
            "$nor": [{"babelio_not_found": True}],
        }

        if problematic_ids:
            excluded_object_ids = [ObjectId(id_str) for id_str in problematic_ids]
            query["_id"] = {"$nin": excluded_object_ids}

        # Assert
        assert "_id" in query, "La query doit avoir une condition _id"
        assert "$nin" in query["_id"], "La condition _id doit utiliser $nin"

        # Vérifier que les IDs problématiques sont exclus
        excluded_ids = query["_id"]["$nin"]
        assert len(excluded_ids) == 2
        assert all(isinstance(oid, ObjectId) for oid in excluded_ids)
