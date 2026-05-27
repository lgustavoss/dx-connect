import re
import urllib.request
import urllib.error
import json
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload, contains_eager

from app.database import get_db
from app.core.ordenacao_lista import OrdemLista, expr_ordem
from app.models import Empresa, Rede, Ticket, FuncionarioRede, FuncionarioRedeEmpresa
from app.models.atendente import Atendente
from app.schemas.empresa import (
    EmpresaCreate,
    EmpresaUpdate,
    EmpresaRead,
    ConsultaCNPJResponse,
    EmpresaListaResumo,
    RedeListaResumo,
)
from app.schemas.lista_paginada import ListaPaginada
from app.core.auth import exigir_admin, obter_atendente_atual
from app.core.audit import registrar_audit
from app.core.setor_scope import ids_setores_visiveis_atendente, select_rede_ids_com_ticket_nos_setores

router = APIRouter(prefix="/empresas", tags=["empresas"])

_MAX_PAGE = 100
_DEFAULT_PAGE = 20


class OrdenarEmpresasPor(str, Enum):
    nome = "nome"
    cnpj_cpf = "cnpj_cpf"
    cidade = "cidade"
    rede = "rede"
    ativo = "ativo"


@router.get("", response_model=ListaPaginada[EmpresaRead] | ListaPaginada[EmpresaListaResumo])
def listar_empresas(
    rede_id: int | None = Query(None),
    incluir_inativos: bool = Query(False, description="Incluir empresas inativas"),
    busca: str | None = Query(None, description="Nome, razão social, fantasia, CNPJ ou e-mail"),
    offset: int = Query(0, ge=0),
    limit: int = Query(_DEFAULT_PAGE, ge=1, le=_MAX_PAGE),
    ordenar_por: OrdenarEmpresasPor | None = Query(None),
    ordem: OrdemLista = Query(OrdemLista.asc),
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    """Admin: modelo completo. Atendente: resumo (PII mínima) só de redes que já tiveram ticket nos setores que ele atende."""
    admin = atendente.role == "admin"
    q = db.query(Empresa).filter(Empresa.tenant_id == atendente.tenant_id)
    if not admin:
        vis = ids_setores_visiveis_atendente(db, atendente)
        q = q.filter(Empresa.rede_id.in_(select_rede_ids_com_ticket_nos_setores(vis)))
    if rede_id is not None:
        q = q.filter(Empresa.rede_id == rede_id)
    if not incluir_inativos:
        q = q.filter(Empresa.ativo.is_(True))
    if busca and busca.strip():
        term = f"%{busca.strip()}%"
        q = q.filter(
            or_(
                Empresa.nome.ilike(term),
                Empresa.razao_social.ilike(term),
                Empresa.nome_fantasia.ilike(term),
                Empresa.cnpj_cpf.ilike(term),
                Empresa.email.ilike(term),
            )
        )
    total = q.count()
    if ordenar_por is None:
        order_cols = [Empresa.nome.asc(), Empresa.id.asc()]
        if not admin:
            q = q.options(joinedload(Empresa.rede))
    else:
        if ordenar_por == OrdenarEmpresasPor.rede:
            q = q.join(Empresa.rede)
            if not admin:
                q = q.options(contains_eager(Empresa.rede))
            primary = expr_ordem(Rede.nome, ordem)
        elif ordenar_por == OrdenarEmpresasPor.nome:
            if not admin:
                q = q.options(joinedload(Empresa.rede))
            primary = expr_ordem(Empresa.nome, ordem)
        elif ordenar_por == OrdenarEmpresasPor.cnpj_cpf:
            if not admin:
                q = q.options(joinedload(Empresa.rede))
            primary = expr_ordem(Empresa.cnpj_cpf, ordem)
        elif ordenar_por == OrdenarEmpresasPor.cidade:
            if not admin:
                q = q.options(joinedload(Empresa.rede))
            primary = expr_ordem(Empresa.cidade, ordem)
        else:
            if not admin:
                q = q.options(joinedload(Empresa.rede))
            primary = expr_ordem(Empresa.ativo, ordem)
        order_cols = [primary, expr_ordem(Empresa.id, ordem)]
    items = q.order_by(*order_cols).offset(offset).limit(limit).all()
    if not admin:
        resumos: list[EmpresaListaResumo] = []
        for e in items:
            r = e.rede
            resumos.append(
                EmpresaListaResumo(
                    id=e.id,
                    nome=e.nome,
                    ativo=e.ativo,
                    rede=RedeListaResumo(id=r.id, nome=r.nome) if r else RedeListaResumo(id=e.rede_id, nome=""),
                )
            )
        return ListaPaginada(items=resumos, total=total)
    return ListaPaginada(items=items, total=total)


def _digitos(s: str) -> str:
    return re.sub(r"\D", "", s) if s else ""


@router.get("/consultar-cnpj/{cnpj}", response_model=ConsultaCNPJResponse)
def consultar_cnpj(
    cnpj: str,
    _: Atendente = Depends(exigir_admin),
):
    """Consulta dados do CNPJ na ReceitaWS e retorna normalizado para preenchimento do formulário."""
    digits = _digitos(cnpj)
    if len(digits) != 14:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CNPJ deve conter 14 dígitos.",
        )
    url = f"https://www.receitaws.com.br/v1/cnpj/{digits}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "DX-Connect/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        if e.code == 429:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Limite de consultas excedido. Tente novamente em alguns minutos.",
            )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Serviço de consulta CNPJ indisponível.",
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Erro ao consultar CNPJ.",
        )
    if data.get("status") == "ERROR":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=data.get("message", "CNPJ não encontrado."),
        )
    logradouro = data.get("logradouro") or ""
    numero = data.get("numero") or ""
    complemento = data.get("complemento") or ""
    parts = [logradouro, numero, complemento]
    endereco = ", ".join(p for p in parts if p.strip())
    atv = data.get("atividade_principal")
    atividade_principal = atv[0].get("text") if isinstance(atv, list) and atv else None
    return ConsultaCNPJResponse(
        cnpj=data.get("cnpj", digits),
        razao_social=data.get("nome") or "",
        nome_fantasia=data.get("fantasia") or None,
        situacao=data.get("situacao"),
        endereco=endereco,
        numero=data.get("numero") or None,
        complemento=data.get("complemento") or None,
        bairro=data.get("bairro") or None,
        cidade=data.get("municipio") or None,
        estado=data.get("uf") or None,
        cep=data.get("cep") or None,
        email=data.get("email") or None,
        telefone=data.get("telefone") or None,
        abertura=data.get("abertura"),
        natureza_juridica=data.get("natureza_juridica"),
        atividade_principal=atividade_principal,
    )


@router.post("", response_model=EmpresaRead, status_code=201)
def criar_empresa(
    data: EmpresaCreate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_admin),
):
    rede = (
        db.query(Rede)
        .filter(Rede.id == data.rede_id, Rede.tenant_id == atendente.tenant_id)
        .first()
    )
    if not rede:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rede não encontrada")
    payload = data.model_dump()
    empresa = Empresa(**payload, tenant_id=atendente.tenant_id)
    db.add(empresa)
    db.flush()
    registrar_audit(db, "empresa", empresa.id, "create", atendente.id)
    db.commit()
    db.refresh(empresa)
    return empresa


@router.get("/{empresa_id}", response_model=EmpresaRead)
def obter_empresa(
    empresa_id: int,
    db: Session = Depends(get_db),
    _: Atendente = Depends(exigir_admin),
):
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empresa não encontrada")
    return empresa


@router.patch("/{empresa_id}", response_model=EmpresaRead)
def atualizar_empresa(
    empresa_id: int,
    data: EmpresaUpdate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_admin),
):
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empresa não encontrada")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(empresa, k, v)
    registrar_audit(db, "empresa", empresa_id, "update", atendente.id)
    db.commit()
    db.refresh(empresa)
    return empresa


@router.delete("/{empresa_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_empresa(
    empresa_id: int,
    db: Session = Depends(get_db),
    _: Atendente = Depends(exigir_admin),
):
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empresa não encontrada")
    tickets_count = db.query(Ticket).filter(Ticket.empresa_id == empresa_id).count()
    if tickets_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não é possível excluir uma empresa que possua tickets vinculados. Resolva ou transfira os tickets antes. Sugere-se inativar o registro.",
        )
    colaboradores_count = db.query(FuncionarioRede).filter(FuncionarioRede.empresa_id == empresa_id).count()
    supervisores_count = db.query(FuncionarioRedeEmpresa).filter(FuncionarioRedeEmpresa.empresa_id == empresa_id).count()
    if colaboradores_count > 0 or supervisores_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não é possível excluir uma empresa que possua funcionários vinculados (colaboradores ou supervisores). Remova ou transfira os vínculos antes. Sugere-se inativar o registro.",
        )
    db.delete(empresa)
    db.commit()
