# Guia da Feature: Gestão Estratégica — Gestão de Processos (Execução e Instâncias)

## Metadados
- `feature_id`: `gestao_processos_execucao`
- `dominio`: `processes`
- `ramo_menu`: `Gestão Estratégica`
- `caminho_menu`: `Gestão Estratégica > Execução > Gestão de Processos`
- `rotas_app`: `/process-routines`, `/process-instances`
- `surfaces_permitidas`: `user`, `admin`, `analytics`
- `sensibilidade`: `alta`
- `company_id_obrigatorio`: `sim`

## Objetivo
Configurar o vínculo entre rotina (POP) e processo, e acompanhar as instâncias de execução resultantes — abertas, atrasadas e encerradas — com evidência de conclusão.

## Quando usar
- explicar como vincular uma rotina/POP a um processo, para que ele passe a gerar instâncias de execução
- explicar como listar as instâncias de processo abertas ou atrasadas da empresa (ou de um colaborador específico)
- orientar como encerrar uma instância de processo — sempre exigindo evidência de conclusão já registrada
- explicar a diferença entre "processo" (a definição/estrutura) e "instância de processo" (uma execução concreta, com prazo e responsável)

## Quando não usar
- para criar ou estruturar a hierarquia de processos (Área/Macro/Processo) — feature própria: `gestao_processos_estrutura`
- para análise de gaps de fluxo BPMN — feature própria: `processos_copiloto_fluxo`
- fora da surface autorizada

## Entradas esperadas
### Obrigatórias
- `company_id`: escopo do tenant (opcional em leitura — usa a empresa ativa quando ausente)

### Para encerrar uma instância
- `instance_id`: instância de processo a encerrar
- `evidence`: ID de um artefato de execução (`ProcessActivityArtifactExecution`) já registrado com status `completed`, comprovando a conclusão — a instância **nunca** é encerrada sem essa evidência

### Opcionais (leitura)
- `status` (um ou vários: pending, in_progress, overdue), `due_before`, `assigned_to`

## Saídas esperadas
- `lista_de_instancias_abertas`: instâncias com processo, rotina, status, prazo, dias de atraso, responsável e referência de manual vinculada
- `resultado_do_encerramento`: confirmação do encerramento (completed, cancelled ou failed)

## Como orientar o usuário
1. Acessar **Gestão Estratégica > Execução > Gestão de Processos > Rotina de Processos** para vincular POPs a processos — esse vínculo é o que faz o processo gerar instâncias de execução ao longo do tempo.
2. Em **Instâncias de Processos**, consultar o que está aberto, em andamento ou atrasado — a listagem já traz dias de atraso calculados e o responsável por cada instância.
3. Ao concluir uma instância, ela só pode ser encerrada com **evidência já registrada** (um artefato de execução comprovando a conclusão) — a IA nunca fabrica essa evidência, apenas confirma o encerramento quando ela já existe.
4. Encerrar uma instância é ação sensível: sempre exige confirmação humana antes de ser efetivada.

## Uso por IA / MCP
Esta feature nasceu diretamente ligada ao MCP nesta mesma frente de trabalho:
- `list_open_process_instances` já lista as instâncias abertas/atrasadas, com cálculo de atraso e filtro por responsável;
- `close_process_instance` já permite encerrar uma instância — mas **apenas com evidência já existente**, nunca fabricando evidência, e sempre com `human_gate=True` (mutação de alto risco, por impactar execução operacional e trilha de auditoria).

Ainda não é capability remota: configurar o vínculo entre rotina e processo (isso continua só no APP).

## Validações e restrições
- `company_id` obrigatório; instância de outra empresa nunca é retornada ou encerrada
- encerrar sem evidência válida é sempre recusado
- encerrar uma instância é mutação de alto risco e precisa de confirmação humana

## O que nunca expor
- estrutura de tabelas internas (instâncias, execuções, artefatos)
- nomes de services e métodos internos
- dados de outra empresa/tenant
