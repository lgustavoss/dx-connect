"""Vários acessos remotos por PDV (#S202610-0014)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.empresa_pdv import EmpresaPdv, EmpresaPdvAcessoRemoto, PdvTipoAcessoRemoto
from app.schemas.pdv import EmpresaPdvAcessoWrite
from app.services.secret_box import encrypt_str

MAX_ACESSOS_REMOTOS = 10


def tipo_permite_conectar(nome: str | None) -> bool:
    """Só DeskRudder (e nomes antigos da frota) abre o cliente integrado."""
    compacto = "".join((nome or "").split()).casefold()
    if not compacto:
        return False
    return compacto in {"rustdesk", "acessoremoto"} or compacto.startswith("deskrudder")


def acessos_ordenados(pdv: EmpresaPdv) -> list[EmpresaPdvAcessoRemoto]:
    rows = list(pdv.acessos_remotos or [])
    rows.sort(key=lambda a: (a.ordem_exibicao, a.id or 0))
    return rows


def sincronizar_colunas_pdv(pdv: EmpresaPdv) -> None:
    """Espelha o acesso preferencial (DeskRudder, senão o primeiro) nas colunas do PDV."""
    rows = acessos_ordenados(pdv)
    preferido: EmpresaPdvAcessoRemoto | None = None
    for acesso in rows:
        nome = acesso.tipo_acesso_remoto.nome if acesso.tipo_acesso_remoto else None
        if tipo_permite_conectar(nome) and (acesso.acesso_remoto_id or "").strip():
            preferido = acesso
            break
    if preferido is None:
        preferido = rows[0] if rows else None
    if preferido is None:
        pdv.tipo_acesso_remoto_id = None
        pdv.acesso_remoto_id = None
        pdv.acesso_remoto_senha_cifrada = None
        return
    pdv.tipo_acesso_remoto_id = preferido.tipo_acesso_remoto_id
    pdv.acesso_remoto_id = preferido.acesso_remoto_id
    pdv.acesso_remoto_senha_cifrada = preferido.acesso_remoto_senha_cifrada


def _validar_tipo(db: Session, tipo_id: int | None) -> PdvTipoAcessoRemoto | None:
    if tipo_id is None:
        return None
    tipo = (
        db.query(PdvTipoAcessoRemoto)
        .filter(PdvTipoAcessoRemoto.id == tipo_id, PdvTipoAcessoRemoto.ativo.is_(True))
        .first()
    )
    if not tipo:
        raise ValueError("Tipo de acesso remoto inválido ou inativo.")
    return tipo


def aplicar_acessos(db: Session, pdv: EmpresaPdv, itens: list[EmpresaPdvAcessoWrite]) -> None:
    if len(itens) > MAX_ACESSOS_REMOTOS:
        raise ValueError(f"Máximo de {MAX_ACESSOS_REMOTOS} acessos remotos por PDV.")
    existentes = {a.id: a for a in acessos_ordenados(pdv)}
    vistos: set[int] = set()
    for ordem, item in enumerate(itens):
        tipo = _validar_tipo(db, item.tipo_acesso_remoto_id)
        rid = (item.acesso_remoto_id or "").strip() or None
        senha = item.acesso_remoto_senha
        if item.id is not None and item.id in existentes:
            acesso = existentes[item.id]
            acesso.tipo_acesso_remoto_id = tipo.id if tipo else None
            acesso.acesso_remoto_id = rid
            acesso.ordem_exibicao = ordem
            if senha is not None:
                acesso.acesso_remoto_senha_cifrada = encrypt_str(senha.strip()) if senha.strip() else None
            vistos.add(acesso.id)
            continue
        cifrada = encrypt_str(senha.strip()) if senha and senha.strip() else None
        if tipo is None and rid is None and cifrada is None:
            continue
        acesso = EmpresaPdvAcessoRemoto(
            tipo_acesso_remoto_id=tipo.id if tipo else None,
            acesso_remoto_id=rid,
            acesso_remoto_senha_cifrada=cifrada,
            ordem_exibicao=ordem,
        )
        if tipo is not None:
            acesso.tipo_acesso_remoto = tipo
        pdv.acessos_remotos.append(acesso)
    for eid, acesso in existentes.items():
        if eid not in vistos:
            pdv.acessos_remotos.remove(acesso)
    db.flush()
    sincronizar_colunas_pdv(pdv)


def garantir_filho_legado(db: Session, pdv: EmpresaPdv) -> None:
    """Se o PDV ainda só tem colunas, cria o primeiro filho."""
    if acessos_ordenados(pdv):
        return
    if not (pdv.tipo_acesso_remoto_id or pdv.acesso_remoto_id or pdv.acesso_remoto_senha_cifrada):
        return
    pdv.acessos_remotos.append(
        EmpresaPdvAcessoRemoto(
            tipo_acesso_remoto_id=pdv.tipo_acesso_remoto_id,
            acesso_remoto_id=pdv.acesso_remoto_id,
            acesso_remoto_senha_cifrada=pdv.acesso_remoto_senha_cifrada,
            ordem_exibicao=0,
            tipo_acesso_remoto=pdv.tipo_acesso_remoto,
        )
    )
    db.flush()
