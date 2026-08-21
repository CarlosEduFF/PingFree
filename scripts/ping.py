"""Pinga os serviços configurados e grava o resultado em docs/data/status.json.

Roda no GitHub Actions (cron). Mantém um histórico curto por serviço para que a
página estática possa desenhar a barra de uptime sem precisar de backend.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGETS_FILE = ROOT / "targets.json"
STATUS_FILE = ROOT / "docs" / "data" / "status.json"

TIMEOUT = 60          # Render free tier dorme; cold start pode passar de 50s
HISTORY_LIMIT = 144   # ~24h de histórico com ping a cada 10 min
USER_AGENT = "uptime-pinger/1.0 (+https://github.com)"


def load_targets() -> list[dict]:
    with TARGETS_FILE.open(encoding="utf-8") as fh:
        return json.load(fh)["targets"]


def load_previous() -> dict:
    if not STATUS_FILE.exists():
        return {}
    try:
        with STATUS_FILE.open(encoding="utf-8") as fh:
            return json.load(fh)
    except json.JSONDecodeError:
        return {}


def is_up(code: int, accept: list[int]) -> bool:
    """O objetivo é manter o serviço acordado, não validar a rota.

    Qualquer resposta HTTP prova que o processo está de pé — inclusive um 404,
    que só diz que a raiz não tem rota. Por isso o default aceita < 500, e cada
    alvo pode restringir isso com "accept" no targets.json.
    """
    if accept:
        return code in accept
    return code < 500


def ping(url: str, accept: list[int]) -> dict:
    """Faz um GET e devolve status/latência. Nunca levanta exceção."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            elapsed_ms = round((time.perf_counter() - started) * 1000)
            code = response.status
            return {
                "ok": is_up(code, accept),
                "code": code,
                "ms": elapsed_ms,
                "error": None,
            }
    except urllib.error.HTTPError as exc:
        # Respondeu, mas com erro: o serviço está de pé, a rota é que falhou.
        ok = is_up(exc.code, accept)
        return {
            "ok": ok,
            "code": exc.code,
            "ms": round((time.perf_counter() - started) * 1000),
            "error": None if ok else f"HTTP {exc.code}",
        }
    except Exception as exc:  # timeout, DNS, conexão recusada, TLS...
        return {
            "ok": False,
            "code": None,
            "ms": round((time.perf_counter() - started) * 1000),
            "error": type(exc).__name__,
        }


def main() -> None:
    targets = load_targets()
    previous = load_previous()
    previous_by_url = {s["url"]: s for s in previous.get("services", [])}

    checked_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    services = []

    for target in targets:
        result = ping(target["url"], target.get("accept", []))
        old = previous_by_url.get(target["url"], {})

        history = old.get("history", [])
        history.append({"t": checked_at, "ok": result["ok"], "ms": result["ms"]})
        history = history[-HISTORY_LIMIT:]

        checks = len(history)
        ups = sum(1 for h in history if h["ok"])

        services.append({
            "name": target["name"],
            "url": target["url"],
            "ok": result["ok"],
            "code": result["code"],
            "ms": result["ms"],
            "error": result["error"],
            "checked_at": checked_at,
            "uptime": round(ups / checks * 100, 2) if checks else 0.0,
            "history": history,
        })

        status = "UP" if result["ok"] else "DOWN"
        detail = result["error"] or result["code"]
        print(f"{status:<4} {target['name']:<20} {result['ms']:>6}ms  {detail}")

    payload = {"generated_at": checked_at, "services": services}
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with STATUS_FILE.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    print(f"\nGravado em {STATUS_FILE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
