"""Similaridade de nomes de funcionários (dedupe no cadastro WhatsApp).

Critério (#593):
- Normaliza acentos, caixa e espaços.
- Pontua com o máximo entre: SequenceMatcher (difflib), Jaccard de tokens
  e bónus se um nome contém o outro.
- Limiar mínimo ``LIMIAR_SIMILARIDADE`` (0,72); ``LIMIAR_ALTA`` (0,90) para aviso.
"""

from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher

LIMIAR_SIMILARIDADE = 0.72
LIMIAR_ALTA = 0.90
_TOKEN_MIN = 3


def normalizar_nome(texto: str) -> str:
    s = unicodedata.normalize("NFKD", texto or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def tokens_significativos(nome_norm: str) -> list[str]:
    return [t for t in nome_norm.split() if len(t) >= _TOKEN_MIN]


def score_nomes(a: str, b: str) -> float:
    na = normalizar_nome(a)
    nb = normalizar_nome(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    seq = SequenceMatcher(None, na, nb).ratio()
    ta, tb = set(na.split()), set(nb.split())
    jaccard = (len(ta & tb) / len(ta | tb)) if (ta | tb) else 0.0
    if na in nb or nb in na:
        contain = 0.85 + 0.15 * seq
    else:
        contain = 0.0
    return max(seq, jaccard, contain)


def ranquear_similares(
    nome_consulta: str,
    candidatos: list[tuple[int, str]],
    *,
    limiar: float = LIMIAR_SIMILARIDADE,
    limit: int = 5,
) -> list[tuple[int, str, float]]:
    """
    ``candidatos``: lista de ``(id, nome)``.
    Retorna top ``limit`` acima do limiar, ordenados por score desc.
    """
    q = (nome_consulta or "").strip()
    if len(normalizar_nome(q)) < _TOKEN_MIN:
        return []
    scored: list[tuple[int, str, float]] = []
    for cid, nome in candidatos:
        sc = score_nomes(q, nome)
        if sc >= limiar:
            scored.append((cid, nome, sc))
    scored.sort(key=lambda x: (-x[2], x[1].lower(), x[0]))
    return scored[: max(1, limit)]
