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
