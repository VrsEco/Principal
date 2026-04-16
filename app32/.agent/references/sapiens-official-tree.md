# Árvore Oficial do Sapiens

## Objetivo
Consolidar a estrutura oficial do Sapiens para menu, roteamento, contexto e evolução de workflows.

## Regras estruturais
- a árvore do Sapiens é orientada por domínio
- os códigos de menu usam formato sem ponto
- o menu visível não precisa reproduzir o mesmo nome do `action_key`
- o escopo operacional deve ficar explícito entre pessoal, equipe e empresa

## Domínios oficiais
- `1` Gestão da Rotina
- `2` Gestão Estratégica
- `3` Gestão Financeira
- `4` Sapiens
- `5` Governança e Aprovações
- `6` Implantação e Funcionamento
- `7` Sapiens Factory

## Gestão da Rotina
- `11` Minhas Tarefas
  - `111` O que tenho para hoje
  - `112` O que tenho para esta semana
  - `113` O que está vencido
  - `114` O que vence no período
  - `115` O que foi concluído no período
- `12` Atividades de Projetos
  - `121` Consultar atividades
  - `122` Criar atividade
  - `123` Editar atividade
  - `124` Concluir atividade
- `13` Instâncias de Processos
  - `131` Consultar instâncias
  - `132` Iniciar instância
  - `133` Atualizar instância
  - `134` Concluir instância
- `14` Reuniões
  - `141` Consultar reuniões
  - `142` Agendar reunião
  - `143` Iniciar reunião
  - `144` Resumir reunião
  - `145` Encerrar reunião
  - `146` Enviar resumo de reunião por e-mail
  - `147` Enviar resumo de reunião por WhatsApp
- `15` Tarefas da Equipe
  - `151` O que tem para hoje
  - `152` O que tem para esta semana
  - `153` O que está vencido
  - `154` O que vence no período
  - `155` O que foi concluído no período
- `16` Tarefas da Empresa
  - `161` O que tem para hoje
  - `162` O que tem para esta semana
  - `163` O que está vencido
  - `164` O que vence no período
  - `165` O que foi concluído no período
- `17` Resumos Operacionais
  - `171` Resumo de hoje
  - `172` Resumo da semana
  - `173` Resumo do mês
  - `174` Resumo personalizado
- `18` Capacidade Operacional
  - `181` Ocupação do colaborador
  - `182` Capacidade da equipe
  - `183` Capacidade da empresa

## Escopos canônicos
- pessoal: `11x`
- equipe: `15x`
- empresa: `16x`
- capacidade: `18x`

## Regras de contexto
- empresa explícita na mensagem tem prioridade sobre a empresa ativa
- empresa escolhida em wizard operacional tem prioridade sobre a empresa ativa quando o fluxo exigir seleção
- no WhatsApp, quando houver múltiplas empresas elegíveis, selecionar empresa antes da confirmação final

## Regras de roteamento
- priorizar workflow determinístico antes de fallback LLM
- aceitar código numérico direto como atalho de navegação e execução
- preservar coerência entre domínio, código, intenção e `action_key`

## Workflows destacados
- `meeting.close`
- `meeting.send_summary_email`
- `meeting.send_summary_whatsapp`

## Payload canônico recomendado para escopos de equipe/empresa
```json
{
  "empresa": "AA - Empresa X",
  "colaborador": "Fulano",
  "periodo": "esta semana",
  "status": "aberto|vencido|concluido",
  "entidade": "atividade|processo|reuniao"
}
```
