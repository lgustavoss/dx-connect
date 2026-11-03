"""Fatura interna: geração mensal e aprovação do financeiro (#326)."""

from __future__ import annotations

import calendar
import re
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from app.models.comercial_contrato import CONTRATO_ASSINADO, Contrato
from app.models.crm import CrmNegociacaoCnpjLinha
from app.models.empresa import Empresa
from app.models.atendente import Atendente
from app.models.faturamento import (
    ANEXO_BOLETO,
    ANEXO_NFSE_PDF,
    ANEXO_TIPOS,
    ANEXO_TIPOS_NFSE,
    DIA_VENCIMENTO_MAX,
    DIA_VENCIMENTO_MIN,
    FATURA_AGUARDANDO,
    FATURA_APROVADA,
    FATURA_CANCELADA,
    FATURA_REJEITADA,
    GATILHO_DATA_INICIO,
    GATILHO_DIAS_APOS_ASSINATURA,
    GATILHO_DIAS_APOS_MARCO,
    GATILHO_OPCOES,
    GATILHO_TICKET_IMPLANTACAO_FECHADO,
    TITULO_ABERTO,
    TITULO_PAGO,
    TITULO_STATUS_FILTRO,
    TITULO_VENCIDO,
    VENCIMENTO_DIA_PADRAO,
    Fatura,
    FaturaAnexo,
    FaturamentoPolitica,
    TituloReceber,
)
from app.services import faturamento_anexo_storage as anexo_storage

TZ_SP = ZoneInfo("America/Sao_Paulo")
_COMPETENCIA_RE = re.compile(r"^(\d{4})-(\d{2})$")


def competencia_atual(hoje: date | None = None) -> str:
    d = hoje or datetime.now(TZ_SP).date()
    return f"{d.year:04d}-{d.month:02d}"


def validar_competencia(valor: str | None) -> str:
    raw = (valor or competencia_atual()).strip()
    m = _COMPETENCIA_RE.match(raw)
    if not m:
        raise HTTPException(status_code=400, detail="Competência inválida. Use YYYY-MM.")
    ano, mes = int(m.group(1)), int(m.group(2))
    if mes < 1 or mes > 12:
        raise HTTPException(status_code=400, detail="Competência inválida. Use YYYY-MM.")
    return f"{ano:04d}-{mes:02d}"


def vencimento_da_competencia(competencia: str, dia: int = VENCIMENTO_DIA_PADRAO) -> date:
    """Dia D do mês seguinte à competência (fatura de agosto vence em 10/09 por padrão).

    `dia` vem da política da instância (ou do override do contrato), nunca solto no job (#1339).
    """
    ano, mes = (int(p) for p in competencia.split("-"))
    if mes == 12:
        ano, mes = ano + 1, 1
    else:
        mes += 1
    ultimo = calendar.monthrange(ano, mes)[1]
    return date(ano, mes, min(max(dia, DIA_VENCIMENTO_MIN), min(DIA_VENCIMENTO_MAX, ultimo)))


def garantir_politica(db: Session) -> FaturamentoPolitica:
    """Singleton da política de faturamento; semente = perfil atual (dia 10, data_inicio)."""
    row = db.query(FaturamentoPolitica).order_by(FaturamentoPolitica.id.asc()).first()
    if row:
        return row
    row = FaturamentoPolitica(
        id=1,
        dia_vencimento=VENCIMENTO_DIA_PADRAO,
        gatilho=GATILHO_DATA_INICIO,
        gatilho_dias=0,
        proporcional_primeira_fatura=False,
    )
    db.add(row)
    db.flush()
    return row


def atualizar_politica(db: Session, data) -> FaturamentoPolitica:
    row = garantir_politica(db)
    payload = data.model_dump(exclude_unset=True)
    if payload.get("dia_vencimento") is not None:
        dia = int(payload["dia_vencimento"])
        if dia < DIA_VENCIMENTO_MIN or dia > DIA_VENCIMENTO_MAX:
            raise HTTPException(status_code=400, detail="Dia de vencimento deve ficar entre 1 e 28.")
        row.dia_vencimento = dia
    if payload.get("gatilho") is not None:
        gatilho = str(payload["gatilho"]).strip()
        if gatilho not in GATILHO_OPCOES:
            raise HTTPException(status_code=400, detail="Gatilho de mensalidade inválido.")
        row.gatilho = gatilho
    if payload.get("gatilho_dias") is not None:
        row.gatilho_dias = int(payload["gatilho_dias"])
    if payload.get("proporcional_primeira_fatura") is not None:
        row.proporcional_primeira_fatura = bool(payload["proporcional_primeira_fatura"])
    db.flush()
    return row


def politica_para_read(db: Session) -> dict:
    row = garantir_politica(db)
    return {
        "dia_vencimento": row.dia_vencimento,
        "gatilho": row.gatilho or GATILHO_DATA_INICIO,
        "gatilho_dias": int(row.gatilho_dias or 0),
        "proporcional_primeira_fatura": bool(row.proporcional_primeira_fatura),
    }


def dia_vencimento_do_contrato(db: Session, contrato: Contrato, *, politica: FaturamentoPolitica | None = None) -> int:
    """Override do contrato (negociação) vence a política da instância; fallback dia 10."""
    override = getattr(contrato, "dia_vencimento_override", None)
    if override is not None and DIA_VENCIMENTO_MIN <= int(override) <= DIA_VENCIMENTO_MAX:
        return int(override)
    pol = politica or garantir_politica(db)
    dia = int(pol.dia_vencimento or VENCIMENTO_DIA_PADRAO)
    if dia < DIA_VENCIMENTO_MIN or dia > DIA_VENCIMENTO_MAX:
        return VENCIMENTO_DIA_PADRAO
    return dia


def vencimento_da_fatura(
    db: Session,
    contrato: Contrato,
    competencia: str,
    *,
    politica: FaturamentoPolitica | None = None,
) -> date:
    return vencimento_da_competencia(competencia, dia_vencimento_do_contrato(db, contrato, politica=politica))



def _linha_contrato(db: Session, contrato: Contrato) -> CrmNegociacaoCnpjLinha | None:
    if contrato.linha:
        return contrato.linha
    return db.query(CrmNegociacaoCnpjLinha).filter(CrmNegociacaoCnpjLinha.id == contrato.negociacao_linha_cnpj_id).first()


def _anexo_para_read(a: FaturaAnexo) -> dict:
    return {
        "id": a.id,
        "tipo": a.tipo,
        "nome_original": a.nome_original,
        "content_type": a.content_type,
        "tamanho_bytes": a.tamanho_bytes,
        "created_at": a.created_at,
    }


def _hoje() -> date:
    return datetime.now(TZ_SP).date()


def status_titulo_efetivo(row: TituloReceber, hoje: date | None = None) -> str:
    if row.status == TITULO_ABERTO and row.vencimento < (hoje or _hoje()):
        return TITULO_VENCIDO
    return row.status


def titulo_para_read(db: Session, row: TituloReceber) -> dict:
    fatura = row.fatura
    contrato = (fatura.contrato if fatura else None) or (
        db.query(Contrato).filter(Contrato.id == row.contrato_id).first()
    )
    empresa = row.empresa
    if empresa is None and row.empresa_id:
        empresa = db.query(Empresa).filter(Empresa.id == row.empresa_id).first()
    if empresa is None and fatura is not None:
        empresa = fatura.empresa
    linha = _linha_contrato(db, contrato) if contrato else None
    return {
        "id": row.id,
        "fatura_id": row.fatura_id,
        "contrato_id": row.contrato_id,
        "empresa_id": row.empresa_id,
        "empresa_nome": empresa.nome if empresa else None,
        "cnpj": linha.cnpj if linha else (empresa.cnpj_cpf if empresa else None),
        "razao_social": (linha.razao_social if linha else None) or (empresa.razao_social if empresa else None),
        "competencia": row.competencia,
        "valor": row.valor,
        "vencimento": row.vencimento,
        "status": status_titulo_efetivo(row),
        "status_persistido": row.status,
        "pago_em": row.pago_em,
        "valor_pago": row.valor_pago,
        "baixa_observacao": row.baixa_observacao,
        "baixado_por_id": row.baixado_por_id,
        "baixado_por_nome": row.baixado_por.nome if row.baixado_por else None,
        "baixado_em": row.baixado_em,
    }


def garantir_titulo_da_fatura(db: Session, fatura: Fatura) -> TituloReceber:
    existente = fatura.titulo or db.query(TituloReceber).filter(TituloReceber.fatura_id == fatura.id).first()
    if existente:
        return existente
    row = TituloReceber(
        fatura_id=fatura.id,
        contrato_id=fatura.contrato_id,
        empresa_id=fatura.empresa_id,
        competencia=fatura.competencia,
        valor=fatura.valor,
        vencimento=fatura.vencimento,
        status=TITULO_ABERTO,
    )
    db.add(row)
    db.flush()
    fatura.titulo = row
    return row


def documentos_completos(row: Fatura) -> bool:
    tipos = {a.tipo for a in (row.anexos or [])}
    if ANEXO_BOLETO not in tipos:
        return False
    if bool(row.emite_nfse) and ANEXO_NFSE_PDF not in tipos:
        return False
    return True


def fatura_para_read(db: Session, row: Fatura) -> dict:
    contrato = row.contrato or db.query(Contrato).filter(Contrato.id == row.contrato_id).first()
    empresa = row.empresa
    if empresa is None and row.empresa_id:
        empresa = db.query(Empresa).filter(Empresa.id == row.empresa_id).first()
    linha = _linha_contrato(db, contrato) if contrato else None
    anexos = sorted(row.anexos or [], key=lambda a: (a.tipo, a.id))
    return {
        "id": row.id,
        "contrato_id": row.contrato_id,
        "empresa_id": row.empresa_id,
        "empresa_nome": empresa.nome if empresa else None,
        "cnpj": linha.cnpj if linha else (empresa.cnpj_cpf if empresa else None),
        "razao_social": (linha.razao_social if linha else None) or (empresa.razao_social if empresa else None),
        "competencia": row.competencia,
        "valor": row.valor,
        "vencimento": row.vencimento,
        "emite_nfse": bool(row.emite_nfse),
        "status": row.status,
        "rejeicao_motivo": row.rejeicao_motivo,
        "gerada_em": row.gerada_em,
        "aprovada_por_id": row.aprovada_por_id,
        "aprovada_por_nome": row.aprovada_por.nome if row.aprovada_por else None,
        "aprovada_em": row.aprovada_em,
        "boleto_linha_digitavel": row.boleto_linha_digitavel,
        "boleto_nosso_numero": row.boleto_nosso_numero,
        "nfse_numero": row.nfse_numero,
        "documentos_completos": documentos_completos(row),
        "anexos": [_anexo_para_read(a) for a in anexos],
        "titulo": titulo_para_read(db, row.titulo) if row.titulo else None,
    }


def _contratos_faturaveis(db: Session) -> list[Contrato]:
    """Um contrato assinado por linha. O mais recente inclui a mudança e é o que fatura."""
    rows = (
        db.query(Contrato)
        .options(joinedload(Contrato.linha))
        .filter(Contrato.status == CONTRATO_ASSINADO, Contrato.empresa_id.isnot(None))
        .order_by(Contrato.id.asc())
        .all()
    )
    por_linha: dict[int, Contrato] = {}
    for row in rows:
        por_linha[row.negociacao_linha_cnpj_id] = row
    return list(por_linha.values())


def _emite_nfse_empresa(db: Session, empresa_id: int | None) -> bool:
    if not empresa_id:
        return True
    emp = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if emp is None:
        return True
    return bool(getattr(emp, "emite_nfse", True))


MOTIVO_AGUARDANDO_PRIMEIRA_VENDA = "aguardando_primeira_venda"
MOTIVO_AGUARDANDO_IMPLANTACAO = "aguardando_fechamento_implantacao"


def _ticket_implantacao_fechado_em(db: Session, contrato_id: int) -> date | None:
    """Data de fechamento do ticket de implantação do contrato (#1339)."""
    from app.models.ticket import Ticket

    row = (
        db.query(Ticket)
        .filter(Ticket.contrato_id == contrato_id)
        .order_by(Ticket.id.asc())
        .first()
    )
    if row is None or row.fechado_em is None:
        return None
    return row.fechado_em.date()


def inicio_da_mensalidade(
    db: Session,
    contrato: Contrato,
    *,
    politica: FaturamentoPolitica | None = None,
) -> tuple[date | None, str | None]:
    """Data em que a mensalidade começa a contar e, se ainda não pode nascer, o motivo.

    Ordem: override do contrato (negociação) > gatilho da instância. Devolve
    `(None, motivo)` quando o gatilho depende de um marco que ainda não aconteceu —
    a fatura não nasce e a tela sinaliza em vez de silenciar (#1340).
    """
    override = getattr(contrato, "inicio_mensalidade_override", None)
    if override is not None:
        return override, None
    pol = politica or garantir_politica(db)
    gatilho = pol.gatilho or GATILHO_DATA_INICIO
    dias = max(int(pol.gatilho_dias or 0), 0)
    if gatilho == GATILHO_DIAS_APOS_MARCO:
        marco = getattr(contrato, "primeira_venda_pdv", None)
        if marco is None:
            return None, MOTIVO_AGUARDANDO_PRIMEIRA_VENDA
        base = marco
    elif gatilho == GATILHO_TICKET_IMPLANTACAO_FECHADO:
        base = _ticket_implantacao_fechado_em(db, contrato.id)
        if base is None:
            return None, MOTIVO_AGUARDANDO_IMPLANTACAO
    elif gatilho == GATILHO_DIAS_APOS_ASSINATURA:
        base = contrato.assinado_em.date() if contrato.assinado_em else contrato.data_inicio
    else:
        base = contrato.data_inicio
    if base is None:
        return None, None
    return base + timedelta(days=dias), None


def _competencia_antes_inicio(inicio: date | None, competencia: str) -> bool:
    if inicio is None:
        return False
    return competencia < f"{inicio.year:04d}-{inicio.month:02d}"


def _limpar_documentos(db: Session, row: Fatura) -> None:
    for a in list(row.anexos or []):
        anexo_storage.apagar_arquivo(a.storage_key)
        db.delete(a)
    row.anexos = []
    row.boleto_linha_digitavel = None
    row.boleto_nosso_numero = None
    row.nfse_numero = None


def _preencher_fatura(
    db: Session,
    row: Fatura,
    contrato: Contrato,
    competencia: str,
    *,
    politica: FaturamentoPolitica | None = None,
) -> None:
    row.contrato_id = contrato.id
    row.empresa_id = contrato.empresa_id
    row.competencia = competencia
    row.valor = Decimal(str(contrato.valor_mensalidade or 0))
    row.vencimento = vencimento_da_fatura(db, contrato, competencia, politica=politica)
    row.emite_nfse = _emite_nfse_empresa(db, contrato.empresa_id)
    row.status = FATURA_AGUARDANDO
    row.rejeicao_motivo = None
    row.aprovada_por_id = None
    row.aprovada_em = None
    row.gerada_em = datetime.now(timezone.utc)
    _limpar_documentos(db, row)


def obter_fatura(db: Session, fatura_id: int) -> Fatura:
    row = (
        db.query(Fatura)
        .options(
            joinedload(Fatura.contrato).joinedload(Contrato.linha),
            joinedload(Fatura.empresa),
            joinedload(Fatura.aprovada_por),
            joinedload(Fatura.anexos),
            joinedload(Fatura.titulo).joinedload(TituloReceber.baixado_por),
        )
        .filter(Fatura.id == fatura_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Fatura não encontrada.")
    return row


def listar_faturas(
    db: Session,
    *,
    competencia: str | None,
    status_filtro: str | None,
    emite_nfse: bool | None = None,
) -> list[Fatura]:
    q = db.query(Fatura).options(
        joinedload(Fatura.contrato).joinedload(Contrato.linha),
        joinedload(Fatura.empresa),
        joinedload(Fatura.aprovada_por),
        joinedload(Fatura.anexos),
        joinedload(Fatura.titulo).joinedload(TituloReceber.baixado_por),
    )
    if competencia:
        q = q.filter(Fatura.competencia == validar_competencia(competencia))
    if status_filtro:
        q = q.filter(Fatura.status == status_filtro.strip())
    if emite_nfse is not None:
        q = q.filter(Fatura.emite_nfse.is_(emite_nfse))
    return q.order_by(Fatura.competencia.desc(), Fatura.id.desc()).all()


def listar_contratos_elegiveis(db: Session) -> list[dict]:
    out: list[dict] = []
    politica = garantir_politica(db)
    for c in _contratos_faturaveis(db):
        emp = db.query(Empresa).filter(Empresa.id == c.empresa_id).first() if c.empresa_id else None
        linha = _linha_contrato(db, c)
        inicio, motivo = inicio_da_mensalidade(db, c, politica=politica)
        out.append(
            {
                "id": c.id,
                "empresa_id": c.empresa_id,
                "empresa_nome": emp.nome if emp else None,
                "cnpj": linha.cnpj if linha else (emp.cnpj_cpf if emp else None),
                "razao_social": (linha.razao_social if linha else None) or (emp.razao_social if emp else None),
                "valor_mensalidade": c.valor_mensalidade,
                "dia_vencimento": dia_vencimento_do_contrato(db, c, politica=politica),
                "inicio_mensalidade": inicio,
                "aguardando_motivo": motivo,
            }
        )
    return out


def gerar_fatura_contrato(db: Session, contrato_id: int, competencia: str | None) -> tuple[Fatura, bool]:
    comp = validar_competencia(competencia)
    contrato = (
        db.query(Contrato)
        .options(joinedload(Contrato.linha))
        .filter(Contrato.id == contrato_id)
        .first()
    )
    if not contrato:
        raise HTTPException(status_code=404, detail="Contrato não encontrado.")
    if contrato.status != CONTRATO_ASSINADO or not contrato.empresa_id:
        raise HTTPException(status_code=400, detail="Só contratos assinados com empresa vinculada geram fatura.")
    politica = garantir_politica(db)
    inicio, motivo = inicio_da_mensalidade(db, contrato, politica=politica)
    if motivo:
        raise HTTPException(
            status_code=400,
            detail={
                MOTIVO_AGUARDANDO_PRIMEIRA_VENDA: "Mensalidade aguardando a data da primeira venda no PDV.",
                MOTIVO_AGUARDANDO_IMPLANTACAO: "Mensalidade aguardando o fechamento do ticket de implantação.",
            }.get(motivo, "Mensalidade ainda não começou."),
        )
    if _competencia_antes_inicio(inicio, comp):
        raise HTTPException(status_code=400, detail="Competência anterior ao início do contrato.")
    existente = db.query(Fatura).filter(Fatura.contrato_id == contrato.id, Fatura.competencia == comp).first()
    if existente:
        if existente.status == FATURA_APROVADA:
            raise HTTPException(status_code=400, detail="Já existe fatura aprovada desta competência.")
        if existente.status == FATURA_CANCELADA:
            raise HTTPException(status_code=400, detail="Fatura desta competência está cancelada.")
        if existente.status == FATURA_AGUARDANDO:
            return existente, False
        _preencher_fatura(db, existente, contrato, comp, politica=politica)
        db.flush()
        return existente, False
    row = Fatura()
    _preencher_fatura(db, row, contrato, comp, politica=politica)
    db.add(row)
    db.flush()
    return row, True


def gerar_competencia(
    db: Session,
    competencia: str | None,
    *,
    reabrir_rejeitadas: bool = False,
) -> tuple[str, int, int, int, int, int | None]:
    """Gera faturas da competência. O job não reabre rejeitadas; a acção manual sim."""
    comp = validar_competencia(competencia)
    politica = garantir_politica(db)
    criadas = 0
    existentes = 0
    reabertas = 0
    aguardando = 0
    audit_id: int | None = None
    for contrato in _contratos_faturaveis(db):
        inicio, motivo = inicio_da_mensalidade(db, contrato, politica=politica)
        if motivo:
            aguardando += 1
            continue
        if _competencia_antes_inicio(inicio, comp):
            continue
        existente = db.query(Fatura).filter(Fatura.contrato_id == contrato.id, Fatura.competencia == comp).first()
        if existente:
            if reabrir_rejeitadas and existente.status == FATURA_REJEITADA:
                _preencher_fatura(db, existente, contrato, comp, politica=politica)
                reabertas += 1
                if audit_id is None:
                    audit_id = existente.id
            else:
                existentes += 1
            continue
        row = Fatura()
        _preencher_fatura(db, row, contrato, comp, politica=politica)
        db.add(row)
        db.flush()
        criadas += 1
        if audit_id is None:
            audit_id = row.id
    db.flush()
    return comp, criadas, existentes, reabertas, aguardando, audit_id


def processar_faturamento_mensal(db: Session) -> int:
    """Job: gera faturas novas da competência atual (idempotente; não reabre rejeitadas)."""
    _, criadas, _, _, _, _ = gerar_competencia(db, None, reabrir_rejeitadas=False)
    return criadas


def aprovar_fatura(db: Session, row: Fatura, ator: Atendente) -> Fatura:
    if row.status != FATURA_AGUARDANDO:
        raise HTTPException(status_code=400, detail="Só faturas aguardando aprovação podem ser aprovadas.")
    row.status = FATURA_APROVADA
    row.aprovada_por_id = ator.id
    row.aprovada_em = datetime.now(timezone.utc)
    row.rejeicao_motivo = None
    db.flush()
    garantir_titulo_da_fatura(db, row)
    db.flush()
    return row


def rejeitar_fatura(db: Session, row: Fatura, motivo: str) -> Fatura:
    if row.status != FATURA_AGUARDANDO:
        raise HTTPException(status_code=400, detail="Só faturas aguardando aprovação podem ser rejeitadas.")
    texto = (motivo or "").strip()
    if len(texto) < 3:
        raise HTTPException(status_code=400, detail="Informe o motivo da rejeição.")
    row.status = FATURA_REJEITADA
    row.rejeicao_motivo = texto
    row.aprovada_por_id = None
    row.aprovada_em = None
    db.flush()
    return row


def _exigir_aprovada(row: Fatura) -> None:
    if row.status != FATURA_APROVADA:
        raise HTTPException(status_code=400, detail="Só dá para anexar documentos em fatura aprovada.")


def _normalizar_texto_curto(valor: str | None, *, max_len: int) -> str | None:
    if valor is None:
        return None
    texto = " ".join(valor.split()).strip()
    if not texto:
        return None
    return texto[:max_len]


def _normalizar_linha_digitavel(valor: str | None) -> str | None:
    if valor is None:
        return None
    digits = re.sub(r"\D", "", valor)
    if not digits:
        return None
    if len(digits) < 44 or len(digits) > 48:
        raise HTTPException(
            status_code=400,
            detail="Linha digitável inválida. Use os números do boleto (44 a 48 dígitos).",
        )
    return digits


def atualizar_documentos(
    db: Session,
    row: Fatura,
    *,
    boleto_linha_digitavel: str | None = None,
    boleto_nosso_numero: str | None = None,
    nfse_numero: str | None = None,
) -> Fatura:
    _exigir_aprovada(row)
    if boleto_linha_digitavel is not None:
        row.boleto_linha_digitavel = _normalizar_linha_digitavel(boleto_linha_digitavel)
    if boleto_nosso_numero is not None:
        row.boleto_nosso_numero = _normalizar_texto_curto(boleto_nosso_numero, max_len=40)
    if nfse_numero is not None:
        if not row.emite_nfse and _normalizar_texto_curto(nfse_numero, max_len=40):
            raise HTTPException(status_code=400, detail="Esta fatura não emite NFS-e.")
        row.nfse_numero = _normalizar_texto_curto(nfse_numero, max_len=40)
    db.flush()
    return row


def gravar_anexo(
    db: Session,
    row: Fatura,
    *,
    tipo: str,
    data: bytes,
    nome_original: str | None,
    content_type: str | None,
    ator: Atendente,
) -> FaturaAnexo:
    _exigir_aprovada(row)
    tipo_norm = (tipo or "").strip().lower()
    if tipo_norm not in ANEXO_TIPOS:
        raise HTTPException(status_code=400, detail="Tipo de documento inválido.")
    if tipo_norm in ANEXO_TIPOS_NFSE and not row.emite_nfse:
        raise HTTPException(status_code=400, detail="Esta fatura não emite NFS-e.")
    try:
        nome, mime = anexo_storage.validar_upload(nome_original, content_type, len(data), tipo=tipo_norm)
        storage_key = anexo_storage.gravar_bytes_em_disco(data, mimetype=mime, nome_original=nome)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except OSError as e:
        raise HTTPException(status_code=500, detail="Falha ao gravar o arquivo.") from e

    existente = next((a for a in (row.anexos or []) if a.tipo == tipo_norm), None)
    if existente:
        anexo_storage.apagar_arquivo(existente.storage_key)
        existente.nome_original = nome
        existente.content_type = mime
        existente.tamanho_bytes = len(data)
        existente.storage_key = storage_key
        existente.enviado_por_id = ator.id
        db.flush()
        return existente

    anexo = FaturaAnexo(
        fatura_id=row.id,
        tipo=tipo_norm,
        nome_original=nome,
        content_type=mime,
        tamanho_bytes=len(data),
        storage_key=storage_key,
        enviado_por_id=ator.id,
    )
    db.add(anexo)
    db.flush()
    row.anexos.append(anexo)
    return anexo


def obter_anexo(db: Session, row: Fatura, anexo_id: int) -> FaturaAnexo:
    anexo = next((a for a in (row.anexos or []) if a.id == anexo_id), None)
    if anexo is None:
        raise HTTPException(status_code=404, detail="Anexo não encontrado.")
    return anexo


def remover_anexo(db: Session, row: Fatura, anexo_id: int) -> Fatura:
    _exigir_aprovada(row)
    anexo = obter_anexo(db, row, anexo_id)
    anexo_storage.apagar_arquivo(anexo.storage_key)
    db.delete(anexo)
    db.flush()
    return row


def obter_titulo(db: Session, titulo_id: int) -> TituloReceber:
    row = (
        db.query(TituloReceber)
        .options(
            joinedload(TituloReceber.fatura).joinedload(Fatura.contrato).joinedload(Contrato.linha),
            joinedload(TituloReceber.fatura).joinedload(Fatura.empresa),
            joinedload(TituloReceber.empresa),
            joinedload(TituloReceber.baixado_por),
        )
        .filter(TituloReceber.id == titulo_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Título não encontrado.")
    return row


def listar_titulos(
    db: Session,
    *,
    competencia: str | None,
    status_filtro: str | None,
) -> list[TituloReceber]:
    q = db.query(TituloReceber).options(
        joinedload(TituloReceber.fatura).joinedload(Fatura.contrato).joinedload(Contrato.linha),
        joinedload(TituloReceber.fatura).joinedload(Fatura.empresa),
        joinedload(TituloReceber.empresa),
        joinedload(TituloReceber.baixado_por),
    )
    if competencia:
        q = q.filter(TituloReceber.competencia == validar_competencia(competencia))
    status_norm = (status_filtro or "").strip()
    hoje = _hoje()
    if status_norm:
        if status_norm not in TITULO_STATUS_FILTRO:
            raise HTTPException(status_code=400, detail="Status de título inválido.")
        if status_norm == TITULO_VENCIDO:
            q = q.filter(TituloReceber.status == TITULO_ABERTO, TituloReceber.vencimento < hoje)
        elif status_norm == TITULO_ABERTO:
            q = q.filter(TituloReceber.status == TITULO_ABERTO, TituloReceber.vencimento >= hoje)
        else:
            q = q.filter(TituloReceber.status == status_norm)
    return q.order_by(TituloReceber.vencimento.asc(), TituloReceber.id.desc()).all()


def baixar_titulo(
    db: Session,
    row: TituloReceber,
    ator: Atendente,
    *,
    pago_em: date | None,
    valor_pago: Decimal | None,
    observacao: str | None,
) -> TituloReceber:
    efetivo = status_titulo_efetivo(row)
    if efetivo not in {TITULO_ABERTO, TITULO_VENCIDO}:
        raise HTTPException(status_code=400, detail="Só títulos em aberto ou vencidos podem receber baixa.")
    valor = Decimal(str(valor_pago if valor_pago is not None else row.valor))
    if valor <= 0:
        raise HTTPException(status_code=400, detail="Informe um valor pago maior que zero.")
    row.status = TITULO_PAGO
    row.valor_pago = valor
    row.pago_em = pago_em or _hoje()
    row.baixa_observacao = _normalizar_texto_curto(observacao, max_len=2000)
    row.baixado_por_id = ator.id
    row.baixado_em = datetime.now(timezone.utc)
    db.flush()
    return row
