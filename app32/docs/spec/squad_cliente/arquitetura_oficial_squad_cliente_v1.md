# Arquitetura Oficial do Squad Cliente v1

Status: oficial  
Escopo: `Sapiens Cliente`, `Squad Cliente`, agentes oficiais iniciais, surface principal, fronteiras, economia de tokens e regras de escalonamento

## 1. Objetivo

Definir a arquitetura oficial do `Squad Cliente` no APP32 / Gestão Versus, consolidando a passagem dos papers conceituais para a camada canônica de SPEC.

Esta SPEC congela a leitura oficial de:
- `Sapiens Cliente`
- `Squad Cliente`
- agentes iniciais do cliente
- relação com `Harnesses`
- relação com `Squad Versus`
- relação com `Squad de Engenharia`
- economia de tokens como princípio transversal

---

## 2. Leitura oficial em camadas

A leitura oficial do ecossistema do cliente é:

- `Sapiens Cliente` = experiência / front door visível ao usuário
- `Squad Cliente` = família canônica de agentes do cliente
- `Agentes` = papéis funcionais de negócio
- `Harnesses` = invólucros operacionais dos agentes no runtime
- `APP32` = plataforma operacional, domínio, dados, services, MCP, governança e auditoria

### Regra oficial
`Sapiens Cliente` não é um agente isolado.  
`Squad Cliente` não é um harness isolado.  
`Agente` e `Harness` não podem ser confundidos.

---

## 3. Missão oficial do Squad Cliente

O `Squad Cliente` existe para atuar como copiloto operacional do cliente no uso do APP32, ajudando-o a:

- entender a demanda
- navegar melhor o sistema
- organizar a ação
- apoiar a execução do dia a dia
- apoiar decisões operacionais e comerciais do contexto atual

### Limites oficiais
O `Squad Cliente` não existe para:
- substituir consultoria estrutural da Versus
- substituir o `Squad de Engenharia`
- operar livremente temas financeiros sensíveis
- transformar toda demanda simples em deliberação cara

---

## 4. Runtime e boundary operacional

## 4.1 Runtime preferencial
O `Squad Cliente` opera prioritariamente em runtime externo / CLI do cliente, consumindo o APP32 via MCP.

## 4.2 Plataforma base
O APP32 permanece como:
- núcleo de domínio
- fonte de dados
- provedor MCP
- camada de governança
- camada de auditoria

## 4.3 Multi-tenancy
Toda operação do `Squad Cliente` deve respeitar:
- `company_id` explícito ou resolvido de forma segura
- isolamento tenant a tenant
- escopo de usuário compatível com o perfil autenticado

## 4.4 Compatibilidade oficial com Claude Desktop (Windows)
O `Squad Cliente` é oficialmente compatível com `Claude Desktop (Windows)` quando a conexão MCP for instalada localmente com:

- `npx.cmd`
- pacote `mcp-remote`
- arquivo `claude_desktop_config.json`
- Bearer Token pessoal do APP32

### Regra
Nesta variante, o Claude Desktop consome o APP32 por proxy local STDIO → MCP remoto HTTP.
Não tratar este fluxo como conector remoto OAuth puro do Claude.

### Ativação oficial
Quando a experiência usar `Claude Desktop / Claude Code`, a ativação oficial deve preferir comandos slash instalados localmente, por exemplo:

- `/sapiens-cliente-on`
- `/sapiens-on`

Texto livre como `sapiens on` não constitui comando oficial instalado.

---

## 5. Surface oficial

## 5.1 Surface principal
A surface principal do `Squad Cliente` é:
- `user`

## 5.2 Regra de boundary
O `Squad Cliente` deve preferir a menor surface necessária para resolver a demanda com segurança.

## 5.3 Consequência prática
O `Squad Cliente` não deve depender por padrão de:
- `admin`
- `analytics`
- `ops`

Qualquer transição para contextos mais sensíveis deve ocorrer por escalonamento apropriado, nunca como atalho rotineiro.

---

## 6. Agentes oficiais da fase 1

A família inicial oficial do `Squad Cliente` é composta por:

- `SC-COORD` — Agente Líder / Coordenador
- `SC-COM` — Agente Comercial
- `SC-OPS` — Agente Operacional
- `SC-ADM` — Agente Administrativo / Financeiro

### Regra oficial da fase 1
Estes quatro agentes compõem a base canônica do `Squad Cliente` em v1.

### Fora do escopo oficial desta SPEC v1
Permanecem fora da família oficial congelada desta SPEC:
- `estrategico_cliente`
- `pessoas_capacidade_cliente`

Esses papéis ficam reservados para avaliação em fase posterior.

---

## 7. Princípio transversal de economia de tokens

## 7.1 Princípio oficial
O `Squad Cliente` deve operar sob a seguinte regra:

> resolver o máximo com o menor custo cognitivo e computacional possível, sem sacrificar segurança, governança e qualidade mínima necessária.

## 7.2 Consequências obrigatórias
O `Squad Cliente` deve:
- responder diretamente quando for seguro
- preferir um único especialista quando o domínio estiver claro
- evitar multiagente sem justificativa real
- evitar contextualização excessiva para demandas simples
- evitar relatórios longos quando uma síntese acionável bastar

## 7.3 Exceção formal
O `Squad de Engenharia` não segue esta premissa como prioridade principal, pois nele a prioridade dominante é excelência técnica.

---

## 8. Precedência interna oficial

## 8.1 Porta de entrada
Toda demanda do `Squad Cliente` entra por:
- `SC-COORD`

## 8.2 Resolução preferencial
A ordem preferencial de atuação é:
1. resposta direta do `SC-COORD`, se segura
2. delegação para um único especialista
3. coordenação entre múltiplos especialistas, se justificado
4. `Modo Conselho`, apenas em casos de alto custo de erro ou incerteza relevante

## 8.3 Regra de custo
Orquestração expandida é exceção.  
Simplicidade operacional é o default.

---

## 9. Relação oficial entre os especialistas

## 9.1 `SC-COM`
Responsável por mercado, carteira, funil, propostas, negociação, preço e rentabilidade comercial.

## 9.2 `SC-OPS`
Responsável por rotina, backlog, tarefas, projetos, cadência e execução assistida.

## 9.3 `SC-ADM`
Responsável por organização administrativa, leitura financeira operacional segura, alertas, vencimentos, inadimplência e preparação de contexto administrativo/financeiro.

## 9.4 Regra de separação
- `SC-COM` não substitui `SC-OPS`
- `SC-OPS` não substitui `SC-COM`
- `SC-ADM` não substitui operador financeiro pleno
- colaboração entre especialistas é permitida quando houver interdependência real, sem colapsar os papéis

---

## 10. Fronteiras sensíveis

## 10.1 Financeiro sensível
O `Squad Cliente`, em especial via `SC-ADM`, não deve operar livremente:
- pagamentos
- aprovações financeiras sensíveis
- credenciais bancárias
- mutações financeiras sem gate apropriado
- compromissos fiscais formais de alto risco

## 10.2 Governança
Temas de:
- estratégia
- método
- governança
- redesenho estrutural
- controladoria estrutural

não pertencem por padrão ao `Squad Cliente` e devem ser escalados quando ultrapassarem a operação local.

---

## 11. Relação com o Squad Versus

O `Squad Cliente` deve escalar para o `Squad Versus` quando a demanda sair da operação local e entrar em:
- estratégia
- posicionamento
- revisão de portfólio
- método
- governança
- controladoria estrutural
- revisão estrutural de processo

### Regra curta
O `Squad Cliente` ajuda a operar melhor o contexto atual.  
O `Squad Versus` ajuda a redesenhar o contexto quando ele deixa de servir.

---

## 12. Relação com o Squad de Engenharia

O `Squad Cliente` deve escalar para o `Squad de Engenharia` quando houver:
- erro técnico
- defeito de módulo
- falha de integração
- problema de MCP
- limitação estrutural do APP32
- necessidade de investigação técnica profunda

### Regra curta
Problema de negócio fica no `Squad Cliente`.  
Problema técnico sobe para o `Squad de Engenharia`.

---

## 13. Relação com Harnesses

Cada agente oficial do `Squad Cliente` deve possuir um harness correspondente, responsável por:
- startup operacional
- prompt-base
- superfície e guardrails
- preferências de tool use
- regras de escalonamento

### Mapeamento esperado na fase 1
- `SC-COORD` -> `harness_coordenador_cliente_v1`
- `SC-COM` -> `harness_comercial_cliente_v1`
- `SC-OPS` -> `harness_operacional_cliente_v1`
- `SC-ADM` -> `harness_admfin_cliente_v1`

Esta SPEC não congela os detalhes dos harnesses; congela apenas o vínculo canônico entre agente e invólucro operacional.

---

## 13.1 Bootstrap operacional do runtime

O runtime externo do `Sapiens Cliente` não deve depender da leitura de SPECs longas para agir corretamente.

### Regra oficial
O APP32 deve expor um bootstrap operacional curto e executável do `Squad Cliente`, suficiente para orientar o CLI com:
- agente de entrada
- especialistas oficiais da fase 1
- ordem de roteamento
- regra de economia de tokens
- regra de escalonamento
- harnesses oficiais expostos ao runtime

### Tool oficial de bootstrap
- `describe_app32_squad_runtime_tool`

### Consequência prática
A SPEC continua sendo a fonte de verdade, mas o comportamento do runtime deve ser guiado pelo bootstrap operacional resumido e pelos harnesses correspondentes.

---

## 14. Modo Conselho

O `Modo Conselho` permanece, em v1, como protocolo especial em amadurecimento conceitual.

### Regra oficial
- não é agente permanente
- não é fluxo padrão
- não substitui o `SC-COORD`
- só pode ser usado quando o custo do erro ou a ambiguidade justificar

Referência conceitual:
- `C:\GestaoVersus\app32\app32\docs\papers\paper_conceitual_modo_conselho_squad_cliente_v1.md`

---

## 15. Critérios de conformidade desta SPEC

Uma implementação do `Squad Cliente` só é aderente a esta SPEC se:
- preservar a leitura `Sapiens -> Squad -> Agente -> Harness`
- operar prioritariamente na `surface user`
- respeitar `company_id` e multi-tenancy
- adotar economia de tokens como princípio transversal
- preservar os quatro agentes oficiais da fase 1
- manter `SC-COORD` como orquestrador leve
- manter `SC-ADM` como agente útil sem ser perigoso
- escalar corretamente para `Squad Versus` e `Squad de Engenharia`

---

## 16. Documentos de origem

Esta SPEC foi consolidada a partir de:
- `C:\GestaoVersus\app32\app32\docs\papers\paper_adaptacao_especificacao_squad_cliente_v1.md`
- `C:\GestaoVersus\app32\app32\docs\papers\paper_sc_coord_squad_cliente_v1.md`
- `C:\GestaoVersus\app32\app32\docs\papers\paper_sc_com_squad_cliente_v1.md`
- `C:\GestaoVersus\app32\app32\docs\papers\paper_sc_ops_squad_cliente_v1.md`
- `C:\GestaoVersus\app32\app32\docs\papers\paper_sc_adm_squad_cliente_v1.md`
- `C:\GestaoVersus\app32\app32\docs\papers\paper_consolidacao_agentes_iniciais_squad_cliente_v1.md`

---

## 17. Descoberta e modelagem de processos

O Squad Cliente usa `squad-cliente-descoberta-modelagem-processos` para levantar evidências e propor o AS-IS. `SC-OPS` conduz a descoberta e `SC-COORD` preserva o handoff.

Autonomia oficial:

- pode registrar realidade, exceções, gatilhos, saídas, executores e rascunho AS-IS;
- deve percorrer o AS-IS progressivamente do gatilho ao objetivo pelos pontos SIPOC e validá-lo regressivamente, registrando lacunas sem inventar o TO-BE;
- pode recomendar necessidade de POP, sem impor POP a toda atividade;
- não pode redefinir sozinho fronteira, TO-BE, método ou responsabilidade estrutural;
- não pode publicar BPMN nem validar em nome do Squad Versus;
- deve escalar redesenho e aprovação para `squad-versus-arquitetura-modelagem-processos`.
