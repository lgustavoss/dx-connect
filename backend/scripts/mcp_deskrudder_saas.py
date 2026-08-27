"""MCP stdio — fila SaaS DeskRudder para o Cursor (#857).

O processo corre no PC do ops (Cursor). A API é a do control-plane em produção.

Env:
  DESKRUDDER_API_URL   (omissão: https://api.deskrudder.com.br — control-plane, #875)
  DESKRUDDER_MCP_TOKEN (token gerado em /saas/conta; legado: SAAS_MCP_TOKEN da VPS)

Em local, no .cursor/mcp.json usa http://127.0.0.1:8000 e o token de /saas/conta
(legado: SAAS_MCP_TOKEN no backend/.env).
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = (os.environ.get("DESKRUDDER_API_URL") or "https://api.deskrudder.com.br").rstrip("/")
PROTOCOL = "2024-11-05"
MCP_INSTRUCTIONS = (
    "Fila SaaS DeskRudder. Escreva sempre em português do Brasil (pt-BR). "
    "comentar_solicitacao sem publico_cliente é nota interna. "
    "Mensagem ao cliente (publico_cliente=true): o cliente lê — sem GitHub, issue #, "
    "nem vocabulário de Portugal (equipe não equipa; mouse não rato; planejamento não planeamento)."
)


def _api_e_loopback() -> bool:
    host = urllib.parse.urlparse(API).hostname or ""
    return host in {"127.0.0.1", "localhost", "::1"}


def _ler_token() -> str:
    env = (os.environ.get("DESKRUDDER_MCP_TOKEN") or "").strip()
    if env:
        return env
    # Só em local: evita misturar o token do Docker com a API de produção.
    if not _api_e_loopback():
        return ""
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if env_path.is_file():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            raw = line.strip()
            if raw.startswith("SAAS_MCP_TOKEN="):
                return raw.split("=", 1)[1].strip().strip('"').strip("'")
    return ""

TOOLS = [
    {
        "name": "listar_solicitacoes",
        "description": (
            "Lista pedidos de melhoria/bug na fila SaaS DeskRudder. "
            "Cada item tem protocolo #SYYYYMM-NNNN, único no produto DeskRudder. "
            "peso_clientes > 1 significa vários clientes pedindo o mesmo (grupo só visível no SaaS). "
            "No título da issue use o protocolo; no corpo cole texto_github_demanda (lista de protocolos)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": "aberta | em_analise | planejada | em_desenvolvimento | concluida | nao_sera_desenvolvida",
                },
                "tipo": {"type": "string", "description": "sugestao | problema"},
                "slug": {"type": "string", "description": "Slug da instância (ex.: duplex-soft)"},
                "busca": {"type": "string"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 100},
            },
        },
    },
    {
        "name": "obter_solicitacao",
        "description": (
            "Detalhe de um pedido. Inclui grupo (pedidos iguais) e texto_github_demanda para colar na issue. "
            "O cliente da instância NÃO vê o grupo. Use id ou protocolo (#S202608-0001)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": {"type": "integer", "minimum": 1},
                "protocolo": {"type": "string", "description": "Ex.: #S202608-0001"},
                "slug": {"type": "string"},
            },
        },
    },
    {
        "name": "alterar_status",
        "description": (
            "Atualiza a triagem com máquina de estados rígida. "
            "Fluxo: aberta→em_analise→planejada→em_desenvolvimento→concluida; "
            "de qualquer etapa (exceto finais) pode ir a nao_sera_desenvolvida (+ motivo). "
            "em_desenvolvimento exige issue GitHub já ligada — preferir a tool implementar. "
            "O cliente vê o status em Minhas solicitações (sem GitHub)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": {"type": "integer", "minimum": 1},
                "protocolo": {"type": "string"},
                "slug": {"type": "string"},
                "status": {"type": "string"},
                "motivo_nao_desenvolvimento": {"type": "string"},
            },
            "required": ["status"],
        },
    },
    {
        "name": "definir_versao_alvo",
        "description": (
            "Define versão CalVer prevista/liberada visível ao cliente (G3). "
            "Só em planejada ou em_desenvolvimento. Comentário público opcional."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": {"type": "integer", "minimum": 1},
                "protocolo": {"type": "string"},
                "slug": {"type": "string"},
                "versao_alvo": {"type": "string", "description": "Ex.: 2026.08.26 — vazio para limpar"},
                "comentario_publico": {"type": "string"},
            },
        },
    },
    {
        "name": "implementar",
        "description": (
            "A partir de planejada: cria ou liga issue GitHub e marca em_desenvolvimento. "
            "Passe github_issue_url (ou número) para ligar; senão cria via API GitHub "
            "(GITHUB_TOKEN no control-plane). O cliente NÃO vê o GitHub."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": {"type": "integer", "minimum": 1},
                "protocolo": {"type": "string"},
                "slug": {"type": "string"},
                "github_issue_url": {"type": "string"},
                "github_issue_number": {"type": "integer"},
                "criar_issue": {
                    "type": "boolean",
                    "description": "Se true (padrão) e sem URL, cria a issue no GitHub",
                },
            },
        },
    },
    {
        "name": "comentar_solicitacao",
        "description": (
            "Comentário no pedido, em português do Brasil. "
            "Sem publico_cliente (ou false) = nota interna só no SaaS. "
            "publico_cliente=true o cliente lê: sem GitHub, issue # nem jargão de ops."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": {"type": "integer", "minimum": 1},
                "protocolo": {"type": "string"},
                "slug": {"type": "string"},
                "corpo": {"type": "string"},
                "publico_cliente": {
                    "type": "boolean",
                    "description": "true = o cliente lê (pt-BR, sem GitHub). Omissão = nota interna.",
                },
            },
            "required": ["corpo"],
        },
    },
    {
        "name": "ligar_issue_github",
        "description": (
            "Depois de criar a issue com o MCP GitHub, grave a URL neste pedido. "
            "Cole texto_github_demanda no corpo da issue (um ou mais protocolos = demanda). "
            "A issue fica ligada a todos os pedidos do grupo. O cliente NÃO vê o GitHub."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": {"type": "integer", "minimum": 1},
                "protocolo": {"type": "string"},
                "slug": {"type": "string"},
                "github_issue_url": {"type": "string", "description": "https://github.com/org/repo/issues/123"},
                "github_issue_number": {"type": "integer"},
            },
        },
    },
    {
        "name": "vincular_solicitacao",
        "description": (
            "Marca dois pedidos como o mesmo pedido de produto (clientes diferentes). "
            "Sobe o peso. Só no painel SaaS; o cliente não vê. "
            "Indique o pedido atual (id ou protocolo) e o outro (outra_id ou outro_protocolo)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": {"type": "integer", "minimum": 1},
                "protocolo": {"type": "string"},
                "outra_id": {"type": "integer", "minimum": 1},
                "outro_protocolo": {"type": "string"},
            },
        },
    },
    {
        "name": "desvincular_solicitacao",
        "description": "Tira um pedido do grupo de iguais. Só ops SaaS.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": {"type": "integer", "minimum": 1},
                "protocolo": {"type": "string"},
                "membro_id": {"type": "integer", "minimum": 1},
                "membro_protocolo": {"type": "string"},
            },
        },
    },
]


def _out(msg: dict) -> None:
    sys.stdout.write(json.dumps(msg, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def _err_result(req_id, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


def _ok(req_id, result) -> dict:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _api(method: str, path: str, body: dict | None = None) -> tuple[int, object]:
    token = _ler_token()
    if not token:
        raise RuntimeError(
            "Defina DESKRUDDER_MCP_TOKEN no .cursor/mcp.json "
            "(token gerado em /saas/conta). "
            "No ambiente local (127.0.0.1) também pode usar SAAS_MCP_TOKEN no backend/.env (legado)."
        )
    url = f"{API}{path}"
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "User-Agent": "DeskRudder-MCP/1.0",
    }
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            parsed: object = json.loads(raw) if raw else {}
            return resp.getcode(), parsed
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace") if e.fp else str(e.reason)
        raise RuntimeError(f"HTTP {e.code}: {err[:1500]}") from e


def _text(payload: object) -> dict:
    return {"content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False, indent=2)}]}


def _normalizar_protocolo(raw: object) -> str:
    s = str(raw or "").strip()
    if not s:
        return ""
    if not s.startswith("#"):
        s = "#" + s
    if len(s) < 3:
        return s
    return "#" + s[1].upper() + s[2:]


def _id_fila(args: dict) -> int:
    if args.get("id") is not None and str(args.get("id")).strip() != "":
        return int(args["id"])
    proto = _normalizar_protocolo(args.get("protocolo"))
    if not proto:
        raise RuntimeError("Indique id ou protocolo (ex.: #S202608-0001).")
    qs: dict[str, object] = {"busca": proto, "limit": 50}
    if args.get("slug"):
        qs["slug"] = str(args["slug"]).strip().lower()
    path = f"/v1/saas/solicitacoes?{urllib.parse.urlencode(qs)}"
    _, body = _api("GET", path)
    items = body.get("items") if isinstance(body, dict) else None
    if not isinstance(items, list):
        raise RuntimeError("Resposta inesperada ao procurar o protocolo.")
    want = proto.upper()
    exact = [i for i in items if str(i.get("protocolo") or "").upper() == want]
    if len(exact) == 1:
        return int(exact[0]["id"])
    if not exact:
        raise RuntimeError(f"Protocolo {proto} não encontrado na fila.")
    raise RuntimeError(
        f"Há {len(exact)} pedidos com {proto}. Isto não deveria acontecer (o protocolo é único). "
        "Passe o id da fila ou o slug."
    )


def call_tool(name: str, args: dict) -> object:
    args = args or {}
    if name == "listar_solicitacoes":
        qs = {}
        if args.get("status"):
            qs["status"] = args["status"]
        if args.get("tipo"):
            qs["tipo"] = args["tipo"]
        if args.get("slug"):
            qs["slug"] = args["slug"]
        if args.get("busca"):
            qs["busca"] = args["busca"]
        qs["limit"] = int(args.get("limit") or 30)
        path = "/v1/saas/solicitacoes"
        if qs:
            path = f"{path}?{urllib.parse.urlencode(qs)}"
        _, body = _api("GET", path)
        return body
    if name == "obter_solicitacao":
        sid = _id_fila(args)
        _, body = _api("GET", f"/v1/saas/solicitacoes/{sid}")
        if isinstance(body, dict) and API:
            for a in body.get("anexos") or []:
                url = a.get("url") or ""
                if url.startswith("/"):
                    a["url"] = f"{API}{url}"
        return body
    if name == "alterar_status":
        sid = _id_fila(args)
        payload = {"status": args["status"]}
        motivo = (args.get("motivo_nao_desenvolvimento") or "").strip()
        if motivo:
            payload["motivo_nao_desenvolvimento"] = motivo
        _, body = _api("PATCH", f"/v1/saas/solicitacoes/{sid}/status", payload)
        return body
    if name == "definir_versao_alvo":
        sid = _id_fila(args)
        payload: dict[str, object] = {}
        if "versao_alvo" in args:
            payload["versao_alvo"] = (args.get("versao_alvo") or "").strip() or None
        if args.get("comentario_publico"):
            payload["comentario_publico"] = str(args["comentario_publico"])
        _, body = _api("PATCH", f"/v1/saas/solicitacoes/{sid}/versao-alvo", payload)
        return body
    if name == "implementar":
        sid = _id_fila(args)
        payload: dict[str, object] = {}
        if args.get("github_issue_url"):
            payload["github_issue_url"] = args["github_issue_url"]
        if args.get("github_issue_number") is not None:
            payload["github_issue_number"] = int(args["github_issue_number"])
        if "criar_issue" in args:
            payload["criar_issue"] = bool(args["criar_issue"])
        _, body = _api("POST", f"/v1/saas/solicitacoes/{sid}/implementar", payload or None)
        return body
    if name == "comentar_solicitacao":
        sid = _id_fila(args)
        payload = {
            "corpo": args["corpo"],
            "publico_cliente": bool(args["publico_cliente"]) if "publico_cliente" in args else False,
        }
        _, body = _api("POST", f"/v1/saas/solicitacoes/{sid}/comentarios", payload)
        return body
    if name == "ligar_issue_github":
        sid = _id_fila(args)
        payload = {}
        if args.get("github_issue_url"):
            payload["github_issue_url"] = args["github_issue_url"]
        if args.get("github_issue_number") is not None:
            payload["github_issue_number"] = int(args["github_issue_number"])
        _, body = _api("PATCH", f"/v1/saas/solicitacoes/{sid}/github", payload)
        return body
    if name == "vincular_solicitacao":
        sid = _id_fila(args)
        payload: dict[str, object] = {}
        if args.get("outra_id") is not None:
            payload["solicitacao_id"] = int(args["outra_id"])
        elif args.get("outro_protocolo"):
            payload["protocolo"] = str(args["outro_protocolo"])
        else:
            raise RuntimeError("Indique outra_id ou outro_protocolo.")
        _, body = _api("POST", f"/v1/saas/solicitacoes/{sid}/vinculos", payload)
        return body
    if name == "desvincular_solicitacao":
        sid = _id_fila(args)
        if args.get("membro_id") is not None:
            mid = int(args["membro_id"])
        elif args.get("membro_protocolo"):
            mid = _id_fila({"protocolo": args["membro_protocolo"]})
        else:
            raise RuntimeError("Indique membro_id ou membro_protocolo.")
        _, body = _api("DELETE", f"/v1/saas/solicitacoes/{sid}/vinculos/{mid}")
        return body
    raise RuntimeError(f"Ferramenta desconhecida: {name}")


def handle(msg: dict) -> dict | None:
    if msg.get("jsonrpc") != "2.0":
        return None
    method = msg.get("method")
    req_id = msg.get("id")
    if method is None:
        return None
    if req_id is None:
        return None
    if method == "initialize":
        return _ok(
            req_id,
            {
                "protocolVersion": PROTOCOL,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "deskrudder-saas", "version": "1.0.0"},
                "instructions": MCP_INSTRUCTIONS,
            },
        )
    if method == "ping":
        return _ok(req_id, {})
    if method == "tools/list":
        return _ok(req_id, {"tools": TOOLS})
    if method == "tools/call":
        params = msg.get("params") or {}
        name = params.get("name") or ""
        arguments = params.get("arguments") or {}
        try:
            result = call_tool(name, arguments)
            return _ok(req_id, _text(result))
        except Exception as e:
            return _ok(
                req_id,
                {"content": [{"type": "text", "text": str(e)}], "isError": True},
            )
    return _err_result(req_id, -32601, f"Método não suportado: {method}")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stdin, "reconfigure"):
        sys.stdin.reconfigure(encoding="utf-8")
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(msg, dict):
            continue
        reply = handle(msg)
        if reply is not None:
            _out(reply)


if __name__ == "__main__":
    main()
