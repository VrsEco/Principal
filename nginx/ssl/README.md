# 🔒 Certificados SSL

## Como Obter Certificado SSL GRÁTIS

### Usando Let's Encrypt (Recomendado)

```bash
# 1. Instalar Certbot
sudo apt-get update
sudo apt-get install certbot python3-certbot-nginx

# 2. Obter certificado
sudo certbot certonly --standalone -d congigr.com -d www.congigr.com

# 3. Certificados gerados em:
# /etc/letsencrypt/live/congigr.com/fullchain.pem
# /etc/letsencrypt/live/congigr.com/privkey.pem

# 4. Copiar para o projeto
sudo cp /etc/letsencrypt/live/congigr.com/fullchain.pem ./
sudo cp /etc/letsencrypt/live/congigr.com/privkey.pem ./
```

### Renovação Automática

```bash
# Adicionar ao crontab
0 3 * * * certbot renew --quiet --deploy-hook "docker-compose restart nginx"
```

## Estrutura de Arquivos

```
nginx/ssl/
├── fullchain.pem    # Certificado completo (público)
├── privkey.pem      # Chave privada (NUNCA commitar!)
└── README.md        # Este arquivo
```

## ⚠️ IMPORTANTE

1. **NUNCA** commite arquivos `.pem` ou `.key` no Git
2. Arquivos SSL já estão no `.gitignore`
3. Configure no servidor de produção
4. Use permissões adequadas: `chmod 600 privkey.pem`

## Desenvolvimento Local

Para desenvolvimento local, você pode:
1. Usar HTTP (sem SSL)
2. Gerar certificado auto-assinado (navegador vai avisar)

```bash
# Certificado auto-assinado (dev only)
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout privkey.pem \
  -out fullchain.pem \
  -subj "/CN=localhost"
```

