"""Cliente HTTP do DocuSeal self-hosted (#1380 / #1429).

Testes injetam um fake via ``set_client_factory`` — sem rede no CI.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Protocol

import httpx

from app.config import settings


class DocusealError(Exception):
    """Falha de integração com o DocuSeal (mensagem segura para a ficha)."""

    def __init__(self, mensagem: str, *, status_code: int | None = None):
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.status_code = status_code


@dataclass(frozen=True)
class DocusealSubmitterOut:
    role: str
    slug: str
    link_assinatura: str
    email: str | None = None


@dataclass(frozen=True)
class DocusealSubmission:
    submission_id: str
    submitters: list[DocusealSubmitterOut] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def submitter_slug(self) -> str:
        return self.submitters[0].slug if self.submitters else ""

    @property
    def link_assinatura(self) -> str:
        return self.submitters[0].link_assinatura if self.submitters else ""


class DocusealClient(Protocol):
    def criar_submissao(
        self,
        *,
        template_id: str,
        submitters: list[dict[str, Any]],
        send_email: bool = False,
    ) -> DocusealSubmission: ...

    def cancelar_submissao(self, submission_id: str) -> None: ...

    def baixar_url(self, url: str) -> bytes: ...


class HttpDocusealClient:
    def __init__(self, base_url: str, api_token: str, *, app_url: str | None = None):
        self.base_url = base_url.rstrip("/")
        self.api_token = api_token
        self.app_url = (app_url or base_url).rstrip("/")

    def _headers(self) -> dict[str, str]:
        return {
            "X-Auth-Token": self.api_token,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def criar_submissao(
        self,
        *,
        template_id: str,
        submitters: list[dict[str, Any]],
        send_email: bool = False,
    ) -> DocusealSubmission:
        if not submitters:
            raise DocusealError("Nenhum signatário informado para o DocuSeal.")
        payload: dict[str, Any] = {
            "template_id": template_id,
            "send_email": send_email,
            "submitters": submitters,
        }
        try:
            with httpx.Client(timeout=30.0, follow_redirects=True) as client:
                resp = client.post(
                    f"{self.base_url}/api/submissions",
                    headers=self._headers(),
                    json=payload,
                )
        except httpx.HTTPError as exc:
            raise DocusealError(f"Não foi possível contatar o DocuSeal: {exc}") from exc
        if resp.status_code >= 400:
            raise DocusealError(
                f"DocuSeal recusou a submissão (HTTP {resp.status_code}).",
                status_code=resp.status_code,
            )
        data = resp.json()
        raw_submitters = data if isinstance(data, list) else data.get("submitters") or []
        if not isinstance(raw_submitters, list) or not raw_submitters:
            raise DocusealError("DocuSeal devolveu submissão sem signatários.")
        submission_id = str(
            (raw_submitters[0].get("submission_id") if isinstance(raw_submitters[0], dict) else None)
            or (data.get("id") if isinstance(data, dict) else None)
            or ""
        ).strip()
        parsed: list[DocusealSubmitterOut] = []
        for item in raw_submitters:
            if not isinstance(item, dict):
                continue
            slug = str(item.get("slug") or "").strip()
            if not slug:
                continue
            role = str(item.get("role") or "").strip()
            email = str(item.get("email") or "").strip() or None
            sid = str(item.get("submission_id") or submission_id or "").strip()
            if sid and not submission_id:
                submission_id = sid
            parsed.append(
                DocusealSubmitterOut(
                    role=role,
                    slug=slug,
                    link_assinatura=f"{self.app_url}/s/{slug}",
                    email=email,
                )
            )
        if not submission_id or not parsed:
            raise DocusealError("Resposta do DocuSeal sem submission_id/slug.")
        return DocusealSubmission(
            submission_id=submission_id,
            submitters=parsed,
            raw=data if isinstance(data, dict) else {"submitters": raw_submitters},
        )

    def cancelar_submissao(self, submission_id: str) -> None:
        try:
            with httpx.Client(timeout=30.0, follow_redirects=True) as client:
                resp = client.delete(
                    f"{self.base_url}/api/submissions/{submission_id}",
                    headers=self._headers(),
                )
        except httpx.HTTPError as exc:
            raise DocusealError(f"Não foi possível cancelar no DocuSeal: {exc}") from exc
        if resp.status_code >= 400 and resp.status_code != 404:
            raise DocusealError(
                f"DocuSeal recusou o cancelamento (HTTP {resp.status_code}).",
                status_code=resp.status_code,
            )

    def baixar_url(self, url: str) -> bytes:
        try:
            with httpx.Client(timeout=60.0, follow_redirects=True) as client:
                resp = client.get(url, headers=self._headers())
        except httpx.HTTPError as exc:
            raise DocusealError(f"Falha ao baixar artefato do DocuSeal: {exc}") from exc
        if resp.status_code >= 400:
            raise DocusealError(
                f"Download do DocuSeal falhou (HTTP {resp.status_code}).",
                status_code=resp.status_code,
            )
        return bytes(resp.content)


_ClientFactory = Callable[[], DocusealClient]
_factory: _ClientFactory | None = None


def set_client_factory(factory: _ClientFactory | None) -> None:
    global _factory
    _factory = factory


def docuseal_configurado() -> bool:
    return bool(
        (settings.DOCUSEAL_URL or "").strip()
        and (settings.DOCUSEAL_API_TOKEN or "").strip()
        and (settings.DOCUSEAL_TEMPLATE_ID or "").strip()
    )


def get_client() -> DocusealClient:
    if _factory is not None:
        return _factory()
    if not docuseal_configurado():
        raise DocusealError(
            "Assinatura eletrônica não está configurada "
            "(defina DOCUSEAL_URL, DOCUSEAL_API_TOKEN e DOCUSEAL_TEMPLATE_ID)."
        )
    app_url = (settings.DOCUSEAL_URL or "").strip()
    return HttpDocusealClient(
        settings.DOCUSEAL_URL.strip(),  # type: ignore[union-attr]
        settings.DOCUSEAL_API_TOKEN.strip(),  # type: ignore[union-attr]
        app_url=app_url,
    )
