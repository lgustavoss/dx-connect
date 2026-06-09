"""Simulacao local de classificacao/prioridade (#107/#108). Uso: python scripts/simular_classificacao_local.py"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from datetime import datetime

BASE = "http://localhost:8000/v1"
ERROS = 0


def req(method: str, path: str, token: str | None = None, body: dict | None = None):
    url = f"{BASE}{path}"
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            detail = json.loads(raw)
        except json.JSONDecodeError:
            detail = {"detail": raw}
        return e.code, detail


def ok(msg: str):
    print(f"[OK] {msg}")


def fail(msg: str, extra: str = ""):
    global ERROS
    ERROS += 1
    print(f"[FALHA] {msg}" + (f" -- {extra}" if extra else ""))


def login(email: str, senha: str) -> str:
    _, data = req("POST", "/auth/login", body={"email": email, "senha": senha})
    return data["access_token"]


def main() -> int:
    token = login("admin@email.com", "admin123")

    _, naturezas = req("GET", "/ticket-naturezas?limit=20", token)
    _, motivos = req("GET", "/ticket-motivos?limit=50", token)
    nat_items = naturezas["items"]
    mot_items = motivos["items"]

    nat_by_slug = {n["slug"]: n for n in nat_items}
    mot_by_key = {(m["natureza_id"], m["slug"]): m for m in mot_items}

    if len(nat_items) >= 3 and len(mot_items) >= 9:
        ok(f"Catalogos seed ({len(nat_items)} naturezas, {len(mot_items)} motivos)")
    else:
        fail("Catalogos seed", f"n={len(nat_items)} m={len(mot_items)}")

    _, empresas = req("GET", "/empresas?limit=1", token)
    _, setores = req("GET", "/setores?limit=1", token)
    _, statuses = req("GET", "/status-ticket?limit=50", token)
    empresa_id = empresas["items"][0]["id"]
    setor_id = setores["items"][0]["id"]
    status_fechado = next(s for s in statuses["items"] if s["slug"] == "fechado")

    def novo_ticket(prioridade: str = "normal") -> dict:
        _, t = req(
            "POST",
            "/tickets",
            token,
            {
                "empresa_id": empresa_id,
                "setor_id": setor_id,
                "assunto": f"Sim {prioridade} {datetime.now():%H%M%S}",
                "descricao": "Simulacao automatica",
                "prioridade": prioridade,
            },
        )
        return t

    def patch_ticket(tid: int, patch: dict) -> tuple[int, dict | None]:
        return req("PATCH", f"/tickets/{tid}", token, patch)

    # Prioridades
    for p in ("baixa", "normal", "alta", "urgente"):
        t = novo_ticket(p)
        if t.get("prioridade") == p:
            ok(f"Criar prioridade={p} (#{t['id']})")
        else:
            fail(f"Prioridade {p}", str(t.get("prioridade")))

    code, _ = req(
        "POST",
        "/tickets",
        token,
        {
            "empresa_id": empresa_id,
            "setor_id": setor_id,
            "assunto": "x",
            "prioridade": "critica",
        },
    )
    if code in (400, 422):
        ok("Rejeita prioridade invalida")
    else:
        fail("Prioridade invalida", f"code={code}")

    # Classificacao opcional aberto
    t_ab = novo_ticket()
    m_op = mot_by_key[(nat_by_slug["duvida"]["id"], "operacional")]
    _, u = patch_ticket(t_ab["id"], {"motivo_id": m_op["id"]})
    if u.get("motivo_nome") == "Operacional" and u.get("natureza_nome") == "Dúvida":
        ok("Classificacao opcional em aberto")
    else:
        fail("Classificacao aberto", f"{u.get('natureza_nome')} / {u.get('motivo_nome')}")

    # Fechar sem motivo
    t_sem = novo_ticket("baixa")
    code, err = patch_ticket(t_sem["id"], {"status_id": status_fechado["id"]})
    if code == 400 and "motivo" in str(err.get("detail", "")).lower():
        ok("Fechar sem motivo rejeitado")
    else:
        fail("Fechar sem motivo", f"code={code} {err}")

    # Fechar cada motivo (Outros exige texto)
    for n in nat_items:
        for m in [x for x in mot_items if x["natureza_id"] == n["id"]]:
            t = novo_ticket()
            patch = {"status_id": status_fechado["id"], "motivo_id": m["id"]}
            if m["slug"] == "outros":
                code, err = patch_ticket(t["id"], patch)
                if code != 400:
                    fail(f"Outros sem texto ({n['nome']})", f"code={code}")
                    continue
                patch["motivo_outro_texto"] = f"Detalhe sim {n['slug']}"
            _, closed = patch_ticket(t["id"], patch)
            if closed and closed.get("fechado_em") and closed.get("motivo_id") == m["id"]:
                ok(f"Fechar {n['nome']} -> {m['nome']}")
            else:
                fail(f"Fechar {n['nome']} -> {m['nome']}")

    # Texto complementar fora de Outros
    t_txt = novo_ticket()
    m_falha = mot_by_key[(nat_by_slug["erro"]["id"], "falha-pdv")]
    code, err = patch_ticket(
        t_txt["id"],
        {"motivo_id": m_falha["id"], "motivo_outro_texto": "nao permitido"},
    )
    if code == 400:
        ok("Texto complementar so em Outros")
    else:
        fail("Texto complementar", f"code={code}")

    # Admin altera fechado
    t_adm = novo_ticket()
    m1 = mot_by_key[(nat_by_slug["erro"]["id"], "falha-pdv")]
    patch_ticket(t_adm["id"], {"status_id": status_fechado["id"], "motivo_id": m1["id"]})
    m2 = mot_by_key[(nat_by_slug["duvida"]["id"], "fiscal")]
    _, alt = patch_ticket(t_adm["id"], {"motivo_id": m2["id"], "prioridade": "urgente"})
    if alt.get("prioridade") == "urgente" and alt.get("motivo_nome") == "Fiscal":
        ok("Admin altera prioridade/motivo em fechado")
    else:
        fail("Admin altera fechado")

    # CRUD catalogo
    slug_n = f"sim-nat-{datetime.now():%H%M%S}"
    _, nova = req(
        "POST",
        "/ticket-naturezas",
        token,
        {"nome": "Sim Natureza", "slug": slug_n, "ordem": 50, "ativo": True},
    )
    _, novo_m = req(
        "POST",
        "/ticket-motivos",
        token,
        {
            "natureza_id": nova["id"],
            "nome": "Sim Motivo",
            "slug": "sim-mot",
            "ordem": 1,
            "ativo": True,
        },
    )
    if nova.get("id") and novo_m.get("id"):
        ok("Admin CRUD natureza/motivo")
    else:
        fail("Admin CRUD")

    # Duplicado com motivo
    t_orig = novo_ticket("alta")
    t_dup = novo_ticket("alta")
    _, v = req(
        "POST",
        f"/tickets/{t_dup['id']}/vinculos",
        token,
        {
            "related_ticket_id": t_orig["id"],
            "tipo": "duplicado_de",
            "fechar_como_duplicado": True,
            "motivo_id": m1["id"],
        },
    )
    _, dup_closed = req("GET", f"/tickets/{t_dup['id']}", token)
    if v.get("duplicado_fechado") and dup_closed.get("fechado_em") and dup_closed.get("motivo_id") == m1["id"]:
        ok("Duplicado fecha com motivo")
    else:
        fail("Duplicado com motivo")

    # Duplicado sem motivo
    t_d2 = novo_ticket()
    t_d3 = novo_ticket()
    code, _ = req(
        "POST",
        f"/tickets/{t_d3['id']}/vinculos",
        token,
        {
            "related_ticket_id": t_d2["id"],
            "tipo": "duplicado_de",
            "fechar_como_duplicado": True,
        },
    )
    if code == 400:
        ok("Duplicado sem motivo rejeitado")
    else:
        fail("Duplicado sem motivo", f"code={code}")

    # Relacionado sem fechar
    t_r1 = novo_ticket("baixa")
    t_r2 = novo_ticket("baixa")
    _, rel = req(
        "POST",
        f"/tickets/{t_r1['id']}/vinculos",
        token,
        {"related_ticket_id": t_r2["id"], "tipo": "relacionado_a"},
    )
    _, rel_open = req("GET", f"/tickets/{t_r1['id']}", token)
    if rel.get("tipo") == "relacionado_a" and not rel_open.get("fechado_em"):
        ok("Relacionado mantem aberto (sem motivo)")
    else:
        fail("Relacionado")

    # Duplicado sem fechar (mantem aberto)
    t_df1 = novo_ticket()
    t_df2 = novo_ticket()
    _, v2 = req(
        "POST",
        f"/tickets/{t_df2['id']}/vinculos",
        token,
        {
            "related_ticket_id": t_df1["id"],
            "tipo": "duplicado_de",
            "fechar_como_duplicado": False,
        },
    )
    _, df_open = req("GET", f"/tickets/{t_df2['id']}", token)
    if not v2.get("duplicado_fechado") and not df_open.get("fechado_em"):
        ok("Duplicado sem fechar (sem motivo)")
    else:
        fail("Duplicado sem fechar")

    _, lista = req("GET", "/tickets?situacao=fechados&limit=5", token)
    item = lista["items"][0] if lista.get("items") else {}
    if "prioridade" in item:
        ok("Lista retorna prioridade")
    else:
        fail("Lista prioridade")

    print()
    if ERROS == 0:
        print(
            f"Simulacao API: {len(nat_items)} naturezas, {len(mot_items)} motivos, "
            "4 prioridades, duplicado/relacionado — 0 falhas."
        )
        return 0
    print(f"Simulacao API: {ERROS} falha(s).")
    return 1


if __name__ == "__main__":
    sys.exit(main())
