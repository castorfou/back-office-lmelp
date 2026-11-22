"""Tests du comptage des émissions livrées par lmelp-pap (Issue #376).

Les fiches suivent le contrat `pap_remises` de lmelp-pap : `_id` est une
chaîne (URL de l'enregistrement pap), `audio_rel_filename` est relatif au
dossier audio du back-office (`<année>/<nom>`), `date_remise` une date UTC.
"""

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock

from back_office_lmelp.services.pap_remises_service import count_livrees


def _fiche(audio_rel_filename: str, n: int = 1) -> dict:
    return {
        "_id": f"https://pap.example/enregistrements/{n}",
        "audio_rel_filename": audio_rel_filename,
        "date_remise": datetime(2026, 11, 20, 10, 0, tzinfo=UTC),
    }


def _collection(fiches: list[dict]) -> MagicMock:
    collection = MagicMock()
    collection.find.return_value = iter(fiches)
    return collection


def _audio(root: Path, rel: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"audio")


def test_compte_seulement_les_fiches_dont_le_fichier_est_present(tmp_path):
    _audio(tmp_path, "1987/masque_1987-03-01.m4a")
    collection = _collection(
        [
            _fiche("1987/masque_1987-03-01.m4a", 1),
            _fiche("1990/masque_1990-05-06.m4a", 2),
        ]
    )

    assert count_livrees(collection, str(tmp_path)) == 1


def test_ne_compte_pas_les_audios_presents_sans_fiche_pap(tmp_path):
    """Le dossier audio contient aussi les épisodes RSS : seuls comptent ceux
    qui ont une fiche pap."""
    _audio(tmp_path, "1987/masque_1987-03-01.m4a")
    _audio(tmp_path, "2025/episode_rss_1.mp3")
    _audio(tmp_path, "2025/episode_rss_2.mp3")
    collection = _collection([_fiche("1987/masque_1987-03-01.m4a")])

    assert count_livrees(collection, str(tmp_path)) == 1


def test_logue_une_ligne_par_fichier_absent(tmp_path, caplog):
    _audio(tmp_path, "1987/present.m4a")
    collection = _collection(
        [
            _fiche("1987/present.m4a", 1),
            _fiche("1990/absent_a.m4a", 2),
            _fiche("1991/absent_b.m4a", 3),
        ]
    )

    with caplog.at_level("WARNING"):
        count_livrees(collection, str(tmp_path))

    messages = [r.getMessage() for r in caplog.records]
    assert messages == [
        "fiche pap https://pap.example/enregistrements/2 : fichier absent dans "
        f"{tmp_path}/1990/absent_a.m4a",
        "fiche pap https://pap.example/enregistrements/3 : fichier absent dans "
        f"{tmp_path}/1991/absent_b.m4a",
    ]


def test_collection_vide_ou_absente_renvoie_zero_sans_log(tmp_path, caplog):
    """Une collection Mongo absente se lit comme une collection vide."""
    with caplog.at_level("WARNING"):
        assert count_livrees(_collection([]), str(tmp_path)) == 0
    assert caplog.records == []


def test_fiche_sans_audio_rel_filename_non_comptee_et_loguee(tmp_path, caplog):
    _audio(tmp_path, "1987/present.m4a")
    fiche = _fiche("1987/present.m4a", 7)
    del fiche["audio_rel_filename"]

    with caplog.at_level("WARNING"):
        assert count_livrees(_collection([fiche]), str(tmp_path)) == 0
    assert "https://pap.example/enregistrements/7" in caplog.text


def test_un_dossier_au_nom_du_fichier_ne_compte_pas(tmp_path):
    (tmp_path / "1987" / "masque.m4a").mkdir(parents=True)
    collection = _collection([_fiche("1987/masque.m4a")])

    assert count_livrees(collection, str(tmp_path)) == 0


def test_lecture_seule_aucune_ecriture_sur_pap_remises(tmp_path):
    collection = _collection([_fiche("1990/absent.m4a")])

    count_livrees(collection, str(tmp_path))

    called = {name for name, _args, _kwargs in collection.method_calls}
    assert called == {"find"}
