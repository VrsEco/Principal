# Organograma, cargos, ocupação e processos

Classe: SPEC
Data: 2026-09-04
Status: fluxo funcional aprovado; contrato técnico para implementação, ainda não implantado.
Entrega: AA.J.21.238 — Organograma integrado a processos.

## 1. Fluxo aprovado

1. Cadastrar cargos na estrutura, sem exigir ocupante ou login.
2. Selecionar colaborador da empresa ou cadastrar colaborador sem acesso.
3. Associar usuário existente ao colaborador somente quando houver necessidade de acesso e autorização. Nunca criar outro login automaticamente.
4. Relacionar cargos aos processos e, opcionalmente, às atividades BPMN.

Cargo não é usuário. Colaborador não precisa ter login. A troca de ocupante não altera a responsabilidade estrutural do cargo no processo.

## 2. Base existente e limites

- `Role`: cargo com superior, departamento, quantidade prevista e jornada; também contém permissões legadas. Preservar IDs e hierarquia.
- `Employee`: vínculo da pessoa com a empresa; `user_id` opcional e um `role_id` legado.
- `CompanyIdentityService`: resumo e árvore atualmente baseados em `Employee.role_id`.
- `RoutineRoleAssignment`: atribuição de cargos a rotinas já existente. Não criar atribuição concorrente para o mesmo propósito.
- `ProcessExecutionAssignment`: destinatário de execução; não substituir pelo planejamento organizacional.
- `ProcessResourceLink`: consumo e custo de recursos por processo/elemento BPMN. Reutilizar esta camada, conforme a SPEC de recursos habilitadores.

## 3. Contrato de dados

### Cargo

Reutilizar `Role`: título, superior, departamento, quantidade prevista inteira não negativa, jornada semanal positiva quando informada e responsabilidades descritivas. Cargo pode existir vago. Não criar uma tabela paralela de posições no MVP: cada cargo representa um grupo de posições equivalentes com a mesma chefia.

### Ocupação

Introduzir vínculo `EmployeeRoleOccupancy` com `company_id`, `employee_id`, `role_id`, início, fim opcional, horas semanais dedicadas e auditoria. Todas as relações devem pertencer à mesma empresa. Vigência usa intervalo [início, fim); fim deve ser posterior ao início.

- Uma pessoa pode ocupar vários cargos; um cargo pode ter vários ocupantes.
- Impedir períodos sobrepostos para o mesmo par colaborador/cargo.
- A soma das horas simultâneas de ocupação não deve exceder a jornada do colaborador. Jornada desconhecida gera pendência; não atribuir capacidade zero nem presumir 100%.
- Validar limites sob bloqueio transacional do colaborador, evitando gravações concorrentes que ultrapassem a jornada.
- Desvincular significa encerrar vigência, não excluir histórico.
- Colaborador inativo não recebe nova ocupação; ausência/férias afeta disponibilidade, não extingue o vínculo organizacional.

### Qualificação

Catálogo por empresa e requisitos por cargo: qualificação, nível requerido e obrigatoriedade. Evidência do colaborador registra nível comprovado, validade opcional e origem. Ausência de evidência é “não avaliado”, não “não qualificado”. Requisitos específicos de processo permanecem no vínculo processo–recurso.

### Custo

Perfil versionado por cargo: início/fim, moeda e custo mensal estimado por FTE completo, composto por salário-base, encargos, benefícios e outros custos estimados. Valores Decimal, finitos e não negativos; nenhum percentual legal presumido.

- Custo planejado do cargo = posições previstas × custo mensal por FTE.
- FTE ocupado = soma das horas dedicadas ÷ jornada padrão do cargo.
- Custo da ocupação estimado = FTE ocupado × custo mensal por FTE.
- Custos desconhecidos ficam nulos; total parcial deve informar cobertura e não se apresentar como total completo.
- Não denominar estimativa como custo realizado de folha.
- Não somar moedas diferentes. No MVP, consolidação exige uma moeda comum.
- Quantidade nominal de pessoas distintas e FTE são métricas separadas. Pessoa com dois cargos conta uma vez no total de pessoas da empresa.

## 4. Conexão com processos

Relacionar explicitamente cargo ao recurso habilitador de pessoas, sem correspondência automática por nome. No MVP, cada cargo tem no máximo um recurso canônico de planejamento de pessoas e cada recurso deste tipo representa no máximo um cargo. Recursos genéricos não vinculados continuam válidos.

O consumo por processo continua em `ProcessResourceLink`; não cadastrar novamente a mesma capacidade e custo em outro motor. A origem da capacidade/custo deve ser explícita: manual ou derivada do cargo. Ao adotar origem derivada, impedir edição manual concorrente desses mesmos valores.

A responsabilidade RACI deve ter vínculo próprio por cargo e processo, opcionalmente elemento BPMN e versão do diagrama. RACI não é percentual de dedicação nem concede acesso. Um escopo publicado tem exatamente um A; múltiplos R são permitidos. Rascunhos incompletos são sinalizados. Elemento removido/nova versão exige reconciliação explícita antes de publicar, nunca remapeamento por título.

Alocação de custo nos processos é distribuição do custo organizacional, não custo adicional a somar ao total do organograma. Demanda superior à capacidade é sobrecarga visível; não truncar percentuais em 100%.

## 5. Acesso e isolamento

- `company_id` obrigatório em entidades, queries e services; validar todas as referências e reforçar relações por chaves compostas/constraints PostgreSQL quando aplicável.
- Separar autorização para manter estrutura, vincular colaborador, associar login e consultar custos. Esconder campos na UI não basta: serializers e endpoints precisam omiti-los sem permissão.
- Acúmulo de cargos não une automaticamente `Role.permissions`. Preservar a origem atual de permissões via cargo principal legado até migração RBAC deliberada e testada.
- Associação de login não altera senha, perfil global nem privilégios. Não expor diretório global de usuários a quem só administra a estrutura da empresa.
- Rotas finas, schema estrito e services reutilizáveis. Integrações MCP futuras devem respeitar capabilities existentes e gates; não expor custos em surface operacional de menor privilégio.

## 6. Experiência de uso

Organograma oferece “Novo cargo” e, no cargo, “Vincular colaborador” e “Cadastrar colaborador”. Formulário de colaborador permite ausência de login. Associação de usuário é ação separada, com autorização específica.

Detalhe do cargo: estrutura, ocupantes/vigências, qualificações, custos autorizados e processos relacionados. Cartão mostra previstos, ocupantes distintos, FTE e vagas nominais; custo só para autorizados. Exibir excesso de ocupantes separado das vagas e déficit de FTE separado do déficit nominal.

## 7. Migração e aceite

1. Criar estruturas aditivas e migração idempotente das ocupações legadas; não inventar data histórica ou dedicação. Registrar origem legada e pendências.
2. Manter `Employee.role_id` como cargo principal de compatibilidade; mudanças de ocupação secundária não o alteram. Adaptar leitores de organograma e resolução de ocupantes de rotinas antes de habilitar acúmulo na UI.
3. Implementar cadastro/vínculo e qualificação, depois custos e conexão com processos, mantendo consumidores legados funcionais.
4. Validar em PostgreSQL: cargo vazio; colaborador sem login; usuário existente; acúmulo sem dupla contagem; períodos e concorrência; troca de ocupante; segregação de tenant; RBAC sem escalada; custo desconhecido/zero; versões BPMN; migração repetida e regressão de rotinas.

Não executar migração em produção nem publicar alterações de organogramas de clientes como consequência automática desta SPEC.

## 8. Referências e estado da entrega

- `arquitetura_oficial_estrutura_recursos_processos_v1.md`: catálogo corporativo e motor de consumo preservados.
- Modelos: `role.py`, `employee.py`, `routine.py`, `process_resource.py` e `process_assignment.py`.
- Mapeamento e contrato documentados. Implementação do MVP, testes funcionais e deploy pendentes.
- Primeiro incremento local: cadastro de cargos valida headcount inteiro não negativo, jornada opcional positiva de até 168 horas com duas casas decimais e identificador de superior inteiro positivo. Não arredondar entradas inválidas silenciosamente.
- Evidência: 37 testes unitários aprovados em `tests/test_company_role_hierarchy_service.py`, com `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` devido a incompatibilidade do plugin pytest-flask instalado com Flask. Estes testes não usam banco e não substituem a validação PostgreSQL/HTTP do MVP.
- Incremento local seguinte: editor expõe jornada e responsabilidades; formulário cadastra colaborador sem login no cargo salvo selecionado. Endpoint `POST /api/companies/<company_id>/roles/<role_id>/employees` aceita apenas `name`, valida acesso ao tenant e cargo, e reutiliza o orquestrador de identidade sem criar acesso. Nome normalizado repetido exige revisão humana; homônimos não são fundidos automaticamente neste fluxo.
- A criação usa `Employee.role_id` legado exclusivamente para novo colaborador sem login. Não implementa ainda ocupações múltiplas nem altera cargos de colaboradores existentes. Bloqueio de empresa serializa apenas requisições deste novo fluxo; não é garantia contra outros cadastros concorrentes legados.
- Evidência atual: 55 testes unitários/de contrato aprovados entre `test_company_role_hierarchy_service.py` e `test_company_org_employee_service.py`; sintaxe JavaScript/Python validada. Testes de banco PostgreSQL, HTTP autenticado e inspeção visual ainda pendentes. Nenhum deploy realizado.
- Incremento subsequente: `PUT /api/companies/<company_id>/roles/<role_id>/employees` recebe somente `employee_id` inteiro e permite primeira lotação de colaborador ativo sem login e sem cargo. Repetição para o mesmo cargo é idempotente; outro cargo, login existente ou colaborador de outra empresa são rejeitados. Formulário oferece candidatos elegíveis do resumo da própria empresa e confirmação antes de gravar. Não altera departamento nem dados de acesso. Ocupação múltipla permanece pendente.
- Validação acumulada: 67 testes unitários/de contrato aprovados, com persistência simulada nos testes do vínculo; sintaxe Python, JavaScript e Jinja aprovada. Não equivale a homologação PostgreSQL ou visual.
- Contrato HTTP validado com o blueprint Flask real: POST/PUT, gates de permissão e tenant, rollback em erros 400/404/500 e ocultação de detalhes internos. Autorização e persistência são simuladas; não constitui teste de login real nem integração PostgreSQL. Acumulado: 82 testes aprovados incluindo `test_company_org_employee_routes.py`.
- Incremento intermediário de qualificações: `Role.qualification_requirements` armazena requisitos descritivos opcionais (até 10000 caracteres). Editor permite cadastrar/limpar; service valida e resumo/API serializam. Não representa catálogo estruturado, evidência do colaborador ou cálculo de aderência — estes permanecem pendentes no modelo alvo.
- Migração aditiva `20260904_1400` preparada, não aplicada. É obrigatório aplicar antes de carregar o código que consulta `Role`; sem a coluna, queries ORM de cargos falharão. Sem backfill de qualificações presumidas. Downgrade remove os dados e exige exportação prévia.
- Acumulado: 92 testes aprovados com persistência simulada; JavaScript validado. Migração PostgreSQL e inspeção visual ainda não homologadas, sem deploy.
- Motor puro `services/org_capacity_cost_service.py`: calcula snapshot de uma empresa/data previamente autorizado, com pessoas distintas, FTE por cargo, vagas/excesso nominal, projeção monetária Decimal, subtotal conhecido e total nulo quando incompleto. Rejeita dupla ocupação do mesmo par, referências externas ao snapshot, mistura de moedas e dedicação conhecida superior à jornada. Horas desconhecidas geram pendência, sem estimar automaticamente.
- Motor ainda não integrado a banco/API/UI: chamador futuro deve filtrar vigências na data consultada e autorizar custos. Não habilita acúmulo de cargos no cadastro legado. Acumulado: 107 testes aprovados, incluindo cenários de cálculo; perfil de custos versionado e integração continuam pendentes.
- Base temporal implementada localmente: `EmployeeRoleOccupancy` e migração `20260904_1500`, com FKs compostas (empresa/colaborador e empresa/cargo), datas [início,fim), horas opcionais, índices e unicidade por início. A migração NÃO foi aplicada e NÃO faz backfill automático do legado.
- Service interna `create_occupancy` bloqueia o colaborador durante a validação, rejeita sobreposição do mesmo cargo e excesso de horas simultâneas; períodos adjacentes são aceitos. Não altera `Employee.role_id` ou permissões. Apenas flush: futuro adaptador deve garantir commit/rollback. Sobreposição não é constraint de exclusão no banco; todos os escritores precisam respeitar a service e o lock.
- Não há endpoint/UI de acúmulo habilitados. Antes de expor: reconciliar cargo legado e ocupações, adaptar leitores de organograma/rotinas e implementar encerramento de vigência/auditoria de ator. Alterações de jornada precisam validar impacto nas ocupações. Horas desconhecidas permanecem pendência, não aprovação de capacidade suficiente.
- Acumulado: 115 testes aprovados; inclui validação temporal e compilação DDL PostgreSQL, mas não execução da migração nem teste concorrente em banco real.
- Encerramento interno implementado com data final exclusiva, autor e timestamp, sem delete. Retentativa idêntica mantém a autoria; alteração de encerramento já registrado exige futuro fluxo de correção auditada. Criador é obrigatório e recebido como argumento confiável, não no payload. A migração ainda não aplicada `20260904_1500` inclui esses campos.
- Transição protegida: cargo secundário exige ocupação do cargo principal legado com dedicação conhecida cobrindo o período solicitado. Não é backfill automático. API/UI e leitores ainda precisam ser integrados antes de habilitar acúmulo ou encerramento aos usuários. Autorizações e commit/rollback cabem ao adaptador futuro.
- Acumulado: 128 testes aprovados; encerramento, idempotência, datas estritas, ator e transição legada cobertos em testes unitários. Sem execução de migração ou publicação.
- Consulta `GET /api/companies/<company_id>/occupancy-snapshot?as_of=AAAA-MM-DD` adicionada com permissão de leitura de empresas e gate de tenant, sem custos/login/permissões no payload. Resolve vigências [início,fim), pessoas distintas e origem temporal/legada. Exige as migrações preparadas antes de uso.
- Legado só aparece como vínculo atual não verificado na data local do servidor, sem inferir dedicação. Consulta histórica/futura mantém a pendência e não presume vigência. Um colaborador com histórico temporal não recebe fallback legado, inclusive após encerramento. O indicador de reconciliação não comprova completude do histórico real; status atual não reconstrói disponibilidade passada.
- 136 testes aprovados no conjunto; leitura ainda não integrada à árvore visual nem ao resolvedor de rotinas. Teste HTTP específico desta nova consulta e homologação PostgreSQL permanecem pendentes.
- Aba de consulta **Ocupações por data** implementada, com data obrigatória, pessoas distintas, cargo, horas, origem e pendências. Erros não são apresentados como lista vazia; nomes são escapados no HTML. Aba não substitui o organograma principal legado e não oferece mutações temporais.
- Acumulado: 142 testes aprovados, incluindo contrato HTTP da consulta com gates simulados, 400/403/404/500; sintaxe JavaScript e Jinja validada. QA visual e homologação PostgreSQL ainda pendentes. Migrações permanecem não aplicadas.
- `RoleCostProfile` e migração `20260904_1600` preparados: componentes monetários opcionais separados do cargo, moeda, vigência e criador; FK composta empresa/cargo. Service interna valida decimais, datas e moeda e rejeita sobreposição após lock do cargo. Commit/rollback e autorização pertencem ao adaptador futuro. Não há edição destrutiva de histórico ou endpoint de custos publicado.
- Custo integral só é conhecido com todos os quatro componentes informados, inclusive zeros explícitos. Ausências permanecem nulas e o subtotal é identificado. O serializer geral de Role não expõe os componentes econômicos.
- 159 testes aprovados no conjunto. Perfis de custos ainda sem UI/API, resolução por data, encerramento de vigência e ligação com o cálculo. Migração não aplicada; testes PostgreSQL/concorrência e revisão de permissões continuam necessários.
- Consulta econômica adicionada: `GET /api/companies/<company_id>/planned-role-costs?as_of=AAAA-MM-DD`, exigindo simultaneamente `companies:view`, `financial:view` e acesso ao tenant. Não há mutação nem divulgação dos componentes individuais nesta rota. Os códigos são permissões HTTP existentes, não novo domínio MCP.
- Perfis vigentes alimentam cálculo por cargo e subtotal conhecido. A base é explicitamente **quantidade planejada atual × custo por FTE vigente na data**, não quadro histórico nem folha realizada. Perfil ausente/incompleto produz total nulo; sobreposição é rejeitada.
- 165 testes aprovados, incluindo negação de cada permissão da consulta econômica (gates simulados). Ainda sem UI econômica, homologação PostgreSQL ou migrações aplicadas.
- Aba **Custos planejados** implementada para usuários com leitura financeira; backend continua exigindo as duas permissões e acesso ao tenant. Consulta sob demanda, com nome do cargo, custo planejado, cobertura e subtotal conhecido/total incompleto. Não carrega componentes individuais, não cadastra perfis e não altera valores. JavaScript usa textContent para valores do servidor e preserva strings decimais.
- Regressão focal após UI: 44 testes de perfis/rotas aprovados; sintaxe dos dois scripts e Jinja validada. Inspeção visual e homologação PostgreSQL continuam pendentes. Sem deploy.
- Cadastro econômico conectado: `POST /api/companies/<company_id>/roles/<role_id>/cost-profiles` exige `companies:edit`, `financial:edit` e acesso ao tenant. Autor vem da sessão, nunca do payload; rota controla commit/rollback. O formulário é exibido na aba de custos somente para editores autorizados, permite selecionar cargo e informar vigência/moeda/componentes. Valores vazios permanecem nulos; confirmação precede a gravação.
- Cadastro é aditivo, sem substituir perfis. Perfil aberto bloqueia outro período sobreposto; encerramento/revisão auditada de perfil ainda pendente. Falha de rede após commit pode exigir consulta para confirmar gravação; sobreposição impede duplicata idêntica.
- Acumulado: 171 testes aprovados; contrato HTTP de gravação cobre permissões, ator, commit/rollback e erros com dependências simuladas. JavaScript e Jinja validados, ainda sem teste visual ou integração PostgreSQL. Nenhuma migração aplicada ou publicação executada.
- RACI foi deliberadamente adiada por decisão humana. Não há modelo, migração, endpoint ou UI RACI nesta entrega; o mock-up permanece apenas como referência não canônica.
- Base de evidências de qualificação implementada: `EmployeeQualificationEvidence` separa qualificação, nível, origem (`declared`, `documented` ou `verified`), referência e validade. Possui FK composta de empresa/colaborador e criador auditável. A ausência da evidência continua sendo **não avaliado**, não reprovação; não há correspondência automática entre texto do requisito do cargo e a evidência.
- Migração `20260904_1800` preparada com linhagem sem RACI, ainda não aplicada. Service interna normaliza o contrato e rejeita duplicata; endpoint/UI de cadastro e análise de aderência ainda pendentes.
- Acumulado atual: 178 testes aprovados; sintaxe da migração validada e diff sem erros. Não houve aplicação de migração, homologação PostgreSQL, QA visual ou deploy.
- API de cadastro adicionada: `POST /api/companies/<company_id>/employees/<employee_id>/qualification-evidences`, com `companies:edit`, acesso ao tenant, ator vindo da sessão e commit/rollback na rota. Não expõe avaliação automática, não altera cargo, ocupação ou acesso.
- Regressão focal: 94 testes aprovados para rotas, qualificação e cargos. Interface de cadastro/listagem, expiração visual e análise humana de aderência permanecem pendentes.
- Formulário de evidências incluído na aba de estrutura para editores autorizados: seleciona colaborador, qualificação, nível, origem, referência e validade, com confirmação explícita. Não exibe aderência automática nem altera requisitos do cargo. Lista/edição/expiração visual das evidências ainda pendentes.
- Regressão focal UI: 61 testes de qualificação/cargos aprovados; JavaScript e Jinja validados. Migração não aplicada e QA visual ainda pendente.
- Consulta de evidências por colaborador implementada com `companies:view`, isolamento por `company_id` e indicador de validade (sem validade, expirada, vence em breve ou válida). O indicador não representa aderência ao cargo e não altera acesso, ocupação ou requisito.
