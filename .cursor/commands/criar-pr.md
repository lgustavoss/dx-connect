# Criar PR

Finalize a feature e abra Pull Request para **`main`**.

## Pré-requisitos

- Feature implementada e revisada (`/revisar-e-testar` recomendado)
- Branch **não** é `main` nem `staging`
- Testes passando localmente

## Passo 1 — Diagnóstico Git

Execute em paralelo:

```bash
git status
git diff
git diff --staged
git branch --show-current
git log main..HEAD --oneline
git status -sb
```

Se estiver em `main` ou `staging`, **pare** — oriente usar `/iniciar-feature` primeiro.

## Passo 2 — Commit (se necessário)

Se houver alterações não commitadas:

1. Analise o diff completo
2. **Não** incluir arquivos sensíveis (`.env`, credenciais)
3. Mensagem no estilo do repo: `feat(escopo): descrição concisa`
4. Commit com HEREDOC (PowerShell: equivalente seguro)

Só commitar quando este comando foi invocado — o usuário está pedindo finalização.

## Passo 3 — Push

```bash
git push -u origin HEAD
```

## Passo 4 — Criar PR

Use `gh pr create` com base **`main`**:

```bash
gh pr create --base main --title "título descritivo" --body "$(cat <<'EOF'
## Summary
- ...

## Test plan
- [ ] pytest passou
- [ ] npm run build passou
- [ ] Testado manualmente: ...

## Issue
Closes #NNN (se aplicável)
EOF
)"
```

Adapte título e corpo ao diff real e à issue relacionada.

## Passo 5 — Entrega

Informe:
- URL do PR
- Branch → main
- O que foi incluído no PR
- Pendências (se houver)

**Não** fazer merge — só abrir o PR.
