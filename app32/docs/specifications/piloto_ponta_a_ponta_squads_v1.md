# Piloto Ponta a Ponta dos Squads v1

## Objetivo
Executar um piloto controlado da arquitetura publicada para validar o ciclo mínimo:
- APP32 como núcleo operacional
- MCP como contrato canônico
- perfis externos do Squad Versus e Squad Cliente
- uso assistido e telemetria mínima

## Escopo do piloto
### Perfis validados
- `sapiens_default`
- `squad_versus`
- `squad_cliente`

### Superfícies validadas
- `/mcp/user/`
- `/mcp/admin/`

## Evidências do piloto
### 1. Estado do console IA/MCP
Validação local do `frontend_state`:
- perfis externos expostos: `sapiens_default`, `squad_versus`, `squad_cliente`
- dimensões mínimas de governança: `company_id`, `runtime`, `actor_role`, `surface`, `capability`, `status`
- fases assistidas expostas: `conducao_forte`, `coproducao_orientada`, `autonomia_assistida`

### 2. Produção — proteção das superfícies MCP
Validação remota em produção:
- `https://app.gestaoversus.com.br/mcp/user/` -> `401`
- `https://app.gestaoversus.com.br/mcp/admin/` -> `401`

Interpretação:
- as superfícies estão publicadas
- exigem autenticação
- não ficaram expostas anonimamente

### 3. Regressão direcionada
Pacote de testes executado:
- `test_ai_mcp_console_route.py`
- `test_mcp_connection_snippet_service.py`
- `test_core_mcp_http_auth.py`
- `test_operational_audit_service.py`
- `test_ai_audit_persistence.py`

Resultado:
- **31 testes passando**

### 4. Produção
Deploy final estável com:
- migrações verificadas
- uWSGI reiniciado com sucesso
- MCP HTTP remoto ativo em `127.0.0.1:8101`

## Conclusão do piloto
O piloto valida que a arquitetura mínima está operável para uso controlado:
- os perfis externos foram publicados
- o APP32 expõe as superfícies MCP esperadas
- existe trilha mínima de auditoria/telemetria por runtime, papel e surface
- o modo de utilização assistida já está materializado como contrato inicial

## Limites atuais identificados
1. ainda não há scoring persistido de maturidade por usuário
2. a telemetria está disponível no console, mas ainda não fechada em painéis específicos por squad
3. o bootstrap documental MCP segue em degradação segura quando o catálogo documental não está presente no runtime publicado
4. o piloto foi controlado e técnico; ainda não foi executado com usuários finais reais em rotina completa

## Backlog pós-piloto recomendado
### Prioridade alta
1. persistir sinais de maturidade por ator e runtime
2. criar painel dedicado de telemetria por squad no console IA/MCP
3. ligar approvals/human gate aos fluxos assistidos mais críticos

### Prioridade média
4. executar piloto assistido com consultor Versus real
5. executar piloto assistido com usuário cliente real
6. consolidar playbook operacional do rollout Modelo B

### Prioridade baixa
7. sofisticar score e gamificação de maturidade
8. expandir telemetria para jornadas por domínio

## Veredito
**Piloto técnico concluído com sucesso.**
A iniciativa sai do estágio de estruturação arquitetural e entra em condição de rollout assistido controlado.
