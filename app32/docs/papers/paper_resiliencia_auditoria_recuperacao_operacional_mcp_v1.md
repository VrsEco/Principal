# Paper Conceitual — Resiliência, Auditoria e Recuperação Operacional para MCP e Squads v1

Status: conceitual para amadurecimento e posterior fatiamento em SPEC, Playbook e Runbook  
Escopo: PostgreSQL, PITR, WAL, trilha auditável, operações MCP, Squads, multi-tenancy com `company_id`, undo seletivo, gates de segurança e governança operacional

## 1. Objetivo

Definir a direção arquitetural para proteger o APP32 / Gestão Versus contra erros operacionais de alto impacto causados por:

- usuário humano
- operador interno
- automação de sistema
- MCP remoto
- Squads e agentes com capacidade de mutação

Este paper existe para amadurecer três perguntas centrais:

1. como recuperar o banco para um ponto anterior com previsibilidade
2. como registrar cada ação relevante com trilha forte e tenant-safe
3. como reduzir a chance de uma ação destrutiva acontecer sem controle

Ele ainda não congela a implementação oficial.  
Seu papel é consolidar a tese, os princípios e o desenho recomendado antes da passagem para SPEC.

---

## 2. Problema estrutural

O APP32 está entrando em uma fase em que o risco operacional deixa de ser apenas:

- bug de tela
- erro manual isolado
- alteração pontual de cadastro

E passa a incluir:

- execução rápida de comandos de alto alcance
- automação assistida por MCP
- agentes e squads capazes de operar em múltiplas entidades
- mutações em lote com baixa fricção operacional
- decisões que podem afetar dados, processos e contexto de várias áreas

### Tese do problema

> Quanto maior a capacidade de ação do runtime MCP + Squads, maior precisa ser a capacidade de rastrear, conter e reverter efeitos operacionais.

Sem isso, a potência da automação vira passivo sistêmico.

---

## 3. Tese central

> O APP32 não deve depender de uma única camada de proteção. A arquitetura correta combina recuperação do banco, auditoria imutável e gates de segurança operacional.

### Tradução prática

A solução robusta não é:

- apenas backup
- apenas log técnico
- apenas confirmação humana
- apenas regra de permissão

A solução robusta é a combinação de quatro capacidades:

1. **recuperação global do banco** para desastre amplo
2. **auditoria de negócio append-only** para rastrear quem fez o quê
3. **undo seletivo por entidade e tenant** para corrigir erro localizado
4. **gates de alto impacto** para evitar mutações perigosas sem controle

---

## 4. Princípios inegociáveis

## 4.1 Multi-tenancy obrigatório

Toda trilha, toda leitura e toda mutação devem preservar:

- `company_id`
- `user_id` quando houver ator humano
- `actor_type` quando houver agente, sistema ou automação
- `surface` de origem da ação

### Regra

> Não existe auditoria confiável no APP32 sem escopo explícito de tenant.

---

## 4.2 MCP First com governança explícita

Se a operação acontece via MCP, a governança não pode estar fora do MCP.

Isso significa que o runtime deve carregar, por request:

- identidade do ator
- `company_id`
- perfil efetivo
- surface efetiva
- contexto de aprovação, quando aplicável

### Consequência

Toda tool de mutação precisa ser tratada como evento operacional auditável, e não como mero detalhe técnico do transporte.

---

## 4.3 Sem confiança em reversão improvisada

Confiar que a equipe "depois dá um jeito no banco" não escala.

A reversão precisa nascer como capacidade arquitetural explícita.

---

## 4.4 Separação entre recuperação global e correção localizada

Recuperar o banco inteiro e desfazer uma única ação são problemas diferentes.

### Regra

- **PITR** resolve desastre global
- **undo seletivo** resolve erro localizado

Misturar os dois leva a restaurações excessivas, downtime desnecessário e risco de afetar tenants não envolvidos.

---

## 5. Capacidade 1 — Recuperação global do banco

## 5.1 Direção recomendada

Para PostgreSQL, a direção correta é adotar:

- **base backup periódico**
- **arquivamento contínuo de WAL**
- **Point-in-Time Recovery (PITR)**

### Motivo

Esse modelo permite:

- restaurar o banco para um instante específico
- reduzir perda de dados em incidentes graves
- evitar a necessidade de full backups em intervalos agressivos

---

## 5.2 O que PITR resolve bem

PITR é a resposta certa para:

- exclusão ou corrupção massiva
- bug de mutação em larga escala
- deploy com efeito destrutivo no banco
- ação indevida de tool privilegiada
- incidente estrutural que exige restauração ampla

---

## 5.3 O que PITR não resolve sozinho

PITR não é suficiente para:

- desfazer só uma alteração de uma empresa sem tocar no resto
- explicar com precisão quem causou o problema
- reconstruir intenção, aprovação e contexto da ação
- oferecer replay reverso por entidade

### Conclusão

> PITR é necessário, mas insuficiente como solução única.

---

## 5.4 Frequência e impacto

A prática recomendada não é gerar backup completo de poucos em poucos minutos.

O desenho mais saudável tende a ser:

- base backup diário ou em janela previsível
- WAL contínuo
- retenção compatível com RPO e RTO definidos
- cópia externa/offsite
- teste recorrente de restore

### Tese operacional

> O custo correto deve recair mais em armazenamento e governança de restore do que em full backup excessivo com impacto desnecessário no banco.

---

## 5.5 Objetivos operacionais que precisam existir

Resiliência sem meta operacional explícita tende a virar discurso genérico.

Por isso, este tema precisa ser amarrado a pelo menos quatro noções:

- **RPO** — quanto de dado a empresa aceita perder
- **RTO** — quanto tempo o sistema pode ficar sem operar
- **escopo de restore** — banco inteiro, tenant, domínio ou entidade
- **janela de retenção** — por quanto tempo o passado continua recuperável

### Regra conceitual

> PITR só é governança real quando estiver vinculado a objetivos operacionais claros, e não apenas a “ter backup”.

### Consequência

No amadurecimento posterior, o APP32 precisa declarar oficialmente:

- RPO alvo por ambiente
- RTO alvo por ambiente
- retenção mínima de backups e WAL
- quais incidentes exigem restore total
- quais incidentes devem preferir undo seletivo

---

## 6. Capacidade 2 — Trilha auditável forte de negócio

## 6.1 O que o sistema precisa registrar

O APP32 precisa registrar não só requisições HTTP, mas eventos de negócio e eventos operacionais.

### Isso inclui

- criação
- edição
- exclusão
- aprovação
- rejeição
- execução de tool MCP
- ações em lote
- mudanças de configuração sensível
- troca de empresa ativa quando isso alterar escopo operacional

---

## 6.2 O que não basta

Não basta ter apenas:

- log de servidor
- log de erro
- log de rota
- histórico genérico de chat

Esses artefatos ajudam na observabilidade, mas não substituem uma trilha formal de auditoria.

---

## 6.3 Modelo conceitual recomendado

A direção recomendada é uma tabela canônica de eventos append-only, por exemplo `audit_event`, com dados como:

- `id`
- `created_at`
- `company_id`
- `user_id`
- `actor_type`
- `surface`
- `request_id`
- `trace_id`
- `entity_type`
- `entity_id`
- `action`
- `before_data` em JSONB
- `after_data` em JSONB
- `diff_data` em JSONB
- `reason`
- `approval_id`
- `tool_name`
- `risk_level`

### Regra

> O evento de auditoria deve nascer como fato imutável, não como relatório reconstruído depois.

---

## 6.4 Onde a auditoria deve ser gravada

A trilha principal deve ser registrada no **service layer** ou em boundary transacional equivalente.

Não é o lugar correto:

- depender só da rota Flask
- depender só do frontend
- depender só do agente
- depender só de trigger invisível sem contexto de negócio

### Motivo

O service layer é o ponto em que convivem:

- intenção
- ator
- escopo de tenant
- entidade
- mutação real
- contexto de aprovação

---

## 6.5 Integridade da trilha

A auditoria precisa ser:

- append-only
- protegida contra alteração banal
- mascarada para segredos e dados sensíveis desnecessários
- indexada por `company_id`, tempo, ator e entidade

Em estágios mais maduros, pode evoluir para:

- hash encadeado entre eventos
- envio para storage imutável externo
- integração com SIEM ou lakehouse de auditoria

---

## 6.6 Taxonomia mínima do evento de auditoria

Para não virar um superlog amorfo, a trilha precisa nascer com taxonomia mínima.

### O evento precisa responder

1. **quem** agiu
2. **em nome de quem** agiu
3. **em qual tenant** agiu
4. **por qual canal/surface** agiu
5. **sobre qual entidade** agiu
6. **qual ação** foi tentada
7. **qual ação** foi efetivamente aplicada
8. **com qual impacto esperado**
9. **com qual aprovação**
10. **com qual resultado**

### Tradução arquitetural

Isso implica separar no evento, de forma explícita:

- ator humano
- ator sistêmico
- agente/squad executor
- trigger de origem
- entidade alvo
- escopo do lote
- estado antes
- estado depois
- diff calculado
- resultado final

### Benefício

Essa taxonomia evita três falhas comuns:

- log bonito que não explica o incidente
- trilha técnica sem semântica de negócio
- dado suficiente para acusar alguém, mas insuficiente para reverter com segurança

---

## 6.7 Auditoria não é lugar para despejar tudo

Uma trilha forte não significa registrar payload bruto de forma irresponsável.

### A auditoria deve evitar

- segredos em claro
- tokens
- credenciais
- dados sensíveis sem necessidade de reconstrução
- blobs enormes que inviabilizam consulta e retenção

### Direção correta

O evento deve carregar:

- contexto suficiente para investigação
- diffs úteis para reversão
- referências para artefatos externos quando o payload completo for pesado
- mascaramento/redaction por padrão em campos sensíveis

### Regra

> A auditoria precisa maximizar rastreabilidade sem virar vazamento permanente de informação.

---

## 7. Capacidade 3 — Undo seletivo e reconstrução localizada

## 7.1 Por que isso é necessário

No APP32 multi-tenant, muitas falhas não exigem restaurar o banco todo.

Exemplos:

- alteração errada de um processo
- exclusão lógica indevida de registros de uma empresa
- mutação em lote errada dentro de um único domínio
- tool MCP acionada com parâmetro incorreto

Nesses casos, restaurar o banco inteiro pode causar dano colateral.

---

## 7.2 Direção recomendada

O APP32 deve caminhar para suportar reversão seletiva baseada em:

- `company_id`
- entidade afetada
- intervalo temporal
- trilha `before/after/diff`

### Interpretação

O objetivo não é prometer um botão mágico universal de undo para tudo.

O objetivo é identificar domínios críticos em que a reversão localizada precisa ser capacidade de primeira classe.

---

## 7.3 Classes de reversão

A maturidade recomendada pode seguir três níveis:

### Nível 1 — reconstrução assistida
- leitura da auditoria
- reexecução manual segura
- apoio operacional humano

### Nível 2 — undo guiado por serviço
- serviços dedicados para reverter entidades críticas
- validação de tenant, estado atual e pré-condições

### Nível 3 — replay reverso controlado
- geração automática de plano de reversão
- dry-run
- aprovação humana
- execução auditada

---

## 7.4 Nem toda entidade precisa nascer com undo pleno

Tentar dar undo universal para todo o sistema no primeiro momento tende a produzir complexidade cara e frágil.

### A pergunta correta não é

- “como desfazer tudo?”

### A pergunta correta é

- “quais domínios têm custo de erro alto o suficiente para justificar reversão estruturada?”

### Critérios de prioridade

Entidades devem entrar primeiro na trilha de undo seletivo quando tiverem:

- alta frequência de mutação
- alto custo de erro
- alto risco de mutação em lote
- baixa tolerância a indisponibilidade
- impacto grande em operação, finanças ou governança

### Consequência

O desenho recomendado é começar por um conjunto pequeno de entidades críticas e expandir com evidência operacional, não por ambição abstrata.

---

## 8. Capacidade 4 — Gates de segurança para MCP e Squads

## 8.1 Princípio

Quanto maior o alcance de uma tool, maior deve ser o atrito de segurança.

### Isso significa

Ferramentas capazes de:

- mutar em lote
- atuar em domínio sensível
- tocar múltiplas entidades
- afetar finanças
- alterar configuração estrutural

não devem rodar apenas porque o agente “entendeu” a intenção.

---

## 8.2 Controles recomendados

Para operações sensíveis, a direção correta é combinar:

- classificação de risco
- dry-run obrigatório
- escopo explícito por `company_id`
- resumo do impacto esperado
- confirmação humana quando houver alto impacto
- trilha de aprovação vinculada ao evento executado

---

## 8.3 Regra especial para domínio financeiro

No APP32, `finance` é domínio canônico sensível.

### Consequência

Mutações financeiras ou administrativas críticas não devem estar expostas em surface operacional de menor privilégio sem gate reforçado.

---

## 8.4 Observabilidade de ação perigosa

Além da auditoria histórica, o runtime deve conseguir alertar sobre:

- volume anormal de mutações
- sequência incomum de exclusões
- operação massiva fora da janela esperada
- tentativa de ação cross-tenant
- uso de tool privilegiada sem trilha de aprovação válida

---

## 8.5 Classificação conceitual de risco

Nem toda mutação precisa do mesmo peso de controle.

Uma taxonomia inicial útil é:

### Risco 0 — baixo impacto
- alteração pequena
- escopo unitário
- reversão simples
- sem sensibilidade financeira

### Risco 1 — impacto moderado
- mutação relevante em entidade importante
- lote pequeno
- impacto localizado por tenant

### Risco 2 — alto impacto
- ação em lote
- alteração estrutural
- domínio sensível
- potencial de parada operacional

### Risco 3 — crítico
- efeito massivo
- múltiplos domínios
- potencial cross-tenant
- mutação financeira ou administrativa crítica
- possibilidade de dano sistêmico relevante

### Regra

> O gate não deve ser decidido pela tool em abstrato, mas pela combinação entre tool, escopo, domínio, volume e surface.

---

## 8.6 Protocolo conceitual de aprovação

Para operações de alto impacto, a aprovação precisa ser modelada como parte da operação, e não como mensagem informal.

### A aprovação idealmente precisa vincular

- quem solicitou
- quem aprovou
- qual ação foi aprovada
- em qual tenant
- em qual intervalo temporal
- com qual escopo máximo
- por quanto tempo a autorização vale

### Consequência

O `approval_id` não deve ser apenas um texto solto.  
Ele precisa representar um artefato operacional verificável.

### Regra

Uma execução não deve reaproveitar aprovação antiga fora de contexto, fora de escopo ou fora da janela de validade.

---

## 8.7 Contenção ativa e kill switch

Além de prevenir e auditar, o APP32 precisa poder conter.

### Isso significa ter mecanismos para

- bloquear temporariamente tools de alto risco
- pausar superfícies de mutação específicas
- rebaixar o sistema para modo leitura em incidentes graves
- exigir aprovação reforçada após comportamento anômalo

### Tese

> Um sistema com automação forte sem capacidade de contenção ativa é rápido para errar e lento para parar de errar.

---

## 9. Camadas de log que não devem ser confundidas

## 9.1 Log técnico

Serve para:

- debug
- performance
- falha
- tracing
- observabilidade

## 9.2 Log de auditoria de negócio

Serve para:

- compliance
- responsabilização
- reconstrução de contexto
- suporte a reversão

## 9.3 Log de execução MCP / agente

Serve para:

- explicar qual tool rodou
- com qual escopo
- por qual ator
- com qual aprovação
- com qual resultado

### Regra

> Os três tipos são complementares. Nenhum substitui o outro.

---

## 10. Riscos de desenho que devem ser evitados

O APP32 deve evitar:

- confiar só em backup lógico simples
- restaurar banco inteiro para corrigir erro localizado
- gravar auditoria sem `company_id`
- permitir mutação privilegiada sem `request_id` e `trace_id`
- registrar eventos apenas no frontend
- depender de logs informais para investigação crítica
- deixar tool perigosa sem gate humano e sem dry-run
- tratar auditoria como relatório opcional em vez de capability estrutural

### Anti-pattern adicional

Também deve evitar o falso conforto de:

- “temos backup, então estamos seguros”
- “o banco restaura, depois entendemos o resto”
- “o log de request já resolve auditoria”
- “o agente sabe o que está fazendo”
- “a aprovação estava no chat, então está valendo”

---

## 11. Direção de maturidade recomendada

## 11.1 Fase 1 — fundação obrigatória

- PITR com WAL archiving
- política de retenção definida
- rotina real de teste de restore
- tabela canônica `audit_event`
- registro de mutações críticas no service layer
- rastreio de ações MCP com `company_id`, `actor_type`, `tool_name` e `approval_id`

## 11.2 Fase 2 — endurecimento operacional

- diffs por entidade crítica
- dashboard de auditoria operacional
- alertas de mutação de alto risco
- catálogo de operações que exigem dry-run e confirmação humana
- primeiros fluxos de undo seletivo

## 11.3 Fase 3 — maturidade enterprise

- hash chain de eventos
- storage externo imutável
- CDC a partir de WAL
- replay reverso controlado em domínios prioritários
- integração com trilha formal de governança e compliance

---

## 12. Decisões conceituais que este paper propõe

Este paper propõe como direção:

1. **backup e auditoria são problemas diferentes e ambos são obrigatórios**
2. **PITR deve ser a base da recuperação global do PostgreSQL**
3. **o APP32 precisa de auditoria append-only orientada a negócio, não só a request**
4. **o desenho multi-tenant exige reversão seletiva por `company_id` onde houver domínio crítico**
5. **MCP e Squads precisam de gates explícitos para operações de alto impacto**
6. **a governança correta é preventiva, detetiva e corretiva ao mesmo tempo**

---

## 13. O que ainda precisa virar SPEC

Este paper ainda não define oficialmente:

- esquema final da tabela `audit_event`
- catálogo oficial de risk levels
- contrato oficial de `approval_id`
- lista de tools de alto impacto
- política oficial de retenção
- RPO e RTO do ambiente de produção
- domínios que terão undo seletivo na fase inicial

Esses pontos devem ser congelados em SPEC posterior.

---

## 14. Encaminhamento recomendado

A sequência natural após este paper é:

1. criar uma **SPEC de arquitetura oficial** para resiliência e auditoria operacional
2. criar um **Playbook** para classificação de risco e gates de mutação
3. criar um **Runbook** de backup, restore e teste periódico de PITR
4. mapear as entidades prioritárias para undo seletivo orientado a `company_id`

---

## 15. Tese final

> No APP32, a entrada de MCP e Squads com poder real de mutação exige que recuperação, auditoria e contenção deixem de ser acessórios operacionais e passem a ser parte do núcleo arquitetural do sistema.

Sem isso, a automação aumenta velocidade.  
Mas não aumenta segurança, governança nem capacidade de correção.

Com isso, o sistema ganha:

- memória confiável do que ocorreu
- capacidade real de investigação
- possibilidade de reversão proporcional ao incidente
- proteção estrutural contra erro humano e erro agentic
