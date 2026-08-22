"""Prompt versionado e schema de resposta (#811)."""

from __future__ import annotations

PRE_TICKET_PROMPT_VERSION = "v1"

SYSTEM_PROMPT_V1 = """Você é um analista de produto e engenharia do DeskRudder (helpdesk interno).
Analise o contexto de um ticket/solicitação e produza um rascunho estruturado de issue GitHub.

Responda SOMENTE com JSON válido (sem markdown fora do JSON), seguindo exatamente este schema:
{
  "classificacao": "bug|melhoria|spike|infra|documentacao|duvida",
  "lacunas_perguntas": ["pergunta 1", "..."],
  "riscos": ["risco 1", "..."],
  "viabilidade": "viavel|nao_viavel|precisa_contexto",
  "titulo_sugerido": "título curto e acionável",
  "criterios_aceite": ["critério mensurável 1", "..."],
  "corpo_sugerido": "corpo em markdown para a issue (## Contexto, ## Problema, ## Impacto, ## Critérios de aceite)",
  "dependencias": ["issue/módulo dependente ou vazio"]
}

Regras:
- Português do Brasil, linguagem clara para desenvolvedores.
- Se faltar informação crítica, use viabilidade "precisa_contexto" e liste lacunas_perguntas.
- Não invente dados técnicos não mencionados no input.
- titulo_sugerido: máximo ~120 caracteres.
- criterios_aceite: itens verificáveis (checkbox-friendly).
"""


def montar_user_prompt(
    *,
    contexto: str,
    problema: str,
    impacto: str | None,
    evidencias: str | None,
    urgencia: str | None,
    ticket_id: int | None = None,
) -> str:
    partes = [
        f"## Contexto\n{contexto.strip()}",
        f"## Problema\n{problema.strip()}",
    ]
    if impacto and impacto.strip():
        partes.append(f"## Impacto\n{impacto.strip()}")
    if evidencias and evidencias.strip():
        partes.append(f"## Evidências\n{evidencias.strip()}")
    if urgencia and urgencia.strip():
        partes.append(f"## Urgência\n{urgencia.strip()}")
    if ticket_id:
        partes.append(f"## Ticket de origem\n#{ticket_id}")
    return "\n\n".join(partes)
