"""Testes do migrador de product no manifest (#676)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from migrate_release_notes_product import classify_product, migrate_manifest  # noqa: E402


def test_classify_saas_prefix():
    assert classify_product("SaaS: licenças") == "saas"
    assert classify_product("SaaS DeskRudder (#519): painel") == "saas"
    assert classify_product("WhatsApp: fila") == "deskrudder"
    assert classify_product("Comercial (#321): simulador") == "deskrudder"


def test_migrate_manifest_idempotent():
    data = {
        "releases": [
            {
                "version": "26.08.006",
                "changes": [
                    {"category": "melhorias", "text": "SaaS: planos"},
                    {"category": "correcoes", "text": "Chat (#651)"},
                    {"product": "saas", "category": "melhorias", "text": "SaaS: já tagueado"},
                ],
            }
        ]
    }
    migrated, stats = migrate_manifest(data)
    changes = migrated["releases"][0]["changes"]
    assert changes[0]["product"] == "saas"
    assert changes[1]["product"] == "deskrudder"
    assert changes[2]["product"] == "saas"
    assert stats["saas"] == 2
    assert stats["deskrudder"] == 1
    again, stats2 = migrate_manifest(migrated)
    assert again == migrated
    assert stats2["kept"] == 3


def test_migrate_reclassify_saas_overrides_wrong_tag():
    data = {
        "releases": [
            {
                "version": "26.08.006",
                "changes": [
                    {"product": "deskrudder", "category": "melhorias", "text": "SaaS: planos"},
                    {"product": "deskrudder", "category": "correcoes", "text": "Chat (#651)"},
                ],
            }
        ]
    }
    migrated, stats = migrate_manifest(data, reclassify_saas=True)
    changes = migrated["releases"][0]["changes"]
    assert changes[0]["product"] == "saas"
    assert changes[1]["product"] == "deskrudder"
    assert stats["reclassified_to_saas"] == 1
    assert stats["saas"] == 1
    assert stats["deskrudder"] == 1
