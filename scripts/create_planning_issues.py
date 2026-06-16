#!/usr/bin/env python3
"""Cria épicos e issues filhas a partir de .github/planning-issue-bodies/."""

from __future__ import annotations

import re
import subprocess
import sys
import time
from pathlib import Path

REPO = "lgustavoss/dx-connect"
META_ISSUE = 16
PLANNING_DIR = Path(__file__).resolve().parents[1] / ".github/planning-issue-bodies"

EPICS = [
    ("RT", "RT-epic-tempo-real.md"),
    ("T", "T-epic-distribuicao-tickets.md"),
    ("R", "R-epic-roteamento.md"),
    ("S", "S-epic-sla.md"),
    ("D", "D-epic-dashboards-relatorios.md"),
    ("A", "A-epic-auditoria.md"),
    ("KB", "KB-epic-base-conhecimento.md"),
    ("P", "P-epic-portal-cliente.md"),
]

CHILDREN: dict[str, list[str]] = {
    "RT": [
        "RT-01-backend-infra-sse.md",
        "RT-02-backend-eventos-tickets-chats.md",
        "RT-03-backend-eventos-notificacoes.md",
        "RT-04-frontend-cliente-sse.md",
        "RT-05-frontend-integracao-chat-sse.md",
        "RT-06-frontend-integracao-tickets-notificacoes-sse.md",
    ],
    "T": [
        "T-01-backend-config-setor-distribuicao.md",
        "T-02-backend-worker-atribuicao-automatica.md",
        "T-03-frontend-config-distribuicao-setor.md",
        "T-04-frontend-indicadores-fila-tickets.md",
    ],
    "R": [
        "R-01-backend-modelo-regras-roteamento.md",
        "R-02-backend-motor-aplicacao-roteamento.md",
        "R-03-frontend-crud-regras-roteamento.md",
    ],
    "S": [
        "S-01-backend-modelo-config-sla.md",
        "S-02-backend-calculo-violacoes-sla.md",
        "S-03-backend-notificacoes-sla.md",
        "S-04-frontend-config-sla-admin.md",
        "S-05-frontend-indicadores-sla-tickets.md",
    ],
    "D": [
        "D-01-backend-metricas-dashboard-geral.md",
        "D-02-backend-metricas-dashboard-tickets.md",
        "D-03-backend-metricas-dashboard-chats.md",
        "D-04-backend-relatorios-export.md",
        "D-05-frontend-dashboard-geral.md",
        "D-06-frontend-dashboard-tickets.md",
        "D-07-frontend-dashboard-chats.md",
        "D-08-frontend-relatorios-ui.md",
    ],
    "A": [
        "A-01-backend-audit-trail-expandido.md",
        "A-02-backend-consulta-export-auditoria.md",
        "A-03-frontend-auditoria-ui.md",
    ],
    "KB": [
        "KB-01-backend-modelo-artigos-categorias.md",
        "KB-02-backend-api-admin-artigos.md",
        "KB-03-backend-api-publica-artigos.md",
        "KB-04-backend-vinculo-motivo-artigos.md",
        "KB-05-frontend-editor-artigos-admin.md",
        "KB-06-frontend-gestao-categorias-admin.md",
        "KB-07-frontend-leitura-artigos-interno.md",
    ],
    "P": [
        "P-01-backend-auth-portal-funcionario.md",
        "P-02-backend-api-tickets-portal.md",
        "P-03-backend-mensagens-anexos-portal.md",
        "P-04-backend-notificacoes-portal.md",
        "P-05-frontend-shell-portal.md",
        "P-06-frontend-listagem-tickets-portal.md",
        "P-07-frontend-abertura-ticket-portal.md",
        "P-08-frontend-detalhe-ticket-portal.md",
        "P-09-frontend-kb-portal-cliente.md",
    ],
}


def read_md(filename: str) -> tuple[str, str]:
    path = PLANNING_DIR / filename
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or not lines[0].startswith("# "):
        raise ValueError(f"Título inválido em {filename}")
    title = lines[0][2:].strip()
    body = "\n".join(lines[1:]).strip()
    return title, body


def labels_for(filename: str, is_epic: bool) -> list[str]:
    if is_epic:
        return ["epic", "documentation", "enhancement"]
    labels = ["enhancement"]
    if "backend" in filename:
        labels.extend(["backend", "python"])
    elif "frontend" in filename:
        labels.extend(["frontend", "ux"])
    if filename.startswith("P-"):
        labels.append("documentation")
    return labels


def gh_issue_create(title: str, body: str, labels: list[str]) -> int:
    cmd = [
        "gh",
        "issue",
        "create",
        "--repo",
        REPO,
        "--title",
        title,
        "--body",
        body,
    ]
    for label in labels:
        cmd.extend(["--label", label])
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    url = result.stdout.strip()
    m = re.search(r"/issues/(\d+)", url)
    if not m:
        raise RuntimeError(f"URL inesperada: {url}")
    return int(m.group(1))


def append_footer(body: str, filename: str, epic_num: int | None) -> str:
    lines = [
        "",
        "---",
        f"**Rascunho:** `.github/planning-issue-bodies/{filename}`",
        f"**Meta-issue:** #{META_ISSUE}",
    ]
    if epic_num is not None:
        lines.append(f"**Épico pai:** #{epic_num}")
    return body + "\n".join(lines)


def main() -> int:
    epic_numbers: dict[str, int] = {}
    child_map: dict[str, list[int]] = {k: [] for k in CHILDREN}

    print("=== Criando épicos ===")
    for prefix, epic_file in EPICS:
        title, body = read_md(epic_file)
        body = append_footer(
            body
            + f"\n\n---\n\n**Relacionado:** meta-issue #{META_ISSUE} (melhorias operacionais).\n",
            epic_file,
            None,
        )
        num = gh_issue_create(title, body, labels_for(epic_file, True))
        epic_numbers[prefix] = num
        print(f"  #{num} {title}")
        time.sleep(0.5)

    print("\n=== Criando issues filhas ===")
    total_children = 0
    for prefix, files in CHILDREN.items():
        epic_num = epic_numbers[prefix]
        for child_file in files:
            title, body = read_md(child_file)
            body = append_footer(body, child_file, epic_num)
            num = gh_issue_create(title, body, labels_for(child_file, False))
            child_map[prefix].append(num)
            total_children += 1
            print(f"  #{num} [{prefix}] {title}")
            time.sleep(0.4)

    print("\n=== Atualizando épicos com checklist ===")
    for prefix, epic_file in EPICS:
        epic_num = epic_numbers[prefix]
        title, body = read_md(epic_file)
        checklist = "\n".join(f"- [ ] #{n}" for n in child_map[prefix])
        new_body = (
            append_footer(body, epic_file, None)
            + f"\n\n## Issues filhas (GitHub)\n\n{checklist}\n"
        )
        subprocess.run(
            [
                "gh",
                "issue",
                "edit",
                str(epic_num),
                "--repo",
                REPO,
                "--body",
                new_body,
            ],
            check=True,
        )
        print(f"  #{epic_num} checklist ({len(child_map[prefix])} filhas)")
        time.sleep(0.3)

    print(f"\nConcluído: {len(EPICS)} épicos, {total_children} filhas.")
    print("Épicos:", ", ".join(f"{p}=#{n}" for p, n in epic_numbers.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
