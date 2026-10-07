# Paper — Publicação governada de Status WhatsApp

Comandos no chat utilizam o conector **mcp-versus existente**, com OAuth/PKCE,
identidade APP32 e serviço tenant-owned. O fornecedor continua sendo a instância
Z-API já contratada; o agendamento pertence ao scheduler dedicado do APP32.

Nenhum navegador opera publicações. A conexão inicial exige autenticação humana;
depois não há cópia de tokens. Artes são IDs versionados, aprovados e com
integridade verificada, nunca URLs livres.

Aceite do fornecedor, incerteza e conferência humana no celular são fatos distintos.
Crash/timeout interrompem a sequência e exigem revisão, sem reenvio automático.

Contrato: [SPEC](../spec/whatsapp_status_mcp_v1.md). Esta entrega local não é
evidência de implantação nem de funcionamento da conta real.
