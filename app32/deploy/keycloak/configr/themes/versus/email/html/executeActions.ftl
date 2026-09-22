<#-- Email de ação nativo do Keycloak, apenas com apresentação Versus. -->
<!doctype html>
<html lang="pt-BR">
  <body style="margin:0;padding:0;background:#f5f8fc;font-family:Segoe UI,Arial,sans-serif;color:#172033;">
    <div style="max-width:640px;margin:24px auto;padding:0 14px;">
      <div style="background:linear-gradient(145deg,#112a61 0%,#1d4baa 100%);border-radius:16px;padding:26px 28px;color:#ffffff;">
        <img src="${url.resourcesUrl}/img/versus-logo-light-v2.png" alt="Versus Gestão Corporativa" width="190" style="display:block;max-width:190px;height:auto;border:0;" />
        <div style="margin-top:22px;font-size:11px;font-weight:700;letter-spacing:.8px;text-transform:uppercase;opacity:.92;">Acesso seguro</div>
        <h1 style="margin:8px 0 0;font-size:25px;line-height:1.25;">Defina sua senha</h1>
      </div>
      <div style="margin-top:14px;padding:24px 26px;border:1px solid #dbe4ee;border-radius:16px;background:#ffffff;line-height:1.65;">
        <p style="margin:0 0 14px;font-size:15px;color:#334155;">Olá,</p>
        <p style="margin:0 0 20px;font-size:15px;color:#334155;">Recebemos uma solicitação para definir ou atualizar sua senha de acesso ao <strong>Gestão Versus</strong>.</p>
        <p style="margin:0 0 22px;"><a href="${link?html}" style="display:inline-block;padding:13px 20px;border-radius:10px;background:#2563eb;color:#ffffff;text-decoration:none;font-size:15px;font-weight:700;">Definir senha de acesso</a></p>
        <p style="margin:0;font-size:13px;color:#64748b;">Por segurança, este link expira em ${linkExpirationFormatter(linkExpiration)}. Se você não solicitou esta ação, ignore esta mensagem.</p>
      </div>
      <div style="padding:16px 8px;text-align:center;color:#64748b;font-size:12px;line-height:1.5;">Sapiens Versus · Gestão Corporativa<br>Mensagem automática de segurança.</div>
    </div>
  </body>
</html>
