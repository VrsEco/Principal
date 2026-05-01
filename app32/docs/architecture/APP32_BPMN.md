# Paper — APP32 - BPMN

**Status:** paper de evolução arquitetural — atualizado com MVP operacional implementado
**Data:** 25/04/2026
**Última atualização:** 25/04/2026
**Especialista líder:** @ARQUITETO
**Apoios naturais:** @FRONTEND, @BACKEND_API, @BACKEND_SERVICE, @DBA, @AI_ENGINEER, @QA_AUTOMATION

---

## 1. Resumo executivo

O APP32 já possui uma base funcional relevante para documentação e gestão de processos: mapa de processos, fluxo anexado, POP com atividades e passos, prints de tela, rotinas, executores, prazos, tempos e indicadores. O próximo salto arquitetural não deve ser apenas substituir o Bizagi por um editor de fluxograma dentro do sistema. O salto correto é transformar o APP32 em uma plataforma de **processos operacionais legíveis por humanos e por IAs**.

A proposta deste paper é criar a visão **APP32 - BPMN**: uma evolução do módulo de processos para combinar:

1. **BPMN 2.0** para modelagem visual e interoperável do fluxo.
2. **POP estruturado** para instrução humana detalhada.
3. **Contrato operacional da atividade** para padronizar entradas, saídas, regras, sistemas, responsáveis, riscos, evidências e critérios de aceite.
4. **Manifesto AI-readable** para permitir que agentes, Sapiens, MCP tools e mecanismos de RAG entendam o que deve ser executado, conferido e monitorado.
5. **Book do Processo** como saída executiva e operacional, contendo fluxo, POP, indicadores, rotinas, executores, tempos, SLAs e evidências.

Tese central:

> O APP32 - BPMN deve documentar processos não apenas como desenho ou manual, mas como um contrato vivo de execução: visual para humanos, estruturado para sistemas e semanticamente claro para IAs.

---

## 2. Problema atual

Hoje o processo de documentação costuma seguir este padrão:

```text
Bizagi
→ desenho do fluxo BPM/BPMN
→ exportação de imagem
→ upload da imagem no APP32
→ criação de POP no APP32
→ inclusão de prints e descrições
→ emissão do Book do Processo
```

Este fluxo funciona, mas gera alguns limites:

- O fluxo entra no APP32 como imagem, não como modelo editável.
- A IA não entende a semântica do fluxo quando ele está apenas em PNG/JPG/PDF.
- O POP é excelente para treinamento humano, mas ainda pouco estruturado para automação.
- Regras de decisão ficam misturadas em textos livres.
- Prints de tela ajudam o usuário, mas não informam à IA quais campos, validações, permissões e resultados devem ser observados.
- Indicadores, rotina, executores e prazos existem, mas precisam ficar semanticamente conectados às atividades do fluxo.

O risco é o APP32 virar apenas um repositório documental. A oportunidade é maior: tornar o APP32 a fonte viva de verdade operacional dos processos.

---

## 3. Estado atual observado no APP32

O APP32 já possui elementos essenciais para essa evolução:

```text
Process
├── Área
├── Macroprocesso
├── Processo
├── Fluxo anexado
├── Fluxo Mermaid
├── POP / atividades
│   └── Passos com descrição, resultado esperado, layout e imagem
├── Rotinas
│   ├── frequência
│   ├── prazo
│   ├── executores
│   └── horas
├── Indicadores
└── Book do Processo
```

Arquivos relevantes existentes:

- `C:\GestaoVersus\app32\app32\models\process.py`
- `C:\GestaoVersus\app32\app32\services\process_book_service.py`
- `C:\GestaoVersus\app32\app32\templates\modules\processes\process_details_v2.html`
- `C:\GestaoVersus\app32\app32\templates\reports\process_book_v2.html`
- `C:\GestaoVersus\app32\app32\api\resources\process.py`

Conclusão arquitetural:

> O APP32 não precisa começar do zero. Ele precisa evoluir o módulo atual de processos para suportar semântica operacional e interoperabilidade BPMN.

### 3.1 Estado implementado em 25/04/2026

Após a primeira onda de implementação, o APP32 já deixou de ser apenas um repositório de imagem de fluxo e passou a ter um **MVP BPMN operacional**. O que já foi entregue:

```text
APP32 BPMN — MVP implementado
├── APP32 BPMN Modeler
│   ├── modelagem BPMN 2.0 no navegador
│   ├── biblioteca bpmn-js embarcada localmente
│   ├── importação .bpmn
│   ├── exportação .bpmn
│   ├── salvar rascunho
│   └── publicar versão
│
├── Persistência e versionamento inicial
│   ├── tabela process_bpmn_diagrams
│   ├── status draft | published | archived
│   ├── bpmn_xml
│   ├── svg_snapshot
│   ├── version
│   └── published_at
│
├── Exibição do fluxo publicado
│   ├── aba Fluxo do processo
│   ├── Book do Processo
│   └── badge FLX no card quando há BPMN salvo/publicado
│
├── Integração BPMN → POP
│   ├── Data Object Reference como marcador de atividade documentável
│   ├── criação/abertura de atividade POP a partir do elemento BPMN
│   ├── bpmn_element_id em process_routines
│   ├── bpmn_data_objects em process_routines
│   └── geração automática de código da atividade pelo código do processo
│
├── POP operacional aprimorado
│   ├── colar print diretamente com Ctrl+V
│   ├── upload tenant-safe de imagens
│   ├── ajuste visual do tamanho da imagem por passo
│   ├── Book respeitando o tamanho da imagem configurado no POP
│   └── ocultação do metadado técnico BPMN/Data Object na interface do POP
│
└── Book do Processo aprimorado
    ├── página do fluxo em A4 paisagem
    ├── renderização do BPMN publicado via snapshot SVG
    ├── POP com prints e tamanhos preservados
    └── consolidação com rotinas e indicadores
```

Arquivos implementados ou significativamente evoluídos:

- `C:\GestaoVersus\app32\app32\templates\modules\processes\bpmn_modeler.html`
- `C:\GestaoVersus\app32\app32\static\js\process_bpmn_modeler.js`
- `C:\GestaoVersus\app32\app32\static\css\process_bpmn_modeler.css`
- `C:\GestaoVersus\app32\app32\static\vendor\bpmn-js\18.6.3\...`
- `C:\GestaoVersus\app32\app32\services\process_bpmn_service.py`
- `C:\GestaoVersus\app32\app32\services\process_book_service.py`
- `C:\GestaoVersus\app32\app32\api\resources\process.py`
- `C:\GestaoVersus\app32\app32\models\process.py`
- `C:\GestaoVersus\app32\app32\templates\modules\processes\process_details_v2.html`
- `C:\GestaoVersus\app32\app32\templates\reports\process_book_v2.html`

Migrações relevantes:

- `20260425_0900_create_process_bpmn_diagrams.py`
- `20260425_1010_add_bpmn_binding_to_process_routines.py`
- `20260425_1030_backfill_bpmn_pop_activity_codes.py`

Decisão consolidada:

> O APP32 - BPMN passa a ter um núcleo funcional real: o BPMN é editável e versionável, a publicação aparece no fluxo e no Book, e o Data Object Reference se torna o gatilho prático para abrir documentação POP vinculada à atividade.

---

## 4. Princípios do APP32 - BPMN

### 4.1 Processo como ativo operacional vivo

O processo não deve ser apenas um documento aprovado. Ele deve ser uma entidade viva conectada a:

- rotina;
- execução;
- responsável;
- indicador;
- risco;
- evidência;
- prazo;
- sistema utilizado;
- agente ou pessoa executora.

### 4.2 BPMN para fluxo, POP para execução

BPMN é excelente para representar sequência, eventos, gateways, subprocessos e responsabilidades. Porém, BPMN sozinho não substitui o POP. O POP descreve o detalhe operacional que o usuário precisa seguir.

Portanto:

```text
BPMN responde: o que acontece, em qual ordem, com quais decisões.
POP responde: como executar cada atividade corretamente.
Contrato operacional responde: quais dados, regras, evidências e resultados tornam a atividade válida.
```

### 4.2-A BPMN revela necessidade; BPMS não nasce antes do domínio

O BPMN não deve ser tratado como gerador automático de módulo. Ele deve funcionar como instrumento de descoberta operacional.

Esteira correta:

```text
BPMN
→ revela necessidade do processo
→ exige análise funcional
→ exige análise de capacidades existentes
→ classifica o que será:
   - núcleo novo
   - capability complementar
   - execução externa
   - integração REST/MCP
   - reaproveitamento de capacidade existente
→ projeto e implementação
→ configuração BPMS
```

Regra central:

> O BPMS nunca deve substituir o domínio funcional.  
> O domínio guarda a verdade do negócio.  
> O BPMS orquestra como essa verdade é operada ao longo do fluxo.

### 4.3 Documento duplo: humano e máquina

Cada processo deve gerar duas saídas complementares, com separação explícita para evitar que a necessidade de um público prejudique o outro:

1. **Book humano:** HTML/PDF com layout executivo e instrucional.
2. **Manifesto AI-readable:** JSON/YAML/Markdown estruturado, consumível por IA, MCP, RAG e automações.

Princípio de separação:

```text
Versão humana
├── linguagem natural
├── prints
├── orientação didática
├── contexto visual
├── exemplos
└── alertas para usuário

Versão IA
├── estrutura canônica
├── IDs estáveis
├── entradas e saídas
├── regras
├── exceções
├── critérios de aceite
├── permissões
├── evidências esperadas
└── instruções operacionais sem ambiguidade
```

A versão humana pode ser mais narrativa, visual e didática. A versão IA deve ser mais rígida, versionada e validável. As duas devem nascer da mesma fonte operacional, mas não precisam ter o mesmo formato.

### 4.4 Multi-tenancy obrigatório

Toda nova entidade precisa ser escopada por `company_id`. Nenhuma leitura ou escrita deve depender apenas do `id` do objeto.

### 4.5 Rotas finas, regra em service

As rotas Flask devem apenas validar, autenticar, autorizar e delegar. A lógica de negócio deve ficar em services.

### 4.6 MCP First

Quando agentes precisarem consultar processos, POPs, rotinas, indicadores ou manifestos, a leitura operacional deve ser exposta por tools MCP tenant-safe.

---

## 5. Conceito central: Atividade BPMN enriquecida

### 5.0 Esteira oficial de evolução

Toda iniciativa derivada de processo deve seguir a sequência abaixo:

1. **Modelagem BPMN**
2. **Análise das necessidades do processo**
3. **Análise das capacidades do APP32**
4. **Classificação do gap**
   - módulo núcleo
   - capability complementar
   - execução externa sem vínculo
   - execução externa com vínculo REST/MCP
   - uso de capacidade já existente
5. **Projeto e execução do que faltar**
6. **Configuração do BPMS**
7. **Vinculação com rotina, indicadores e shell de execução**

O passo 6 só deve acontecer depois do 4 e do 5.

A unidade mais importante do APP32 - BPMN não é apenas o processo. É a **atividade enriquecida**.

Cada atividade do fluxo deve poder apontar para uma estrutura operacional:

```text
Atividade BPMN
├── Identidade
│   ├── código
│   ├── nome
│   ├── descrição
│   └── versão
├── Execução humana
│   ├── POP
│   ├── passos
│   ├── prints
│   └── resultado esperado
├── Contrato operacional
│   ├── entrada
│   ├── saída
│   ├── critérios de aceite
│   ├── exceções
│   ├── sistemas utilizados
│   ├── permissões
│   ├── evidências exigidas
│   └── riscos/controles
├── Rotina
│   ├── frequência
│   ├── prazo
│   ├── executor
│   └── tempo estimado
└── Medição
    ├── indicadores
    ├── SLA
    └── qualidade da execução
```

Observação importante:

> O contrato operacional da atividade não define o domínio do negócio; ele define como a activity consome, altera, valida ou aciona uma capacidade de domínio.

---

## 6. Arquitetura conceitual proposta

```text
APP32 - BPMN
├── Camada Visual
│   ├── Editor BPMN
│   ├── Viewer BPMN
│   ├── POP com prints
│   └── Book do Processo
│
├── Camada de Domínio
│   ├── Processos
│   ├── Atividades
│   ├── Passos
│   ├── Contratos operacionais
│   ├── Regras de decisão
│   ├── Rotinas
│   ├── Indicadores
│   └── Evidências
│
├── Camada de Persistência
│   ├── BPMN XML
│   ├── POP estruturado
│   ├── Manifesto AI-readable
│   └── Versionamento
│
├── Camada de Inteligência
│   ├── Geração assistida de POP
│   ├── Leitura por agentes
│   ├── Validação de consistência
│   ├── Sugestão de indicadores
│   └── RAG de processos
│
└── Camada MCP
    ├── consulta de processos
    ├── consulta de atividade
    ├── consulta de POP
    ├── consulta de rotina
    └── consulta de manifesto operacional
```

---

## 7. Modelo de informação proposto

### 7.1 Processo

Representa o processo macro já existente no APP32.

Campos-chave:

- `id`
- `company_id`
- `macro_id`
- `code`
- `name`
- `description`
- `responsible_id`
- `owner_employee_id`
- `status`
- `version`
- `published_at`

### 7.2 Diagrama BPMN

Entidade já implementada:

```text
process_bpmn_diagrams
├── id
├── company_id
├── process_id
├── version
├── status              draft | published | archived
├── bpmn_xml
├── svg_snapshot
├── png_snapshot
├── created_by_user_id
├── updated_by_user_id
├── created_at
└── updated_at
```

Objetivo:

- importar `.bpmn` do Bizagi;
- editar dentro do APP32;
- exportar `.bpmn`;
- renderizar no Book;
- permitir mapeamento de atividades BPMN para atividades POP.

Estado atual:

- `bpmn_xml` é salvo no PostgreSQL com escopo por `company_id`;
- `svg_snapshot` é usado para renderizar o fluxo publicado no detalhe do processo e no Book;
- publicação de nova versão arquiva/substitui a versão publicada anterior no contexto do processo;
- a biblioteca `bpmn-js` está embarcada localmente no APP32 para reduzir dependência de CDN.

### 7.3 Atividade operacional

No MVP atual, a atividade operacional vinculada ao POP está sendo materializada em `process_routines`, com colunas adicionais para vínculo BPMN.

Campos sugeridos:

```text
process_activities
├── id
├── company_id
├── process_id
├── bpmn_element_id
├── code
├── name
├── description
├── owner_employee_id
├── executor_role
├── order_index
├── is_active
└── metadata_json
```

Observação:

> A coluna `bpmn_element_id` é crítica. Ela conecta o elemento visual do BPMN à documentação operacional do APP32.

Estado atual implementado:

- `bpmn_element_id` guarda o identificador/código do elemento BPMN que originou a atividade POP;
- `bpmn_element_type` guarda o tipo BPMN;
- `bpmn_data_objects` guarda os Data Object References associados;
- atividades com Data Object Reference podem abrir/criar atividade POP;
- códigos de atividade POP são gerados automaticamente a partir do código do processo, sem repetir o código no nome da atividade;
- o metadado técnico BPMN/Data Object foi mantido no banco, mas removido da interface humana do POP para não poluir a experiência do usuário.

### 7.4 Contrato operacional da atividade

Nova entidade sugerida:

```text
process_activity_contracts
├── id
├── company_id
├── process_id
├── activity_id
├── objective
├── input_schema_json
├── output_schema_json
├── acceptance_criteria_json
├── exceptions_json
├── systems_json
├── permissions_json
├── evidence_requirements_json
├── risks_controls_json
├── ai_instructions
├── human_notes
└── updated_at
```

Exemplo:

```json
{
  "objective": "Conferir se o pagamento informado entrou na conta correta.",
  "inputs": ["cliente", "valor", "data_prevista"],
  "outputs": ["pagamento_confirmado", "divergencia_registrada"],
  "acceptance_criteria": [
    "Valor localizado",
    "Cliente identificado",
    "Data compatível"
  ],
  "exceptions": [
    "Pagamento não localizado",
    "Valor divergente",
    "Cliente não identificado"
  ],
  "systems": [
    {"name": "APP32", "screen": "/financial/receivables"},
    {"name": "Banco", "screen": "Extrato"}
  ]
}
```

### 7.5 Passo do POP

A estrutura atual `process_steps` já atende parcialmente. Ela pode ser enriquecida.

Campos adicionais sugeridos:

- `screen_url`
- `screen_name`
- `field_annotations_json`
- `validation_rules_json`
- `evidence_type`
- `ai_readable_instruction`
- `risk_level`
- `control_type`

---

## 8. Prints de tela como evidência instrucional

O uso atual de prints deve ser preservado, mas enriquecido.

### 8.1 Modelo atual

```text
Print da tela
Descrição textual
Resultado esperado
```

### 8.2 Modelo recomendado

```text
Print da tela
├── descrição humana
├── tela/sistema
├── URL ou módulo
├── campos relevantes
├── valores de exemplo
├── validações
├── erros comuns
├── resultado esperado
└── evidência exigida
```

Exemplo:

```json
{
  "screen": "Cadastro de Cliente",
  "url": "/clients/new",
  "fields": [
    {
      "name": "cpf_cnpj",
      "label": "CPF/CNPJ",
      "required": true,
      "rule": "Deve ser único por empresa"
    }
  ],
  "expected_result": "Cliente salvo com status ativo",
  "common_errors": ["CPF/CNPJ duplicado", "Campo obrigatório vazio"]
}
```

Assim, a imagem continua ajudando o humano, mas os metadados ajudam a IA.

---

## 9. Manifesto AI-readable

O APP32 deve gerar automaticamente um manifesto por processo.

Formato sugerido inicial: JSON.

Exemplo:

```json
{
  "type": "app32.process_manifest",
  "version": "1.0",
  "company_id": 1,
  "process": {
    "id": 123,
    "code": "FIN.01",
    "name": "Contas a Receber"
  },
  "activities": [
    {
      "bpmn_element_id": "Activity_ConferirPagamento",
      "code": "FIN.01.02",
      "name": "Conferir pagamento",
      "objective": "Validar se o pagamento entrou na conta correta.",
      "executor": "Financeiro",
      "inputs": ["cliente", "valor", "data"],
      "outputs": ["status_pagamento"],
      "steps": [
        {
          "order": 1,
          "instruction": "Acessar a tela de recebimentos.",
          "screen": "/financial/receivables",
          "expected_result": "Lista de recebimentos carregada."
        }
      ],
      "acceptance_criteria": [
        "Pagamento localizado",
        "Valor compatível",
        "Cliente identificado"
      ],
      "exceptions": [
        "pagamento_nao_localizado",
        "valor_divergente"
      ],
      "indicators": [
        "tempo_medio_conferencia",
        "percentual_divergencias"
      ]
    }
  ]
}
```

Esse manifesto deve ser:

- versionado;
- gerado a partir do dado oficial do processo;
- escopado por `company_id`;
- consumível por IA;
- exportável;
- usado como base para MCP tools.

---

## 10. Copiloto de POP

O APP32 - BPMN deve prever um modo de construção assistida chamado **Copiloto de POP**.

Objetivo:

> Permitir que o especialista de processo, junto com a IA, transforme a execução real de uma tela/sistema em POP humano e contrato operacional IA-readable.

O Copiloto de POP deve suportar três modos de trabalho.

### 10.1 Modo A — Captura guiada durante a execução

Neste modo, o usuário executa a atividade e o assistente acompanha a estruturação.

Fluxo:

```text
Usuário abre a etapa do POP no APP32
→ executa ou simula a tela do sistema
→ captura print
→ informa observações rápidas
→ IA propõe:
   ├── título do passo
   ├── descrição humana
   ├── campos a observar
   ├── resultado esperado
   ├── riscos de erro
   ├── evidência esperada
   └── instrução AI-readable
→ usuário revisa
→ APP32 salva no campo correto
```

Exemplo:

```text
Processo: Gerir Compras
Atividade: Cadastrar fornecedor
Passo: Acessar cadastro de fornecedor

Versão humana:
"Entrar no menu Compras > Cadastros > Fornecedores. Conferir se a tela exibida é Cadastro de Fornecedor antes de iniciar o preenchimento."

Campos a observar:
- CNPJ/CPF
- Razão social
- Tipo de fornecedor
- Dados bancários
- Situação fiscal

Resultado esperado:
"Tela de cadastro aberta e pronta para preenchimento."

Versão IA:
{
  "screen": "Cadastro de Fornecedor",
  "navigation_path": ["Compras", "Cadastros", "Fornecedores"],
  "expected_state": "supplier_form_ready",
  "required_fields": ["document_number", "legal_name", "supplier_type"],
  "risk_points": ["documento duplicado", "dados fiscais incompletos"]
}
```

### 10.2 Modo B — Print + anotação de caderno

Neste modo, o usuário envia um print e uma anotação livre. A IA transforma isso em POP estruturado.

Fluxo:

```text
Usuário preenche a tela corretamente
→ tira print
→ anota em linguagem livre o que deve ser observado
→ envia print + anotação ao APP32
→ IA transforma em:
   ├── descrição do passo
   ├── campos críticos
   ├── regras de preenchimento
   ├── erros comuns
   ├── resultado esperado
   ├── evidência
   └── contrato operacional
→ usuário aprova
→ sistema grava no POP e no manifesto IA
```

Esse modo é importante porque respeita o processo real de trabalho: muitas vezes o conhecimento está na cabeça do usuário ou em anotações rápidas, não em um documento formal.

### 10.3 Modo C — Robô/assistente explorador

Neste modo, um assistente controlado acessa o APP32 ou outro sistema autorizado, navega pelas telas, entende o fluxo e propõe um POP preliminar.

Fluxo ideal:

```text
Usuário informa o processo e o objetivo
→ usuário fornece ou seleciona o fluxo BPMN
→ assistente navega pelas telas autorizadas
→ identifica menus, formulários, campos e validações visíveis
→ gera rascunho de POP
→ gera contrato operacional
→ usuário especialista valida
→ APP32 publica como rascunho ou versão aprovada
```

Guardrail obrigatório:

> O assistente pode propor documentação, mas a publicação do POP oficial deve exigir validação humana.

### 10.4 Papel do humano especialista

A IA não substitui o dono do processo. Ela acelera a documentação.

Responsabilidades do humano:

- confirmar se o fluxo está correto;
- validar prints;
- revisar regras;
- confirmar exceções;
- aprovar campos críticos;
- publicar versão oficial.

Responsabilidades da IA:

- estruturar texto;
- identificar campos visíveis;
- propor observações;
- padronizar linguagem;
- gerar versão humana e IA;
- apontar lacunas;
- sugerir critérios de aceite e evidências.

### 10.5 Campos sugeridos para captura assistida

Cada passo do POP deveria aceitar:

```text
process_step
├── name
├── description_human
├── expected_result_human
├── image_path
├── screen_name
├── navigation_path_json
├── observed_fields_json
├── critical_fields_json
├── fill_rules_json
├── common_errors_json
├── evidence_requirement
├── ai_instruction
├── ai_expected_state
└── confidence_score
```

O `confidence_score` é relevante para distinguir:

- conteúdo escrito por humano;
- conteúdo inferido pela IA;
- conteúdo confirmado pelo usuário.

### 10.6 Níveis de confiança da documentação

Toda informação assistida por IA deve carregar status:

```text
draft_ai_generated     → IA gerou, humano ainda não revisou
human_reviewed         → humano revisou
approved               → aprovado como POP oficial
needs_clarification    → há dúvida ou lacuna
deprecated             → passo obsoleto
```

Isso evita que uma inferência da IA seja tratada como procedimento oficial sem validação.

### 10.7 Evolução — Squad de Agentes da Empresa

Além do Copiloto de POP, o APP32 - BPMN deve prever uma camada superior: um **Squad de Agentes da Empresa**.

Essa camada não teria como objetivo apenas documentar processos. Ela teria como objetivo criar copilotos funcionais para gestores e donos de processo, como se cada gestor tivesse um **clone operacional especializado**, capaz de conhecer a arquitetura da empresa, os processos, os objetivos, os indicadores, as rotinas, a equipe executora, as medições e os resultados esperados.

Exemplo:

> Um **Agente Comercial** auxiliaria o gerente comercial a executar, monitorar e melhorar a performance dos processos comerciais e, consequentemente, o resultado da empresa.

Tese:

> O POP para IA não deve servir apenas para a IA entender como uma atividade é executada. Ele deve servir também para que agentes especializados compreendam a arquitetura operacional da empresa e formem duplas de alta performance com os gestores responsáveis pelos resultados.

#### 10.7.1 Visão conceitual

```text
Missão / Visão / Estratégia da Empresa
→ Objetivos estratégicos
→ Áreas / frentes de gestão
→ Macroprocessos
→ Processos
→ Objetivos e sub-objetivos
→ POP humano / POP para IA
→ Rotinas / execução / evidências
→ Indicadores / medições / incentivos
→ Dados estratégicos, financeiros e operacionais
→ Squad de agentes da empresa
→ Duplas gestor + agente
→ Recomendações, alertas, análises, planos de melhoria e acompanhamento
```

O agente não deve atuar como um "chat genérico". Ele deve ser um copiloto contextualizado do gestor, consumindo os ativos reais do APP32 e entendendo o papel daquele gestor dentro da arquitetura da empresa.

#### 10.7.2 Base de conhecimento dos agentes

Os agentes da empresa devem consumir, sempre com escopo de `company_id` e permissão adequada:

```text
Gestão de Processos
├── arquitetura de processos
├── áreas
├── macroprocessos
├── processos
├── BPMN
├── POP humano
├── manifesto IA
├── rotinas
├── instâncias de processo
├── ocorrências
├── evidências
└── indicadores

Gestão Estratégica
├── missão
├── visão
├── objetivos
├── metas
├── planos
├── projetos estratégicos
└── iniciativas

Gestão Financeira
├── orçamento
├── previsto vs realizado
├── centros de resultado
├── receitas
├── despesas
├── margem
└── desvios financeiros

Gestão de Pessoas / Execução
├── donos
├── responsáveis
├── executores
├── carga de trabalho
├── prazos
├── capacidade
└── histórico de entrega

Contexto externo
├── dados de mercado
├── benchmarks
├── tendências
├── riscos setoriais
└── boas práticas

Interação com o gestor / dono do processo
├── percepções
├── hipóteses
├── decisões
├── restrições
├── prioridades
└── validações humanas
```

#### 10.7.3 Papéis de agentes

O squad pode ser composto por agentes especializados:

```text
Agente Comercial
├── auxilia o gerente comercial a executar a rotina de vendas
├── monitora funil, metas, conversão, carteira e follow-ups
├── cruza processos comerciais com indicadores e resultado financeiro
├── identifica gargalos entre prospecção, proposta, negociação e fechamento
├── sugere melhorias de abordagem, cadência e priorização
├── consulta dados externos de mercado quando autorizado
└── apoia o gestor comercial na entrega das metas

Agente Financeiro
├── auxilia o gestor financeiro a monitorar orçamento, caixa e desvios
├── cruza processos financeiros com metas e indicadores
├── identifica riscos de inadimplência, margem, custo e liquidez
├── alerta sobre desvios relevantes
└── sugere ações de correção e controle

Agente de Compras / Suprimentos
├── apoia o gestor de compras na execução dos processos de aquisição
├── monitora cadastro de fornecedores, solicitações, aprovações e pedidos
├── identifica compras emergenciais, atrasos e concentração de fornecedores
├── cruza prazo, custo, qualidade e risco
└── sugere melhorias de negociação e controle

Agente de Operações
├── acompanha execução operacional, capacidade e gargalos
├── cruza rotinas, prazos, equipe, ocorrências e indicadores
├── identifica retrabalho e falhas de fluxo
└── propõe melhorias de produtividade

Agente de Pessoas / Equipe
├── acompanha capacidade, alocação e sobrecarga
├── identifica dependência excessiva de pessoas-chave
├── cruza competências, executores e prazos
└── sugere redistribuição e desenvolvimento

Agente Estrategista do Processo
├── entende missão, visão e objetivos
├── verifica alinhamento do processo com objetivos estratégicos
└── sugere ajustes de foco

Agente de Performance
├── monitora indicadores
├── identifica desvios
├── compara metas vs realizado
└── recomenda ações corretivas

Agente de Rotina e Execução
├── acompanha rotinas, prazos e responsáveis
├── identifica gargalos
├── aponta atrasos recorrentes
└── sugere redistribuição ou priorização

Agente Financeiro do Processo
├── cruza dados financeiros relacionados
├── identifica impacto econômico
├── avalia custo, margem, orçamento e desvios
└── alerta sobre riscos financeiros

Agente de Melhoria Contínua
├── lê POPs, ocorrências e evidências
├── identifica retrabalho, falhas e etapas frágeis
├── propõe melhorias de processo
└── sugere revisão de BPMN/POP

Agente de Mercado e Benchmark
├── consulta fontes externas aprovadas
├── compara práticas do mercado
├── identifica tendências
└── traz insights externos para o gestor responsável

Agente de Auditoria, Governança e Risco
├── verifica controles
├── identifica ausência de evidência
├── aponta riscos operacionais
├── avalia aderência do processo ao POP aprovado
├── identifica gaps de segregação de função
├── cruza execução, evidências, indicadores e exceções
├── gera trilhas de auditoria e achados preliminares
├── sugere testes de controle
└── recomenda controles adicionais
```

#### 10.7.4 Interação com o gestor

O agente deve ter uma rotina de interação ativa com o gestor responsável pela área, macroprocesso ou processo.

Exemplos:

```text
"Seu indicador de prazo de compras caiu 18% nos últimos 30 dias.
As principais causas aparentes são atraso na aprovação e cadastro incompleto de fornecedor.
Deseja revisar o POP da atividade Cadastrar Fornecedor?"
```

```text
"O macroprocesso Compras está ligado ao objetivo estratégico Reduzir custo operacional.
Porém, não há indicador financeiro vinculado ao processo Gerir Compras.
Sugestão: acompanhar economia negociada, prazo médio de compra e percentual de compras emergenciais."
```

```text
"Há três rotinas críticas vencendo esta semana sob responsabilidade da equipe de suprimentos.
O executor com maior carga prevista é João, com 18 horas alocadas.
Deseja redistribuir ou priorizar as entregas?"
```

Exemplo comercial:

```text
"Sua meta comercial mensal está em 62% de atingimento, mas o funil atual cobre apenas 78% do necessário para bater a meta.
O gargalo principal está entre proposta enviada e follow-up.
Deseja revisar o processo Comercial > Propostas > Acompanhamento de negociação?"
```

```text
"Nos últimos 45 dias, 38% dos leads qualificados não tiveram segunda interação registrada.
Isso indica falha de rotina ou ausência de responsável claro.
Sugestão: criar rotina automática de follow-up e indicador de tempo médio de resposta."
```

#### 10.7.5 Relação com o POP para IA

O POP para IA passa a ser uma peça estratégica.

Ele deve responder:

- como o processo funciona;
- quem executa;
- qual é o objetivo;
- quais entradas e saídas existem;
- quais indicadores medem sucesso;
- quais riscos precisam ser controlados;
- quais evidências comprovam execução;
- quais sistemas são usados;
- quais decisões humanas são necessárias;
- quais exceções devem gerar alerta.

Com isso, o agente consegue sair de uma análise genérica e passar para uma análise contextualizada, considerando o processo e também o papel gerencial responsável por entregar o resultado.

#### 10.7.6 Arquitetura de conhecimento

Arquitetura sugerida:

```text
Fontes APP32
├── processos
├── POPs
├── BPMN
├── rotinas
├── indicadores
├── medições
├── projetos
├── financeiro
├── estratégia
└── interações

Camada de Normalização
├── company_id
├── domínio canônico
├── permissões
├── entidade origem
├── versão
└── qualidade/confiança da informação

Camada de Conhecimento
├── manifesto do processo
├── embeddings/RAG quando aplicável
├── consultas estruturadas
├── MCP tools
└── memória controlada do processo

Squad de Agentes da Empresa
├── análise
├── diagnóstico
├── recomendação
├── perguntas ao gestor
└── acompanhamento de plano
```

#### 10.7.7 Guardrails do squad de agentes

Regras obrigatórias:

- todo consumo de dados deve respeitar `company_id`;
- dados financeiros exigem surface e permissão compatível;
- agente não deve alterar processo, rotina, indicador ou financeiro sem autorização;
- recomendações devem trazer origem dos dados usados;
- dados de mercado devem possuir fonte e data;
- insights externos não podem sobrescrever dados internos;
- decisões críticas continuam com o humano;
- o agente deve diferenciar fato, inferência e recomendação.
- achados de auditoria gerados por IA devem nascer como preliminares e exigir validação humana.

#### 10.7.8 Agente de Auditoria, Governança e Risco

O agente de auditoria deve ser um papel explícito no squad, e não apenas uma variação genérica de risco.

Objetivo:

> Avaliar se o processo está sendo executado conforme o desenho aprovado, se existem evidências suficientes, se os controles são adequados e se há riscos relevantes para a entrega dos objetivos.

Esse agente deve consumir:

```text
Processo aprovado
├── BPMN publicado
├── POP humano aprovado
├── POP para IA / manifesto operacional
├── contratos operacionais
├── regras de decisão
└── matriz de riscos e controles

Execução real
├── instâncias de processo
├── rotinas executadas
├── evidências anexadas
├── logs
├── ocorrências
├── exceções
├── atrasos
└── retrabalhos

Resultados
├── indicadores
├── medições
├── metas
├── impactos financeiros
└── incentivos
```

Saídas esperadas:

```text
Relatório preliminar de auditoria
├── escopo analisado
├── critérios usados
├── evidências consultadas
├── exceções encontradas
├── riscos identificados
├── controles frágeis ou ausentes
├── recomendações
├── nível de confiança
└── necessidade de validação humana
```

Exemplos de análises:

```text
"A atividade Aprovar Pedido de Compra exige evidência de aprovação formal,
mas 32% das execuções dos últimos 60 dias não possuem anexo ou log correspondente."
```

```text
"O POP aprovado exige validação fiscal do fornecedor antes da primeira compra.
Foram encontradas 4 compras realizadas antes da conclusão dessa etapa."
```

```text
"O mesmo usuário cadastrou fornecedor e aprovou pedido em 7 casos.
Isso pode indicar fragilidade de segregação de função."
```

Guardrail específico:

> O agente pode gerar achados preliminares, mas não deve publicar parecer final de auditoria sem validação humana.

#### 10.7.9 Resultado esperado

O gestor deixa de ter apenas documentação estática e passa a ter um copiloto de gestão.

Resultado esperado:

```text
Gestor + Agente
├── entende melhor seus objetivos
├── acompanha desvios com antecedência
├── recebe recomendações contextualizadas
├── melhora POPs e rotinas
├── conecta operação com estratégia
├── entende impacto financeiro
└── melhora a entrega dos resultados esperados
```

Síntese:

> Cada gestor pode ter uma dupla com um agente especializado. O gestor traz contexto, decisão e responsabilidade. O agente traz memória, análise, cruzamento de dados, disciplina operacional e recomendações.

### 10.8 Squad de Arquitetura e Modelagem de Processos

Além dos agentes funcionais da empresa, o APP32 - BPMN deve prever um papel anterior e estruturante: um **Squad de Arquitetura e Modelagem de Processos**.

Esse squad atuaria como um **clone metodológico do arquiteto de processos**, auxiliando na construção da arquitetura corporativa, dos macroprocessos, dos processos, das rotinas, dos indicadores, dos donos e das equipes executoras.

Tese:

> Antes de cada gestor ter um agente de performance, a empresa precisa ter processos bem arquitetados. O Squad de Arquitetura e Modelagem ajuda a transformar conhecimento disperso em uma arquitetura operacional coerente, mensurável e executável.

#### 10.8.1 Objetivo do squad

O objetivo não é substituir o arquiteto humano. O objetivo é acelerar, organizar e criticar a estruturação.

Responsabilidades:

```text
Squad de Arquitetura e Modelagem
├── ajudar a definir áreas e macroprocessos
├── conectar macroprocessos à missão, visão e objetivos estratégicos
├── decompor macroprocessos em processos coerentes
├── definir objetivo e sub-objetivos de cada processo
├── sugerir dono do processo e perfil recomendado
├── mapear equipe executora e papéis
├── sugerir rotinas e frequência de execução
├── sugerir indicadores e metas
├── apoiar modelagem BPMN
├── apoiar construção do POP humano
├── apoiar construção do POP para IA
├── identificar lacunas, sobreposições e processos órfãos
└── preparar material para validação humana
```

#### 10.8.2 Agente único ou squad?

A recomendação arquitetural é iniciar como **um agente orquestrador com subcompetências**, e evoluir para squad conforme a complexidade crescer.

MVP:

```text
Agente Arquiteto de Processos
├── entrevista o arquiteto humano
├── organiza informações
├── sugere arquitetura
├── propõe BPMN inicial
├── propõe rotinas
├── propõe indicadores
└── gera pendências de validação
```

Evolução:

```text
Squad de Arquitetura e Modelagem
├── Agente de Arquitetura Corporativa
├── Agente de Modelagem BPMN
├── Agente de Rotinas e Capacidade
├── Agente de Indicadores e Metas
├── Agente de Papéis, Donos e Equipe
├── Agente de POP Humano
├── Agente de POP para IA
└── Agente de Qualidade e Coerência
```

Essa abordagem evita criar complexidade antes da hora, mas mantém o desenho preparado para escalar.

#### 10.8.3 Papéis sugeridos

```text
Agente de Arquitetura Corporativa
├── organiza áreas, macroprocessos e processos
├── verifica alinhamento com missão, visão e objetivos
├── identifica processos faltantes ou duplicados
└── propõe árvore de processos

Agente de Modelagem BPMN
├── transforma descrição textual em fluxo BPMN
├── sugere eventos, atividades, gateways e raias
├── identifica atividades sem responsável
├── aponta decisões sem critério claro
└── prepara o diagrama para validação humana

Agente de Rotinas e Capacidade
├── sugere quais processos precisam virar rotina
├── propõe frequência, prazo e tempo estimado
├── estima carga operacional
├── identifica sobrecarga de equipe
└── conecta rotina com execução real

Agente de Indicadores e Metas
├── sugere indicadores por processo
├── diferencia indicador de esforço, resultado e controle
├── propõe fórmula, unidade, fonte e periodicidade
├── conecta indicador a objetivo estratégico
└── identifica processo sem medição

Agente de Papéis, Donos e Equipe
├── sugere perfil do dono do processo
├── define papéis típicos: dono, responsável, executor, aprovador
├── identifica segregação de função necessária
├── cruza processo com equipe disponível
└── aponta lacunas de responsabilidade

Agente de POP Humano
├── transforma conhecimento operacional em instrução didática
├── organiza passos
├── sugere prints necessários
├── escreve orientações para o usuário
└── prepara Book humano

Agente de POP para IA
├── transforma POP em contrato operacional estruturado
├── define entradas, saídas, critérios e exceções
├── cria manifesto AI-readable
├── aponta ambiguidade operacional
└── prepara base para agentes funcionais

Agente de Qualidade e Coerência
├── revisa consistência entre arquitetura, BPMN, POP, rotina e indicador
├── identifica processo sem dono
├── identifica indicador sem processo
├── identifica rotina sem POP
├── identifica POP sem evidência
└── gera checklist de maturidade
```

#### 10.8.4 Fluxo de trabalho com o arquiteto humano

Fluxo recomendado:

```text
Arquiteto humano informa contexto
→ agente organiza a arquitetura inicial
→ agente propõe macroprocessos e processos
→ humano valida/ajusta
→ agente propõe modelagem BPMN
→ humano valida/ajusta
→ agente propõe POP, rotinas, indicadores e equipe
→ humano valida/ajusta
→ APP32 gera Book humano e manifesto IA
→ agentes funcionais passam a consumir essa base
```

Exemplo de interação:

```text
"Você informou que o objetivo estratégico é aumentar receita recorrente.
Sugiro que a área Comercial tenha, no mínimo, os macroprocessos:
1. Gestão de Mercado e Prospecção
2. Gestão de Oportunidades
3. Gestão de Propostas
4. Gestão de Contratos
5. Gestão de Relacionamento e Retenção

Deseja detalhar primeiro Gestão de Oportunidades?"
```

```text
"O processo Gestão de Propostas tem objetivo claro, mas ainda não possui:
- indicador de taxa de conversão;
- prazo padrão de envio de proposta;
- responsável por follow-up;
- critério de perda.

Deseja que eu proponha uma estrutura inicial?"
```

#### 10.8.5 Relação com os agentes funcionais

O Squad de Arquitetura e Modelagem cria a base. Os agentes funcionais usam essa base para operar melhor.

```text
Squad de Arquitetura e Modelagem
→ cria arquitetura, BPMN, POP humano, POP para IA, rotinas e indicadores
→ publica versão validada
→ Squad de Agentes da Empresa consome essa base
→ gestores recebem apoio operacional e estratégico
```

Sem uma boa arquitetura, o agente funcional vira apenas um analista genérico. Com arquitetura, ele vira copiloto contextualizado.

#### 10.8.6 Guardrails

- o agente não deve criar arquitetura oficial sem validação humana;
- toda sugestão deve diferenciar hipótese, inferência e decisão validada;
- toda estrutura deve manter `company_id`;
- todo processo deve ter objetivo, dono, equipe ou justificativa de ausência;
- todo indicador sugerido deve possuir fórmula, fonte e periodicidade;
- toda rotina deve ter frequência, prazo e responsável;
- todo POP para IA deve nascer vinculado ao processo e à versão do BPMN/POP humano.

---

## 11. Regras de decisão e DMN

Nem toda regra cabe bem no BPMN ou no POP. Decisões com múltiplos critérios devem ser modeladas separadamente.

Exemplos:

- Se valor maior que R$ 50.000, exigir aprovação do diretor.
- Se cliente inadimplente, bloquear faturamento.
- Se documento incompleto, retornar para cadastro.
- Se centro de custo não permitido, rejeitar lançamento.

Para esses casos, o APP32 pode evoluir futuramente para suporte a **DMN** ou a uma matriz de decisão própria.

No MVP, recomenda-se começar com uma estrutura simples:

```text
process_decision_rules
├── id
├── company_id
├── process_id
├── activity_id
├── name
├── condition_json
├── result_json
├── priority
└── is_active
```

---

## 12. Book do Processo 3.0

O Book atual deve evoluir para o **Book do Processo 3.0**.

Estrutura recomendada:

```text
Book do Processo
├── 1. Capa executiva
├── 2. Identificação do processo
├── 3. Mapa BPMN
├── 4. Escopo e objetivo
├── 5. Papéis e responsabilidades
├── 6. Atividades do processo
│   ├── POP humano
│   ├── contrato operacional
│   ├── prints anotados
│   ├── entradas e saídas
│   ├── critérios de aceite
│   ├── exceções
│   └── evidências
├── 7. Regras de decisão
├── 8. Rotinas
│   ├── frequência
│   ├── executor
│   ├── tempo previsto
│   └── SLA
├── 9. Indicadores
├── 10. Riscos e controles
├── 11. Histórico de versões
└── 12. Anexo AI-readable
```

### 12.1 Evolução já implementada no Book

O Book atual já incorporou parte importante da visão 3.0:

- o fluxo BPMN publicado é renderizado no Book a partir do `svg_snapshot`;
- a página do fluxo usa orientação **A4 paisagem**, melhorando a leitura e a impressão;
- o POP preserva as imagens dos passos;
- o tamanho ajustado da imagem no POP passa a ser refletido no Book por meio de `image_width`;
- a saída humana permanece limpa, sem exibir metadados técnicos como `BPMN: Activity_...` ou `Data Object: ...`;
- o Book continua consolidando fluxo, POP, rotinas e indicadores.

Pendências para Book 3.0 completo:

- incluir contrato operacional por atividade;
- incluir anexo AI-readable;
- incluir histórico formal de versões do processo/documento;
- incluir seção de riscos, controles e evidências auditáveis.

---

## 13. MVP recomendado

### Situação atual do MVP

```text
Fase 1 — BPMN como fluxo editável ................ IMPLEMENTADA
Fase 2 — Vincular atividade BPMN ao POP .......... IMPLEMENTADA PARCIALMENTE
Fase 3 — Contrato operacional da atividade ....... PENDENTE
Fase 4 — Manifesto AI-readable ................... PENDENTE
Fase 5 — Book do Processo 3.0 .................... IMPLEMENTADA PARCIALMENTE
Fase 6 — Copiloto de POP ......................... INICIADO NA CAPTURA DE PRINTS
Fase 7 — Squad de Agentes da Empresa ............. CONCEITUAL
Fase 8 — Squad de Arquitetura e Modelagem ........ CONCEITUAL
```

O MVP real já validou o fluxo principal:

```text
Modelar BPMN no APP32
→ publicar versão
→ exibir fluxo publicado no processo e no Book
→ detectar atividade marcada por Data Object Reference
→ abrir/criar atividade POP vinculada
→ documentar passos com texto, print colado e tamanho de imagem
→ imprimir Book com fluxo em paisagem e POP preservado
```

### Fase 1 — BPMN como fluxo editável

Objetivo:

- importar `.bpmn` do Bizagi;
- visualizar BPMN no APP32;
- salvar XML BPMN no PostgreSQL;
- renderizar o BPMN no Book.

Escopo visual e mecânico do Modeler:

- criar um **APP32 Modeler** com experiência familiar a ferramentas BPMN como Bizagi, porém com identidade visual própria do APP32;
- usar elementos BPMN padrão: eventos, atividades, gateways, subprocessos, conectores, pools, lanes, data objects, grupos e anotações;
- suportar mecânicas esperadas de modelagem: drag-and-drop, palette lateral, canvas central, context pad, conexão entre elementos, edição de rótulos, zoom, pan, undo/redo, importação e exportação `.bpmn`;
- evitar cópia pixel-perfect, marca, ícones proprietários, layout protegido ou identidade visual específica de terceiros;
- priorizar interoperabilidade BPMN 2.0 sobre reprodução proprietária de ferramenta.

Diretriz:

> Podemos criar uma experiência "familiar ao Bizagi" por compartilhar a notação BPMN, mas o produto deve ser juridicamente e visualmente APP32.

Critério de sucesso:

> Um processo deixa de depender exclusivamente de imagem e passa a ter um fluxo BPMN editável e versionável.

Status em 25/04/2026:

> Implementado no APP32 BPMN Modeler com `bpmn-js` local, persistência em `process_bpmn_diagrams`, exportação `.bpmn`, publicação de versão e renderização do fluxo publicado no processo/Book.

### Fase 2 — Vincular atividade BPMN ao POP

Objetivo:

- associar `bpmn_element_id` a uma atividade POP;
- clicar em uma atividade do fluxo e abrir o POP correspondente;
- usar **Data Object Reference** associado à atividade BPMN como marcador explícito de que aquela atividade deve abrir/criar atividade no POP;
- validar atividades BPMN sem POP associado quando elas possuírem o marcador Data Object Reference.

Critério de sucesso:

> Toda atividade relevante do fluxo pode possuir documentação operacional vinculada.

Status em 25/04/2026:

> Implementado parcialmente. O Data Object Reference funciona como marcador prático de atividade documentável. A rotina POP é criada/aberta com `bpmn_element_id`, `bpmn_element_type` e `bpmn_data_objects`. Falta evoluir validações formais de completude e checklist de atividades marcadas sem POP aprovado.

### Fase 3 — Contrato operacional da atividade

Objetivo:

- criar campos estruturados de entrada, saída, exceção, critério de aceite, sistema, permissão e evidência;
- gerar JSON operacional por atividade.

Critério de sucesso:

> A atividade deixa de ser apenas texto livre e passa a ser entendível por humano, sistema e IA.

Status em 25/04/2026:

> Pendente. Esta passa a ser a próxima camada de maturidade após estabilizar o vínculo BPMN → POP.

### Fase 4 — Manifesto AI-readable

Objetivo:

- gerar manifesto JSON do processo;
- expor manifesto por endpoint interno;
- futuramente expor via MCP tenant-safe.

Critério de sucesso:

> Uma IA consegue ler o processo e entender o que deve ser executado, validado e monitorado.

Status em 25/04/2026:

> Pendente. O caminho foi preparado pela estrutura BPMN/POP, mas ainda falta gerar o contrato AI-readable canônico.

### Fase 5 — Book do Processo 3.0

Objetivo:

- consolidar BPMN, POP, contratos, prints, rotinas, indicadores e manifesto em uma saída única.

Critério de sucesso:

> O Book passa a ser uma peça completa para treinamento, auditoria, operação e inteligência artificial.

Status em 25/04/2026:

> Implementado parcialmente. O Book já mostra o BPMN publicado em paisagem, preserva POP, prints e tamanho de imagem. Ainda faltam contrato operacional, manifesto AI-readable, riscos/controles e histórico formal de versão documental.

### Fase 6 — Copiloto de POP

Objetivo:

- criar fluxo assistido para transformar print + anotação em passo de POP;
- gerar simultaneamente versão humana e versão IA;
- permitir revisão humana antes da publicação;
- salvar metadados estruturados da tela, campos e observações.

Critério de sucesso:

> Um usuário consegue documentar uma etapa operacional com print e anotação simples, e o APP32 gera um POP revisável com campos humanos e AI-readable preenchidos.

Status em 25/04/2026:

> Iniciado. Já é possível colar print diretamente no passo do POP com Ctrl+V. Falta a IA transformar print + anotação em conteúdo estruturado humano e AI-readable.

### Fase 7 — Squad de Agentes da Empresa

Objetivo:

- criar agentes consultivos por área, função, macroprocesso ou processo;
- iniciar com agentes funcionais, como Agente Comercial, Agente Financeiro, Agente de Compras, Agente de Operações e Agente de Auditoria, Governança e Risco;
- consumir manifesto IA, BPMN, POP, rotinas, indicadores, medições, estratégia e financeiro;
- interagir com gestores e donos de processo;
- gerar alertas, diagnósticos, perguntas e recomendações;
- incluir papel específico de Auditoria, Governança e Risco para achados preliminares, testes de controle e validação de evidências;
- manter gate humano para decisões e alterações relevantes.

Critério de sucesso:

> O gestor recebe um agente parceiro, contextualizado pelos dados reais do APP32 e pelo conhecimento documentado no POP para IA, capaz de apoiá-lo na execução, monitoramento e melhoria dos resultados sob sua responsabilidade.

### Fase 8 — Squad de Arquitetura e Modelagem de Processos

Objetivo:

- criar um agente/arquiteto assistente para apoiar a estruturação da arquitetura de processos;
- ajudar a definir macroprocessos, processos, objetivos, sub-objetivos, rotinas, indicadores, donos e equipe executora;
- transformar conhecimento do arquiteto humano em arquitetura modelada e documentada;
- gerar rascunhos de BPMN, POP humano e POP para IA;
- aplicar checklist de coerência antes da publicação.

Critério de sucesso:

> O arquiteto humano consegue estruturar uma área ou macroprocesso com apoio de um agente que organiza, critica e propõe arquitetura, modelagem, rotinas, indicadores e papéis, mantendo validação humana como condição de publicação.

---

## 14. Integração com Sapiens e agentes

O domínio canônico para esta evolução deve ser `processes`.

Possíveis capabilities futuras:

```text
processes.get_process_manifest
processes.get_process_book_context
processes.get_activity_contract
processes.search_operational_steps
processes.validate_process_documentation
processes.list_process_gaps
```

Guardrails:

- `company_id` obrigatório em toda tool.
- Surface `user` apenas para leitura operacional permitida.
- Escritas e publicação de versão devem exigir autorização compatível.
- Agentes não devem executar mutações críticas sem gate humano.

---

## 15. Riscos técnicos

### 14.1 Duplicidade entre POP, rotina e atividade

O APP32 já possui `process_routines`, `process_steps` e `routines`. A evolução deve evitar criar uma terceira semântica confusa.

Recomendação:

> Definir claramente a diferença entre atividade documental, rotina agendada e instância executada.

### 14.2 Acoplamento excessivo no template

Parte relevante da UI atual de processo está no template. A evolução deve modularizar JS/CSS e mover regra de negócio para services.

### 14.3 Versionamento

Processos documentados precisam de versão. Um Book emitido em uma data deve poder ser reproduzido no futuro.

### 14.4 Importação de BPMN externo

Nem todo BPMN importado do Bizagi estará limpo ou padronizado. Será necessário validar:

- elementos sem nome;
- atividades duplicadas;
- gateways sem condição;
- atividades sem POP;
- pools/lanes incompatíveis;
- IDs instáveis.

### 14.5 IA interpretando imagem sem metadados

Prints são úteis, mas não devem ser a fonte primária para IA. A fonte primária deve ser o manifesto estruturado.

### 15.6 Publicação automática indevida

O Copiloto de POP não deve publicar procedimento oficial sem revisão humana.

Risco:

- IA interpretar tela incorretamente;
- IA omitir exceção importante;
- IA sugerir preenchimento inadequado;
- IA confundir regra local com regra geral.

Mitigação:

- status `draft_ai_generated`;
- revisão obrigatória;
- trilha de auditoria;
- versão oficial apenas após aprovação.

---

## 16. Decisões arquiteturais propostas

1. Adotar BPMN 2.0 como padrão de fluxo visual e interoperável.
2. Manter POP como camada humana de instrução operacional.
3. Criar contrato operacional estruturado para cada atividade relevante.
4. Gerar manifesto AI-readable por processo.
5. Evoluir o Book atual para Book do Processo 3.0.
6. Persistir BPMN XML no PostgreSQL, sempre com `company_id`.
7. Mapear `bpmn_element_id` para atividade POP/operacional.
8. Usar services para geração, validação e exportação.
9. Preparar leitura MCP tenant-safe para agentes.
10. Tratar DMN como evolução posterior para regras complexas de decisão.
11. Separar explicitamente a versão humana da versão IA.
12. Criar Copiloto de POP com captura assistida por print, anotação e navegação autorizada.
13. Exigir validação humana antes de publicar conteúdo gerado por IA.
14. Criar, como evolução posterior, um Squad de Agentes da Empresa.
15. Usar o POP para IA como base de conhecimento operacional desses agentes.
16. Diferenciar fato, inferência e recomendação em toda análise agentic.
17. Permitir agentes funcionais por área de gestão, como Comercial, Financeiro, Compras, Operações, Pessoas e Auditoria/Governança/Risco.
18. Criar um Squad de Arquitetura e Modelagem de Processos para apoiar a estruturação inicial e evolução da arquitetura operacional da empresa.
19. Iniciar esse squad como agente orquestrador único e evoluir para múltiplos agentes especializados quando houver maturidade.

---

## 17. Referências

- BPMN 2.0.2 — Object Management Group: https://www.omg.org/spec/BPMN/2.0.2/
- DMN — Object Management Group: https://www.omg.org/dmn/index.htm
- bpmn-js — BPMN 2.0 viewer/editor para browser: https://bpmn.io/toolkit/bpmn-js
- bpmn.io — toolkits para BPMN, DMN, CMMN e Forms: https://bpmn.io/

---

## 18. Conclusão

O APP32 - BPMN deve ser concebido como uma evolução estratégica do módulo de processos, não apenas como um editor de desenhos.

O diferencial do APP32 está em unir aquilo que ferramentas tradicionais tratam separadamente:

- fluxo;
- POP;
- prints;
- rotina;
- executor;
- tempo;
- indicador;
- evidência;
- IA;
- operação real.

Com essa arquitetura, o APP32 pode superar o fluxo atual baseado em Bizagi + imagem + POP manual, criando uma base operacional viva, auditável, versionável e preparada para agentes de IA.

Síntese final:

> BPMN organiza o fluxo. POP ensina a pessoa. O contrato operacional orienta o sistema. O manifesto AI-readable orienta a IA. O Copiloto de POP acelera a captura do conhecimento real. O Squad de Arquitetura e Modelagem ajuda a desenhar a empresa. O Squad de Agentes da Empresa cria duplas gestor + agente para transformar conhecimento em performance. O Book do Processo une tudo em uma fonte única de verdade.
