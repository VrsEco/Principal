# Guia da Feature: Gestão Financeira — Central de Automação

## Metadados
- `feature_id`: `financeiro_central_automacao`
- `dominio`: `finance`
- `ramo_menu`: `Gestão Financeira`
- `caminho_menu`: `Gestão Financeira > Movimentos > Central de Automação`
- `rota_app`: `/financial/automation`
- `surfaces_permitidas`: `user`, `admin`, `analytics`
- `sensibilidade`: `alta`
- `company_id_obrigatorio`: `sim`

## Objetivo
Importar lotes de documentos financeiros (notas fiscais, boletos, comprovantes, prestação de contas) e usar regras de automação e classificação para gerar títulos e lançamentos automaticamente — sempre com revisão humana antes da confirmação final.

## Quando usar
- explicar como importar um lote de documentos financeiros (upload de arquivos)
- explicar como o sistema extrai dados dos documentos e sugere classificação (conta contábil, centro de resultado, favorecido) com base em regras e histórico
- orientar a revisão dos registros extraídos antes de confirmar — nada vira título/lançamento sem essa revisão
- explicar como criar ou editar uma regra de classificação/automação
- explicar como consultar o histórico de execuções de regras (auditoria)
- explicar o fluxo de prestação de contas (documentos de despesa enviados por colaboradores)

## Quando não usar
- para lançar um movimento manualmente sem documento — usar `financeiro_lancamento_rapido` ou `financeiro_agendamentos`
- para conciliar extrato bancário — usar `financeiro_conciliacao_bancaria`
- fora da surface autorizada

## Entradas esperadas
### Obrigatórias
- `company_id`: escopo do tenant
- lote de documentos (upload de arquivos) ou documentos de prestação de contas

### Opcionais
- regras de classificação/automação a aplicar
- filtros de revisão (status, tipo de documento, data)

## Saídas esperadas
- `lista_de_lotes`: lotes de importação e seu status de processamento
- `registros_extraidos`: dados extraídos de cada documento, com sinalizadores de revisão (ex: possível duplicidade)
- `lista_de_regras`: regras de automação/classificação configuradas
- `historico_de_execucoes`: auditoria de quando e como as regras foram aplicadas
- `titulo_ou_lancamento_gerado`: resultado da confirmação de um registro

## Como orientar o usuário
1. Acessar **Gestão Financeira > Movimentos > Central de Automação** no menu.
2. Fazer upload de um lote de documentos (notas fiscais, boletos, comprovantes) — também é possível baixar um modelo de planilha para importação estruturada.
3. O sistema extrai os dados de cada documento e sugere classificação com base em regras já configuradas e no histórico de classificações anteriores; possíveis duplicidades são sinalizadas, não bloqueadas automaticamente.
4. Revisar cada registro extraído — ajustar classificação, favorecido ou valores quando necessário.
5. Confirmar o registro gera o título ou lançamento correspondente.
6. Criar ou ajustar regras de automação/classificação para acelerar revisões futuras semelhantes.
7. Consultar o histórico de execuções para auditar quando e como cada regra foi aplicada.
8. Documentos de prestação de contas (despesas de colaboradores) seguem um fluxo semelhante, com o mesmo motor de extração e revisão.

## Uso por IA / MCP
Parte desta feature já é consultável via MCP hoje:
- `list_financial_automation_rules` e `list_financial_classification_rules` já permitem à IA **listar** (leitura) as regras configuradas na empresa;
- `list_financial_entries` permite consultar lançamentos já gerados a partir de automação.

O que **ainda não é capability remota**: subir documentos, processar um lote, criar/editar regras ou confirmar um registro extraído — essas ações continuam operacionais apenas no APP, sempre com revisão humana antes de gerar título/lançamento.

Qualquer evolução futura que exponha criação de regras ou confirmação de registros via MCP deve seguir o mesmo padrão de mutação sensível já usado em `create_financial_settlement` (gate humano obrigatório).

## Validações e restrições
- `company_id` obrigatório; regras e registros só se aplicam dentro da mesma empresa
- nenhum registro extraído vira título/lançamento sem revisão e confirmação humana
- duplicidade detectada é sinalizada para revisão, nunca descartada ou confirmada automaticamente
- criar/editar regra e confirmar registro são mutações financeiras sensíveis

## O que nunca expor
- lógica interna de extração de documentos e detecção de duplicidade
- lógica de sugestão de classificação (memória de classificações anteriores)
- nomes de services e métodos internos
- dados financeiros de outra empresa/tenant
