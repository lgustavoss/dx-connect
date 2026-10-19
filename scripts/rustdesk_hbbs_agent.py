"""Expõe os computadores do hbbs (RustDesk gratuito) em JSON na rede interna.

A lista é leitura do SQLite. Excluir um ID apaga a linha em `peer`: o hbbs só
recria essa linha quando o computador volta a se registrar. O online vem do
registro UDP que o cliente envia
enquanto está acessível (o hbbs considera offline depois de 30s sem esse
registro). RUSTDESK_UDP_PORT observa essa porta com tcpdump. O log `update_pk`
só reforça o mesmo sinal.

Variáveis:
  RUSTDESK_DB_PATH          caminho de db_v2.sqlite3 (obrigatório)
  RUSTDESK_AGENT_TOKEN      token Bearer (obrigatório)
  RUSTDESK_AGENT_HOST       escuta; padrão 127.0.0.1
  RUSTDESK_AGENT_PORT       padrão 21120
  RUSTDESK_UDP_PORT         porta do hbbs (21116) para saber quem está acessível
  RUSTDESK_LOG_PATH         arquivo de log do hbbs para seguir
  RUSTDESK_DOCKER_CONTAINER nome do container (docker logs -f); tem prioridade sobre o arquivo
  RUSTDESK_STATE_PATH       JSON opcional para não perder a última atividade ao reiniciar
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

_LINHA_PK = re.compile(r"update_pk\s+(\S+)")
_ID_KEEPALIVE = re.compile(r"(?<!\d)(\d{6,12})(?!\d)")
_CONTAINER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


def normalizar_id(valor: str | None) -> str | None:
    if not valor:
        return None
    compacto = "".join(str(valor).split())
    if not compacto:
        return None
    if compacto.isdigit():
        return compacto
    return compacto.casefold()


def extrair_id_do_log(linha: str) -> str | None:
    achado = _LINHA_PK.search(linha)
    if not achado:
        return None
    return normalizar_id(achado.group(1))


def extrair_ids_keepalive(linha: str) -> list[str]:
    """ID presente no registro UDP do cliente. Cabeçalho do tcpdump é ignorado."""
    texto = linha.strip()
    if not texto or len(texto) > 80 or " IP " in texto or "tcpdump" in texto:
        return []
    ids: list[str] = []
    for achado in _ID_KEEPALIVE.findall(texto):
        rid = normalizar_id(achado)
        if rid:
            ids.append(rid)
    return ids


def _campo(info: dict, *chaves: str) -> str | None:
    for chave in chaves:
        valor = info.get(chave)
        if isinstance(valor, str) and valor.strip():
            texto = valor.strip()
            if texto.startswith("::ffff:"):
                texto = texto[7:]
            return texto
    return None


def ler_peers(db_path: str) -> list[dict]:
    uri = Path(db_path).expanduser().resolve().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True, timeout=2)
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.execute("SELECT id, info FROM peer")
        linhas = cur.fetchall()
    finally:
        conn.close()
    peers: list[dict] = []
    for linha in linhas:
        info: dict = {}
        bruto = linha["info"]
        if isinstance(bruto, str) and bruto.strip():
            try:
                parsed = json.loads(bruto)
                if isinstance(parsed, dict):
                    info = parsed
            except json.JSONDecodeError:
                info = {}
        rid = normalizar_id(linha["id"])
        if not rid:
            continue
        peers.append(
            {
                "id": rid,
                "ip": _campo(info, "ip"),
                "hostname": _campo(info, "hostname", "device_name", "name"),
                "username": _campo(info, "username", "user"),
                "os": _campo(info, "os", "platform"),
            }
        )
    return peers


def excluir_peer(db_path: str, rustdesk_id: str) -> bool:
    """Apaga o ID do banco do hbbs. Não impede o cliente de se registrar de novo."""
    chave = normalizar_id(rustdesk_id)
    if not chave:
        return False
    conn = sqlite3.connect(db_path, timeout=5)
    try:
        conn.execute("BEGIN IMMEDIATE")
        alvos = [
            row[0]
            for row in conn.execute("SELECT id FROM peer").fetchall()
            if normalizar_id(row[0]) == chave
        ]
        if not alvos:
            conn.rollback()
            return False
        conn.executemany("DELETE FROM peer WHERE id = ?", [(alvo,) for alvo in alvos])
        conn.commit()
        return True
    except sqlite3.Error:
        conn.rollback()
        raise
    finally:
        conn.close()


class _Estado:
    def __init__(self, db_path: str, state_path: str | None) -> None:
        self.db_path = db_path
        self.state_path = state_path
        self.observando_log = False
        self._vistos: dict[str, str] = {}
        self._lock = threading.Lock()
        self._carregar()

    def _carregar(self) -> None:
        if not self.state_path or not os.path.isfile(self.state_path):
            return
        try:
            with open(self.state_path, encoding="utf-8") as arquivo:
                dados = json.load(arquivo)
        except (OSError, json.JSONDecodeError):
            return
        if isinstance(dados, dict):
            self._vistos = {str(k): str(v) for k, v in dados.items() if v}

    def esquecer(self, rustdesk_id: str) -> None:
        chave = normalizar_id(rustdesk_id)
        if not chave:
            return
        with self._lock:
            self._vistos.pop(chave, None)
            vistos = dict(self._vistos)
        self._gravar(vistos)

    def marcar(self, rustdesk_id: str) -> None:
        agora = datetime.now(timezone.utc).isoformat()
        with self._lock:
            self._vistos[rustdesk_id] = agora
            vistos = dict(self._vistos)
        self._gravar(vistos)

    def _gravar(self, vistos: dict[str, str]) -> None:
        if not self.state_path:
            return
        try:
            pasta = os.path.dirname(self.state_path)
            if pasta:
                os.makedirs(pasta, exist_ok=True)
            tmp = self.state_path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as arquivo:
                json.dump(vistos, arquivo)
            os.replace(tmp, self.state_path)
        except OSError:
            return

    def resposta(self) -> dict:
        peers = ler_peers(self.db_path)
        with self._lock:
            vistos = dict(self._vistos)
        for peer in peers:
            peer["last_seen"] = vistos.get(peer["id"])
        return {"observando_log": self.observando_log, "peers": peers}


def _thread_arquivo(estado: _Estado, caminho: str) -> None:
    while not os.path.isfile(caminho):
        time.sleep(2)
    with open(caminho, encoding="utf-8", errors="replace") as arquivo:
        arquivo.seek(0, os.SEEK_END)
        while True:
            linha = arquivo.readline()
            if not linha:
                time.sleep(0.5)
                continue
            rid = extrair_id_do_log(linha)
            if rid:
                estado.marcar(rid)


def _thread_docker(estado: _Estado, container: str) -> None:
    while True:
        proc = subprocess.Popen(
            ["docker", "logs", "-f", "--tail", "0", container],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        assert proc.stdout is not None
        try:
            for linha in proc.stdout:
                rid = extrair_id_do_log(linha.decode("utf-8", errors="replace"))
                if rid:
                    estado.marcar(rid)
        finally:
            proc.kill()
        time.sleep(2)


def _thread_udp(estado: _Estado, porta: int) -> None:
    if not shutil.which("tcpdump"):
        print("tcpdump não encontrado; situação online indisponível.", file=sys.stderr)
        return
    while True:
        proc = subprocess.Popen(
            [
                "tcpdump",
                "-i",
                "any",
                "-n",
                "-l",
                "-s",
                "256",
                "-A",
                "udp",
                "dst",
                "port",
                str(porta),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        assert proc.stdout is not None
        try:
            for bruto in proc.stdout:
                for rid in extrair_ids_keepalive(bruto.decode("utf-8", errors="replace")):
                    estado.marcar(rid)
        finally:
            proc.kill()
        time.sleep(2)


def _iniciar_observacao(estado: _Estado) -> None:
    container = os.environ.get("RUSTDESK_DOCKER_CONTAINER", "").strip()
    log_path = os.environ.get("RUSTDESK_LOG_PATH", "").strip()
    udp = os.environ.get("RUSTDESK_UDP_PORT", "").strip()
    if container:
        if not _CONTAINER.match(container):
            print("RUSTDESK_DOCKER_CONTAINER inválido.", file=sys.stderr)
            sys.exit(1)
        estado.observando_log = True
        threading.Thread(target=_thread_docker, args=(estado, container), daemon=True).start()
    elif log_path:
        estado.observando_log = True
        threading.Thread(target=_thread_arquivo, args=(estado, log_path), daemon=True).start()
    if udp:
        porta = int(udp)
        if porta < 1 or porta > 65535:
            print("RUSTDESK_UDP_PORT inválida.", file=sys.stderr)
            sys.exit(1)
        estado.observando_log = True
        threading.Thread(target=_thread_udp, args=(estado, porta), daemon=True).start()


def criar_handler(estado: _Estado, token: str):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args) -> None:
            return

        def _negar(self, codigo: int, mensagem: str) -> None:
            corpo = json.dumps({"detail": mensagem}).encode("utf-8")
            self.send_response(codigo)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(corpo)))
            self.end_headers()
            self.wfile.write(corpo)

        def do_GET(self) -> None:  # noqa: N802
            caminho = urlparse(self.path).path.rstrip("/") or "/"
            if caminho not in {"/peers", "/v1/peers"}:
                self._negar(404, "Não encontrado.")
                return
            auth = self.headers.get("Authorization", "")
            if auth != f"Bearer {token}":
                self._negar(401, "Token inválido.")
                return
            try:
                corpo = json.dumps(estado.resposta()).encode("utf-8")
            except sqlite3.Error:
                self._negar(503, "Não foi possível ler o banco do RustDesk.")
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(corpo)))
            self.end_headers()
            self.wfile.write(corpo)

        def do_DELETE(self) -> None:  # noqa: N802
            caminho = urlparse(self.path).path.rstrip("/") or "/"
            prefixo = "/v1/peers/" if caminho.startswith("/v1/peers/") else "/peers/"
            if not caminho.startswith(prefixo) or caminho == prefixo.rstrip("/"):
                self._negar(404, "Não encontrado.")
                return
            rustdesk_id = unquote(caminho[len(prefixo) :])
            if not rustdesk_id or "/" in rustdesk_id:
                self._negar(404, "Não encontrado.")
                return
            auth = self.headers.get("Authorization", "")
            if auth != f"Bearer {token}":
                self._negar(401, "Token inválido.")
                return
            try:
                removido = excluir_peer(estado.db_path, rustdesk_id)
            except sqlite3.Error:
                self._negar(503, "Não foi possível gravar no banco do RustDesk.")
                return
            if not removido:
                self._negar(404, "Computador não encontrado.")
                return
            estado.esquecer(rustdesk_id)
            corpo = json.dumps({"removido": True}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(corpo)))
            self.end_headers()
            self.wfile.write(corpo)

    return Handler


def main() -> None:
    db_path = os.environ.get("RUSTDESK_DB_PATH", "").strip()
    token = os.environ.get("RUSTDESK_AGENT_TOKEN", "").strip()
    if not db_path or not os.path.isfile(db_path):
        print("Defina RUSTDESK_DB_PATH com o arquivo db_v2.sqlite3.", file=sys.stderr)
        sys.exit(1)
    if not token:
        print("Defina RUSTDESK_AGENT_TOKEN.", file=sys.stderr)
        sys.exit(1)
    host = os.environ.get("RUSTDESK_AGENT_HOST", "127.0.0.1").strip() or "127.0.0.1"
    port = int(os.environ.get("RUSTDESK_AGENT_PORT", "21120"))
    estado = _Estado(db_path, os.environ.get("RUSTDESK_STATE_PATH", "").strip() or None)
    _iniciar_observacao(estado)
    servidor = ThreadingHTTPServer((host, port), criar_handler(estado, token))
    print(f"Agente RustDesk em http://{host}:{port}/peers", flush=True)
    servidor.serve_forever()


if __name__ == "__main__":
    main()
