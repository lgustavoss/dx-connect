# IC-09 — Chat interno: editar legenda de mídia

## Contexto

Follow-up IC-06 (#503). Edição de texto já funciona com janela de 5 minutos; mídia bloqueada em `permissoes_mensagem` e `editar_mensagem`.

## Proposta

### Backend

- Permitir `PATCH` em mensagens com `tipo_midia` em `TIPOS_MENSAGEM_MIDIA`
- Só altera `corpo` (legenda); arquivo de mídia inalterado
- Legenda vazia permitida (remove legenda customizada)
- Mesmas regras: autor, 5 min, não apagada
- Admin **não** edita legenda alheia (exceto regra existente de canal setor só para texto — mídia segue autor)

### Frontend

- Menu **Editar** em mensagens de mídia quando `pode_editar`
- Modo edição da legenda (textarea); preview da mídia permanece

## Critérios de aceite

- [ ] Editar legenda de imagem dentro de 5 min
- [ ] Adicionar legenda a mídia enviada sem legenda (dentro da janela)
- [ ] Após 5 min API retorna erro e `pode_editar=false`
- [ ] SSE propaga alteração na thread aberta
- [ ] Testes backend

## Dependências

- #503 (edição de texto)

## Fora de escopo

- Substituir arquivo de mídia após envio

## Origem

Fora de escopo IC-06 — lote `feat/chat-interno-v3`.
