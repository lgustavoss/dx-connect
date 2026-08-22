"""Microcopy pública de status das solicitações (#807)."""

from __future__ import annotations

STATUS_LABELS: dict[str, str] = {
    "aberta": "Recebida",
    "em_analise": "Em análise",
    "planejada": "Planejada",
    "em_desenvolvimento": "Em desenvolvimento",
    "concluida": "Concluída",
    "nao_sera_desenvolvida": "Não será desenvolvida",
}

STATUS_MENSAGENS: dict[str, str] = {
    "aberta": "Recebemos o seu pedido. A equipa vai analisar em breve.",
    "em_analise": "Estamos a analisar o seu pedido com atenção.",
    "planejada": "O seu pedido foi incluído no planeamento de melhorias.",
    "em_desenvolvimento": "Já estamos a trabalhar nesta melhoria.",
    "concluida": "Esta melhoria ficou disponível. Obrigado pelo contributo!",
    "nao_sera_desenvolvida": (
        "Neste momento não vamos avançar com este pedido. "
        "Apreciamos o feedback — se fizer sentido no futuro, voltamos a avaliar."
    ),
}

STATUS_FINAIS = frozenset({"concluida", "nao_sera_desenvolvida"})

STATUS_VALIDOS = frozenset(STATUS_LABELS.keys())
TIPOS_VALIDOS = frozenset({"sugestao", "problema"})


def mensagem_publica_status(status: str, *, motivo: str | None = None) -> str:
    base = STATUS_MENSAGENS.get(status, "O estado do seu pedido foi atualizado.")
    if status == "nao_sera_desenvolvida" and (motivo or "").strip():
        return f"{base}\n\nMotivo: {motivo.strip()}"
    return base


def rotulo_status(status: str) -> str:
    return STATUS_LABELS.get(status, status.replace("_", " "))
