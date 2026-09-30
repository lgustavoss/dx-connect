#!/usr/bin/env python3
"""Marca solicitações citadas no release CalVer como concluídas (#956).

Uso (control-plane, após o build da API):
  python scripts/concluir_solicitacoes_release.py --version 26.09.005

No container a API fica em /app (só o backend). O CHANGELOG da raiz do
repositório não entra na imagem; as notas publicadas vão em
/app/app/data/release_notes.json, gravadas no deploy antes do build.
Idempotente — re-run seguro.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[1]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from app.config import settings  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.services.saas_solicitacao_release import concluir_pedidos_release  # noqa: E402

_VERSAO_RE = re.compile(r"^v?(?P<v>\d{2}\.\d{2}\.\d{3})$", re.IGNORECASE)


def normalizar_versao_release(versao: str) -> str:
    bruto = (versao or "").strip()
    m = _VERSAO_RE.match(bruto)
    return m.group("v") if m else bruto.lstrip("vV")


def _bullets_de_linhas(bloco: str) -> list[str]:
    return [ln[2:].strip() for ln in bloco.splitlines() if ln.strip().startswith("- ")]


def _bullets_changelog_versao(changelog: str, versao: str) -> list[str]:
    m = re.search(
        rf"## \[{re.escape(versao)}\].*?(?=\n## \[|\Z)",
        changelog,
        re.DOTALL | re.IGNORECASE,
    )
    if not m:
        return []
    return _bullets_de_linhas(m.group(0))


def _bullets_unreleased(changelog: str) -> list[str]:
    m = re.search(
        r"## \[Unreleased\].*?(?=\n## \[|\Z)",
        changelog,
        re.DOTALL | re.IGNORECASE,
    )
    if not m:
        return []
    return _bullets_de_linhas(m.group(0))


def _bullets_release_notes(notes: dict, versao: str) -> list[str]:
    def _de_entry(entry: dict | None) -> list[str]:
        if not isinstance(entry, dict):
            return []
        if normalizar_versao_release(str(entry.get("version") or "")) != versao:
            return []
        out: list[str] = []
        for ch in entry.get("changes") or []:
            if isinstance(ch, dict) and ch.get("text"):
                out.append(str(ch["text"]))
        return out

    atuais = _de_entry(notes.get("current") if isinstance(notes.get("current"), dict) else None)
    if atuais:
        return atuais
    for rel in notes.get("releases") or []:
        textos = _de_entry(rel if isinstance(rel, dict) else None)
        if textos:
            return textos
    return []


def textos_da_versao(
    versao: str,
    *,
    changelog: str | None = None,
    release_notes: dict | None = None,
) -> list[str]:
    """Bullets da versão pedida. Notas publicadas vencem [Unreleased]."""
    versao_n = normalizar_versao_release(versao)
    if not versao_n:
        return []
    if changelog:
        publicados = _bullets_changelog_versao(changelog, versao_n)
        if publicados:
            return publicados
    if release_notes:
        publicados = _bullets_release_notes(release_notes, versao_n)
        if publicados:
            return publicados
    if changelog:
        return _bullets_unreleased(changelog)
    return []


def _changelog_no_checkout() -> str | None:
    """CHANGELOG da raiz do repo (dev). No container de produção esse arquivo não existe."""
    raiz = _BACKEND.parent
    path = raiz / "CHANGELOG.md"
    if path.is_file():
        return path.read_text(encoding="utf-8")
    return None


def _release_notes_na_imagem() -> dict | None:
    """Notas copiadas para a imagem: backend/app/data (no container, /app/app/data)."""
    path = _BACKEND / "app" / "data" / "release_notes.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _textos_release(versao: str) -> list[str]:
    return textos_da_versao(
        versao,
        changelog=_changelog_no_checkout(),
        release_notes=_release_notes_na_imagem(),
    )


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
        print(
            f"Nenhum bullet da versão {args.version} "
            "(release_notes.json da imagem nem CHANGELOG do checkout).",
            file=sys.stderr,
        )
        return 1

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
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
