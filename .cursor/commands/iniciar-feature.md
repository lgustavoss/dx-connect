# Iniciar feature

Prepare o ambiente Git para uma nova feature **antes** de codar.

## Entrada

Peça se não informado:
- número/link da issue **ou** slug da feature
- tipo: `feat` (padrão), `fix`, `chore`, `docs`

## Passo 1 — Verificar estado

```bash
git status
git branch --show-current
```

Se houver alterações não commitadas, **pare** e pergunte ao usuário:
- fazer stash
- commitar na branch atual
- descartar

Não prossiga com working tree suja sem decisão explícita.

## Passo 2 — Atualizar main

```bash
git fetch origin
git checkout main
git pull origin main
```

## Passo 3 — Criar branch

Nome: `{tipo}/{slug}[-{issue}]`

Exemplos:
- issue IC-02 → `feat/chat-interno-api-ic02`
- issue #119 → `feat/observabilidade-119`
- fix de scroll → `fix/whatsapp-scroll-mobile`

```bash
git checkout -b {nome-da-branch}
```

Confirme a branch ativa com `git branch --show-current`.

## Passo 4 — Handoff

Informe:
- Branch criada
- Base: `main` @ commit curto (`git log -1 --oneline`)

Sugira próximo passo:

```
/implementar-issue @<arquivo-da-issue.md>
```

**Não** escreva código de feature neste comando — só preparar Git.
