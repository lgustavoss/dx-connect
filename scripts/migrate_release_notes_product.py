#!/usr/bin/env python3
"""
Migra docs/releases/manifest.json com campo product por bullet (#676).

Idempotente: bullets já com product válido são preservados.
Heurística: texto que começa com «SaaS» → saas; resto → deskrudder.

Uso:
  python scripts/migrate_release_notes_product.py
  python scripts/migrate_release_notes_product.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from prepare_release import (  # noqa: E402
    PRODUCT_DESKRUDDER,
    PRODUCT_SAAS,
    ROOT,
    build_payload,
    write_release_notes,
)

MANIFEST_FILE = ROOT / "docs" / "releases" / "manifest.json"
VERSION_FILE = ROOT / "VERSION"

_SAAS_PREFIX = re.compile(r"(?i)^saas\b")


def classify_product(text: str) -> str:
    if _SAAS_PREFIX.match((text or "").strip()):
        return PRODUCT_SAAS
    return PRODUCT_DESKRUDDER


def migrate_manifest(data: dict, *, reclassify_saas: bool = False) -> tuple[dict, dict[str, int]]:
    """
    Tagua bullets com product.

    - Default: preserva product já válido; só classifica os sem tag.
    - reclassify_saas=True: texto com prefixo «SaaS» → saas mesmo se estava deskrudder
      (corrige histórico publicado antes da separação por produto).
    """
    stats = {
        "saas": 0,
        "deskrudder": 0,
        "kept": 0,
        "total": 0,
        "reclassified_to_saas": 0,
    }
    releases = []
    for rel in data.get("releases") or []:
        entry = dict(rel)
        changes = []
        for ch in entry.get("changes") or []:
            if not isinstance(ch, dict):
                changes.append(ch)
                continue
            item = dict(ch)
            stats["total"] += 1
            existing = item.get("product")
            inferred = classify_product(str(item.get("text") or ""))

            if reclassify_saas and inferred == PRODUCT_SAAS and existing != PRODUCT_SAAS:
                item["product"] = PRODUCT_SAAS
                stats["reclassified_to_saas"] += 1
                stats["saas"] += 1
            elif existing in (PRODUCT_DESKRUDDER, PRODUCT_SAAS):
                stats["kept"] += 1
                stats[existing] += 1
            else:
                item["product"] = inferred
                stats[inferred] += 1
            changes.append(item)
        entry["changes"] = changes
        releases.append(entry)
    return {"releases": releases}, stats


def main() -> int:
    ap = argparse.ArgumentParser(description="Classifica bullets do manifest com product (#676)")
    ap.add_argument("--dry-run", action="store_true", help="Só imprime estatísticas")
    ap.add_argument("--no-write-json", action="store_true", help="Não regenera release_notes.json")
    ap.add_argument(
        "--reclassify-saas",
        action="store_true",
        help="Força product=saas em bullets com prefixo «SaaS» (mesmo se tagueados DeskRudder)",
    )
    args = ap.parse_args()

    if not MANIFEST_FILE.is_file():
        print(f"::error::{MANIFEST_FILE} não encontrado", file=sys.stderr)
        return 1

    raw = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
    migrated, stats = migrate_manifest(raw, reclassify_saas=args.reclassify_saas)
    print(
        f"Bullets: total={stats['total']} deskrudder={stats['deskrudder']} "
        f"saas={stats['saas']} (ja tinham product={stats['kept']}, "
        f"reclassificados->saas={stats['reclassified_to_saas']})"
    )

    if args.dry_run:
        return 0

    MANIFEST_FILE.write_text(json.dumps(migrated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Atualizado: {MANIFEST_FILE.relative_to(ROOT)}")

    if not args.no_write_json:
        version = VERSION_FILE.read_text(encoding="utf-8").strip() if VERSION_FILE.is_file() else None
        payload = build_payload(current_version=version or None, manifest=migrated, upcoming=[])
        write_release_notes(payload)
        print("Regenerados: backend/app/data/release_notes.json e frontend/public/release-notes.json")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
