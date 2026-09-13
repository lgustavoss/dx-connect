#!/usr/bin/env python3
"""Passo 5 do release: alinha CHANGELOG.md da working tree com a staging.

Preserva em [Unreleased] só bullets da main que ainda não estão no histórico publicado.
Uso (na branch chore/sync-changelog-…, após ``git merge origin/staging`` ou em conflito):

    python scripts/sync_changelog_from_staging.py
    python scripts/sync_changelog_from_staging.py --staging-ref origin/staging
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from check_changelog import CHANGELOG, compose_changelog_for_main_sync  # noqa: E402


def _git_show(ref: str, path: str) -> str:
    r = subprocess.run(
        ["git", "show", f"{ref}:{path}"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if r.returncode != 0:
        raise SystemExit(r.stderr.strip() or f"falha ao ler {ref}:{path}")
    return r.stdout


def main() -> int:
    ap = argparse.ArgumentParser(description="Compõe CHANGELOG.md pós-deploy (staging → main)")
    ap.add_argument("--staging-ref", default="origin/staging")
    ap.add_argument("--main-file", type=Path, default=CHANGELOG)
    args = ap.parse_args()

    if not args.main_file.is_file():
        print(f"CHANGELOG não encontrado: {args.main_file}", file=sys.stderr)
        return 1

    main_text = args.main_file.read_text(encoding="utf-8")
    staging_text = _git_show(args.staging_ref, "CHANGELOG.md")
    composed = compose_changelog_for_main_sync(main_text, staging_text)
    args.main_file.write_text(composed, encoding="utf-8")
    print(f"OK: {args.main_file.relative_to(ROOT)} alinhado com {args.staging_ref}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
