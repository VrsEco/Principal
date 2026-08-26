# Repertório de Casos

## Política

O arquivo `cases.json` é o registro operacional. Cada caso possui status:

- `candidate`: recebido, ainda não aprovado como referência;
- `reference`: aprovado para orientar o raciocínio;
- `retired`: preservado como histórico, mas não usado para novas propostas.

Um caso novo pode substituir outro quando demonstrar melhor clareza de identidade, fatoração, encadeamento, rastreabilidade e validação. A substituição nunca apaga o caso antigo.

Comandos:

```powershell
python scripts/gerir_casos.py validate
python scripts/gerir_casos.py list
python scripts/gerir_casos.py add --input novo_caso.json
python scripts/gerir_casos.py promote --case-id caso-v2 --replace caso-v1
python scripts/gerir_casos.py retire --case-id caso-v1 --replaced-by caso-v2
```

## Casos iniciais

### BRN — referência principal

- Origem: Paper BRN v0.19 e artefatos canônicos de arquitetura, catálogo e gestão de processos.
- Aprendizado: derivação da identidade e do modelo operacional; fatoração coerente de grandes entregas, entregas e microentregas; separação entre processos permanentes, capacidades habilitadoras e projetos; encadeamento ponta a ponta.
- Não transferir: códigos `AZ.C.*`, mineração, FEL/FID, comissionamento, ramp-up ou taxonomia industrial.
- Correções conhecidas: catálogo ainda preliminar; subprocesso L4 não promovido ao núcleo; pequenos ajustes de fronteira e nomenclatura pendentes.

### M1 Autopeças — referência de simplicidade

- Origem: portfólio demonstrativo tenant-safe `seed_m1_autoparts_process_portfolio.py`.
- Aprendizado: identidade curta convertida em Gestão, Finalísticos e Apoio; cadeia comercial–produção–entrega; processos nomeados por entrega; SIPOC ponta a ponta.
- Não transferir: estrutura fabril, taxonomia fiscal ou canais digitais como padrões universais.
- Limite: caso demonstrativo, menos profundo que BRN.

### Versus — candidato a ingestão MCP

- Origem esperada: catálogo canônico vigente da Versus no APP32.
- Status: não usar até exportação MCP tenant-safe, comparação antes/depois e validação do consultor.

### Empresa Testes — candidato a ingestão MCP

- Origem esperada: catálogo vigente/refatorado no APP32.
- Status: não usar até exportação MCP tenant-safe, rastreabilidade da refatoração e validação do consultor.
