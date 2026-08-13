# Integração remota com o projeto operacional de engenharia

## Alvo confirmado em produção
- projeto vigente: `AA.J.2`
- projeto histórico: `AA.J.1`
- empresa: `AA - Versus Gestao Corporativa`
- company_id: `9`
- o `project_id` deve ser resolvido pelo código e `company_id`, nunca fixado

## Script operacional
`python .agent/skills/aa-j-31-card-execution/scripts/aa_j_31_cards_ssh.py <comando>`

## Wrapper operacional preferencial
`python .agent/skills/aa-j-31-card-execution/scripts/aa_j_31_step_wrapper.py <comando>`

## Pré-requisito local
- definir `GV_DEPLOY_KEY_PATH` apontando para a chave SSH de deploy quando a sessão não tiver isso configurado automaticamente
- exemplo:
  - PowerShell: `$env:GV_DEPLOY_KEY_PATH='C:\GestaoVersus\app32\app32\.codex_temp_deploy_key'`

## Comandos
- listar cards abertos do projeto vigente:
  - `python .agent/skills/aa-j-31-card-execution/scripts/aa_j_31_cards_ssh.py list`
- criar card:
  - `python .agent/skills/aa-j-31-card-execution/scripts/aa_j_31_cards_ssh.py create --title "[Nome da Etapa - Passo 1 de 4]" --due-date 2026-04-20`
- concluir card:
- `python .agent/skills/aa-j-31-card-execution/scripts/aa_j_31_cards_ssh.py complete --identifier "AA.J.1.123" --evidence "Passo validado"`
- materializar uma entrega com checklist:
  - `python .agent/skills/aa-j-31-card-execution/scripts/aa_j_31_step_wrapper.py materialize --stage-name "Alterar Front End Página XYZ" --steps "ajustar layout" "validar backend" "rodar smoke"`
- registrar um passo da execução:
  - `python .agent/skills/aa-j-31-card-execution/scripts/aa_j_31_step_wrapper.py complete-step --stage-name "Alterar Front End Página XYZ" --step-number 1 --total-steps 3 --steps "ajustar layout" "validar backend" "rodar smoke" --evidence "smoke concluído"`
- consultar o status dos cards da execução:
  - `python .agent/skills/aa-j-31-card-execution/scripts/aa_j_31_step_wrapper.py status --stage-name "Alterar Front End Página XYZ"`

## Observações
- a criação ocorre como `ProjectTask`
- o script usa o servidor real por SSH e resolve o projeto pelo código dentro da empresa `AA`
- por padrão, novos cards entram como `status=planned` e `stage=inbox`
- validação ponta a ponta executada em produção em `2026-04-16` com criação e conclusão real do card `AA.J.1.1431`
