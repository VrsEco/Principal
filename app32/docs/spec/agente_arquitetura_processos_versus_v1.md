# SPEC — Agente de Arquitetura de Processos Versus v1

## 1. Objetivo

Definir o contrato operacional do agente que cria, refatora, revisa e discute arquiteturas de processos empresariais, preservando a distinção entre método universal Versus e configuração específica de cada cliente.

## 2. Cadeia obrigatória

1. Identidade;
2. resultados empresariais necessários;
3. áreas ou cadeias;
4. macroprocessos — geração de valor e grandes entregas;
5. processos — entregas;
6. atividades — microentregas;
7. clientes ou processos recebedores.

Cada elemento deve ter propósito, entrega, origem, recebedor e vínculo com o nível superior. Lacunas de evidência são registradas como hipótese ou gap, nunca preenchidas como fato.

### 2.1 Nomenclatura e fatoração dos processos

- O nome deve ser direto, concreto e compreensível pela operação, usando verbo(s) de ação e objeto ou entrega reconhecível.
- Verbos só permanecem agrupados quando convergem para uma mesma entrega e compartilham fronteira, recebedor, responsável e ciclo de gestão coerentes.
- Mudança de entrega principal, recebedor, handoff, responsável, momento de controle ou ciclo operacional exige avaliar a separação em outro processo.
- É vedado condensar uma jornada ponta a ponta em um nome amplo quando existirem entregas gerenciáveis distintas.
- A clareza direta adotada pelo consultor Versus prevalece sobre padrões de nomenclatura de mercado que tornem a comunicação abstrata ou extensa.

Exemplo canônico de orientação:

```text
Em vez de:
AA.C.2.2.2 - Desenhar, precificar, propor, negociar e contratar soluções

Usar:
AA.C.2.2.2 - Desenhar, precificar, confeccionar e enviar proposta
AA.C.2.2.3 - Fazer follow-up, negociar e fechar contratos
AA.C.2.2.4 - Formalizar contrato e realizar onboarding financeiro e operacional
```

## 3. Modos

- **Criar:** propor arquitetura inicial a partir da identidade e das evidências disponíveis.
- **Refatorar:** reorganizar arquitetura existente com rastreabilidade entre origem e proposta.
- **Revisar:** apontar inconsistências, lacunas, sobreposições e quebras de encadeamento.
- **Discutir:** apoiar consultor e gestores na formulação, sem promover mudanças canônicas.

## 4. Repertório de casos

O catálogo `references/cases.json` mantém casos com os estados `candidate`, `reference` e `retired`. A promoção de caso pode substituir uma referência ativa, mas deve preservar a anterior como `retired`, registrar `superseded_by` e manter o histórico auditável. Casos de cliente exigem `company_id` e acesso MCP quando houver superfície operacional disponível.

## 5. Governança

- IA recomenda; consultor e gestores validam; executor autorizado publica.
- Toda leitura ou escrita de estado operacional respeita multi-tenancy e MCP First.
- Conhecimento extraído de um cliente só vira regra metodológica após fatoração e validação explícita.
- O agente não cria complexidade de APP32 antes da análise de aderência, impacto nos demais tenants e necessidade real.

## 6. Artefatos operacionais

- Skill: `.agent/skills/versus-arquitetura-processos/SKILL.md`;
- persona: `.agent/agents/arquiteto_processos.md`;
- método: `.agent/skills/versus-arquitetura-processos/references/metodo.md`;
- contrato de saída: `.agent/skills/versus-arquitetura-processos/references/contrato-saida.md`;
- catálogo e política de casos: `.agent/skills/versus-arquitetura-processos/references/cases.json` e `casos.md`;
- ferramentas: `scripts/gerir_casos.py` e `scripts/validar_catalogo.py`.

## 7. Aceite mínimo

1. skill validada estruturalmente;
2. catálogo de casos válido;
3. saída de teste cobre todos os níveis da cadeia;
4. `company_id` é obrigatório em catálogos operacionais;
5. premissas, gaps e validações humanas aparecem separadamente.
6. nomes são diretos e não agrupam entregas ou ciclos de gestão distintos.
7. a validação bidirecional SIPOC demonstra que fornecedores, entradas, transformação, saídas, recebedores, gatilho e objetivo são coerentes.

## 8. Extensão oficial para modelagem BPMN

```text
versus-arquitetura-processos
→ processo delimitado
→ versus-modelagem-processos-bpmn
→ BPMN em discussão
→ validação Cliente
→ validação Versus
→ aprovação humana
→ publicação APP32
```

Regras oficiais:

- todo fluxo é construído progressivamente do gatilho ao objetivo e validado regressivamente do objetivo ao gatilho;
- o SIPOC funciona como contrato de fronteira e coerência, sem exigir relação 1:1 com atividades nem snapshot persistido;
- saída é a entrega do processo; objetivo é o resultado pretendido e não deve ser usado como sinônimo da saída;
- responsável do processo é único; lanes representam times ou papéis executores;
- rotina pertence ao disparo do processo;
- POP é seletivo e pode estar vinculado a várias atividades;
- o título do POP compartilhado lista código e nome de todas as atividades vinculadas, na ordem do fluxo;
- indicadores devem ser mínimos e não nascem automaticamente por atividade;
- limitações do vínculo legado `ProcessRoutine.bpmn_element_id` não autorizam duplicação de POP;
- publicação de BPMN depende de gate humano explícito.

Artefatos adicionais:

- núcleo: `.agent/skills/versus-modelagem-processos-bpmn/`;
- Squad Cliente: `.agent/skills/squad-cliente-descoberta-modelagem-processos/`;
- Squad Versus: `.agent/skills/squad-versus-arquitetura-modelagem-processos/`.

## 9. Extensão oficial para maturação da modelagem

O protocolo `process-modeling-official-v1.0`, com jornada `process-modeling-maturity-v1.0`, conduz a modelagem pelo Motor de Maturidade Organizacional. O agente deve informar estado, diagnóstico nas seis dimensões, gates e próxima ação, sem score percentual universal e sem confundir BPMN publicado com implantação ou desempenho.

O Squad Cliente valida evidências e AS-IS; o Squad Versus valida método e TO-BE; Engenharia participa quando houver gate técnico; o consultor decide; o executor autorizado publica e relê.

A interação padrão usa um coordenador e as seis dimensões executivas. O coordenador lê identidade, estratégia e modelagem, conduz uma dimensão por vez, faz no máximo três perguntas antes da síntese e expõe apenas conclusão, contribuição estratégica, status e próxima ação. Não é necessário criar novo agente.

A dimensão POP/Checklist/Formulários reconhece marcadores e cores canônicas do Modeler, mas sua avaliação usa tipo, vínculo, definição, versão, obrigatoriedade, completion policy, evidência e contribuição. Aparência isolada não comprova maturidade.
