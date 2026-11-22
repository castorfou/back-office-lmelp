"""Intégration des remises pap comme épisodes (Issue #378).

Les fiches suivent le contrat `pap_remises` de lmelp-pap (copié d'une fiche
réelle) : `_id` chaîne (URL de l'enregistrement), `date` datetime à 00:00,
`duree` entier ou nul, `episode_page_url` chaîne ou nulle, `sha256`
hexadécimal du fichier `<dossier audio>/<audio_rel_filename>`.

MongoDB, ntfy et le runner PGX sont simulés ; les fichiers audio sont réels.
"""

import asyncio
import hashlib
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from back_office_lmelp.services.pap_remises_service import (
    PapRemiseError,
    PapRemisesService,
)


def _remise_id(n: int) -> str:
    return f"https://media.radiofrance-podcast.net/podcast09/14007-{n}.m4a"


def _fiche(
    n: int, date: datetime, contenu: bytes = b"audio", **overrides: object
) -> dict:
    fiche = {
        "_id": _remise_id(n),
        "emission_id": date.strftime("%Y-%m-%d"),
        "titre": f"Le Masque et la Plume du {date:%d/%m/%Y}",
        "date": date,
        "type": "livres",
        "duree": 3287,
        "description": "durée : 00:54:47  - Le Masque et la Plume - par : "
        "Jérôme Garcin - équipe : Didier Lagarde, Lysiane Sellam",
        "sources_description": {"duree": "fichier", "animateur": "radiofrance"},
        "episode_page_url": "https://www.radiofrance.fr/franceinter/podcasts/"
        f"le-masque-et-la-plume/et-si-on-lisait-{n}",
        "url": _remise_id(n),
        "audio_rel_filename": f"{date:%Y}/14007-{n}.m4a",
        "sha256": hashlib.sha256(contenu).hexdigest(),
        "date_remise": datetime(2026, 11, 22, 10, 12, 59),
    }
    fiche.update(overrides)
    return fiche


def _audio(root: Path, fiche: dict, contenu: bytes = b"audio") -> None:
    path = root / fiche["audio_rel_filename"]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(contenu)


class FakeMongo:
    """Simule les deux lectures et l'unique écriture du service."""

    def __init__(self, fiches: list[dict], integrees: list[str] | None = None):
        self.remises = MagicMock()
        self.remises.find.side_effect = lambda *a, **k: iter(list(fiches))
        self.remises.find_one.side_effect = lambda filtre, *a, **k: next(
            (f for f in fiches if f["_id"] == filtre["_id"]), None
        )
        self.integrees = list(integrees or [])
        self.episodes_collection = MagicMock()
        self.episodes_collection.distinct.side_effect = lambda champ: list(
            self.integrees
        )
        self.inserted: list[dict] = []

    def get_collection(self, name: str) -> MagicMock:
        assert name == "pap_remises"
        return self.remises

    def insert_episode(self, episode: dict) -> str:
        self.inserted.append(episode)
        self.integrees.append(episode["pap_remise_id"])
        return "6af47e76a1c0d162e8518b99"  # pragma: allowlist secret


@pytest.fixture
def runner():
    runner = MagicMock()
    runner.start_transcription = AsyncMock(return_value={"status": "started"})
    return runner


@pytest.fixture
def notify():
    return AsyncMock()


def _service(
    mongo: FakeMongo,
    tmp_path: Path,
    runner: MagicMock | None = None,
    notify: AsyncMock | None = None,
) -> PapRemisesService:
    return PapRemisesService(
        mongodb_service=mongo,
        audio_root=str(tmp_path),
        transcription_runner=runner,
        notify=notify,
    )


# ── Liste des remises à intégrer ─────────────────────────────────────────────


def test_liste_les_remises_livrees_non_integrees_des_plus_recentes(tmp_path):
    f2015 = _fiche(1, datetime(2015, 1, 4))
    f2016 = _fiche(2, datetime(2016, 6, 5), duree=None, episode_page_url=None)
    f1990 = _fiche(3, datetime(1990, 5, 6))
    absente = _fiche(4, datetime(2016, 1, 1))
    integree = _fiche(5, datetime(2016, 12, 1))
    for fiche in (f2015, f2016, f1990, integree):
        _audio(tmp_path, fiche)
    mongo = FakeMongo(
        [f2015, f1990, absente, f2016, integree], integrees=[_remise_id(5)]
    )

    remises = _service(mongo, tmp_path).list_a_integrer()

    assert remises == [
        {
            "remise_id": _remise_id(2),
            "titre": "Le Masque et la Plume du 05/06/2016",
            "date": "2016-06-05",
            "duree": None,
            "description": f2016["description"],
            "episode_page_url": None,
        },
        {
            "remise_id": _remise_id(1),
            "titre": "Le Masque et la Plume du 04/01/2015",
            "date": "2015-01-04",
            "duree": 3287,
            "description": f2015["description"],
            "episode_page_url": f2015["episode_page_url"],
        },
        {
            "remise_id": _remise_id(3),
            "titre": "Le Masque et la Plume du 06/05/1990",
            "date": "1990-05-06",
            "duree": 3287,
            "description": f1990["description"],
            "episode_page_url": f1990["episode_page_url"],
        },
    ]


def test_le_compte_est_la_taille_de_la_liste_et_ne_logue_que_les_non_integrees(
    tmp_path, caplog
):
    presente = _fiche(1, datetime(2015, 1, 4))
    _audio(tmp_path, presente)
    absente = _fiche(2, datetime(2016, 6, 5))
    integree_dont_le_fichier_manque = _fiche(3, datetime(2016, 12, 1))
    mongo = FakeMongo(
        [presente, absente, integree_dont_le_fichier_manque],
        integrees=[_remise_id(3)],
    )

    with caplog.at_level("WARNING"):
        count = _service(mongo, tmp_path).count_a_integrer()

    assert count == 1
    assert [r.getMessage() for r in caplog.records] == [
        f"fiche pap {_remise_id(2)} : fichier absent dans {tmp_path}/2016/14007-2.m4a"
    ]


def test_ne_compte_pas_les_audios_presents_sans_fiche_ni_un_dossier(tmp_path):
    """Le dossier audio contient aussi les épisodes RSS."""
    (tmp_path / "2025").mkdir()
    (tmp_path / "2025" / "episode_rss.mp3").write_bytes(b"rss")
    dossier = _fiche(1, datetime(2015, 1, 4))
    (tmp_path / dossier["audio_rel_filename"]).mkdir(parents=True)
    sans_fichier = _fiche(2, datetime(2015, 2, 4))
    del sans_fichier["audio_rel_filename"]

    mongo = FakeMongo([dossier, sans_fichier])

    assert _service(mongo, tmp_path).count_a_integrer() == 0


# ── Intégration d'une remise ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_integration_insere_l_episode_notifie_et_lance_la_transcription(
    tmp_path, runner, notify
):
    fiche = _fiche(1, datetime(2016, 6, 5))
    _audio(tmp_path, fiche)
    mongo = FakeMongo([fiche])

    result = await _service(mongo, tmp_path, runner, notify).integrer(_remise_id(1))

    assert mongo.inserted == [
        {
            "titre": "Le Masque et la Plume du 05/06/2016",
            "date": datetime(2016, 6, 5),
            "type": "livres",
            "duree": 3287,
            "description": fiche["description"],
            "url": _remise_id(1),
            "audio_rel_filename": "2016/14007-1.m4a",
            "episode_page_url": fiche["episode_page_url"],
            "transcription": None,
            "masked": False,
            "source": "pap",
            "pap_remise_id": _remise_id(1),
        }
    ]
    notify.assert_awaited_once_with(
        "Nouvel épisode Le Masque et la Plume intégré — 05/06/16",
        "Le Masque et la Plume du 05/06/2016",
        prefix="pap",
    )
    runner.start_transcription.assert_awaited_once_with(trigger="api")
    assert result == {
        "episode_id": "6af47e76a1c0d162e8518b99",  # pragma: allowlist secret
        "remise_id": _remise_id(1),
        "titre": "Le Masque et la Plume du 05/06/2016",
        "date": "2016-06-05",
        "transcription_status": "started",
    }
    # La remise intégrée sort de la liste
    assert _service(mongo, tmp_path).list_a_integrer() == []


@pytest.mark.asyncio
async def test_un_echec_du_lancement_de_la_transcription_n_annule_pas_l_integration(
    tmp_path, runner, notify
):
    fiche = _fiche(1, datetime(2016, 6, 5))
    _audio(tmp_path, fiche)
    mongo = FakeMongo([fiche])
    runner.start_transcription.side_effect = OSError("PGX injoignable")

    result = await _service(mongo, tmp_path, runner, notify).integrer(_remise_id(1))

    assert result["transcription_status"] == "error"
    assert len(mongo.inserted) == 1
    assert mongo.inserted[0]["transcription"] is None


# ── Refus : aucun épisode inséré, aucune notification, aucune transcription ──


async def _refus(
    mongo: FakeMongo,
    tmp_path: Path,
    runner: MagicMock,
    notify: AsyncMock,
    remise_id: str,
) -> PapRemiseError:
    with pytest.raises(PapRemiseError) as exc_info:
        await _service(mongo, tmp_path, runner, notify).integrer(remise_id)
    assert mongo.inserted == []
    notify.assert_not_awaited()
    runner.start_transcription.assert_not_awaited()
    return exc_info.value


@pytest.mark.asyncio
async def test_refuse_une_remise_inconnue(tmp_path, runner, notify):
    mongo = FakeMongo([])

    error = await _refus(mongo, tmp_path, runner, notify, _remise_id(9))

    assert error.status_code == 404
    assert error.message == "Émission inconnue de lmelp-pap"


@pytest.mark.asyncio
async def test_refuse_une_remise_deja_integree_meme_si_son_episode_est_masque(
    tmp_path, runner, notify
):
    fiche = _fiche(1, datetime(2016, 6, 5))
    _audio(tmp_path, fiche)
    mongo = FakeMongo([fiche], integrees=[_remise_id(1)])

    error = await _refus(mongo, tmp_path, runner, notify, _remise_id(1))

    assert error.status_code == 409
    assert error.message == "Émission déjà intégrée"


@pytest.mark.asyncio
async def test_refuse_une_remise_dont_le_fichier_audio_est_absent(
    tmp_path, runner, notify
):
    mongo = FakeMongo([_fiche(1, datetime(2016, 6, 5))])

    error = await _refus(mongo, tmp_path, runner, notify, _remise_id(1))

    assert error.status_code == 422
    assert error.message == (
        "Fichier audio absent du dossier audio de lmelp : 2016/14007-1.m4a"
    )


@pytest.mark.asyncio
async def test_refuse_une_copie_dont_l_empreinte_differe_de_la_fiche(
    tmp_path, runner, notify
):
    """Une copie tronquée ou corrompue ne doit jamais partir en transcription."""
    fiche = _fiche(1, datetime(2016, 6, 5), contenu=b"audio complet")
    _audio(tmp_path, fiche, contenu=b"audio compl")
    mongo = FakeMongo([fiche])

    error = await _refus(mongo, tmp_path, runner, notify, _remise_id(1))

    assert error.status_code == 422
    assert error.message == (
        "Empreinte SHA-256 du fichier audio différente de celle donnée par "
        "lmelp-pap : copie incomplète ou corrompue"
    )


@pytest.mark.asyncio
async def test_un_double_clic_n_integre_jamais_deux_fois_la_meme_remise(
    tmp_path, runner, notify
):
    """Les deux appels se chevauchent pendant le calcul de l'empreinte."""
    fiche = _fiche(1, datetime(2016, 6, 5))
    _audio(tmp_path, fiche)
    mongo = FakeMongo([fiche])
    service = _service(mongo, tmp_path, runner, notify)

    results = await asyncio.gather(
        service.integrer(_remise_id(1)),
        service.integrer(_remise_id(1)),
        return_exceptions=True,
    )

    assert len(mongo.inserted) == 1
    refus = [r for r in results if isinstance(r, PapRemiseError)]
    assert [(e.status_code, e.message) for e in refus] == [
        (409, "Émission déjà intégrée")
    ]


@pytest.mark.asyncio
async def test_aucune_ecriture_dans_pap_remises(tmp_path, runner, notify):
    fiche = _fiche(1, datetime(2016, 6, 5))
    _audio(tmp_path, fiche)
    mongo = FakeMongo([fiche])
    service = _service(mongo, tmp_path, runner, notify)

    service.list_a_integrer()
    service.count_a_integrer()
    await service.integrer(_remise_id(1))

    called = {name for name, _args, _kwargs in mongo.remises.method_calls}
    assert called <= {"find", "find_one"}
