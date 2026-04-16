# Fronteiras dos Componentes

## Agente
Arquivo curto de papel. Contém missão, foco, limites e critérios de decisão do domínio.

## Skill
Workflow reutilizável. Deve dizer quando usar, sequência curta e quais referências/scripts consultar.

## Router
Decide para onde o pedido vai. Não executa procedimentos detalhados.

## Reference
Documento consultivo, checklist, troubleshooting, blueprint, política e variantes.

## Script
Automação repetitiva, scaffolding, probe, smoke ou coleta de evidência.

## Anti-padrões
- persona completa dentro de skill
- checklist longo dentro de agente
- documentação grande dentro do orquestrador
- duplicar regra global em todos os arquivos
