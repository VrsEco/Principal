# SPEC — Motor de Maturidade Organizacional Versus v1

## 1. Decisão

O APP32 deve possuir um **núcleo único de maturação organizacional**, aplicável às quatro frentes da Estruturação Empresarial. Regras específicas ficam em protocolos versionados; não devem ser duplicadas no motor nem codificadas por cliente.

Esta SPEC trata da maturidade dos elementos organizacionais. Ela não substitui a especificação legada de maturidade de uso assistido, que avalia autonomia de consultores e usuários na interação com Squads e agentes.

## 2. Escopo

| Frente | Elementos abrangidos |
|---|---|
| Identidade Organizacional | entendimento da empresa, mercado e sócios; MVV; posicionamento; organograma; competências e capacidade organizacional |
| Processos | arquitetura; modelagem; SIPOC/riscos; BPMN; atividades; controles; responsabilidades; indicadores; checklists; formulários; POPs; implantação; estabilização; auditoria e melhoria |
| Planejamento Estratégico | implantação ou evolução; direcionadores; objetivos; OKRs; metas; iniciativas; conexões; priorização e desdobramento |
| Gerenciamento Estratégico | definição e monitoramento de indicadores; rotinas; Business Reviews; análise de desempenho; incentivos; decisões; ações corretivas e aprendizado |

## 3. Ciclo comum

Todo elemento percorre:

1. compreender;
2. discutir;
3. identificar gaps;
4. definir;
5. validar;
6. consolidar como vigente;
7. acompanhar alinhamento;
8. amadurecer novamente.

O ciclo é iterativo. Uma versão vigente pode ser reaberta para nova discussão sem perder seu histórico nem deixar de representar a última definição válida até que outra seja aprovada.

## 4. Estados

### 4.1 Estado do conteúdo

- `in_discussion` — **Em discussão**;
- `current` — **Vigente**;
- `discarded` — **Descartado**.

### 4.2 Estado de maturidade relativa

- `behind` — **Atrasado**;
- `aligned` — **Em linha com os demais**;
- `ahead` — **Adiantado**.

As duas classificações são independentes. Um conteúdo pode estar vigente e atrasado; em discussão e adiantado; ou vigente e em linha. `Adiantado` sinaliza desalinhamento potencial, não superioridade automática.

## 5. Registro mínimo do ciclo

Cada ciclo deve manter:

- `company_id` e elemento avaliado;
- protocolo e versão utilizados;
- estado do conteúdo e estado de maturidade relativa;
- histórico de discussões;
- evidências e respectivas origens;
- gaps encontrados;
- alternativas consideradas;
- definições aprovadas;
- itens descartados e justificativas;
- ideias ainda abertas;
- responsáveis e gates de validação;
- versão vigente resultante;
- dependências e impactos transversais;
- próxima ação recomendada.

Registros históricos são imutáveis para fins de auditoria. Correções produzem novo evento, versão ou ciclo, sem reescrever a fotografia metodológica anterior.

## 6. Protocolo por elemento

O protocolo contém:

1. perguntas orientadoras;
2. evidências mínimas;
3. critérios de qualidade;
4. dependências com outros elementos;
5. gaps verificáveis;
6. entregável esperado;
7. gates humanos;
8. critérios para vigência e reavaliação.

A resolução segue `tenant → global → fallback`. O protocolo tenant-owned pode adaptar nomenclatura e requisitos do cliente, mas não alterar estados, gates globais, isolamento multi-tenant ou regras canônicas sem decisão metodológica explícita.

## 7. Avaliação relacional

O motor não deve calcular maturidade apenas por completude cadastral ou nota isolada. Deve confrontar dependências entre elementos, incluindo:

- identidade versus estratégia;
- estratégia versus processos e capacidades;
- processos versus organograma, competências e controles;
- objetivos versus indicadores;
- indicadores versus dados e rotinas;
- incentivos versus comportamentos e resultados desejados.

O diagnóstico deve explicitar o desalinhamento, seu efeito provável na execução e a próxima decisão recomendada.

## 8. Relação com projetos

Gap não cria projeto automaticamente. Após validação humana, o tratamento pode ser:

- definição ou ajuste simples;
- ação operacional;
- projeto de implantação, correção ou melhoria.

O Gestor de Projetos administra o projeto. O Motor de Maturidade registra o vínculo, recebe evidências de execução e reavalia o elemento afetado.

## 9. Contrato de apresentação

A interface padrão deve priorizar:

1. onde a empresa está;
2. o que está vigente;
3. o que está em discussão;
4. gaps e desalinhamentos relevantes;
5. próxima decisão recomendada.

Discussões, evidências, eventos, versões e dependências permanecem acessíveis em detalhe, sem sobrecarregar a visão principal.

## 10. Guardrails

- `company_id` obrigatório em toda leitura e escrita operacional;
- MCP First para consumo por CLI, Squads e agentes;
- IA recomenda; responsáveis validam; consultor decide; executor autorizado publica;
- cobertura cadastral não equivale a maturidade;
- protocolo novo não reescreve avaliações antigas;
- configuração específica de cliente não vira regra global automaticamente;
- nenhuma expansão do APP32 deve ocorrer sem análise de aderência, impacto multi-tenant e complexidade.

## 11. Fora de escopo desta decisão

- desenho definitivo de banco, APIs ou telas;
- migração automática de registros existentes;
- cálculo de score percentual universal;
- gestão operacional de projetos dentro do motor;
- publicação autônoma de conteúdo canônico por agentes.
