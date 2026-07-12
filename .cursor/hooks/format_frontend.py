#!/usr/bin/env python3
"""ESLint --fix em arquivos frontend editados (best-effort, não bloqueia)."""

import json
import subprocess
import sys
from pathlib import Path


def file_path_from_payload(payload: dict) -> str | None:
    for key in ("file_path", "path", "filePath"):
        val = payload.get(key)
        if val:
            return str(val)
    tool_input = payload.get("tool_input") or payload.get("input") or {}
    if isinstance(tool_input, dict):
        for key in ("file_path", "path", "target_notebook"):
            val = tool_input.get(key)
            if val and str(val).endswith((".ts", ".tsx", ".js", ".jsx")):
                return str(val)
    return None


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return

    raw = file_path_from_payload(payload)
    if not raw:
        return

    path = Path(raw.replace("\\", "/"))
    if "frontend/" not in str(path).replace("\\", "/"):
        return
    if path.suffix not in {".ts", ".tsx", ".js", ".jsx"}:
        return

    frontend_dir = Path("frontend")
    if not frontend_dir.is_dir():
        return

    rel = path
    if path.is_absolute():
        try:
            rel = path.relative_to(Path.cwd())
        except ValueError:
            parts = path.parts
            if "frontend" in parts:
                idx = parts.index("frontend")
                rel = Path(*parts[idx:])
            else:
                return

    try:
        subprocess.run(
            ["npx", "eslint", "--fix", str(rel)],
            cwd=frontend_dir,
            capture_output=True,
            timeout=30,
        )
    except (subprocess.SubprocessError, OSError):
        pass


if __name__ == "__main__":
    main()
