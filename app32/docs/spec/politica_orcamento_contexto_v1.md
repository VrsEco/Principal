# SPEC — Política de Orçamento de Contexto v1

**Status:** vigente  
**Classe:** SPEC  
**Escopo:** agentes e automações que atuam no APP32/Gestão Versus.

## Decisão
Contexto, chamadas de ferramenta e delegações são recursos controlados. A execução deve buscar a menor evidência suficiente para decidir, implementar e validar, sem reduzir os guardrails técnicos do produto.

## Regras normativas
1. **Núcleo primeiro.** Leia a skill global e os controles mandatórios; referências de domínio, runbooks e specs extensas são abertas apenas quando o pedido, o risco ou uma dúvida concreta exigir.
2. **Leitura cirúrgica.** Use caminho exato, busca por símbolo e recorte de linhas. É proibido varrer recursivamente ou imprimir integralmente `app32/.agent/vendor-skills/`, logs extensos, árvores de arquivos ou documentos sem relevância demonstrada.
3. **Saída limitada.** Toda chamada de shell, MCP ou web deve pedir somente os campos e o volume necessários. Resuma evidências antes de reutilizá-las em outra rodada.
4. **Contrato de entrega.** Antes de implementação, defina objetivo, escopo de arquivos, critério de aceite e teste. Uma entrega comum tem até duas rodadas de correção; na terceira falha equivalente, pare e reporte hipótese, evidência e decisão necessária.
5. **Delegação por exceção.** Use um agente por entrega como padrão. Delegue somente subtarefa independente, com entrada curta, saída esperada e sem sobreposição de arquivos. Revisão adicional exige risco objetivo: segurança, tenancy, migração, produção ou decisão arquitetural transversal.
6. **Memória operacional.** Em continuidade, referencie o resumo e os artefatos existentes; não replique prompts longos, históricos, checklists ou especificações já lidos. Registre a decisão no card da entrega quando houver 3+ etapas.
7. **Modelo proporcional.** Luna para transformação mecânica; Terra como padrão; Sol/Astra para produção, segurança, arquitetura complexa ou investigação que justifique a escalada.

## Preservação de qualidade
Esta política não flexibiliza `company_id`, RBAC, validação de schema, MCP First, testes de aceite, revisão de segurança ou gates de deploy. Economia é eliminar repetição e busca irrelevante, não pular validação.

## Indicadores
- tamanho do contexto deliberadamente carregado por entrega;
- número de rodadas de correção e motivo da escalada;
- quantidade de delegações e se houve sobreposição;
- evidência de aceite produzida versus chamadas/leituras realizadas.

## Adoção
O orquestrador e a skill `gestao_versus_core` apontam para esta SPEC. Atualizações devem preservar os guardrails acima e evitar duplicar regras em múltiplos documentos.
## Automação local
- `python app32/scripts/qa/check_agent_context_budget.py --root app32 --json` valida teto de palavras, headings duplicados, presença da SPEC e seu vínculo à skill-base. Ele deve rodar em revisão de governança e antes de alterar instruções obrigatórias.
- `python app32/scripts/qa/generate_agent_handoff.py --objective "..." --decision "..." --file "..." --test "..."` gera a transferência compacta entre task, modelo ou agente. Só registre fatos verificáveis e pendências acionáveis.

