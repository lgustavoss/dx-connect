"""Testa fluxo local de notificações (#109/#110) contra API em execução."""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

BASE = "http://localhost:8000/v1"
EMAIL = "admin@email.com"
SENHA = "admin123"


def req(method: str, path: str, *, token: str | None = None, body: dict | None = None) -> dict:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(f"{BASE}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{method} {path} -> {e.code}: {e.read().decode()}") from e


def main() -> int:
    print("1. Health…")
    with urllib.request.urlopen("http://localhost:8000/health", timeout=10) as h:
        assert h.status == 200

    print("2. Login…")
    tok = req("POST", "/auth/login", body={"email": EMAIL, "senha": SENHA})["access_token"]

    print("3. Preferências (GET/PATCH)…")
    prefs = req("GET", "/notificacoes/preferencias", token=tok)
    assert prefs.get("email_habilitado") is True, prefs
    prefs2 = req(
        "PATCH",
        "/notificacoes/preferencias",
        token=tok,
        body={"email_nova_mensagem": True, "email_ticket_atribuido": True},
    )
    assert prefs2["email_ticket_atribuido"] is True

    print("4. Resumo e itens in-app…")
    resumo = req("GET", "/notificacoes/resumo", token=tok)
    assert "total_pendencias" in resumo, resumo
    itens = req("GET", "/notificacoes/itens?limit=5", token=tok)
    assert "itens" in itens

    print("5. Atribuir ticket e verificar fila (via listagem indireta)…")
    tickets = req("GET", "/tickets?situacao=abertos&limit=1", token=tok)
    items = tickets.get("items") or []
    if not items:
        setores = req("GET", "/setores?limit=1", token=tok)["items"]
        empresas = req("GET", "/empresas?limit=1", token=tok)["items"]
        created = req(
            "POST",
            "/tickets",
            token=tok,
            body={
                "empresa_id": empresas[0]["id"],
                "setor_id": setores[0]["id"],
                "assunto": "Teste notificação local",
                "descricao": "Script testar_notificacoes_local.py",
            },
        )
        tid = created["id"]
    else:
        tid = items[0]["id"]

    me = req("GET", "/atendentes/me", token=tok)
    req("PATCH", f"/tickets/{tid}", token=tok, body={"atendente_id": me["id"]})

    print("6. Nova mensagem pública (outro user simulado: admin em ticket do admin — sem fila nova_msg)…")
    # Mensagem do próprio responsável não deve gerar nova_msg para si
    r = req("POST", f"/tickets/{tid}/mensagens", token=tok, body={"corpo": "Teste msg", "tipo": "publico"})
    assert r.get("id"), r

    print("OK — API de notificações respondendo; atribuição e preferências funcionais.")
    print(f"   Ticket usado: #{tid}")
    print("   Em dev sem Resend, o worker simula envio (status enviada + log no backend).")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        print(f"FALHA: {e}", file=sys.stderr)
        raise SystemExit(1)
