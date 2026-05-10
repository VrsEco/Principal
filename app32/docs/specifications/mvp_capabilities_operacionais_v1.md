# MVP de Capabilities Operacionais — Versus Gestão Corporativa

## Status
Versão inicial v1 produzida no contexto do card `AA.J.15.5`.

## Objetivo
Registrar a primeira implementação concreta do MVP operacional para squads externos, com foco em tornar o catálogo canônico mais aderente à superfície MCP real da jornada operacional.

---

## 1. Implementação realizada
Foi implementado um ajuste no catálogo canônico de capabilities para refletir um subconjunto operacional já existente no MCP de jornada/rotina.

### Arquivos alterados
- `C:/GestaoVersus/app32/app32/src/intelligence/tooling/capabilities.py`
- `C:/GestaoVersus/app32/app32/src/intelligence/tool_catalog.py`

### Objetivo técnico
Incluir no manifesto canônico por surface um conjunto mínimo de tools MCP operacionais já disponíveis, reduzindo o drift entre:
- capabilities efetivamente registradas no MCP
- capabilities oficialmente descobertas pelos manifestos de surface

---

## 2. Capabilities incluídas no catálogo canônico
Foram adicionadas ao catálogo canônico as seguintes tools MCP operacionais de jornada:

- `get_work_journey_board_tool`
- `list_work_journey_blocks_tool`
- `save_work_journey_block_tool`
- `list_work_journey_rules_tool`
- `save_work_journey_rule_tool`
- `update_work_journey_item_tool`
- `list_work_journey_manual_tasks_tool`
- `create_work_journey_manual_task_tool`
- `get_work_journey_agenda_tool`
- `move_work_journey_agenda_item_tool`

### Domínio canônico adotado
Todas foram classificadas no domínio canônico:
- `routine`

com tags de apoio contendo:
- `work_journey`

---

## 3. Impacto funcional
### Antes
O manifesto canônico das surfaces `user` e `admin` não refletia esse subconjunto operacional, embora o registrador MCP já expusesse essas tools.

### Depois
O manifesto por surface passou a incluir esse conjunto mínimo de jornada/rotina operacional, permitindo:
- descoberta melhor por agentes externos
- planejamento mais confiável do MVP assistido
- menor diferença entre MCP real e catálogo canônico

---

## 4. Validação local executada
Validação realizada por introspecção local do manifesto:

### Surface `user`
- total de tools: **36**
- total de tools do domínio `routine`: **14**
- `get_work_journey_board_tool`: presente
- `get_work_journey_agenda_tool`: presente

### Surface `admin`
- total de tools: **43**
- total de tools do domínio `routine`: **14**
- `get_work_journey_board_tool`: presente
- `get_work_journey_agenda_tool`: presente

### Observação de teste
Uma tentativa de rodar `pytest` local falhou por incompatibilidade do plugin `pytest_flask` com a versão de Flask do ambiente local, sem invalidar a introspecção funcional do catálogo.

---

## 5. Limite desta implementação
Esta entrega **não resolve todo o drift do catálogo MCP**.

Ela resolve apenas um primeiro recorte do MVP operacional, focado em jornada/rotina.

Ainda permanecem como trabalhos posteriores:
- saneamento mais amplo do domínio financeiro
- normalização adicional de registradores MCP fora do catálogo legado
- consolidação de objetos colaborativos no fluxo real

---

## 6. Veredito do passo
O Passo 5 entregou uma primeira implementação concreta e segura do MVP operacional:
- pequena
- validável
- alinhada ao fluxo assistido inicial
- útil para reduzir discrepância entre manifesto e MCP real

Essa é a primeira base prática para os próximos passos de integração dos squads externos.
