## Problema
No chat ativo é possível identificar/cadastrar o contato do cliente (funcionário da rede). No Histórico, ao abrir um atendimento já encerrado, o botão e o banner de identificação somem — só a UI bloqueia; a API já permite.

Além disso, o cadastro/vínculo pelo chat não grava o `wa_id` em `funcionarios_rede.telefone`, então o contato pode não aparecer utilizável na aba Contatos / outbound (#531).

## Critérios de aceite
- [ ] Em conversa encerrada (ou aguardando avaliação), sem vínculo: banner e ação «Identificar contato» disponíveis
- [ ] Composer, transferir e encerrar continuam indisponíveis no encerrado
- [ ] Cadastrar ou vincular pelo chat preenche `telefone` a partir do `wa_id` quando o cadastro ainda não tem telefone
- [ ] Contato fica acionável na aba Contatos após o vínculo/cadastro
- [ ] Teste cobrindo vincular/cadastrar em chat encerrado e assert de telefone

## Origem
Feedback de produção após Contatos (#531).
