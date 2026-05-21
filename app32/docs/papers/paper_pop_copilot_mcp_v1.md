# Paper — POP Copilot Multimodal via MCP

Status: em evolução  
Classe: Paper

## 1. Tese

O POP do APP32 deve evoluir para um modelo **multimodal e assistido por MCP**, onde:

- a **ferramenta** concentra captura, revisão e publicação;
- o **MCP** concentra análise, sugestão, orquestração e integração;
- a **intervenção humana continua obrigatória** para validar clareza, segurança e aderência operacional.

## 2. Problema

Hoje, a produção de POP tende a ser cara porque exige:

- captura manual de prints;
- redação manual dos passos;
- organização visual do documento;
- revisão para garantir que o procedimento esteja correto;
- cuidado com dados sensíveis presentes nas telas.

Além disso, muitos POPs tratam de:

- operação de sistemas;
- execução de rotinas administrativas;
- navegação em telas com múltiplos campos, menus e botões;
- atividades em que a explicação verbal do operador é tão importante quanto a imagem.

## 3. Hipótese central

O melhor caminho não é um único modo de geração, e sim um **POP Studio + POP Copilot**.

### POP Studio
Camada da ferramenta para:

- upload de vídeo, prints e anexos;
- gravação de áudio/narração;
- revisão de frames;
- edição dos passos;
- aprovação e publicação.

### POP Copilot
Camada MCP para:

- transcrição de áudio;
- extração de frames-chave;
- OCR e leitura de telas;
- sugestão de passos e descrições;
- detecção de lacunas;
- sugestão de automações e integrações;
- vínculo com Fluxo, Rotina e Indicadores.

## 4. Modos de entrada recomendados

O POP Copilot deve aceitar quatro modos principais:

1. **prints + texto/áudio**  
   caminho mais simples e rápido para MVP;

2. **gravação de tela com narração**  
   melhor relação entre contexto, qualidade e esforço do usuário;

3. **vídeo da execução correta**  
   útil para segmentar etapas e produzir tutorial visual;

4. **execução assistida da IA em ambiente controlado**  
   modo avançado, com sandbox, credenciais seguras e revisão humana obrigatória.

## 5. O que fica na ferramenta

- captura e upload de evidências;
- timeline visual;
- seleção/remoção de prints;
- edição do texto dos passos;
- ordenação manual;
- comparação entre rascunho e publicado;
- preview do POP final;
- aprovação humana.

## 6. O que fica no MCP

- análise multimodal;
- extração de keyframes;
- transcrição e alinhamento fala ↔ tela;
- geração de rascunho estruturado;
- sugestão de automação/conexão;
- detecção de dados sensíveis;
- checagem de consistência com o Fluxo.

## 7. Princípio operacional

> O MCP não “substitui o operador” na autoria final do POP.  
> O MCP reduz o trabalho pesado, prepara o rascunho e amplia a qualidade da documentação.

## 8. Saídas esperadas

Um POP maduro deve poder gerar simultaneamente:

- **documento POP estruturado**;
- **passo a passo com prints**;
- **roteiro de treinamento**;
- **vídeo tutorial com legendas**, quando houver mídia suficiente.

## 9. Riscos principais

- excesso de frames irrelevantes;
- transcrição com ambiguidade;
- erro na interpretação de telas;
- vazamento de dados sensíveis em prints;
- automação sugerida sem contexto suficiente;
- tentativa prematura de deixar a IA operar sistemas reais sem sandbox.

## 10. Guardrails inegociáveis

- multi-tenancy com `company_id`;
- mascaramento/revisão de dados sensíveis;
- revisão humana antes da publicação;
- separação entre rascunho gerado e versão oficial;
- uso de ambiente controlado para execução assistida;
- MCP First para orquestração operacional e integrações.

## 11. Sequência recomendada de evolução

### Recorte MVP implementado em 2026-05-20
- o sistema passa a aceitar **vídeo curto por passo** no detalhe do processo;
- o vídeo deve representar **um passo**, não o POP inteiro;
- o usuário pode:
  - anexar vídeo curto em MP4/WebM;
  - visualizar o vídeo no passo;
  - capturar o frame atual do vídeo para transformá-lo em print do POP;
- adicionar **narração/contexto do operador** no próprio passo;
- pedir à IA um **rascunho inicial da descrição** com base no contexto já salvo;
- o MCP passa a enxergar o contexto multimídia básico do passo para orientar próximos passos.

### Onda 1 — MVP forte
- prints + texto/áudio;
- geração de rascunho do POP;
- revisão e publicação pela ferramenta.

### Onda 2 — ganho de produtividade real
- gravação de tela com narração;
- extração automática de passos e prints.

### Onda 3 — experiência premium
- vídeo tutorial legendado;
- roteiro de treinamento derivado do POP.

### Onda 4 — modo avançado
- execução assistida da IA em ambiente controlado;
- geração semiautomática de POP a partir da navegação guiada.

## 12. Decisão sobre agentes

Neste momento, **não é necessário criar um agente novo**.

O tema cabe melhor na composição:

- `@ARQUITETO` para boundary, governança e desenho do workspace;
- `@AI_ENGINEER` para pipeline multimodal, MCP e copiloto;
- `@BACKEND_API` para surfaces, contratos e publicação;
- `@QA_AUTOMATION` para validação, evidência e segurança operacional.

Se no futuro surgir uma operação recorrente de captura massiva, análise multimídia e publicação assistida de POPs, pode fazer sentido criar um agente especializado.
