#!/usr/bin/env python3
"""Classifica o diff: pytest backend e/ou build frontend (CI e /revisar-e-testar)."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Alterar o workflow de CI reexecuta os dois jobs (o YAML é a definição deles).
BACKEND_MARKERS = (
    "backend/",
    "scripts/",
    ".github/workflows/ci.yml",
)
FRONTEND_MARKERS = (
    "frontend/",
    ".github/workflows/ci.yml",
)


def normalize(path: str) -> str:
    p = path.replace("\\", "/").strip()
    while p.startswith("./"):
        p = p[2:]
    return p


def path_matches(path: str, markers: tuple[str, ...]) -> bool:
    p = normalize(path)
    for marker in markers:
        if marker.endswith("/"):
            if p.startswith(marker):
                return True
        elif p == marker:
            return True
    return False


def classify(paths: list[str]) -> dict[str, bool]:
    normalized = [normalize(p) for p in paths if p and p.strip()]
    return {
        "backend": any(path_matches(p, BACKEND_MARKERS) for p in normalized),
        "frontend": any(path_matches(p, FRONTEND_MARKERS) for p in normalized),
    }


def _git(*args: str) -> list[str]:
    r = subprocess.run(["git", *args], capture_output=True, text=True, check=False, cwd=ROOT)
    if r.returncode != 0:
        return []
    return [ln.strip() for ln in r.stdout.splitlines() if ln.strip()]


def git_changed_files(*, base: str, head: str, two_dot: bool, include_working_tree: bool) -> list[str]:
    spec = f"{base} {head}" if two_dot else f"{base}...{head}"
    files = set(_git("diff", "--name-only", *spec.split()))
    if include_working_tree:
        files.update(_git("diff", "--name-only"))
        files.update(_git("diff", "--cached", "--name-only"))
        files.update(_git("ls-files", "--others", "--exclude-standard"))
    return sorted(files)


def format_result(result: dict[str, bool]) -> str:
    return "\n".join(
        f"{key}={'true' if result[key] else 'false'}" for key in ("backend", "frontend")
    )


def write_github_output(result: dict[str, bool]) -> None:
    out = os.environ.get("GITHUB_OUTPUT")
    if not out:
        raise SystemExit("GITHUB_OUTPUT não definido (use sem --github-output localmente)")
    with open(out, "a", encoding="utf-8") as f:
        f.write(format_result(result) + "\n")


def _is_zero_sha(value: str | None) -> bool:
    if not value:
        return True
    return set(value) <= {"0"}


def classify_from_github_env() -> dict[str, bool]:
    event = os.environ.get("GITHUB_EVENT_NAME", "")
    if event == "workflow_dispatch":
        return {"backend": True, "frontend": True}

    if event == "pull_request":
        base = os.environ.get("PR_BASE_SHA") or ""
        head = os.environ.get("GITHUB_SHA") or "HEAD"
        if _is_zero_sha(base):
            return {"backend": True, "frontend": True}
        return classify(git_changed_files(base=base, head=head, two_dot=False, include_working_tree=False))

    if event == "push":
        before = os.environ.get("BEFORE") or ""
        head = os.environ.get("GITHUB_SHA") or "HEAD"
        if _is_zero_sha(before):
            return {"backend": True, "frontend": True}
        return classify(git_changed_files(base=before, head=head, two_dot=True, include_working_tree=False))

    raise SystemExit(f"Evento GitHub não suportado: {event!r}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Diz se o diff exige pytest backend e/ou build frontend")
    ap.add_argument("--base", default="origin/main", help="Ref base (uso local / três pontos)")
    ap.add_argument("--head", default="HEAD")
    ap.add_argument("--include-working-tree", action="store_true", help="Inclui staged, unstaged e untracked")
    ap.add_argument("--github-output", action="store_true", help="Escreve GITHUB_OUTPUT (Actions)")
    ap.add_argument("--all", action="store_true", help="Força backend e frontend")
    args = ap.parse_args(argv)

    if args.all:
        result = {"backend": True, "frontend": True}
    elif args.github_output:
        result = classify_from_github_env()
    else:
        files = git_changed_files(
            base=args.base,
            head=args.head,
            two_dot=False,
            include_working_tree=args.include_working_tree,
        )
        result = classify(files)

    text = format_result(result)
    if args.github_output:
        write_github_output(result)
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
