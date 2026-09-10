# SPEC — Central Pessoas UI/UX v1

## Decisão

`Sistema → Pessoas` será a única entrada de pessoas no APP32. A tela usa os
componentes e convenções já consolidados: `layouts/app.html`, breadcrumb,
sidebar, cards, tabs, tabelas, botões primário/secundário, estados vazios e
responsividade do design system existente. Não criar um design paralelo.

## Contexto

A empresa ativa é obrigatória para toda aba operacional. A conta do sistema é
global; seus vínculos, colaboradores, cargos, ocupações e custos são
`company_id`-scoped.

## Ordem das abas

1. Visão geral
2. Usuários e acessos
3. Cargos
   - Perfil
   - Quantidade
4. Organograma
5. Colaboradores
   - Perfil
   - Ocupação por data
   - Custos planejados por cargo
6. Relatórios

## UX

- cada aba possui um CTA primário inequívoco;
- Visão geral orienta o fluxo: usuário/acesso → cargo → colaborador → ocupação;
- Usuários e acessos diferencia visualmente conta global e vínculo na empresa;
- custos exibidos em Colaboradores conservam a legenda "por cargo";
- perfis técnicos não ocupam área da tela; RBAC controla ações e visibilidade;
- URLs legadas passam a redirecionar para a aba equivalente após migração.

## Perfis oficiais

- Administrador: plataforma, identidades globais, empresas e configurações técnicas;
- Cliente: gestão operacional da própria empresa;
- Colaborador: próprios dados autorizados.

Tokens MCP, integrações e observabilidade de infraestrutura não pertencem à
Central Pessoas.
