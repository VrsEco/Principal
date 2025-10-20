# Bugfix: [Título do Bug]

**Data de Criação:** YYYY-MM-DD  
**Responsável:** [Nome]  
**Status:** 🔍 Investigando | 🔄 Em Correção | ✅ Corrigido | ✔️ Verificado  
**Severidade:** 🔴 Crítica | 🟡 Alta | 🟢 Média | ⚪ Baixa  
**Ambiente:** 🌐 Produção | 🧪 Staging | 💻 Desenvolvimento

---

## 🐛 Descrição do Bug

### Resumo
[Descrição curta do problema em 1-2 frases]

### Comportamento Esperado
[O que deveria acontecer]

### Comportamento Atual
[O que está acontecendo]

### Impacto
- **Usuários afetados:** [Todos | Alguns | Admin apenas | etc.]
- **Frequência:** [Sempre | Às vezes | Raramente]
- **Workaround disponível?** [Sim/Não - descrever se sim]

---

## 📸 Evidências

### Screenshots/Vídeos
[Anexar ou descrever]

### Logs de Erro
```
[Colar logs relevantes aqui]
```

### Stack Trace (se aplicável)
```python
[Colar stack trace completo]
```

---

## 🔄 Reprodução

### Passos para Reproduzir
1. Acessar [URL ou página]
2. Clicar em [elemento]
3. Preencher [campo] com [valor]
4. [Próximo passo]
5. Observar erro

### Dados de Teste
```json
{
  "campo1": "valor1",
  "campo2": "valor2"
}
```

### Ambiente de Teste
- **Browser:** [Chrome 120, Firefox 115, etc.]
- **OS:** [Windows 11, macOS 14, etc.]
- **Banco de Dados:** [PostgreSQL 15, SQLite 3.43]
- **Versão da aplicação:** [commit hash ou tag]

### Reproduzível?
- [ ] Sempre (100%)
- [ ] Frequentemente (> 50%)
- [ ] Às vezes (< 50%)
- [ ] Raramente (< 10%)
- [ ] Não consegui reproduzir

---

## 🔍 Investigação

### Causa Raiz
[Descrever a causa raiz identificada. Se ainda não identificada, colocar "Em investigação"]

**Exemplos:**
- Validação faltando no campo X
- N+1 query causando timeout
- Condição de corrida em transação
- Encoding UTF-8 não configurado
- etc.

### Arquivos Envolvidos
- [ ] `[caminho/arquivo.py]` - [descrição do problema]
- [ ] `[caminho/arquivo.html]` - [descrição do problema]
- [ ] `[caminho/arquivo.js]` - [descrição do problema]

### Linha(s) do Código Problemático
```python
# arquivo.py:linha_numero
# Código problemático
def funcao_com_bug(param):
    resultado = param + 1  # Bug: não valida se param é None
    return resultado
```

### Por Que o Bug Aconteceu?
[Explicar o contexto que levou ao bug]

**Exemplos:**
- Validação não foi implementada inicialmente
- Mudança anterior introduziu regressão
- Caso de uso não foi considerado
- Falta de testes para este cenário

---

## 🔧 Solução

### Abordagem Escolhida
[Descrever a solução implementada]

### Código Corrigido
```python
# arquivo.py:linha_numero
# Código corrigido
def funcao_corrigida(param):
    if param is None:
        raise ValueError("param não pode ser None")
    resultado = param + 1
    return resultado
```

### Alternativas Consideradas

**Opção 1:** [Descrição]
- Prós: [...]
- Contras: [...]
- Por que não escolhida: [...]

**Opção 2 (Escolhida):** [Descrição]
- Prós: [...]
- Contras: [...]
- Por que escolhida: [...]

### Mudanças Necessárias

**Arquivos Modificados:**
- [ ] `[caminho/arquivo1.py]` - [o que mudou]
- [ ] `[caminho/arquivo2.py]` - [o que mudou]

**Arquivos Criados:**
- [ ] `[caminho/arquivo_novo.py]` - [propósito]

**Migrations Necessárias?**
- [ ] Não
- [ ] Sim: [descrever migration]

---

## 🧪 Testes

### Testes Adicionados

**Teste para Reproduzir o Bug:**
```python
def test_bug_[numero]_[descricao]:
    """Teste que reproduz o bug original."""
    # Arrange
    param = None
    
    # Act & Assert
    with pytest.raises(ValueError, match="não pode ser None"):
        funcao_corrigida(param)
```

**Teste para Validar Fix:**
```python
def test_fix_[numero]_[descricao]:
    """Teste que valida a correção."""
    # Arrange
    param = 5
    
    # Act
    resultado = funcao_corrigida(param)
    
    # Assert
    assert resultado == 6
```

### Testes de Regressão
- [ ] Testar cenário original (que quebrava)
- [ ] Testar cenários similares
- [ ] Testar happy path (não quebrou funcionalidade normal)
- [ ] Testar edge cases

### Testes Manuais
- [ ] Reproduzir bug original (não deve mais aparecer)
- [ ] Testar funcionalidade completa
- [ ] Testar em diferentes navegadores (se frontend)
- [ ] Testar em PostgreSQL E SQLite (se DB)

---

## ✅ Checklist de Validação

### Correção
- [ ] Bug foi corrigido na raiz (não apenas sintoma)
- [ ] Solução não introduz novos problemas
- [ ] Código segue CODING_STANDARDS.md
- [ ] Não viola FORBIDDEN_PATTERNS.md

### Testes
- [ ] Teste que reproduz bug foi adicionado
- [ ] Teste que valida fix foi adicionado
- [ ] Testes de regressão passando
- [ ] Cobertura de código não diminuiu

### Documentação
- [ ] Comentários explicando fix (se código complexo)
- [ ] README atualizado (se necessário)
- [ ] CHANGELOG atualizado
- [ ] Post-mortem criado (se bug crítico)

### Deploy
- [ ] Testado localmente
- [ ] Testado em staging
- [ ] Rollback plan definido (se crítico)

---

## 🚀 Deploy

### Urgência
- [ ] 🔴 Hotfix (deploy imediato)
- [ ] 🟡 Alta (próximo deploy)
- [ ] 🟢 Normal (próximo sprint)

### Plano de Deploy
1. [Passo 1]
2. [Passo 2]
3. [Passo 3]

### Rollback Plan
Se algo der errado após deploy:
1. [Como reverter]
2. [Dados a preservar]
3. [Comunicação necessária]

### Comunicação
- [ ] Notificar usuários afetados? [Sim/Não]
- [ ] Atualizar status page? [Sim/Não]
- [ ] Informar time? [Sim/Não]

---

## 📊 Prevenção Futura

### Como Evitar Similar?

**Testes:**
- [ ] Adicionar testes para casos similares
- [ ] Aumentar cobertura de testes

**Código:**
- [ ] Adicionar validação/assertion em locais similares
- [ ] Refatorar código frágil
- [ ] Adicionar type hints

**Processo:**
- [ ] Adicionar checklist de code review
- [ ] Atualizar FORBIDDEN_PATTERNS.md
- [ ] Treinar time sobre este tipo de bug

**Monitoramento:**
- [ ] Adicionar logs específicos
- [ ] Criar alerta para detectar similar
- [ ] Implementar health check

### Lições Aprendidas
1. [Lição 1]
2. [Lição 2]
3. [Lição 3]

---

## 🔗 Referências

- **Issue/Ticket:** [link]
- **PR com fix:** [link]
- **Discussão:** [link]
- **Bugs similares:** [links]
- **Documentação relevante:** [links]

---

## 📅 Cronologia

| Data/Hora | Evento | Responsável |
|-----------|--------|-------------|
| YYYY-MM-DD HH:MM | Bug reportado | [Nome] |
| YYYY-MM-DD HH:MM | Investigação iniciada | [Nome] |
| YYYY-MM-DD HH:MM | Causa raiz identificada | [Nome] |
| YYYY-MM-DD HH:MM | Fix implementado | [Nome] |
| YYYY-MM-DD HH:MM | Testes adicionados | [Nome] |
| YYYY-MM-DD HH:MM | PR aprovado | [Nome] |
| YYYY-MM-DD HH:MM | Deployed em produção | [Nome] |
| YYYY-MM-DD HH:MM | Verificado funcionando | [Nome] |

---

## 📝 Post-Mortem (Se Bug Crítico)

### Timeline Detalhada
- **HH:MM** - [Evento]
- **HH:MM** - [Evento]

### O Que Correu Bem?
- [Item 1]
- [Item 2]

### O Que Poderia Ser Melhor?
- [Item 1]
- [Item 2]

### Action Items
- [ ] [Ação 1] - Responsável: [Nome] - Prazo: [Data]
- [ ] [Ação 2] - Responsável: [Nome] - Prazo: [Data]

---

## ✔️ Status Final

- [ ] Bug corrigido
- [ ] Testes adicionados e passando
- [ ] Code review aprovado
- [ ] Deployed em staging
- [ ] Validado em staging
- [ ] Deployed em produção
- [ ] Validado em produção
- [ ] Usuários notificados (se necessário)
- [ ] Documentação atualizada
- [ ] Post-mortem completo (se crítico)

**Data de Fechamento:** YYYY-MM-DD  
**Tempo Total para Correção:** [X horas/dias]

---

**Notas Adicionais:**
[Qualquer informação relevante adicional]



