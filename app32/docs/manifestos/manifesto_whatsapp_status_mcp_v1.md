# Manifesto — Status WhatsApp tenant-owned

Aplicar a [SPEC](../spec/whatsapp_status_mcp_v1.md).

- Identidade OAuth humana, grant AA restrito e surface admin por chamada.
- Permissões exclusivas: whatsapp_status.read, publish, schedule e review.
- Nenhuma leitura de conversas/contatos ou alteração de tokens/webhooks/dispositivos.
- Mídia identificada/versionada, privada e com hash; não existe URL livre de publicação.
- Publicação/retomada/conferência/configuração/importação exigem gate persistido.
- Falha/incerteza para a sequência; crash não reenvia. accepted não significa visto no celular.
- O conector permanece mcp-versus; não criar conexão, conta ou contratação paralela.
