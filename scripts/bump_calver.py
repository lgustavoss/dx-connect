#!/usr/bin/env python3
"""CalVer YY.MM.NNN com fuso America/Sao_Paulo (#401)."""

from __future__ import annotations

import re
from datetime import datetime
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/Sao_Paulo")
_VERSION_RE = re.compile(r"^v?(?P<yy>\d{2})\.(?P<mm>\d{2})\.(?P<nnn>\d{3})$")


def parse_version(raw: str | None) -> tuple[int, int, int] | None:
    if not raw or not str(raw).strip():
        return None
    m = _VERSION_RE.match(str(raw).strip())
    if not m:
        return None
    return int(m.group("yy")), int(m.group("mm")), int(m.group("nnn"))


def version_display(version: str) -> str:
    v = version.strip().lstrip("v")
    return f"v{v}"


def next_calver(current: str | None, *, now: datetime | None = None) -> str:
    """Próxima versão CalVer para a data informada (default: agora em SP)."""
    ref = now or datetime.now(TZ)
    yy, mm = ref.year % 100, ref.month
    cur = parse_version(current)
    if cur and cur[0] == yy and cur[1] == mm:
        nnn = cur[2] + 1
    else:
        nnn = 1
    return f"{yy:02d}.{mm:02d}.{nnn:03d}"


if __name__ == "__main__":
    import argparse
    from pathlib import Path

    p = argparse.ArgumentParser(description="Calcula próximo CalVer")
    p.add_argument("--current", default="", help="Versão atual (ex.: 26.06.001)")
    p.add_argument("--version-file", type=Path, help="Lê versão de arquivo VERSION")
    args = p.parse_args()
    current = args.current
    if args.version_file and args.version_file.is_file():
        current = args.version_file.read_text(encoding="utf-8").strip()
    print(next_calver(current or None))
