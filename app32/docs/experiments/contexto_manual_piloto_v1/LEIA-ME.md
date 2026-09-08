# Kit preparado — piloto manual

Status: **preparado, não executado**. Nenhuma tarefa, chamada de geração ou medição real foi criada.

## O que fazer

1. Leia `C:\GestaoVersus\app32\app32\docs\runbooks\experimento_manual_contexto_engenharia_v1.md`.
2. Confirme que consegue usar o mesmo runtime/modelo/esforço e obter medições por execução. Se não conseguir observar tokens, preserve null; não use consumo percentual do plano.
3. Abra manualmente duas tarefas vazias e independentes. Sorteie a ordem; em uma envie o conteúdo de `baseline.md` e na outra de `candidate.md`. Não envie este LEIA-ME, critérios de QA, manifesto ou resultado da outra tarefa. Não execute os dois lados nesta conversa, pois ela já contém contexto e resultados prévios.
4. Os pacotes incluem a mesma governança explícita e a mesma pergunta. O baseline inclui dois arquivos técnicos extras; o candidate contém os dois necessários. Não altere os pacotes congelados. Se regras superiores exigirem ferramentas/contexto adicional, registre o desvio e não considere o par controlado.
5. Revise as respostas usando `criterios_qa.md`, sem revelar ao revisor qual variante gerou cada resposta. Preencha a ficha do roteiro.
6. Faça uma cópia privada de `medicoes.pendente.json` e preencha as medições revisadas. Os fingerprints de workload e avaliação já estão calculados; **identity_fingerprint e runtime_fingerprint estão null de propósito** e precisam ser estabelecidos pelos manifestos reais descritos no roteiro. O arquivo pendente não passa no contrato da CLI; isso impede comparação prematura.
7. Somente após revisar a equivalência, executar o comparador conforme o roteiro. Não alterar fingerprints apenas para fazer duas execuções diferentes passarem na validação.

## Integridade e limites

`integridade.json` contém SHA-256 e tamanho dos dois pacotes, critérios e manifesto congelados. Não inclui o próprio índice, este LEIA-ME ou a ficha editável. Tamanho em bytes não é medição de tokens. Hash não autentica autoria nem comprova equivalência do runtime.

Nenhum número de consumo foi inventado. Os pacotes são experimento de seleção manual, não teste end-to-end do Governor, do Broker ou de produção. As cópias das fontes são fixtures congeladas, não documentação canônica nem código para importar. Não sincronizá-las quando o código evoluir: uma nova revisão do experimento precisa de novo kit.

Resultados/evidências de execução devem ficar em local privado e fora de commits. Não compartilhar logs com segredos ou dados empresariais. Este piloto não autoriza calls pagas extras, testes com banco, deploy ou alteração de configuração.
