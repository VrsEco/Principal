# 🤖 Integração com Múltiplas IAs

**Última Atualização:** 18/10/2025  
**Versão:** 1.0  
**Status:** ✅ Configurado

---

## 🎯 Visão Geral

Este projeto está configurado para funcionar com **múltiplas assistentes de IA**, todas seguindo a mesma governança técnica.

## 🔧 IAs Suportadas

| IA | Método | Arquivo | Status |
|----|--------|---------|--------|
| **Cursor AI** | Automático | `/.cursorrules` | ✅ Configurado |
| **MCP (Model Context Protocol)** | Automático | `src/core/mcp_server.py` | ✅ Ativo |
| **GitHub Copilot** | Automático | `/.github/copilot-instructions.md` | ✅ Configurado |
| **OpenAI Codex** | Manual/API | `/.ai/codex-instructions.md` | ✅ Configurado |
| **Google Gemini** | Manual | `/.ai/gemini-instructions.md` | ✅ Configurado |
| **Anthropic Claude** | Manual | `/.ai/claude-instructions.md` | ✅ Configurado |
| **OpenAI ChatGPT** | Manual | `/.ai/chatgpt-instructions.md` | ✅ Configurado |

---

## 📁 Estrutura de Configuração

```
GestaoVersus/app30/
│
├── .cursorrules                          ← Cursor AI (automático)
│
├── .github/
│   └── copilot-instructions.md           ← GitHub Copilot (automático)
│
└── .ai/
    ├── README.md                         ← Guia de uso
    ├── codex-instructions.md             ← OpenAI Codex
    ├── gemini-instructions.md            ← Google Gemini
    ├── claude-instructions.md            ← Anthropic Claude
    └── chatgpt-instructions.md           ← OpenAI ChatGPT

GestaoVersus/app32/src/intelligence/
└── tools.py                             ← Definição de Ferramentas MCP/AI
```

---

## 🚀 Como Usar Cada IA

### 1. Cursor AI (Claude) - ✅ Automático

**Configuração:** Já feito via `.cursorrules` (raiz)

**Como usar:**
```
1. Abra o projeto no Cursor
2. Comece a trabalhar normalmente
3. O Cursor LÊ AUTOMATICAMENTE o .cursorrules
4. Todas as regras são aplicadas automaticamente
```

**Teste:**
```
Você: "Como criar uma API REST para projetos?"

Cursor: [Responde seguindo API_STANDARDS.md automaticamente]
```

**Nível de automação:** 🟢 Alto (não precisa fazer nada)

---

### 1.1 MCP (Model Context Protocol) - ✅ Ativo
O sistema expõe funcionalidades de negócio diretamente para IAs via ferramentas estruturadas.

**Regra do Espelhamento:**
- Toda funcionalidade crítica (Layer 3) deve ter uma Tool correspondente em `src/intelligence/tools.py`.
- As ferramentas devem ser **Context-Aware** (funcionar via Flask Session ou ACTIVE_COMPANY_ID).
- **Segurança:** Filtros de `company_id` devem ser injetados programaticamente nas ferramentas.

---

### 2. GitHub Copilot - ✅ Automático

**Configuração:** Já feito via `.github/copilot-instructions.md`

**Como usar:**
```
1. Abra o projeto no VSCode/outro editor com Copilot
2. Comece a digitar código
3. Copilot LÊ AUTOMATICAMENTE o arquivo de instruções
4. Sugestões seguem os padrões do projeto
```

**Teste:**
```python
# Digite:
def create_project

# Copilot sugere (seguindo padrões):
def create_project(company_id: int) -> dict:
    """Cria novo projeto."""
    # ... código seguindo padrões
```

**Nível de automação:** 🟢 Alto (sugestões seguem padrões)

---

### 3. OpenAI Codex - 🔵 Manual/API

**Configuração:** Use `.ai/codex-instructions.md` como system prompt ou cole no início

**Como usar:**

#### Opção A: Via API (Programático)
```python
import openai

system_message = """
[Cole conteúdo de .ai/codex-instructions.md aqui]
"""

response = openai.ChatCompletion.create(
    model="gpt-3.5-turbo",  # ou gpt-4
    messages=[
        {"role": "system", "content": system_message},
        {"role": "user", "content": "Create Flask route for projects"}
    ],
    temperature=0.2  # Mais consistente
)
```

#### Opção B: Playground/IDE
```
1. OpenAI Playground ou IDE com Codex
2. System message: Cole .ai/codex-instructions.md
3. User message: Sua pergunta
4. Codex responde seguindo padrões
```

**Teste:**
```
Você: "Generate Flask route to create projects"

Codex: [Gera com @login_required, @auto_log_crud, validation, etc.]
```

**Nível de automação:** 🟡 Médio (API) / 🟢 Alto (se configurado em IDE)

---

### 4. Google Gemini - 🔵 Manual

**Configuração:** Cole conteúdo de `.ai/gemini-instructions.md`

**Como usar:**

#### Opção A: Cole no Início da Conversa
```
1. Abra Gemini (web ou app)
2. Copie CONTEÚDO COMPLETO de .ai/gemini-instructions.md
3. Cole na primeira mensagem
4. Gemini responde: "✅ Confirmo que li..."
5. Agora pode fazer perguntas normalmente
```

#### Opção B: Referencie o Arquivo (se Gemini tiver acesso)
```
Você: "Leia .ai/gemini-instructions.md e confirme que entendeu."

Gemini: [Lê e confirma]
```

**Teste:**
```
Você: "Crie uma API REST para gerenciar projetos"

Gemini: [Gera código seguindo todos os padrões]
```

**Nível de automação:** 🟡 Médio (precisa colar uma vez por conversa)

**Dica:** Salve como snippet ou template para facilitar.

---

### 5. Anthropic Claude (Web/App) - 🔵 Manual

**Configuração:** Cole conteúdo de `.ai/claude-instructions.md`

**Como usar:**

#### Opção A: Cole no Início
```
1. Abra Claude (web ou app)
2. Copie conteúdo de .ai/claude-instructions.md
3. Cole na primeira mensagem
4. Claude confirma: "✅ Confirmo que li..."
5. Trabalhe normalmente
```

#### Opção B: Custom Instructions (se disponível)
```
1. Claude → Settings → Custom Instructions
2. Cole conteúdo de .ai/claude-instructions.md
3. Salve
4. Todas as conversas seguirão automaticamente
```

**Teste:**
```
Você: "Preciso criar um model para projetos"

Claude: [Gera model com todos os campos obrigatórios]
```

**Nível de automação:** 🟡 Médio (Custom Instructions = automático)

---

### 6. OpenAI ChatGPT - 🔵 Manual

**Configuração:** Cole conteúdo de `.ai/chatgpt-instructions.md`

**Como usar:**

#### Opção A: Cole no Início
```
1. Abra ChatGPT
2. Copie conteúdo de .ai/chatgpt-instructions.md
3. Cole na primeira mensagem
4. ChatGPT confirma
5. Trabalhe normalmente
```

#### Opção B: Custom Instructions (Recomendado)
```
1. ChatGPT → Settings → Custom Instructions
2. Campo "What would you like ChatGPT to know about you":
   - Cole primeira parte (contexto do projeto)
3. Campo "How would you like ChatGPT to respond":
   - Cole segunda parte (como gerar código)
4. Salve
5. Todas as conversas seguirão automaticamente
```

**Teste:**
```
Você: "Gere uma rota Flask para listar projetos"

ChatGPT: [Gera rota com @login_required, paginação, etc.]
```

**Nível de automação:** 🟢 Alto (com Custom Instructions)

---

## 📊 Comparação de IAs

| IA | Automação | Setup | Melhor Para |
|----|-----------|-------|-------------|
| **Cursor** | 🟢 Alta | Nenhum | Desenvolvimento diário |
| **Copilot** | 🟢 Alta | Nenhum | Autocomplete inteligente |
| **Codex** | 🟡 Média | System prompt | Geração via API/script |
| **Gemini** | 🟡 Média | Cole 1x/conversa | Explicações e análises |
| **Claude** | 🟡 Média | Custom Instructions | Refatoração e review |
| **ChatGPT** | 🟢 Alta | Custom Instructions | Prototipagem rápida |

---

## 🎯 Quando Usar Cada IA

### Cursor AI (Primária)
**Use para:**
- ✅ Desenvolvimento dia-a-dia
- ✅ Edição de código existente
- ✅ Refatoração
- ✅ Debug

**Por quê:** Integrado ao editor, lê arquivos automaticamente

---

### GitHub Copilot (Complementar)
**Use para:**
- ✅ Autocomplete enquanto digita
- ✅ Implementações rápidas
- ✅ Boilerplate code

**Por quê:** Sugestões inline em tempo real

---

### Google Gemini (Consulta)
**Use para:**
- ✅ Explicações detalhadas
- ✅ Análise de arquitetura
- ✅ Brainstorming de soluções
- ✅ Code review extenso

**Por quê:** Ótimo para análise e explicação

---

### Claude (Review e Refatoração)
**Use para:**
- ✅ Code review detalhado
- ✅ Refatoração de código legado
- ✅ Documentação técnica
- ✅ Identificar anti-patterns

**Por quê:** Excelente em análise e qualidade

---

### ChatGPT (Prototipagem)
**Use para:**
- ✅ Protótipos rápidos
- ✅ Scripts utilitários
- ✅ Testes
- ✅ Exploração de ideias

**Por quê:** Rápido e versátil

---

## 💡 Workflow Recomendado

### Feature Nova (Completa)

```
1. ChatGPT/Gemini → Brainstorm e planejamento
   "Preciso criar módulo de relatórios. Como estruturar?"

2. Cursor AI → Implementação
   "Crie o código seguindo o plano"

3. Copilot → Completar detalhes
   [Autocomplete enquanto digita]

4. Claude → Code review
   "Revise este código contra FORBIDDEN_PATTERNS.md"

5. Cursor AI → Correções finais
   "Aplique sugestões do review"
```

### Bug Fix (Rápido)

```
1. Cursor AI → Identificar problema
   "Analise este erro: [stack trace]"

2. Cursor AI → Implementar fix
   "Corrija seguindo CODING_STANDARDS.md"

3. Claude → Validar
   "Este fix está correto?"
```

### Refatoração (Detalhada)

```
1. Claude → Análise
   "Analise este arquivo e sugira melhorias"

2. Gemini → Arquitetura
   "Como refatorar mantendo arquitetura?"

3. Cursor AI → Implementação
   "Refatore seguindo sugestões"

4. Copilot → Ajustes finos
   [Autocomplete durante refatoração]
```

---

## 🔄 Manutenção dos Arquivos de Configuração

### Quando Atualizar

Atualizar TODAS as configurações quando:
- ✅ Adicionar nova tecnologia aprovada
- ✅ Proibir nova tecnologia
- ✅ Mudar padrão de código importante
- ✅ Adicionar novo anti-pattern crítico
- ✅ Atualizar versão de dependência importante

### Arquivos a Atualizar (em ordem)

```bash
1. docs/governance/[documento].md    # Fonte da verdade
2. .cursorrules                      # Cursor AI
3. .github/copilot-instructions.md   # Copilot
4. .ai/gemini-instructions.md        # Gemini
5. .ai/claude-instructions.md        # Claude
6. .ai/chatgpt-instructions.md       # ChatGPT
```

### Checklist de Atualização

- [ ] Atualizar docs/governance/
- [ ] Atualizar .cursorrules
- [ ] Atualizar .github/copilot-instructions.md
- [ ] Atualizar .ai/gemini-instructions.md
- [ ] Atualizar .ai/claude-instructions.md
- [ ] Atualizar .ai/chatgpt-instructions.md
- [ ] Testar com cada IA
- [ ] Documentar mudança em DECISION_LOG.md

---

## 🧪 Como Testar se IA Está Seguindo Padrões

### Teste Universal (Funciona em Qualquer IA)

```
Você: "Crie uma rota Flask completa para criar projetos.
       Inclua TODOS os padrões do projeto."

✅ IA Deve Incluir:
- @login_required
- @auto_log_crud('project')
- Validação de entrada
- Response format padronizado {'success': bool, 'data': ...}
- Status code 201 para criação
- Docstring
- Type hints

❌ IA NÃO Deve Incluir:
- print() statements
- Credenciais hardcoded
- Bare except
- Tipos PostgreSQL específicos (JSONB, ARRAY)
```

### Teste de Proibições

```
Você: "Posso usar React no frontend?"

✅ IA Deve Responder:
"Não, React está na lista de tecnologias proibidas.
Use JavaScript Vanilla ES6+ conforme TECH_STACK.md."

❌ IA NÃO Deve:
Sugerir usar React ou outro framework
```

---

## 📚 Recursos Adicionais

### Documentação Completa
- `docs/governance/` - Toda a governança
- `docs/INDEX.md` - Índice de navegação
- `.ai/README.md` - Guia específico de IAs

### Arquivos de Configuração
- `.cursorrules` - Cursor AI
- `.github/copilot-instructions.md` - GitHub Copilot
- `.ai/*.md` - Outras IAs

---

## ✅ Checklist de Setup para Nova IA

Se quiser adicionar suporte a outra IA:

- [ ] Criar arquivo `.ai/[nome]-instructions.md`
- [ ] Incluir contexto do projeto
- [ ] Incluir stack aprovada/proibida
- [ ] Incluir padrões de código
- [ ] Incluir exemplos práticos
- [ ] Incluir anti-patterns proibidos
- [ ] Testar com casos de uso reais
- [ ] Documentar em `.ai/README.md`
- [ ] Adicionar neste documento

---

## 🎉 Conclusão

Agora você tem:
- ✅ 6 IAs configuradas para seguir governança
- ✅ 2 automáticas (Cursor, Copilot)
- ✅ 4 manuais/configuráveis (Codex, Gemini, Claude, ChatGPT)
- ✅ Workflow recomendado
- ✅ Testes de validação

**Todas as IAs seguem a mesma governança = Código consistente sempre!** 🚀

---

**Responsável:** Tech Lead  
**Próxima revisão:** Mensal (junto com TECH_STACK.md)

