"""Testa fluxo CSAT local sem envio de e-mail (endpoint link-dev)."""
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
        err = e.read().decode()
        raise RuntimeError(f"{method} {path} -> {e.code}: {err}") from e


def main() -> int:
    print("1. Login…")
    tok = req("POST", "/auth/login", body={"email": EMAIL, "senha": SENHA})["access_token"]

    print("2. Listar tickets fechados…")
    tickets = req("GET", "/tickets?situacao=fechados&limit=5", token=tok)
    items = tickets.get("items") or []
    ticket = items[0] if items else None

    if not ticket:
        print("   Nenhum ticket fechado — criando e fechando um…")
        setores = req("GET", "/setores?limit=1", token=tok)["items"]
        empresas = req("GET", "/empresas?limit=1", token=tok)["items"]
        status_list = req("GET", "/status-ticket?limit=50", token=tok)["items"]
        fechado = next((s for s in status_list if (s.get("slug") or "").lower() == "fechado"), None)
        if not fechado:
            print("ERRO: cadastre status slug 'fechado'", file=sys.stderr)
            return 1
        motivos = req("GET", "/ticket-classificacao/motivos?limit=50", token=tok)
        motivo_items = motivos if isinstance(motivos, list) else motivos.get("items") or []
        motivo = motivo_items[0] if motivo_items else None
        if not motivo:
            print("ERRO: cadastre ao menos um motivo de ticket", file=sys.stderr)
            return 1
        created = req(
            "POST",
            "/tickets",
            token=tok,
            body={
                "empresa_id": empresas[0]["id"],
                "setor_id": setores[0]["id"],
                "assunto": "Teste CSAT local",
                "descricao": "Gerado por scripts/testar_csat_local.py",
            },
        )
        ticket = req(
            "PATCH",
            f"/tickets/{created['id']}",
            token=tok,
            body={"status_id": fechado["id"], "motivo_id": motivo["id"]},
        )
        print(f"   Ticket #{ticket['id']} fechado.")

    tid = ticket["id"]
    if ticket.get("avaliacao_nota") is not None:
        print(f"   Ticket {tid} já avaliado — usando mesmo ticket para novo convite dev.")

    print(f"3. Gerar link dev (ticket {tid})…")
    link_resp = req("POST", f"/tickets/{tid}/csat/link-dev", token=tok)
    link = link_resp["link"]
    print(f"   Link: {link}")

    token_raw = link.split("token=")[-1]
    print("4. GET página pública (pendente)…")
    pub = req("GET", f"/public/csat/tickets/{token_raw}")
    assert pub["status"] == "pendente", pub
    print(f"   OK — protocolo {pub.get('protocolo')}")

    print("5. POST avaliação (nota 4)…")
    pub2 = req("POST", f"/public/csat/tickets/{token_raw}", body={"nota": 4, "comentario": "Teste local OK"})
    assert pub2["status"] == "respondido" and pub2["nota"] == 4, pub2
    print("   Avaliação registrada.")

    print("6. Verificar ticket…")
    t2 = req("GET", f"/tickets/{tid}", token=tok)
    assert t2.get("avaliacao_nota") == 4, t2
    print(f"   Ticket exibe nota {t2['avaliacao_nota']} — fluxo completo OK.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        print(f"FALHA: {e}", file=sys.stderr)
        raise SystemExit(1)
