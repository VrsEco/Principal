# Workflow de Cards — AA.J.1 (Produção)

## Quando aplicar
Sempre que a execução tiver 3 ou mais etapas.

## Template de nome
`[<nome da etapa> - Passo X de N]`

## Exemplo
`[Alterar Front End Página XYZ - Passo 1 de 4]`

## Checklist por passo
1. descrever a etapa
2. criar o card
3. executar a mudança
4. testar
5. corrigir se necessário
6. concluir o card
7. só então iniciar o próximo

## Wrapper recomendado
- materializar passos:
  - `python .agent/skills/aa-j-31-card-execution/scripts/aa_j_31_step_wrapper.py materialize --stage-name "Nome da Etapa" --steps "passo 1" "passo 2" "passo 3"`
- concluir um passo:
  - `python .agent/skills/aa-j-31-card-execution/scripts/aa_j_31_step_wrapper.py complete-step --stage-name "Nome da Etapa" --step-number 1 --total-steps 3 --evidence "teste executado"`
- consultar status:
  - `python .agent/skills/aa-j-31-card-execution/scripts/aa_j_31_step_wrapper.py status --stage-name "Nome da Etapa"`

## Saída mínima esperada do agente
- plano com os passos
- lista de cards correspondentes
- status atual do passo em execução
- evidência de teste antes de fechar cada passo
