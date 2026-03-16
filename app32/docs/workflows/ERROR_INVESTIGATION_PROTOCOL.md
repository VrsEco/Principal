# Protocolo Oficial de Investigação e Correção de Erros

## Objetivo

Padronizar a resposta técnica a incidentes no Gestão Versus seguindo o princípio:

1. **analisar primeiro em produção**
2. **comparar produção com desenvolvimento**
3. **corrigir divergência estrutural antes de alterar regra de negócio**
4. **só então evoluir o código em DEV e publicar**

---

## Fluxo obrigatório

### A. Analisar o erro primeiro em produção

Antes de alterar código em desenvolvimento:

- identificar a rota/fluxo exato com erro
- capturar horário exato do incidente
- verificar logs de produção
- verificar hash ativo em produção
- verificar resposta real da aplicação em produção
- verificar se o erro é:
  - de banco/schema
  - de configuração
  - de dependência
  - de dado
  - de código

Checklist mínimo:

- `git rev-parse --short HEAD` local
- hash ativo em produção
- logs do minuto do erro
- status HTTP real
- contexto de empresa/usuário/tenant

---

### B. Comparar produção com DEV

Comparar obrigatoriamente:

#### 1. Código
- hash local x hash produção
- diff dos arquivos do fluxo afetado

#### 2. Banco
- versão Alembic
- existência de colunas/tabelas esperadas
- constraints e tipos críticos
- dados mínimos exigidos para o fluxo

#### 3. Dependências
- `requirements.txt`
- ambiente virtual ativo
- versões efetivamente instaladas em produção

#### 4. Configuração
- variáveis de ambiente
- integrações externas
- tokens/chaves
- sessão/empresa ativa

---

### C. Se houver divergência entre produção e DEV

A divergência tem prioridade sobre refatoração funcional.

Ação obrigatória:

1. corrigir a divergência
2. publicar em produção
3. validar novamente o caso real

Exemplos:

- migration pendente
- coluna ausente
- código em produção atrás do `main`
- dependência diferente
- configuração ausente

---

### D. Se não houver divergência

Quando produção e DEV estiverem alinhados:

1. reproduzir no DEV
2. analisar o código
3. corrigir no DEV
4. validar tecnicamente
5. fazer deploy
6. validar novamente em produção

Validação mínima antes do deploy:

- `py_compile` ou teste equivalente
- revisão de multi-tenancy
- revisão de mensagens públicas
- checagem de impacto em rotas correlatas

---

## Regra de tratamento de erro público

### Obrigatório

- nunca retornar `str(e)` ao frontend
- nunca retornar SQL bruto
- nunca retornar traceback ao usuário
- manter log técnico no backend

Mensagem pública padrão:

`Erro interno do servidor. Tente novamente ou contate o suporte.`

---

## Regra de decisão

### Corrigir primeiro infraestrutura/schema quando:

- produção diverge de DEV
- erro é `UndefinedColumn`
- migration não aplicada
- endpoint funciona em DEV e quebra só em produção

### Corrigir primeiro código quando:

- produção e DEV estão alinhados
- erro reproduz localmente com mesmo schema/configuração
- causa está na lógica da rota/resource/service

---

## Evidências mínimas por incidente

Cada correção deve registrar:

- URL/rota afetada
- data e hora da análise
- hash local
- hash em produção
- diagnóstico de divergência ou não
- arquivos alterados
- resultado do deploy
- validação final

---

## Diretriz permanente

Toda nova investigação de erro no projeto deve seguir esta ordem:

**produção → comparação PROD x DEV → correção estrutural se houver divergência → correção funcional em DEV se não houver divergência → deploy → validação final**
