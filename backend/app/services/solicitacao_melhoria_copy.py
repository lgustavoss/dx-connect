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
    "aberta": "Recebemos o seu pedido. A equipe vai analisar em breve.",
    "em_analise": "Estamos analisando o seu pedido com atenção.",
    "planejada": "O seu pedido foi incluído no planejamento de melhorias.",
    "em_desenvolvimento": "Já estamos trabalhando nesta melhoria.",
    "concluida": "Esta melhoria ficou disponível. Obrigado pela contribuição!",
    "nao_sera_desenvolvida": (
        "Neste momento não vamos seguir com este pedido. "
        "Agradecemos o feedback — se fizer sentido no futuro, voltamos a avaliar."
    ),
}

STATUS_FINAIS = frozenset({"concluida", "nao_sera_desenvolvida"})

STATUS_VALIDOS = frozenset(STATUS_LABELS.keys())
TIPOS_VALIDOS = frozenset({"sugestao", "problema"})

# Transições permitidas na triagem (#953). Sync SaaS→instância aplica o status
# já validado no control-plane (pode "saltar" se o pull atrasar).
STATUS_TRANSICOES: dict[str, frozenset[str]] = {
    "aberta": frozenset({"em_analise", "nao_sera_desenvolvida"}),
    "em_analise": frozenset({"planejada", "nao_sera_desenvolvida"}),
    "planejada": frozenset({"em_desenvolvimento", "nao_sera_desenvolvida"}),
    "em_desenvolvimento": frozenset({"concluida", "nao_sera_desenvolvida"}),
    "concluida": frozenset(),
    "nao_sera_desenvolvida": frozenset(),
}

MSG_TRANSICAO_INVALIDA = "Transição de status não permitida"
MSG_GITHUB_OBRIGATORIO = (
    "Para marcar como em desenvolvimento, vincule ou crie uma issue no GitHub "
    "(ação Implementar)."
)

# Fases para filtro rápido no painel ops (agrupa status)
FASES_STATUS: dict[str, frozenset[str]] = {
    "aguardando": frozenset({"aberta", "em_analise", "planejada"}),
    "desenvolvimento": frozenset({"em_desenvolvimento"}),
    "finalizadas": frozenset(STATUS_FINAIS),
}
FASES_VALIDAS = frozenset(FASES_STATUS.keys())


def status_da_fase(fase: str) -> frozenset[str] | None:
    key = (fase or "").strip().lower()
    return FASES_STATUS.get(key)


def proximos_status(de: str) -> frozenset[str]:
    return STATUS_TRANSICOES.get(de, frozenset())


def validar_transicao_status(
    de: str,
    para: str,
    *,
    tem_vinculo_github: bool = False,
    motivo_nao_desenvolvimento: str | None = None,
) -> None:
    """Rejeita saltos ilegais na triagem ops (#953 / #954). Idempotente se de==para."""
    from fastapi import HTTPException

    if para not in STATUS_VALIDOS:
        raise HTTPException(status_code=400, detail="Status inválido")
    if de == para:
        if para == "nao_sera_desenvolvida" and not (motivo_nao_desenvolvimento or "").strip():
            raise HTTPException(
                status_code=400,
                detail="Informe o motivo quando marcar como não será desenvolvida",
            )
        return
    permitidos = STATUS_TRANSICOES.get(de)
    if permitidos is None or para not in permitidos:
        raise HTTPException(
            status_code=400,
            detail=f"{MSG_TRANSICAO_INVALIDA}: {rotulo_status(de)} → {rotulo_status(para)}",
        )
    if para == "nao_sera_desenvolvida" and not (motivo_nao_desenvolvimento or "").strip():
        raise HTTPException(
            status_code=400,
            detail="Informe o motivo quando marcar como não será desenvolvida",
        )
    if para == "em_desenvolvimento" and not tem_vinculo_github:
        raise HTTPException(status_code=400, detail=MSG_GITHUB_OBRIGATORIO)


def mensagem_publica_status(status: str, *, motivo: str | None = None) -> str:
    base = STATUS_MENSAGENS.get(status, "O estado do seu pedido foi atualizado.")
    if status == "nao_sera_desenvolvida" and (motivo or "").strip():
        return f"{base}\n\nMotivo: {motivo.strip()}"
    return base


def rotulo_status(status: str) -> str:
    return STATUS_LABELS.get(status, status.replace("_", " "))


def normalizar_versao_alvo(valor: str | None) -> str | None:
    v = (valor or "").strip()
    return v[:64] if v else None


def rotulo_versao_alvo_publica(status: str, versao: str | None) -> str | None:
    """Rótulo amigável para Minhas solicitações (#955)."""
    v = normalizar_versao_alvo(versao)
    if not v:
        return None
    if status == "concluida":
        return f"Disponível na {v}"
    if status in ("planejada", "em_desenvolvimento"):
        return f"Prevista para {v}"
    return None
