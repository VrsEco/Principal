# SPEC — Arquitetura de Ofertas e Contrato Operacional Versus v1

**Classificação:** SPEC  
**Status:** Oficial para implementação  
**Data-base:** 2026-09-03  
**Empresa inicial:** Versus Gestão Corporativa (`company_id=9`)  
**Paper de origem:** `app32/docs/papers/paper_reestruturacao_integrada_versus_v1.md`  

## 1. Decisão oficial

A arquitetura comercial da Versus terá:

1. dois trilhos metodológicos: **Necessidade Urgente** e **Estruturação Empresarial**;
2. **Diagnóstico inicial / Fase 00** como mecanismo de qualificação e entrada;
3. **Performance Hub** como modelo recorrente de sustentação e operação assistida;
4. **Business Review** como registro do valor agregado, nunca como produto isolado.

O ICP prioritário é formado por PMEs que precisam **crescer com controle** ou **conduzir um ciclo de adequação com eficiência e preservação de valor**, especialmente quando a complexidade da operação começa a superar a capacidade atual de acompanhamento e controle dos gestores.

## 2. Princípios obrigatórios

- oferta comercial não cria um terceiro trilho metodológico;
- produto contratado precisa apontar para capacidade real de entrega;
- promessa, escopo, entregável, aceite, processo, indicador e valor devem formar uma cadeia rastreável;
- alteração futura do produto não pode mudar silenciosamente o contrato já assinado;
- toda leitura e escrita deve respeitar `company_id`;
- IA e squads podem analisar e recomendar; preço, promessa sensível, aceite e decisão final permanecem sob gate humano;
- nenhum resultado financeiro, operacional ou de maturidade pode ser prometido sem premissas e evidência.

## 3. Arquitetura do catálogo

O catálogo atual do APP32 suporta três níveis: Grupo, Subgrupo e Item contratável. Para preservar o código já utilizado pelo Performance Hub, a estrutura inicial da Versus será:

| Código | Nível | Nome | Contratável | Papel |
|---|---|---|---|---|
| `1` | Grupo | Soluções Versus | não | raiz comercial |
| `1.01` | Subgrupo | Sustentação Recorrente | não | organização do modelo recorrente |
| `1.01.001` | Item | Performance Hub | sim | sustentação e operação assistida |
| `1.02` | Subgrupo | Necessidades Urgentes | não | primeiro trilho metodológico |
| `1.02.001` | Item | Intervenção de Necessidade Urgente | sim | projeto ou programa para dor específica |
| `1.03` | Subgrupo | Estruturação Empresarial | não | segundo trilho metodológico |
| `1.03.001` | Item | Diagnóstico Inicial — Fase 00 | sim quando remunerado | qualificação aprofundada e priorização |
| `1.03.002` | Item | Programa de Estruturação Empresarial | sim | estruturação faseada com gates |

### 3.1 Regras de compatibilidade

- o registro existente `1.01.001 — Performance Hub` deve manter `id` e código;
- os contratos ativos não serão recriados nem terão preço, período ou cobrança alterados;
- a implantação criará os níveis pais ausentes e vinculará o item existente ao subgrupo `1.01`;
- itens contratuais existentes sem vínculo ao catálogo serão saneados individualmente, com releitura posterior;
- Diagnóstico gratuito não gera contrato; Diagnóstico remunerado utiliza `1.03.001`;
- Business Review não entra no catálogo.

## 4. Contrato operacional da oferta

Cada item contratável deverá possuir um `commercial_contract_v1` validado. O contrato define o que a Versus pode vender e comprovar antes de existir um contrato com um cliente.

### 4.1 Campos obrigatórios

| Campo | Função |
|---|---|
| `version` | versão imutável do contrato da oferta |
| `status` | `draft`, `validated`, `active` ou `retired` |
| `offer_role` | `qualification`, `canonical_offer` ou `sustainment` |
| `method_track` | `urgent_need`, `business_structuring` ou nulo |
| `icp_summary` | público e condição de aderência |
| `buying_triggers` | situações que justificam a compra |
| `exclusion_criteria` | situações que impedem ou despriorizam a oferta |
| `sponsor_required` | papel com poder de patrocínio e decisão |
| `required_participants` | pessoas e áreas exigidas do cliente |
| `problem_statement` | problema que a oferta trata |
| `promised_outcome` | transformação esperada, sem garantia indevida |
| `scope_in` | escopo incluído |
| `scope_out` | exclusões e limites |
| `deliverables` | entregáveis com critério de aceite |
| `client_dependencies` | dados, agenda, pessoas e decisões do cliente |
| `versus_capabilities` | capacidade e papéis necessários da Versus |
| `execution_model` | `project`, `program` ou `recurring` |
| `process_links` | processos responsáveis pela venda, implantação e entrega |
| `indicator_contract` | indicadores mínimos da oferta |
| `business_review_policy` | quando e como registrar valor agregado |
| `closure_criteria` | condições para encerramento ou renovação |
| `evidence_requirements` | provas necessárias para comunicar resultados |
| `pricing_policy` | regra de formação e aprovação, sem expor informação desnecessária |
| `approved_by_user_id` | aprovador humano |
| `approved_at` | data da aprovação humana |

### 4.2 Estruturas internas

Cada item de `deliverables` deve conter:

- `key`;
- `name`;
- `description`;
- `acceptance_criterion`;
- `evidence_type`;
- `responsible_role`.

Cada item de `process_links` deve conter:

- `process_id` da mesma empresa;
- `role`: `market`, `sales`, `implementation`, `delivery`, `support` ou `review`;
- `required`;
- `owner_verified_at`.

Cada item de `indicator_contract` deve conter:

- `indicator_key`;
- `name`;
- `purpose`;
- `frequency`;
- `responsible_role`;
- `target_rule` ou justificativa para ainda não possuir meta;
- `source`.

## 5. Snapshot contratual

Ao inserir uma oferta em um contrato de cliente, o APP32 deverá copiar para `ContractItem.metadata_json`:

- `catalog_item_id`;
- `catalog_item_code`;
- `commercial_contract_version`;
- resumo de escopo e entregáveis;
- critérios de aceite;
- dependências do cliente;
- política de Business Review;
- data e usuário da materialização.

Esse snapshot é imutável para a versão contratada. Mudança posterior exige aditivo, renovação ou nova versão do contrato, preservando a rastreabilidade.

## 6. Contrato por oferta

### 6.1 Intervenção de Necessidade Urgente

**Modelo:** projeto ou programa de projetos.

Obrigatórios:

- dor e consequência identificadas;
- patrocinador e responsável do projeto;
- escopo, prazo, entregáveis e aceite;
- dependências técnicas ou profissionais externos;
- indicadores de prazo, entrega, esforço e resultado;
- vínculo do projeto/programa à classificação de Necessidade Urgente;
- Business Review antes do encerramento, com necessidade, solução, resultado e valor agregado.

### 6.2 Diagnóstico Inicial — Fase 00

**Modelo:** etapa de qualificação; contrato somente quando remunerada.

Obrigatórios:

- contexto e evidências disponíveis;
- dores, riscos, restrições e capacidade de mobilização;
- classificação preliminar entre Necessidade Urgente e Estruturação Empresarial;
- prioridades e plano recomendado;
- premissas, limitações e itens ainda não auditados;
- decisão humana sobre continuidade.

O diagnóstico não pode declarar maturidade apenas pela existência de cadastros.

### 6.3 Programa de Estruturação Empresarial

**Modelo:** programa faseado.

Obrigatórios:

- frentes contratadas e estágio inicial;
- fases e gates aplicáveis;
- projetos de implantação e treinamento;
- processos, responsáveis e indicadores vinculados;
- estabilização baseada em três ciclos dentro das faixas de controle, auditados pela Versus;
- inclusão no ciclo de auditoria quando aplicável;
- Business Review quando houver resultado e valor comprováveis, no encerramento de projeto, fase ou intervenção relevante.

### 6.4 Performance Hub

**Modelo:** sustentação recorrente.

Obrigatórios:

- capacidade mensal contratada e regras de priorização;
- cadências de acompanhamento e decisão;
- papéis do consultor, cliente, Squad Cliente, Squad Versus e Squad Engenharia;
- itens que podem ser conduzidos dentro do Hub e itens que exigem contratação adicional;
- indicadores de capacidade, execução, prazo, aceite, satisfação e resultado;
- regra de renovação, redimensionamento e encerramento;
- Business Review sempre que um resultado mensurável for consolidado, sem fabricar valor quando ainda não houver evidência.

## 7. Vínculo com processos da Versus

Na implantação para `company_id=9`, as ofertas deverão ser vinculadas, no mínimo, aos processos equivalentes a:

- Desenvolvimento de Mercados;
- Desenvolvimento de Produtos;
- Gerir Marketing Digital;
- Gerir Vendas;
- Gerir Operações Próprias;
- Relacionamento com Clientes;
- Gerir Projetos;
- Gerir Processos;
- Gerir Indicadores;
- Business Review ou processo responsável pelo registro de valor.

O vínculo deve usar `process_id` real da empresa. Nome de processo é referência humana e não substitui chave canônica.

## 8. Indicadores mínimos

### 8.1 Comuns

- aderência ao ICP;
- conversão por oferta e motivo de perda;
- tempo de venda e tempo até o início;
- margem prevista e realizada;
- utilização da capacidade;
- entregáveis aceitos no prazo;
- retrabalho;
- satisfação e continuidade;
- Business Reviews concluídos e valor agregado comprovado.

### 8.2 Específicos

- **Necessidade Urgente:** tempo de resposta, risco controlado, prazo e reincidência da causa;
- **Estruturação Empresarial:** avanço por gate, implantação, treinamento, estabilidade e auditoria;
- **Performance Hub:** cadência cumprida, prioridades concluídas, capacidade consumida e decisões executadas;
- **Fase 00:** tempo de diagnóstico, qualidade da evidência e conversão responsável para o trilho adequado.

## 9. Gates

### 9.1 Ativação da oferta

Uma oferta somente pode assumir `status=active` quando:

1. o contrato operacional estiver completo;
2. os processos obrigatórios e seus donos estiverem confirmados;
3. houver capacidade mínima de entrega;
4. entregáveis e critérios de aceite estiverem definidos;
5. indicadores e política de Business Review estiverem definidos;
6. preço e margem tiverem aprovação humana;
7. a comunicação pública possuir evidência compatível.

### 9.2 Proposta e contratação

- proposta não pode selecionar item `draft`, `retired` ou sem contrato operacional válido;
- exceção exige justificativa e aprovação humana registrada;
- contrato deve preservar o snapshot da oferta;
- alteração sensível exige nova versão.

### 9.3 Entrega e encerramento

- entrega exige evidência de aceite;
- Necessidade Urgente não encerra sem Business Review;
- Estruturação não declara estabilidade sem três ciclos auditados;
- Hub não renova automaticamente por falta de decisão registrada;
- resultado não comprovado permanece como hipótese ou pendência.

## 10. Papéis dos quatro pilares

| Pilar | Responsabilidade no contrato operacional |
|---|---|
| Forma de Trabalho | trilho, fases, gates, entregáveis, aceite e estabilização |
| Ferramenta | catálogo, contrato, projetos, processos, indicadores, evidências e Business Review no APP32 |
| Agentes | análise, pesquisa, preparação, validação e recomendação dentro de permissões explícitas |
| Orquestração | próxima ação, handoff, gate humano, capacidade, cadência e rastreabilidade ponta a ponta |

## 11. Impacto técnico no APP32

### 11.1 Reuso obrigatório

- `ContractCatalogItem` continua sendo o objeto canônico da oferta;
- `Contract` e `ContractItem` continuam sendo os objetos canônicos da contratação;
- Projeto, Programa, Processo, Indicador e Business Review permanecem objetos canônicos de execução e evidência;
- não será criado um módulo comercial paralelo.

### 11.2 Evoluções necessárias

1. permitir `commercial_contract_v1` estruturado em `ContractCatalogItem.metadata_json`;
2. preservar objetos e listas nesse campo, pois a normalização atual converte metadados em texto e aceita somente dados fiscais;
3. validar o contrato por schema próprio antes de ativar a oferta;
4. criar editor operacional com seções progressivas e boa usabilidade;
5. materializar snapshot em `ContractItem` na contratação;
6. criar vínculos tenant-safe entre oferta e processos/indicadores;
7. publicar tools MCP de leitura e escrita governada, com gate humano para ativação;
8. exibir prontidão da oferta sem confundir preenchimento com capacidade comprovada;
9. criar migração/backfill idempotente para `company_id=9`, preservando contratos ativos.

## 12. Segurança e multi-tenancy

- todas as consultas e mutações exigem `company_id`;
- `catalog_item_id`, `process_id`, `indicator_id`, contrato e projeto devem pertencer à mesma empresa;
- nenhum ID recebido do cliente pode ser usado sem filtro de tenant;
- ativação, preço, margem, promessa sensível e publicação de case exigem usuário autorizado;
- escrita MCP deve reler o objeto e registrar auditoria;
- ferramentas de análise não recebem permissão implícita de alterar oferta ou contrato.

## 13. Critérios de aceite da implementação

1. hierarquia do catálogo criada sem mudar ID/código do Performance Hub;
2. contratos atuais continuam legíveis, faturáveis e sem alteração econômica;
3. quatro itens comerciais aparecem nas posições corretas;
4. contrato operacional inválido impede ativação;
5. proposta e contrato usam somente item ativo e contratável;
6. snapshot preserva a versão vendida;
7. vínculos entre ofertas e processos rejeitam tenant crossing;
8. gates humanos são auditáveis;
9. testes cobrem criação, atualização, ativação, snapshot, legado e isolamento;
10. smoke local comprova catálogo, contrato e MCP sem regressão.

## 14. Fora de escopo desta versão

- alteração do site e campanhas;
- definição final de preços;
- publicação de cases;
- especialização setorial do ICP;
- migração automática de contratos sem revisão;
- promessa automática de ROI;
- deploy em produção.

## 15. Ordem de implementação

1. schema e validação de `commercial_contract_v1`;
2. compatibilidade do catálogo e backfill seguro do Performance Hub;
3. editor e leitura da prontidão da oferta;
4. snapshot no contrato;
5. vínculos com processos e indicadores;
6. tools MCP e auditoria;
7. testes tenant-safe e smoke local;
8. homologação humana antes de qualquer deploy.
