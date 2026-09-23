# Harness — Isolamento dos testes unitários MCP financeiro

Data: 2026-09-23
Status: correção local; sem commit ou deploy.

## Incidente
Ao executar test_core_mcp_financial_tools.py junto com test_core_mcp_surface_registry.py, testes com serviço simulado não substituíam create_app. O wrapper carregou o runtime real e acionou tarefas de conhecimento. O sucesso dos asserts não comprovava isolamento.

## Evidência somente leitura
Conexão diagnóstica direta, sem Flask, com transaction_read_only=on e timeout. Servidor confirmou 127.0.0.1:5432. Janela consultada: 2026-09-23 16:32:00 até 16:34:00 (timestamps armazenados; logs utilizam UTC).
- 44 execuções company: contadores de criação, atualização e desativação iguais a zero; duas execuções com falha na empresa 2.
- 2 execuções product: contadores somados de 1 criação e 4 atualizações; zero desativações.
- São contadores registrados das execuções na janela, não uma auditoria completa de todas as tabelas ou atribuição exclusiva de cada evento ao teste.
- Não foi realizada reversão: faltam estado anterior e atribuição suficiente para um rollback seguro. Registros não foram apagados.

## Correção
Fixture autouse no arquivo de testes substitui o módulo app por contexto simulado e bloqueia psycopg2.connect. Nenhuma alteração de lógica de produção.
Nova execução: 55 testes aprovados, sem log de atualização automática observado.

## Limites
Revisão de todos os testes do repositório e de todas as tarefas acionadas pelo bootstrap fora do escopo desta correção. Não afirmar ausência de outras alterações com base somente nesses contadores. Limpeza da raiz permanece pendente.
