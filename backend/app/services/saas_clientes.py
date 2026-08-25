"""Regras de negócio do painel SaaS / licenças — #521–#522."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.cliente_saas import STATUS_CLIENTE_SAAS, ClienteSaaS
from app.schemas.saas import ClienteSaaSCreate, ClienteSaaSRegistrarInstancia, ClienteSaaSUpdate


class SaasErro(Exception):
    def __init__(self, detail: str, status_code: int = 400):
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


def obter(db: Session, cliente_id: int) -> ClienteSaaS:
    row = db.query(ClienteSaaS).filter(ClienteSaaS.id == cliente_id).first()
    if not row:
        raise SaasErro("Cliente SaaS não encontrado", 404)
    return row


def _garantir_slug_unico(db: Session, slug: str, excluir_id: int | None = None) -> None:
    q = db.query(ClienteSaaS).filter(ClienteSaaS.slug == slug)
    if excluir_id is not None:
        q = q.filter(ClienteSaaS.id != excluir_id)
    if q.first():
        raise SaasErro("Já existe um cliente com este slug", 409)


def _url_do_slug(slug: str) -> str | None:
    from app.services.saas_provisionamento import _montar_instancia_url

    return _montar_instancia_url(slug)


def criar(db: Session, data: ClienteSaaSCreate) -> ClienteSaaS:
    if data.status not in STATUS_CLIENTE_SAAS:
        raise SaasErro("Status inválido")
    _garantir_slug_unico(db, data.slug)
    payload = data.model_dump()
    lead_id = payload.pop("lead_comercial_id", None)
    modulo_ids = payload.pop("modulo_ids", None)
    usuarios_contratados = payload.pop("usuarios_contratados", None)
    # URL pública é sempre derivada do slug (+ domínio base); não é campo livre.
    payload["instancia_url"] = _url_do_slug(data.slug) or payload.get("instancia_url")

    from app.services.saas_catalogo import aplicar_plano_em_cliente

    plano_id = payload.pop("plano_id", None)
    # Texto livre `plano` só como fallback legado; preferir plano_id.
    if plano_id is not None:
        pid, nome, codigos, max_p, max_u = aplicar_plano_em_cliente(
            db, plano_id=plano_id, modulo_ids=modulo_ids
        )
        payload["plano_id"] = pid
        payload["plano"] = nome
        payload["modulos_snapshot"] = codigos
        payload["max_postos"] = None
        if usuarios_contratados is not None:
            payload["max_usuarios"] = usuarios_contratados
        elif max_u is not None:
            payload["max_usuarios"] = max_u
    elif payload.get("plano"):
        # Trial / legado: tentar resolver por código ou deixar só o rótulo.
        from app.services.saas_catalogo import obter_plano_por_codigo

        p = obter_plano_por_codigo(db, str(payload["plano"]))
        if p is not None:
            payload["plano_id"] = p.id
            payload["plano"] = p.nome

    row = ClienteSaaS(**payload)
    db.add(row)
    db.flush()
    if getattr(row, "plano_id", None) and not payload.get("modulos_snapshot"):
        from app.services.saas_catalogo import sincronizar_snapshot_licenca

        sincronizar_snapshot_licenca(db, row)
    if lead_id:
        from app.services.saas_lead_convert import ligar_lead_ao_criar

        ligar_lead_ao_criar(db, row, lead_id)
    return row


def atualizar(db: Session, cliente_id: int, data: ClienteSaaSUpdate) -> ClienteSaaS:
    row = obter(db, cliente_id)
    payload = data.model_dump(exclude_unset=True)
    if "status" in payload and payload["status"] not in STATUS_CLIENTE_SAAS:
        raise SaasErro("Status inválido")
    if "slug" in payload:
        _garantir_slug_unico(db, payload["slug"], excluir_id=cliente_id)
    # instancia_url deixa de ser editável à mão — sempre acompanha o slug.
    payload.pop("instancia_url", None)
    modulo_ids = payload.pop("modulo_ids", None)
    usuarios_contratados = payload.pop("usuarios_contratados", None)

    if "plano_id" in payload or modulo_ids is not None:
        from app.services.saas_catalogo import aplicar_plano_em_cliente

        plano_ref = payload["plano_id"] if "plano_id" in payload else getattr(row, "plano_id", None)
        pid, nome, codigos, _max_p, max_u = aplicar_plano_em_cliente(
            db,
            plano_id=plano_ref,
            plano_actual_id=getattr(row, "plano_id", None),
            modulo_ids=modulo_ids,
        )
        payload["plano_id"] = pid
        payload["plano"] = nome
        payload["modulos_snapshot"] = codigos
        payload["max_postos"] = None
        if usuarios_contratados is not None:
            payload["max_usuarios"] = usuarios_contratados
        elif "plano_id" in data.model_dump(exclude_unset=True) and max_u is not None:
            # Troca de plano sem informar usuários — mantém o contratado actual se existir
            if getattr(row, "max_usuarios", None) is None:
                payload["max_usuarios"] = max_u
    elif "plano" in payload and payload.get("plano"):
        from app.services.saas_catalogo import obter_plano_por_codigo

        p = obter_plano_por_codigo(db, str(payload["plano"]))
        if p is not None:
            payload["plano_id"] = p.id
            payload["plano"] = p.nome

    if usuarios_contratados is not None and "max_usuarios" not in payload:
        payload["max_usuarios"] = usuarios_contratados

    for k, v in payload.items():
        setattr(row, k, v)
    auto = _url_do_slug(row.slug)
    if auto:
        row.instancia_url = auto
    db.flush()
    return row


def suspender(db: Session, cliente_id: int) -> ClienteSaaS:
    from app.services.saas_stack import aplicar_suspensao_stack

    row = obter(db, cliente_id)
    if row.status == "suspenso":
        raise SaasErro("Cliente já está suspenso")
    if row.status == "churn":
        raise SaasErro("Cliente em churn — edite o status se necessário")
    row.status = "suspenso"
    db.flush()
    return aplicar_suspensao_stack(db, row)


def reativar(db: Session, cliente_id: int) -> ClienteSaaS:
    from app.services.saas_stack import aplicar_reativacao_stack

    row = obter(db, cliente_id)
    if row.status == "churn":
        raise SaasErro("Cliente em churn não pode ser reativado por este atalho; edite o status")
    if getattr(row, "aprovacao_status", None) == "rejeitado":
        raise SaasErro("Licença rejeitada não pode ser reativada")
    if row.status == "ativo":
        raise SaasErro("Cliente já está ativo")
    row.status = "ativo"
    db.flush()
    return aplicar_reativacao_stack(db, row)


def confirmar_stack(db: Session, cliente_id: int) -> ClienteSaaS:
    from app.services.saas_stack import confirmar_stack_ops

    return confirmar_stack_ops(db, cliente_id)


def registrar_instancia(db: Session, cliente_id: int, data: ClienteSaaSRegistrarInstancia) -> ClienteSaaS:
    """Sincroniza a URL pública a partir do slug (body opcional é ignorado se o domínio base existir)."""
    row = obter(db, cliente_id)
    auto = _url_do_slug(row.slug)
    row.instancia_url = auto or data.instancia_url
    db.flush()
    return row


def solicitar_provisionamento(db: Session, cliente_id: int) -> ClienteSaaS:
    """Enfileira provisionamento (DR-04)."""
    from app.services.saas_provisionamento import enfileirar_provisionamento

    return enfileirar_provisionamento(db, cliente_id)


def confirmar_provisionamento(
    db: Session,
    cliente_id: int,
    *,
    instancia_url: str | None = None,
) -> ClienteSaaS:
    """Confirma provisionamento ops-assisted (DR-04)."""
    from app.services.saas_provisionamento import confirmar_provisionamento as _confirmar

    return _confirmar(db, cliente_id, instancia_url=instancia_url)


def reenviar_entrega(db: Session, cliente_id: int) -> ClienteSaaS:
    """Reenvia e-mail de entrega ao contacto (pós-health)."""
    from app.services.saas_notify import notificar_contacto_entrega

    row = obter(db, cliente_id)
    if row.provisionamento_status != "sucesso":
        raise SaasErro("Só é possível notificar entrega após provisionamento com sucesso")
    if not (row.contato_email or "").strip():
        raise SaasErro("Licença sem e-mail de contacto")
    ok = notificar_contacto_entrega(db, row, forcar=True)
    if not ok:
        raise SaasErro("Não foi possível enviar o e-mail de entrega (verifique Resend / SMTP)")
    return row


def serializar_cliente(row: ClienteSaaS) -> dict:
    from sqlalchemy.orm import object_session

    from app.services import saas_catalogo
    from app.services.saas_provisionamento import montar_comandos_ops
    from app.services.saas_renovacoes import dias_para_renovacao
    from app.services.saas_stack import montar_comandos_stack

    plano_modulos: list[dict] = []
    plano_id = getattr(row, "plano_id", None)
    sess = object_session(row)
    usuarios_inclusos = 3
    preco_usuario_extra = 10.0
    if plano_id and sess is not None:
        try:
            plano = saas_catalogo.obter_plano(sess, plano_id)
            ser = saas_catalogo.serializar_plano(plano)
            plano_modulos = ser.get("modulos") or []
            usuarios_inclusos = int(ser.get("usuarios_inclusos") or 3)
            preco_usuario_extra = float(ser.get("preco_usuario_extra") or 10)
        except SaasErro:
            plano_modulos = []

    preco_modulos = 0.0
    snapshot = list(getattr(row, "modulos_snapshot", None) or [])
    modulos_contratados: list[dict] = []
    if sess is not None and snapshot:
        try:
            mods = saas_catalogo.resolver_modulos_por_codigos(sess, snapshot)
            preco_modulos = saas_catalogo.soma_preco_modulos(mods)
            modulos_contratados = [
                {
                    "id": m.id,
                    "codigo": m.codigo,
                    "nome": m.nome,
                    "ativo": bool(m.ativo),
                    "preco_mensal": float(m.preco_mensal) if m.preco_mensal is not None else None,
                }
                for m in mods
            ]
        except SaasErro:
            preco_modulos = 0.0
    elif plano_modulos:
        preco_modulos = round(
            sum(float(m.get("preco_mensal") or 0) for m in plano_modulos),
            2,
        )
        modulos_contratados = list(plano_modulos)

    usuarios_contratados = getattr(row, "max_usuarios", None)
    preco_users = saas_catalogo.preco_extra_usuarios(
        usuarios_inclusos=usuarios_inclusos,
        preco_usuario_extra=preco_usuario_extra,
        usuarios_contratados=usuarios_contratados,
    )
    preco_estimado = round(preco_modulos + preco_users, 2)
    negociado_raw = getattr(row, "preco_mensal_negociado", None)
    negociado = float(negociado_raw) if negociado_raw is not None else None
    efetivo = negociado if negociado is not None else preco_estimado

    return {
        "id": row.id,
        "nome": row.nome,
        "slug": row.slug,
        "status": row.status,
        "plano": row.plano,
        "plano_id": plano_id,
        "plano_modulos": plano_modulos,
        "modulos_contratados": modulos_contratados,
        "modulos_snapshot": snapshot,
        "max_postos": getattr(row, "max_postos", None),
        "max_usuarios": usuarios_contratados,
        "usuarios_inclusos": usuarios_inclusos,
        "preco_usuario_extra": preco_usuario_extra,
        "preco_modulos": preco_modulos,
        "preco_usuarios_extra": preco_users,
        "preco_mensal_estimado": preco_estimado,
        "preco_mensal_negociado": negociado,
        "preco_mensal_efetivo": efetivo,
        "data_inicio": row.data_inicio,
        "data_renovacao": row.data_renovacao,
        "instancia_url": row.instancia_url,
        "contato_email": row.contato_email,
        "contato_nome": row.contato_nome,
        "api_port": row.api_port,
        "notas": row.notas,
        "provisionamento_solicitado": bool(row.provisionamento_solicitado),
        "provisionamento_status": row.provisionamento_status,
        "provisionamento_mensagem": row.provisionamento_mensagem,
        "provisionamento_atualizado_em": row.provisionamento_atualizado_em,
        "aprovacao_status": getattr(row, "aprovacao_status", None) or "aprovado",
        "aprovacao_notas": getattr(row, "aprovacao_notas", None),
        "aprovacao_em": getattr(row, "aprovacao_em", None),
        "stack_status": getattr(row, "stack_status", None),
        "stack_ops_pendente": getattr(row, "stack_ops_pendente", None),
        "stack_ops_mensagem": getattr(row, "stack_ops_mensagem", None),
        "stack_ops_atualizado_em": getattr(row, "stack_ops_atualizado_em", None),
        "lead_comercial_id": getattr(row, "lead_comercial_id", None),
        "entrega_notificada_em": getattr(row, "entrega_notificada_em", None),
        "comandos_ops": montar_comandos_ops(row),
        "comandos_stack": montar_comandos_stack(row),
        "dias_para_renovacao": dias_para_renovacao(row.data_renovacao),
        "ingest_token_configurado": bool((getattr(row, "ingest_token_hash", None) or "").strip()),
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }
