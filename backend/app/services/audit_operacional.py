"""Hooks de auditoria para tickets, chats e exportações sensíveis."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.audit import registrar_audit


def audit_ticket_assign(
    db: Session,
    *,
    ticket_id: int,
    atendente_id: int | None,
    de_atendente_id: int | None,
    para_atendente_id: int | None,
    protocolo: str | None = None,
) -> None:
    registrar_audit(
        db,
        "ticket",
        ticket_id,
        "assign",
        atendente_id,
        payload={
            "protocolo": protocolo,
            "de_atendente_id": de_atendente_id,
            "para_atendente_id": para_atendente_id,
        },
    )


def audit_ticket_transfer(
    db: Session,
    *,
    ticket_id: int,
    atendente_id: int | None,
    de_setor_id: int,
    para_setor_id: int,
    protocolo: str | None = None,
) -> None:
    registrar_audit(
        db,
        "ticket",
        ticket_id,
        "transfer",
        atendente_id,
        payload={
            "protocolo": protocolo,
            "de_setor_id": de_setor_id,
            "para_setor_id": para_setor_id,
        },
    )


def audit_ticket_status_change(
    db: Session,
    *,
    ticket_id: int,
    atendente_id: int | None,
    de_status_id: int,
    para_status_id: int,
    protocolo: str | None = None,
) -> None:
    registrar_audit(
        db,
        "ticket",
        ticket_id,
        "status_change",
        atendente_id,
        payload={
            "protocolo": protocolo,
            "de_status_id": de_status_id,
            "para_status_id": para_status_id,
        },
    )


def audit_ticket_close(
    db: Session,
    *,
    ticket_id: int,
    atendente_id: int | None,
    status_id: int,
    protocolo: str | None = None,
) -> None:
    registrar_audit(
        db,
        "ticket",
        ticket_id,
        "close",
        atendente_id,
        payload={"protocolo": protocolo, "status_id": status_id},
    )


def audit_ticket_reopen(
    db: Session,
    *,
    ticket_id: int,
    atendente_id: int | None,
    status_id: int,
    protocolo: str | None = None,
) -> None:
    registrar_audit(
        db,
        "ticket",
        ticket_id,
        "reopen",
        atendente_id,
        payload={"protocolo": protocolo, "status_id": status_id},
    )


def audit_ticket_send_email(
    db: Session,
    *,
    ticket_id: int,
    mensagem_id: int,
    atendente_id: int | None,
    origem: str,
) -> None:
    registrar_audit(
        db,
        "ticket_mensagem",
        mensagem_id,
        "send_email",
        atendente_id,
        payload={"ticket_id": ticket_id, "origem": origem},
    )


def audit_view_credential(
    db: Session,
    *,
    pdv_id: int,
    empresa_id: int,
    atendente_id: int | None,
    campo: str = "acesso_remoto_senha",
) -> None:
    registrar_audit(
        db,
        "empresa_pdv",
        pdv_id,
        "view_credential",
        atendente_id,
        payload={"empresa_id": empresa_id, "campo": campo},
    )


def audit_whatsapp_chat(
    db: Session,
    *,
    chat_id: int,
    action: str,
    atendente_id: int | None,
    payload: dict | None = None,
) -> None:
    registrar_audit(db, "whatsapp_chat", chat_id, action, atendente_id, payload=payload)


def audit_export_relatorio(
    db: Session,
    *,
    tipo: str,
    atendente_id: int | None,
    filtros: dict | None = None,
) -> None:
    registrar_audit(
        db,
        "export_relatorio",
        0,
        "export",
        atendente_id,
        payload={"tipo": tipo, "filtros": filtros or {}},
    )
