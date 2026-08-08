# Plano — Catálogo de custos lote B (#331 / #332 / #335)

**Épico:** [#321](https://github.com/lgustavoss/dx-connect/issues/321)  
**Branch:** `feat/comercial-custos-regras-331-332-335`  
**Base:** `main` com lote A (#656 mergeado)  
**Status:** plano **revisado** e **implementado** na branch `feat/comercial-custos-regras-331-332-335` (2026-08-08)

---

## Resumo

Completar CM01-F2 com o fluxo real do comercial: catálogo traz **valores padrão**; na proposta/simulação o admin **escolhe** desconto de posto (&lt;100k) e **sobrescreve** TEF (custo interno + valor ao cliente); o motor devolve **snapshot** para uso futuro em contrato. Controlo do desconto após os 3 meses é **manual** — sem ecrã pesado de validação.

---

## Regras de negócio (confirmadas)

### Posto &lt;100k L (#332)

1. Cliente **declara** que o posto vende menos de 100k L/mês.
2. Comercial **ativa o desconto** (custo a **20% SM** em vez de 30%).
3. Nos **3 primeiros meses** de uso do sistema: se em **qualquer** mês passar de 100k L → **perde o desconto** (volta a 30%).
4. Depois disso (ou a qualquer momento), o desconto pode ser **aplicado ou removido manualmente** — não depende de ecrã automático rígido.

### TEF (#331)

1. Catálogo guarda só os **valores padrão** (base 1º PDV + adicional).
2. Oferta do fornecedor muda caso a caso → **não** há “promoção cadastrada com vigência” no catálogo.
3. No momento da **proposta/contrato**, o comercial informa:
   - **custo promocional** (o que a DeskRudder paga / usa no custo interno), e/ou
   - **valor ao cliente** (com ou sem promoção de venda).
4. O snapshot grava o que foi usado naquela proposta.

### Ecrã de validação

Não é prioridade: o controlo é interno e manual. Neste lote **não** há UI rica de volumes/congelamento; no máximo campos simples na simulação + API mínima se ajudar o motor.

---

## Escopo do lote B

### Dentro

| Issue | Entrega |
|-------|---------|
| **#331** | Catálogo TEF = padrão; simulação/motor aceita **override** opcional `tef_custo_base` / `tef_custo_adicional` (e opcional `tef_valor_cliente_*` para registo no snapshot). Sem campos promo no item do catálogo. |
| **#332** | Itens `% SM` com flag `aplica_tier_posto`; na simulação: `desconto_posto_100k: true\|false` (true → 20%, false/omitido → usa % do catálogo ou 30% default do item). Sem tabela elaborada de avaliação nem job automático. Doc da regra no código. |
| **#335** | `calcular_custo_pacote` + snapshot JSON imutável; `simular` como fachada; testes com override TEF + desconto posto. |
| **UI** | Aba Simular: checkbox «desconto posto &lt;100k»; campos opcionais de override TEF (custo e valor cliente); mostrar snapshot/resumo. Formulário de item **sem** promo. |

### Fora (follow-ups)

- Persistência do snapshot em negociação/contrato (#322+)
- Tela na empresa para anotar volumes dos 3 meses (opcional, depois)
- Integração automática com implantação / retaguarda de litros
- Cadastro de promoções TEF no catálogo com vigência (descartado para o fluxo actual)
- SSE

---

## Desenho técnico

### TEF no motor

```text
valores_efetivos =
  override da request, se enviado
  senão tef_base / tef_adicional do catálogo

custo_linha = base + max(0, pdvs-1) * adicional
```

Valor ao cliente (se informado) entra só no **snapshot** / metadados — não soma no `total` de **custo** interno (o total continua sendo custo DeskRudder).

### Tier posto no motor

```text
se item.aplica_tier_posto:
  percentual = 20 se desconto_posto_100k else (item.percentual_sm ou 30)
senão:
  percentual = item.percentual_sm
```

Default recomendado no catálogo: item “Posto” com `percentual_sm=30` e `aplica_tier_posto=true`; o checkbox na simulação aplica o 20%.

### Snapshot (exemplo)

```json
{
  "versao": 1,
  "calculado_em": "...",
  "data_referencia": "...",
  "salario_minimo": {"id": 1, "valor": "1518.00"},
  "desconto_posto_100k": true,
  "quantidade_pdvs": 3,
  "itens": [
    {
      "id": 1, "slug": "posto", "tipo": "percentual_sm",
      "percentual_usado": "20", "valor": "303.60",
      "aplica_tier_posto": true
    },
    {
      "id": 10, "slug": "tef", "tipo": "composto_tef",
      "tef_base_catalogo": "100.00", "tef_adicional_catalogo": "30.00",
      "tef_base_usado": "80.00", "tef_adicional_usado": "25.00",
      "override_custo": true,
      "tef_valor_cliente_base": "120.00",
      "tef_valor_cliente_adicional": "40.00",
      "valor_custo": "130.00"
    }
  ],
  "total_custo": "..."
}
```

### RBAC

Só admin (`exigir_admin`). Sem SSE.

---

## Mapa de arquivos

| Ação | Caminho |
|------|---------|
| alterar | `backend/app/models/comercial_custo.py` (`aplica_tier_posto`) |
| criar | `backend/alembic/versions/083_*.py` |
| alterar | `backend/app/schemas/comercial_custo.py` |
| alterar | `backend/app/services/comercial_custo.py` |
| alterar | `backend/app/api/comercial_custos.py` |
| alterar | `backend/tests/test_comercial_custos.py` |
| alterar | `frontend/src/api/client.ts` |
| alterar | `frontend/src/pages/ConfigComercialCustos.tsx` |
| alterar | `CHANGELOG.md` |

---

## Ordem de implementação

1. Migration: `aplica_tier_posto` em `custo_catalogo_itens`
2. Schemas: request de simular com `desconto_posto_100k`, overrides TEF, response com snapshot
3. `calcular_custo_pacote` + refatorar `simular_custo`
4. Testes (#331 fórmula + override; #332 20 vs 30 / qualquer mês &gt;100k só documentado; #335 snapshot estável)
5. UI simulador
6. CHANGELOG; pytest; build frontend

---

## Testes (aceite)

- [ ] TEF sem override = valores do catálogo (1, 2, N PDVs)
- [ ] TEF com override = usa override; snapshot marca `override_custo`
- [ ] Valor cliente no snapshot não altera `total_custo`
- [ ] `desconto_posto_100k=true` em item `aplica_tier_posto` → 20% SM
- [ ] Sem desconto → percentual do catálogo (ex. 30%)
- [ ] Snapshot não muda se SM/catálogo forem alterados depois (objecto já devolvido)
- [ ] Atendente → 403

---

## Próximo passo

Implementar neste branch `feat/comercial-custos-regras-331-332-335` conforme este plano revisado.
