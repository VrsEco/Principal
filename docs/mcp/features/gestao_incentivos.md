# Guia da Feature: Gestão Estratégica — Gestão de Incentivos

## Metadados
- `feature_id`: `gestao_incentivos`
- `dominio`: `strategy`
- `ramo_menu`: `Gestão Estratégica`
- `caminho_menu`: `Gestão Estratégica > Desempenho > Gestão de Incentivos`
- `rotas_app`: `/incentives`, `/incentives/closings`, `/incentives/reports`, `/incentives/statement`
- `surfaces_permitidas`: `user`, `admin`, `analytics`
- `sensibilidade`: `alta`
- `company_id_obrigatorio`: `sim`

## Objetivo
Configurar planos de incentivo (regras, participantes, faixas de premiação), coletar fatos de desempenho vindos de processos, projetos e ocorrências, calcular e fechar incentivos por período, aprovar/pagar fechamentos e consultar extratos por colaborador.

## Quando usar
- explicar como configurar um plano de incentivo (regras, participantes, faixas/vetores de premiação)
- explicar como rodar o cálculo de incentivo de um período
- explicar como aprovar ou marcar como pago um fechamento de incentivo
- explicar como consultar o extrato de incentivo de um colaborador
- explicar de onde vêm os dados do cálculo (fatos de processos, projetos e ocorrências)

## Quando não usar
- para gerenciar o indicador em si (fora do contexto de cálculo de incentivo) — feature própria: `gestao_indicadores`
- para visualizar conexões de governança entre metas e indicadores — feature própria: `teia_de_conexoes`
- fora da surface autorizada

## Entradas esperadas
### Obrigatórias
- `company_id`: escopo do tenant

### Opcionais
- `rule_set_id`: plano de incentivo de referência
- `period_start` / `period_end`: período de cálculo
- `employee_id`: colaborador para consulta de extrato
- `calc_id`: fechamento específico

## Saídas esperadas
- `dashboard_de_incentivos`: estatísticas e histórico de cálculos
- `lista_de_fechamentos`: fechamentos (`IncentiveCalculation`) e planos ativos
- `extrato_do_colaborador`: extrato individual de um fechamento
- `relatorio_do_fechamento`: relatório detalhado de um fechamento específico

## Como orientar o usuário
1. Acessar **Gestão Estratégica > Desempenho > Gestão de Incentivos** no menu.
2. Configurar o plano de incentivo: regras, participantes e faixas de premiação (vetores).
3. Rodar a coleta de fatos (processos, projetos, ocorrências) e o cálculo do incentivo para o período desejado.
4. Em **Fechamento de Incentivos**, revisar o resultado e aprovar ou marcar como pago.
5. Em **Extratos de Incentivos** / **Meu Extrato**, consultar o detalhamento por colaborador.

## Uso por IA / MCP
Hoje **não existe nenhuma tool MCP** para o domínio de incentivos no `mcp-versus` — toda a operação é feita exclusivamente pela interface web.

**Achado importante — limitação de segurança já existente no código, não introduzida por esta documentação:** a consulta de extrato de outro colaborador (`/incentives/statement/<calc_id>/<employee_id>`) tem um `TODO` explícito no código-fonte para checagem de permissão de gestor — hoje o sistema não valida que quem está pedindo o extrato de um terceiro é de fato gestor dessa pessoa. Da mesma forma, as ações de aprovar/marcar como pago um fechamento (`/incentives/closing/<calc_id>/<action>`) não têm controle de RBAC granular por ação — qualquer usuário logado com acesso à empresa ativa pode executá-las. Isso deve ser tratado com cautela: **nunca** oriente o usuário a tratar extrato ou aprovação de incentivo como algo protegido por controle de gestor hoje, e sinalize esse ponto como prioridade caso uma tool MCP de mutação neste domínio seja avaliada no futuro (exigiria `human_gate` reforçado e checagem de papel de gestor antes de expor).

## Validações e restrições
- `company_id` obrigatório; incentivos de outra empresa nunca são retornados
- fechamento em modo "protegido" exige confirmação extra para alterar dados já fechados (`_require_protected_mode`)
- exclusão de plano/regra/participante/fechamento é sempre soft-delete, com validação prévia de que não quebra histórico já fechado
- cálculo considera a polaridade do indicador (quanto maior melhor vs. quanto menor melhor) ao apurar percentual de atingimento

## O que nunca expor
- estrutura de tabelas internas ou nomes de classes/serviços (`IncentiveService`, `IncentiveRuleSet`, etc.)
- valores de incentivo/remuneração de um colaborador para outro usuário sem confirmar que quem pede tem relação de gestão — mesmo sabendo que o código hoje não impõe essa checagem, a orientação ao usuário deve ser conservadora
- dados de outra empresa/tenant
