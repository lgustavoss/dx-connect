#!/usr/bin/env python3
"""Bloqueia git commit/push perigosos em main/staging."""

import json
import re
import subprocess
import sys


PROTECTED = frozenset({"main", "staging"})


def current_branch() -> str:
    try:
        r = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return (r.stdout or "").strip()
    except (subprocess.SubprocessError, OSError):
        return ""


def deny(msg: str) -> None:
    print(
        json.dumps(
            {
                "permission": "deny",
                "user_message": msg,
                "agent_message": "Hook block_main_branch bloqueou comando git em branch protegida.",
            }
        )
    )
    sys.exit(0)


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        print(json.dumps({"permission": "allow"}))
        return

    command = payload.get("command") or ""
    if not re.search(r"\bgit\b", command):
        print(json.dumps({"permission": "allow"}))
        return

    branch = current_branch()

    # Push direto para main/staging (mesmo a partir de outra branch)
    if re.search(r"\bgit\s+push\b", command):
        if re.search(r"\b(main|staging)\b", command) or re.search(
            r"HEAD:(main|staging)", command
        ):
            deny(
                "Push para main/staging bloqueado. Abra PR com /criar-pr a partir de uma branch de feature."
            )

    # Operações destrutivas na branch atual protegida
    if branch in PROTECTED:
        if re.search(r"\bgit\s+(commit|merge|reset|rebase)\b", command):
            deny(
                f"Comando git bloqueado na branch '{branch}'. "
                "Use /iniciar-feature para criar uma branch antes de implementar."
            )
        if re.search(r"\bgit\s+push\b", command):
            deny(
                f"Push bloqueado na branch '{branch}'. "
                "Trabalhe em uma branch de feature e abra PR para main."
            )

    print(json.dumps({"permission": "allow"}))


if __name__ == "__main__":
    main()
