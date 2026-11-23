"""Fluxo de assinatura eletrônica multiparte do contrato (#1380 / #1429)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.core.audit import registrar_audit
from app.models.atendente import Atendente
from app.models.comercial_contrato import (
    CONTRATO_ASSINADO,
    CONTRATO_ENVIADO,
    CONTRATO_RASCUNHO,
    Contrato,
)
from app.models.contrato_assinatura import (
    DOCUSEAL_ROLE_FIXO,
    PAPEL_CONTRATADA,
    PAPEL_CONTRATANTE,
    PAPEL_TESTEMUNHA,
    PROVEDOR_DOCUSEAL,
    PROVEDOR_EXTERNO,
    STATUS_ASSINADO,
    STATUS_ATIVOS,
    STATUS_CANCELADO,
    STATUS_ENVIADO,
    STATUS_ERRO,
    STATUS_EXPIRADO,
    STATUS_PARCIAL,
    STATUS_PENDENTE,
    STATUS_RECUSADO,
    STATUS_VISUALIZADO,
    ContratoAssinatura,
    ContratoAssinaturaParte,
)
from app.models.crm import ATIVIDADE_DOCUMENTO, CrmNegociacaoAtividade
from app.schemas.comercial_contrato import ContratoMarcarAssinadoIn
from app.schemas.contrato_assinatura import (
    ContratoAssinaturaEnviarIn,
    ContratoAssinaturaParteIn,
    formatar_cpf,
    mascarar_cpf,
)
from app.services import comercial_contrato as contrato_svc
from app.services import contrato_assinatura_storage as storage
from app.services import docuseal_client as docuseal
from app.services.email_send_sistema import enviar_mensagem_texto_sistema


def _agora() -> datetime:
    return datetime.now(timezone.utc)


def _expira_em() -> datetime:
    dias = max(1, int(settings.DOCUSEAL_EXPIRACAO_DIAS or 7))
    return _agora() + timedelta(days=dias)


def _parte_to_read(p: ContratoAssinaturaParte) -> dict[str, Any]:
    return {
        "id": p.id,
        "papel": p.papel,
        "ordem": p.ordem,
        "nome": p.nome,
        "email": p.email,
        "cpf_mascarado": mascarar_cpf(p.cpf),
        "telefone": p.telefone,
        "role_docuseal": p.role_docuseal,
        "submitter_slug": p.submitter_slug,
        "link_assinatura": p.link_assinatura,
        "status": p.status,
        "visualizado_em": p.visualizado_em,
        "assinado_em": p.assinado_em,
        "ultimo_erro": p.ultimo_erro,
    }


def to_read(row: ContratoAssinatura) -> dict[str, Any]:
    partes = list(row.partes or [])
    return {
        "id": row.id,
        "contrato_id": row.contrato_id,
        "provedor": row.provedor,
        "status": row.status,
        "submission_id": row.submission_id,
        "submitter_slug": row.submitter_slug,
        "link_assinatura": row.link_assinatura,
        "enviado_em": row.enviado_em,
        "visualizado_em": row.visualizado_em,
        "assinado_em": row.assinado_em,
        "expira_em": row.expira_em,
        "tem_pdf_assinado": bool(row.pdf_assinado_path),
        "tem_audit_log": bool(row.audit_log_path),
        "tem_selfie": bool(row.selfie_path),
        "pdf_sha256": row.pdf_sha256,
        "audit_sha256": row.audit_sha256,
        "ultimo_erro": row.ultimo_erro,
        "criado_por_id": row.criado_por_id,
        "created_at": row.created_at,
        "partes": [_parte_to_read(p) for p in partes],
    }


def envelope_ativo(db: Session, contrato_id: int) -> ContratoAssinatura | None:
    return (
        db.query(ContratoAssinatura)
        .options(joinedload(ContratoAssinatura.partes))
        .filter(
            ContratoAssinatura.contrato_id == contrato_id,
            ContratoAssinatura.status.in_(tuple(STATUS_ATIVOS)),
        )
        .order_by(ContratoAssinatura.id.desc())
        .first()
    )


def ultima_assinatura(db: Session, contrato_id: int) -> ContratoAssinatura | None:
    return (
        db.query(ContratoAssinatura)
        .options(joinedload(ContratoAssinatura.partes))
        .filter(ContratoAssinatura.contrato_id == contrato_id)
        .order_by(ContratoAssinatura.id.desc())
        .first()
    )


def _exige_configurado() -> None:
    if not docuseal.docuseal_configurado() and docuseal._factory is None:  # noqa: SLF001
        raise HTTPException(
            status_code=503,
            detail=(
                "Assinatura eletrônica não está configurada nesta instância. "
                "Use «Anexar PDF assinado» (assinatura externa) ou configure o DocuSeal."
            ),
        )


def _assert_contrato_enviavel(row: Contrato) -> None:
    if row.status not in {CONTRATO_RASCUNHO, CONTRATO_ENVIADO}:
        raise HTTPException(
            status_code=400,
            detail="Só contratos em rascunho ou enviados podem ir para assinatura eletrônica.",
        )


def _roles_docuseal(signatarios: list[ContratoAssinaturaParteIn]) -> list[tuple[ContratoAssinaturaParteIn, str]]:
    """Mapeia papel interno → role do template DocuSeal."""
    out: list[tuple[ContratoAssinaturaParteIn, str]] = []
    n_testemunha = 0
    for s in signatarios:
        if s.papel == PAPEL_TESTEMUNHA:
            n_testemunha += 1
            out.append((s, f"Testemunha {n_testemunha}"))
        else:
            out.append((s, DOCUSEAL_ROLE_FIXO[s.papel]))
    return out


def _cancelar_ativo(db: Session, ativo: ContratoAssinatura, *, motivo: str) -> None:
    if ativo.provedor == PROVEDOR_DOCUSEAL and ativo.submission_id:
        try:
            docuseal.get_client().cancelar_submissao(ativo.submission_id)
        except docuseal.DocusealError:
            ativo.ultimo_erro = f"Cancelamento remoto falhou ao {motivo}."
    ativo.status = STATUS_CANCELADO
    ativo.updated_at = _agora()
    for p in ativo.partes or []:
        if p.status in STATUS_ATIVOS or p.status == STATUS_PENDENTE:
            p.status = STATUS_CANCELADO
            p.updated_at = _agora()
    db.flush()


def enviar_para_assinatura(
    db: Session,
    row: Contrato,
    data: ContratoAssinaturaEnviarIn,
    ator: Atendente,
) -> ContratoAssinatura:
    _exige_configurado()
    _assert_contrato_enviavel(row)
    contrato_svc.garantir_pdf(db, row)

    ativo = envelope_ativo(db, row.id)
    if ativo is not None:
        if not data.forcar_reenvio:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Já existe um envelope de assinatura ativo neste contrato. "
                    "Cancele ou reenvie com forcar_reenvio=true."
                ),
            )
        _cancelar_ativo(db, ativo, motivo="reenvio")

    mapeados = _roles_docuseal(data.signatarios)
    # Ordem estável: contratante, contratada, testemunhas.
    ordem_papel = {PAPEL_CONTRATANTE: 0, PAPEL_CONTRATADA: 1, PAPEL_TESTEMUNHA: 2}
    mapeados.sort(key=lambda x: (ordem_papel.get(x[0].papel, 9), x[1]))

    submitters_payload = []
    for s, role in mapeados:
        cpf_fmt = formatar_cpf(s.cpf) or s.cpf
        item: dict[str, Any] = {
            "role": role,
            "name": s.nome,
            "email": s.email,
            # Pré-preenche o campo CPF do template (nome do field = «CPF»).
            "fields": [{"name": "CPF", "default_value": cpf_fmt}],
        }
        if s.telefone:
            item["phone"] = s.telefone
        submitters_payload.append(item)

    template_id = (settings.DOCUSEAL_TEMPLATE_ID or "").strip()
    client = docuseal.get_client()
    try:
        sub = client.criar_submissao(
            template_id=template_id,
            submitters=submitters_payload,
            send_email=False,
        )
    except docuseal.DocusealError as exc:
        falha = ContratoAssinatura(
            contrato_id=row.id,
            provedor=PROVEDOR_DOCUSEAL,
            status=STATUS_ERRO,
            criado_por_id=ator.id,
            ultimo_erro=exc.mensagem,
        )
        db.add(falha)
        db.flush()
        registrar_audit(
            db,
            entity_type="contrato_assinatura",
            entity_id=falha.id,
            action="create",
            atendente_id=ator.id,
            payload={"erro": exc.mensagem, "contrato_id": row.id},
        )
        return falha

    # Casa resposta DocuSeal com o pedido (por role, depois e-mail).
    por_role = {s.role: s for s in sub.submitters}
    por_email = {(s.email or "").lower(): s for s in sub.submitters if s.email}

    agora = _agora()
    env = ContratoAssinatura(
        contrato_id=row.id,
        provedor=PROVEDOR_DOCUSEAL,
        status=STATUS_ENVIADO,
        submission_id=sub.submission_id,
        enviado_em=agora,
        expira_em=_expira_em(),
        criado_por_id=ator.id,
    )
    db.add(env)
    db.flush()

    partes: list[ContratoAssinaturaParte] = []
    for idx, (s, role) in enumerate(mapeados):
        match = por_role.get(role) or por_email.get(s.email.lower())
        slug = match.slug if match else None
        link = match.link_assinatura if match else None
        parte = ContratoAssinaturaParte(
            assinatura_id=env.id,
            papel=s.papel,
            ordem=idx,
            nome=s.nome,
            email=s.email,
            cpf=s.cpf,
            telefone=s.telefone,
            role_docuseal=role,
            submitter_slug=slug,
            link_assinatura=link,
            status=STATUS_ENVIADO,
        )
        db.add(parte)
        partes.append(parte)

    # Atalhos no envelope = contratante (ou primeira parte).
    principal = next((p for p in partes if p.papel == PAPEL_CONTRATANTE), partes[0] if partes else None)
    if principal is not None:
        env.submitter_slug = principal.submitter_slug
        env.link_assinatura = principal.link_assinatura

    if row.status == CONTRATO_RASCUNHO:
        row.status = CONTRATO_ENVIADO
        if row.enviado_em is None:
            row.enviado_em = agora
    linha = row.linha or contrato_svc.obter_linha(db, row.negociacao_linha_cnpj_id)
    n_partes = len(partes)
    db.add(
        CrmNegociacaoAtividade(
            negociacao_id=linha.negociacao_id,
            autor_id=ator.id,
            tipo=ATIVIDADE_DOCUMENTO,
            texto=(
                f"Contrato #{row.id} enviado para assinatura eletrônica "
                f"({n_partes} parte(s): DocuSeal)."
            ),
        )
    )
    db.flush()
    registrar_audit(
        db,
        entity_type="contrato_assinatura",
        entity_id=env.id,
        action="create",
        atendente_id=ator.id,
        payload={
            "contrato_id": row.id,
            "submission_id": env.submission_id,
            "provedor": PROVEDOR_DOCUSEAL,
            "partes": [{"papel": p.papel, "email": p.email} for p in partes],
        },
    )
    db.refresh(env)
    _ = env.partes  # ensure loaded
    return env


def cancelar_envelope(db: Session, row: Contrato, ator: Atendente) -> ContratoAssinatura:
    ativo = envelope_ativo(db, row.id)
    if ativo is None:
        raise HTTPException(status_code=404, detail="Não há envelope de assinatura ativo.")
    _cancelar_ativo(db, ativo, motivo="cancelamento manual")
    registrar_audit(
        db,
        entity_type="contrato_assinatura",
        entity_id=ativo.id,
        action="update",
        atendente_id=ator.id,
        payload={"status": STATUS_CANCELADO, "contrato_id": row.id},
    )
    return ativo


def registrar_anexo_externo(
    db: Session,
    row: Contrato,
    *,
    pdf_path: str,
    pdf_sha256: str,
    ator: Atendente,
) -> ContratoAssinatura:
    """Fluxo B — PDF anexado manualmente vira envelope «externo» assinado."""
    ativo = envelope_ativo(db, row.id)
    if ativo is not None:
        _cancelar_ativo(db, ativo, motivo="anexo externo")
    agora = _agora()
    env = ContratoAssinatura(
        contrato_id=row.id,
        provedor=PROVEDOR_EXTERNO,
        status=STATUS_ASSINADO,
        assinado_em=agora,
        pdf_assinado_path=pdf_path,
        pdf_sha256=pdf_sha256,
        criado_por_id=ator.id,
    )
    db.add(env)
    db.flush()
    registrar_audit(
        db,
        entity_type="contrato_assinatura",
        entity_id=env.id,
        action="create",
        atendente_id=ator.id,
        payload={"contrato_id": row.id, "provedor": PROVEDOR_EXTERNO},
    )
    return env


def _marcar_expirados(db: Session, contrato_id: int | None = None) -> int:
    agora = _agora()
    q = db.query(ContratoAssinatura).filter(
        ContratoAssinatura.status.in_(tuple(STATUS_ATIVOS)),
        ContratoAssinatura.expira_em.isnot(None),
        ContratoAssinatura.expira_em < agora,
    )
    if contrato_id is not None:
        q = q.filter(ContratoAssinatura.contrato_id == contrato_id)
    n = 0
    for row in q.options(joinedload(ContratoAssinatura.partes)).all():
        row.status = STATUS_EXPIRADO
        row.ultimo_erro = "Envelope expirou sem assinatura."
        row.updated_at = agora
        for p in row.partes or []:
            if p.status != STATUS_ASSINADO:
                p.status = STATUS_EXPIRADO
                p.updated_at = agora
        n += 1
    if n:
        db.flush()
    return n


def obter_assinatura(db: Session, assinatura_id: int) -> ContratoAssinatura:
    row = (
        db.query(ContratoAssinatura)
        .options(joinedload(ContratoAssinatura.partes))
        .filter(ContratoAssinatura.id == assinatura_id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Assinatura não encontrada.")
    return row


def bytes_evidencia(row: ContratoAssinatura, tipo: str) -> tuple[bytes, str, str]:
    """Devolve (bytes, nome, media_type)."""
    if tipo == "pdf":
        path = storage.caminho_absoluto(row.pdf_assinado_path)
        nome = f"contrato-{row.contrato_id}-assinado.pdf"
        media = "application/pdf"
    elif tipo == "audit":
        path = storage.caminho_absoluto(row.audit_log_path)
        nome = f"contrato-{row.contrato_id}-auditoria.pdf"
        media = "application/pdf"
    elif tipo == "selfie":
        path = storage.caminho_absoluto(row.selfie_path)
        nome = f"contrato-{row.contrato_id}-selfie.jpg"
        media = "image/jpeg"
    else:
        raise HTTPException(status_code=400, detail="Tipo de evidência inválido.")
    if path is None:
        raise HTTPException(status_code=404, detail="Evidência não encontrada.")
    return path.read_bytes(), nome, media


def limpar_evidencias_contrato(db: Session, contrato_id: int, *, ator_id: int | None = None) -> int:
    n = storage.apagar_evidencias(contrato_id)
    for row in (
        db.query(ContratoAssinatura).filter(ContratoAssinatura.contrato_id == contrato_id).all()
    ):
        row.pdf_assinado_path = None
        row.audit_log_path = None
        row.selfie_path = None
        row.pdf_sha256 = None
        row.audit_sha256 = None
    db.flush()
    registrar_audit(
        db,
        entity_type="contrato",
        entity_id=contrato_id,
        action="delete",
        atendente_id=ator_id,
        payload={"limpeza_evidencias_assinatura": n},
    )
    return n


def _todas_partes_assinaram(env: ContratoAssinatura) -> bool:
    partes = list(env.partes or [])
    if not partes:
        # Envelope legado sem partes: trata como único signatário no próprio env.
        return env.status == STATUS_ASSINADO
    return all(p.status == STATUS_ASSINADO for p in partes)


def _encontrar_parte(
    env: ContratoAssinatura,
    *,
    slug: str | None,
    email: str | None,
    role: str | None,
) -> ContratoAssinaturaParte | None:
    partes = list(env.partes or [])
    if slug:
        for p in partes:
            if p.submitter_slug == slug:
                return p
    if email:
        em = email.strip().lower()
        for p in partes:
            if p.email.lower() == em:
                return p
    if role:
        for p in partes:
            if p.role_docuseal == role or p.papel == role.lower():
                return p
    return None


def _finalizar_envelope_completo(
    db: Session,
    env: ContratoAssinatura,
    data: dict[str, Any],
) -> ContratoAssinatura:
    client = docuseal.get_client()
    pdf_url = data.get("combined_document_url") or data.get("documents_url")
    if not pdf_url and isinstance(data.get("documents"), list) and data.get("documents"):
        first_doc = data["documents"][0]
        if isinstance(first_doc, dict):
            pdf_url = first_doc.get("url")
    audit_url = data.get("audit_log_url") or data.get("audit_log")
    if not pdf_url and isinstance(data.get("submission"), dict):
        pdf_url = data["submission"].get("combined_document_url")
        audit_url = audit_url or data["submission"].get("audit_log_url")

    if not pdf_url:
        env.status = STATUS_ERRO
        env.ultimo_erro = "Webhook de conclusão sem URL do PDF assinado."
        env.updated_at = _agora()
        db.flush()
        raise HTTPException(status_code=422, detail=env.ultimo_erro)

    try:
        pdf_bytes = client.baixar_url(str(pdf_url))
        pdf_path, pdf_hash = storage.gravar_evidencia(
            env.contrato_id, conteudo=pdf_bytes, nome_logico="pdf-assinado", extensao=".pdf"
        )
        audit_path = audit_hash = None
        if audit_url:
            audit_bytes = client.baixar_url(str(audit_url))
            audit_path, audit_hash = storage.gravar_evidencia(
                env.contrato_id, conteudo=audit_bytes, nome_logico="audit-log", extensao=".pdf"
            )
        selfie_url = None
        values = data.get("values") if isinstance(data.get("values"), dict) else {}
        for key, val in values.items():
            if "selfie" in str(key).lower() or "image" in str(key).lower():
                if isinstance(val, str) and val.startswith("http"):
                    selfie_url = val
                    break
        selfie_path = None
        if selfie_url:
            selfie_bytes = client.baixar_url(selfie_url)
            selfie_path, _ = storage.gravar_evidencia(
                env.contrato_id, conteudo=selfie_bytes, nome_logico="selfie", extensao=".jpg"
            )
    except (docuseal.DocusealError, ValueError) as exc:
        msg = getattr(exc, "mensagem", None) or str(exc)
        env.status = STATUS_ERRO
        env.ultimo_erro = msg
        env.updated_at = _agora()
        db.flush()
        raise HTTPException(status_code=502, detail=msg) from exc

    agora = _agora()
    env.status = STATUS_ASSINADO
    env.assinado_em = agora
    env.pdf_assinado_path = pdf_path
    env.pdf_sha256 = pdf_hash
    env.audit_log_path = audit_path
    env.audit_sha256 = audit_hash
    env.selfie_path = selfie_path
    env.ultimo_erro = None
    env.updated_at = agora
    for p in env.partes or []:
        if p.status != STATUS_ASSINADO:
            p.status = STATUS_ASSINADO
            p.assinado_em = p.assinado_em or agora

    from app.services.ticket_anexo_storage import gravar_bytes_em_disco

    key_legado = gravar_bytes_em_disco(
        pdf_bytes,
        mimetype="application/pdf",
        nome_original=f"contrato-{env.contrato_id}-docuseal.pdf",
    )
    contrato = contrato_svc.obter_contrato(db, env.contrato_id)
    contrato.pdf_assinado_storage_key = key_legado
    contrato.pdf_assinado_nome_original = f"contrato-{contrato.id}-docuseal.pdf"
    contrato.referencia_externa = f"docuseal:{env.submission_id}"

    ator = None
    if env.criado_por_id:
        ator = db.get(Atendente, env.criado_por_id)
    if ator is None:
        ator = db.get(Atendente, contrato.gerado_por_id)
    if ator is None:
        raise HTTPException(status_code=500, detail="Sem atendente para concluir a assinatura.")

    if contrato.status != CONTRATO_ASSINADO:
        contrato_svc.marcar_assinado(
            db,
            contrato,
            ContratoMarcarAssinadoIn(abrir_ticket_implantacao=True),
            ator,
        )
        linha = contrato.linha or contrato_svc.obter_linha(db, contrato.negociacao_linha_cnpj_id)
        db.add(
            CrmNegociacaoAtividade(
                negociacao_id=linha.negociacao_id,
                autor_id=ator.id,
                tipo=ATIVIDADE_DOCUMENTO,
                texto=f"Contrato #{contrato.id} assinado eletronicamente (DocuSeal multiparte).",
            )
        )

    registrar_audit(
        db,
        entity_type="contrato_assinatura",
        entity_id=env.id,
        action="update",
        atendente_id=ator.id,
        payload={
            "status": STATUS_ASSINADO,
            "contrato_id": contrato.id,
            "pdf_sha256": pdf_hash,
            "provedor": PROVEDOR_DOCUSEAL,
        },
    )
    db.flush()
    return env


def processar_webhook_docuseal(db: Session, payload: dict[str, Any]) -> ContratoAssinatura | None:
    """Processa eventos por parte e conclusão do envelope (#1429)."""
    event = str(payload.get("event_type") or payload.get("event") or "").strip().lower()
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    submission_id = str(
        data.get("submission_id")
        or data.get("id")
        or (data.get("submission") or {}).get("id")
        or ""
    ).strip()
    if not submission_id:
        submitters = data.get("submitters") if isinstance(data.get("submitters"), list) else []
        if submitters and isinstance(submitters[0], dict):
            submission_id = str(submitters[0].get("submission_id") or "").strip()
    if not submission_id:
        raise HTTPException(status_code=400, detail="Webhook sem submission_id.")

    env = (
        db.query(ContratoAssinatura)
        .options(joinedload(ContratoAssinatura.partes))
        .filter(
            ContratoAssinatura.provedor == PROVEDOR_DOCUSEAL,
            ContratoAssinatura.submission_id == submission_id,
        )
        .order_by(ContratoAssinatura.id.desc())
        .first()
    )
    if env is None:
        raise HTTPException(status_code=404, detail="Envelope não encontrado para este submission_id.")

    if env.status == STATUS_ASSINADO:
        return env

    slug = str(data.get("slug") or data.get("submitter_slug") or "").strip() or None
    email = str(data.get("email") or "").strip() or None
    role = str(data.get("role") or "").strip() or None
    parte = _encontrar_parte(env, slug=slug, email=email, role=role)

    if "declin" in event or "refus" in event or data.get("status") in {"declined", "rejected"}:
        agora = _agora()
        if parte is not None:
            parte.status = STATUS_RECUSADO
            parte.ultimo_erro = "Signatário recusou a assinatura."
            parte.updated_at = agora
        env.status = STATUS_RECUSADO
        quem = parte.nome if parte is not None else "Uma das partes"
        env.ultimo_erro = f"{quem} recusou a assinatura."
        env.updated_at = agora
        db.flush()
        return env

    if "view" in event or data.get("status") == "opened":
        agora = _agora()
        if parte is not None and parte.status in STATUS_ATIVOS:
            parte.status = STATUS_VISUALIZADO
            if parte.visualizado_em is None:
                parte.visualizado_em = agora
            parte.updated_at = agora
        if env.status in STATUS_ATIVOS and env.visualizado_em is None:
            env.status = STATUS_VISUALIZADO
            env.visualizado_em = agora
            env.updated_at = agora
        db.flush()
        return env

    form_done = (
        "form.completed" in event
        or "submitter.completed" in event
        or (data.get("status") in {"completed", "complete"} and slug)
    )
    submission_done = (
        "submission.completed" in event
        or (
            "complete" in event
            and not form_done
            and bool(data.get("combined_document_url") or data.get("documents_url"))
        )
        or bool(data.get("completed_at") and not slug)
    )

    if form_done and parte is not None:
        agora = _agora()
        parte.status = STATUS_ASSINADO
        parte.assinado_em = agora
        parte.ultimo_erro = None
        parte.updated_at = agora
        if not _todas_partes_assinaram(env):
            env.status = STATUS_PARCIAL
            env.updated_at = agora
            db.flush()
            return env
        # Todas assinaram neste evento parcial — tenta finalizar se houver PDF.
        if data.get("combined_document_url") or data.get("documents_url"):
            return _finalizar_envelope_completo(db, env, data)
        env.status = STATUS_PARCIAL
        env.updated_at = agora
        db.flush()
        return env

    if submission_done or (_todas_partes_assinaram(env) and ("complete" in event)):
        for p in env.partes or []:
            if p.status != STATUS_ASSINADO:
                p.status = STATUS_ASSINADO
                p.assinado_em = p.assinado_em or _agora()
        return _finalizar_envelope_completo(db, env, data)

    completed = "complete" in event or data.get("status") in {"completed", "complete"}
    if completed and not (env.partes or []):
        # Legado sem partes.
        return _finalizar_envelope_completo(db, env, data)

    return env


def _rotulo_papel(papel: str) -> str:
    if papel == PAPEL_CONTRATANTE:
        return "contratante"
    if papel == PAPEL_CONTRATADA:
        return "contratada"
    if papel == PAPEL_TESTEMUNHA:
        return "testemunha"
    return papel


def obter_parte(db: Session, contrato_id: int, parte_id: int) -> ContratoAssinaturaParte:
    parte = (
        db.query(ContratoAssinaturaParte)
        .join(ContratoAssinatura, ContratoAssinaturaParte.assinatura_id == ContratoAssinatura.id)
        .filter(
            ContratoAssinaturaParte.id == parte_id,
            ContratoAssinatura.contrato_id == contrato_id,
        )
        .first()
    )
    if parte is None:
        raise HTTPException(status_code=404, detail="Parte da assinatura não encontrada.")
    return parte


def enviar_convite_email_parte(
    db: Session,
    row: Contrato,
    parte: ContratoAssinaturaParte,
    ator: Atendente,
) -> None:
    """Envia o link de assinatura por e-mail (DeskRudder controla o convite)."""
    env = obter_assinatura(db, parte.assinatura_id)
    if env.status not in STATUS_ATIVOS:
        raise HTTPException(
            status_code=400,
            detail="Só é possível enviar convite de um envelope ativo.",
        )
    link = (parte.link_assinatura or "").strip()
    if not link:
        raise HTTPException(status_code=400, detail="Esta parte ainda não tem link de assinatura.")
    email = (parte.email or "").strip()
    if not email:
        raise HTTPException(status_code=400, detail="Esta parte não tem e-mail cadastrado.")

    prazo = ""
    if env.expira_em is not None:
        prazo = f"\nPrazo para assinar: {env.expira_em.astimezone(timezone.utc).strftime('%d/%m/%Y %H:%M')} UTC."

    papel = _rotulo_papel(parte.papel)
    subject = f"Assinatura do contrato #{row.id} — {papel}"
    body = (
        f"Olá, {parte.nome},\n\n"
        f"Você foi convidado(a) a assinar o contrato #{row.id} no DeskRudder "
        f"como {papel}.\n\n"
        f"Abra o link abaixo, confira seus dados (incluindo o CPF) e conclua a assinatura:\n"
        f"{link}\n"
        f"{prazo}\n\n"
        "Se você não esperava este e-mail, ignore esta mensagem.\n"
    )
    try:
        enviar_mensagem_texto_sistema(db, to_addr=email, subject=subject, body=body)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    registrar_audit(
        db,
        entity_type="contrato_assinatura",
        entity_id=env.id,
        action="update",
        atendente_id=ator.id,
        payload={
            "convite_email": True,
            "parte_id": parte.id,
            "papel": parte.papel,
            "email": email,
            "contrato_id": row.id,
        },
    )


def sincronizar_expiracao(db: Session, contrato_id: int) -> None:
    _marcar_expirados(db, contrato_id)
