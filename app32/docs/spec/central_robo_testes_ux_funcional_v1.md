# SPEC — Central do Robô de Testes UX/Funcional v1

**Classe documental:** SPEC  
**Status:** Proposta oficial para implementação incremental  
**Data:** 2026-06-14  
**Escopo:** APP32 / Gestão Versus  
**Documento de origem:** `C:\GestaoVersus\app32\docs\papers\paper_robo_auditor_ux_funcional.md`  
**Mockup de referência:** `C:\GestaoVersus\app32\docs\papers\mockup_central_robo_testes_app32_v4.png`  

---

## 1. Decisão oficial

A nova **Central do Robô de Testes** deve ser criada como uma camada funcional e amigável sobre a infraestrutura E2E existente.

Não devemos substituir, reescrever ou desativar a Central E2E atual nesta fase.

A Central E2E atual permanece como **motor técnico / modo avançado**.  
A nova Central do Robô de Testes será a **experiência principal para usuários leigos, gestores e QA funcional**.

---

## 2. Objetivo

Permitir que um usuário não técnico consiga:

- entender se o sistema está saudável;
- rodar testes por área ou teste completo;
- ver últimos resultados por área;
- identificar novidades sem teste;
- analisar erros em linguagem simples;
- acionar correções ou abrir decisão;
- acessar evidências sem precisar conhecer pytest, logs, manifestos ou traces.

---

## 3. Princípios obrigatórios

1. **Não duplicar motor de execução.**
   - Reutilizar suíte E2E, catálogo, histórico, manifesto, evidências e detector de deriva atuais.

2. **Linguagem em português.**
   - A UI deve falar com usuário leigo.
   - Nomes técnicos podem existir apenas em metadados ou detalhes avançados.

3. **Multi-tenancy explícito.**
   - Toda execução deve operar com `company_id` resolvido e visível.
   - Não pode haver execução ambígua em múltiplas empresas.

4. **PROD_SAFE protegido.**
   - Ações destrutivas continuam proibidas em produção segura, exceto rotinas explicitamente controladas e reversíveis.

5. **Detalhe técnico sob demanda.**
   - Logs, JSON, traces e stack técnico ficam ocultos por padrão.
   - Usuário acessa via “Ver detalhes técnicos”.

6. **Correção assistida, não automática sem regra.**
   - Botão “Corrigir” deve iniciar fluxo assistido.
   - Mutação sensível exige confirmação humana.

---

## 4. Arquitetura de convivência

```text
Central do Robô de Testes
├── UI funcional em português
├── API agregadora de resultados
├── resumo por área
├── fila de erros e decisões
└── ações assistidas via Sapiens

Infraestrutura E2E atual
├── run_full_system_suite.py
├── suite_catalog.py
├── inventory.yaml
├── drift_detector.py
├── manifest.json
├── execution_history.py
├── evidence.py
└── Central E2E técnica /qa/e2e
```

A nova central consome os resultados da infraestrutura atual, sem alterar o contrato técnico existente na primeira versão.

---

## 5. Rota e navegação

### 5.1 Rota proposta

```text
/qa/robot-tests
```

### 5.2 Nome exibido

```text
Robô de Testes
```

### 5.3 Breadcrumb

```text
Portal / Sistema / Qualidade / Robô de Testes
```

### 5.4 Entrada pela Central E2E atual

A Central E2E atual pode ter um atalho:

```text
Ver nova Central do Robô de Testes
```

A nova Central deve ter link discreto:

```text
Detalhes técnicos / Central E2E
```

---

## 6. Layout funcional v1

A tela deve seguir o padrão APP32:

- topo horizontal padrão;
- pill da empresa ativa;
- breadcrumb;
- cards brancos com borda cinza-azulada;
- fundo claro levemente azulado;
- ação principal em azul/roxo;
- verde apenas para sucesso;
- amarelo/laranja para atenção/decisão;
- vermelho apenas para crítico.

### 6.1 Estrutura visual

```text
Robô de Testes
├── 4 cards superiores
│   ├── Saúde do Sistema
│   ├── Deriva de Cobertura
│   ├── Falhas Encontradas
│   └── Pendentes de Decisão
│
├── Área central esquerda
│   ├── Último teste por área
│   └── Erros encontrados e correções
│
└── Coluna direita
    ├── Teste completo
    ├── Saúde do Sistema
    ├── Deriva de Cobertura
    ├── Gestão Financeira
    ├── Gestão Comercial
    ├── Sapiens e IA
    ├── Relatórios
    ├── WhatsApp
    ├── Permissões
    ├── Histórico de testes
    ├── Relatórios gerados
    └── Evidências
```

---

## 7. Componentes da tela

### 7.1 Cards superiores

#### Saúde do Sistema

Mostra:

- status geral;
- último horário de checagem;
- falhas de login/app/MCP/Sapiens;
- badge: `Tudo certo`, `Atenção`, `Crítico`.

#### Deriva de Cobertura

Mostra:

- quantidade de itens novos sem contrato;
- telas novas;
- endpoints novos;
- Ferramentas MCP novas;
- campos/actions novos.

#### Falhas Encontradas

Mostra:

- total de falhas abertas;
- quantidade crítica;
- quantidade em atenção;
- link para lista filtrada.

#### Pendentes de Decisão

Mostra:

- itens aguardando decisão humana;
- correções pendentes;
- itens enviados ao Sapiens/WhatsApp.

---

### 7.2 Coluna direita de execução

A coluna direita é o painel de comando.

Botão principal:

```text
Teste completo
```

Botões secundários:

- Saúde do Sistema;
- Deriva de Cobertura;
- Gestão Financeira;
- Gestão Comercial;
- Sapiens e IA;
- Relatórios;
- WhatsApp;
- Permissões.

Botões de consulta:

- Histórico de testes;
- Relatórios gerados;
- Evidências.

### 7.3 Regras dos botões

- Cada botão deve mostrar loading ao executar.
- Deve bloquear duplo clique.
- Deve informar empresa ativa antes da execução.
- Deve registrar `company_id` no run.
- Em `PROD_SAFE`, deve bloquear pacote com mutação destrutiva não permitida.

---

### 7.4 Último teste por área

Cada área aparece como card retangular clicável.

Campos mínimos:

- área;
- status;
- última data/hora;
- resumo simples;
- quantidade de erros;
- link para pop-up de detalhe.

Áreas iniciais:

- Saúde do Sistema;
- Gestão Financeira;
- Cadastros;
- Relatórios;
- Sapiens e IA;
- WhatsApp;
- Permissões;
- Deriva de Cobertura.

### 7.5 Pop-up de detalhe da área

Ao clicar em um card de área, abrir modal com:

- último run;
- testes executados;
- testes ignorados;
- falhas;
- evidências;
- botão “Repetir esta área”;
- botão “Ver detalhes técnicos”.

---

### 7.6 Erros encontrados e correções

Cada erro deve aparecer como linha/card com:

- severidade;
- área;
- mensagem simples;
- impacto;
- ação sugerida;
- botão “Corrigir”;
- botão “Detalhes”.

Exemplo:

```text
Crítico — Gestão Financeira
Conciliação aceitou valores divergentes.
Impacto: pode gerar baixa financeira incorreta.
[Corrigir regra] [Detalhes]
```

### 7.7 Regra para sumir da lista

Um erro só sai da lista quando:

1. for corrigido e o teste relacionado passar novamente; ou
2. for classificado como aceito temporariamente com justificativa; ou
3. for marcado como falso positivo; ou
4. virar card/incidente e a UI estiver filtrada para “pendentes de decisão”.

A remoção nunca deve ocorrer apenas porque o usuário clicou em “Corrigir”.

---

## 8. Nomenclatura canônica da UI

| Nome exibido | ID técnico sugerido |
|---|---|
| Saúde do Sistema | `health` |
| Deriva de Cobertura | `coverage_drift` |
| Gestão Financeira | `finance` |
| Gestão Comercial | `commercial` |
| Sapiens e IA | `sapiens_ai` |
| Ferramentas MCP | `mcp_tools` |
| Relatórios | `reports` |
| WhatsApp | `whatsapp` |
| Permissões | `permissions` |
| Limpeza e Reversão | `cleanup` |
| Teste completo | `full` |
| Histórico de testes | `history` |
| Relatórios gerados | `generated_reports` |
| Evidências | `evidence` |

---

## 9. APIs necessárias v1

### 9.1 Estado geral da central

```http
GET /api/qa/robot-tests/overview?company_id=<company_id>
```

Retorna:

```json
{
  "company_id": 10,
  "summary": {
    "health": {"status": "ok", "label": "Tudo certo"},
    "coverage_drift": {"status": "attention", "count": 3},
    "failures": {"critical": 2, "total": 5},
    "pending_decisions": {"total": 5}
  },
  "areas": [],
  "open_errors": []
}
```

### 9.2 Últimos resultados por área

```http
GET /api/qa/robot-tests/areas/latest?company_id=<company_id>
```

### 9.3 Detalhe de uma área

```http
GET /api/qa/robot-tests/areas/<area_id>/latest?company_id=<company_id>
```

### 9.4 Erros abertos

```http
GET /api/qa/robot-tests/errors?company_id=<company_id>&status=open
```

### 9.5 Executar pacote

```http
POST /api/qa/robot-tests/runs
```

Payload:

```json
{
  "company_id": 10,
  "profile": "safe_prod",
  "package": "finance"
}
```

### 9.6 Ação sobre erro

```http
POST /api/qa/robot-tests/errors/<error_id>/actions
```

Payload:

```json
{
  "action": "start_fix_flow",
  "company_id": 10
}
```

Ações iniciais:

- `start_fix_flow`;
- `repeat_test`;
- `open_card`;
- `request_more_evidence`;
- `mark_accepted_temporarily`;
- `mark_false_positive`.

---

## 10. Origem dos dados v1

A nova Central deve ler prioritariamente:

- `app32/tests/e2e/outputs/**/reports/manifest.json`;
- summaries do `run_full_system_suite.py`;
- histórico de `execution_history.py`;
- resultados do `drift_detector.py`;
- catálogo de `suite_catalog.py`;
- inventário `inventory.yaml`;
- evidências existentes em screenshots, traces e vídeos.

Persistência futura pode ser feita em tabela própria, mas v1 deve reaproveitar o que já existe para acelerar entrega.

---

## 11. Regras de segurança e tenant

- Toda API deve exigir `company_id` explícito.
- O usuário precisa ter acesso à empresa solicitada.
- A empresa ativa exibida no topo deve ser a mesma do run.
- Runs em `PROD_SAFE` não podem permitir `E2E_DESTRUCTIVE_ACTIONS_ALLOWED=true`.
- Botão de correção sensível deve exigir confirmação humana.
- Ações via Sapiens devem respeitar surface e capability.

---

## 12. Onda 1 de implementação

### 12.1 Entregar primeiro

1. Rota `/qa/robot-tests`.
2. Template APP32 da nova tela.
3. API `overview` lendo últimos manifestos/resultados existentes.
4. Cards superiores.
5. Coluna direita com botões.
6. Último teste por área.
7. Lista de erros aberta a partir de falhas do último run.
8. Links para evidências e Central E2E técnica.

### 12.2 Fora da Onda 1

- Correção automática real;
- WhatsApp ativo;
- criação automática de contratos;
- matriz completa por tela;
- execução profunda de conciliação/faturamento;
- persistência nova complexa.

Esses entram na Onda 2+.

---

## 13. Critérios de aceite da Onda 1

A Onda 1 será aceita quando:

- a tela abrir no padrão APP32;
- a empresa ativa estiver visível;
- os 4 cards superiores refletirem dados reais ou estado vazio coerente;
- a coluna direita listar os pacotes em português;
- “Teste completo” iniciar ou encaminhar para execução existente;
- últimos resultados por área forem exibidos;
- falhas do último run aparecerem em linguagem simples;
- detalhes técnicos estiverem acessíveis sem poluir a leitura principal;
- não houver possibilidade de executar pacote sem `company_id`.

---

## 14. Dívidas e decisões futuras

- Definir tabela persistente para erros abertos.
- Definir integração completa com Sapiens/WhatsApp.
- Definir contratos YAML oficiais por tela.
- Definir política de quando uma falha bloqueia deploy.
- Definir geração automática de contrato inicial para deriva.
- Refinar paleta visual final junto ao padrão APP32.

---

## 15. Relação com documentos existentes

Esta SPEC deriva do Paper:

- `C:\GestaoVersus\app32\docs\papers\paper_robo_auditor_ux_funcional.md`

E deve conviver com:

- `C:\GestaoVersus\app32\app32\docs\spec\esteira_oficial_completude_testes_e2e_v1.md`
- `C:\GestaoVersus\app32\app32\docs\harnesses\robot_e2e_operations_center_harness.md`
- `C:\GestaoVersus\app32\app32\tests\e2e\README.md`

Qualquer implementação deve atualizar esta SPEC se alterar o contrato da UI, das APIs ou da convivência com a Central E2E atual.
