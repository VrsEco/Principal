# Guia da Feature: Consultivo — Jornada do Cliente

## Metadados
- `feature_id`: `consultivo_jornada_cliente`
- `dominio`: `consultive`
- `ramo_menu`: `Consultivo`
- `caminho_menu`: `Consultivo > Jornada do Cliente`
- `rotas_app`: `/structuring-journey/client`, `/structuring-journey/consultant`, `/structuring-journey`
- `surfaces_permitidas`: `user`, `admin`
- `sensibilidade`: `media`
- `company_id_obrigatorio`: `sim`

## Objetivo
Mostrar a maturidade estrutural da empresa em 4 blocos — Identidade Organizacional, Processos, Planejamento Estratégico, Gerenciamento Estratégico —, cada um com suas etapas e evidências reais, como um mapa de progresso da jornada de estruturação.

## Quando usar
- explicar os 4 blocos da jornada e as etapas de cada um
- explicar como o progresso de cada etapa é calculado (evidência real do sistema, não estimativa)
- explicar a diferença entre a visão "Jornada do Cliente" e "Jornada do Consultor"

## Quando não usar
- para a análise detalhada e as recomendações de uma frente — feature própria: `consultivo_cockpit`
- para o roteiro/prompt de condução metodológica — feature própria: `consultivo_protocolos`
- fora da surface autorizada

## Entradas esperadas
### Obrigatórias
- `company_id`: escopo do tenant

### Opcionais
- `audience`: `client` ou `consultant` (mesma informação, apresentação diferente)

## Saídas esperadas
- `jornada_de_estruturacao`: os 4 blocos, suas etapas, evidências e status de gate por bloco

## Como orientar o usuário
1. Acessar **Consultivo > Jornada do Cliente** no menu.
2. Percorrer os 4 blocos: Identidade Organizacional (missão, visão, valores, posicionamento, organograma), Processos (arquitetura, modelagem, implementação, estabilização, auditoria), Planejamento Estratégico (estruturado, conectado, desdobrado, ligado à gestão) e Gerenciamento Estratégico (indicadores, ciclos, incentivos, teia de conexões).
3. Cada etapa mostra evidência real contada do sistema (ex.: quantos processos têm dono definido, quantos OKRs existem) — não é uma estimativa.
4. A tela é somente leitura; não há nenhuma ação de criação/edição por aqui.
5. Se o usuário for consultor, mencionar que a versão "Jornada do Consultor" (mesma URL, `/structuring-journey/consultant`) tem atalhos extras para abrir a análise detalhada de cada frente no Cockpit.

## Uso por IA / MCP
**Achado importante:** o "gate" entre os blocos é puramente informativo — a página sinaliza visualmente se um bloco está "liberado" com base no anterior estar pronto, mas **não existe nenhum bloqueio técnico real**: a flag interna que impediria escrita fica sempre desligada, e a tela é 100% leitura (não há rota de escrita nesta jornada). "Soft gate" aqui significa "avisa, não impede".

**Achado sobre a diferença client vs consultant:** as duas rotas (`/structuring-journey/client` e `/structuring-journey/consultant`) têm exatamente o mesmo RBAC (usuário autenticado com empresa ativa, sem checagem de perfil) e retornam os mesmos dados — a diferença é só de texto e de atalhos de navegação extras na versão consultor (links diretos para abrir a análise de cada frente no Cockpit). Um cliente pode acessar a URL do consultor diretamente digitando o endereço; não é um vazamento de dado, mas não espere que a URL por si só restrinja quem vê o quê.

Hoje **não existe tool MCP dedicada a esta tela específica** — os mesmos dados (evidência real por bloco/etapa) são obtidos via `StructuringJourneyService`, que também alimenta as análises de frente do Cockpit (`consultive_get_front_context`/`consultive_get_front_evidence`, ver guia `consultivo_cockpit`). Não há tool MCP separada só para "a jornada" como tal.

## Validações e restrições
- `company_id` obrigatório; jornada de outra empresa nunca é retornada
- leitura liberada a qualquer usuário autenticado com empresa ativa, em ambas as rotas (client/consultant)
- não há mutação nesta tela

## O que nunca expor
- estrutura de tabelas internas ou nomes de services (`StructuringJourneyService`)
- o "gate" como se fosse um bloqueio técnico real — é só sinalização visual
- dados de outra empresa/tenant
