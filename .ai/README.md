# 🤖 Configurações para Múltiplas IAs

Este diretório contém configurações de governança para diferentes assistentes de IA.

## 📁 Estrutura

```
.ai/
├── README.md                    ← Este arquivo
├── gemini-instructions.md       ← Google Gemini
├── claude-instructions.md       ← Anthropic Claude
└── chatgpt-instructions.md      ← OpenAI ChatGPT
```

## 🎯 IAs Suportadas

| IA | Arquivo de Configuração | Como Usa |
|----|------------------------|----------|
| **Cursor AI (Claude)** | `/.cursorrules` | Automático (raiz) |
| **GitHub Copilot** | `/.github/copilot-instructions.md` | Automático |
| **Google Gemini** | `.ai/gemini-instructions.md` | Manual |
| **Anthropic Claude** | `.ai/claude-instructions.md` | Manual |
| **ChatGPT** | `.ai/chatgpt-instructions.md` | Manual |

## 📖 Governança Completa

Todas as IAs devem seguir os padrões em:

```
docs/governance/
├── TECH_STACK.md           ← Stack aprovada
├── ARCHITECTURE.md         ← Arquitetura
├── CODING_STANDARDS.md     ← Padrões Python
├── DATABASE_STANDARDS.md   ← Padrões DB
├── API_STANDARDS.md        ← Padrões REST
├── FORBIDDEN_PATTERNS.md   ← Anti-patterns
└── DECISION_LOG.md         ← ADR
```

## 🚀 Como Usar

### Para Cursor AI (Automático)
```
✅ Já configurado via .cursorrules
Não precisa fazer nada!
```

### Para GitHub Copilot (Automático)
```
✅ Já configurado via .github/copilot-instructions.md
Não precisa fazer nada!
```

### Para Codex (Manual/API)
```
1. Se via API: Use como system message
2. Se via playground: Cole no início
3. Veja exemplos em .ai/codex-instructions.md
```

### Para Gemini (Manual)
```
1. Copie conteúdo de .ai/gemini-instructions.md
2. Cole no início da conversa
3. Pergunte: "Confirma que leu a governança?"
```

### Para Claude Web/App (Manual)
```
1. Copie conteúdo de .ai/claude-instructions.md
2. Cole no início da conversa
3. Ou crie Custom Instructions com este conteúdo
```

### Para ChatGPT (Manual)
```
1. Copie conteúdo de .ai/chatgpt-instructions.md
2. Cole no início da conversa
3. Ou configure em Settings > Custom Instructions
```

## 🔄 Atualização

Quando atualizar governança em `docs/governance/`:
1. Atualizar `.cursorrules` (raiz)
2. Atualizar `.github/copilot-instructions.md`
3. Atualizar `.ai/*.md`

## 📝 Manutenção

| Arquivo | Responsável | Frequência |
|---------|-------------|-----------|
| `.cursorrules` | Tech Lead | Mensal |
| `copilot-instructions.md` | Tech Lead | Mensal |
| `.ai/*.md` | Tech Lead | Mensal |

---

**Versão:** 1.0  
**Data:** 18/10/2025

