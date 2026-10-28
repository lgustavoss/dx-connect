"""Frota RustDesk: cache do hbbs, cruzamento com PDVs e vínculo do ID."""

from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload, selectinload

from app.config import settings
from app.core.audit import registrar_audit
from app.models.atendente import Atendente
from app.models.deskremote_enroll import DeskremoteDispositivo
from app.models.empresa import Empresa
from app.models.empresa_pdv import EmpresaPdv, EmpresaPdvAcessoRemoto, PdvTipoAcessoRemoto
from app.models.rustdesk_peer import RustdeskPeer
from app.services.empresa_pdv_acessos import (
    MAX_ACESSOS_REMOTOS,
    acessos_ordenados,
    garantir_filho_legado,
    sincronizar_colunas_pdv,
    tipo_permite_conectar,
)

_CARREGAR_PDV = (
    joinedload(EmpresaPdv.empresa).joinedload(Empresa.rede),
    joinedload(EmpresaPdv.rotulo),
    joinedload(EmpresaPdv.tipo_acesso_remoto),
    selectinload(EmpresaPdv.acessos_remotos).joinedload(EmpresaPdvAcessoRemoto.tipo_acesso_remoto),
)

_sync_lock = threading.Lock()
_ultimo_sync_mono = 0.0
_estado: dict = {
    "monitoramento_online": False,
    "agent_configurado": False,
    "agent_indisponivel": False,
    "sincronizado_em": None,
}


def normalizar_id_remoto(valor: str | None) -> str | None:
    """Tira espaços. ID numérico fica só com dígitos; ID com letras fica em minúsculas."""
    if not valor:
        return None
    compacto = "".join(valor.split())
    if not compacto:
        return None
    if compacto.isdigit():
        return compacto
    return compacto.casefold()


_NOME_TIPO_HOSPEDADO = "DeskRemote"


def _compactar_nome_tipo(nome: str | None) -> str:
    if not nome:
        return ""
    return "".join(nome.split()).casefold()


def _nome_e_tipo_frota(compacto: str) -> bool:
    """Frota / Online / vínculo no hbbs: só o tipo DeskRemote."""
    return compacto.startswith("deskremote")


def _nome_e_rustdesk(nome: str | None) -> bool:
    compacto = _compactar_nome_tipo(nome)
    if not compacto:
        return False
    return _nome_e_tipo_frota(compacto)


def _limite_online() -> timedelta:
    segundos = settings.RUSTDESK_ONLINE_SECONDS
    if segundos < 30:
        segundos = 30
    return timedelta(seconds=segundos)


def _como_utc(valor: datetime) -> datetime:
    if valor.tzinfo is None:
        return valor.replace(tzinfo=timezone.utc)
    return valor.astimezone(timezone.utc)


def calcular_online(last_seen: datetime | None, monitoramento: bool | None = None) -> bool | None:
    if monitoramento is None:
        monitoramento = bool(_estado["monitoramento_online"])
    if last_seen is None:
        return False if monitoramento else None
    recente = datetime.now(timezone.utc) - _como_utc(last_seen) <= _limite_online()
    return recente


def _limite_dispositivo() -> timedelta:
    """O cliente DeskRemote consulta a API a cada ~2 min; folga além do UDP do hbbs (45s)."""
    return timedelta(seconds=max(settings.RUSTDESK_ONLINE_SECONDS, 180))


def marcar_visto_enroll(db: Session, rustdesk_id: str, last_seen: datetime | None = None) -> None:
    """Garante o ID na frota quando o PDV confirma o vínculo, mesmo sem linha ainda no SQLite do hbbs."""
    chave = normalizar_id_remoto(rustdesk_id)
    if not chave:
        return
    row = db.query(RustdeskPeer).filter(RustdeskPeer.rustdesk_id == chave).first()
    if row is None:
        row = RustdeskPeer(rustdesk_id=chave)
        db.add(row)
    if last_seen is not None:
        row.last_seen = last_seen


def mapa_online(db: Session) -> dict[str, bool | None]:
    """Online/offline atual (sincroniza o cache do hbbs, igual à tela de acesso remoto)."""
    sincronizar(db)
    mapa: dict[str, bool | None] = {}
    for row in db.query(RustdeskPeer).all():
        chave = normalizar_id_remoto(row.rustdesk_id)
        if chave:
            mapa[chave] = calcular_online(row.last_seen)
    agora = datetime.now(timezone.utc)
    dispositivos = (
        db.query(DeskremoteDispositivo)
        .filter(
            DeskremoteDispositivo.revoked_at.is_(None),
            DeskremoteDispositivo.rustdesk_id.isnot(None),
        )
        .all()
    )
    for dispositivo in dispositivos:
        chave = normalizar_id_remoto(dispositivo.rustdesk_id)
        if not chave:
            continue
        if chave not in mapa:
            mapa[chave] = False
        visto_em = dispositivo.last_seen_at
        if visto_em is not None and agora - _como_utc(visto_em) <= _limite_dispositivo():
            mapa[chave] = True
    return mapa


def _truncar(valor: object, limite: int) -> str | None:
    if valor is None:
        return None
    texto = str(valor).strip()
    if texto.startswith("::ffff:"):
        texto = texto[7:]
    if not texto:
        return None
    return texto[:limite]


def _parse_last_seen(valor: object) -> datetime | None:
    if not valor or not isinstance(valor, str):
        return None
    try:
        parsed = datetime.fromisoformat(valor.replace("Z", "+00:00"))
    except ValueError:
        return None
    return _como_utc(parsed)


class AgentErro(Exception):
    pass


def configuracao_cliente() -> dict:
    """Valores que o DeskRemote cola em Configurações → Rede. A chave é pública."""
    servidor_id = (settings.RUSTDESK_ID_SERVER or "").strip()
    servidor_relay = (settings.RUSTDESK_RELAY_SERVER or "").strip()
    chave = (settings.RUSTDESK_PUBLIC_KEY or "").strip()
    return {
        "configurado": bool(servidor_id and servidor_relay and chave),
        "servidor_id": servidor_id,
        "servidor_relay": servidor_relay,
        "chave": chave,
    }


def obter_snapshot() -> dict:
    url = (settings.RUSTDESK_AGENT_URL or "").strip().rstrip("/")
    token = (settings.RUSTDESK_AGENT_TOKEN or "").strip()
    if not url or not token:
        raise AgentErro("nao-configurado")
    req = urllib.request.Request(
        f"{url}/peers",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        raise AgentErro("indisponivel") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("peers"), list):
        raise AgentErro("indisponivel")
    return payload


def excluir_no_agente(rustdesk_id: str) -> None:
    url = (settings.RUSTDESK_AGENT_URL or "").strip().rstrip("/")
    token = (settings.RUSTDESK_AGENT_TOKEN or "").strip()
    if not url or not token:
        raise AgentErro("nao-configurado")
    req = urllib.request.Request(
        f"{url}/peers/{urllib.parse.quote(rustdesk_id)}",
        method="DELETE",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            if resp.status not in (200, 204):
                raise AgentErro("indisponivel")
    except urllib.error.HTTPError as exc:
        corpo = exc.read()
        if exc.code == 404 and b"Computador" in corpo:
            raise AgentErro("ausente") from exc
        raise AgentErro("indisponivel") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise AgentErro("indisponivel") from exc


def sincronizar(db: Session, *, forcar: bool = False) -> None:
    """Atualiza o cache se o agente estiver configurado. Falha de rede mantém o cache."""
    global _ultimo_sync_mono
    url = (settings.RUSTDESK_AGENT_URL or "").strip()
    token = (settings.RUSTDESK_AGENT_TOKEN or "").strip()
    if not url or not token:
        _estado["agent_configurado"] = False
        _estado["agent_indisponivel"] = False
        _estado["monitoramento_online"] = False
        return

    agora_mono = time.monotonic()
    with _sync_lock:
        if not forcar and agora_mono - _ultimo_sync_mono < settings.RUSTDESK_SYNC_MIN_INTERVAL_SECONDS:
            _estado["agent_configurado"] = True
            return
        _estado["agent_configurado"] = True
        try:
            payload = obter_snapshot()
        except AgentErro as exc:
            if str(exc) == "nao-configurado":
                _estado["agent_configurado"] = False
                _estado["agent_indisponivel"] = False
                return
            _estado["agent_indisponivel"] = True
            return
        _aplicar_snapshot(db, payload)
        _ultimo_sync_mono = time.monotonic()
        _estado["agent_indisponivel"] = False
        _estado["monitoramento_online"] = bool(payload.get("observando_log"))
        _estado["sincronizado_em"] = datetime.now(timezone.utc)


def _aplicar_snapshot(db: Session, payload: dict) -> None:
    observando = bool(payload.get("observando_log"))
    existentes = {row.rustdesk_id: row for row in db.query(RustdeskPeer).all()}
    vistos: set[str] = set()
    for item in payload.get("peers") or []:
        if not isinstance(item, dict):
            continue
        rid = normalizar_id_remoto(str(item.get("id") or ""))
        if not rid:
            continue
        vistos.add(rid)
        row = existentes.get(rid)
        if row is None:
            row = RustdeskPeer(rustdesk_id=rid)
            db.add(row)
            existentes[rid] = row
        row.hostname = _truncar(item.get("hostname"), 255)
        row.username = _truncar(item.get("username"), 255)
        row.sistema = _truncar(item.get("os"), 120)
        row.ip = _truncar(item.get("ip"), 64)
        if observando:
            row.last_seen = _parse_last_seen(item.get("last_seen"))
    protegidos = {
        chave
        for chave in (
            normalizar_id_remoto(d.rustdesk_id)
            for d in db.query(DeskremoteDispositivo)
            .filter(
                DeskremoteDispositivo.revoked_at.is_(None),
                DeskremoteDispositivo.rustdesk_id.isnot(None),
            )
            .all()
        )
        if chave
    }
    for rid, row in list(existentes.items()):
        if rid not in vistos and rid not in protegidos:
            db.delete(row)
    db.commit()


def _pares_acesso(row: EmpresaPdv) -> list[tuple[str | None, str | None]]:
    acessos = acessos_ordenados(row)
    if acessos:
        return [
            (a.acesso_remoto_id, a.tipo_acesso_remoto.nome if a.tipo_acesso_remoto else None)
            for a in acessos
        ]
    return [(row.acesso_remoto_id, row.tipo_acesso_remoto.nome if row.tipo_acesso_remoto else None)]


def _vinculos_por_id(db: Session) -> dict[str, list[dict]]:
    rows = db.query(EmpresaPdv).options(*_CARREGAR_PDV).all()
    indice: dict[str, list[dict]] = {}
    for row in rows:
        vistos: set[str] = set()
        for rid, nome in _pares_acesso(row):
            chave = normalizar_id_remoto(rid)
            if not chave or chave in vistos:
                continue
            vistos.add(chave)
            indice.setdefault(chave, []).append(_vinculo_de(row, tipo_nome=nome))
    return indice


def _vinculo_de(row: EmpresaPdv, tipo_nome: str | None = None) -> dict:
    empresa = row.empresa
    rede = empresa.rede if empresa else None
    if tipo_nome is None:
        tipo_nome = row.tipo_acesso_remoto.nome if row.tipo_acesso_remoto else None
    return {
        "empresa_id": row.empresa_id,
        "empresa_nome": empresa.nome if empresa else "",
        "rede_id": rede.id if rede else None,
        "rede_nome": rede.nome if rede else "",
        "rotulo_nome": row.rotulo.nome if row.rotulo else "",
        "pdv_id": row.id,
        "pdv_codigo": row.codigo,
        "pdv_ativo": bool(row.ativo),
        "tipo_acesso_remoto_nome": tipo_nome,
        "versao_pdv": empresa.versao_pdv if empresa else None,
    }


def _pdvs_nao_vistos(db: Session, ids_servidor: set[str]) -> list[dict]:
    rows = db.query(EmpresaPdv).options(*_CARREGAR_PDV).filter(EmpresaPdv.ativo.is_(True)).all()
    ausentes: list[dict] = []
    vistos_pdv_id: set[tuple[int, str]] = set()
    for row in rows:
        for rid, nome in _pares_acesso(row):
            if not tipo_permite_conectar(nome) and not _nome_e_rustdesk(nome):
                continue
            chave = normalizar_id_remoto(rid)
            if not chave or chave in ids_servidor:
                continue
            marca = (row.id, chave)
            if marca in vistos_pdv_id:
                continue
            vistos_pdv_id.add(marca)
            item = _vinculo_de(row, tipo_nome=nome)
            item["acesso_remoto_id"] = rid
            ausentes.append(item)
    ausentes.sort(key=lambda item: (item["rede_nome"].casefold(), item["empresa_nome"].casefold(), item["pdv_codigo"]))
    return ausentes


def listar(db: Session, filtro: str) -> dict:
    sincronizar(db)
    indice = _vinculos_por_id(db)
    peers = db.query(RustdeskPeer).order_by(RustdeskPeer.rustdesk_id.asc()).all()
    items: list[dict] = []
    for row in peers:
        vinculos = indice.get(row.rustdesk_id, [])
        online = calcular_online(row.last_seen)
        item = {
            "rustdesk_id": row.rustdesk_id,
            "hostname": row.hostname,
            "username": row.username,
            "sistema": row.sistema,
            "ip": row.ip,
            "last_seen": row.last_seen,
            "online": online,
            "vinculos": vinculos,
            "sem_vinculo": len(vinculos) == 0,
            "id_repetido": len(vinculos) > 1,
        }
        if filtro == "online" and online is not True:
            continue
        if filtro == "offline" and online is not False:
            continue
        if filtro == "sem_vinculo" and vinculos:
            continue
        if filtro == "vinculado" and not vinculos:
            continue
        items.append(item)
    items.sort(key=lambda item: (item["online"] is not True, (item["hostname"] or "").casefold(), item["rustdesk_id"]))
    return {
        "items": items,
        "total": len(items),
        "pdvs_nao_vistos": _pdvs_nao_vistos(db, {row.rustdesk_id for row in peers}),
        "monitoramento_online": bool(_estado["monitoramento_online"]),
        "agent_configurado": bool(_estado["agent_configurado"]),
        "agent_indisponivel": bool(_estado["agent_indisponivel"]),
        "sincronizado_em": _estado["sincronizado_em"],
    }


def garantir_tipo_rustdesk(db: Session) -> PdvTipoAcessoRemoto:
    tipos = db.query(PdvTipoAcessoRemoto).order_by(PdvTipoAcessoRemoto.id.asc()).all()
    ativo = next((row for row in tipos if row.ativo and _nome_e_rustdesk(row.nome)), None)
    if ativo:
        db.flush()
        return ativo
    inativo = next((row for row in tipos if _nome_e_rustdesk(row.nome)), None)
    if inativo:
        inativo.ativo = True
        db.flush()
        return inativo
    criado = PdvTipoAcessoRemoto(nome=_NOME_TIPO_HOSPEDADO, ativo=True, ordem_exibicao=0)
    db.add(criado)
    db.flush()
    return criado


def vincular(
    db: Session,
    rustdesk_id: str,
    pdv_id: int,
    confirmar_substituicao: bool,
    atendente: Atendente,
) -> dict:
    chave = normalizar_id_remoto(rustdesk_id)
    if not chave:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Computador não encontrado no servidor de acesso remoto.")
    peer = db.query(RustdeskPeer).filter(RustdeskPeer.rustdesk_id == chave).first()
    if not peer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Computador não encontrado no servidor de acesso remoto.")
    row = (
        db.query(EmpresaPdv)
        .options(*_CARREGAR_PDV)
        .filter(EmpresaPdv.id == pdv_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PDV não encontrado.")
    garantir_filho_legado(db, row)
    acessos = acessos_ordenados(row)
    deskrudder = [
        a
        for a in acessos
        if tipo_permite_conectar(a.tipo_acesso_remoto.nome if a.tipo_acesso_remoto else None)
        or _nome_e_rustdesk(a.tipo_acesso_remoto.nome if a.tipo_acesso_remoto else None)
    ]
    ja_tem = next((a for a in acessos if normalizar_id_remoto(a.acesso_remoto_id) == chave), None)
    tipo = garantir_tipo_rustdesk(db)
    if ja_tem is None:
        alvo = deskrudder[0] if deskrudder else None
        atual = normalizar_id_remoto(alvo.acesso_remoto_id) if alvo else None
        if atual and atual != chave and not confirmar_substituicao:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Este PDV já está com o ID {alvo.acesso_remoto_id}. Confirme para trocar para {chave}.",
            )
        if alvo is not None:
            alvo.acesso_remoto_id = chave
            alvo.tipo_acesso_remoto_id = tipo.id
        else:
            if len(acessos) >= MAX_ACESSOS_REMOTOS:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Máximo de {MAX_ACESSOS_REMOTOS} acessos remotos por PDV.",
                )
            row.acessos_remotos.append(
                EmpresaPdvAcessoRemoto(
                    tipo_acesso_remoto_id=tipo.id,
                    acesso_remoto_id=chave,
                    ordem_exibicao=len(acessos),
                    tipo_acesso_remoto=tipo,
                )
            )
            db.flush()
    sincronizar_colunas_pdv(row)
    registrar_audit(
        db,
        "empresa_pdv",
        row.id,
        "update",
        atendente.id,
        payload={"acesso_remoto_id": chave, "origem": "rustdesk"},
    )
    db.commit()
    atualizado = (
        db.query(EmpresaPdv)
        .options(*_CARREGAR_PDV)
        .filter(EmpresaPdv.id == row.id)
        .first()
    )
    assert atualizado is not None
    return _vinculo_de(atualizado) | {"acesso_remoto_id": chave}


def desvincular(db: Session, rustdesk_id: str, pdv_id: int, atendente: Atendente) -> dict:
    chave = normalizar_id_remoto(rustdesk_id)
    if not chave:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Computador não encontrado.")
    row = (
        db.query(EmpresaPdv)
        .options(*_CARREGAR_PDV)
        .filter(EmpresaPdv.id == pdv_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PDV não encontrado.")
    garantir_filho_legado(db, row)
    alvo = next((a for a in acessos_ordenados(row) if normalizar_id_remoto(a.acesso_remoto_id) == chave), None)
    if alvo is None and normalizar_id_remoto(row.acesso_remoto_id) != chave:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Este PDV não está com este ID.")
    if alvo is not None:
        alvo.acesso_remoto_id = None
    else:
        row.acesso_remoto_id = None
    sincronizar_colunas_pdv(row)
    registrar_audit(
        db,
        "empresa_pdv",
        row.id,
        "update",
        atendente.id,
        payload={"acesso_remoto_id": None, "origem": "rustdesk_desvincular"},
    )
    db.commit()
    return {"pdv_id": row.id, "acesso_remoto_id": None}


def excluir(db: Session, rustdesk_id: str, atendente: Atendente) -> dict:
    """Remove um ID offline e sem vínculo do banco do hbbs. Online, o cliente recria a linha."""
    chave = normalizar_id_remoto(rustdesk_id)
    if not chave:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Computador não encontrado no servidor de acesso remoto.")
    peer = db.query(RustdeskPeer).filter(RustdeskPeer.rustdesk_id == chave).first()
    if not peer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Computador não encontrado no servidor de acesso remoto.")
    if calcular_online(peer.last_seen) is not False:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Só dá para excluir um computador offline. Enquanto ele estiver acessível, o ID volta sozinho.",
        )
    if _vinculos_por_id(db).get(chave):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Desvincule este ID dos PDVs antes de excluir do servidor.",
        )
    try:
        excluir_no_agente(chave)
    except AgentErro as exc:
        codigo = str(exc)
        if codigo == "nao-configurado":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="O servidor de acesso remoto não está ligado a este painel.",
            ) from exc
        if codigo != "ausente":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Não foi possível excluir no servidor de acesso remoto agora.",
            ) from exc
    registrar_audit(
        db,
        "rustdesk_peer",
        peer.id,
        "delete",
        atendente.id,
        payload={"rustdesk_id": chave, "origem": "rustdesk_excluir"},
    )
    db.delete(peer)
    db.commit()
    return {"rustdesk_id": chave, "removido": True}
