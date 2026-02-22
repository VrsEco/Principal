# 🔧 Implementação do Botão Editar - Instruções Manuais

## ✅ Backend Completo (JÁ IMPLEMENTADO)

### 1. Serviço (`services/notes_service.py`)
- ✅ Função `update_note()` criada
- ✅ Validação de ownership
- ✅ Validação de dados

### 2. API (`api/notes.py`)  
- ✅ Endpoint `PUT /api/notes/<id>` criado
- ✅ Tratamento de erros 400/403/404/500

---

## 📝 Frontend - PENDENTE (Edição Manual Necessária)

### Arquivo: `templates/ecosystem.html`

#### 1. Adicionar Estilo CSS (linha ~395)

Após `.note-controls .btn-primary`, adicionar:

```css
    .note-controls .btn-secondary {
      background: linear-gradient(135deg, #f59e0b, #d97706);
      color: #fff;
    }
```

#### 2. Adicionar Botão HTML (linha ~568)

Alterar:
```html
<div class="note-controls">
  <button class="btn-primary" id="action-create" disabled>Criar atividade</button>
  <button class="btn-danger" id="action-delete" disabled>Excluir</button>
</div>
```

Para:
```html
<div class="note-controls">
  <button class="btn-primary" id="action-create" disabled>Criar atividade</button>
  <button class="btn-secondary" id="action-edit" disabled>Editar</button>
  <button class="btn-danger" id="action-delete" disabled>Excluir</button>
</div>
```

#### 3. Adicionar Referência no JavaScript (linha ~635)

Alterar:
```javascript
const actionCreate = document.getElementById("action-create");
const actionDelete = document.getElementById("action-delete");
```

Para:
```javascript
const actionCreate = document.getElementById("action-create");
const actionEdit = document.getElementById("action-edit");
const actionDelete = document.getElementById("action-delete");
```

#### 4. Atualizar função updateSelection (linha ~690)

Alterar:
```javascript
function updateSelection(id) {
  selectedNoteId = id;
  actionCreate.disabled = !id;
  actionDelete.disabled = !id;
  renderNotes();
}
```

Para:
```javascript
function updateSelection(id) {
  selectedNoteId = id;
  actionCreate.disabled = !id;
  actionEdit.disabled = !id;
  actionDelete.disabled = !id;
  renderNotes();
}
```

#### 5. Adicionar Função updateNoteOnServer (após loadNotes, linha ~742)

```javascript
async function updateNoteOnServer(noteId, text) {
  try {
    const response = await fetch(`${notesEndpoint}/${noteId}`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        "Accept": "application/json",
      },
      body: JSON.stringify({ text }),
    });

    const result = await response.json();

    if (!response.ok || !result.success) {
      throw new Error(result.message || "Erro ao atualizar nota no servidor.");
    }

    return result.note;
  } catch (error) {
    console.error("Erro ao atualizar nota:", error);
    throw error;
  }
}
```

#### 6. Adicionar Event Listener do Botão Editar (antes de actionCreate, linha ~795)

```javascript
actionEdit.addEventListener("click", async () => {
  if (!selectedNoteId) return;

  const note = notes.find((n) => n.id === selectedNoteId);
  if (!note) return;

  const newText = prompt(`Editar nota ${note.code}:`, note.text);
  
  if (newText === null) return; // Cancelled
  
  const trimmedText = newText.trim();
  if (!trimmedText) {
    alert("O texto da nota não pode estar vazio.");
    return;
  }

  if (trimmedText === note.text) return; // No changes

  // Disable button while updating
  actionEdit.disabled = true;
  const originalBtnText = actionEdit.textContent;
  actionEdit.textContent = "Atualizando...";

  try {
    const updatedNote = await updateNoteOnServer(selectedNoteId, trimmedText);
    
    // Update in local list
    const index = notes.findIndex((n) => n.id === selectedNoteId);
    if (index >= 0) {
      notes[index] = {
        ...updatedNote,
        id: String(updatedNote.id),
      };
    }
    
    renderNotes();
    
    // Show success feedback
    actionEdit.textContent = "✓ Atualizada!";
    setTimeout(() => {
      actionEdit.textContent = originalBtnText;
      actionEdit.disabled = false;
    }, 2000);
  } catch (error) {
    alert(`Erro ao atualizar nota: ${error.message}`);
    actionEdit.textContent = originalBtnText;
    actionEdit.disabled = false;
  }
});
```

---

## 🎯 Resumo das Mudanças

| Arquivo | Status | Descrição |
|---------|--------|-----------|
| `services/notes_service.py` | ✅ Completo | Função update_note |
| `api/notes.py` | ✅ Completo | Endpoint PUT |
| `templates/ecosystem.html` | ⚠️ Manual | 6 edições necessárias |

---

## 🧪 Como Testar

1. Fazer as 6 edições manuais acima
2. Reiniciar o servidor
3. Acessar `/main`
4. Criar uma nota
5. Selecionar a nota
6. Clicar em "Editar"
7. Alterar o texto no prompt
8. Verificar atualização na lista

---

## 📊 Funcionalidades Completas

- ✅ Criar nota (POST)
- ✅ Listar notas (GET)
- ✅ Editar nota (PUT) - Backend pronto, frontend pendente
- ✅ Excluir nota (DELETE)
- ✅ Geração automática de código
- ✅ Validação de ownership
- ✅ Feedback visual

---

**Nota**: O arquivo `ecosystem.html` está tendo problemas com edições automáticas devido ao seu tamanho e complexidade. As edições manuais acima são simples e diretas.
