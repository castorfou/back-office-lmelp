"""Corriger les Passages d'une émission (Issue #427, tranche 4).

Les règles reprennent le prototype validé « Correction des passages » (#398,
#400, #401) : deux Passages voisins partagent une frontière, toute correction
passe le Passage en `corrige` et retire la validation de l'émission, un livre
sans Passage se dépose sur un trou. Routes réelles, vrai `mongodb_service` sur
mongomock, témoin du 15/11/2026.
"""

import json
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import patch

import mongomock
import pytest
from fastapi.testclient import TestClient


FIXTURE = Path(__file__).parent / "fixtures" / "passages" / "temoin_2026-11-15.json"
TEMOIN = json.loads(FIXTURE.read_text())
# une borne se pose à l'heure exacte d'un Segment : début ou fin d'une phrase
PHRASES = [
    (debut, fin) for debut, fin, texte in TEMOIN["segments"] if texte.strip(" .")
]
DEBUTS: list[int] = sorted({debut for debut, _ in PHRASES})
FINS: list[int] = sorted({fin for _, fin in PHRASES})


def phrase_avant(ms: int, rang: int = 1) -> int:
    """Début de la rang-ième phrase qui commence avant `ms`."""
    return [d for d in DEBUTS if d < ms][-rang]


def phrase_apres(ms: int, rang: int = 1) -> int:
    """Début de la rang-ième phrase qui commence après `ms`."""
    return [d for d in DEBUTS if d > ms][rang - 1]


def fin_de_phrase_apres(ms: int) -> int:
    return next(f for f in FINS if f > ms)


@pytest.fixture
def db() -> Iterator[Any]:
    from back_office_lmelp.services.mongodb_service import mongodb_service

    base: Any = mongomock.MongoClient().db
    collections: dict[str, Any] = {
        "db": base,
        "episodes_collection": base.episodes,
        "avis_critiques_collection": base.avis_critiques,
        "livresauteurs_cache_collection": base.livresauteurs_cache,
        "livres_collection": base.livres,
    }
    with patch.multiple(mongodb_service, **collections):
        yield base


@pytest.fixture
def client(db: Any) -> TestClient:
    from back_office_lmelp.app import app

    return TestClient(app)


@pytest.fixture
def episode(db: Any) -> str:
    from back_office_lmelp.services.passages_service import passages_service

    oid = str(
        db.episodes.insert_one(
            {"titre": "Le Masque du 15/11/2026", "date": datetime(2026, 11, 15)}
        ).inserted_id
    )
    db.avis_critiques.insert_one({"episode_oid": oid, "summary": TEMOIN["resume"]})
    whisper = {
        "transcription": [
            {"offsets": {"from": debut, "to": fin}, "text": texte}
            for debut, fin, texte in TEMOIN["segments"]
        ]
    }
    passages_service.enregistrer_segments(oid, whisper)
    return oid


def lire(client: TestClient, episode: str) -> dict[str, Any]:
    return dict(client.get(f"/api/episodes/{episode}/passages?segments=false").json())


def passage(client: TestClient, episode: str, titre: str) -> dict[str, Any]:
    return next(p for p in lire(client, episode)["passages"] if p["titre"] == titre)


def test_avancer_le_debut_d_un_passage_deplace_la_fin_du_precedent(client, episode):
    paradisi = passage(client, episode, "Paradisi Gloria")
    nouveau_debut = phrase_avant(paradisi["debut_ms"], 3)

    response = client.patch(
        f"/api/passages/{paradisi['id']}/debut", json={"debut_ms": nouveau_debut}
    )

    assert response.status_code == 200
    fondateur = passage(client, episode, "Le Fondateur")
    paradisi = passage(client, episode, "Paradisi Gloria")
    assert paradisi["debut_ms"] == nouveau_debut
    assert fondateur["fin_ms"] == nouveau_debut
    assert paradisi["origine"] == fondateur["origine"] == "corrige"


def test_reculer_la_fin_d_un_passage_deplace_le_debut_du_suivant(client, episode):
    fondateur = passage(client, episode, "Le Fondateur")
    nouvelle_fin = fin_de_phrase_apres(fondateur["fin_ms"] + 10_000)

    client.patch(f"/api/passages/{fondateur['id']}/fin", json={"fin_ms": nouvelle_fin})

    assert passage(client, episode, "Paradisi Gloria")["debut_ms"] == nouvelle_fin


def test_un_trou_entre_deux_passages_reste_un_trou(client, db, episode):
    paradisi = passage(client, episode, "Paradisi Gloria")
    # un trou de 30 s sépare les deux Passages (une borne posée à la main
    # déplacerait aussi le voisin, puisqu'ils se touchent)
    db.passages.update_one(
        {"titre": "Le Fondateur"}, {"$set": {"fin_ms": paradisi["debut_ms"] - 30_000}}
    )

    client.patch(
        f"/api/passages/{paradisi['id']}/debut",
        json={"debut_ms": phrase_avant(paradisi["debut_ms"], 2)},
    )

    assert (
        passage(client, episode, "Le Fondateur")["fin_ms"]
        == paradisi["debut_ms"] - 30_000
    )


@pytest.mark.parametrize(
    "borne,valeur",
    [
        ("debut", "apres_la_fin"),
        ("debut", "avant_le_precedent"),
        ("fin", "avant_le_debut"),
        ("fin", "apres_le_suivant"),
    ],
)
def test_une_borne_qui_casserait_l_ordre_est_refusee(client, episode, borne, valeur):
    fondateur = passage(client, episode, "Le Fondateur")
    paradisi = passage(client, episode, "Paradisi Gloria")
    grandes = passage(client, episode, "Dans les grandes lignes")
    cas = {
        "apres_la_fin": (paradisi, paradisi["fin_ms"] + 1),
        "avant_le_precedent": (paradisi, fondateur["debut_ms"] - 1),
        "avant_le_debut": (paradisi, paradisi["debut_ms"] - 1),
        "apres_le_suivant": (paradisi, grandes["fin_ms"] + 1),
    }
    cible, ms = cas[valeur]

    response = client.patch(
        f"/api/passages/{cible['id']}/{borne}", json={f"{borne}_ms": ms}
    )

    assert response.status_code == 422
    assert passage(client, episode, "Paradisi Gloria") == paradisi


def test_un_passage_inconnu_repond_404(client):
    response = client.patch(
        "/api/passages/6af98629a3c9beafb9dcb702/debut", json={"debut_ms": 0}
    )

    assert response.status_code == 404


def test_une_correction_retire_la_validation_de_l_emission(client, db, episode):
    from bson import ObjectId

    db.episodes.update_one(
        {"_id": ObjectId(episode)},
        {"$set": {"passages_valides_le": datetime(2026, 11, 20)}},
    )
    fondateur = passage(client, episode, "Le Fondateur")

    client.patch(
        f"/api/passages/{fondateur['id']}/debut",
        json={"debut_ms": phrase_apres(fondateur["debut_ms"])},
    )

    assert "passages_valides_le" not in db.episodes.find_one({"_id": ObjectId(episode)})


def test_supprimer_un_passage_le_garde_pour_qu_il_puisse_revenir(client, episode):
    vivre = passage(client, episode, "Vivre après")

    response = client.post(f"/api/passages/{vivre['id']}/supprimer")

    assert response.status_code == 200
    data = lire(client, episode)
    assert "Vivre après" not in [p["titre"] for p in data["passages"]]
    assert [s["titre"] for s in data["supprimes"]] == ["Vivre après"]
    absent = next(s for s in data["sans_passage"] if s["titre"] == "Vivre après")
    assert absent["raison"] == "supprime"


def test_un_passage_supprime_n_est_pas_recree_par_un_recalcul(client, episode):
    from back_office_lmelp.services.passages_service import passages_service

    vivre = passage(client, episode, "Vivre après")
    client.post(f"/api/passages/{vivre['id']}/supprimer")

    passages_service.recalculer(episode)

    assert "Vivre après" not in [p["titre"] for p in lire(client, episode)["passages"]]


def test_restaurer_un_passage_le_rend_sans_chevauchement(client, episode):
    vivre = passage(client, episode, "Vivre après")
    client.post(f"/api/passages/{vivre['id']}/supprimer")
    # pendant ce temps, le Passage précédent a été étendu sur son temps
    souterrains = passage(client, episode, "Le Livre des souterrains")
    client.patch(
        f"/api/passages/{souterrains['id']}/fin",
        json={"fin_ms": fin_de_phrase_apres(vivre["fin_ms"] - 20_000)},
    )

    client.post(f"/api/passages/{vivre['id']}/restaurer")

    passages = lire(client, episode)["passages"]
    for avant, apres in zip(passages, passages[1:], strict=False):
        assert avant["fin_ms"] <= apres["debut_ms"]
    assert "Vivre après" in [p["titre"] for p in passages]


@pytest.fixture
def trou(client: TestClient, db: Any, episode: str) -> dict[str, int]:
    """« Vivre après » non repéré : son temps devient un trou entre ses voisins."""
    vivre = passage(client, episode, "Vivre après")
    db.passages.delete_one({"titre": "Vivre après"})
    return {"debut_ms": vivre["debut_ms"], "fin_ms": vivre["fin_ms"]}


def deposer(client: TestClient, episode: str, trou: dict[str, int]) -> Any:
    return client.post(
        f"/api/episodes/{episode}/passages", json={"titre": "Vivre après", **trou}
    )


def test_un_livre_sans_passage_se_depose_sur_un_trou(client, episode, trou):
    assert "Vivre après" in [s["titre"] for s in lire(client, episode)["sans_passage"]]

    response = deposer(client, episode, trou)

    assert response.status_code == 200
    vivre = passage(client, episode, "Vivre après")
    assert (vivre["debut_ms"], vivre["fin_ms"]) == (trou["debut_ms"], trou["fin_ms"])
    assert vivre["origine"] == "corrige"
    assert vivre["place_main"] is True
    assert "Vivre après" not in [
        s["titre"] for s in lire(client, episode)["sans_passage"]
    ]


def test_un_livre_ne_se_depose_pas_sur_un_autre_passage(client, episode, trou):
    fondateur = passage(client, episode, "Le Fondateur")

    response = deposer(
        client, episode, {"debut_ms": fondateur["debut_ms"], "fin_ms": trou["fin_ms"]}
    )

    assert response.status_code == 422


def test_un_titre_qui_a_deja_un_passage_ne_se_depose_pas(client, episode, trou):
    response = client.post(
        f"/api/episodes/{episode}/passages", json={"titre": "Le Fondateur", **trou}
    )

    assert response.status_code == 422


@pytest.mark.parametrize("mode", ["tete", "fin"])
def test_un_livre_place_prend_une_moitie_du_trou_coupee_a_une_phrase(
    client, episode, trou, mode
):
    deposer(client, episode, trou)
    vivre = passage(client, episode, "Vivre après")

    response = client.patch(f"/api/passages/{vivre['id']}/occuper", json={"mode": mode})

    assert response.status_code == 200
    vivre = passage(client, episode, "Vivre après")
    debuts_de_phrase = {debut for debut, _, _ in TEMOIN["segments"]}
    if mode == "tete":
        assert vivre["debut_ms"] == trou["debut_ms"]
        assert vivre["fin_ms"] in debuts_de_phrase
    else:
        assert vivre["fin_ms"] == trou["fin_ms"]
        assert vivre["debut_ms"] in debuts_de_phrase
    milieu = (trou["debut_ms"] + trou["fin_ms"]) / 2
    coupe = vivre["fin_ms"] if mode == "tete" else vivre["debut_ms"]
    assert abs(coupe - milieu) < 15_000


def test_un_livre_place_reprend_tout_le_trou(client, episode, trou):
    deposer(client, episode, trou)
    vivre = passage(client, episode, "Vivre après")
    client.patch(f"/api/passages/{vivre['id']}/occuper", json={"mode": "tete"})

    client.patch(f"/api/passages/{vivre['id']}/occuper", json={"mode": "tout"})

    vivre = passage(client, episode, "Vivre après")
    assert (vivre["debut_ms"], vivre["fin_ms"]) == (trou["debut_ms"], trou["fin_ms"])


def test_un_livre_place_se_remet_a_placer(client, episode, trou):
    deposer(client, episode, trou)
    vivre = passage(client, episode, "Vivre après")

    response = client.post(f"/api/passages/{vivre['id']}/remettre")

    assert response.status_code == 200
    data = lire(client, episode)
    assert "Vivre après" not in [p["titre"] for p in data["passages"]]
    assert "Vivre après" in [s["titre"] for s in data["sans_passage"]]


def test_un_passage_repere_ne_se_remet_pas_a_placer(client, episode):
    fondateur = passage(client, episode, "Le Fondateur")

    assert client.post(f"/api/passages/{fondateur['id']}/remettre").status_code == 422


def test_valider_les_passages_d_une_emission_puis_retirer_la_validation(
    client, episode
):
    assert lire(client, episode)["valide"] is False

    assert (
        client.post(f"/api/episodes/{episode}/passages/validation").status_code == 200
    )
    assert lire(client, episode)["valide"] is True

    assert (
        client.delete(f"/api/episodes/{episode}/passages/validation").status_code == 200
    )
    assert lire(client, episode)["valide"] is False


def test_une_correction_apres_validation_fait_repasser_l_emission_a_verifier(
    client, episode
):
    client.post(f"/api/episodes/{episode}/passages/validation")
    fondateur = passage(client, episode, "Le Fondateur")

    data = client.patch(
        f"/api/passages/{fondateur['id']}/debut",
        json={"debut_ms": phrase_apres(fondateur["debut_ms"])},
    ).json()

    assert data["valide"] is False


def test_chaque_emission_a_sa_pastille(client, db, episode):
    sans_segments = str(db.episodes.insert_one({"titre": "Ancienne"}).inserted_id)
    validee = str(db.episodes.insert_one({"titre": "Vérifiée"}).inserted_id)
    db.episode_segments.insert_one(
        {
            "episode_oid": validee,
            "segments": [{"debut_ms": 0, "fin_ms": 1, "texte": "a"}],
        }
    )
    client.post(f"/api/episodes/{validee}/passages/validation")

    statuts = client.get("/api/passages/statuts").json()

    assert statuts[episode] == "a_verifier"
    assert statuts[validee] == "valide"
    assert sans_segments not in statuts  # sans Segments : pastille 🔴 par défaut


@pytest.mark.parametrize("borne", ["debut", "fin"])
def test_une_borne_au_milieu_d_une_phrase_est_refusee(client, episode, borne):
    paradisi = passage(client, episode, "Paradisi Gloria")
    milieu_de_phrase = phrase_apres(paradisi["debut_ms"], 3) + 333

    response = client.patch(
        f"/api/passages/{paradisi['id']}/{borne}",
        json={f"{borne}_ms": milieu_de_phrase},
    )

    assert response.status_code == 422


def test_restaurer_un_passage_marque_corrige_le_voisin_qu_il_raccourcit(
    client, db, episode
):
    vivre = passage(client, episode, "Vivre après")
    client.post(f"/api/passages/{vivre['id']}/supprimer")
    # le voisin, resté automatique, s'étend sur le temps du Passage supprimé
    db.passages.update_one(
        {"titre": "Le Livre des souterrains"},
        {"$set": {"fin_ms": fin_de_phrase_apres(vivre["fin_ms"] - 20_000)}},
    )
    assert passage(client, episode, "Le Livre des souterrains")["origine"] == "auto"

    client.post(f"/api/passages/{vivre['id']}/restaurer")

    souterrains = passage(client, episode, "Le Livre des souterrains")
    assert souterrains["fin_ms"] == vivre["debut_ms"]
    assert souterrains["origine"] == "corrige"


def test_les_bornes_d_un_passage_supprime_ne_se_corrigent_pas(client, episode):
    vivre = passage(client, episode, "Vivre après")
    client.post(f"/api/passages/{vivre['id']}/supprimer")

    response = client.patch(
        f"/api/passages/{vivre['id']}/debut", json={"debut_ms": vivre["debut_ms"]}
    )

    assert response.status_code == 422


@pytest.mark.parametrize("episode_id", ["6af98629a3c9beafb9dcb702", "pas-un-id"])
def test_valider_une_emission_inconnue_repond_404(client, episode_id):
    assert (
        client.post(f"/api/episodes/{episode_id}/passages/validation").status_code
        == 404
    )


def test_un_livre_ne_se_depose_pas_hors_d_un_trou(client, episode, trou):
    derniere_fin = lire(client, episode)["passages"][-1]["fin_ms"]

    response = deposer(
        client,
        episode,
        {"debut_ms": derniere_fin, "fin_ms": fin_de_phrase_apres(derniere_fin)},
    )

    assert response.status_code == 422


def test_un_livre_depose_va_jusqu_a_la_fin_du_trou(client, episode, trou):
    response = deposer(
        client,
        episode,
        {"debut_ms": trou["debut_ms"], "fin_ms": phrase_avant(trou["fin_ms"], 2)},
    )

    assert response.status_code == 422


def test_un_livre_depose_peut_commencer_a_une_phrase_du_trou(client, episode, trou):
    debut = phrase_apres(trou["debut_ms"], 3)

    response = deposer(client, episode, {"debut_ms": debut, "fin_ms": trou["fin_ms"]})

    assert response.status_code == 200
    assert passage(client, episode, "Vivre après")["debut_ms"] == debut


def test_les_corrections_survivent_a_un_recalcul(client, episode, trou):
    from back_office_lmelp.services.passages_service import passages_service

    deposer(client, episode, trou)
    paradisi = passage(client, episode, "Paradisi Gloria")
    nouveau_debut = phrase_avant(paradisi["debut_ms"], 3)
    client.patch(
        f"/api/passages/{paradisi['id']}/debut", json={"debut_ms": nouveau_debut}
    )

    def sans_id(passages: list[dict]) -> list[dict]:
        return [{k: v for k, v in p.items() if k != "id"} for p in passages]

    avant = sans_id(lire(client, episode)["passages"])

    passages_service.recalculer(episode)

    # les Passages automatiques sont refaits (nouveaux id), les corrections restent
    assert sans_id(lire(client, episode)["passages"]) == avant
