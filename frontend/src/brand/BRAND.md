# DeskRudder — identidade visual

Guia de referência para UI, marketing e materiais derivados.

## Conceito

**Desk** = mesa operacional (tickets, fila, dashboard).  
**Rudder** = leme (direcionar, rotear, manter o rumo do atendimento).

Metáfora: plataforma que **comanda** a operação multicanal da carteira de clientes.

## Logotipo

| Asset | Caminho | Uso |
|-------|---------|-----|
| Ícone | `public/deskrudder-mark.svg` | Sidebar recolhida, favicon base |
| Favicon | `public/deskrudder-favicon.svg` | Aba do navegador |
| Painel login | `public/deskrudder-login-panel.svg` | Coluna esquerda desktop |
| Componente React | `src/brand/RudderMark.tsx`, `BrandLogo.tsx` | UI dinâmica |

**Wordmark:** `Desk` (peso médio, slate) + `Rudder` (bold, gradiente teal → sky).

**Símbolo:** tile arredondado em gradiente + três linhas horizontais (desk) + leme com pino latão.

## Paleta

| Token | Hex | Uso |
|-------|-----|-----|
| Navy | `#0B2D4A` | Fundos escuros, extremo de gradiente |
| Navy mid | `#134166` | Painéis, login |
| Teal | `#0D9488` | Primária — botões, links, SLA |
| Teal light | `#14B8A6` | Hover, gradiente início |
| Sky | `#0284C7` | Gradiente fim, acentos |
| Brass | `#C9973A` | **Só no ícone** (pino do leme) |
| Deck | `#F8FAFC` | Superfícies claras |
| Ink | `#0F172A` | Texto principal |

Gradiente primário: `135deg, #14B8A6 → #0D9488 → #0284C7`

## Tipografia

**Plus Jakarta Sans** (Google Fonts) — pesos 400–700.

- Títulos: semibold/bold, `tracking-tight`
- UI/corpo: 14–16px, antialiased

## Tom de voz (UI)

- Claro, operacional, sem jargão de nicho (evitar “posto”, “revenda” na marca)
- Tagline: **O leme da sua operação de atendimento**

## Implementação técnica

- Tokens: `src/brand/tokens.ts`
- Tema Tailwind: `src/index.css` (`@theme` remapeia `cyan-*` e `blue-600/700` para a paleta)
- Import único: `import { BrandLogo, APP_NAME } from '../brand'`

## Espaçamento mínimo do ícone

Manter área livre equivalente a **½** da altura do tile ao redor do mark em materiais impressos.

## O que não fazer

- Esticar ou rotacionar o leme
- Usar o latão como cor de botão (reservado ao detalhe do ícone)
- Separar “Desk” e “Rudder” em cores invertidas no wordmark claro
