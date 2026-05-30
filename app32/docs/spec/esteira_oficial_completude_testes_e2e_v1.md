# Esteira Oficial — Completude dos Testes E2E

Status: canônico  
Classe: SPEC

## 1. Objetivo

Definir a esteira oficial para evoluir a suíte E2E do APP32 até um nível de cobertura realmente completo, orientado por:

- inventário funcional do sistema;
- uso real dos usuários;
- falhas reais observadas em DEV, homologação e produção;
- segurança de execução por `company_id` e por ambiente.

## 2. Princípios oficiais

1. **Completude não é só abrir tela**
2. **Toda cobertura precisa nascer com tenant explícito**
3. **Fluxo real do usuário vale mais que rota isolada**
4. **Erro real observado em produção alimenta a esteira**
5. **PROD_SAFE não executa mutação destrutiva**
6. **Sem evidência, não há diagnóstico confiável**

## 3. Critério oficial de “teste realmente completo”

Uma área só pode ser considerada realmente coberta quando a suíte valida, no mínimo:

- abertura da tela;
- autenticação e contexto corretos;
- carregamento visual mínimo;
- ação principal do usuário;
- persistência ou efeito esperado;
- resposta de erro quando a ação falha;
- evidência de execução.

Abrir a página sem validar a ação principal **não** conta como cobertura completa.

## 4. Esteira oficial de completude

### 4.1 Inventário de superfícies

Toda superfície relevante precisa entrar no inventário canônico:

- telas;
- rotas;
- botões;
- campos;
- relatórios;
- imports/exports;
- processamentos;
- integrações;
- editores especiais.

Arquivo base:
- `C:\GestaoVersus\app32\app32\tests\e2e\catalog\inventory.yaml`

### 4.2 Cobertura de ações reais

Após entrar no inventário, a superfície deve evoluir para cobertura de ação real:

- criar;
- salvar;
- alterar;
- excluir;
- publicar;
- aprovar;
- processar;
- exportar;
- vincular;
- configurar.

### 4.3 Cobertura de erro funcional

Toda ação principal precisa validar também a falha observável:

- toast de erro;
- banner de erro;
- modal de erro;
- resposta HTTP inválida;
- ausência de persistência;
- redirecionamento indevido;
- estado inconsistente após salvar.

### 4.4 Cobertura por domínio

A expansão oficial deve ser organizada por domínio funcional:

- `auth`
- `workspace`
- `meetings`
- `work_journey`
- `processes`
- `financial`
- `reports`
- `integrations`
- `admin`

### 4.5 Cobertura de fluxos especiais

Fluxos especiais exigem trilha própria de cobertura:

- editores BPMN;
- canvas;
- componentes drag-and-drop;
- configuradores com save assíncrono;
- páginas com renderização rica em JavaScript;
- telas com upload/download acoplado.

Exemplo que passa a orientar esta esteira:

- rota: `/processes/<id>/bpmn-modeler`
- ação necessária: `salvar_rascunho`
- validação necessária:
  - não pode exibir `Erro ao salvar`
  - não pode exibir `Erro interno do servidor`
  - deve confirmar persistência funcional

Esse caso entra como **lacuna real observada**, sem classificação automática de criticidade.

### 4.6 Cobertura segura em produção

Em produção, a completude precisa respeitar a superfície `PROD_SAFE`:

- login real;
- tenant isolado;
- consultas;
- navegação;
- relatórios;
- saves seguros quando houver escopo controlado;
- sem mutação destrutiva fora do laboratório permitido.

### 4.7 Cobertura de volume e concorrência

Não existe completude real sem:

- alto volume de dados;
- múltiplos usuários;
- múltiplas sessões MCP;
- relatórios com filtros volumosos;
- degradação observável sob carga funcional.

### 4.8 Cobertura de drift

Toda mudança funcional nova deve entrar no radar:

- nova tela;
- nova rota;
- novo botão relevante;
- novo endpoint;
- novo editor;
- novo relatório;
- novo processamento.

## 5. Regra oficial de expansão da suíte

Um fluxo entra obrigatoriamente na fila de automação quando ocorrer qualquer um dos eventos abaixo:

1. erro real observado por usuário;
2. novo módulo/tela adicionada ao sistema;
3. nova ação principal sem automação;
4. regressão recorrente em produção;
5. editor ou fluxo especial ainda não coberto;
6. integração sem evidência automatizada.

## 6. Ordem oficial de implementação

Para cada nova cobertura:

1. registrar no inventário;
2. modelar page object / task object;
3. definir ambiente permitido;
4. automatizar ação principal;
5. automatizar falha observável;
6. anexar evidências;
7. incluir no catálogo de suítes;
8. expor na Central E2E quando fizer sentido operacional.

## 7. Métrica oficial de maturidade

O progresso da completude deve ser lido por quatro perguntas:

1. **o que existe no sistema?**
2. **o que o robô já executa?**
3. **o que ainda falha sem cobertura?**
4. **o que apareceu na operação real e ainda não entrou na suíte?**

## 8. Decisão oficial

A evolução da suíte E2E do APP32 passa a seguir esta regra:

- erro real observado e não coberto vira insumo de expansão;
- editor especial e ação principal não podem ficar fora do inventário;
- cobertura completa exige ação principal + tratamento de falha + evidência;
- produção continua restrita a `PROD_SAFE`.

