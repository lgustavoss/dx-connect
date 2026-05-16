from __future__ import annotations

import imaplib
import smtplib


def format_email_probe_error(exc: BaseException) -> str:
    """Converte excepções de imaplib/smtplib em texto legível (evita ``b'LOGIN failed.'`` no JSON)."""
    if isinstance(exc, imaplib.IMAP4.error):
        parts: list[str] = []
        for a in getattr(exc, "args", ()) or ():
            if isinstance(a, bytes):
                parts.append(a.decode("utf-8", errors="replace"))
            else:
                parts.append(str(a))
        msg = " ".join(parts).strip() or "Erro IMAP"
        low = msg.lower()
        if "login failed" in low or "authentication failed" in low:
            return (
                f"{msg} — O servidor recusou o login IMAP. "
                "No Microsoft 365 o envio (SMTP autenticado) e a receção (IMAP) são controlados em separado: o teste SMTP "
                "pode passar mesmo quando IMAP está desligado na caixa, a autenticação básica para IMAP está bloqueada "
                "no tenant, ou só o SMTP foi autorizado. Isto não indica senha errada por si só. "
                "Peça ao administrador para rever a caixa no Exchange (IMAP ativo, políticas de autenticação) e a "
                "documentação sobre autenticação básica em Exchange Online. "
                "https://learn.microsoft.com/exchange/clients-and-mobile-in-exchange-online/deprecation-of-basic-authentication-exchange-online"
            )
        return msg
    return (str(exc) or "").strip() or "Erro desconhecido"


def _imap_auth_login_or_plain(imap: imaplib.IMAP4, user: str, password: str) -> None:
    """Tenta LOGIN; se falhar, tenta AUTHENTICATE PLAIN quando o servidor anunciar AUTH=PLAIN (alguns hosts diferem)."""
    try:
        imap.login(user, password)
        return
    except imaplib.IMAP4.error as login_err:
        cap_raw: bytes | str = b""
        try:
            _typ, dat = imap.capability()
            if dat and isinstance(dat[0], (bytes, bytearray)):
                cap_raw = bytes(dat[0])
            elif dat:
                cap_raw = str(dat[0]).encode("ascii", errors="ignore")
        except Exception:
            raise login_err from None
        caps = cap_raw.decode("ascii", errors="ignore").upper()
        if "AUTH=PLAIN" not in caps:
            raise login_err from None
        u = user.encode("utf-8")
        p = password.encode("utf-8")

        def plain_handler(_resp: bytes) -> bytes:
            return b"\0" + u + b"\0" + p

        try:
            imap.authenticate("PLAIN", plain_handler)
        except imaplib.IMAP4.error:
            raise login_err from None


def testar_smtp(
    *,
    host: str,
    port: int,
    user: str | None,
    password: str | None,
    use_starttls: bool,
    timeout_seconds: int = 10,
) -> None:
    if not host or not str(host).strip():
        raise ValueError("SMTP host não informado.")
    if not isinstance(port, int) or port <= 0:
        raise ValueError("SMTP port inválida.")

    with smtplib.SMTP(host=host, port=port, timeout=timeout_seconds) as smtp:
        smtp.ehlo()
        if use_starttls:
            smtp.starttls()
            smtp.ehlo()
        if user and password:
            smtp.login(user, password)


def testar_imap(
    *,
    host: str,
    port: int,
    user: str | None,
    password: str | None,
    use_ssl: bool,
    folder: str | None,
    timeout_seconds: int = 10,
) -> None:
    if not host or not str(host).strip():
        raise ValueError("IMAP host não informado.")
    if not isinstance(port, int) or port <= 0:
        raise ValueError("IMAP port inválida.")
    if not user or not user.strip() or not password or not password.strip():
        raise ValueError("IMAP user/password não informados.")

    cls = imaplib.IMAP4_SSL if use_ssl else imaplib.IMAP4
    imap = cls(host=host, port=port, timeout=timeout_seconds)  # type: ignore[misc]
    try:
        _imap_auth_login_or_plain(imap, user.strip(), password)
        f = (folder or "INBOX").strip() or "INBOX"
        imap.select(f, readonly=True)
    finally:
        try:
            imap.logout()
        except Exception:
            pass

