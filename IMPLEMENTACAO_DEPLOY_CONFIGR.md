# Plano de Implementação: Sistemática de Deploy (Local -> GitHub -> Configr)

Este plano descreve a automação do processo de deploy para garantir que as alterações feitas localmente cheguem ao servidor Configr.com de forma segura e consistente, respeitando as diferenças entre os ambientes.

## 1. Arquitetura de Ambientes

| Recurso | Ambiente Local | Ambiente Configr (Produção) |
| :--- | :--- | :--- |
| **Branch Git** | `main` | `main` |
| **Configuração** | `.env` local | `.env` no servidor (não versionado) |
| **Banco de Dados** | PostgreSQL Local | PostgreSQL Configr |
| **Static/Uploads** | Pasta `uploads/` local | Pasta `/home/app2/public_html/uploads` |
| **Servidor Web** | Flask Dev Server | Apache/Passenger |

## 2. Etapas de Configuração

### A. Preparação do Servidor Configr (SSH)
1.  **Chave de Deploy**: Gerar uma chave SSH no servidor Configr (ou usar a gerada localmente) e adicioná-la como "Deploy Key" no GitHub ou como secret.
2.  **Clone Inicial**: O código deve estar no diretório `/home/app2/public_html`.

### B. Gestão de Segredos (GitHub Actions)
Configurar os seguintes "Secrets" no repositório GitHub:
*   `CONFIGR_HOST`: `ip-69-164-205-75.cloudezapp.io`
*   `CONFIGR_PORT`: `22122`
*   `CONFIGR_USER`: `app2`
*   `CONFIGR_SSH_PRIVATE_KEY`: A chave privada correspondente à chave pública autorizada no servidor.

### C. Workflow do GitHub Actions
O arquivo `.github/workflows/deploy-configr.yml` automatiza:
1.  Conexão via SSH.
2.  `git reset --hard origin/main`.
3.  Atualização do `venv` (`pip install -r requirements.txt`).
4.  Execução de migrações do banco (`flask db upgrade`).
5.  Restart da aplicação (`touch tmp/restart.txt`).

## 3. Respeito às Diferenças de Ambiente

1.  **Arquivos Sensíveis**: O `.env` original no Configr é preservado.
2.  **Migrações**: Sincronização automática do schema.
3.  **Encodings**: UTF-8 em ambos os ambientes.
4.  **Pastas**: Uso de variáveis de ambiente para caminhos de upload.

## 4. Próximos Passos
1.  [ ] Configurar as Secrets no GitHub.
2.  [ ] Adicionar a chave pública ao servidor.
3.  [ ] Realizar o push do código atualizado.
