"""Pipeline de transcription automatisée via la station GPU PGX (Issue #302).

Porté depuis castorfou/lmelp (nbs/pgx.py) : un service watcher tourne en
permanence sur PGX et transcrit automatiquement tout fichier audio déposé
dans le répertoire surveillé. Ce module vérifie que PGX est joignable,
envoie l'audio, attend la transcription puis la rapatrie. PGX (Wi-Fi
uniquement, veille système désactivée pour raisons GPU) doit être allumée
manuellement — aucun réveil à distance n'est tenté (pas de Wake-on-LAN).
"""

import asyncio
import contextlib
import os
import tempfile


class PgxError(RuntimeError):
    """Erreur levée lorsqu'une étape du pipeline de transcription PGX échoue."""


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


async def wait_for_pgx_reachable(
    host: str, port: int = 22, timeout_s: float = 120, poll_interval_s: float = 5
) -> bool:
    """Poll la disponibilité de PGX (connexion TCP) jusqu'à dispo ou expiration du délai."""
    deadline = asyncio.get_event_loop().time() + timeout_s
    while True:
        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port), timeout=poll_interval_s
            )
            writer.close()
            await writer.wait_closed()
            return True
        except (TimeoutError, OSError):
            if asyncio.get_event_loop().time() >= deadline:
                return False
            await asyncio.sleep(poll_interval_s)


def _known_hosts_path() -> str:
    """Fichier known_hosts dédié, dans un répertoire toujours accessible en écriture.

    Jamais le ~/.ssh/known_hosts par défaut (potentiellement en lecture
    seule, ex: bind-mount ro en devcontainer), ni un chemin dérivé de
    PGX_SSH_KEY_PATH (qui peut lui aussi vivre dans un emplacement en
    lecture seule pour un usage local/dev). Pas besoin de persistance :
    StrictHostKeyChecking=accept-new réaccepte la clé d'hôte à chaque
    redémarrage, sans risque sur un réseau local de confiance.
    """
    return os.path.join(tempfile.gettempdir(), "back_office_lmelp_pgx_known_hosts")


def _ssh_base_command(user: str, host: str, key_path: str) -> list[str]:
    return [
        "ssh",
        "-i",
        key_path,
        "-o",
        "IdentitiesOnly=yes",
        "-o",
        f"UserKnownHostsFile={_known_hosts_path()}",
        "-o",
        "StrictHostKeyChecking=accept-new",
        f"{user}@{host}",
    ]


def _scp_base_command(key_path: str) -> list[str]:
    return [
        "scp",
        "-i",
        key_path,
        "-o",
        "IdentitiesOnly=yes",
        "-o",
        f"UserKnownHostsFile={_known_hosts_path()}",
        "-o",
        "StrictHostKeyChecking=accept-new",
    ]


async def _run_command(
    command: list[str], *, timeout_s: float | None = None
) -> tuple[int, str, str]:
    """Exécute une commande subprocess et retourne (returncode, stdout, stderr)."""
    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(
            process.communicate(), timeout=timeout_s
        )
    except TimeoutError as exc:
        with contextlib.suppress(ProcessLookupError):
            process.kill()
            await process.wait()
        raise TimeoutError from exc
    return process.returncode or 0, stdout.decode(), stderr.decode()


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
        returncode, _, stderr = await _run_command(command, timeout_s=timeout_s)
    except TimeoutError as exc:
        raise PgxError("Timeout lors de l'envoi du fichier audio vers PGX") from exc
    if returncode != 0:
        raise PgxError(f"Échec de l'envoi du fichier audio vers PGX: {stderr}")


async def wait_for_pgx_transcription(
    remote_txt_path: str,
    *,
    host: str,
    user: str,
    key_path: str,
    timeout_s: float = 1800,
    poll_interval_s: float = 10,
) -> bool:
    """Poll (via ssh) l'apparition du fichier de transcription sur PGX."""
    command = _ssh_base_command(user, host, key_path) + [f"test -f '{remote_txt_path}'"]
    deadline = asyncio.get_event_loop().time() + timeout_s
    while True:
        returncode, _, _ = await _run_command(command)
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


async def _check_ssh_auth(*, host: str, user: str, key_path: str) -> tuple[bool, str]:
    """Teste une authentification SSH réelle avec la clé dédiée (pas juste le port ouvert)."""
    command = _ssh_base_command(user, host, key_path) + ["echo ok"]
    try:
        returncode, stdout, stderr = await _run_command(command, timeout_s=10)
    except TimeoutError:
        return False, "Timeout lors de la tentative d'authentification"
    if returncode == 0 and "ok" in stdout:
        return True, "Authentification réussie avec la clé dédiée"
    base_message = (
        "Échec de l'authentification — vérifiez que la clé publique est bien "
        "dans authorized_keys sur PGX"
    )
    stderr_detail = stderr.strip()
    if stderr_detail:
        return False, f"{base_message} (détail SSH : {stderr_detail})"
    return False, base_message


async def _check_remote_dir_exists(
    remote_dir: str, *, host: str, user: str, key_path: str
) -> tuple[bool, str]:
    """Vérifie qu'un répertoire distant existe sur PGX."""
    command = _ssh_base_command(user, host, key_path) + [f"test -d '{remote_dir}'"]
    returncode, _, _ = await _run_command(command, timeout_s=10)
    if returncode == 0:
        return True, f"{remote_dir} existe"
    return False, f"{remote_dir} n'existe pas ou n'est pas accessible"


async def run_pgx_diagnostics(config: dict) -> list[dict]:
    """Exécute une checklist de vérifications PGX (joignabilité, authentification SSH,
    répertoires distants) — chaque vérification arrête les suivantes si elle échoue,
    puisqu'elles en dépendent (inutile de tester l'authentification si injoignable, etc.).

    Args:
        config: dict avec les clés host, user, key_path, remote_audio_root,
        remote_transcription_root (voir get_pgx_config_missing_vars pour la
        vérification préalable de complétude).

    Returns:
        list[dict]: une entrée par vérification, avec les clés "name" (str),
        "status" ("ok", "fail" ou "skipped") et "detail" (str).
    """
    host = config["host"]
    user = config["user"]
    key_path = config["key_path"]
    remote_audio_root = config["remote_audio_root"]
    remote_transcription_root = config["remote_transcription_root"]

    results = []

    reachable = await wait_for_pgx_reachable(host, timeout_s=5, poll_interval_s=2)
    results.append(
        {
            "name": "Machine joignable",
            "status": "ok" if reachable else "fail",
            "detail": (
                f"{host} répond sur le port 22"
                if reachable
                else f"{host} ne répond pas sur le port 22 — vérifiez qu'elle est allumée"
            ),
        }
    )
    if not reachable:
        for name in (
            "Authentification SSH (clé dédiée)",
            "Répertoire audio distant",
            "Répertoire transcriptions distant",
        ):
            results.append(
                {"name": name, "status": "skipped", "detail": "PGX injoignable"}
            )
        return results

    ssh_ok, ssh_detail = await _check_ssh_auth(host=host, user=user, key_path=key_path)
    results.append(
        {
            "name": "Authentification SSH (clé dédiée)",
            "status": "ok" if ssh_ok else "fail",
            "detail": ssh_detail,
        }
    )
    if not ssh_ok:
        for name in ("Répertoire audio distant", "Répertoire transcriptions distant"):
            results.append(
                {
                    "name": name,
                    "status": "skipped",
                    "detail": "Authentification SSH impossible",
                }
            )
        return results

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
    }
    return [env_name for key, env_name in env_var_names.items() if not config.get(key)]


def pgx_fully_configured(diagnostics: list[dict]) -> bool:
    """True uniquement si run_pgx_diagnostics() a retourné une liste non vide où
    toutes les vérifications sont "ok" — utilisé pour n'autoriser le
    déclenchement d'une transcription que lorsque PGX est réellement prête."""
    return bool(diagnostics) and all(r["status"] == "ok" for r in diagnostics)
