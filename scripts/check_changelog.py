#!/usr/bin/env python3
"""Valida CHANGELOG [Unreleased] em PRs com mudanças de produto (#400 / #673)."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHANGELOG = ROOT / "CHANGELOG.md"
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from prepare_release import (  # noqa: E402
    PRODUCT_DESKRUDDER,
    PRODUCT_SAAS,
    parse_changelog_unreleased,
)

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
    "frontend/public/release_notes.json",
    "frontend/public/release-notes.json",
    "backend/tests/test_check_changelog.py",
)

# Bumps Dependabot / lockfile — sem entrega visível ao usuário (#1048 follow-up)
DEPS_MANIFESTS = frozenset(
    {
        "frontend/package.json",
        "frontend/package-lock.json",
        "backend/requirements.txt",
        "backend/requirements-dev.txt",
    }
)

# Paths tipicamente do control-plane SaaS (#673)
SAAS_PATH_MARKERS = (
    "frontend/src/pages/saas/",
    "frontend/src/lib/saasControlPlane",
    "backend/app/api/saas",
    "backend/app/services/saas_",
    "backend/app/models/cliente_saas",
    "backend/app/models/saas_",
    "backend/app/schemas/saas",
    "backend/tests/test_saas",
    "deploy/scripts/saas-",
    "deploy/scripts/stack-client",
)


def _run(*args: str) -> str:
    r = subprocess.run(args, capture_output=True, text=True, check=False, cwd=ROOT)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip() or r.stdout.strip() or f"comando falhou: {args}")
    return r.stdout


def changed_files(base: str, head: str) -> list[str]:
    out = _run("git", "diff", "--name-only", f"{base}...{head}")
    return [ln.strip() for ln in out.splitlines() if ln.strip()]


def is_staging_base(base: str) -> bool:
    ref = base.removeprefix("origin/").strip()
    return ref == "staging"


def changelog_after_simulated_merge(base: str, head: str) -> tuple[str | None, str | None]:
    """Simula merge base←head e devolve CHANGELOG.md resultante (ou erro de conflito)."""
    import tempfile

    base_sha = _run("git", "rev-parse", base).strip()
    head_sha = _run("git", "rev-parse", head).strip()
    wt: Path | None = None
    try:
        td = tempfile.mkdtemp(prefix="dx-changelog-merge-")
        wt = Path(td) / "wt"
        _run("git", "worktree", "add", str(wt), base_sha)
        merge = subprocess.run(
            ["git", "merge", "--no-commit", "--no-ff", head_sha],
            cwd=wt,
            capture_output=True,
            text=True,
            check=False,
        )
        if merge.returncode != 0:
            return None, (
                "Merge simulado falhou (conflitos entre base e head). "
                "Para release staging, abra branch `merge/main-into-staging-…`, resolva CHANGELOG "
                "mantendo os bullets de [Unreleased] da main e abra PR → staging."
            )
        cl = wt / "CHANGELOG.md"
        return (cl.read_text(encoding="utf-8") if cl.is_file() else ""), None
    finally:
        if wt is not None:
            subprocess.run(
                ["git", "worktree", "remove", "--force", str(wt)],
                cwd=ROOT,
                capture_output=True,
                check=False,
            )
            parent = wt.parent
            if parent.exists():
                import shutil

                shutil.rmtree(parent, ignore_errors=True)


def _norm_path(path: str) -> str:
    return path.replace("\\", "/")


def is_deps_only_change(paths: list[str]) -> bool:
    """True quando o diff (fora de SKIP_PREFIXES) só toca manifests de dependências."""
    relevant: list[str] = []
    for p in paths:
        norm = _norm_path(p)
        if any(norm.startswith(s) for s in SKIP_PREFIXES):
            continue
        relevant.append(norm)
    return bool(relevant) and all(p in DEPS_MANIFESTS for p in relevant)


def is_tests_only_change(paths: list[str]) -> bool:
    """True quando o diff (fora de SKIP_PREFIXES) só toca ``backend/tests/``."""
    relevant: list[str] = []
    for p in paths:
        norm = _norm_path(p)
        if any(norm.startswith(s) for s in SKIP_PREFIXES):
            continue
        relevant.append(norm)
    return bool(relevant) and all(p.startswith("backend/tests/") for p in relevant)


def requires_changelog(paths: list[str]) -> bool:
    if is_deps_only_change(paths) or is_tests_only_change(paths):
        return False
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


def is_saas_path(path: str) -> bool:
    p = path.replace("\\", "/")
    return any(p.startswith(m) or m in p for m in SAAS_PATH_MARKERS)


def products_required_by_paths(paths: list[str]) -> set[str]:
    """Heurística: paths SaaS → saas; demais de produto → deskrudder."""
    needed: set[str] = set()
    for p in paths:
        if any(p.startswith(s) for s in SKIP_PREFIXES):
            continue
        is_product = (
            any(p.startswith(prefix) for prefix in PRODUCT_PREFIXES)
            or p.startswith("backend/")
            or p.startswith("frontend/")
            or (p.startswith("scripts/") and "check_changelog" not in p)
        )
        if not is_product:
            continue
        if is_saas_path(p):
            needed.add(PRODUCT_SAAS)
        else:
            needed.add(PRODUCT_DESKRUDDER)
    return needed


def parse_unreleased_bullets(text: str) -> list[str]:
    return [c["text"] for c in parse_changelog_unreleased(text, warn_legacy=False)]


def bullets_by_product(text: str) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {PRODUCT_DESKRUDDER: [], PRODUCT_SAAS: []}
    for c in parse_changelog_unreleased(text, warn_legacy=False):
        out.setdefault(c["product"], []).append(c["text"])
    return out


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

    if not requires_changelog(paths) and not is_staging_base(args.base):
        print("OK: alterações só em arquivos isentos — CHANGELOG não exigido.")
        if is_deps_only_change(paths):
            print("(somente manifests de dependências)")
        elif is_tests_only_change(paths):
            print("(somente testes backend)")
        print("Arquivos:", ", ".join(paths[:12]) + ("…" if len(paths) > 12 else ""))
        return 0

    if is_staging_base(args.base):
        text, merge_err = changelog_after_simulated_merge(args.base, args.head)
        if merge_err:
            print(f"::error::{merge_err}", file=sys.stderr)
            return 1
        if text is None:
            print("::error::Não foi possível simular merge para validar CHANGELOG.", file=sys.stderr)
            return 1
    else:
        try:
            text = _run("git", "show", f"{args.head}:{args.changelog.relative_to(ROOT).as_posix()}")
        except RuntimeError:
            text = args.changelog.read_text(encoding="utf-8") if args.changelog.is_file() else ""

    bullets = parse_unreleased_bullets(text)
    if not bullets:
        staging_hint = (
            "\nPR → staging: confira o CHANGELOG **após merge simulado** — conflitos costumam esvaziar [Unreleased]."
            if is_staging_base(args.base)
            else ""
        )
        print(
            "::error::Este PR altera código de produto, mas CHANGELOG.md não tem bullets em ## [Unreleased].\n"
            "Adicione entregas sob ### DeskRudder e/ou ### SaaS Control Plane, ex.:\n"
            "  ### DeskRudder\n"
            "  #### Melhorias\n"
            "  - Descrição curta da funcionalidade (#123)\n"
            f"Veja docs/RELEASES.md{staging_hint}",
            file=sys.stderr,
        )
        print("Arquivos de produto no diff:", ", ".join(paths[:20]), file=sys.stderr)
        return 1

    needed = products_required_by_paths(paths)
    by_prod = bullets_by_product(text)
    missing = [p for p in sorted(needed) if not by_prod.get(p)]
    if missing:
        labels = {
            PRODUCT_DESKRUDDER: "### DeskRudder",
            PRODUCT_SAAS: "### SaaS Control Plane",
        }
        want = ", ".join(labels[p] for p in missing)
        print(
            f"::error::Este PR altera código de {', '.join(missing)}, mas CHANGELOG [Unreleased] "
            f"não tem bullets na(s) subseção(ões) {want}.\n"
            "Separe notas por produto (docs/RELEASES.md — «Dois produtos, um deploy»).",
            file=sys.stderr,
        )
        print("Arquivos no diff:", ", ".join(paths[:20]), file=sys.stderr)
        return 1

    parts = [f"{p}={len(by_prod.get(p, []))}" for p in sorted(needed or by_prod.keys())]
    suffix = " (merge simulado)" if is_staging_base(args.base) else ""
    print(f"OK: CHANGELOG [Unreleased] com {len(bullets)} item(ns) ({', '.join(parts)}){suffix}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
