"""Tests TDD pour notebooks/dataset_avis.py.

Le script est exécuté via runpy.run_path() avec un mock MongoDB injecté,
ce qui permet de tester le comportement sans base de données réelle.

Données de référence extraites de MongoDB (réelles) :
- avis._id          : ObjectId (ex: 696d46f0e738dcd14c128589)  # pragma: allowlist secret
- avis.critique_oid : String (ex: "694eb58bffd25d11ce052759")  # pragma: allowlist secret
- avis.livre_oid    : String (ex: "6948458b4c7793c317f9f795")  # pragma: allowlist secret
- avis.note         : Number (1-10)
- avis.critique_nom_extrait : String (nom dénormalisé, peut être incohérent)
- avis.livre_titre_extrait  : String
- critiques._id     : ObjectId
- critiques.nom     : String (nom canonique)
"""

import runpy
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from bson import ObjectId


# Chemin absolu du script
DATASET_SCRIPT = Path("/workspaces/back-office-lmelp/notebooks/dataset_avis.py")


def make_mock_db(avis_docs: list[dict], critiques_docs: list[dict]) -> MagicMock:
    """Construit un mock db MongoDB avec les données fournies."""
    mock_db = MagicMock()

    # mock db.avis.find(...)
    mock_db.avis.find.return_value = avis_docs

    # mock db.critiques.find(...)
    mock_db.critiques.find.return_value = critiques_docs

    # mock db.livres.find(...) — utilisé par le chemin Calibre
    mock_db.livres.find.return_value = []

    return mock_db


def run_dataset(avis_docs: list[dict], critiques_docs: list[dict]) -> dict:
    """Exécute dataset_avis.py avec des données mockées et retourne les variables."""
    import matplotlib

    matplotlib.use("Agg")  # backend non-interactif, sans display

    mock_db = make_mock_db(avis_docs, critiques_docs)
    mock_client = MagicMock()
    mock_client.get_default_database.return_value = mock_db

    with (
        patch("pymongo.MongoClient", return_value=mock_client),
        patch("matplotlib.pyplot.show"),
    ):
        globs = runpy.run_path(str(DATASET_SCRIPT))

    return globs


# ── Fixtures de données réalistes ────────────────────────────────────────────

OID_VIVIANT = "694eb58bffd25d11ce052759"  # pragma: allowlist secret
OID_PHILIPPE = "694eb72b3696842476c793cd"  # pragma: allowlist secret
OID_NEUHOFF = "695679b0b49e0e1c6b6e3161"  # pragma: allowlist secret

OID_LIVRE_1 = "6948458b4c7793c317f9f795"  # pragma: allowlist secret
OID_LIVRE_2 = "6948458b4c7793c317f9f796"  # pragma: allowlist secret
OID_LIVRE_3 = "6948458b4c7793c317f9f797"  # pragma: allowlist secret


@pytest.fixture
def avis_simple() -> list[dict]:
    """Deux avis valides, deux critiques distincts."""
    return [
        {
            "_id": ObjectId("696d46f0e738dcd14c128589"),
            "critique_oid": OID_VIVIANT,
            "livre_oid": OID_LIVRE_1,
            "note": 8,
            "critique_nom_extrait": "Arnaud Viviant",
            "livre_titre_extrait": "Combats de filles",
        },
        {
            "_id": ObjectId("696d46f0e738dcd14c128590"),
            "critique_oid": OID_PHILIPPE,
            "livre_oid": OID_LIVRE_2,
            "note": 9,
            "critique_nom_extrait": "Elisabeth Philippe",
            "livre_titre_extrait": "Mon deuxième livre",
        },
    ]


@pytest.fixture
def critiques_simple() -> list[dict]:
    """Noms canoniques pour les deux critiques."""
    return [
        {"_id": ObjectId(OID_VIVIANT), "nom": "Arnaud Viviant"},
        {"_id": ObjectId(OID_PHILIPPE), "nom": "Elisabeth Philippe"},
    ]


# ── Tests : noms canoniques ───────────────────────────────────────────────────


class TestNomsCanoiques:
    """Le nom affiché doit toujours venir de la collection critiques, pas de avis."""

    def test_nom_canonique_remplace_nom_extrait(self, avis_simple, critiques_simple):
        """Le critique_nom dans df doit être le nom canonique de critiques."""
        # Modifier le nom extrait pour qu'il soit différent du nom canonique
        avis_simple[0]["critique_nom_extrait"] = "A. Viviant"  # nom abrégé / ancien

        globs = run_dataset(avis_simple, critiques_simple)
        df = globs["df"]

        viviant_rows = df[df["critique_oid"] == OID_VIVIANT]
        assert all(viviant_rows["critique_nom"] == "Arnaud Viviant"), (
            "Le nom doit être le nom canonique depuis critiques, pas le nom extrait"
        )

    def test_doublon_eric_neuhoff_fusionne_en_un_seul_nom(self):
        """Même critique_oid avec deux noms extraits différents → un seul nom canonique."""
        # Ajouter un second critique pour que GroupShuffleSplit puisse faire le split
        avis_docs = [
            {
                "_id": ObjectId("696d46f0e738dcd14c128591"),
                "critique_oid": OID_NEUHOFF,
                "livre_oid": OID_LIVRE_1,
                "note": 7,
                "critique_nom_extrait": "Eric Neuhoff",  # sans accent (ancien)
                "livre_titre_extrait": "Livre A",
            },
            {
                "_id": ObjectId("696d46f0e738dcd14c128592"),
                "critique_oid": OID_NEUHOFF,
                "livre_oid": OID_LIVRE_2,
                "note": 8,
                "critique_nom_extrait": "Éric Neuhoff",  # avec accent (récent)
                "livre_titre_extrait": "Livre B",
            },
            {
                "_id": ObjectId("696d46f0e738dcd14c128593"),
                "critique_oid": OID_VIVIANT,
                "livre_oid": OID_LIVRE_3,
                "note": 9,
                "critique_nom_extrait": "Arnaud Viviant",
                "livre_titre_extrait": "Livre C",
            },
        ]
        critiques_docs = [
            {"_id": ObjectId(OID_NEUHOFF), "nom": "Éric Neuhoff"},  # nom canonique
            {"_id": ObjectId(OID_VIVIANT), "nom": "Arnaud Viviant"},
        ]

        globs = run_dataset(avis_docs, critiques_docs)
        df = globs["df"]

        noms_neuhoff = df[df["critique_oid"] == OID_NEUHOFF]["critique_nom"].unique()
        assert len(noms_neuhoff) == 1, (
            f"Eric/Éric Neuhoff doit apparaître sous un seul nom, trouvé : {noms_neuhoff}"
        )
        assert noms_neuhoff[0] == "Éric Neuhoff"

    def test_critique_sans_entree_critiques_garde_nom_extrait(self, avis_simple):
        """Si critique_oid absent de critiques, on garde le nom extrait comme fallback."""
        # Pas de doc dans critiques pour OID_VIVIANT
        critiques_docs = [
            {"_id": ObjectId(OID_PHILIPPE), "nom": "Elisabeth Philippe"},
        ]
        globs = run_dataset(avis_simple, critiques_docs)
        df = globs["df"]

        viviant_rows = df[df["critique_oid"] == OID_VIVIANT]
        assert all(viviant_rows["critique_nom"] == "Arnaud Viviant"), (
            "Sans entrée dans critiques, le nom extrait doit être conservé"
        )


# ── Tests : filtrage des notes ────────────────────────────────────────────────


class TestFiltrageNotes:
    """Seules les notes entre 1 et 10 inclus doivent être conservées."""

    def _avis_deux_critiques(
        self, notes_viviant: list, notes_philippe: list
    ) -> list[dict]:
        """Helper : crée des avis pour deux critiques (requis par GroupShuffleSplit)."""
        docs = []
        for i, note in enumerate(notes_viviant):
            docs.append(
                {
                    "_id": ObjectId(),
                    "critique_oid": OID_VIVIANT,
                    "livre_oid": f"livre_v_{i:024d}",
                    "note": note,
                    "critique_nom_extrait": "Arnaud Viviant",
                    "livre_titre_extrait": f"Livre V{i}",
                }
            )
        for i, note in enumerate(notes_philippe):
            docs.append(
                {
                    "_id": ObjectId(),
                    "critique_oid": OID_PHILIPPE,
                    "livre_oid": f"livre_p_{i:024d}",
                    "note": note,
                    "critique_nom_extrait": "Elisabeth Philippe",
                    "livre_titre_extrait": f"Livre P{i}",
                }
            )
        return docs

    def test_notes_valides_conservees(self, critiques_simple):
        """Notes 1 à 10 inclus sont toutes conservées."""
        avis_docs = self._avis_deux_critiques([1, 5, 10], [7])
        globs = run_dataset(avis_docs, critiques_simple)
        assert len(globs["df"]) == 4

    def test_note_zero_exclue(self, critiques_simple):
        """Note 0 (Calibre non noté) est exclue."""
        avis_docs = self._avis_deux_critiques([0, 8], [7])
        globs = run_dataset(avis_docs, critiques_simple)
        # note=0 exclue → 2 avis conservés (8 et 7)
        assert len(globs["df"]) == 2
        assert set(globs["df"]["note"].tolist()) == {8.0, 7.0}

    def test_note_manquante_exclue(self, critiques_simple):
        """Avis sans note (None/NaN) est exclu."""
        avis_docs = self._avis_deux_critiques([None, 7], [6])
        globs = run_dataset(avis_docs, critiques_simple)
        # note=None exclue → 2 avis conservés (7 et 6)
        assert len(globs["df"]) == 2

    def test_note_hors_echelle_exclue(self, critiques_simple):
        """Note > 10 est exclue."""
        # Les deux critiques gardent au moins un avis valide pour que le split reste possible
        avis_docs = self._avis_deux_critiques([11, 7], [8, 9])
        globs = run_dataset(avis_docs, critiques_simple)
        # note=11 exclue → 3 avis conservés (7, 8 et 9)
        assert len(globs["df"]) == 3
        assert 11.0 not in globs["df"]["note"].tolist()


# ── Tests : structure du DataFrame ───────────────────────────────────────────


class TestStructureDataFrame:
    """Le DataFrame df doit avoir les colonnes attendues et les bons types."""

    def test_colonnes_requises_presentes(self, avis_simple, critiques_simple):
        """df doit avoir exactement les colonnes : critique_oid, livre_oid, note, critique_nom, livre_titre."""
        globs = run_dataset(avis_simple, critiques_simple)
        df = globs["df"]

        colonnes_attendues = {
            "critique_oid",
            "livre_oid",
            "note",
            "critique_nom",
            "livre_titre",
        }
        assert colonnes_attendues.issubset(set(df.columns)), (
            f"Colonnes manquantes : {colonnes_attendues - set(df.columns)}"
        )

    def test_note_est_float(self, avis_simple, critiques_simple):
        """La colonne note doit être de type float64."""
        globs = run_dataset(avis_simple, critiques_simple)
        df = globs["df"]
        assert df["note"].dtype == "float64"

    def test_statistiques_exposees(self, avis_simple, critiques_simple):
        """n_avis, n_critiques, n_livres doivent être exposés et cohérents."""
        globs = run_dataset(avis_simple, critiques_simple)

        assert globs["n_avis"] == 2
        assert globs["n_critiques"] == 2
        assert globs["n_livres"] == 2

    def test_critique_names_dict(self, avis_simple, critiques_simple):
        """critique_names doit mapper critique_oid → nom canonique."""
        globs = run_dataset(avis_simple, critiques_simple)

        critique_names = globs["critique_names"]
        assert critique_names[OID_VIVIANT] == "Arnaud Viviant"
        assert critique_names[OID_PHILIPPE] == "Elisabeth Philippe"

    def test_livre_titles_dict(self, avis_simple, critiques_simple):
        """livre_titles doit mapper livre_oid → titre."""
        globs = run_dataset(avis_simple, critiques_simple)

        livre_titles = globs["livre_titles"]
        assert livre_titles[OID_LIVRE_1] == "Combats de filles"
        assert livre_titles[OID_LIVRE_2] == "Mon deuxième livre"


# ── Tests : split train/test ──────────────────────────────────────────────────


class TestTrainTestSplit:
    """df_train et df_test doivent couvrir tous les avis sans duplication."""

    def test_split_couvre_tous_les_avis(self, critiques_simple):
        """df_train + df_test = df (pas de perte, pas de duplication)."""
        # 10 avis pour avoir un split 80/20 significatif
        avis_docs = [
            {
                "_id": ObjectId(),
                "critique_oid": OID_VIVIANT if i % 2 == 0 else OID_PHILIPPE,
                "livre_oid": f"livre_oid_{i:024d}",
                "note": float(5 + (i % 5)),
                "critique_nom_extrait": "Arnaud Viviant"
                if i % 2 == 0
                else "Elisabeth Philippe",
                "livre_titre_extrait": f"Livre {i}",
            }
            for i in range(10)
        ]
        globs = run_dataset(avis_docs, critiques_simple)

        total = len(globs["df"])
        assert len(globs["df_train"]) + len(globs["df_test"]) == total

    def test_split_stratifie_par_critique(self):
        """GroupShuffleSplit split par critique (groupe), pas par avis individuel.

        Avec 5 critiques à volumes égaux (test_size=0.2), on s'attend à 1 critique
        dans le test set et 4 dans le train set → ratio ~20%.
        """
        # 5 critiques avec 10 avis chacun = 50 avis au total
        # OIDs valides : 24 caractères hexadécimaux
        oids = [f"{i:024x}" for i in range(1, 6)]
        critiques_docs = [
            {"_id": ObjectId(oid), "nom": f"Critique {i}"} for i, oid in enumerate(oids)
        ]
        avis_docs = [
            {
                "_id": ObjectId(),
                "critique_oid": oid,
                "livre_oid": f"{(i * 100 + j):024x}",
                "note": float(5 + (j % 5)),
                "critique_nom_extrait": f"Critique {i}",
                "livre_titre_extrait": f"Livre {i}-{j}",
            }
            for i, oid in enumerate(oids)
            for j in range(10)
        ]
        globs = run_dataset(avis_docs, critiques_docs)

        total = len(globs["df"])
        ratio_test = len(globs["df_test"]) / total
        # GroupShuffleSplit avec 5 groupes et test_size=0.2 → 1 groupe en test = 20%
        assert 0.15 <= ratio_test <= 0.30, (
            f"Ratio test attendu ~20% (1 critique sur 5), obtenu {ratio_test:.0%}"
        )
