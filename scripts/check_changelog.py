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
    CATEGORY_TITLE,
    PRODUCT_DESKRUDDER,
    PRODUCT_SAAS,
    PRODUCT_TITLE,
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
    "scripts/prepare_release.py",
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
    "backend/tests/test_control_plane",
    "backend/tests/test_deploy_dual_stack",
    "deploy/admin-center/",
    "deploy/scripts/provision-control-plane",
    "deploy/scripts/gha-deploy-vps",
    "deploy/scripts/saas-",
    "deploy/scripts/stack-client",
)


def _run(*args: str) -> str:
    r = subprocess.run(
        args,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        cwd=ROOT,
    )
    if r.returncode != 0:
        raise RuntimeError((r.stderr or "").strip() or (r.stdout or "").strip() or f"comando falhou: {args}")
    return r.stdout or ""


def changed_files(base: str, head: str) -> list[str]:
    out = _run("git", "diff", "--name-only", f"{base}...{head}")
    return [ln.strip() for ln in out.splitlines() if ln.strip()]


_UNRELEASED_SECTION = re.compile(
    r"(## \[Unreleased\].*?)(?=\n## \[|\Z)",
    re.DOTALL | re.IGNORECASE,
)
_PUBLISHED_START = re.compile(r"\n## \[\d", re.MULTILINE)

# Cabeçalhos de [Unreleased] (mais curtos que as tags do manifest).
_UNRELEASED_CATEGORY_TITLE = {
    "melhorias": "Melhorias",
    "correcoes": "Correções",
    "interno": "Interno",
}


def is_staging_base(base: str, pr_base_ref: str | None = None) -> bool:
    if pr_base_ref and pr_base_ref.strip().removeprefix("origin/") == "staging":
        return True
    ref = base.removeprefix("origin/").strip()
    if ref == "staging":
        return True
    try:
        staging_sha = _run("git", "rev-parse", "--verify", "origin/staging").strip()
        base_sha = _run("git", "rev-parse", "--verify", base).strip()
    except RuntimeError:
        return False
    return bool(staging_sha) and staging_sha == base_sha


def extract_changelog_preamble(text: str) -> str:
    m = re.search(r"^(.*?)(?=^## \[Unreleased\])", text, re.DOTALL | re.IGNORECASE | re.MULTILINE)
    return m.group(1) if m else "# Changelog\n\n"


def extract_unreleased_block(text: str) -> str:
    m = _UNRELEASED_SECTION.search(text)
    if not m:
        return "## [Unreleased]\n\n"
    return m.group(1).rstrip() + "\n\n"


def extract_published_history(text: str) -> str:
    m = _PUBLISHED_START.search(text)
    if not m:
        return ""
    return text[m.start() + 1 :]


def format_unreleased_section(changes: list[dict[str, str]]) -> str:
    """Reconstrói ## [Unreleased] a partir dos dicts de parse_changelog_unreleased."""
    if not changes:
        return "## [Unreleased]\n\n"
    by_product: dict[str, dict[str, list[str]]] = {}
    product_order: list[str] = []
    for c in changes:
        prod = c["product"]
        if prod not in by_product:
            by_product[prod] = {}
            product_order.append(prod)
        cat_title = _UNRELEASED_CATEGORY_TITLE.get(c["category"]) or CATEGORY_TITLE.get(
            c["category"], "Melhorias"
        )
        by_product[prod].setdefault(cat_title, []).append(c["text"])
    lines = ["## [Unreleased]", ""]
    for prod in product_order:
        lines.append(f"### {PRODUCT_TITLE.get(prod, prod)}")
        lines.append("")
        for cat_title, items in by_product[prod].items():
            lines.append(f"#### {cat_title}")
            lines.append("")
            for item in items:
                lines.append(f"- {item}")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n\n"


def compose_changelog_for_staging_pr(base_text: str, head_text: str) -> str:
    """Unreleased da head (lote a publicar) + histórico CalVer da staging.

    Evita ``git merge`` do repositório: o deploy esvazia [Unreleased] na staging e o
    3-way do Git conflita em todo release, mesmo com branch ``merge/…`` já resolvida.
    """
    preamble = extract_changelog_preamble(head_text) or extract_changelog_preamble(base_text)
    unreleased = extract_unreleased_block(head_text)
    published = extract_published_history(base_text) or extract_published_history(head_text)
    return preamble + unreleased + published


def compose_changelog_for_main_sync(main_text: str, staging_text: str) -> str:
    """Passo 5: histórico da staging; [Unreleased] só com bullets ainda não publicados."""
    published = extract_published_history(staging_text)
    leftover = [
        c
        for c in parse_changelog_unreleased(main_text, warn_legacy=False)
        if c["text"] not in published
    ]
    preamble = extract_changelog_preamble(staging_text) or extract_changelog_preamble(main_text)
    return preamble + format_unreleased_section(leftover) + published


def changelog_for_staging_pr(base: str, head: str) -> tuple[str | None, str | None]:
    """Lê CHANGELOG da base e da head e devolve o resultado composto (sem git merge)."""
    try:
        base_text = _run("git", "show", f"{base}:CHANGELOG.md")
        head_text = _run("git", "show", f"{head}:CHANGELOG.md")
    except RuntimeError as e:
        return None, f"Não foi possível ler CHANGELOG.md ({e})"
    return compose_changelog_for_staging_pr(base_text, head_text), None


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
        "--pr-base-ref",
        default="",
        help="Nome da branch base do PR (ex.: staging). Usado quando --base é um SHA.",
    )
    ap.add_argument(
        "--changelog",
        type=Path,
        default=CHANGELOG,
        help="Caminho do CHANGELOG (usa versão do head)",
    )
    args = ap.parse_args()
    staging_pr = is_staging_base(args.base, args.pr_base_ref or None)

    paths = changed_files(args.base, args.head)
    if not paths:
        print("OK: PR sem arquivos alterados — CHANGELOG não exigido.")
        return 0

    if not requires_changelog(paths) and not staging_pr:
        print("OK: alterações só em arquivos isentos — CHANGELOG não exigido.")
        if is_deps_only_change(paths):
            print("(somente manifests de dependências)")
        elif is_tests_only_change(paths):
            print("(somente testes backend)")
        print("Arquivos:", ", ".join(paths[:12]) + ("…" if len(paths) > 12 else ""))
        return 0

    if staging_pr:
        text, compose_err = changelog_for_staging_pr(args.base, args.head)
        if compose_err:
            print(f"::error::{compose_err}", file=sys.stderr)
            return 1
        if text is None:
            print("::error::Não foi possível compor CHANGELOG para validar [Unreleased].", file=sys.stderr)
            return 1
    else:
        try:
            text = _run("git", "show", f"{args.head}:{args.changelog.relative_to(ROOT).as_posix()}")
        except RuntimeError:
            text = args.changelog.read_text(encoding="utf-8") if args.changelog.is_file() else ""

    bullets = parse_unreleased_bullets(text)
    if not bullets:
        staging_hint = (
            "\nPR para staging: o [Unreleased] precisa estar na head (main/merge branch); "
            "não aceite o [Unreleased] vazio da staging."
            if staging_pr
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
    suffix = " (PR para staging: Unreleased da head)" if staging_pr else ""
    print(f"OK: CHANGELOG [Unreleased] com {len(bullets)} item(ns) ({', '.join(parts)}){suffix}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
