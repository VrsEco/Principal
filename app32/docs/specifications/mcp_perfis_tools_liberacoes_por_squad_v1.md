# MCP, Perfis, Tools e Liberações por Squad — Empresa-Laboratório Versus v1

## Status
Documento de execução do card `AA.J.16.3`.

## Objetivo
Fechar a arquitetura MCP do experimento, definindo:
- se cliente e consultor usam o mesmo MCP ou MCPs separados
- como os perfis de runtime se relacionam com contracts e permission matrix
- quais surfaces e domínios cada squad deve usar
- quais gaps atuais do catálogo e da policy precisam ser resolvidos

---

## 1. Decisão principal
A arquitetura do experimento deve usar **um único MCP canônico do APP32**, com **surfaces e perfis distintos por squad**.

### Decisão oficial
- **não** criar MCP separado para cliente e consultor
- usar o mesmo catálogo/superfície canônica do APP32
- diferenciar por:
  - `runtime_profile`
  - `surface`
  - `actor_type`
  - `fallback_role`
  - `company_id`
  - permission matrix e contracts publicados

### Motivação
Esse desenho:
- preserva MCP First
- reduz duplicação de catálogo
- evita drift entre MCPs paralelos
- centraliza governança, trilha e auditoria
- permite isolar cliente, consultor e engenharia por policy, não por servidor duplicado

---

## 2. Estado atual confirmado

### 2.1 Surfaces canônicas publicadas
O MCP já está estruturado em quatro surfaces:
- `user`
- `admin`
- `analytics`
- `ops`

Arquivos-base observados:
- `C:\GestaoVersus\app32\app32\src\core\mcp_surface_registry.py`
- `C:\GestaoVersus\app32\app32\src\core\mcp_http_auth.py`
- `C:\GestaoVersus\app32\app32\src\intelligence\mcp_contracts\profiles.py`
- `C:\GestaoVersus\app32\app32\src\intelligence\mcp_contracts\permission_matrix.py`
- `C:\GestaoVersus\app32\app32\src\intelligence\mcp_contracts\playbooks.py`

### 2.2 Runtime profiles já publicados no console/snippets
Profiles atualmente publicados:
- `sapiens_default`
- `squad_versus`
- `squad_cliente`

Arquivo-base observado:
- `C:\GestaoVersus\app32\app32\services\mcp_connection_snippet_service.py`

### 2.3 Contratos genéricos de perfil atualmente disponíveis
Profiles canônicos atuais do contrato MCP:
- `colaborador`
- `cliente`
- `administrador`
- `admin_tecnico`

Leitura importante:
Esses contratos existem, mas **ainda não modelam explicitamente os papéis operacionais de harness do experimento**.

---

## 3. Mapeamento recomendado por squad

## 3.1 Squad Cliente
### Runtime profile
- `squad_cliente`

### Surface principal
- `user`

### Papel arquitetural
- runtime externo do cliente
- operação assistida
- menor privilégio
- interação contextual com o APP32

### Mapeamento recomendado
O `squad_cliente` **não deve** ser tratado como simples profile `cliente` do contrato atual.

Motivo:
- o profile `cliente` na matriz atual está praticamente em **modo leitura** para `routine`, `processes`, `projects` e `meetings`
- isso é insuficiente para o experimento, no qual o Squad Cliente precisa apoiar execução, organização e atualização operacional

### Recomendação
Criar ou formalizar um overlay funcional equivalente a:
- `agente_cliente_operacional`

Com política-alvo:
- surface: `user`
- domínios centrais: `routine`, `projects`, `processes`, `meetings`, `work_journey`
- ações: `discover`, `read`, `create`, `update`
- sem `delete` por padrão
- sem `admin`, `analytics` ou `ops`
- `strategy` apenas em `read/analyze`
- `finance` fora da surface `user` sensível, salvo leitura operacional explicitamente saneada no futuro

### Conclusão
O profile canônico `cliente` atual está **restritivo demais** para o papel real do `Squad Cliente` no laboratório.

---

## 3.2 Squad Versus
### Runtime profile
- `squad_versus`

### Surface principal
- `admin`

### Papel arquitetural
- runtime externo consultivo/governante
- discovery, revisão, estruturação e mutação controlada

### Mapeamento recomendado
O `squad_versus` deve se apoiar no contrato próximo de:
- `administrador`

Mas com overlay funcional consultivo, equivalente a:
- `agente_versus_consultivo`

### Política-alvo
- surface principal: `admin`
- `company_id` explícito para ações sensíveis
- domínios: `strategy`, `projects`, `processes`, `routine`, `governance`, `finance` em análise controlada
- mutações apenas quando o rito exigir
- preferência por discovery, leitura, análise e direcionamento antes de alterar

### Conclusão
O contrato `administrador` é uma boa base, mas o `Squad Versus` precisa de uma camada explícita de governança consultiva por runtime profile.

---

## 3.3 Squad de Engenharia
### Runtime profile
- `engineering` ou equivalente técnico operacional

### Surface principal
- `ops`, `admin`, `analytics`

### Base contratual atual
- `admin_tecnico`

### Conclusão
Aqui o alinhamento é o melhor dos três. O contrato atual de `admin_tecnico` já está mais próximo da necessidade do experimento.

---

## 4. Regra recomendada de profiles
A arquitetura do experimento deve separar duas camadas:

### 4.1 Contracts canônicos MCP
Perfis-base publicados pelo APP32, usados na governança principal.

### 4.2 Runtime profiles de harness
Perfis operacionais do experimento, usados para representar a intenção real do actor.

### Exemplo
- contract base: `administrador`
- runtime profile: `squad_versus`

- contract base: `cliente` ou novo perfil derivado
- runtime profile: `squad_cliente`

### Regra
`runtime_profile` não substitui permission matrix, mas ajuda a especializar:
- comportamento esperado
- startup
- trilha
- telemetria
- protocolos do harness

---

## 5. Liberação recomendada por surface e domínio

## 5.1 Squad Cliente
### Surface
- `user`

### Deve poder usar
- `routine`
- `projects`
- `processes`
- `meetings`
- `work_journey`
- `strategy` em leitura/análise assistida

### Não deve poder usar
- `admin`
- `analytics`
- `ops`
- mutações financeiras sensíveis
- governança privilegiada

### Observação crítica
`work_journey` precisa estar coerentemente enquadrado no catálogo canônico e na policy para o experimento funcionar bem.

---

## 5.2 Squad Versus
### Surface
- `admin`

### Deve poder usar
- `strategy`
- `projects`
- `processes`
- `routine`
- `governance`
- `finance` em leitura/análise controlada
- eventualmente mutações estruturais auditadas

### Não deve poder usar como atalho
- `ops` para tarefas consultivas
- mutações financeiras sem gate
- atuação multiempresa implícita sem `company_id`

---

## 5.3 Engenharia
### Surfaces
- `ops`
- `admin`
- `analytics`

### Deve poder usar
- incidentes
- observabilidade
- diagnóstico
- validação de contracts e policies
- correções e smoke técnico

### Não deve fazer
- operar o negócio como se fosse o cliente ou a consultoria

---

## 6. Startup mínimo por squad

### 6.1 Squad Cliente
- `list_user_app32_capabilities`
- `describe_app32_profile_contracts_tool`
- `describe_app32_surface_playbooks_tool`

### 6.2 Squad Versus
- `list_admin_app32_capabilities`
- `describe_app32_profile_contracts_tool`
- `describe_app32_surface_playbooks_tool`
- `describe_app32_domain_playbooks_tool`

### 6.3 Engenharia
- tools de health, manifest, permission matrix, profiles e diagnósticos técnicos conforme a surface

---

## 7. Gaps identificados no estado atual

## G1. Profile `cliente` atual não atende ao Squad Cliente operacional
Hoje o contrato `cliente` está centrado em leitura e não suporta bem o papel operacional assistido do laboratório.

### Ação recomendada
Formalizar profile/overlay para o Squad Cliente com `create/update` em domínios operacionais da surface `user`.

---

## G2. Runtime profiles já existem, mas ainda não estão amarrados formalmente aos contracts de permissão
Hoje `squad_cliente` e `squad_versus` aparecem em snippets/console, mas a amarração explícita com permission matrix ainda precisa ficar canônica.

### Ação recomendada
Criar documentação/manifesto que relacione:
- runtime profile
- contract base
- surface
- domínios autorizados
- ações autorizadas

---

## G3. Work Journey ainda precisa costura canônica no catálogo e na policy
O experimento depende fortemente de jornada operacional e capacidade, então esse domínio precisa ficar mais claro em:
- manifesto canônico
- política de uso por surface
- papel do Squad Cliente

---

## G4. Financeiro continua sensível para o Squad Cliente
O estado atual está correto ao proteger `finance` da surface `user`, mas isso exige desenho cuidadoso para o papel `admfin_cliente`.

### Leitura recomendada
Na primeira etapa, o `admfin_cliente` deve operar sobretudo como:
- organizador contextual
- leitor operacional do que for seguro
- escalador para Versus/financeiro privilegiado quando houver sensibilidade

---

## G5. Catálogo canônico ainda não expressa toda a superfície real dos registradores MCP
Isso já havia sido identificado no `AA.J.15.1` e continua relevante aqui.

### Impacto
Há risco de o harness descobrir menos do que o MCP realmente expõe, ou de a governança ficar aquém da superfície real.

---

## 8. Decisão operacional para o experimento
Para o `AA.J.16`, a regra operacional deve ser:

### Cliente
- usa `squad_cliente`
- em `user`
- com harness thin
- com escopo operacional assistido
- sem receber metodologia profunda da Versus

### Versus
- usa `squad_versus`
- em `admin`
- com harness consultivo
- com `company_id` explícito quando necessário
- com leitura e análise antes de mutação

### Engenharia
- usa surface técnica adequada
- observa, valida, corrige e endurece

---

## 9. Critérios de aceite do card AA.J.16.3
Este card é considerado atendido quando:
- a decisão de MCP único estiver formalizada
- o mapeamento por squad estiver definido
- os gaps relevantes estiverem nomeados
- a insuficiência do profile `cliente` atual estiver explicitada
- o experimento puder avançar para criação da empresa teste com clareza de política

---

## 10. Próximo passo
Com este fechamento, o próximo passo do projeto é o `AA.J.16.4`:
- criar a empresa teste
- preparar a base mínima no APP32
- preservar a regra de que a operação posterior deve acontecer prioritariamente via CLI/MCP
