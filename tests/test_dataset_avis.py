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


# Chemin du script relatif à ce fichier de test (tests/ -> .. -> notebooks/)
DATASET_SCRIPT = Path(__file__).resolve().parents[1] / "notebooks" / "dataset_avis.py"


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
    """Deux critiques avec 10 avis chacun (seuil minimum pour le filtrage CF)."""
    docs = []
    # Arnaud Viviant : 10 avis
    for i in range(10):
        docs.append(
            {
                "_id": ObjectId(),
                "critique_oid": OID_VIVIANT,
                "livre_oid": f"livre_v_{i:024d}",
                "note": 8 if i == 0 else 7,
                "critique_nom_extrait": "Arnaud Viviant",
                "livre_titre_extrait": "Combats de filles" if i == 0 else f"Livre V{i}",
            }
        )
    # Elisabeth Philippe : 10 avis
    for i in range(10):
        docs.append(
            {
                "_id": ObjectId(),
                "critique_oid": OID_PHILIPPE,
                "livre_oid": f"livre_p_{i:024d}",
                "note": 9 if i == 0 else 7,
                "critique_nom_extrait": "Elisabeth Philippe",
                "livre_titre_extrait": "Mon deuxième livre"
                if i == 0
                else f"Livre P{i}",
            }
        )
    return docs


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
        # 10 avis par critique pour dépasser le seuil MIN_AVIS_PAR_CRITIQUE
        avis_docs = []
        for i in range(5):
            avis_docs.append(
                {
                    "_id": ObjectId(),
                    "critique_oid": OID_NEUHOFF,
                    "livre_oid": f"{i:024x}",
                    "note": 7,
                    "critique_nom_extrait": "Eric Neuhoff",  # sans accent (ancien)
                    "livre_titre_extrait": f"Livre A{i}",
                }
            )
        for i in range(5, 10):
            avis_docs.append(
                {
                    "_id": ObjectId(),
                    "critique_oid": OID_NEUHOFF,
                    "livre_oid": f"{i:024x}",
                    "note": 8,
                    "critique_nom_extrait": "Éric Neuhoff",  # avec accent (récent)
                    "livre_titre_extrait": f"Livre B{i}",
                }
            )
        for i in range(10):
            avis_docs.append(
                {
                    "_id": ObjectId(),
                    "critique_oid": OID_VIVIANT,
                    "livre_oid": f"{100 + i:024x}",
                    "note": 9,
                    "critique_nom_extrait": "Arnaud Viviant",
                    "livre_titre_extrait": f"Livre C{i}",
                }
            )
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

    MIN_AVIS = 10  # seuil défini dans dataset_avis.py

    def _avis_deux_critiques(
        self, notes_viviant: list, notes_philippe: list
    ) -> list[dict]:
        """Helper : crée des avis pour deux critiques.

        Complète automatiquement jusqu'à MIN_AVIS avis valides (note=7) par critique
        afin que le filtrage CF n'exclue pas les critiques testés.
        Les notes passées en paramètre sont ajoutées EN PREMIER, puis des avis
        de remplissage avec note=7 sont ajoutés pour atteindre le seuil.
        """
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
        # Compléter Viviant jusqu'au seuil avec des avis valides
        n_viviant = len(notes_viviant)
        for i in range(n_viviant, self.MIN_AVIS + n_viviant):
            docs.append(
                {
                    "_id": ObjectId(),
                    "critique_oid": OID_VIVIANT,
                    "livre_oid": f"livre_vx_{i:024d}",
                    "note": 7,
                    "critique_nom_extrait": "Arnaud Viviant",
                    "livre_titre_extrait": f"Livre VX{i}",
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
        # Compléter Philippe jusqu'au seuil avec des avis valides
        n_philippe = len(notes_philippe)
        for i in range(n_philippe, self.MIN_AVIS + n_philippe):
            docs.append(
                {
                    "_id": ObjectId(),
                    "critique_oid": OID_PHILIPPE,
                    "livre_oid": f"livre_px_{i:024d}",
                    "note": 7,
                    "critique_nom_extrait": "Elisabeth Philippe",
                    "livre_titre_extrait": f"Livre PX{i}",
                }
            )
        return docs

    def test_notes_valides_conservees(self, critiques_simple):
        """Notes 1 à 10 inclus sont toutes conservées."""
        # 3 notes testées + 10 remplissage = 13 avis pour Viviant, 1+10=11 pour Philippe
        avis_docs = self._avis_deux_critiques([1, 5, 10], [7])
        globs = run_dataset(avis_docs, critiques_simple)
        # 3 + 10 (Viviant) + 1 + 10 (Philippe) = 24 avis valides
        assert len(globs["df"]) == 24

    def test_note_zero_exclue(self, critiques_simple):
        """Note 0 (Calibre non noté) est exclue."""
        # [0, 8] → 2 avis + 10 remplissage = 12 pour Viviant
        # [7] → 1 avis + 10 remplissage = 11 pour Philippe
        # note=0 exclue → (12 - 1) + 11 = 22 avis conservés
        avis_docs = self._avis_deux_critiques([0, 8], [7])
        globs = run_dataset(avis_docs, critiques_simple)
        assert len(globs["df"]) == 22
        assert 0.0 not in globs["df"]["note"].tolist()

    def test_note_manquante_exclue(self, critiques_simple):
        """Avis sans note (None/NaN) est exclu."""
        # [None, 7] → 2 avis + 10 remplissage = 12 pour Viviant
        # [6] → 1 avis + 10 remplissage = 11 pour Philippe
        # note=None exclue → (12 - 1) + 11 = 22 avis conservés
        avis_docs = self._avis_deux_critiques([None, 7], [6])
        globs = run_dataset(avis_docs, critiques_simple)
        assert len(globs["df"]) == 22

    def test_note_hors_echelle_exclue(self, critiques_simple):
        """Note > 10 est exclue."""
        # [11, 7] → 2 avis + 10 remplissage = 12 pour Viviant
        # [8, 9] → 2 avis + 10 remplissage = 12 pour Philippe
        # note=11 exclue → (12 - 1) + 12 = 23 avis conservés
        avis_docs = self._avis_deux_critiques([11, 7], [8, 9])
        globs = run_dataset(avis_docs, critiques_simple)
        assert len(globs["df"]) == 23
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

        assert globs["n_avis"] == 20  # 10 avis par critique × 2 critiques
        assert globs["n_critiques"] == 2
        assert globs["n_livres"] == 20

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
        # Premier livre de Viviant et de Philippe (générés par la fixture avis_simple)
        assert livre_titles["livre_v_000000000000000000000000"] == "Combats de filles"
        assert livre_titles["livre_p_000000000000000000000000"] == "Mon deuxième livre"


# ── Tests : filtrage des critiques avec trop peu d'avis ──────────────────────


class TestFiltrageMinAvis:
    """Les critiques avec moins de MIN_AVIS_PAR_CRITIQUE avis doivent être exclus du dataset CF."""

    def test_critique_avec_moins_de_10_avis_exclu(self):
        """Un critique avec seulement 5 avis est exclu du dataset final."""
        # Trois critiques : deux avec ≥10 avis, un avec 5 avis seulement
        oids = [f"{i:024x}" for i in range(1, 4)]
        critiques_docs = [
            {"_id": ObjectId(oid), "nom": f"Critique {i}"} for i, oid in enumerate(oids)
        ]

        avis_docs = []
        # Critique 0 : 10 avis (conservé)
        for j in range(10):
            avis_docs.append(
                {
                    "_id": ObjectId(),
                    "critique_oid": oids[0],
                    "livre_oid": f"{j:024x}",
                    "note": 7.0,
                    "critique_nom_extrait": "Critique 0",
                    "livre_titre_extrait": f"Livre 0-{j}",
                }
            )
        # Critique 1 : 5 avis seulement (exclu)
        for j in range(5):
            avis_docs.append(
                {
                    "_id": ObjectId(),
                    "critique_oid": oids[1],
                    "livre_oid": f"{100 + j:024x}",
                    "note": 8.0,
                    "critique_nom_extrait": "Critique 1",
                    "livre_titre_extrait": f"Livre 1-{j}",
                }
            )
        # Critique 2 : 12 avis (conservé)
        for j in range(12):
            avis_docs.append(
                {
                    "_id": ObjectId(),
                    "critique_oid": oids[2],
                    "livre_oid": f"{200 + j:024x}",
                    "note": 6.0,
                    "critique_nom_extrait": "Critique 2",
                    "livre_titre_extrait": f"Livre 2-{j}",
                }
            )

        globs = run_dataset(avis_docs, critiques_docs)
        df = globs["df"]

        # Critique 1 (5 avis) doit être absent
        assert oids[1] not in df["critique_oid"].values, (
            "Le critique avec 5 avis ne doit pas apparaître dans df"
        )
        # Critiques 0 et 2 doivent être présents
        assert oids[0] in df["critique_oid"].values
        assert oids[2] in df["critique_oid"].values

    def test_critique_avec_exactement_10_avis_conserve(self):
        """Un critique avec exactement 10 avis est conservé (seuil inclusif)."""
        oids = [f"{i:024x}" for i in range(1, 3)]
        critiques_docs = [
            {"_id": ObjectId(oid), "nom": f"Critique {i}"} for i, oid in enumerate(oids)
        ]

        avis_docs = []
        for c_idx, oid in enumerate(oids):
            for j in range(10):  # exactement 10 avis chacun
                avis_docs.append(
                    {
                        "_id": ObjectId(),
                        "critique_oid": oid,
                        "livre_oid": f"{c_idx * 100 + j:024x}",
                        "note": 7.0,
                        "critique_nom_extrait": f"Critique {c_idx}",
                        "livre_titre_extrait": f"Livre {c_idx}-{j}",
                    }
                )

        globs = run_dataset(avis_docs, critiques_docs)
        df = globs["df"]

        assert oids[0] in df["critique_oid"].values
        assert oids[1] in df["critique_oid"].values
        assert len(df) == 20  # 10 + 10 avis

    def test_n_critiques_reflète_filtrage(self):
        """n_critiques doit compter uniquement les critiques retenus après filtrage."""
        oids = [f"{i:024x}" for i in range(1, 4)]
        critiques_docs = [
            {"_id": ObjectId(oid), "nom": f"Critique {i}"} for i, oid in enumerate(oids)
        ]

        avis_docs = []
        for j in range(15):  # critique 0 : 15 avis
            avis_docs.append(
                {
                    "_id": ObjectId(),
                    "critique_oid": oids[0],
                    "livre_oid": f"{j:024x}",
                    "note": 7.0,
                    "critique_nom_extrait": "Critique 0",
                    "livre_titre_extrait": f"Livre 0-{j}",
                }
            )
        for j in range(3):  # critique 1 : 3 avis → exclu
            avis_docs.append(
                {
                    "_id": ObjectId(),
                    "critique_oid": oids[1],
                    "livre_oid": f"{100 + j:024x}",
                    "note": 8.0,
                    "critique_nom_extrait": "Critique 1",
                    "livre_titre_extrait": f"Livre 1-{j}",
                }
            )
        for j in range(10):  # critique 2 : 10 avis
            avis_docs.append(
                {
                    "_id": ObjectId(),
                    "critique_oid": oids[2],
                    "livre_oid": f"{200 + j:024x}",
                    "note": 6.0,
                    "critique_nom_extrait": "Critique 2",
                    "livre_titre_extrait": f"Livre 2-{j}",
                }
            )

        globs = run_dataset(avis_docs, critiques_docs)

        assert globs["n_critiques"] == 2, (
            f"Attendu 2 critiques (critique 1 exclu), obtenu {globs['n_critiques']}"
        )


# ── Tests : split train/test ──────────────────────────────────────────────────


class TestTrainTestSplit:
    """df_train et df_test doivent couvrir tous les avis sans duplication."""

    def test_split_couvre_tous_les_avis(self, critiques_simple):
        """df_train + df_test = df (pas de perte, pas de duplication)."""
        # 20 avis (10 par critique) pour dépasser le seuil MIN_AVIS_PAR_CRITIQUE=10
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
            for i in range(20)
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
