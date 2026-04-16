# Piloto real: routine.consult

## Objetivo
Transformar consultas operacionais em linguagem natural do Sapiens em execução determinística sobre projetos, processos e reuniões, usando contexto da sessão antes de qualquer fallback em LLM.

## Frases-alvo
- `Quais atividades tenho para hoje?`
- `Quais as atividades eu tenho vencidas na empresa Versus Gestão Corporativa?`
- `Quais processos tenho hoje?`
- `Quais reuniões tenho esta semana?`

## Fluxo canônico
1. **Identificar workflow**
   - intenção: consultar
   - entidade: `project_task`, `process_instance`, `meeting` ou `mixed`
   - período/status: extraído da frase
2. **Validar permissões**
   - resolver usuário da sessão
   - resolver empresa explícita ou empresa ativa
   - validar tenant acessível
3. **Confirmar**
   - confirmar o fluxo `3.0 - Consulta de Rotina` quando necessário
4. **Hidratar contexto**
   - usuário
   - empresa
   - período
   - status padrão
   - canal/thread
5. **Executar**
   - derivar para `my_work.open`, `my_work.overdue`, `my_work.due_range` ou `my_work.completed_range`
6. **Responder**
   - saída curta, operacional e coerente com o canal

## Payload mínimo
- `_session_user_id`
- `_selected_company_id`
- `empresa` quando explicitada
- `entidade`
- `status_consulta`
- `periodo` ou datas
- `colaborador` apenas quando realmente necessário

## Defaults
- consulta pessoal -> colaborador = usuário atual implícito
- status default -> abertas
- empresa -> explícita > sessão > seleção
- período -> inferido da frase; perguntar só quando faltar

## Armadilhas já aprendidas
- não abrir resumo executivo para pergunta operacional simples
- não usar empresa ativa quando o usuário citou outra empresa
- não capturar a frase inteira como colaborador
- não depender de `current_user` no WhatsApp
- não executar opcional com resposta numérica vazia

## Testes mínimos
- saudação não interfere em pedido claro
- sessão pendente ambígua pergunta nova x continuar
- empresa explícita é respeitada
- consultas simples não viram wizard executivo
- resposta numerada em WhatsApp aceita `1 - valor`
