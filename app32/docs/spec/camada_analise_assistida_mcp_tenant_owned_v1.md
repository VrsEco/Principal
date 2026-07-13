# SPEC — Camada de Análise Assistida via MCP Tenant-Owned

**Classe documental:** SPEC  
**Status:** Decisão oficial v1  
**Data:** 2026-07-01  
**Origem:** `app32/docs/papers/paper_metodo_versus_estruturacao_evolutiva_v1.md`, seção 12.5  
**Escopo:** Cockpit do Consultor, Método Versus, MCP, Squad Cliente, Squad Versus, Squad de Engenharia, agentes e custos de IA

---

## 1. Decisão

A camada de análise assistida da Estruturação Empresarial deve ser **MCP-first** e **tenant-owned**.

Isso significa:

- o APP32 não deve, por padrão, consumir tokens próprios da Versus para análises amplas de IA do cliente;
- o cliente deve ser o responsável por capacidade, tokens, provedor, limite de uso e custo da IA quando acionar análises assistidas;
- a Versus deve fornecer método, contexto estruturado, ferramentas MCP, governança, validação e apoio dos squads;
- o MCP deve ser a ponte oficial entre a IA utilizada pelo cliente e a verdade operacional registrada no APP32.

A regra central é:

> **A IA do cliente analisa; o MCP ancora na verdade operacional; Squad Cliente valida contexto; Squad Versus valida método; o consultor aprova a decisão.**

---

## 2. Objetivo

Organizar a análise assistida do Cockpit do Consultor sem transferir para a Versus, de forma automática, o custo computacional da IA.

A SPEC define:

1. responsabilidades por custo, token, capacidade e governança;
2. papel do MCP como superfície de contexto tenant-safe;
3. papéis de Squad Cliente, Squad Versus e Squad de Engenharia;
4. fluxo de análise assistida nas quatro frentes;
5. contrato mínimo das MCP tools;
6. critérios de aceite e anti-padrões.

---

## 3. Princípios

### 3.1. Cliente dono do consumo de IA

Quando a análise exigir IA generativa, pesquisa ampla, síntese longa, benchmarking ou execução agentic externa, o consumo deve estar vinculado ao ambiente, token, plano, conector ou provedor autorizado pelo cliente.

O APP32 pode facilitar a experiência, mas não deve mascarar quem paga e quem autoriza o consumo.

### 3.2. MCP como fonte operacional

A IA não deve receber contexto por cópia manual, planilha paralela ou exportação solta quando o dado já existir no APP32.

O MCP deve expor ferramentas que entreguem:

- contexto da empresa;
- evidências por frente;
- gaps;
- recomendações metodológicas iniciais;
- objetos canônicos vinculados;
- decisões e registros anteriores;
- Business Reviews;
- projetos, processos, indicadores e reuniões relacionados.

Tudo sempre com `company_id`, permissões e menor privilégio.

### 3.3. IA recomenda, humano decide

Nenhuma análise assistida deve virar decisão final sem gate humano.

A cadeia de validação mínima é:

1. IA gera análise ou sugestão;
2. Squad Cliente valida realidade operacional;
3. Squad Versus valida aderência metodológica;
4. consultor ou responsável autorizado aprova, ajusta ou rejeita;
5. APP32 registra decisão, evidência e próximo passo.

### 3.4. Pesquisa externa é subsídio consultivo

Benchmarks, boas práticas e pesquisas na internet alimentam a Camada Consultiva/Evolutiva.

Eles não substituem:

- dados reais do APP32;
- evidências internas;
- decisões do cliente;
- leitura do consultor;
- restrições operacionais da empresa.

---

## 4. Papéis e responsabilidades

### 4.1. Cliente / tenant

Responsável por:

- autorizar uso da IA;
- prover token, conector, plano ou capacidade computacional quando aplicável;
- aceitar custos de processamento, pesquisa e geração;
- validar limites de dados enviados ao provedor de IA;
- decidir quais frentes deseja aprofundar.

### 4.2. APP32

Responsável por:

- expor contexto tenant-safe via MCP;
- registrar análises, decisões, fontes e evidências;
- preservar rastreabilidade entre análise e objetos canônicos;
- aplicar permissões, `company_id`, surfaces e human gate;
- não executar mutações operacionais críticas sem autorização explícita.

### 4.3. MCP

Responsável por:

- servir como interface oficial entre IA externa/autorizada pelo cliente e APP32;
- limitar ferramentas por surface, permissão e empresa;
- entregar contexto estruturado, não dumps indiscriminados;
- permitir registro de recomendações e decisões;
- auditar quem solicitou, quando solicitou e em qual empresa.

### 4.4. Squad Cliente

Responsável por:

- complementar contexto operacional;
- identificar se a análise entendeu corretamente a realidade;
- apontar restrições práticas;
- validar linguagem, viabilidade e aderência ao cotidiano da empresa.

### 4.5. Squad Versus

Responsável por:

- validar aderência ao Método Versus;
- qualificar maturidade, prioridade, risco e próximos passos;
- transformar sugestão em plano consultivo;
- apoiar o consultor na decisão final.

### 4.6. Squad de Engenharia

Responsável por:

- validar se o APP32/MCP possui dados suficientes para a análise;
- identificar gaps técnicos, modelagem, API, read model e automação;
- propor ajustes quando a ferramenta não representar bem a realidade;
- proteger segurança, performance e multi-tenancy.

### 4.7. Consultor Versus

Responsável por:

- conduzir o processo metodológico;
- aprovar, ajustar ou rejeitar a recomendação;
- decidir se a saída vira projeto, processo, revisão, Business Review, maturação ou registro;
- preservar o gate humano.

---

## 5. Fluxo oficial

1. Consultor abre uma frente no Cockpit do Consultor.
2. APP32 apresenta evidências internas e maturidade inicial.
3. Usuário autorizado aciona análise assistida via MCP.
4. A IA do cliente consulta as tools MCP permitidas.
5. MCP entrega contexto estruturado e tenant-safe.
6. IA gera análise, benchmark, síntese ou recomendação.
7. Squad Cliente valida realidade operacional.
8. Squad Versus valida método e prioridade.
9. Squad de Engenharia aponta gaps técnicos quando necessário.
10. Consultor aprova, ajusta ou rejeita.
11. APP32 registra decisão, evidências, fontes, próximos passos e vínculos.

---

## 6. Frentes atendidas

A análise assistida deve atuar dentro das quatro frentes oficiais do Cockpit:

1. **Identidade Organizacional**
   - missão;
   - visão;
   - valores;
   - posicionamento;
   - organograma.

2. **Processos**
   - arquitetura;
   - modelagem;
   - implantação;
   - estabilização;
   - auditoria.

3. **Planejamento Estratégico**
   - estruturado;
   - conectado;
   - desdobrado;
   - vinculado ao Gerenciamento Estratégico.

4. **Gerenciamento Estratégico**
   - indicadores;
   - ciclos;
   - incentivos;
   - teia de conexões.

---

## 7. Contrato mínimo de MCP tools

A camada deve nascer com tools conceituais equivalentes a:

### 7.1. Leitura

- `consultive_get_front_context`
  - Entrada: `company_id`, `front_key`.
  - Saída: contexto resumido da frente, maturidade, subfases e vínculos principais.

- `consultive_get_front_evidence`
  - Entrada: `company_id`, `front_key`.
  - Saída: evidências internas, fonte do dado, data e objeto canônico relacionado.

- `consultive_get_front_gaps`
  - Entrada: `company_id`, `front_key`.
  - Saída: lacunas metodológicas e técnicas já identificadas.

- `consultive_get_methodology_guidance`
  - Entrada: `front_key`, `subphase_key` opcional.
  - Saída: orientação oficial do Método Versus para a frente/subfase.

- `consultive_resolve_protocol`
  - Entrada: `front_key`, `subphase_key` opcional, `audience`, `depth_level` opcional.
  - Saída: protocolo ativo tenant/global/fallback para orientar a IA/CLI.
  - Regra: quando `subphase_key` não for informado, deve retornar o **roteiro MCP da frente completa**; quando informado, deve retornar o protocolo específico da subfase.

### 7.1.1. Roteiros MCP obrigatórios das quatro frentes

A camada assistida deve expor roteiros de frente completa para:

1. `identity` — Missão, Visão, Valores, Posicionamento e Organograma.
2. `processes` — Arquitetura, Modelagem, Implantação, Estabilização e Auditoria.
3. `growth_plan` — Estruturado, Conectado, Desdobrado e Vinculado à gestão.
4. `strategic_management` — Indicadores, Ciclos, Incentivos e Teia de Conexões.

Cada roteiro deve conter:

- objetivo da frente;
- subfases consideradas;
- camadas de investigação;
- tools MCP esperadas;
- papel do Squad Cliente, Squad Versus e Squad Engenharia;
- instrução explícita de pesquisa profunda/benchmarking quando aplicável;
- saída esperada e gate humano obrigatório.

### 7.2. Registro

- `consultive_register_assisted_analysis`
  - Registra síntese gerada pela IA, prompt/resumo, fontes, custo estimado quando informado, responsável e contexto.

- `consultive_register_squad_validation`
  - Registra validação do Squad Cliente, Squad Versus ou Squad de Engenharia.

- `consultive_register_consultant_decision`
  - Registra aprovação, ajuste ou rejeição pelo consultor.

### 7.3. Conversão em ação

- `consultive_create_recommended_action`
  - Converte recomendação aprovada em projeto, atividade, revisão de processo, maturação, Business Review ou follow-up.

Nenhuma tool de conversão deve executar mutação relevante sem autorização e rastreabilidade.

---

## 8. Superfície no APP32

Nas telas de frente consultiva, a seção deve ser chamada:

> **Análise Assistida via MCP**

Ela deve mostrar no mínimo:

- contexto disponível para o MCP;
- botão ou instrução para acionar IA do cliente;
- análise gerada/importada;
- fontes internas e externas;
- validação Squad Cliente;
- validação Squad Versus;
- apontamentos do Squad de Engenharia;
- decisão do consultor;
- ação resultante.

A UI deve deixar explícito que:

- o consumo de IA é responsabilidade do cliente quando executado por conector/token do cliente;
- a Versus fornece método e governança;
- a decisão final é humana.

---

## 9. Dados mínimos de uma análise assistida

Cada análise registrada deve conter:

- `company_id`;
- frente (`front_key`);
- subfase, se houver;
- solicitante;
- provedor/conector de IA, quando informado;
- data/hora;
- pergunta ou objetivo;
- contexto MCP utilizado;
- evidências internas consultadas;
- fontes externas, quando houver;
- síntese da IA;
- riscos e limitações;
- validação Squad Cliente;
- validação Squad Versus;
- validação Squad Engenharia, quando aplicável;
- decisão do consultor;
- próximo passo;
- vínculo com objeto canônico ou Business Review, quando aplicável.

---

## 10. Segurança, privacidade e custo

### 10.1. Segurança

- Toda tool deve respeitar `company_id`.
- Toda tool deve passar por surface MCP adequada.
- Leitura ampla deve ser preferencialmente `analytics` ou surface consultiva equivalente, não mutação operacional.
- Mutação deve exigir autorização explícita e human gate.

### 10.2. Privacidade

- O cliente deve saber que contexto pode ser enviado para a IA utilizada por ele.
- Dados sensíveis devem ser minimizados.
- O MCP deve expor contexto necessário, não base completa sem recorte.

### 10.3. Custo

- Custos de IA acionada com token/conector do cliente pertencem ao cliente.
- A Versus pode oferecer assistência, templates, prompts e validação, mas não assume consumo ilimitado por padrão.
- Quando a Versus executar análise com infraestrutura própria, isso deve ser tratado como serviço, pacote ou exceção explicitamente aprovada.

---

## 11. Anti-padrões proibidos

1. APP32 consumir IA da Versus de forma invisível ao cliente para análises extensas.
2. IA tomar decisão sem gate humano.
3. Enviar dados sensíveis para IA externa sem autorização clara.
4. Permitir MCP tool sem `company_id` em contexto de empresa.
5. Usar benchmark externo como verdade superior à operação real.
6. Registrar recomendação sem fonte, evidência ou responsável.
7. Criar módulo de agentes separado e desconectado das frentes do Cockpit.
8. Permitir que Squad Cliente aprove método sem validação Versus quando houver decisão metodológica.
9. Permitir que Squad Versus ignore restrições operacionais validadas pelo cliente.
10. Converter recomendação em projeto/processo/Business Review sem rastreabilidade.

---

## 12. Critérios de aceite

A arquitetura estará aderente quando:

1. as quatro frentes do Cockpit tiverem seção de Análise Assistida via MCP;
1.1. cada frente expuser roteiro MCP de frente completa e protocolos específicos por subfase;
2. o contrato de tools separar leitura, registro e conversão em ação;
3. o cliente puder usar sua própria IA/token/conector;
4. o APP32 registrar análise, validações, decisão e próximos passos;
5. o MCP limitar contexto por `company_id` e permissão;
6. Squad Cliente, Squad Versus e Squad de Engenharia tiverem papéis explícitos;
7. a decisão final depender de consultor ou responsável autorizado;
8. custos e limites de IA estiverem transparentes para o cliente;
8.1. pesquisa profunda e benchmarking estiverem orientados por protocolo e registrados com fontes/limitações;
9. benchmarks externos forem tratados como subsídio consultivo;
10. não houver duplicidade entre Objeto Canônico e Camada Consultiva/Evolutiva.

---

## 13. Decisão final

A análise assistida da Versus no APP32 não será desenhada como uma automação central em que a Versus assume silenciosamente tokens, custos e capacidade de IA para todos os clientes.

Ela será desenhada como uma **camada MCP-first, tenant-owned e human-gated**:

- o cliente controla o consumo da IA;
- o APP32 fornece contexto e registro;
- o MCP protege a fronteira técnica;
- os squads qualificam a análise;
- o consultor decide.

Essa decisão preserva escalabilidade, transparência de custos, segurança, governança e aderência ao Método Versus.
