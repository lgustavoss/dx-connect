#!/usr/bin/env python3
"""Marca solicitações citadas no release CalVer como concluídas (#956).

Uso (control-plane, após migrate):
  python scripts/concluir_solicitacoes_release.py --version 2026.08.26

Lê bullets de ## [Unreleased] no CHANGELOG (antes do finalize no CI).
Idempotente — re-run seguro.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from prepare_release import (  # noqa: E402
    CHANGELOG_FILE,
    MANIFEST_FILE,
    parse_changelog_unreleased,
)

_BACKEND = Path(__file__).resolve().parents[1]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from app.config import settings  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.services.saas_solicitacao_release import concluir_pedidos_release  # noqa: E402


def _textos_release(versao: str) -> list[str]:
    """Bullets do release: [Unreleased] (pré-finalize) ou manifest/CHANGELOG publicado."""
    changelog = CHANGELOG_FILE.read_text(encoding="utf-8") if CHANGELOG_FILE.is_file() else ""
    unreleased = parse_changelog_unreleased(changelog, warn_legacy=False)
    if unreleased:
        return [c["text"] for c in unreleased if c.get("text")]

    if MANIFEST_FILE.is_file():
        manifest = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
        for rel in reversed(manifest.get("releases") or []):
            if rel.get("version") == versao:
                out: list[str] = []
                for ch in rel.get("changes") or []:
                    if isinstance(ch, dict) and ch.get("text"):
                        out.append(str(ch["text"]))
                if out:
                    return out

    m = re.search(
        rf"## \[{re.escape(versao)}\].*?(?=\n## \[|\Z)",
        changelog,
        re.DOTALL | re.IGNORECASE,
    )
    if m:
        return [ln[2:].strip() for ln in m.group(0).splitlines() if ln.strip().startswith("- ")]
    return []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True, help="Versão CalVer publicada")
    ap.add_argument("--dry-run", action="store_true", help="Só lista referências, não grava")
    args = ap.parse_args()

    if not settings.SAAS_CONTROL_PLANE:
        print("Skip: SAAS_CONTROL_PLANE=false (só roda no admin-center).")
        return 0

    textos = _textos_release(args.version)
    if not textos:
        print("Nenhum bullet em [Unreleased] — nada a concluir.")
        return 0

    if args.dry_run:
        from app.services.saas_solicitacao_release import extrair_referencias_release

        protocolos, issues = extrair_referencias_release(textos)
        print(f"Protocolos: {sorted(protocolos)}")
        print(f"Issues: {sorted(issues)}")
        return 0

    db = SessionLocal()
    try:
        stats = concluir_pedidos_release(db, versao=args.version, textos_changelog=textos)
    finally:
        db.close()

    print(
        f"Solicitações release {args.version}: "
        f"processados={stats['processados']} concluidos={stats['concluidos']} "
        f"ignorados={stats['ignorados']} erros={stats['erros']}"
    )
    if stats["erros"]:
        print("::warning::Alguns pedidos não foram concluídos — ver logs do backend.", file=sys.stderr)
    return 0 if stats["erros"] == 0 else 0  # não derruba deploy


if __name__ == "__main__":
    raise SystemExit(main())
