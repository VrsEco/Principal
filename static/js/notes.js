// Notes functionality
(function () {
    const noteBoard = document.getElementById("noteBoard");
    const noteForm = document.getElementById("noteForm");
    const noteText = document.getElementById("noteText");
    const actionCreate = document.getElementById("action-create");
    const actionEdit = document.getElementById("action-edit");
    const actionDelete = document.getElementById("action-delete");

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
          <div class="note-row ${selectedNoteId === noteId ? "selected" : ""}" data-id="${noteId}" draggable="true">
            <div class="note-row-top">
              <label class="note-select">
                <input type="checkbox" ${selectedNoteId === noteId ? "checked" : ""} />
              </label>
              <span class="note-row-meta">${metaText}</span>
            </div>
            <div class="note-row-bottom">
              <p class="note-row-text">${note.text}</p>
              ${locationText ? `<span class="note-row-location">${locationText}</span>` : ""}
            </div>
          </div>
        `;
            })
            .join("");
    }

    function updateSelection(id) {
        selectedNoteId = id;
        if (actionCreate) actionCreate.disabled = !id;
        if (actionEdit) actionEdit.disabled = !id;
        if (actionDelete) actionDelete.disabled = !id;
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

            // Disable form while saving
            noteText.disabled = true;
            const submitBtn = noteForm.querySelector('button[type="submit"]');
            const originalBtnText = submitBtn.textContent;
            submitBtn.textContent = "Salvando...";
            submitBtn.disabled = true;

            try {
                const savedNote = await saveNoteToServer(text);

                // Add to local list
                notes.unshift({
                    ...savedNote,
                    id: String(savedNote.id),
                });

                noteText.value = "";
                updateSelection(String(savedNote.id));

                // Show success feedback
                submitBtn.textContent = "✓ Salva!";
                setTimeout(() => {
                    submitBtn.textContent = originalBtnText;
                }, 2000);
            } catch (error) {
                alert(`Erro ao salvar nota: ${error.message}`);
                submitBtn.textContent = originalBtnText;
            } finally {
                noteText.disabled = false;
                submitBtn.disabled = false;
                noteText.focus();
            }
        });
    }

    if (noteBoard) {
        noteBoard.addEventListener("click", (event) => {
            const row = event.target.closest(".note-row");
            if (!row) return;
            const id = row.dataset.id;
            updateSelection(selectedNoteId === id ? null : id);
        });
    }

    if (actionEdit) {
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
    }

    if (actionDelete) {
        actionDelete.addEventListener("click", async () => {
            if (!selectedNoteId) return;

            const note = notes.find((n) => n.id === selectedNoteId);
            if (!note) return;

            const confirmed = confirm(
                `Tem certeza que deseja excluir a nota "${note.code}"?\n\nEsta ação não pode ser desfeita.`
            );

            if (!confirmed) return;

            // Disable button while deleting
            actionDelete.disabled = true;
            const originalBtnText = actionDelete.textContent;
            actionDelete.textContent = "Excluindo...";

            try {
                await deleteNoteFromServer(selectedNoteId);

                // Remove from local list
                const index = notes.findIndex((n) => n.id === selectedNoteId);
                if (index >= 0) {
                    notes.splice(index, 1);
                }

                updateSelection(null);

                // Show success feedback
                actionDelete.textContent = "✓ Excluída!";
                setTimeout(() => {
                    actionDelete.textContent = originalBtnText;
                }, 2000);
            } catch (error) {
                alert(`Erro ao excluir nota: ${error.message}`);
                actionDelete.textContent = originalBtnText;
                actionDelete.disabled = false;
            }
        });
    }

    if (actionCreate) {
        actionCreate.addEventListener("click", () => {
            if (!selectedNoteId) return;
            alert(`Criar atividade a partir da nota selecionada (${selectedNoteId}).`);
        });
    }

    loadNotes();
})();
