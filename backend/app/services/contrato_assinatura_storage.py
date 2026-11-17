"""Storage local das evidências de assinatura (#1380)."""

from __future__ import annotations

import hashlib
import re
import uuid
from pathlib import Path

from app.config import settings

_SAFE = re.compile(r"[^a-zA-Z0-9._-]+")


def diretorio_contrato(contrato_id: int) -> Path:
    base = Path(settings.CONTRATO_ASSINATURAS_DIR)
    if not base.is_absolute():
        base = Path.cwd() / base
    dest = base / str(int(contrato_id)) / "assinatura"
    dest.mkdir(parents=True, exist_ok=True)
    return dest


def sha256_bytes(conteudo: bytes) -> str:
    return hashlib.sha256(conteudo).hexdigest()


def gravar_evidencia(
    contrato_id: int,
    *,
    conteudo: bytes,
    nome_logico: str,
    extensao: str,
) -> tuple[str, str]:
    """Grava bytes e devolve (caminho relativo ao CONTRATO_ASSINATURAS_DIR, sha256)."""
    if not conteudo:
        raise ValueError("Arquivo de evidência vazio.")
    if len(conteudo) > settings.CONTRATO_ASSINATURAS_MAX_BYTES:
        raise ValueError("Arquivo de evidência excede o tamanho máximo permitido.")
    ext = extensao if extensao.startswith(".") else f".{extensao}"
    safe = _SAFE.sub("_", (nome_logico or "evidencia").strip())[:80] or "evidencia"
    nome = f"{safe}-{uuid.uuid4().hex[:12]}{ext}"
    pasta = diretorio_contrato(contrato_id)
    caminho = pasta / nome
    caminho.write_bytes(conteudo)
    rel = f"{int(contrato_id)}/assinatura/{nome}"
    return rel, sha256_bytes(conteudo)


def caminho_absoluto(rel_path: str | None) -> Path | None:
    if not (rel_path or "").strip():
        return None
    base = Path(settings.CONTRATO_ASSINATURAS_DIR)
    if not base.is_absolute():
        base = Path.cwd() / base
    full = (base / rel_path).resolve()
    try:
        full.relative_to(base.resolve())
    except ValueError:
        return None
    return full if full.is_file() else None


def apagar_evidencias(contrato_id: int) -> int:
    """Remove a pasta de assinatura do contrato. Devolve quantos ficheiros apagou."""
    pasta = diretorio_contrato(contrato_id)
    if not pasta.exists():
        return 0
    n = 0
    for f in pasta.iterdir():
        if f.is_file():
            f.unlink(missing_ok=True)
            n += 1
    try:
        pasta.rmdir()
        pasta.parent.rmdir()
    except OSError:
        pass
    return n
