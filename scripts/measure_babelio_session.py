#!/usr/bin/env python3
"""Mesure grandeur nature de la durée de vie de la session Babelio (Issue #370).

À lancer UNIQUEMENT depuis un réseau jetable (partage de connexion mobile) :
le test s'arrête au premier 403, que Babelio transforme en ban IP ~24 h.

Envoie une seule recherche d'auteur par palier, via le backend local
(POST /api/verify-babelio), avec des écarts croissants entre deux requêtes.
Une session PHP expire après une période d'inactivité : le premier 403 la
situe entre les deux derniers écarts. Chaque recherche porte un nom différent
(un cache hit n'envoie rien à Babelio, l'essai passe alors au nom suivant).

Garde-fous :
- l'IP publique est relevée au départ, puis revérifiée avant chaque requête :
  si elle change (retour sur le Wi-Fi de la maison), le test s'arrête sans
  rien envoyer ;
- refus de démarrer si le garde-fou du serveur n'a pas été élargi, si le
  cookie est absent, anonyme, ou collé depuis un autre navigateur que Firefox,
  ou si le circuit breaker est déjà ouvert.

Usage :
    BABELIO_COOKIE_MAX_AGE_SEC=86400 nohup ./scripts/start-dev.sh \
        > /tmp/start-dev.log 2>&1 & disown
    # coller un cookie frais (Firefox connecté) dans lmelp, puis :
    python scripts/measure_babelio_session.py
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_INTERVALS_MIN = "5,10,15,20,25,30,40,60,90,120"
MIN_GUARD_SEC = 4 * 3600
PUBLIC_IP_URL = "https://api.ipify.org"

# Auteurs réels, peu susceptibles d'être déjà dans le cache Babelio local
AUTHOR_NAMES = [
    "Marie NDiaye",
    "Éric Vuillard",
    "Maylis de Kerangal",
    "Pierre Michon",
    "Laurent Binet",
    "Lydie Salvayre",
    "Jean Echenoz",
    "Hélène Gaudy",
    "Mathias Énard",
    "Christine Angot",
    "Olivier Rolin",
    "Nathalie Azoulai",
    "Jean Rolin",
    "Brigitte Giraud",
    "Patrick Deville",
    "Céline Minard",
    "Antoine Volodine",
    "Marie Darrieussecq",
    "Hervé Le Tellier",
    "Neige Sinno",
    "Alice Zeniter",
    "Mohamed Mbougar Sarr",
    "Tanguy Viel",
    "Nathalie Quintane",
]


def log(msg: str) -> None:
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


def http_json(
    url: str, payload: dict[str, Any] | None = None, timeout: float = 90
) -> Any:
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"} if data else {},
        method="POST" if data is not None else "GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        try:
            return {"_http_status": e.code, **json.loads(body)}
        except json.JSONDecodeError:
            return {"_http_status": e.code, "_body": body}


def public_ip() -> str:
    with urllib.request.urlopen(PUBLIC_IP_URL, timeout=15) as resp:
        return resp.read().decode().strip()


def default_backend_url() -> str:
    script = Path(__file__).resolve().parent.parent / ".claude/get-backend-info.sh"
    out = subprocess.run(
        [str(script), "--url"], capture_output=True, text=True, check=False
    )
    url = out.stdout.strip()
    if not url.startswith("http"):
        sys.exit("Backend introuvable : lancez start-dev.sh ou passez --backend-url")
    return url


def check_preconditions(backend: str) -> dict[str, Any]:
    st = http_json(f"{backend}/api/babelio/status")
    problems = []
    if not st.get("cookie_active"):
        problems.append("aucun cookie Babelio enregistré")
    if st.get("cookie_anonymous"):
        problems.append("cookie anonyme (copié déconnecté)")
    if st.get("cookie_browser_not_firefox"):
        problems.append(
            "cookie collé dans lmelp depuis un navigateur autre que Firefox"
        )
    if st.get("circuit_open"):
        problems.append(f"circuit breaker déjà ouvert ({st.get('circuit_reason')})")
    if (st.get("cookie_max_age_sec") or 0) < MIN_GUARD_SEC:
        problems.append(
            f"garde-fou à {st.get('cookie_max_age_sec')} s : relancer le backend "
            "avec BABELIO_COOKIE_MAX_AGE_SEC=86400"
        )
    if problems:
        sys.exit("Préconditions non remplies :\n- " + "\n- ".join(problems))
    return st


def search_once(backend: str, names: list[str]) -> tuple[str, dict, dict] | None:
    """Une recherche qui part réellement vers Babelio (pas de cache hit)."""
    while names:
        name = names.pop(0)
        before = time.time()
        result = http_json(
            f"{backend}/api/verify-babelio", {"type": "author", "name": name}
        )
        recent = http_json(f"{backend}/api/babelio/requests/recent")
        entry = next(
            (
                r
                for r in recent
                if r.get("term_or_url") == name and r.get("timestamp", 0) >= before
            ),
            None,
        )
        blocked = result.get("status") in ("blocked_403", "blocked")
        if entry and entry.get("cache_hit") and not blocked:
            log(f"  « {name} » servi par le cache, nom suivant")
            continue
        return name, result, entry or {}
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--backend-url")
    parser.add_argument(
        "--intervals",
        default=DEFAULT_INTERVALS_MIN,
        help=f"écarts en minutes entre deux requêtes (défaut {DEFAULT_INTERVALS_MIN})",
    )
    parser.add_argument(
        "--log-file",
        default=f"/tmp/babelio_session_{datetime.now():%Y%m%d_%H%M%S}.jsonl",
    )
    args = parser.parse_args()

    backend = (args.backend_url or default_backend_url()).rstrip("/")
    intervals = [float(x) * 60 for x in args.intervals.split(",") if x.strip()]
    log_path = Path(args.log_file)

    st = check_preconditions(backend)
    ip = public_ip()
    log(f"Backend : {backend}")
    log(f"IP publique : {ip}")
    log(f"Garde-fou serveur : {st['cookie_max_age_sec']:.0f} s")
    log(f"Paliers (min) : 0, {args.intervals}")
    if (
        input("Cette IP est-elle celle du réseau mobile ? [o/N] ").strip().lower()
        != "o"
    ):
        sys.exit("Arrêt : connectez le laptop au partage de connexion mobile.")

    names = list(AUTHOR_NAMES)
    last_request_at: float | None = None
    for step, wait_sec in enumerate([0.0, *intervals]):
        if wait_sec:
            log(f"Palier {step} : attente {wait_sec / 60:.0f} min d'inactivité…")
            time.sleep(wait_sec)

        current_ip = public_ip()
        if current_ip != ip:
            sys.exit(f"IP changée ({ip} → {current_ip}) : arrêt sans requête.")

        status = http_json(f"{backend}/api/babelio/status")
        found = search_once(backend, names)
        if found is None:
            sys.exit("Plus de noms d'auteur disponibles hors cache.")
        name, result, entry = found
        now = time.time()
        record = {
            "step": step,
            "at": datetime.now().isoformat(timespec="seconds"),
            "idle_sec": round(now - last_request_at) if last_request_at else None,
            "cookie_age_sec": status.get("cookie_age_sec"),
            "name": name,
            "result_status": result.get("status"),
            "http_status": entry.get("status_code"),
            "ip": current_ip,
        }
        last_request_at = now

        blocked = result.get("status") in ("blocked_403", "blocked") or (
            entry.get("status_code") == 403
        )
        if blocked:
            record["blocked_responses"] = http_json(
                f"{backend}/api/babelio/blocked-responses"
            )[:1]
            record["circuit_reason"] = http_json(f"{backend}/api/babelio/status").get(
                "circuit_reason"
            )
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

        log(
            f"Palier {step} : « {name} » → {record['result_status']} "
            f"(HTTP {record['http_status']}, âge cookie "
            f"{record['cookie_age_sec']} s, inactivité {record['idle_sec']} s)"
        )
        if blocked:
            log(f"403 reçu (motif : {record['circuit_reason']}). Fin du test.")
            log(f"Détail : {log_path}")
            return

    log(f"Aucun 403 sur tous les paliers. Détail : {log_path}")


if __name__ == "__main__":
    main()
