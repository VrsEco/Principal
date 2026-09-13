# Runbook — Cronograma de Rotação de Credenciais APP32 v1

**Classe:** Runbook
**Fuso:** America/Bahia (BRT)
**Regra:** nunca registrar a credencial, seu valor, URL completa de conexão ou cópia de `.env` no card, chat, log ou commit.

## Janela operacional padrão

- A revisão ocorre no primeiro dia útil de cada mês, às 09:00 BRT.
- A rotação é executada em janela combinada, com teste de conexão, atualização segura do runtime Configr e smoke da aplicação.
- Uma credencial é rotacionada imediatamente em caso de suspeita de exposição, desligamento de responsável, acesso indevido ou incidente; não se aguarda a data prevista.

## Ciclos

| Classe | Exemplos | Ciclo | Próxima janela a partir de 12/09/2026 | Responsável |
|---|---|---:|---|---|
| Banco de dados de aplicação | usuário PostgreSQL do APP32 | 90 dias | 11/12/2026 | DBA/responsável APP32 |
| OAuth/OIDC e MCP | client secrets, tokens de serviço e integrações de IA | 90 dias | 11/12/2026 | Segurança/AI Engineer |
| CI/CD e acesso de deploy | chaves SSH, tokens GitHub e credenciais de automação | 90 dias | 11/12/2026 | Responsável de engenharia |
| E-mail transacional | SMTP da conta de serviço | 180 dias | 11/03/2027 | Responsável de infraestrutura |
| Chave de sessão Flask | `SECRET_KEY` | anual, com sobreposição controlada | 12/09/2027 | Backend/Segurança |

## Exceção obrigatória: `SECRET_KEY`

Não rotacionar como simples troca de variável. Ela pode invalidar sessões e fluxos assinados. Antes da janela anual, implantar suporte a chave anterior por período curto, validar login/redefinição de senha e só então retirar a chave antiga.

## Usuários finais

Não aplicar rotação periódica indiscriminada. A aplicação deve usar redefinição por e-mail, expiração de token, limite de tentativas e rotação imediata por compromisso de conta. Uma política de vencimento de senha, se aprovada, deve disparar o fluxo de redefinição já implementado.

## Checklist de cada rotação

1. Confirmar responsável e janela.
2. Criar a credencial nova no provedor, sem exibi-la em evidências.
3. Atualizar somente o armazenamento seguro/runtime correspondente.
4. Executar teste de conexão e smoke funcional.
5. Revogar a credencial anterior após a validação e janela de rollback.
6. Registrar no AA.J apenas data, classe, responsável, resultado e identificador não sensível.

## Próxima revisão

**01/10/2026, 09:00 BRT:** revisar responsáveis, registrar as datas em calendário corporativo e preparar as rotações trimestrais de dezembro.
