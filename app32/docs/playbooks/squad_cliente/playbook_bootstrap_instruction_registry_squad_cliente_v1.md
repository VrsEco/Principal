# Playbook — Bootstrap do Instruction Registry do Squad Cliente v1

Status: oficial

## 1. Quando usar

Usar quando o runtime externo do `Sapiens Cliente` precisar iniciar com instrução remota, curta e versionada.

## 2. Sequência

1. resolver bundle via `resolve_app32_instruction_bundle_tool`
2. validar `runtime_profile`, `agent_key`, `harness_key`, `channel` e `bundle_version`
3. carregar apenas o bundle mínimo no contexto inicial
4. executar o discovery operacional padrão do APP32
5. consultar docs completos apenas se o caso exigir

## 2.1 Entrada genérica `Sapiens On`

Se a sessão começar por `Sapiens On`:

1. resolver os squads disponíveis
2. se houver um só, ativar diretamente
3. se houver mais de um, perguntar exatamente:
   - `Escolha entre: Cliente, Versus ou Engenharia.`
4. responder a ativação com primeira linha curta no formato `Sapiens <Squad> Ativado`

## 3. Regras

- não abrir SPEC inteira no bootstrap
- não repetir bootstrap completo se a versão em cache continuar válida
- não aplicar override por tenant fora da trilha aprovada
- escalar cedo se houver choque entre bundle e contracts operacionais

## 4. Handoffs

- conflito de policy/runtime -> `Squad de Engenharia`
- ajuste metodológico/governança -> `Squad Versus`
- especialização de domínio -> `SC-COM`, `SC-OPS` ou `SC-ADM`

## 5. Operação assistida pelo console `API / MCP`

Quando o operador estiver no APP32, a entrada visual oficial passa a ser a aba `Instruction Registry` do console `API / MCP`.

### 5.1 Ordem de uso recomendada

1. ler o bloco `AS-IS → TO-BE`
2. confirmar runtime/canal/tenant no resumo
3. criar, editar ou filtrar a entry remota necessária
4. usar a promoção semântica entre canais e as ações rápidas de status quando a intervenção for controlada
5. invalidar cache quando o bundle publicado mudar
6. conferir a auditoria recente antes de encerrar a intervenção

### 5.2 Regra de contenção

- usar a UI para ajustes curtos e governados
- não transformar a tela em editor de documentação longa
- manter o payload focado em bundle mínimo
- preservar `company_id` explícito sempre que houver override por tenant
