"""Status de entrega/leitura de mensagens (WhatsApp e chat interno)."""

from __future__ import annotations

STATUS_PENDENTE = "pendente"
STATUS_ENVIADA = "enviada"
STATUS_ENTREGUE = "entregue"
STATUS_LIDA = "lida"
STATUS_ERRO = "erro"

STATUS_ORDEM: dict[str | None, int] = {
    None: 0,
    STATUS_ERRO: 1,
    STATUS_PENDENTE: 1,
    STATUS_ENVIADA: 2,
    STATUS_ENTREGUE: 3,
    STATUS_LIDA: 4,
}


def status_deve_atualizar(atual: str | None, novo: str) -> bool:
    return STATUS_ORDEM.get(novo, 0) > STATUS_ORDEM.get(atual, 0)


def ack_evolution_para_status(ack: int | str | None) -> str | None:
    """Mapeia ACK Baileys/Evolution para status_entrega."""
    if ack is None:
        return None
    if isinstance(ack, str):
        raw = ack.strip().upper()
        if raw in ("ERROR", "FAILED"):
            return STATUS_ERRO
        if raw in ("PENDING", "SERVER_ACK", "ACK"):
            return STATUS_ENVIADA
        if raw in ("DELIVERY_ACK", "DELIVERED", "RECEIVED"):
            return STATUS_ENTREGUE
        if raw in ("READ", "READ_ACK", "PLAYED"):
            return STATUS_LIDA
        try:
            ack = int(raw)
        except ValueError:
            return None
    try:
        n = int(ack)
    except (TypeError, ValueError):
        return None
    if n <= 0:
        return STATUS_ERRO
    if n == 1:
        return STATUS_ENVIADA
    if n == 2:
        return STATUS_ENTREGUE
    if n >= 3:
        return STATUS_LIDA
    return None


def status_inicial_outbound_whatsapp(*, wa_message_id: str | None, enviado: bool = True) -> str | None:
    if not enviado:
        return STATUS_ERRO
    if wa_message_id:
        return STATUS_ENVIADA
    return STATUS_PENDENTE
