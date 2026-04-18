# Exemplo inicial recomendado

## Caso real atual
`routine.consult`

### Objetivo
Responder consultas operacionais em linguagem natural no Sapiens para atividades, instâncias de processo e reuniões, com roteamento workflow-first e hidratação de contexto.

### Entradas típicas
- `Quais atividades tenho para hoje?`
- `Quais processos tenho hoje?`
- `Quais reuniões tenho esta semana?`
- `Quais atividades eu tenho vencidas na empresa Versus Gestão Corporativa?`

### Saída esperada
- confirmação curta do fluxo selecionado
- uso do usuário/empresa da sessão quando possível
- perguntas apenas para dados realmente faltantes
- resposta operacional final, sem abrir wizard executivo indevido

### Integrações esperadas
- `src/intelligence/intents/builders/routine_consult_form_builder.py`
- `src/intelligence/workflows/handlers/routine_consult_handler.py`
- `src/intelligence/menu_engine.py`
- `src/intelligence/workflows/reranker.py`
- `tests/test_workflow_routine_consult_handler.py`
- `tests/test_menu_engine_conversation_integration.py`

### Aprendizados obrigatórios
- pergunta livre não implica LLM
- empresa explícita tem precedência
- canal WhatsApp precisa parser natural e sessão por thread
- fallback agentic só entra quando o workflow não fecha o caso
