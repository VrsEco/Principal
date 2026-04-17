# Central de Operações Inteligentes do APP32

## Objetivo

Unificar em um único ponto do APP32 tudo que hoje aparece disperso como:

- Sapiens
- MCP
- Tools
- Importações
- Execuções assistidas
- Fluxos automatizados

A proposta é organizar a experiência por **módulo de negócio**, não por tecnologia.

---

## Princípio de UX

O usuário não deve navegar por:

- "MCP"
- "Tools"
- "IA"
- "Importador X"

O usuário deve navegar por:

- Financeiro
- Projetos
- Processos
- Reuniões
- Jornada
- Cadastros
- Administração técnica

Tecnologias como MCP e Sapiens ficam como **camada de execução**, não como camada principal de navegação.

---

## Nome sugerido do menu

### Recomendação principal

**Operações Inteligentes**

### Alternativas

- Central Inteligente
- Central de Operações
- Hub de Execução
- Central Sapiens

### Decisão recomendada

Usar **Operações Inteligentes** como item principal do menu lateral.

---

## Estrutura da página

## Layout macro

1. **Cabeçalho**
   - título da central
   - seletor de empresa
   - busca global por ação/operação
   - filtros rápidos

2. **Abas por módulo**
   - Financeiro
   - Projetos
   - Processos
   - Reuniões
   - Jornada
   - Cadastros
   - Administração técnica

3. **Cards operacionais por módulo**
   - cada card representa uma operação real
   - cada operação pode abrir:
     - wizard
     - tela de revisão
     - execução assistida
     - histórico

4. **Painel lateral opcional**
   - pendências
   - execuções recentes
   - itens aguardando revisão

---

## Organização recomendada

## Aba: Financeiro

### Grupo: Importações
- Prestação de contas
- Importar extrato
- Importar documento para lançamento
- Importar orçamento/base

### Grupo: Classificação e revisão
- Revisar lançamentos sugeridos
- Revisar classificação contábil
- Ajustar vínculos padrão

### Grupo: Execução assistida
- Conversar com Sapiens sobre financeiro
- Criar lançamento por linguagem natural
- Validar inconsistências

### Grupo: Configurações operacionais
- Conta/caixa padrão
- Centro de custo padrão
- Projeto/processo padrão
- Tipo de item padrão
- Plano de contas padrão

### Grupo: Auditoria
- Histórico de importações
- Execuções automáticas
- Pendências para revisão

---

## Aba: Projetos

### Grupo: Operações
- Criar projeto
- Criar atividade
- Atualizar status
- Revisar backlog

### Grupo: Assistido por IA
- Criar projeto por linguagem natural
- Distribuir atividades
- Sugerir responsáveis

### Grupo: Controle
- Projetos recentes
- Atividades atrasadas
- Itens aguardando validação

---

## Aba: Processos

### Grupo: Operações
- Criar macroprocesso
- Criar processo
- Atualizar instância
- Finalizar etapa

### Grupo: Assistido por IA
- Diagnosticar gargalos
- Sugerir ajustes de processo
- Auditar pendências

---

## Aba: Reuniões

### Grupo: Operações
- Agendar reunião
- Iniciar reunião
- Registrar deliberações
- Encerrar reunião
- Enviar ata

### Grupo: Assistido por IA
- Criar ações a partir da reunião
- Resumir reunião
- Gerar follow-up

---

## Aba: Jornada

### Grupo: Operações
- Ver agenda
- Criar tarefa manual
- Mover item
- Criar regra
- Solicitar transferência

### Grupo: Gestão assistida
- Rebalancear agenda
- Detectar sobrecarga
- Ajustar blocos

---

## Aba: Cadastros

### Grupo: Cadastros-base
- Usuários
- Colaboradores
- Papéis
- Empresas
- Centros de custo
- Plano de contas

### Grupo: Apoio operacional
- Vínculos padrão por módulo
- Defaults por colaborador

---

## Aba: Administração técnica

### Grupo: Observabilidade
- Healthcheck
- Logs
- Diagnóstico MCP
- Diagnóstico Sapiens

### Grupo: Catálogo técnico
- Tools registradas
- Workflows disponíveis
- Estado de integrações

### Regra

Essa aba deve ter acesso restrito.

---

## Tipos de operação

Cada card da central deve ser classificado por tipo:

- **Manual**
- **Assistida**
- **Automática**
- **Revisão obrigatória**

Isso ajuda o usuário a entender o comportamento antes de entrar no fluxo.

---

## Fluxo recomendado para operações complexas

Operações mais sensíveis não devem ser uma ação direta de 1 clique.

### Padrão recomendado

1. Entrada de dados
2. Extração/validação
3. Sugestão automática
4. Revisão humana
5. Confirmação
6. Execução
7. Auditoria

---

## Exemplo detalhado: Prestação de contas

## Objetivo

Permitir importar um documento e transformá-lo em lançamentos financeiros com revisão antes da confirmação.

## Fluxo sugerido

### Etapa 1 — Upload
- enviar PDF/imagem/documento

### Etapa 2 — Extração
- OCR / parser
- leitura de data, valor, favorecido, categoria, observações

### Etapa 3 — Sugestão automática
- caixa/conta
- centro de custo
- projeto ou processo
- tipo de item
- plano de contas

### Etapa 4 — Tela de revisão
- grade editável
- campos preenchidos automaticamente
- alertas de inconsistência

### Etapa 5 — Confirmação
- usuário valida
- sistema grava os lançamentos

### Etapa 6 — Auditoria
- registrar origem do documento
- quem revisou
- o que foi aceito/alterado

---

## Modelo de card operacional

Cada operação na central pode seguir este padrão visual:

- Nome da operação
- Descrição curta
- Módulo
- Tipo de execução
- Requer revisão? sim/não
- Última execução
- Botão principal
- Botão secundário "Ver histórico"

---

## Relação com Sapiens e MCP

## Regra

A central unificada é a camada visual e operacional.

Por trás dela:

- alguns cards executam workflows tradicionais;
- alguns cards acionam tools;
- alguns cards abrem fluxos assistidos pelo Sapiens;
- todos podem ser executados via MCP/Sapiens quando aplicável.

### Conclusão

Sapiens e MCP deixam de ser “menus concorrentes” e passam a ser:

- **motores de execução da mesma central**

---

## Taxonomia funcional recomendada

> Referência complementar: `C:\GestaoVersus\app32\app32\docs\architecture\TAXONOMIA_CANONICA_SAPIENS_APP32.md`

Cada operação deve ter:

- `module_key`
- `operation_key`
- `label`
- `description`
- `execution_mode`
- `requires_review`
- `permission_resource`
- `permission_action`
- `entrypoint_type`

### Exemplo

```json
{
  "module_key": "financial",
  "operation_key": "expense_accountability_import",
  "label": "Prestação de contas",
  "description": "Importa documento e sugere lançamentos financeiros para revisão.",
  "execution_mode": "assisted",
  "requires_review": true,
  "permission_resource": "financial",
  "permission_action": "create",
  "entrypoint_type": "workflow"
}
```

---

## Fonte de verdade recomendada

Criar um catálogo único de operações da central.

### Benefícios

- um menu só
- uma taxonomia só
- reuso por UI, Sapiens e MCP
- governança por permissão
- expansão por módulo

---

## Roadmap sugerido

## Fase 1 — Arquitetura e navegação
- unificar o menu
- criar a página única
- definir abas e taxonomia

## Fase 2 — Financeiro piloto
- implementar Prestação de contas
- tela de revisão
- histórico e auditoria

## Fase 3 — Projetos e Processos
- cards de criação/edição
- execução assistida

## Fase 4 — Administração técnica
- mover MCP/Sapiens/tools técnicas para aba restrita

---

## Primeira entrega recomendada

### Escopo

1. Criar menu **Operações Inteligentes**
2. Criar página unificada com abas
3. Subir a aba **Financeiro** como piloto
4. Incluir card **Prestação de contas**
5. Incluir fluxo:
   - upload
   - sugestão
   - revisão
   - confirmação

### Motivo

Esse recorte já resolve:

- unificação visual;
- redução de dispersão de menus;
- primeiro caso de alto valor para IA + workflow + revisão.

