from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.core.ordenacao_lista import OrdemLista, expr_ordem
from app.models import Atendente, Setor
from app.schemas.atendente import AtendenteCreate, AtendenteRead, AtendenteUpdate, TrocaSenhaPropria
from app.schemas.ticket_csat import AtendenteAvaliacoesRead, AvaliacaoResumoRead
from app.schemas.lista_paginada import ListaPaginada
from app.core.auth import exigir_admin, obter_atendente_atual, validar_role
from app.services.atendente_avaliacoes import calcular_avaliacoes_atendente
from app.services.escala import (
    horario_semana_dict,
    horario_semana_para_json,
    modo_jornada as modo_jornada_de,
    validar_campos_jornada,
    validar_horario_previsto,
)
from app.core.setor_scope import atendente_e_financeiro, ids_setores_mesmo_nome, ids_setores_visiveis_atendente
from app.core.security import hash_senha, verificar_senha
from app.core.audit import registrar_audit

router = APIRouter(prefix="/atendentes", tags=["atendentes"])

_MAX_PAGE = 100
_DEFAULT_PAGE = 20


class OrdenarAtendentesPor(str, Enum):
    nome = "nome"
    email = "email"
    role = "role"
    ativo = "ativo"


def _atendente_para_read(atendente: Atendente, *, e_financeiro: bool = False) -> AtendenteRead:
    saas = sorted(getattr(atendente, "saas_setores", None) or [], key=lambda s: (s.nome or "", s.id))
    modo = modo_jornada_de(atendente)
    usa = modo in ("semanal", "ciclo")
    return AtendenteRead(
        id=atendente.id,
        email=atendente.email,
        nome=atendente.nome,
        role=atendente.role,
        ativo=atendente.ativo,
        created_at=atendente.created_at,
        updated_at=atendente.updated_at,
        setor_ids=[s.id for s in atendente.setores],
        e_financeiro=e_financeiro,
        must_change_password=bool(getattr(atendente, "must_change_password", False)),
        modo_jornada=modo,  # type: ignore[arg-type]
        usa_escala=usa,
        horario_semana=horario_semana_dict(atendente),
        escala_horas_trabalho=getattr(atendente, "escala_horas_trabalho", None),
        escala_horas_folga=getattr(atendente, "escala_horas_folga", None),
        escala_inicio_em=getattr(atendente, "escala_inicio_em", None),
        horario_previsto_entrada=getattr(atendente, "horario_previsto_entrada", None),
        horario_previsto_saida=getattr(atendente, "horario_previsto_saida", None),
        tolerancia_atraso_minutos=int(getattr(atendente, "tolerancia_atraso_minutos", 0) or 0),
        usar_local_empresa=bool(getattr(atendente, "usar_local_empresa", True)),
        local_empresa_raio_metros=getattr(atendente, "local_empresa_raio_metros", None),
        he_teto_minutos=getattr(atendente, "he_teto_minutos", None),
        he_teto_mensal_minutos=getattr(atendente, "he_teto_mensal_minutos", None),
        saas_setor_ids=[s.id for s in saas],
        saas_setor_nomes=[s.nome for s in saas],
    )


def _resolver_modo_jornada(data_modo: str | None, usa_escala: bool | None, atual: Atendente | None) -> str:
    if data_modo is not None:
        return (data_modo or "nenhum").strip().lower()
    if usa_escala is not None:
        return "ciclo" if usa_escala else "nenhum"
    if atual is not None:
        return modo_jornada_de(atual)
    return "nenhum"


def _aplicar_campos_jornada(atendente: Atendente, *, modo: str, update: dict) -> None:
    """Normaliza campos de jornada no dict update / no create."""
    if modo == "nenhum":
        atendente.modo_jornada = "nenhum"
        atendente.usa_escala = False
        atendente.escala_horas_trabalho = None
        atendente.escala_horas_folga = None
        atendente.escala_inicio_em = None
        atendente.horario_previsto_entrada = None
        atendente.horario_previsto_saida = None
        atendente.tolerancia_atraso_minutos = 0
        atendente.horario_semana_json = None
        return
    if modo == "semanal":
        hs = update.get("horario_semana")
        if hs is None and atendente.horario_semana_json:
            hs = horario_semana_dict(atendente)
        atendente.modo_jornada = "semanal"
        atendente.usa_escala = True
        atendente.escala_horas_trabalho = None
        atendente.escala_horas_folga = None
        atendente.escala_inicio_em = None
        atendente.horario_previsto_entrada = None
        atendente.horario_previsto_saida = None
        atendente.horario_semana_json = horario_semana_para_json(hs)
        if "tolerancia_atraso_minutos" in update:
            atendente.tolerancia_atraso_minutos = int(update["tolerancia_atraso_minutos"] or 0)
        return
    # ciclo
    atendente.modo_jornada = "ciclo"
    atendente.usa_escala = True
    atendente.horario_semana_json = None
    atendente.escala_horas_trabalho = update.get("escala_horas_trabalho")
    atendente.escala_horas_folga = update.get("escala_horas_folga")
    atendente.escala_inicio_em = update.get("escala_inicio_em")
    atendente.horario_previsto_entrada = update.get("horario_previsto_entrada")
    atendente.horario_previsto_saida = update.get("horario_previsto_saida")
    atendente.tolerancia_atraso_minutos = int(update.get("tolerancia_atraso_minutos") or 0)


@router.get("", response_model=ListaPaginada[AtendenteRead])
def listar_atendentes(
    incluir_inativos: bool = Query(False, description="Incluir atendentes inativos"),
    busca: str | None = Query(None, description="Filtra por nome ou e-mail"),
    offset: int = Query(0, ge=0),
    limit: int = Query(_DEFAULT_PAGE, ge=1, le=_MAX_PAGE),
    ordenar_por: OrdenarAtendentesPor | None = Query(None),
    ordem: OrdemLista = Query(OrdemLista.asc),
    db: Session = Depends(get_db),
    atendente_logado: Atendente = Depends(exigir_admin),
):
    q = db.query(Atendente).filter(
        Atendente.tenant_id == atendente_logado.tenant_id,
        Atendente.role != "saas_ops",
    )
    if not incluir_inativos:
        q = q.filter(Atendente.ativo.is_(True))
    if busca and busca.strip():
        term = f"%{busca.strip()}%"
        q = q.filter(or_(Atendente.nome.ilike(term), Atendente.email.ilike(term)))
    total = q.count()
    if ordenar_por is None:
        order_cols = [Atendente.nome.asc(), Atendente.id.asc()]
    elif ordenar_por == OrdenarAtendentesPor.nome:
        order_cols = [expr_ordem(Atendente.nome, ordem), expr_ordem(Atendente.id, ordem)]
    elif ordenar_por == OrdenarAtendentesPor.email:
        order_cols = [expr_ordem(Atendente.email, ordem), expr_ordem(Atendente.id, ordem)]
    elif ordenar_por == OrdenarAtendentesPor.role:
        order_cols = [expr_ordem(Atendente.role, ordem), expr_ordem(Atendente.id, ordem)]
    else:
        order_cols = [expr_ordem(Atendente.ativo, ordem), expr_ordem(Atendente.id, ordem)]
    rows = (
        q.options(joinedload(Atendente.setores))
        .order_by(*order_cols)
        .offset(offset)
        .limit(limit)
        .all()
    )
    return ListaPaginada(items=[_atendente_para_read(a) for a in rows], total=total)


@router.post("", response_model=AtendenteRead, status_code=201)
def criar_atendente(
    data: AtendenteCreate,
    db: Session = Depends(get_db),
    atendente_logado: Atendente = Depends(exigir_admin),
):
    if (
        db.query(Atendente)
        .filter(Atendente.tenant_id == atendente_logado.tenant_id, Atendente.email == data.email)
        .first()
    ):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="E-mail já cadastrado")
    role = validar_role(data.role)
    modo = _resolver_modo_jornada(data.modo_jornada, data.usa_escala, None)
    validar_campos_jornada(
        modo=modo,
        escala_horas_trabalho=data.escala_horas_trabalho,
        escala_horas_folga=data.escala_horas_folga,
        escala_inicio_em=data.escala_inicio_em,
        horario_semana=data.horario_semana,
    )
    if modo == "ciclo":
        validar_horario_previsto(data.horario_previsto_entrada, data.horario_previsto_saida)
    atendente = Atendente(
        tenant_id=atendente_logado.tenant_id,
        email=data.email,
        nome=data.nome,
        senha_hash=hash_senha(data.senha),
        role=role,
        ativo=data.ativo,
        tolerancia_atraso_minutos=int(data.tolerancia_atraso_minutos or 0) if modo != "nenhum" else 0,
        usar_local_empresa=bool(getattr(data, "usar_local_empresa", True)),
        local_empresa_raio_metros=getattr(data, "local_empresa_raio_metros", None),
        he_teto_minutos=getattr(data, "he_teto_minutos", None),
        he_teto_mensal_minutos=getattr(data, "he_teto_mensal_minutos", None),
    )
    _aplicar_campos_jornada(
        atendente,
        modo=modo,
        update={
            "horario_semana": data.horario_semana,
            "escala_horas_trabalho": data.escala_horas_trabalho,
            "escala_horas_folga": data.escala_horas_folga,
            "escala_inicio_em": data.escala_inicio_em,
            "horario_previsto_entrada": data.horario_previsto_entrada,
            "horario_previsto_saida": data.horario_previsto_saida,
            "tolerancia_atraso_minutos": data.tolerancia_atraso_minutos,
        },
    )
    db.add(atendente)
    db.flush()
    registrar_audit(db, "atendente", atendente.id, "create", atendente_logado.id)
    for setor_id in data.setor_ids:
        setor = db.query(Setor).filter(Setor.id == setor_id).first()
        if setor:
            atendente.setores.append(setor)
    db.commit()
    db.refresh(atendente)
    return _atendente_para_read(atendente)


@router.get("/me", response_model=AtendenteRead)
def me(
    atendente: Atendente = Depends(obter_atendente_atual),
    db: Session = Depends(get_db),
):
    return _atendente_para_read(atendente, e_financeiro=atendente_e_financeiro(db, atendente))


@router.post("/me/trocar-senha", response_model=AtendenteRead)
def trocar_senha_propria(
    data: TrocaSenhaPropria,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    if not verificar_senha(data.senha_atual, atendente.senha_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Senha atual incorreta.")
    if data.senha_atual == data.senha_nova:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A nova senha deve ser diferente da senha atual.",
        )
    atendente.senha_hash = hash_senha(data.senha_nova)
    atendente.must_change_password = False
    db.commit()
    db.refresh(atendente)
    return _atendente_para_read(atendente)


@router.get("/por-setor/{setor_id}", response_model=list[AtendenteRead])
def listar_atendentes_por_setor(
    setor_id: int,
    incluir_inativos: bool = Query(True, description="Incluir inativos (ex.: responsável atual)"),
    db: Session = Depends(get_db),
    atendente_logado: Atendente = Depends(obter_atendente_atual),
):
    """Atendentes vinculados ao setor (e homônimos) + administradores (elegíveis como responsáveis sem vínculo ao setor; #38)."""
    if not db.query(Setor).filter(Setor.id == setor_id).first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Setor não encontrado")
    if atendente_logado.role != "admin":
        if setor_id not in ids_setores_visiveis_atendente(db, atendente_logado):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão para este setor")
    alvo_ids = list(ids_setores_mesmo_nome(db, setor_id))
    q = (
        db.query(Atendente)
        .options(joinedload(Atendente.setores))
        .join(Atendente.setores)
        .filter(Setor.id.in_(alvo_ids))
        .distinct()
    )
    if not incluir_inativos:
        q = q.filter(Atendente.ativo.is_(True))
    rows = q.order_by(Atendente.nome).all()
    by_id = {a.id: a for a in rows}
    q_admins = (
        db.query(Atendente)
        .options(joinedload(Atendente.setores))
        .filter(Atendente.role == "admin")
    )
    if not incluir_inativos:
        q_admins = q_admins.filter(Atendente.ativo.is_(True))
    for a in q_admins.order_by(Atendente.nome).all():
        if a.id not in by_id:
            by_id[a.id] = a
    merged = sorted(by_id.values(), key=lambda x: ((x.nome or "").lower(), x.id))
    return [_atendente_para_read(a) for a in merged]


@router.get("/{atendente_id}/avaliacoes", response_model=AtendenteAvaliacoesRead)
def obter_avaliacoes_atendente(
    atendente_id: int,
    db: Session = Depends(get_db),
    _: Atendente = Depends(exigir_admin),
):
    atendente = db.query(Atendente).filter(Atendente.id == atendente_id).first()
    if not atendente:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Atendente não encontrado")
    data = calcular_avaliacoes_atendente(db, atendente_id)
    return AtendenteAvaliacoesRead(
        geral=AvaliacaoResumoRead(**data["geral"]),
        whatsapp=AvaliacaoResumoRead(**data["whatsapp"]),
        tickets=AvaliacaoResumoRead(**data["tickets"]),
    )


@router.get("/{atendente_id}", response_model=AtendenteRead)
def obter_atendente(
    atendente_id: int,
    db: Session = Depends(get_db),
    _: Atendente = Depends(exigir_admin),
):
    atendente = db.query(Atendente).filter(Atendente.id == atendente_id).first()
    if not atendente or atendente.role == "saas_ops":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Atendente não encontrado")
    return _atendente_para_read(atendente)


@router.patch("/{atendente_id}", response_model=AtendenteRead)
def atualizar_atendente(
    atendente_id: int,
    data: AtendenteUpdate,
    db: Session = Depends(get_db),
    atendente_logado: Atendente = Depends(exigir_admin),
):
    atendente = db.query(Atendente).filter(Atendente.id == atendente_id).first()
    if not atendente or atendente.role == "saas_ops":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Atendente não encontrado")
    update = data.model_dump(exclude_unset=True)
    if "senha" in update and update["senha"]:
        atendente.senha_hash = hash_senha(update.pop("senha"))
        atendente.must_change_password = False
    if "role" in update and update["role"] is not None:
        update["role"] = validar_role(update["role"])
    if "setor_ids" in update:
        setor_ids = update.pop("setor_ids")
        atendente.setores.clear()
        for setor_id in setor_ids:
            setor = db.query(Setor).filter(Setor.id == setor_id).first()
            if setor:
                atendente.setores.append(setor)

    modo = _resolver_modo_jornada(update.get("modo_jornada"), update.get("usa_escala"), atendente)
    ht = update.get("escala_horas_trabalho", atendente.escala_horas_trabalho)
    hf = update.get("escala_horas_folga", atendente.escala_horas_folga)
    inicio = update.get("escala_inicio_em", atendente.escala_inicio_em)
    hs = update.get("horario_semana")
    if hs is None and modo == "semanal":
        hs = horario_semana_dict(atendente)
    he = update.get("horario_previsto_entrada", getattr(atendente, "horario_previsto_entrada", None))
    hs_prev = update.get("horario_previsto_saida", getattr(atendente, "horario_previsto_saida", None))
    tol = update.get(
        "tolerancia_atraso_minutos",
        getattr(atendente, "tolerancia_atraso_minutos", 0),
    )
    jornada_keys = (
        "modo_jornada",
        "usa_escala",
        "escala_horas_trabalho",
        "escala_horas_folga",
        "escala_inicio_em",
        "horario_semana",
        "horario_previsto_entrada",
        "horario_previsto_saida",
        "tolerancia_atraso_minutos",
    )
    if any(k in update for k in jornada_keys):
        validar_campos_jornada(
            modo=modo,
            escala_horas_trabalho=ht,
            escala_horas_folga=hf,
            escala_inicio_em=inicio,
            horario_semana=hs if modo == "semanal" else None,
        )
        if modo == "ciclo":
            validar_horario_previsto(he, hs_prev)
        for k in jornada_keys:
            update.pop(k, None)
        _aplicar_campos_jornada(
            atendente,
            modo=modo,
            update={
                "horario_semana": hs,
                "escala_horas_trabalho": ht,
                "escala_horas_folga": hf,
                "escala_inicio_em": inicio,
                "horario_previsto_entrada": he,
                "horario_previsto_saida": hs_prev,
                "tolerancia_atraso_minutos": tol,
            },
        )

    for k, v in update.items():
        setattr(atendente, k, v)
    registrar_audit(db, "atendente", atendente_id, "update", atendente_logado.id)
    db.commit()
    db.refresh(atendente)
    return _atendente_para_read(atendente)


@router.delete("/{atendente_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_atendente(
    atendente_id: int,
    db: Session = Depends(get_db),
    _: Atendente = Depends(exigir_admin),
):
    atendente = db.query(Atendente).filter(Atendente.id == atendente_id).first()
    if not atendente or atendente.role == "saas_ops":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Atendente não encontrado")
    db.delete(atendente)
    db.commit()
