# Guia da Feature: Copiloto de Fluxo BPMN

## Metadados
- `feature_id`: `processos_copiloto_fluxo`
- `dominio`: `processes`
- `surfaces_permitidas`: `user`, `admin`
- `sensibilidade`: `media`
- `company_id_obrigatorio`: `sim`

## Objetivo
Permitir leitura assistida do fluxo BPMN para:
- apontar gaps de lanes, POPs e gateways;
- sugerir automações internas no APP32;
- sugerir conexões MCP/API com serviços externos;
- manter revisão humana obrigatória antes da publicação.

## Quando usar
- revisar modelagem de um processo no BPMN
- preparar contrato de execução de uma atividade
- descobrir oportunidades de automação ou integração
- entender por que um fluxo ainda depende de intervenção humana

## Quando não usar
- editar layout BPMN pixel a pixel
- publicar automação sensível sem revisão humana
- inferir executor final apenas pelo texto da lane

## Entradas esperadas
### Obrigatórias
- `company_id`: escopo do tenant
- `processo_id`: processo a ser analisado

### Opcionais
- `bpmn_element_id`: restringe a sugestão a uma atividade
- `objetivo`: contexto adicional da atividade
- `diagram_status`: `published`, `draft`

## Saídas esperadas
- `analise_do_fluxo`
- `candidatos_de_automacao`
- `candidatos_de_integracao`
- `alertas_de_revisao_humana`

## Como orientar o usuário
- explicar primeiro os gaps de modelagem e governança;
- sugerir automações como rascunho de contrato, nunca como publicação automática;
- diferenciar automação APP32, MCP interno e integração externa;
- deixar explícito quando o gateway ou a semântica do fluxo ainda exigem decisão humana.

## Validações e restrições
- `company_id` obrigatório
- sem cruzamento entre tenants
- intervenção humana obrigatória para fechar modelagem e publicação
- gateways com split/join ambíguos devem ser tratados como revisão manual

## O que nunca expor
- credenciais de integrações
- payloads administrativos sensíveis
- decisões finais automáticas sem trilha de revisão
