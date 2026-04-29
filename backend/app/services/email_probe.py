from __future__ import annotations

import imaplib
import smtplib


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
    imap = cls(host=host, port=port, timeout=timeout_seconds)  # type: ignore[arg-type]
    try:
        imap.login(user, password)
        f = (folder or "INBOX").strip() or "INBOX"
        imap.select(f, readonly=True)
    finally:
        try:
            imap.logout()
        except Exception:
            pass

