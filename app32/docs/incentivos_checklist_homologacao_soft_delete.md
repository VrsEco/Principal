# Checklist de Homologação — Incentivos (Soft Delete e Ações de Edição/Exclusão)

## Objetivo
Validar o comportamento do módulo **Gestão Estratégica > Planos de Incentivos** após a implantação de:

- ações visíveis de **editar/excluir**
- **soft delete**
- bloqueio de exclusão quando houver **registros vinculados**

---

## 1. Dashboard de Incentivos
Tela: `/incentives`

- [ ] Cada plano exibe ações de **abrir**
- [ ] Cada plano exibe ação de **editar**
- [ ] Cada plano exibe ação de **excluir**
- [ ] Ao tentar excluir um plano com vínculos, o sistema mostra mensagem de bloqueio
- [ ] Ao excluir um plano sem vínculos, ele deixa de aparecer nas listagens padrão

---

## 2. Gestão do Plano
Tela: `/incentives/rules/<id>`

### Plano
- [ ] Botão **Editar Plano** visível
- [ ] Botão **Excluir Plano** visível
- [ ] Exclusão do plano é lógica, sem remoção física

### Participantes
- [ ] Cada participante possui ação de **editar**
- [ ] Cada participante possui ação de **excluir**
- [ ] Ao excluir participante de plano sem apuração, exclusão ocorre com soft delete
- [ ] Ao excluir participante de plano com apuração, exclusão é bloqueada

### Vetores
- [ ] Cada vetor possui ação de **editar**
- [ ] Cada vetor possui ação de **excluir**
- [ ] Ao excluir vetor de plano sem apuração, exclusão ocorre com soft delete
- [ ] Ao excluir vetor de plano com apuração, exclusão é bloqueada

---

## 3. Regras de bloqueio

### Plano não pode ser excluído se possuir:
- [ ] vetores ativos vinculados
- [ ] participantes ativos vinculados
- [ ] apurações/fechamentos vinculados

### Participante não pode ser excluído se:
- [ ] o plano já possuir apuração vinculada

### Vetor não pode ser excluído se:
- [ ] o plano já possuir apuração vinculada

---

## 4. Indicadores
Tela: `/indicators`

- [ ] Ação de **editar** continua disponível
- [ ] Ação de **excluir** continua disponível
- [ ] Indicadores com metas/dados continuam bloqueando exclusão quando aplicável

---

## 5. Telas de consulta
Validar que permanecem consistentes:

- [ ] `/incentives/closings`
- [ ] `/incentives/reports`
- [ ] `/incentives/validation`
- [ ] `/incentives/closing/<id>`
- [ ] `/incentives/statement`

Critério:
- [ ] sem erro visual
- [ ] sem ação indevida de exclusão em telas analíticas
- [ ] navegação principal funcionando

---

## 6. Conferência de banco

Verificar nas tabelas:

- [ ] `incentive_rule_sets.deleted_at`
- [ ] `incentive_rules.deleted_at`
- [ ] `incentive_participants.deleted_at`

Critério:
- [ ] registro excluído recebe `deleted_at`
- [ ] registro não é removido fisicamente

---

## 7. Regressão mínima antes de deploy

Executar:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
pytest tests\test_incentive_soft_delete_service.py tests\test_incentives_soft_delete_routes.py tests\test_incentives_ui_actions.py tests\test_incentives_smoke_routes.py -q
```

Critério:
- [ ] todos os testes passando

---

## 8. Evidências recomendadas

- [ ] print do dashboard com ações de plano
- [ ] print da tela de gestão do plano com ações de participante e vetor
- [ ] print da mensagem de bloqueio ao excluir com vínculo
- [ ] print/consulta SQL comprovando preenchimento de `deleted_at`
