# 🧠 Arquitetura de Agentes (v2.1 - Body-Brain + Workflow-First)

**Última Atualização:** 16/04/2026  
**Versão:** 2.1  
**Status:** ✅ Oficial - OpenAI / LangGraph / MCP First

---

## 🎯 Filosofia "Body-Brain"
O sistema Gestão Versus opera sob separação clara entre execução operacional determinística e raciocínio assistido.

1. **O Corpo (App32):** APIs, CRUDs, tabelas SQL, workflows, políticas de segurança e surfaces.
2. **O Cérebro (Intelligence):** roteamento, LangGraph, memória, síntese, fallback controlado e orquestração de tools.

---

## 🧭 Princípio adicional: Workflow-First
Para Sapiens e canais operacionais, a ordem oficial é:

1. identificar intenção
2. mapear domínio/código oficial
3. resolver empresa e escopo
4. validar permissão
5. executar workflow determinístico
6. usar LLM apenas como fallback controlado

### Consequência prática
- linguagem natural é **entrada**, não licença para execução livre
- consulta operacional clara não deve cair em agente livre por parser fraco
- drift entre catálogo, RBAC e contratos é falha arquitetural

---

## 🏗️ Core Stack (Intelligence Layer)

- **Brain:** OpenAI + LangChain/LangGraph
- **Orquestração:** LangGraph (`StateGraph`) para fluxos cíclicos e roteados
- **Checkpointer:** PostgreSQL (`PostgresSaver` ou equivalente)
- **Memória vetorial / RAG:** ChromaDB quando aplicável
- **Governança operacional:** MCP First + RBAC por domínio + contexto multi-tenant

---

## 🧩 Tipos de Agentes

### 1. Supervisor / Router
Responsável por:
- analisar intenção
- selecionar workflow ou tool determinística
- decidir se existe necessidade real de fallback agentic

Não deve incorporar regra de negócio solta nem mascarar erro estrutural como falta de permissão do usuário.

### 2. Experts / Executors
Agentes especializados por domínio. Devem operar com:
- tools documentadas
- taxonomia canônica de domínio
- contexto explícito (`company_id`, `user_id`, canal, thread)
- política de confirmação proporcional ao risco

### 3. Workflow Executors do Sapiens
Camada orientada a canal/intent para:
- consultas operacionais
- mutações controladas
- reuniões
- resumos
- resoluções por escopo pessoal/equipe/empresa

---

## 🧾 Taxonomia canônica de domínio
A taxonomia é parte da governança, não detalhe de implementação.

### Domínios canônicos relevantes
- `routine`
- `projects`
- `processes`
- `meetings`
- `strategy`
- `finance`
- `analytics`
- `workload`
- `identity_self_service`
- `identity_admin`
- `governance`
- `operations`

### Aliases oficiais
- `work` -> `routine`
- `tasks` -> `routine`
- `worklog` -> `routine`

### Regra mandatória
Antes de passar por RBAC, policy, telemetria ou workflow resolution, o domínio deve estar normalizado para o nome canônico.

---

## 🔐 Segurança, contexto e multi-tenancy

### Regras de contexto
- toda operação com estado precisa respeitar `company_id`
- empresa explícita na mensagem tem precedência sobre empresa ativa da sessão
- canais externos não podem depender de `current_user`
- thread, canal e metadados precisam ser preservados na execução

### Regras de acesso
- `administrador`, `cliente` e `colaborador` podem ter leituras operacionais válidas, conforme escopo efetivo
- citar outro colaborador não implica bloqueio automático
- o sistema deve validar empresa, vínculo e escopo antes de negar acesso

---

## 💾 Memória e Estado

### Memória de Curto Prazo (Thread State)
Persistida no PostgreSQL para continuidade de conversa, retomada de sessão e execução auditável.

### Memória de Longo Prazo (RAG)
Usada apenas quando agrega valor real à resposta. Não substitui workflow determinístico nem consulta operacional governada.

---

## 🔌 Regras de Implementação

1. **Streaming:** chamadas de IA devem suportar streaming quando a surface exigir melhor UX.
2. **Prompt Management:** evitar prompt solto em rota; preferir camadas próprias de intelligence.
3. **MCP First:** quando houver estado operacional, tenant, auditoria ou mutação, priorizar MCP/workflow oficial.
4. **Taxonomia canônica:** novas capabilities devem nascer com domínio canônico, nunca com alias legado como fonte de verdade.
5. **Confirmação proporcional:**
   - confirmar mutações, ambiguidade real e ações sensíveis
   - evitar confirmação desnecessária em consulta read-only clara
6. **WhatsApp:** se houver múltiplas empresas elegíveis, a escolha da empresa vem antes da confirmação final.
7. **Observabilidade:** bloqueios reais devem informar causa auditável correta: tenant, perfil, escopo, domínio ou dado faltante.

---

## 🚫 O que NÃO fazer
- NUNCA usar taxonomia legada solta como se fosse canônica.
- NUNCA publicar capability em domínio que não exista nos contratos e na policy.
- NUNCA cair em agente livre apenas porque o parser não reconheceu um verbo operacional simples.
- NUNCA mascarar drift estrutural como “usuário sem acesso”.
- NUNCA ignorar `thread_id`, `company_id` e contexto de canal.

---

## 📚 Referências associadas
- `C:\GestaoVersus\app32\app32\docs\architecture\TAXONOMIA_CANONICA_SAPIENS_APP32.md`
- `C:\GestaoVersus\app32\app32\.agent\skills\gestao_versus_core\SKILL.md`
- `C:\GestaoVersus\app32\app32\.agent\skills\sapiens-workflow-first\SKILL.md`

---

**Responsável:** AI Lead Designer
