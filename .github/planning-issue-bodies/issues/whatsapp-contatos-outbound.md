# WhatsApp: aba Contatos e chat iniciado pelo atendente

Issue: https://github.com/lgustavoss/dx-connect/issues/531

## Contexto
Hoje o chat WhatsApp só nasce quando o cliente envia a primeira mensagem. O atendente precisa poder retomar contato (ex.: atualizar andamento de uma demanda) pelo WhatsApp do cliente.

## Escopo
- Nova aba **Contatos** no hub `/chat`
- Lista de funcionários com badge da empresa e telefone
- Iniciar a partir de contato, número avulso ou chat encerrado
- Chat já em `em_atendimento` com o iniciador como responsável
- Campo `telefone` em `funcionarios_rede`
