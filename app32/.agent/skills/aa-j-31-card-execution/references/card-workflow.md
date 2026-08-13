# Workflow de Cards — AA.J.1 (Produção)

## Quando aplicar
Sempre que a execução tiver 3 ou mais etapas.

## Template de nome
`[<nome da entrega>]`

## Exemplo
`[Alterar Front End Página XYZ]`

## Checklist por passo
1. descrever a etapa
2. criar ou reutilizar o card único da entrega
3. executar a mudança
4. testar
5. corrigir se necessário
6. atualizar checklist e evidência no card
7. concluir o card somente após o último passo validado

## Wrapper recomendado
- materializar passos:
  - `python .agent/skills/aa-j-31-card-execution/scripts/aa_j_31_step_wrapper.py materialize --stage-name "Nome da Etapa" --steps "passo 1" "passo 2" "passo 3"`
- concluir um passo:
  - `python .agent/skills/aa-j-31-card-execution/scripts/aa_j_31_step_wrapper.py complete-step --stage-name "Nome da Etapa" --step-number 1 --total-steps 3 --steps "passo 1" "passo 2" "passo 3" --evidence "teste executado"`
- consultar status:
  - `python .agent/skills/aa-j-31-card-execution/scripts/aa_j_31_step_wrapper.py status --stage-name "Nome da Etapa"`

## Saída mínima esperada do agente
- plano com os passos
- card único da entrega e seu checklist
- status atual do passo em execução
- evidência de teste antes de fechar cada passo
