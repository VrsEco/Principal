# Arquitetura de Identidade, Autenticação, Papéis e Surfaces — Squads Versus Gestão Corporativa

## Status
Versão inicial v1 produzida no contexto do card `AA.J.15.2`.

## Objetivo
Definir a arquitetura de identidade e autorização necessária para operação segura de:
- humano da Versus
- agente do Squad Versus
- humano do cliente
- agente do Squad Cliente
- perfis de Engenharia

com vínculo explícito a `company_id`, papel, surface MCP e rastreabilidade.

---

## 1. Achados do estado atual
A base atual já contém elementos importantes:

### 1.1 MCP HTTP Auth
Arquivo central:
- `C:/GestaoVersus/app32/app32/src/core/mcp_http_auth.py`

Capacidades presentes:
- validação de bearer token
- resolução de identidade por token estático ou token persistido
- `allowed_surfaces`
- `fallback_role`
- `company_id` por identidade
- `user_id` por identidade
- contexto por request
- override controlado de contexto

### 1.2 Surface registry
Arquivo central:
- `C:/GestaoVersus/app32/app32/src/core/mcp_surface_registry.py`

Surfaces suportadas:
- `user`
- `admin`
- `analytics`
- `ops`

### 1.3 Matriz de permissão canônica
Arquivo relevante:
- `C:/GestaoVersus/app32/app32/src/core/mcp_permission_matrix_tools.py`

Perfis citados pela matriz/documentação:
- `colaborador`
- `cliente`
- `administrador`
- `admin_tecnico`

---

## 2. Princípio arquitetural
A identidade MCP não deve representar apenas um token técnico.

Ela deve representar um ator operacional explícito, com:
- tipo de ator
- vínculo organizacional
- `company_id`
- papel funcional
- surfaces permitidas
- trilha de auditoria por request

---

## 3. Tipos de ator oficiais

### 3.1 Humano da Versus
Pessoa da consultoria atuando sobre contas/clientes.

Campos mínimos esperados:
- `user_id`
- `company_id` alvo da operação
- `fallback_role`
- `actor_type = versus_human`
- `allowed_surfaces`

### 3.2 Agente do Squad Versus
Runtime externo operando em nome metodológico/consultivo da Versus.

Campos mínimos esperados:
- `agent_id` ou identificador equivalente em metadata
- `company_id` alvo da conta/cliente
- `fallback_role` coerente com o tipo de ação
- `actor_type = versus_agent`
- `allowed_surfaces`
- `client_name` / runtime

### 3.3 Humano do cliente
Usuário da empresa cliente operando no contexto da própria empresa.

Campos mínimos esperados:
- `user_id`
- `company_id` da própria empresa
- `fallback_role`
- `actor_type = client_human`
- `allowed_surfaces`

### 3.4 Agente do Squad Cliente
Runtime externo operando em nome da empresa cliente e limitado ao seu contexto.

Campos mínimos esperados:
- `agent_id` ou equivalente em metadata
- `company_id` da própria empresa
- `fallback_role`
- `actor_type = client_agent`
- `allowed_surfaces`
- `client_name` / runtime

### 3.5 Engenharia / Admin técnico
Perfis técnicos responsáveis por sustentação, diagnóstico e evolução.

Campos mínimos esperados:
- `user_id` ou identidade técnica persistida
- `fallback_role = admin_tecnico`
- `actor_type = engineering`
- `allowed_surfaces` com controle forte

---

## 4. Regras de vínculo com company_id

### 4.1 Regra principal
Toda atuação operacional deve carregar `company_id` válido e tenant-safe.

### 4.2 Humano/Agente do Cliente
- só deve operar a própria empresa
- não deve alternar `company_id` livremente
- qualquer override deve ser bloqueado por padrão

### 4.3 Humano/Agente da Versus
- pode atuar em múltiplas empresas elegíveis
- a seleção do `company_id` deve ser explícita e rastreável
- não deve existir atuação implícita ambígua quando houver múltiplas empresas possíveis

### 4.4 Engenharia
- atuação multiempresa só quando estritamente necessária
- preferencialmente via surfaces privilegiadas
- com trilha e objetivo técnico explícitos

---

## 5. Modelo recomendado de surfaces por ator

### 5.1 client_human
Surfaces padrão:
- `user`

Opcional controlado:
- `analytics` restrito

Não recomendado por padrão:
- `admin`
- `ops`

### 5.2 client_agent
Surfaces padrão:
- `user`

Opcional controlado:
- `analytics` em leitura assistida

Não recomendado por padrão:
- `admin`
- `ops`

### 5.3 versus_human
Surfaces padrão:
- `user`
- `analytics`

Opcional controlado:
- `admin`

Uso excepcional:
- `ops`

### 5.4 versus_agent
Surfaces padrão:
- `analytics`
- `user` quando o fluxo exigir coprodução operacional

Opcional controlado:
- `admin` com gate humano quando houver mutação sensível

Uso excepcional:
- `ops`

### 5.5 engineering
Surfaces padrão:
- `admin`
- `ops`
- `analytics`

Uso controlado:
- `user` apenas para testes/smokes específicos

---

## 6. Papéis funcionais mínimos recomendados
Os papéis funcionais não devem ficar reduzidos apenas a perfis genéricos.

Sugestão de normalização inicial:
- `colaborador`
- `gestor_cliente`
- `consultor_versus`
- `auditor_versus`
- `admin_empresa`
- `admin_tecnico`
- `agente_cliente_operacional`
- `agente_versus_consultivo`

Esses papéis devem ser mapeados para a permission matrix e não apenas tratados como texto livre em `fallback_role`.

---

## 7. Metadata mínima por request MCP
Toda request agentic relevante deveria carregar, de forma resolvida no contexto:
- `user_id` ou identificador equivalente
- `company_id`
- `fallback_role`
- `surface`
- `thread_id` quando aplicável
- `client_name`
- `actor_type`
- identificador do token/credencial quando houver

### Observação
Hoje parte disso já existe, mas `actor_type` e distinção formal entre humano/agente ainda precisam ser institucionalizados.

---

## 8. Gaps identificados
1. `actor_type` ainda não está institucionalizado no contexto MCP
2. `fallback_role` ainda funciona mais como texto de apoio do que como taxonomia forte
3. falta mapeamento explícito entre tipo de ator e surfaces padrão
4. falta política formal de override de contexto por tipo de ator
5. falta distinção mais visível entre credencial humana e credencial agentic

---

## 9. Decisão arquitetural recomendada

### 9.1 Identidade forte por ator
Todo runtime deve ser enquadrado como um destes tipos:
- `versus_human`
- `versus_agent`
- `client_human`
- `client_agent`
- `engineering`

### 9.2 Surface padrão por tipo
Cada ator deve nascer com surfaces padrão restritas e expansões controladas.

### 9.3 Company_id obrigatório
Nenhuma atuação operacional relevante deve depender de resolução implícita fraca de empresa.

### 9.4 Auditoria por request
Toda request MCP deve deixar trilha suficiente para reconstruir:
- quem atuou
- em nome de quem
- em qual empresa
- por qual runtime
- em qual surface
- usando qual capability

---

## 10. Impacto no backlog seguinte
Este passo habilita diretamente:
- `AA.J.15.3` — front door / Sapiens / canal inicial
- `AA.J.15.4` — objetos colaborativos mínimos
- `AA.J.15.5` — capabilities MVP do domínio operacional

Sem esta definição, a abertura segura dos squads externos fica frágil.

---

## 11. Veredito final do Passo 2
A base técnica atual já suporta parte importante da arquitetura de identidade e surfaces.

Porém, para uso real dos squads externos, a Versus precisa institucionalizar explicitamente:
- tipos de ator
- papéis funcionais mais fortes
- surfaces padrão por ator
- política de company_id por ator
- trilha unificada por request

Esse é o fechamento mínimo para seguir com segurança para o próximo passo da execução.
