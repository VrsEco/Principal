// Notes functionality
(function () {
    const noteBoard = document.getElementById("noteBoard");
    const noteForm = document.getElementById("noteForm");
    const noteText = document.getElementById("noteText");
    const btnSaveNote = document.getElementById("btnSaveNote");
    const btnCancelEdit = document.getElementById("btnCancelEdit");
    let isEditing = false;
    let editNoteId = null;

    const noteDetailsModalTitle = document.getElementById("noteDetailsModalTitle");
    const noteDetailsModalMeta = document.getElementById("noteDetailsModalMeta");
    const noteDetailsModalBody = document.getElementById("noteDetailsModalBody");
    let noteDetailsModalInstance = null;

    if (document.getElementById("noteDetailsModal") && window.Modal) {
        noteDetailsModalInstance = new Modal("noteDetailsModal", {
            animation: true,
            backdrop: true,
            closeOnBackdrop: true,
            closeOnEscape: true,
        });
    }

    // Get endpoint from data attribute or default
    const notesEndpoint = document.body.dataset.notesEndpoint || "/api/notes/";

    let notes = [];
    let selectedNoteId = null;

    // Helper to ensure URL ends with slash before appending ID
    function getNoteUrl(id) {
        const base = notesEndpoint.endsWith('/') ? notesEndpoint : notesEndpoint + '/';
        return id ? `${base}${id}` : base;
    }

    async function handleResponse(response) {
        const contentType = response.headers.get("content-type");
        if (contentType && contentType.indexOf("application/json") !== -1) {
            const result = await response.json();
            if (!response.ok || !result.success) {
                throw new Error(result.message || "Erro na operação.");
            }
            return result;
        } else {
            // If not JSON, probably an HTML error page (404, 500)
            const text = await response.text();
            console.error("Resposta não-JSON do servidor:", text);
            throw new Error(`Erro do servidor (${response.status}). Verifique o console.`);
        }
    }

    function formatDate(value) {
        if (!value) {
            return "Sem data";
        }
        const parsed = new Date(value);
        if (Number.isNaN(parsed)) {
            return value;
        }
        return parsed.toLocaleDateString("pt-BR");
    }

    function escapeHtml(value) {
        if (value === undefined || value === null) {
            return "";
        }
        return String(value)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function openNoteModal(note) {
        if (!noteDetailsModalInstance || !noteDetailsModalBody) {
            return;
        }

        const displayCode = note.code || (note.id ? `Nota ${note.id}` : "Nota");
        const displayCreated = note.created_at ? formatDate(note.created_at) : note.created || "";
        const metaParts = [];

        if (displayCreated) {
            metaParts.push(displayCreated);
        }
        if (note.location) {
            metaParts.push(note.location);
        }

        if (noteDetailsModalTitle) {
            noteDetailsModalTitle.textContent = displayCode;
        }
        if (noteDetailsModalMeta) {
            noteDetailsModalMeta.textContent = metaParts.join(" • ");
            noteDetailsModalMeta.style.display = metaParts.length ? "block" : "none";
        }

        noteDetailsModalBody.innerHTML = escapeHtml(note.text).replace(/\n/g, "<br>");
        noteDetailsModalInstance.open();
    }

    function renderNotes() {
        if (!notes.length) {
            noteBoard.innerHTML =
                '<p class="empty-state">Nenhuma nota registrada até o momento.</p>';
            return;
        }

        noteBoard.innerHTML = notes
            .map((note) => {
                const noteId = note.id ? String(note.id) : note.code || "";
                const displayCode = note.code || noteId || "Nota";
                const displayCreated =
                    note.created_at ? formatDate(note.created_at) : note.created || "";
                const hasMeta = displayCode && displayCreated;
                const metaText = hasMeta
                    ? `${displayCode} | ${displayCreated}`
                    : displayCode || displayCreated;
                const locationText = note.location || "";

                return `
          <div class="note-row ${selectedNoteId === noteId ? "selected" : ""}" data-id="${noteId}">
            <div class="note-row-top" style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(0,0,0,0.05); padding-bottom: 6px; margin-bottom: 6px;">
              <span class="note-row-meta" style="flex: 1;">${metaText}</span>
              <div class="note-row-actions" style="display: flex; gap: 8px;">
                <button type="button" class="btn-icon btn-edit-note" title="Editar" style="background: none; border: none; cursor: pointer; color: var(--primary); padding: 4px;"><i class="fas fa-edit"></i></button>
                <button type="button" class="btn-icon btn-delete-note" title="Excluir" style="background: none; border: none; cursor: pointer; color: #ef4444; padding: 4px;"><i class="fas fa-trash"></i></button>
              </div>
            </div>
            <div class="note-row-bottom" style="cursor: pointer;" title="Clique para ver detalhes">
              <p class="note-row-text">${escapeHtml(note.text)}</p>
              ${locationText ? `<span class="note-row-location">${escapeHtml(locationText)}</span>` : ""}
            </div>
          </div>
        `;
            })
            .join("");
    }

    function updateSelection(id) {
        selectedNoteId = id;
        renderNotes();
    }

    async function saveNoteToServer(text) {
        try {
            // POST to base URL (e.g. /api/notes/)
            // Remove trailing slash if present for POST if API expects it, 
            // but usually Flask handles both. Let's use getNoteUrl() without ID which adds slash.
            // If your API fails with slash on POST, remove it.
            // Flask Blueprint url_prefix='/api/notes' + route '/' -> '/api/notes/'
            const response = await fetch(getNoteUrl(), {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                body: JSON.stringify({ text }),
            });
            const result = await handleResponse(response);
            return result.note;
        } catch (error) {
            console.error("Erro ao salvar nota:", error);
            throw error;
        }
    }

    async function updateNoteOnServer(noteId, text) {
        try {
            const response = await fetch(getNoteUrl(noteId), {
                method: "PUT",
                headers: {
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                body: JSON.stringify({ text }),
            });
            const result = await handleResponse(response);
            return result.note;
        } catch (error) {
            console.error("Erro ao atualizar nota:", error);
            throw error;
        }
    }

    async function deleteNoteFromServer(noteId) {
        try {
            const response = await fetch(getNoteUrl(noteId), {
                method: "DELETE",
                headers: {
                    "Accept": "application/json",
                },
            });
            await handleResponse(response);
            return true;
        } catch (error) {
            console.error("Erro ao excluir nota:", error);
            throw error;
        }
    }

    async function loadNotes() {
        try {
            const response = await fetch(getNoteUrl(), {
                headers: {
                    Accept: "application/json",
                },
            });

            // Handle non-200 responses manually if handleResponse is not used here
            // or use handleResponse but adapt it since structure might differ slightly
            const contentType = response.headers.get("content-type");
            if (!response.ok) {
                const text = await response.text();
                throw new Error(`Erro ${response.status}: ${text}`);
            }

            if (contentType && contentType.indexOf("application/json") !== -1) {
                const payload = await response.json();
                if (!payload || !payload.success) {
                    throw new Error(payload?.message || "Não foi possível recuperar as notas.");
                }
                notes = (payload.notes || []).map((note) => ({
                    ...note,
                    id: note.id ? String(note.id) : note.code || `tmp-${Date.now()}`,
                }));
            } else {
                throw new Error("Resposta inválida do servidor (não é JSON).");
            }

        } catch (error) {
            console.error("Não foi possível carregar as notas:", error);
            if (noteBoard) {
                noteBoard.innerHTML =
                    '<p class="empty-state">Erro ao carregar as notas. Atualize a página para tentar novamente.</p>';
            }
            return;
        }

        renderNotes();
    }

    if (noteForm) {
        noteForm.addEventListener("submit", async (event) => {
            event.preventDefault();
            const text = noteText.value.trim();
            if (!text) return;

            noteText.disabled = true;
            btnSaveNote.disabled = true;
            const originalBtnText = btnSaveNote.textContent;
            btnSaveNote.textContent = isEditing ? "Atualizando..." : "Salvando...";

            try {
                if (isEditing && editNoteId) {
                    const updatedNote = await updateNoteOnServer(editNoteId, text);
                    const index = notes.findIndex((n) => n.id === editNoteId);
                    if (index >= 0) {
                        notes[index] = { ...updatedNote, id: String(updatedNote.id) };
                    }
                    btnSaveNote.textContent = "✓ Atualizada!";
                    cancelEditMode();
                } else {
                    const savedNote = await saveNoteToServer(text);
                    notes.unshift({ ...savedNote, id: String(savedNote.id) });
                    noteText.value = "";
                    updateSelection(String(savedNote.id));
                    btnSaveNote.textContent = "✓ Salva!";
                }

                setTimeout(() => {
                    if (btnSaveNote) btnSaveNote.textContent = isEditing ? "Atualizar" : "Salvar";
                }, 2000);

                renderNotes();
            } catch (error) {
                alert(`Erro: ${error.message}`);
                btnSaveNote.textContent = originalBtnText;
            } finally {
                noteText.disabled = false;
                btnSaveNote.disabled = false;
                if (!isEditing) noteText.focus();
            }
        });
    }

    function cancelEditMode() {
        isEditing = false;
        editNoteId = null;
        noteText.value = "";
        if (btnSaveNote) btnSaveNote.textContent = "Salvar";
        if (btnCancelEdit) btnCancelEdit.style.display = "none";
    }

    if (btnCancelEdit) {
        btnCancelEdit.addEventListener("click", cancelEditMode);
    }

    if (noteBoard) {
        noteBoard.addEventListener("click", async (event) => {
            const row = event.target.closest(".note-row");
            if (!row) return;

            const id = row.dataset.id;
            const note = notes.find((n) => n.id === id);
            if (!note) return;

            const btnEdit = event.target.closest(".btn-edit-note");
            const btnDelete = event.target.closest(".btn-delete-note");

            if (btnEdit) {
                isEditing = true;
                editNoteId = id;
                noteText.value = note.text;
                if (btnSaveNote) btnSaveNote.textContent = "Atualizar";
                if (btnCancelEdit) btnCancelEdit.style.display = "block";
                noteText.focus();
                return;
            }

            if (btnDelete) {
                const confirmed = confirm(
                    `Tem certeza que deseja excluir a nota "${note.code || 'selecionada'}"?\n\nEsta ação não pode ser desfeita.`
                );

                if (!confirmed) return;

                const originalHtml = btnDelete.innerHTML;
                btnDelete.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
                btnDelete.disabled = true;

                try {
                    await deleteNoteFromServer(id);
                    const index = notes.findIndex((n) => n.id === id);
                    if (index >= 0) {
                        notes.splice(index, 1);
                    }
                    if (isEditing && editNoteId === id) {
                        cancelEditMode();
                    }
                    updateSelection(null);
                } catch (error) {
                    alert(`Erro ao excluir nota: ${error.message}`);
                    btnDelete.innerHTML = originalHtml;
                    btnDelete.disabled = false;
                }
                return;
            }

            // Clicked somewhere else (like the bottom part), open modal
            openNoteModal(note);
        });
    }

    loadNotes();
})();
