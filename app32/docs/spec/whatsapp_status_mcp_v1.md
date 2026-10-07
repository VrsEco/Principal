# SPEC — Status WhatsApp por MCP v1

## Card único: [Status WhatsApp Versus via MCP]

Empresa AA (company_id 9); Marketing Digital: ID 187, código canônico AA.J.26,
confirmado pelo MCP autenticado em 07/10/2026. AA.J.187 era uma referência
informal incorreta, não a sequência do projeto. Card operacional ainda não
materializado: requer autorização de criação via MCP; checklist local preparado
conforme fallback de aa-j-31-card-execution; não usar SSH de produção.

- [ ] Diagnosticar integração, conta, solicitação existente e acervo.
- [x] Implementar persistência tenant-safe e importação versionada autorizada.
- [x] Implementar publicação ordenada, dedupe, resultado incerto e agenda.
- [x] Registrar ferramentas no MCP existente com teto explícito e OAuth (local).
- [x] Executar testes, incluindo PostgreSQL, concorrência e reinício (laboratório).
- [x] Revalidar correções e grafo local: 191 testes aprovados, 07/10/2026.
- [x] Formar candidato isolado e testar sem mudanças alheias do checkout: reconstruído como v2 sobre a main e1af7c18.
- [ ] Ensaiar reversão de runtime com schema aditivo em homologação.
- [ ] Aprovar release, implantar via control plane e validar atendimento.
- [ ] Coordenar uma publicação real e conferência no celular.

## Contrato de entrega

Reutilizar Flask/PostgreSQL, integrations, catálogo/surfaces OAuth mcp-versus e
scheduler dedicado. Não alterar WhatsAppService de atendimento, webhooks,
credenciais, dispositivos, redes sociais ou domínios. A conexão Online não é
evidência do número nem da capacidade de Status.

Somente IDs do acervo de Status aprovado; nunca URL fornecida pelo cliente.
Importação administrativa recebe bytes locais, valida Pillow, hash e versão,
e copia para instance/whatsapp_status, fora de uploads/static públicos,
segregado por empresa. A publicação usa Base64.
Credenciais existentes são resolvidas no servidor por vínculo explícito de
empresa/integração; nenhum fallback global implícito entre empresas.

Estados: queued → sending (commit antes da rede) → accepted/failed/unknown.
accepted significa aceite do fornecedor, não conferência no celular.
sending sobrevivente de crash é unknown; nunca retentar automaticamente.
Trava PostgreSQL por empresa serializa publicação, edição e retomada. Pausa é
um safety stop imediato: a chamada em voo pode terminar, mas o próximo item
observa a pausa. Dedupe
persistente por hash/empresa/dia Bahia e chave de comando com digest do payload.
Falha/incerteza interrompe kit; itens seguintes não são publicados.

Agenda persistida, desativada ao criar: America/Bahia 08:30, segunda Versus
01–03, terça PHub 01–03, quarta Cases 01, quinta Cases 02, sexta Cases 03–04,
sábado Contato 01–02, domingo vazio. Configuração editável por MCP. Revisão
mensal obrigatória; vencimento impede novas publicações agendadas.
Sem catch-up de dias anteriores; tolerância de cinco minutos documentada.

## Segurança e aceitação

Permissões próprias whatsapp_status.read/publish/schedule/review, em surface
admin e teto restrito do PrincipalCompanyGrant. Todas as ferramentas passam
pelo wrapper existente. Agendamento revalida identidade e poderes do criador;
revogação impede execução. Não conceder conversas/contatos ou administration
genérica no teto. Mutação com publicação/retomada exige confirmação persistida.

Endpoint real: https://app.gestaoversus.com.br/mcp/pilot/; validar
reachability, discovery e OAuth/PKCE reais após release, sem endpoint paralelo.
Nenhum commit/push/deploy sem plano aprovado; GitHub Actions/MCP de Deploy são
os executores oficiais. Ausência de deployment_id autenticado é bloqueio.

Fonte fornecedor: https://developer.z-api.io/status/send-image-status

## Evidências e limites

As 12 PNG aprovadas foram localizadas na pasta fornecida pelo usuário e
verificadas com Pillow/SHA-256. Manifesto em seeds/whatsapp_status_versus_20261007.json;
fontes não públicas em seeds/whatsapp_status_versus_20261007/. A importação MCP
aceita apenas esse bundle fixo, reusa versões imutáveis e cria uma única agenda
desativada, sem resetar agenda existente. kit_size impede kits incompletos.

Conexão mcp-versus já configurada no Codex para o endpoint canônico. Health
real 200, metadata OAuth 200, chamada sem auth 401 com challenge. Em produção,
metadata ainda não anuncia mcp:admin; cliente existente solicita access/user/analytics.
O release local acrescenta o anúncio admin. Reautenticação com scope admin e
grant AA explicitamente limitado a Status ainda dependem de validação humana.
Não alterar grant amplo existente sem avaliar os outros usos desse usuário.

O MCP autenticado confirmou empresa e projeto, mas não oferece ferramentas
Status nem Deploy nesta conversa. Conta/número, solicitação anterior e capacidade
real de Status continuam pendentes. Nenhuma solicitação duplicada foi criada.
Card operacional também permanece pendente.

Testes usam PostgreSQL descartável em 127.0.0.1:55439/whatsapp_status_test;
fornecedor/identidade são doubles. Não equivalem a OAuth real nem conferência
no celular. Evidência final e procedimento: Harness e Runbook desta entrega.
