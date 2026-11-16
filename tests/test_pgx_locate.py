"""Localisation de PGX d'après son identité (Issue #362, ADR 0002).

Aucun test ne touche au réseau : un faux réseau répond aux connexions TCP
(port 22) et à `ssh-keyscan` selon une table adresse → clé d'hôte.
"""

import asyncio
from unittest.mock import patch

import pytest

from back_office_lmelp.services import pgx_service
from back_office_lmelp.services.pgx_service import locate_pgx, run_pgx_diagnostics


# Mêmes clés de test que tests/test_pgx_service.py (`ssh-keygen -t ed25519`)
PGX_KEY_B64 = "AAAAC3NzaC1lZDI1NTE5AAAAIFwHMNuxrSKMJxd5UALz3Cx8yg9E0sm0A/hDvHPwbA8d"  # pragma: allowlist secret
OTHER_KEY_B64 = "AAAAC3NzaC1lZDI1NTE5AAAAIFgWg0KeBqeXTeAPCfrOrt9g0Qh3B5QdfwCfI1b0DbUu"  # pragma: allowlist secret
PGX_HOST_KEY = f"ssh-ed25519 {PGX_KEY_B64} root@pgx"
PGX_FINGERPRINT = "SHA256:3lUWrXecKY6L1mZAIResebD/lOeIy3CuYex6u1hU9wU"


class _Process:
    def __init__(self, stdout: bytes, stderr: bytes) -> None:
        self.returncode = 0
        self._out = (stdout, stderr)

    async def communicate(self) -> tuple[bytes, bytes]:
        return self._out


class _HangingProcess:
    """ssh-keyscan qui ne rend jamais la main ; enregistre s'il a été tué."""

    def __init__(self) -> None:
        self.returncode = None
        self.killed = False

    async def communicate(self) -> tuple[bytes, bytes]:
        await asyncio.Event().wait()
        return b"", b""

    def kill(self) -> None:
        self.killed = True

    async def wait(self) -> int:
        return -9


class _Writer:
    def close(self) -> None:
        pass

    async def wait_closed(self) -> None:
        pass


class FakeNetwork:
    """Machines qui répondent sur le port 22, avec la clé d'hôte qu'elles présentent.

    Reproduit les sorties réelles : `ssh-keyscan -t ed25519 <ip>` écrit
    `<ip> ssh-ed25519 <b64>` sur stdout et la bannière en commentaire sur stderr ;
    une adresse sans machine refuse la connexion (« No route to host »).
    """

    def __init__(
        self,
        machines: dict[str, str],
        connect_delay_s: float = 0,
        hanging_keyscan: frozenset[str] = frozenset(),
    ) -> None:
        self.machines = machines
        self.hanging_keyscan = hanging_keyscan
        self.hanging_processes: list[_HangingProcess] = []
        self.connect_delay_s = connect_delay_s
        self.connected: list[str] = []
        self.keyscanned: list[str] = []
        self.ssh_calls: list[tuple] = []
        self.in_flight = 0
        self.max_in_flight = 0

    async def open_connection(self, host: str, port: int) -> tuple[object, _Writer]:
        self.in_flight += 1
        self.max_in_flight = max(self.max_in_flight, self.in_flight)
        try:
            await asyncio.sleep(self.connect_delay_s)
            self.connected.append(host)
            if host not in self.machines:
                raise OSError(113, "No route to host")
            return object(), _Writer()
        finally:
            self.in_flight -= 1

    async def create_subprocess_exec(self, *args, **kwargs):
        if args[0] != "ssh-keyscan":
            # ssh vers PGX : authentification et `test -d` réussissent
            self.ssh_calls.append(args)
            return _Process(b"ok\n", b"")
        host = args[-1]
        self.keyscanned.append(host)
        if host in self.hanging_keyscan:
            process = _HangingProcess()
            self.hanging_processes.append(process)
            return process
        key = self.machines.get(host)
        if key is None:
            return _Process(b"", f"{host}: No route to host\n".encode())
        return _Process(
            f"{host} ssh-ed25519 {key}\n".encode(),
            f"# {host}:22 SSH-2.0-OpenSSH_9.6p1 Ubuntu-3ubuntu13.20\n".encode(),
        )

    def patch(self):
        return _Patches(self)


class _Patches:
    def __init__(self, network: FakeNetwork) -> None:
        self._patches = [
            patch(
                "back_office_lmelp.services.pgx_service.asyncio.open_connection",
                side_effect=network.open_connection,
            ),
            patch(
                "back_office_lmelp.services.pgx_service.asyncio.create_subprocess_exec",
                side_effect=network.create_subprocess_exec,
            ),
        ]

    def __enter__(self):
        for p in self._patches:
            p.start()
        return self

    def __exit__(self, *exc):
        for p in reversed(self._patches):
            p.stop()


class TestLocatePgx:
    @pytest.mark.asyncio
    async def test_pgx_moved_on_the_vpn_should_be_found_by_scanning(self):
        """PGX_HOST est passée au laptop, PGX a pris une autre adresse du pool."""
        network = FakeNetwork(
            {"192.168.49.6": OTHER_KEY_B64, "192.168.49.10": PGX_KEY_B64}
        )
        with network.patch():
            location = await locate_pgx(
                host="192.168.49.6",
                host_key=PGX_HOST_KEY,
                candidates=["192.168.49.0/24"],
            )

        assert location.address == "192.168.49.10"
        assert "PGX trouvée en 192.168.49.10" in location.detail
        assert "PGX_HOST vaut 192.168.49.6" in location.detail

    @pytest.mark.asyncio
    async def test_machines_with_another_host_key_should_never_be_retained(self):
        network = FakeNetwork(
            {"192.168.49.6": OTHER_KEY_B64, "192.168.49.7": OTHER_KEY_B64}
        )
        with network.patch():
            location = await locate_pgx(
                host="192.168.49.6",
                host_key=PGX_HOST_KEY,
                candidates=["192.168.49.0/24"],
            )

        assert location.address is None
        assert "Aucune machine avec l'identité de PGX parmi les candidats" in (
            location.detail
        )
        assert "2 hôte(s) répondent sur le port 22" in location.detail
        assert PGX_FINGERPRINT in location.detail

    @pytest.mark.asyncio
    async def test_pgx_at_pgx_host_should_be_found_without_scanning(self):
        network = FakeNetwork({"192.168.49.10": PGX_KEY_B64})
        with network.patch():
            location = await locate_pgx(
                host="192.168.49.10",
                host_key=PGX_HOST_KEY,
                candidates=["192.168.49.0/24"],
            )

        assert location.address == "192.168.49.10"
        assert location.detail == (
            f"PGX trouvée en 192.168.49.10 (clé d'hôte {PGX_FINGERPRINT})"
        )
        assert network.connected == ["192.168.49.10"]

    @pytest.mark.asyncio
    async def test_last_found_address_should_be_tried_first(self):
        network = FakeNetwork(
            {"192.168.49.6": OTHER_KEY_B64, "192.168.49.10": PGX_KEY_B64}
        )
        args = {
            "host": "192.168.49.6",
            "host_key": PGX_HOST_KEY,
            "candidates": ["192.168.49.0/24"],
        }
        with network.patch():
            await locate_pgx(**args)
            network.connected.clear()
            location = await locate_pgx(**args)

        assert location.address == "192.168.49.10"
        assert network.connected == ["192.168.49.10"]

    @pytest.mark.asyncio
    async def test_after_a_restart_the_search_should_start_from_pgx_host(
        self, monkeypatch
    ):
        network = FakeNetwork(
            {"192.168.49.6": OTHER_KEY_B64, "192.168.49.10": PGX_KEY_B64}
        )
        args = {
            "host": "192.168.49.6",
            "host_key": PGX_HOST_KEY,
            "candidates": ["192.168.49.0/24"],
        }
        with network.patch():
            await locate_pgx(**args)
            monkeypatch.setattr(pgx_service, "_last_pgx_address", None)  # redémarrage
            network.connected.clear()
            await locate_pgx(**args)

        assert network.connected[0] == "192.168.49.6"

    @pytest.mark.asyncio
    async def test_pgx_back_at_the_summer_house_should_be_found(self):
        """Retour à la maison d'été : PGX sur le réseau local, plus sur le VPN."""
        network = FakeNetwork({"192.168.50.151": PGX_KEY_B64})
        with network.patch():
            location = await locate_pgx(
                host="192.168.49.10",
                host_key=PGX_HOST_KEY,
                candidates=["192.168.49.0/24", "192.168.50.0/24"],
            )

        assert location.address == "192.168.50.151"

    @pytest.mark.asyncio
    async def test_without_candidates_only_pgx_host_is_tried(self):
        """Sans PGX_HOST_CANDIDATES, la cause reste nommée comme en #361."""
        network = FakeNetwork({"192.168.49.6": OTHER_KEY_B64})
        with network.patch():
            location = await locate_pgx(
                host="192.168.49.6", host_key=PGX_HOST_KEY, candidates=[]
            )

        assert location.address is None
        assert "La machine sur 192.168.49.6 n'est pas PGX" in location.detail
        assert network.connected == ["192.168.49.6"]

    @pytest.mark.asyncio
    async def test_pgx_host_silent_without_candidates_should_say_so(self):
        with FakeNetwork({}).patch():
            location = await locate_pgx(
                host="192.168.49.6", host_key=PGX_HOST_KEY, candidates=[]
            )

        assert location.address is None
        assert "192.168.49.6 ne répond pas sur le port 22" in location.detail

    @pytest.mark.asyncio
    async def test_invalid_candidates_should_be_reported_without_any_probe(self):
        network = FakeNetwork({"192.168.49.10": PGX_KEY_B64})
        with network.patch():
            location = await locate_pgx(
                host="192.168.49.10",
                host_key=PGX_HOST_KEY,
                candidates=["192.168.49.0/33"],
            )

        assert location.address is None
        assert "PGX_HOST_CANDIDATES invalide" in location.detail
        assert network.connected == []


class TestLocatePgxBounds:
    """Le balayage respecte ses bornes (#337) : parallélisme, délai par hôte, total."""

    @pytest.mark.asyncio
    async def test_at_most_64_hosts_should_be_probed_at_once(self):
        network = FakeNetwork({}, connect_delay_s=0.01)
        with network.patch():
            await locate_pgx(
                host="10.0.0.1", host_key=PGX_HOST_KEY, candidates=["10.0.0.0/24"]
            )

        assert len(network.connected) == 254
        assert network.max_in_flight == 64

    @pytest.mark.asyncio
    async def test_a_silent_host_should_be_given_up_after_one_second(self, monkeypatch):
        """Une adresse sans machine qui ne refuse pas (paquets jetés) : 1 s, pas plus."""
        timeouts: list[float] = []
        real_wait_for = asyncio.wait_for

        async def recording_wait_for(aw, timeout):
            timeouts.append(timeout)
            return await real_wait_for(aw, timeout)

        monkeypatch.setattr(pgx_service.asyncio, "wait_for", recording_wait_for)
        with FakeNetwork({}).patch():
            await locate_pgx(
                host="10.0.0.1", host_key=PGX_HOST_KEY, candidates=["10.0.0.0/30"]
            )

        # 1 borne globale, puis 1 s par connexion TCP : PGX_HOST (10.0.0.1), puis
        # 10.0.0.2 — PGX_HOST, déjà sondée, n'est pas balayée une seconde fois
        assert timeouts == [30.0, 1.0, 1.0]

    @pytest.mark.asyncio
    async def test_the_whole_search_should_stop_at_the_global_bound(self, monkeypatch):
        monkeypatch.setattr(pgx_service, "LOCATE_TIMEOUT_S", 0.05)
        monkeypatch.setattr(pgx_service, "TCP_PROBE_TIMEOUT_S", 10)
        network = FakeNetwork({}, connect_delay_s=5)
        with network.patch():
            location = await asyncio.wait_for(
                locate_pgx(
                    host="10.0.0.1",
                    host_key=PGX_HOST_KEY,
                    candidates=["10.0.0.0/24"],
                ),
                timeout=2,
            )

        assert location.address is None
        assert "PGX introuvable" in location.detail

    @pytest.mark.asyncio
    async def test_the_scan_should_stop_at_the_first_match(self):
        network = FakeNetwork({"10.0.0.2": PGX_KEY_B64}, connect_delay_s=0.01)
        with network.patch():
            location = await locate_pgx(
                host="10.0.0.1", host_key=PGX_HOST_KEY, candidates=["10.0.0.0/22"]
            )

        assert location.address == "10.0.0.2"
        # Les sondes suivantes sont annulées : loin des 1022 adresses de la plage
        assert len(network.connected) < 200


class TestChecklistLocatesPgx:
    @pytest.mark.asyncio
    async def test_checklist_should_show_one_line_with_the_gap_to_pgx_host(
        self, tmp_path
    ):
        network = FakeNetwork(
            {"192.168.49.6": OTHER_KEY_B64, "192.168.49.10": PGX_KEY_B64}
        )
        config = {
            "host": "192.168.49.6",
            "user": "pgxuser",
            "key_path": "/keys/pgx_ed25519",
            "remote_audio_root": "/data/audios",
            "remote_transcription_root": "/data/transcriptions",
            "host_key": PGX_HOST_KEY,
            "candidates": ["192.168.49.0/24"],
        }
        with (
            network.patch(),
            patch(
                "back_office_lmelp.services.pgx_service._known_hosts_path",
                return_value=str(tmp_path / "known_hosts"),
            ),
        ):
            results = await run_pgx_diagnostics(config)

        assert [r["name"] for r in results] == [
            "PGX localisée",
            "Authentification SSH (clé dédiée)",
            "Répertoire audio distant",
            "Répertoire transcriptions distant",
        ]
        assert [r["status"] for r in results] == ["ok"] * 4
        assert (
            "PGX trouvée en 192.168.49.10 (PGX_HOST vaut 192.168.49.6)"
            in (results[0]["detail"])
        )
        # Les vérifications ssh visent l'adresse trouvée, pas PGX_HOST
        assert network.ssh_calls
        assert all("pgxuser@192.168.49.10" in call for call in network.ssh_calls)

    @pytest.mark.asyncio
    async def test_checklist_should_skip_everything_when_pgx_is_not_found(self):
        network = FakeNetwork({"192.168.49.6": OTHER_KEY_B64})
        config = {
            "host": "192.168.49.6",
            "user": "pgxuser",
            "key_path": "/keys/pgx_ed25519",
            "remote_audio_root": "/data/audios",
            "remote_transcription_root": "/data/transcriptions",
            "host_key": PGX_HOST_KEY,
            "candidates": ["192.168.49.0/24"],
        }
        with network.patch():
            results = await run_pgx_diagnostics(config)

        assert results[0]["status"] == "fail"
        assert "Aucune machine avec l'identité de PGX" in results[0]["detail"]
        assert [r["status"] for r in results[1:]] == ["skipped"] * 3
        assert network.ssh_calls == []


class TestLastAddressMemory:
    @pytest.mark.asyncio
    async def test_a_failed_search_should_not_forget_the_last_address(self):
        """PGX éteinte une fois : la recherche suivante repart quand même de la
        dernière adresse où elle a été trouvée (perdue seulement au redémarrage)."""
        args = {
            "host": "192.168.49.6",
            "host_key": PGX_HOST_KEY,
            "candidates": ["192.168.49.0/24"],
        }
        with FakeNetwork({"192.168.49.10": PGX_KEY_B64}).patch():
            await locate_pgx(**args)
        with FakeNetwork({}).patch():  # PGX éteinte
            await locate_pgx(**args)
        network = FakeNetwork({"192.168.49.10": PGX_KEY_B64})
        with network.patch():
            await locate_pgx(**args)

        assert network.connected == ["192.168.49.10"]


class TestNoOrphanKeyscan:
    @pytest.mark.asyncio
    async def test_keyscans_still_running_should_be_killed_when_pgx_is_found(self):
        """Une fois PGX trouvée, les ssh-keyscan encore en cours sont tués (#337)."""
        network = FakeNetwork(
            {"10.0.0.2": OTHER_KEY_B64, "10.0.0.3": PGX_KEY_B64},
            hanging_keyscan=frozenset({"10.0.0.2"}),
        )
        with network.patch():
            location = await locate_pgx(
                host="10.0.0.9", host_key=PGX_HOST_KEY, candidates=["10.0.0.0/29"]
            )

        assert location.address == "10.0.0.3"
        assert len(network.hanging_processes) == 1
        assert network.hanging_processes[0].killed
