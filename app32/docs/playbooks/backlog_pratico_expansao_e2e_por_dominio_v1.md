# Backlog Prático — Expansão E2E por Domínio

Status: operacional  
Classe: Playbook

## 1. Objetivo

Traduzir a esteira oficial de completude E2E em um backlog prático, executável por domínio, para orientar a expansão da suíte do APP32.

Documento dependente:
- `C:\GestaoVersus\app32\app32\docs\spec\esteira_oficial_completude_testes_e2e_v1.md`

## 2. Domínios já cobertos hoje

Cobertura já existente na suíte:

- `auth`
- `workspace`
- `meetings`
- `integrations`
- `work_journey`
- `processes`
- `financial`
- `reports`
- `admin`

Coberturas já materializadas:

- smoke de autenticação e navegação;
- relatórios e filtros do workspace;
- CRUD real de meetings em `DEV_FULL`;
- CRUD real inicial de `work_journey` em `DEV_FULL`;
- drift, diff, volume, multiusuário e MCP.
- probe funcional de `processes` com BPMN Modeler e save controlado em `DEV_FULL`;
- probe funcional de `financial` com páginas e exportações principais;
- probe funcional de `reports` com jornada, workspace e exportações;
- probe funcional de `admin` com leitura de parametrização e save seguro em `DEV_FULL`.

## 3. Lacunas atuais por domínio

### 3.1 auth

Ainda falta:

- validar explicitamente sucesso real de login em produção;
- validar falha de autenticação;
- validar redirecionamento indevido para `/login?next=...`.

### 3.2 workspace

Ainda falta:

- validar ações principais além de abrir e consultar;
- validar save/configuração quando existir;
- validar mensagens de erro visíveis ao usuário;
- ampliar cobertura de exportações.

### 3.3 meetings

Ainda falta:

- ampliar cobertura visual da área em `PROD_SAFE`;
- validar save real de fluxos não destrutivos;
- validar falhas funcionais de renderização e persistência.

### 3.4 integrations

Ainda falta:

- ações reais dentro de `api-mcp` e `channels`;
- validação de erro observável;
- smoke funcional além da simples abertura.

### 3.5 work_journey

Ainda falta:

- cobertura real dos relatórios;
- cobertura do board em `PROD_SAFE`;
- validação de estados assíncronos e filtros relevantes.

### 3.6 processes

Ainda falta praticamente toda a trilha funcional:

- listagem e detalhe de processos;
- fluxos BPMN;
- ações de salvar/publicar;
- falhas visíveis em modeladores;
- persistência de configuração.

Exemplo real observado:

- `/processes/<id>/bpmn-modeler`
- ação: `salvar_rascunho`
- falha observada: `Erro ao salvar`

### 3.7 financial

Ainda falta:

- cobertura de consultas executivas;
- relatórios financeiros;
- filtros de alto volume;
- ações seguras em produção;
- fluxos sensíveis em ambiente controlado.

### 3.8 reports

Ainda falta:

- matriz explícita de relatórios por módulo;
- validação do conteúdo mínimo emitido;
- exportações múltiplas;
- falha de emissão e timeout.

### 3.9 admin

Ainda falta:

- superfícies administrativas reais;
- parametrizações com save;
- validação de permissão e feedback de erro.

## 4. Ordem prática de expansão

### Onda 1 — fechar o que já começou

1. `auth`
2. `workspace`
3. `meetings`
4. `integrations`
5. `work_journey`

Objetivo:
- sair de “abre e consulta” para “executa a ação principal e valida falha”.

### Onda 2 — fluxos especiais

1. `processes`
2. editores BPMN
3. telas com canvas
4. saves assíncronos

Objetivo:
- capturar erros que aparecem no uso real e hoje escapam da suíte.

Status atual:
- materializada na suíte com `processes_functional_probe`

### Onda 3 — domínios sensíveis

1. `financial`
2. `reports`
3. `admin`

Objetivo:
- ampliar cobertura segura e governada de áreas críticas/sensíveis.

Status atual:
- materializada na suíte com `financial_functional_probe`, `reports_functional_probe` e `admin_functional_probe`

## 5. Backlog prático por domínio

### auth

- criar suíte de autenticação real em `PROD_SAFE`
- detectar login aparente com URL ainda em `/login`
- validar seleção real de empresa

### workspace

- validar ações primárias do usuário no `/my-work`
- validar exportações adicionais
- validar falha visual e backend em filtros/atividades

### meetings

- validar entrada real no módulo sem falso positivo de login
- adicionar save seguro em cenário controlado
- validar mensagens de erro e persistência

### integrations

- cobrir ações internas de `api-mcp`
- cobrir ações internas de `channels`
- capturar erros visuais e respostas inesperadas

### work_journey

- cobrir relatórios pendentes
- cobrir exportações pendentes
- cobrir board e filtros relevantes em `PROD_SAFE`

### processes

- cobrir listagem/detalhe
- cobrir BPMN Modeler
- cobrir `salvar_rascunho`
- cobrir `publicar_versao` quando houver ambiente seguro
- cobrir erro visual de salvar

### financial

- cobrir consultas executivas seguras
- cobrir relatórios e filtros
- cobrir alto volume não destrutivo

### reports

- criar catálogo explícito de relatórios prioritários
- validar geração, download e conteúdo mínimo
- validar erro de emissão

### admin

- mapear telas administrativas
- priorizar saves de parametrização
- validar permissão e feedback

## 6. Regra prática de entrada no backlog

Um item entra no backlog quando:

- foi visto por usuário real e falhou;
- existe no inventário mas ainda não tem ação coberta;
- só possui cobertura de abertura;
- depende de editor especial;
- gera erro visual sem diagnóstico automatizado.

## 7. Próximos movimentos recomendados

1. corrigir a validação de autenticação do smoke em `PROD_SAFE`
2. fechar a lacuna de `processes` e BPMN Modeler
3. expandir `workspace` e `integrations` para ação principal + falha
4. estruturar a onda de `financial` e `reports`
