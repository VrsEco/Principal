# Governança Documental Oficial

Status: canônico  
Escopo: APP32, Sapiens, Squads, MCP, agentes, harnesses e operação assistida

## 1. Objetivo

Padronizar como a IA, o CLI e a equipe humana devem criar, classificar, atualizar e manter documentos no APP32.

Esta governança existe para:
- evitar drift documental
- reduzir duplicidade
- garantir uma fonte canônica por assunto
- permitir que a IA atualize automaticamente a documentação correta quando houver mudança estrutural, funcional ou operacional

---

## 2. Classes oficiais de documentos

Toda documentação nova do APP32 deve ser classificada em uma destas 6 classes:

### 2.1 Paper
Uso:
- visão
- tese
- evolução conceitual
- alternativas
- racional das decisões

Regra curta:
> Paper pensa e amadurece a direção.

Convenção de nome:
- `paper_<tema>_v1.md`

---

### 2.2 SPEC
Uso:
- definição oficial
- contrato canônico
- arquitetura adotada
- estrutura que deve ser implementada e mantida

Regra curta:
> SPEC congela a decisão oficial.

Convenções de nome:
- `arquitetura_oficial_<tema>_v1.md`
- `agentes_oficiais_<tema>_v1.md`
- `harnesses_oficiais_<tema>_v1.md`
- `estrutura_oficial_<tema>_v1.md`
- `plano_<tema>_v1.md` quando o documento oficial registrar uma sequência canônica de correção, consolidação ou implantação

---

### 2.3 Manifesto
Uso:
- identidade
- propósito
- princípios
- limites inegociáveis

Regra curta:
> Manifesto declara o que algo é e o que não pode violar.

Convenção de nome:
- `manifesto_oficial_<tema>_v1.md`

---

### 2.4 Playbook
Uso:
- atuação
- decisão
- comportamento esperado
- handoffs
- escalonamento

Regra curta:
> Playbook orienta como atuar.

Convenção de nome:
- `playbook_<tema>_v1.md`

---

### 2.5 Runbook
Uso:
- execução prática
- checklist
- ativação
- operação
- troubleshooting

Regra curta:
> Runbook orienta como executar.

Convenção de nome:
- `runbook_<tema>_v1.md`

---

### 2.6 Harness
Uso:
- invólucro operacional do agente
- prompt-base
- startup
- tools preferidas
- bloqueios
- regras de surface/profile/runtime

Regra curta:
> Harness empacota como o agente roda.

Convenção de nome:
- `harness_<papel>_<squad>_v1.md`

---

## 3. Estrutura canônica alvo

Toda documentação nova deve convergir para esta taxonomia:

```text
app32/docs/
├── papers/
├── spec/
├── manifestos/
├── playbooks/
├── runbooks/
└── harnesses/
```

### Regra de transição
- a pasta legada `docs/specifications/` ainda pode conter material válido
- novas decisões canônicas devem preferir `docs/spec/`
- documentos legados só devem permanecer fora da nova taxonomia quando ainda não tiverem sido migrados

---

## 4. Política de criação vs atualização

### 4.1 Quando atualizar um Paper existente
Atualize o paper atual quando houver:
- aprofundamento da mesma tese
- refinamento do mesmo conceito
- evolução natural do mesmo assunto
- complementação sem mudança do eixo central

### 4.2 Quando criar um novo Paper
Crie novo paper quando houver:
- novo problema estrutural
- nova frente conceitual
- mudança grande de direção
- assunto com vida própria
- risco de deixar o paper atual inchado e confuso

### 4.3 Regra prática
Se a pergunta for:
- “ainda estamos pensando?” -> Paper
- “já decidimos oficialmente?” -> SPEC

---

## 5. Política de versionamento

### 5.1 Manter a mesma versão
Manter a mesma versão quando houver:
- ajustes pequenos
- ampliação coerente
- refinamento sem ruptura conceitual

### 5.2 Subir a versão
Criar nova versão quando houver:
- mudança relevante de tese
- redefinição estrutural importante
- alteração de direção arquitetural

Exemplo:
- `paper_conceitual_squads_agentes_v1.md`
- `paper_conceitual_squads_agentes_v2.md`

---

## 6. Regra de fonte canônica

Cada assunto deve ter uma fonte canônica principal.

### Exemplos
- tese e racional -> Paper
- decisão oficial -> SPEC
- identidade -> Manifesto
- atuação -> Playbook
- execução -> Runbook
- operação do agente no runtime -> Harness

### Regra obrigatória
Não criar documento paralelo para o mesmo assunto se já existir um arquivo canônico adequado.

Antes de criar um novo documento, a IA ou o operador deve:
1. localizar o arquivo canônico existente
2. verificar se a mudança cabe nele
3. atualizar esse arquivo se ele continuar sendo a fonte correta
4. só criar um novo arquivo quando houver justificativa estrutural

---

## 7. Regra de atualização automática pela IA / CLI

Sempre que uma mudança relevante ocorrer no sistema, a IA/CLI deve atualizar a documentação canônica correspondente.

### 7.1 Mudança conceitual
Exemplos:
- nova tese
- nova nomenclatura
- nova relação entre entidades

Atualizar:
- primeiro o **Paper**
- depois a **SPEC**, se a decisão já estiver oficializada

### 7.2 Mudança oficial de arquitetura, contrato ou estrutura
Exemplos:
- novo squad
- novo agente
- nova surface
- mudança em profile, routing ou policy

Atualizar:
- **SPEC**
- e, se necessário, **Manifesto**

### 7.3 Mudança de comportamento esperado
Exemplos:
- novo fluxo de coordenação
- novo critério de escalonamento
- nova regra de atuação do agente

Atualizar:
- **Playbook**

### 7.4 Mudança operacional
Exemplos:
- nova sequência de instalação
- novo smoke
- novo passo de ativação
- novo troubleshooting

Atualizar:
- **Runbook**

### 7.5 Mudança no runtime do agente
Exemplos:
- prompt-base
- startup
- toolset preferencial
- bloqueios
- strategy de surface/profile

Atualizar:
- **Harness**

---

## 8. Ordem obrigatória de sincronização documental

Quando uma mesma mudança impactar mais de uma classe documental, usar esta ordem:

1. **Paper**
2. **SPEC**
3. **Manifesto**
4. **Playbook**
5. **Runbook**
6. **Harness**

### Interpretação
- Paper amadurece
- SPEC oficializa
- Manifesto fixa identidade e princípios
- Playbook orienta atuação
- Runbook orienta execução
- Harness ajusta o runtime operacional

---

## 9. Regras específicas para IA e CLI

Toda IA ou CLI que trabalhar no APP32 deve obedecer às regras abaixo:

1. classificar qualquer novo documento em uma das 6 classes oficiais
2. preferir atualizar o arquivo canônico existente antes de criar um novo
3. usar a nova taxonomia de pastas como destino padrão
4. evitar criar documentos genéricos fora da taxonomia sem justificativa explícita
5. quando houver mudança estrutural, atualizar também a documentação dependente
6. não deixar drift entre código, SPEC, playbook, runbook e harness quando a mudança já estiver decidida

---

## 10. Regra especial para Squads, Agentes e Harnesses

Para temas ligados a Sapiens, Squads e operação assistida:

- o **Paper** registra a evolução conceitual
- a **SPEC** define a arquitetura oficial do squad
- o **Manifesto** define identidade do squad/agente
- o **Playbook** define como o agente atua
- o **Runbook** define ativação, instalação, smoke e troubleshooting
- o **Harness** define como o agente roda no runtime

---

## 11. Critério de suficiência

As 6 classes oficiais são suficientes para documentar o APP32 de forma estruturada:

1. Paper
2. SPEC
3. Manifesto
4. Playbook
5. Runbook
6. Harness

Nenhuma nova classe documental deve ser criada sem necessidade clara e decisão explícita.
