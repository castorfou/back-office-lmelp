"""Pipeline de transcription automatisée via la station GPU PGX (Issue #302).

Porté depuis castorfou/lmelp (nbs/pgx.py) : un service watcher tourne en
permanence sur PGX et transcrit automatiquement tout fichier audio déposé
dans le répertoire surveillé. Ce module localise PGX d'après sa clé d'hôte
(ADR 0002), envoie l'audio, attend la transcription puis la rapatrie. PGX (Wi-Fi
uniquement, veille système désactivée pour raisons GPU) doit être allumée
manuellement — aucun réveil à distance n'est tenté (pas de Wake-on-LAN).
"""

import asyncio
import base64
import binascii
import contextlib
import hashlib
import ipaddress
import json
import os
import tempfile
from dataclasses import dataclass
from typing import Any


class PgxError(RuntimeError):
    """Erreur levée lorsqu'une étape du pipeline de transcription PGX échoue."""


class PgxTimeoutError(PgxError, TimeoutError):
    """Une commande ssh/scp vers PGX n'a pas rendu la main à temps.

    Hérite des deux : le pipeline la traite comme l'échec d'un épisode
    (PgxError), et les appelants qui attendaient un TimeoutError la reçoivent.
    """


# Délai maximal d'une commande ssh/scp courte (test, mkdir, enqueue, rapatriement
# d'un .txt) : une commande sans borne bloquait tout le pipeline (Issue #337).
SSH_COMMAND_TIMEOUT_S = 60.0

# Jamais d'invite interactive, connexion bornée, connexion morte coupée en ~45 s
_SSH_SAFETY_OPTIONS = [
    "-o",
    "BatchMode=yes",
    "-o",
    "ConnectTimeout=10",
    "-o",
    "ServerAliveInterval=15",
    "-o",
    "ServerAliveCountMax=3",
]


async def ensure_pgx_ssh_key(key_path: str) -> str:
    """Génère la paire de clés SSH dédiée à PGX si elle n'existe pas encore.

    Idempotent : ne régénère rien si la clé privée existe déjà à cet
    emplacement — elle doit rester stable dans le temps (stockée sur un
    volume persistant), sous peine d'invalider l'autorisation déjà
    déployée sur PGX.

    Returns:
        str: Le contenu de la clé publique correspondante.
    """
    if not os.path.exists(key_path):
        parent_dir = os.path.dirname(key_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)

        process = await asyncio.create_subprocess_exec(
            "ssh-keygen",
            "-t",
            "ed25519",
            "-f",
            key_path,
            "-N",
            "",
            "-C",
            "back-office-lmelp-pgx",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await process.communicate()
        if process.returncode != 0:
            raise PgxError(
                f"Échec de la génération de la clé SSH PGX: {stderr.decode().strip()}"
            )

    with open(f"{key_path}.pub") as f:
        return f.read().strip()


# Alias sous lequel la clé d'hôte de PGX est connue : ssh vérifie la clé de
# l'alias, pas celle de l'adresse jointe. PGX change d'adresse (maison d'été,
# VPN du NAS) sans changer d'identité (ADR 0002).
PGX_HOST_KEY_ALIAS = "pgx"

# Délai de ssh-keyscan (par tentative) et borne de la commande entière (#337)
KEYSCAN_TIMEOUT_S = 5
KEYSCAN_COMMAND_TIMEOUT_S = 15.0


def parse_pgx_host_key(value: str) -> tuple[str, str]:
    """Extrait (type, clé en base64) d'une clé publique d'hôte ED25519.

    Accepte le contenu de `/etc/ssh/ssh_host_ed25519_key.pub`
    (`ssh-ed25519 AAAA… root@pgx`) comme une ligne de `ssh-keyscan`
    (`<ip> ssh-ed25519 AAAA…`). Lève ValueError si aucune clé ED25519 n'y
    figure : c'est le seul type épinglé (et demandé à ssh-keyscan).
    """
    tokens = value.split()
    for key_type, key_b64 in zip(tokens, tokens[1:], strict=False):
        if key_type == "ssh-ed25519":
            try:
                base64.b64decode(key_b64, validate=True)
            except (binascii.Error, ValueError):
                continue
            return key_type, key_b64
    raise ValueError("Clé d'hôte illisible (attendu : « ssh-ed25519 AAAA… »)")


def host_key_fingerprint(key_b64: str) -> str:
    """Empreinte SHA256 d'une clé, au format affiché par `ssh-keygen -lf`."""
    digest = hashlib.sha256(base64.b64decode(key_b64)).digest()
    return "SHA256:" + base64.b64encode(digest).decode().rstrip("=")


def _known_hosts_path() -> str:
    """Fichier known_hosts dédié, dans un répertoire toujours accessible en écriture.

    Jamais le ~/.ssh/known_hosts par défaut (potentiellement en lecture
    seule, ex: bind-mount ro en devcontainer), ni un chemin dérivé de
    PGX_SSH_KEY_PATH. Il ne contient qu'une ligne, générée depuis
    PGX_HOST_KEY par install_pgx_host_key() : rien n'y est jamais appris.
    """
    return os.path.join(tempfile.gettempdir(), "back_office_lmelp_pgx_known_hosts")


def install_pgx_host_key(host_key: str) -> None:
    """(Ré)écrit le known_hosts dédié avec la seule clé de PGX, sous l'alias fixe.

    À appeler avant toute commande ssh/scp : sans ce fichier, ssh refuse toute
    machine (StrictHostKeyChecking=yes), ce qui est le comportement sûr.
    """
    key_type, key_b64 = parse_pgx_host_key(host_key)
    path = _known_hosts_path()
    tmp_path = f"{path}.{os.getpid()}.tmp"
    with open(tmp_path, "w") as f:
        f.write(f"{PGX_HOST_KEY_ALIAS} {key_type} {key_b64}\n")
    os.replace(tmp_path, path)


def _host_key_options() -> list[str]:
    """Options ssh/scp : seule la clé de PGX est acceptée, quelle que soit l'adresse."""
    return [
        "-o",
        f"UserKnownHostsFile={_known_hosts_path()}",
        "-o",
        "GlobalKnownHostsFile=/dev/null",
        "-o",
        f"HostKeyAlias={PGX_HOST_KEY_ALIAS}",
        "-o",
        "StrictHostKeyChecking=yes",
        "-o",
        "CheckHostIP=no",
    ]


def _ssh_base_command(user: str, host: str, key_path: str) -> list[str]:
    return [
        "ssh",
        "-i",
        key_path,
        "-o",
        "IdentitiesOnly=yes",
        *_host_key_options(),
        *_SSH_SAFETY_OPTIONS,
        f"{user}@{host}",
    ]


def _scp_base_command(key_path: str) -> list[str]:
    return [
        "scp",
        "-i",
        key_path,
        "-o",
        "IdentitiesOnly=yes",
        *_host_key_options(),
        *_SSH_SAFETY_OPTIONS,
    ]


async def _run_command(
    command: list[str], *, timeout_s: float | None = None, unbounded: bool = False
) -> tuple[int, str, str]:
    """Exécute une commande subprocess et retourne (returncode, stdout, stderr).

    Sans `timeout_s`, la commande est bornée par SSH_COMMAND_TIMEOUT_S ;
    `unbounded=True` lève la borne (transfert long, protégé par le keepalive ssh).
    Lève PgxTimeoutError si la commande ne rend pas la main à temps.
    """
    effective_timeout = (
        None
        if unbounded
        else (timeout_s if timeout_s is not None else SSH_COMMAND_TIMEOUT_S)
    )
    process = await asyncio.create_subprocess_exec(
        *command,
        stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(
            process.communicate(), timeout=effective_timeout
        )
    except TimeoutError as exc:
        await _kill(process)
        raise PgxTimeoutError(
            f"PGX ne répond pas (commande ssh/scp > {effective_timeout}s)"
        ) from exc
    except asyncio.CancelledError:
        # Tâche annulée (ex: PGX trouvée ailleurs) : pas de processus orphelin
        await asyncio.shield(_kill(process))
        raise
    return process.returncode or 0, stdout.decode(), stderr.decode()


async def _kill(process: asyncio.subprocess.Process) -> None:
    with contextlib.suppress(ProcessLookupError):
        process.kill()
        await process.wait()


async def _ensure_remote_dir(
    remote_dir: str, *, host: str, user: str, key_path: str
) -> None:
    """Crée le répertoire distant (ex: année) s'il n'existe pas encore — scp ne peut pas
    le créer lui-même."""
    command = _ssh_base_command(user, host, key_path) + [f"mkdir -p '{remote_dir}'"]
    returncode, _, stderr = await _run_command(command)
    if returncode != 0:
        raise PgxError(f"Échec de la création du répertoire distant sur PGX: {stderr}")


async def send_audio_to_pgx(
    local_path: str,
    remote_dir: str,
    *,
    host: str,
    user: str,
    key_path: str,
    timeout_s: float | None = None,
) -> None:
    """Envoie le fichier audio vers PGX par scp (clé SSH dédiée, pas de mot de passe)."""
    await _ensure_remote_dir(remote_dir, host=host, user=user, key_path=key_path)

    command = _scp_base_command(key_path) + [
        local_path,
        f"{user}@{host}:{remote_dir}/",
    ]
    try:
        returncode, _, stderr = await _run_command(
            command, timeout_s=timeout_s, unbounded=timeout_s is None
        )
    except TimeoutError as exc:
        raise PgxError("Timeout lors de l'envoi du fichier audio vers PGX") from exc
    if returncode != 0:
        raise PgxError(f"Échec de l'envoi du fichier audio vers PGX: {stderr}")


async def remote_file_exists(
    remote_path: str, *, host: str, user: str, key_path: str
) -> bool:
    """Teste (via ssh) la présence d'un fichier sur PGX."""
    command = _ssh_base_command(user, host, key_path) + [f"test -f '{remote_path}'"]
    returncode, _, _ = await _run_command(command)
    return returncode == 0


async def requeue_pgx_audio(
    container_audio_path: str, *, container: str, host: str, user: str, key_path: str
) -> None:
    """Remet un audio déjà présent sur PGX dans la file de whisper (Issue #320).

    `container_audio_path` est le chemin vu depuis le conteneur whisper. Un job
    déjà en attente ou en cours pour ce fichier n'est pas une erreur.
    """
    command = _ssh_base_command(user, host, key_path) + [
        f"docker exec '{container}' python3 -m whisper_docker.queue_manager "
        f"enqueue '{container_audio_path}'"
    ]
    returncode, stdout, stderr = await _run_command(command)
    if returncode != 0 and "déjà en queue" not in stdout + stderr:
        raise PgxError(f"Échec de la relance de la transcription sur PGX: {stderr}")


async def wait_for_pgx_transcription(
    remote_txt_path: str,
    *,
    host: str,
    user: str,
    key_path: str,
    timeout_s: float = 1800,
    poll_interval_s: float = 10,
    command_timeout_s: float | None = None,
) -> bool:
    """Poll (via ssh) l'apparition du fichier de transcription sur PGX.

    Chaque vérification est bornée (`command_timeout_s`, SSH_COMMAND_TIMEOUT_S
    par défaut) : une vérification qui ne rend pas la main compte comme « pas
    encore là », et le délai global `timeout_s` reste respecté (Issue #337).
    """
    command = _ssh_base_command(user, host, key_path) + [f"test -f '{remote_txt_path}'"]
    deadline = asyncio.get_event_loop().time() + timeout_s
    while True:
        try:
            returncode, _, _ = await _run_command(command, timeout_s=command_timeout_s)
        except PgxTimeoutError:
            returncode = -1
        if returncode == 0:
            return True
        if asyncio.get_event_loop().time() >= deadline:
            return False
        await asyncio.sleep(poll_interval_s)


async def fetch_transcription_from_pgx(
    remote_txt_path: str,
    local_txt_path: str,
    *,
    host: str,
    user: str,
    key_path: str,
) -> str:
    """Rapatrie le fichier de transcription depuis PGX par scp et retourne son contenu."""
    command = _scp_base_command(key_path) + [
        f"{user}@{host}:{remote_txt_path}",
        local_txt_path,
    ]
    returncode, _, stderr = await _run_command(command)
    if returncode != 0:
        raise PgxError(
            f"Échec du rapatriement de la transcription depuis PGX: {stderr}"
        )

    with open(local_txt_path) as f:
        return f.read()


async def fetch_segments_from_pgx(
    remote_json_path: str,
    local_json_path: str,
    *,
    host: str,
    user: str,
    key_path: str,
    tentatives: int = 3,
    attente_s: float = 10,
) -> dict[str, Any]:
    """Rapatrie le .json horodaté de whisper (`-oj`) et retourne son contenu.

    Un .json encore en cours d'écriture ne se décode pas : il est relu après
    `attente_s`, au plus `tentatives` fois (Issue #427).
    """
    command = _scp_base_command(key_path) + [
        f"{user}@{host}:{remote_json_path}",
        local_json_path,
    ]
    for tentative in range(1, tentatives + 1):
        returncode, _, stderr = await _run_command(command)
        if returncode != 0:
            raise PgxError(f"Échec du rapatriement des segments depuis PGX: {stderr}")
        try:
            with open(local_json_path, encoding="utf-8") as f:
                return dict(json.load(f))
        except json.JSONDecodeError:
            if tentative == tentatives:
                raise PgxError(
                    f"Segments illisibles après {tentatives} essais: {remote_json_path}"
                ) from None
            await asyncio.sleep(attente_s)
    raise PgxError(f"Segments non rapatriés: {remote_json_path}")


async def _check_host_identity(*, host: str, host_key: str) -> tuple[bool, str]:
    """Compare la clé d'hôte présentée sur `host` à PGX_HOST_KEY (sans authentification)."""
    try:
        key_type, expected_b64 = parse_pgx_host_key(host_key)
    except ValueError as exc:
        return False, f"PGX_HOST_KEY invalide : {exc}"

    command = [
        "ssh-keyscan",
        "-T",
        str(KEYSCAN_TIMEOUT_S),
        "-t",
        "ed25519",
        host,
    ]
    try:
        _, stdout, stderr = await _run_command(
            command, timeout_s=KEYSCAN_COMMAND_TIMEOUT_S
        )
    except PgxTimeoutError:
        return False, f"{host} n'a pas présenté de clé d'hôte à temps"

    received = []
    for line in stdout.splitlines():
        if line.startswith("#") or not line.strip():
            continue
        try:
            received.append(parse_pgx_host_key(line))
        except ValueError:
            continue

    expected_fp = host_key_fingerprint(expected_b64)
    if any(b64 == expected_b64 for _, b64 in received):
        return True, f"{host} est bien PGX (clé d'hôte {expected_fp})"
    if not received:
        detail = stderr.strip() or "aucune réponse"
        return False, (
            f"{host} n'a présenté aucune clé d'hôte {key_type} ({detail}) — "
            f"empreinte attendue : {expected_fp}"
        )
    received_fp = ", ".join(host_key_fingerprint(b64) for _, b64 in received)
    return False, (
        f"La machine sur {host} n'est pas PGX (clé d'hôte différente) — "
        "l'adresse VPN a probablement changé de machine. "
        f"Empreinte attendue : {expected_fp} ; empreinte reçue : {received_fp}"
    )


@dataclass(frozen=True)
class PgxLocation:
    """Résultat de la localisation : l'adresse où PGX a été reconnue (None si
    introuvable) et le message affiché dans la checklist."""

    address: str | None
    detail: str


# Dernière adresse où PGX a été reconnue : essayée en premier, perdue au
# redémarrage du backend (la recherche repart alors de PGX_HOST)
_last_pgx_address: str | None = None

# Bornes du balayage des candidats (#337) : délai de connexion TCP par hôte,
# hôtes sondés en parallèle, durée totale de la localisation
TCP_PROBE_TIMEOUT_S = 1.0
SCAN_CONCURRENCY = 64
LOCATE_TIMEOUT_S = 30.0


async def _port_22_open(address: str) -> bool:
    """Connexion TCP sur le port 22, refermée aussitôt (pas de TLS, pas de ssh)."""
    try:
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(address, 22), timeout=TCP_PROBE_TIMEOUT_S
        )
    except (TimeoutError, OSError):
        return False
    writer.close()
    with contextlib.suppress(OSError):
        await writer.wait_closed()
    return True


def _expand_candidates(candidates: list[str]) -> list[str]:
    """Adresses à balayer, dans l'ordre des plages (IP seules ou CIDR)."""
    addresses: list[str] = []
    for candidate in candidates:
        network = ipaddress.ip_network(candidate.strip(), strict=False)
        hosts = list(network.hosts()) or [network.network_address]
        addresses.extend(str(h) for h in hosts)
    return addresses


class _Search:
    """État d'une localisation : adresses sondées et celles qui répondent."""

    def __init__(self, host_key: str) -> None:
        self.host_key = host_key
        self.probed: set[str] = set()
        self.responding: set[str] = set()
        self.details: dict[str, str] = {}

    async def is_pgx(self, address: str) -> bool:
        self.probed.add(address)
        if not await _port_22_open(address):
            return False
        self.responding.add(address)
        ok, detail = await _check_host_identity(host=address, host_key=self.host_key)
        self.details[address] = detail
        return ok

    async def scan(self, addresses: list[str]) -> str | None:
        """Sonde les adresses (SCAN_CONCURRENCY à la fois) ; s'arrête à la première
        qui présente la clé de PGX."""
        semaphore = asyncio.Semaphore(SCAN_CONCURRENCY)

        async def probe(address: str) -> str | None:
            async with semaphore:
                return address if await self.is_pgx(address) else None

        tasks = [asyncio.create_task(probe(a)) for a in addresses]
        try:
            for next_done in asyncio.as_completed(tasks):
                found = await next_done
                if found:
                    return found
            return None
        finally:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)


async def locate_pgx(*, host: str, host_key: str, candidates: list[str]) -> PgxLocation:
    """Trouve l'adresse où répond la machine qui présente la clé d'hôte de PGX.

    Ordre : dernière adresse trouvée, PGX_HOST, puis balayage de `candidates`
    (plages CIDR ou IP). Une adresse n'est retenue que si la clé d'hôte reçue
    est celle de PGX_HOST_KEY (ADR 0002). Bornée par LOCATE_TIMEOUT_S.
    """
    global _last_pgx_address
    try:
        _, expected_b64 = parse_pgx_host_key(host_key)
    except ValueError as exc:
        return PgxLocation(None, f"PGX_HOST_KEY invalide : {exc}")
    try:
        scan_addresses = _expand_candidates(candidates)
    except ValueError as exc:
        return PgxLocation(None, f"PGX_HOST_CANDIDATES invalide : {exc}")
    expected_fp = host_key_fingerprint(expected_b64)

    search = _Search(host_key)
    direct = [a for a in (_last_pgx_address, host) if a]
    direct = list(dict.fromkeys(direct))

    async def find() -> str | None:
        for address in direct:
            if await search.is_pgx(address):
                return address
        return await search.scan([a for a in scan_addresses if a not in search.probed])

    def search_summary() -> str:
        return (
            f"({len(search.responding)} hôte(s) répondent sur le port 22) — "
            f"empreinte attendue : {expected_fp}"
        )

    try:
        found = await asyncio.wait_for(find(), timeout=LOCATE_TIMEOUT_S)
    except TimeoutError:
        return PgxLocation(
            None,
            f"PGX introuvable : recherche arrêtée après {LOCATE_TIMEOUT_S:.0f} s "
            + search_summary(),
        )

    if found is None:
        if not scan_addresses:
            if host not in search.responding:
                return PgxLocation(
                    None,
                    f"{host} ne répond pas sur le port 22 — vérifiez que PGX est "
                    "allumée et connectée au VPN",
                )
            return PgxLocation(None, search.details[host])
        return PgxLocation(
            None,
            "Aucune machine avec l'identité de PGX parmi les candidats "
            + search_summary(),
        )
    _last_pgx_address = found
    if found == host:
        return PgxLocation(found, f"PGX trouvée en {found} (clé d'hôte {expected_fp})")
    return PgxLocation(
        found,
        f"PGX trouvée en {found} (PGX_HOST vaut {host}) — clé d'hôte {expected_fp}",
    )


async def _check_ssh_auth(*, host: str, user: str, key_path: str) -> tuple[bool, str]:
    """Teste une authentification SSH réelle avec la clé dédiée (pas juste le port ouvert).

    Appelée seulement une fois l'identité de la machine vérifiée : un
    « Permission denied » vient alors bien de PGX, et renvoie vers
    authorized_keys. Tout autre échec affiche le stderr ssh tel quel.
    """
    command = _ssh_base_command(user, host, key_path) + ["echo ok"]
    try:
        returncode, stdout, stderr = await _run_command(command, timeout_s=10)
    except TimeoutError:
        return False, "Timeout lors de la tentative d'authentification"
    if returncode == 0 and "ok" in stdout:
        return True, "Authentification réussie avec la clé dédiée"
    stderr_detail = stderr.strip()
    if "Permission denied" in stderr_detail:
        return False, (
            "PGX refuse la clé dédiée — vérifiez que la clé publique est bien "
            f"dans authorized_keys sur PGX (détail SSH : {stderr_detail})"
        )
    if stderr_detail:
        return False, f"Échec de la connexion SSH : {stderr_detail}"
    return False, "Échec de la connexion SSH (ssh n'a renvoyé aucun détail)"


async def _check_remote_dir_exists(
    remote_dir: str, *, host: str, user: str, key_path: str
) -> tuple[bool, str]:
    """Vérifie qu'un répertoire distant existe sur PGX."""
    command = _ssh_base_command(user, host, key_path) + [f"test -d '{remote_dir}'"]
    returncode, _, _ = await _run_command(command, timeout_s=10)
    if returncode == 0:
        return True, f"{remote_dir} existe"
    return False, f"{remote_dir} n'existe pas ou n'est pas accessible"


# Étapes de la checklist, dans l'ordre où run_pgx_diagnostics() les exécute
PGX_DIAGNOSTIC_STEPS = (
    "PGX localisée",
    "Authentification SSH (clé dédiée)",
    "Répertoire audio distant",
    "Répertoire transcriptions distant",
)


def _skip_remaining_steps(results: list[dict], detail: str) -> list[dict]:
    """Marque 'skipped' les étapes qui suivent la dernière exécutée."""
    for name in PGX_DIAGNOSTIC_STEPS[len(results) :]:
        results.append({"name": name, "status": "skipped", "detail": detail})
    return results


async def run_pgx_diagnostics(config: dict) -> list[dict]:
    """Exécute la checklist PGX (PGX_DIAGNOSTIC_STEPS) — chaque vérification
    arrête les suivantes si elle échoue, puisqu'elles en dépendent (inutile de
    tester l'authentification si PGX n'a pas été localisée). Les vérifications
    ssh visent l'adresse où PGX a été trouvée, pas forcément PGX_HOST.

    Args:
        config: dict avec les clés host, user, key_path, remote_audio_root,
        remote_transcription_root, host_key (voir get_pgx_config_missing_vars pour la
        vérification préalable de complétude), et candidates (facultative, plages
        PGX_HOST_CANDIDATES).

    Returns:
        list[dict]: une entrée par vérification, avec les clés "name" (str),
        "status" ("ok", "fail" ou "skipped") et "detail" (str).
    """
    host = config["host"]
    user = config["user"]
    key_path = config["key_path"]
    remote_audio_root = config["remote_audio_root"]
    remote_transcription_root = config["remote_transcription_root"]
    host_key = config["host_key"]

    results = []

    location = await locate_pgx(
        host=host, host_key=host_key, candidates=config.get("candidates") or []
    )
    results.append(
        {
            "name": "PGX localisée",
            "status": "ok" if location.address else "fail",
            "detail": location.detail,
        }
    )
    if location.address is None:
        return _skip_remaining_steps(results, "PGX introuvable")
    host = location.address

    install_pgx_host_key(host_key)

    ssh_ok, ssh_detail = await _check_ssh_auth(host=host, user=user, key_path=key_path)
    results.append(
        {
            "name": "Authentification SSH (clé dédiée)",
            "status": "ok" if ssh_ok else "fail",
            "detail": ssh_detail,
        }
    )
    if not ssh_ok:
        return _skip_remaining_steps(results, "Authentification SSH impossible")

    audio_ok, audio_detail = await _check_remote_dir_exists(
        remote_audio_root, host=host, user=user, key_path=key_path
    )
    results.append(
        {
            "name": "Répertoire audio distant",
            "status": "ok" if audio_ok else "fail",
            "detail": audio_detail,
        }
    )

    txt_ok, txt_detail = await _check_remote_dir_exists(
        remote_transcription_root, host=host, user=user, key_path=key_path
    )
    results.append(
        {
            "name": "Répertoire transcriptions distant",
            "status": "ok" if txt_ok else "fail",
            "detail": txt_detail,
        }
    )

    return results


def get_pgx_config_missing_vars(config: dict) -> list[str]:
    """Noms des variables d'environnement PGX absentes dans `config` — permet à
    l'UI/API de désactiver les actions PGX sans déclencher un diagnostic
    réseau voué à planter (ex: host=None)."""
    env_var_names = {
        "host": "PGX_HOST",
        "user": "PGX_USER",
        "key_path": "PGX_SSH_KEY_PATH",
        "remote_audio_root": "PGX_REMOTE_AUDIO_ROOT",
        "remote_transcription_root": "PGX_REMOTE_TRANSCRIPTION_ROOT",
        "host_key": "PGX_HOST_KEY",
    }
    return [env_name for key, env_name in env_var_names.items() if not config.get(key)]


def pgx_fully_configured(diagnostics: list[dict]) -> bool:
    """True uniquement si run_pgx_diagnostics() a retourné une liste non vide où
    toutes les vérifications sont "ok" — utilisé pour n'autoriser le
    déclenchement d'une transcription que lorsque PGX est réellement prête."""
    return bool(diagnostics) and all(r["status"] == "ok" for r in diagnostics)
