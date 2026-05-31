# Runbook — Habilitação do Módulo Leilões Imobiliários para GanduInvest v1

Status: pronto para homologação
Classe documental: Runbook
SPEC: `C:\GestaoVersus\app32\app32\docs\spec\modulo_leiloes_imobiliarios_multi_tenant_v1.md`

## Decisão

GanduInvest deve ser habilitada como **tenant piloto** do módulo genérico `real_estate_auctions`.

O módulo não usa banco separado por padrão. As tabelas integram o PostgreSQL atual do APP32 e todo dado operacional é isolado por `company_id`.

## Pré-requisitos

1. Migration `20260531_0900_create_real_estate_auction_domain.py` aplicada.
2. Usuário operador vinculado à empresa GanduInvest.
3. Perfil com permissão `real_estate_auctions.view`.
4. Para manutenção: permissões `create`, `edit` e, quando necessário, `delete/configure`.

## Habilitar GanduInvest

Executar no diretório `C:\GestaoVersus\app32`:

```powershell
python app32\seeds\enable_real_estate_auction_module.py --name-contains "GanduInvest" --code-prefix "GND"
```

Alternativas seguras:

```powershell
python app32\seeds\enable_real_estate_auction_module.py --client-code "GND" --code-prefix "GND"
python app32\seeds\enable_real_estate_auction_module.py --company-id 13 --code-prefix "GND"
```

## Desabilitar o módulo

```powershell
python app32\seeds\enable_real_estate_auction_module.py --client-code "GND" --disable
```

## Validação funcional mínima

1. Acessar `/real-estate-auctions?company_id=<id>`.
2. Confirmar que o menu “Leilões Imobiliários” aparece apenas quando o módulo está habilitado.
3. Criar um imóvel com código único por empresa.
4. Confirmar que a API lista apenas imóveis do `company_id` ativo:

```text
GET /api/real-estate-auctions/properties?company_id=<id>
```

## Observação para novos clientes

Quando outro cliente quiser usar o módulo, repetir apenas a habilitação por tenant.
Não criar fork, banco paralelo ou tabela específica do cliente sem exceção arquitetural aprovada.
