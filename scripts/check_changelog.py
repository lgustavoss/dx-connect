#!/usr/bin/env python3
"""Valida CHANGELOG [Unreleased] em PRs com mudanças de produto (#400)."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHANGELOG = ROOT / "CHANGELOG.md"

PRODUCT_PREFIXES = (
    "backend/app/",
    "backend/tests/",
    "frontend/src/",
    "docker-compose.prod.yml",
)

SKIP_PREFIXES = (
    "docs/",
    ".github/planning-issue-bodies/",
    "CHANGELOG.md",
    "VERSION",
    "docs/releases/",
    "backend/app/data/release_notes.json",
    "frontend/public/release-notes.json",
    "frontend/public/release_notes.json",
    "scripts/prepare_release.py",
)


def _run(*args: str) -> str:
    r = subprocess.run(args, capture_output=True, text=True, check=False, cwd=ROOT)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip() or r.stdout.strip() or f"comando falhou: {args}")
    return r.stdout


def changed_files(base: str, head: str) -> list[str]:
    out = _run("git", "diff", "--name-only", f"{base}...{head}")
    return [ln.strip() for ln in out.splitlines() if ln.strip()]


def requires_changelog(paths: list[str]) -> bool:
    product = False
    for p in paths:
        if any(p.startswith(s) for s in SKIP_PREFIXES):
            continue
        if any(p.startswith(prefix) for prefix in PRODUCT_PREFIXES):
            product = True
            break
        if p.startswith("backend/") or p.startswith("frontend/"):
            product = True
            break
        if p.startswith("scripts/") and "check_changelog" not in p:
            product = True
            break
    return product


def parse_unreleased_bullets(text: str) -> list[str]:
    m = re.search(r"## \[Unreleased\](.*?)(?=\n## \[|\Z)", text, re.DOTALL | re.IGNORECASE)
    if not m:
        return []
    bullets: list[str] = []
    for line in m.group(1).splitlines():
        bullet = re.match(r"^-\s+(.+)$", line.strip())
        if bullet:
            bullets.append(bullet.group(1).strip())
    return bullets


def main() -> int:
    ap = argparse.ArgumentParser(description="Exige bullets em CHANGELOG [Unreleased] quando há diff de produto")
    ap.add_argument("--base", required=True, help="Ref base do PR (ex.: origin/main)")
    ap.add_argument("--head", default="HEAD", help="Ref head do PR")
    ap.add_argument(
        "--changelog",
        type=Path,
        default=CHANGELOG,
        help="Caminho do CHANGELOG (usa versão do head)",
    )
    args = ap.parse_args()

    paths = changed_files(args.base, args.head)
    if not paths:
        print("OK: PR sem arquivos alterados — CHANGELOG não exigido.")
        return 0

    if not requires_changelog(paths):
        print("OK: alterações só em arquivos isentos — CHANGELOG não exigido.")
        print("Arquivos:", ", ".join(paths[:12]) + ("…" if len(paths) > 12 else ""))
        return 0

    # CHANGELOG na revisão do PR (head)
    try:
        text = _run("git", "show", f"{args.head}:{args.changelog.relative_to(ROOT).as_posix()}")
    except RuntimeError:
        text = args.changelog.read_text(encoding="utf-8") if args.changelog.is_file() else ""

    bullets = parse_unreleased_bullets(text)
    if bullets:
        print(f"OK: CHANGELOG [Unreleased] com {len(bullets)} item(ns) de produto.")
        return 0

    print(
        "::error::Este PR altera código de produto, mas CHANGELOG.md não tem bullets em ## [Unreleased].\n"
        "Adicione uma linha por entrega (texto para o usuário final), ex.:\n"
        "  ### Melhorias\n"
        "  - Descrição curta da funcionalidade (#123)\n"
        "Veja docs/RELEASES.md",
        file=sys.stderr,
    )
    print("Arquivos de produto no diff:", ", ".join(paths[:20]), file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
