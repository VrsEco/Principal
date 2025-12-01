# Teste de Conformidade — Ações Automatizadas

O serviço `AppComplianceService` passou a suportar ações extras (POST/PUT/DELETE) para que o agente consiga reproduzir erros de negócio como:

- “Erro ao salvar indicador”
- “Erro ao vincular: uma ou mais empresas já estão vinculadas”

## Onde configurar
Use o arquivo `config/compliance_actions.json` (o agente já carrega esse arquivo a cada execução). O formato esperado é:

```json
{
  "035": [
    {
      "description": "Salvar indicador de teste",
      "method": "POST",
      "path": "/grv/api/company/{company_id}/indicators",
      "json": {
        "name": "Indicador QA",
        "code": "QA-{company_id}",
        "goal": 100
      },
      "required_context": ["company_id"],
      "expected_status": [200, 201]
    }
  ]
}
```

### Campos disponíveis
| Campo            | Obrigatório | Descrição                                                                                 |
| ---------------- | ----------- | ----------------------------------------------------------------------------------------- |
| `description`    | Não         | Texto usado no relatório/preview (ex.: “Salvar indicador de teste”).                      |
| `method`         | Não         | Verbo HTTP (`GET`, `POST`, `PUT`, `DELETE`). Default: `GET`.                              |
| `path`           | Sim         | Caminho da rota (pode conter placeholders `{company_id}`, `{plan_id}`, etc.).             |
| `json`           | Não         | Payload JSON (strings também aceitam placeholders).                                       |
| `data`           | Não         | Payload `application/x-www-form-urlencoded`.                                              |
| `required_context` | Não       | Lista de variáveis obrigatórias para executar a ação (ex.: `["company_id","plan_id"]`).   |
| `expected_status` | Não        | Número, lista ou intervalo aceito (ex.: `200`, `[200,201]`, `"2xx"`, `{"min":200,"max":204}`). |

> A cada varredura, o agente preenche os placeholders usando o “Contexto de teste” configurado na própria UI (company_id, plan_id, etc.).  
> Caso algum parâmetro esteja faltando, ele marca o check como ⚠️ e segue para as próximas ações.

## Como o resultado aparece
Cada ação gera um novo check `acao:<descrição>` no relatório. Exemplos:

- `✅ acao:Salvar indicador de teste: POST /grv/api/company/13/indicators -> 201`
- `❌ acao:Vincular empresa piloto: POST /pev/api/alignment/overview -> 400 | Resposta: Erro ao vincular: uma ou mais empresas já estão vinculadas`

Assim, basta adicionar/ajustar as ações relevantes para que o agente capture os mesmos erros que você encontra manualmente. Lembre-se de fornecer dados seguros de teste (planos/projetos temporários) para não impactar clientes reais.***
