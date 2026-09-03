# Contrato de Saída da Modelagem BPMN

Entregar:

1. matriz de cobertura prévia das entregas 1, 2.1, 2.2, 2.3 e 2.4, por elemento e com estado de definição;
2. contrato do processo: objetivo, gatilho, fornecedores, entradas, saídas, recebedores e fronteira;
3. responsável único e times/papéis executores;
4. eventos, atividades, gateways, raias, exceções e encerramentos;
5. POPs necessários, rotina de disparo e indicadores mínimos;
6. validações de XML, conectividade, códigos, semântica, renderização e coerência SIPOC progressiva/regressiva;
7. gaps de dados, cardinalidade ou capability MCP;
8. estado: `Em discussão`, `Validado pelo Cliente`, `Validado pela Versus` ou `Aprovado para publicação`, somente com evidência.

Quando o modo for `maturar`, acrescentar:

9. protocolo e versão da jornada;
10. estado atual e evidência de entrada/saída;
11. diagnóstico por dimensão, sem score percentual universal;
12. gaps, gates pendentes e próxima ação determinística;
13. distinção explícita entre maturidade da modelagem, implantação e desempenho operacional.

Não declarar publicação nem aprovação com base apenas na geração do arquivo.



## Entregas e versões

Organizar a saída por componentes independentes:

1. `1 Arquitetura de Processos`;
2. `2.1 Premissas dos Processos`;
3. `2.2 SIPOC`;
4. `2.3 Fluxo`, com indicação de artefatos junto às atividades;
5. `2.4 Artefatos do Fluxo`, com desenvolvimento dos elementos identificados no fluxo.

Cada componente informa versão, status, mudanças e impactos. A baseline final declara explicitamente as versões vigentes de Premissas, SIPOC, Fluxo e Artefatos.

Definições desconhecidas usam `defined`, `hypothesis`, `pending` ou `not_applicable`. Item pendente registra descrição, responsável, etapa de revisão e impacto `blocking` ou `non_blocking`. Pendência bloqueante impede aprovação para implantação; pendência não bloqueante pode avançar com tratamento definido.
