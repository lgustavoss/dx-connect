"""Testes de versão CalVer e API system (#401)."""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from app.services.system_release import (
    reload_release_notes_cache,
    resolve_app_version,
    sanitize_release_text,
    version_display,
)

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from bump_calver import next_calver  # noqa: E402


def test_version_display():
    assert version_display("26.06.001") == "v26.06.001"
    assert version_display("v26.06.001") == "v26.06.001"


def test_next_calver_same_month():
    sp = datetime(2026, 6, 15, tzinfo=ZoneInfo("America/Sao_Paulo"))
    assert next_calver("26.06.000", now=sp) == "26.06.001"
    assert next_calver("26.06.009", now=sp) == "26.06.010"


def test_next_calver_new_month():
    sp = datetime(2026, 7, 1, tzinfo=ZoneInfo("America/Sao_Paulo"))
    assert next_calver("26.06.010", now=sp) == "26.07.001"


def test_resolve_app_version_env(monkeypatch):
    monkeypatch.setenv("DX_CONNECT_VERSION", "26.06.042")
    assert resolve_app_version() == "26.06.042"


def test_release_notes_sem_version_file_usa_json(client, auth_headers, monkeypatch, tmp_path):
    """Docker local não monta o VERSION da raiz — as notas continuam visíveis (#856)."""
    monkeypatch.delenv("DX_CONNECT_VERSION", raising=False)
    data_path = tmp_path / "release_notes.json"
    data_path.write_text(
        json.dumps(
            {
                "current_version": "26.08.006",
                "releases": [
                    {
                        "version": "26.08.006",
                        "version_display": "v26.08.006",
                        "date": "2026-08-12",
                        "status": "published",
                        "changes": [
                            {"product": "deskrudder", "category": "melhorias", "text": "Notas visíveis em local"}
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    import app.services.system_release as sr

    monkeypatch.setattr(sr, "_DATA_DIR", tmp_path)
    monkeypatch.setattr(sr, "_read_version_file", lambda: None)
    reload_release_notes_cache()

    info = client.get("/v1/system/info", headers=auth_headers["a1"])
    assert info.status_code == 200
    assert info.json()["version"] == "26.08.006"
    assert info.json()["version_display"] == "v26.08.006"

    notes = client.get("/v1/system/release-notes", headers=auth_headers["a1"])
    assert notes.status_code == 200, notes.text
    body = notes.json()
    assert body["current"] is not None
    assert body["current"]["version"] == "26.08.006"
    assert any("visíveis em local" in c["text"] for c in body["current"]["changes"])


def test_system_info_requires_auth(client):
    r = client.get("/v1/system/info")
    assert r.status_code == 401


def test_system_release_notes_requires_auth(client):
    r = client.get("/v1/system/release-notes")
    assert r.status_code == 401


def test_system_info_authenticated(client, auth_headers, monkeypatch):
    monkeypatch.setenv("DX_CONNECT_VERSION", "26.06.099")
    monkeypatch.setenv("DX_CONNECT_GIT_SHA", "abc1234")
    r = client.get("/v1/system/info", headers=auth_headers["a1"])
    assert r.status_code == 200
    body = r.json()
    assert body["version"] == "26.06.099"
    assert body["version_display"] == "v26.06.099"
    assert body["git_sha"] == "abc1234"
    assert body["environment"]


def test_system_release_notes_filters_stale_upcoming(client, auth_headers, monkeypatch, tmp_path):
    data_path = tmp_path / "release_notes.json"
    release = {
        "version": "26.06.001",
        "version_display": "v26.06.001",
        "date": "2026-06-22",
        "status": "published",
        "changes": [{"category": "melhorias", "text": "Distribuição (#399)"}],
    }
    payload = {
        "current_version": "26.06.001",
        "releases": [release],
        "upcoming": [
            {"category": "melhorias", "text": "feat(releases): CalVer (#404)"},
        ],
    }
    data_path.write_text(json.dumps(payload), encoding="utf-8")

    import app.services.system_release as sr

    monkeypatch.setattr(sr, "_DATA_DIR", tmp_path)
    reload_release_notes_cache()
    monkeypatch.setenv("DX_CONNECT_VERSION", "26.06.001")

    body = client.get("/v1/system/release-notes", headers=auth_headers["admin"]).json()
    assert body["upcoming"] == []


def test_system_release_notes_authenticated(client, auth_headers, monkeypatch, tmp_path):
    data_path = tmp_path / "release_notes.json"
    payload = {
        "current_version": "26.06.001",
        "current_version_display": "v26.06.001",
        "current": {
            "version": "26.06.001",
            "version_display": "v26.06.001",
            "date": "2026-06-17",
            "status": "published",
            "changes": [{"category": "melhorias", "text": "Teste"}],
        },
        "releases": [
            {
                "version": "26.06.001",
                "version_display": "v26.06.001",
                "date": "2026-06-17",
                "status": "published",
                "changes": [{"category": "melhorias", "text": "Teste"}],
            }
        ],
        "upcoming": [{"category": "melhorias", "text": "Relatórios CSV (#390)"}],
    }
    data_path.write_text(json.dumps(payload), encoding="utf-8")

    import app.services.system_release as sr

    monkeypatch.setattr(sr, "_DATA_DIR", tmp_path)
    reload_release_notes_cache()
    monkeypatch.setenv("DX_CONNECT_VERSION", "26.06.001")

    r = client.get("/v1/system/release-notes", headers=auth_headers["admin"])
    assert r.status_code == 200
    body = r.json()
    assert body["current_version"] == "26.06.001"
    assert body["current"]["changes"][0]["text"] == "Teste"
    assert body["upcoming"] == []


def test_sanitize_release_text_removes_legacy_brand():
    raw = (
        "Identidade visual (#434): painel lateral do login e assets legados "
        "DX/Duplexsoft removidos — marca DeskRudder em todo o painel"
    )
    assert sanitize_release_text(raw) == (
        "Identidade visual (#434): marca DeskRudder no login e em todo o painel"
    )
    assert "DX" not in sanitize_release_text(raw)
    assert "Duplexsoft" not in sanitize_release_text(raw)


def test_system_release_notes_sanitize_legacy_brand(client, auth_headers, monkeypatch, tmp_path):
    data_path = tmp_path / "release_notes.json"
    legacy = (
        "Identidade visual (#434): painel lateral do login e assets legados "
        "DX/Duplexsoft removidos — marca DeskRudder em todo o painel"
    )
    payload = {
        "current_version": "26.07.001",
        "releases": [
            {
                "version": "26.07.001",
                "version_display": "v26.07.001",
                "date": "2026-07-11",
                "status": "published",
                "changes": [{"category": "melhorias", "text": legacy}],
            }
        ],
        "upcoming": [],
    }
    data_path.write_text(json.dumps(payload), encoding="utf-8")

    import app.services.system_release as sr

    monkeypatch.setattr(sr, "_DATA_DIR", tmp_path)
    reload_release_notes_cache()
    monkeypatch.setenv("DX_CONNECT_VERSION", "26.07.001")

    body = client.get("/v1/system/release-notes", headers=auth_headers["admin"]).json()
    text = body["releases"][0]["changes"][0]["text"]
    assert "DX" not in text
    assert "Duplexsoft" not in text
    assert "DeskRudder" in text


def test_system_release_notes_filters_by_product(client, auth_headers, monkeypatch, tmp_path):
    data_path = tmp_path / "release_notes.json"
    payload = {
        "current_version": "26.08.006",
        "current_version_display": "v26.08.006",
        "releases": [
            {
                "version": "26.08.006",
                "version_display": "v26.08.006",
                "date": "2026-08-13",
                "status": "published",
                "changes": [
                    {"product": "deskrudder", "category": "correcoes", "text": "Chat fila"},
                    {"product": "saas", "category": "melhorias", "text": "SaaS: licenças"},
                ],
            }
        ],
        "upcoming": [],
    }
    data_path.write_text(json.dumps(payload), encoding="utf-8")

    import app.services.system_release as sr

    monkeypatch.setattr(sr, "_DATA_DIR", tmp_path)
    reload_release_notes_cache()
    monkeypatch.setenv("DX_CONNECT_VERSION", "26.08.006")

    body = client.get("/v1/system/release-notes", headers=auth_headers["admin"]).json()
    texts = [c["text"] for c in body["current"]["changes"]]
    assert texts == ["Chat fila"]
    assert all(c.get("product") == "deskrudder" for c in body["current"]["changes"])


def test_system_release_notes_hides_saas_prefix_even_if_wrongly_tagged(
    client, auth_headers, monkeypatch, tmp_path
):
    """Histórico em produção: bullet «SaaS:…» sem tag ou com product=deskrudder."""
    data_path = tmp_path / "release_notes.json"
    payload = {
        "current_version": "26.08.006",
        "releases": [
            {
                "version": "26.08.006",
                "version_display": "v26.08.006",
                "date": "2026-08-13",
                "status": "published",
                "changes": [
                    {"category": "melhorias", "text": "WhatsApp: fila"},
                    {"product": "deskrudder", "category": "melhorias", "text": "SaaS: licenças"},
                    {"category": "melhorias", "text": "SaaS DeskRudder (#519): painel"},
                ],
            }
        ],
        "upcoming": [],
    }
    data_path.write_text(json.dumps(payload), encoding="utf-8")

    import app.services.system_release as sr

    monkeypatch.setattr(sr, "_DATA_DIR", tmp_path)
    reload_release_notes_cache()
    monkeypatch.setenv("DX_CONNECT_VERSION", "26.08.006")

    body = client.get("/v1/system/release-notes", headers=auth_headers["admin"]).json()
    texts = [c["text"] for c in body["current"]["changes"]]
    assert texts == ["WhatsApp: fila"]


def test_saas_release_notes_rbac_and_all_products(client, auth_headers, monkeypatch, tmp_path):
    from app.config import settings

    data_path = tmp_path / "release_notes.json"
    payload = {
        "current_version": "26.08.006",
        "releases": [
            {
                "version": "26.08.006",
                "version_display": "v26.08.006",
                "date": "2026-08-13",
                "status": "published",
                "changes": [
                    {"product": "deskrudder", "category": "correcoes", "text": "Chat fila"},
                    {"product": "saas", "category": "melhorias", "text": "SaaS: licenças"},
                ],
            }
        ],
        "upcoming": [],
    }
    data_path.write_text(json.dumps(payload), encoding="utf-8")

    import app.services.system_release as sr

    monkeypatch.setattr(sr, "_DATA_DIR", tmp_path)
    reload_release_notes_cache()
    monkeypatch.setenv("DX_CONNECT_VERSION", "26.08.006")
    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)

    assert client.get("/v1/saas/release-notes", headers=auth_headers["a1"]).status_code == 403
    assert client.get("/v1/saas/release-notes", headers=auth_headers["admin"]).status_code == 403

    ok = client.get("/v1/saas/release-notes", headers=auth_headers["ops"])
    assert ok.status_code == 200, ok.text
    changes = ok.json()["current"]["changes"]
    assert [(c["text"], c["product"]) for c in changes] == [
        ("Chat fila", "deskrudder"),
        ("SaaS: licenças", "saas"),
    ]


def test_health_includes_version(client, monkeypatch):
    monkeypatch.setenv("DX_CONNECT_VERSION", "26.06.000")
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json().get("version") == "26.06.000"
    caps = r.json()["capabilities"]
    assert caps["system_info"] is True
    assert caps["system_release_notes"] is True
