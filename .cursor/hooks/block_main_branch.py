#!/usr/bin/env python3
"""Bloqueia git/gh perigosos em main/staging (staging = produção)."""

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
                "agent_message": "Hook block_main_branch bloqueou comando em branch protegida / staging.",
            }
        )
    )
    sys.exit(0)


def _pr_base_ref(pr_selector: str | None) -> str | None:
    """baseRefName do PR (número ou PR da branch atual)."""
    args = ["gh", "pr", "view", "--json", "baseRefName"]
    if pr_selector:
        args.insert(3, pr_selector)
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=15)
        if r.returncode != 0:
            return None
        data = json.loads(r.stdout or "{}")
        return data.get("baseRefName")
    except (subprocess.SubprocessError, OSError, json.JSONDecodeError):
        return None


def _blocks_staging_merge(command: str) -> bool:
    """Impede merge de PR cuja base é staging (produção)."""
    if not re.search(r"\bgh\s+pr\s+merge\b", command):
        return False

    m = re.search(r"\bgh\s+pr\s+merge\s+(\d+)\b", command)
    pr_num = m.group(1) if m else None
    base = _pr_base_ref(pr_num)
    if base == "staging":
        return True
    if base is None and ("staging" in command.lower() or "main-into-staging" in command.lower()):
        return True
    # Sem número e sem API: se a branch atual é de merge para staging, bloquear
    branch = current_branch()
    if pr_num is None and branch and re.search(r"main-into-staging|merge/.*staging", branch, re.I):
        return True
    return False


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        print(json.dumps({"permission": "allow"}))
        return

    command = payload.get("command") or ""

    # --- gh: nunca mergear PR cuja base é staging ---
    if re.search(r"\bgh\b", command):
        if _blocks_staging_merge(command):
            deny(
                "Merge de PR para staging bloqueado (staging = produção). "
                "Abra/atualize o PR e peça aprovação/merge manual no GitHub."
            )
        print(json.dumps({"permission": "allow"}))
        return

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
                "Push para main/staging bloqueado. "
                "Feature → PR para main (/criar-pr). "
                "Release → PR main→staging (/release-staging) sem merge pelo agente."
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
