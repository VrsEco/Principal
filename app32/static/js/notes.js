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

    const noteToTaskForm = document.getElementById("noteToTaskForm");
    const noteToTaskCompany = document.getElementById("noteToTaskCompany");
    const noteToTaskProject = document.getElementById("noteToTaskProject");
    const noteToTaskResponsible = document.getElementById("noteToTaskResponsible");
    const noteToTaskDueDate = document.getElementById("noteToTaskDueDate");
    const noteToTaskWhat = document.getElementById("noteToTaskWhat");
    const noteToTaskPreview = document.getElementById("noteToTaskPreview");
    const noteToTaskNoteId = document.getElementById("noteToTaskNoteId");
    const noteToTaskSubmitButton = document.getElementById("noteToTaskSubmitButton");
    let noteToTaskModalInstance = null;

    const portalCompaniesById = { ...(window.portalCompaniesById || {}) };
    const portalCompanyIds = Array.isArray(window.portalCompanyIds) ? [...window.portalCompanyIds] : [];
    const portalProjects = [];
    const portalEmployeesByCompany = new Map();

    if (document.getElementById("noteDetailsModal") && window.Modal) {
        noteDetailsModalInstance = new Modal("noteDetailsModal", {
            animation: true,
            backdrop: true,
            closeOnBackdrop: true,
            closeOnEscape: true,
        });
    }

    if (document.getElementById("noteToTaskModal") && window.Modal) {
        noteToTaskModalInstance = new Modal("noteToTaskModal", {
            animation: true,
            backdrop: true,
            closeOnBackdrop: true,
            closeOnEscape: true,
        });
    }

    const notesEndpoint = document.body.dataset.notesEndpoint || "/api/notes/";

    let notes = [];
    let selectedNoteId = null;

    function getNoteUrl(id) {
        const base = notesEndpoint.endsWith("/") ? notesEndpoint : `${notesEndpoint}/`;
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
        }

        const text = await response.text();
        console.error("Resposta não-JSON do servidor:", text);
        throw new Error(`Erro do servidor (${response.status}). Verifique o console.`);
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

    function getTodayIsoDate() {
        const now = new Date();
        const year = now.getFullYear();
        const month = String(now.getMonth() + 1).padStart(2, "0");
        const day = String(now.getDate()).padStart(2, "0");
        return `${year}-${month}-${day}`;
    }

    function buildTaskTitleFromNote(noteValue) {
        const firstLine = String(noteValue || "")
            .split(/\r?\n/)
            .map((line) => line.trim())
            .find(Boolean);

        if (!firstLine) {
            return "Nova atividade a partir da nota";
        }

        return firstLine.length > 120 ? `${firstLine.slice(0, 117)}...` : firstLine;
    }

    function hydrateCompaniesFromDom() {
        const companyCards = document.querySelectorAll("[data-portal-company-id]");
        companyCards.forEach((card) => {
            const companyId = String(card.dataset.portalCompanyId || "").trim();
            const companyLabel = String(card.dataset.portalCompanyLabel || "").trim();

            if (!companyId) {
                return;
            }

            if (!portalCompanyIds.includes(companyId)) {
                portalCompanyIds.push(companyId);
            }

            if (companyLabel && !portalCompaniesById[companyId]) {
                portalCompaniesById[companyId] = companyLabel;
            }
        });
    }

    function resetResponsibleOptions() {
        if (!noteToTaskResponsible) {
            return;
        }
        noteToTaskResponsible.innerHTML = '<option value="">Selecione um responsável</option>';
        noteToTaskResponsible.disabled = true;
    }

    function resetProjectOptions() {
        if (!noteToTaskProject) {
            return;
        }
        noteToTaskProject.innerHTML = '<option value="">Selecione um projeto</option>';
        noteToTaskProject.disabled = true;
    }

    function populateCompanyOptions() {
        if (!noteToTaskCompany) {
            return;
        }

        noteToTaskCompany.innerHTML = '<option value="">Selecione uma empresa</option>';
        portalCompanyIds.forEach((companyId) => {
            const option = document.createElement("option");
            option.value = String(companyId);
            option.textContent = portalCompaniesById[String(companyId)] || `Empresa ${companyId}`;
            noteToTaskCompany.appendChild(option);
        });
    }

    function populateProjectOptions(companyId) {
        if (!noteToTaskProject) {
            return;
        }

        resetProjectOptions();
        const filteredProjects = portalProjects
            .filter((project) => String(project.company_id) === String(companyId))
            .sort((a, b) => {
                const labelA = `${a.code || ""} ${a.name || a.title || ""}`;
                const labelB = `${b.code || ""} ${b.name || b.title || ""}`;
                return labelA.localeCompare(labelB, "pt-BR");
            });

        filteredProjects.forEach((project) => {
            const option = document.createElement("option");
            option.value = String(project.id);
            option.dataset.companyId = String(project.company_id || "");
            option.textContent = `${project.code ? `${project.code} • ` : ""}${project.name || project.title}`;
            noteToTaskProject.appendChild(option);
        });

        noteToTaskProject.disabled = filteredProjects.length === 0;
    }

    async function loadPortalProjects() {
        if (!portalCompanyIds.length) {
            return;
        }

        const results = await Promise.allSettled(
            portalCompanyIds.map(async (companyId) => {
                const response = await fetch(`/api/projects?company_id=${companyId}&show_inactive=true`, {
                    headers: { Accept: "application/json" },
                });

                if (!response.ok) {
                    throw new Error(`Falha ao carregar projetos da empresa ${companyId}.`);
                }

                const payload = await response.json();
                const list = (Array.isArray(payload) ? payload : []).filter((project) => !["completed", "cancelled", "archived"].includes(project.status));
                return list.map((project) => ({
                    ...project,
                    company_id: project.company_id || companyId,
                    company_name: portalCompaniesById[String(project.company_id || companyId)] || "",
                }));
            })
        );

        results.forEach((result) => {
            if (result.status !== "fulfilled") {
                console.warn(result.reason);
                return;
            }

            result.value.forEach((project) => {
                if (!portalProjects.some((item) => String(item.id) === String(project.id))) {
                    portalProjects.push(project);
                }
            });
        });

        populateCompanyOptions();
    }

    async function loadEmployeesForCompany(companyId) {
        if (!companyId) {
            resetResponsibleOptions();
            return;
        }

        if (!portalEmployeesByCompany.has(companyId)) {
            const response = await fetch(`/api/companies/${companyId}/employees`, {
                headers: { Accept: "application/json" },
            });

            if (!response.ok) {
                throw new Error("Não foi possível carregar os responsáveis do projeto.");
            }

            const payload = await response.json();
            portalEmployeesByCompany.set(companyId, payload.employees || []);
        }

        const employees = portalEmployeesByCompany.get(companyId) || [];
        resetResponsibleOptions();

        employees.forEach((employee) => {
            const option = document.createElement("option");
            option.value = String(employee.id);
            option.textContent = employee.name;
            noteToTaskResponsible.appendChild(option);
        });
        noteToTaskResponsible.disabled = employees.length === 0;
    }

    async function createProjectTaskFromPortal(payload) {
        const response = await fetch(`/api/projects/${payload.project_id}/tasks?company_id=${payload.company_id}`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                Accept: "application/json",
            },
            body: JSON.stringify({
                what: payload.what,
                employee_id: payload.employee_id,
                due_date: payload.due_date,
                how: payload.how,
                status: "planned",
                stage: "inbox",
                priority: "normal",
            }),
        });

        const contentType = response.headers.get("content-type") || "";
        const result = contentType.includes("application/json") ? await response.json() : null;

        if (!response.ok) {
            throw new Error(result?.message || result?.error || "Não foi possível criar a atividade.");
        }

        return result;
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

    async function openNoteToTaskModal(note) {
        if (!noteToTaskModalInstance || !noteToTaskForm) {
            return;
        }

        if (!portalProjects.length) {
            await loadPortalProjects();
        }

        if (!portalCompanyIds.length) {
            alert("Nenhuma empresa vinculada ao usuário para transformar a nota em atividade.");
            return;
        }

        noteToTaskForm.reset();
        populateCompanyOptions();
        resetProjectOptions();
        resetResponsibleOptions();
        noteToTaskNoteId.value = note.id || "";
        noteToTaskWhat.value = buildTaskTitleFromNote(note.text);
        noteToTaskPreview.value = note.text || "";
        noteToTaskDueDate.value = getTodayIsoDate();
        noteToTaskModalInstance.open();
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
                <button type="button" class="btn-icon btn-convert-note" title="Transformar em atividade" style="background: none; border: none; cursor: pointer; color: #0f766e; padding: 4px;"><i class="fas fa-list-check"></i></button>
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
            const response = await fetch(getNoteUrl(), {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Accept: "application/json",
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
                    Accept: "application/json",
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
                    Accept: "application/json",
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
            const btnConvert = event.target.closest(".btn-convert-note");

            if (btnConvert) {
                try {
                    await openNoteToTaskModal(note);
                } catch (error) {
                    console.error("Erro ao preparar formulário de atividade:", error);
                    alert(error.message || "Não foi possível abrir o formulário de atividade.");
                }
                return;
            }

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
                    `Tem certeza que deseja excluir a nota "${note.code || "selecionada"}"?\n\nEsta ação não pode ser desfeita.`
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

            openNoteModal(note);
        });
    }

    if (noteToTaskCompany) {
        noteToTaskCompany.addEventListener("change", async (event) => {
            const companyId = event.target.value;
            populateProjectOptions(companyId);
            resetResponsibleOptions();

            try {
                await loadEmployeesForCompany(companyId);
                if (companyId && noteToTaskProject.disabled) {
                    alert("Nenhum projeto ativo disponível para a empresa selecionada.");
                }
            } catch (error) {
                console.error("Erro ao carregar responsáveis:", error);
                resetResponsibleOptions();
                alert(error.message || "Não foi possível carregar os responsáveis.");
            }
        });
    }

    if (noteToTaskForm) {
        noteToTaskForm.addEventListener("submit", async (event) => {
            event.preventDefault();

            const companyId = noteToTaskCompany.value;
            const projectId = noteToTaskProject.value;

            if (!projectId || !companyId) {
                alert("Selecione uma empresa e um projeto válidos.");
                return;
            }

            const payload = {
                source: "portal_note",
                note_id: noteToTaskNoteId.value || null,
                project_id: projectId,
                company_id: companyId,
                what: noteToTaskWhat.value.trim(),
                employee_id: noteToTaskResponsible.value || "",
                due_date: noteToTaskDueDate.value || "",
                how: noteToTaskPreview.value || "",
            };

            if (!payload.what) {
                alert("Informe o título da atividade.");
                noteToTaskWhat.focus();
                return;
            }

            if (!payload.employee_id) {
                alert("Selecione um responsável.");
                noteToTaskResponsible.focus();
                return;
            }

            if (!payload.due_date) {
                alert("Informe o prazo da atividade.");
                noteToTaskDueDate.focus();
                return;
            }

            const originalButtonText = noteToTaskSubmitButton ? noteToTaskSubmitButton.textContent : "";
            if (noteToTaskSubmitButton) {
                noteToTaskSubmitButton.disabled = true;
                noteToTaskSubmitButton.textContent = "Criando...";
            }

            let taskCreated = false;
            try {
                await createProjectTaskFromPortal(payload);
                taskCreated = true;

                if (payload.note_id) {
                    await deleteNoteFromServer(payload.note_id);
                    notes = notes.filter((note) => String(note.id) !== String(payload.note_id));
                    if (isEditing && String(editNoteId) === String(payload.note_id)) {
                        cancelEditMode();
                    }
                    updateSelection(null);
                }

                renderNotes();
                noteToTaskModalInstance?.close();
                alert("Atividade criada com sucesso e nota removida.");
            } catch (error) {
                console.error("Erro ao criar atividade a partir da nota:", error);
                if (taskCreated) {
                    alert(`Atividade criada, mas a nota não pôde ser removida automaticamente: ${error.message}`);
                } else {
                    alert(error.message || "Não foi possível criar a atividade.");
                }
            } finally {
                if (noteToTaskSubmitButton) {
                    noteToTaskSubmitButton.disabled = false;
                    noteToTaskSubmitButton.textContent = originalButtonText || "Criar Atividade";
                }
            }
        });
    }

    hydrateCompaniesFromDom();

    loadPortalProjects().catch((error) => {
        console.warn("Não foi possível pré-carregar os projetos do portal:", error);
    });

    loadNotes();
})();
