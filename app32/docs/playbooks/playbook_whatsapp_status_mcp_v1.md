# Playbook — Comandos de Status WhatsApp

Pré-requisitos e limites: [Runbook](../runbooks/runbook_whatsapp_status_mcp_v1.md).
Todas as operações recebem company_id AA resolvido pelo principal autenticado;
o agente nunca substitui tenant ou usuário por identidade declarada no texto.

| Comando humano | Operação determinística |
|---|---|
| Confira a conexão e o cadastro anterior | get_whatsapp_status_setup; não criar solicitação duplicada |
| Cadastre as 12 artes aprovadas | register_whatsapp_status_approved_bundle (bundle fixo versus_20261007); agenda desativada |
| Liste kits/artes aprovadas | list_whatsapp_status_arts (kit, versão, ordem e hash) |
| Publique uma arte/kit | publish_whatsapp_status_art / kit; IDs/versionamento e chave única do comando |
| Faça o teste com Versus 01 | publish_whatsapp_status_test, somente após conta/número verificados e gate humano |
| Ative a sequência semanal | resume_whatsapp_status_schedule, após conferência móvel e teste do atendimento |
| Pause as publicações | listar e pause_whatsapp_status_schedule em cada agenda ativa do tenant |
| Edite/revise a agenda | update_whatsapp_status_schedule pausa; resume com reviewed após revisão humana |
| Consulte enviados e falhas | list_whatsapp_status_results; distinguir accepted, failed, unknown e conferência móvel |
| Conferi a publicação no celular | confirm_whatsapp_status_mobile com ID e aprovação humana |

Reutilizar a mesma command_key para repetição do mesmo comando. Nunca gerar
nova chave para contornar unknown/failed/dedupe. Uma nova publicação deliberada
deve ter autorização humana e respeitar o bloqueio diário de hash.
