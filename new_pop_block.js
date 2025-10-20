  const popManager = document.querySelector('[data-pop-manager]');
  if (popManager) {
    const processCode = (popManager.dataset.processCode || '').trim();
    const activitiesEndpoint = popManager.dataset.activitiesEndpoint;
    const activityDetailTemplate = popManager.dataset.activityDetailTemplate || '';
    const entryCreateTemplate = popManager.dataset.entryCreateTemplate || '';
    const entryDetailTemplate = popManager.dataset.entryDetailTemplate || '';
    const listEl = popManager.querySelector('[data-pop-list]');
    const emptyEl = popManager.querySelector('[data-pop-empty]');
    const feedbackEl = popManager.querySelector('[data-pop-feedback]');
    const createForm = popManager.querySelector('[data-pop-create-form]');

    const escapeHtml = (value) => {
      if (value === null || value === undefined) {
        return '';
      }
      return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
    };

    const convertTextToHtml = (value) => escapeHtml(value || '').replace(/\n/g, '<br>');
    const formatActivityEndpoint = (activityId) => activityDetailTemplate.replace('{id}', activityId);
    const formatEntryCreateEndpoint = (activityId) => entryCreateTemplate.replace('{id}', activityId);
    const formatEntryDetailEndpoint = (activityId, entryId) => entryDetailTemplate
      .replace('{activity_id}', activityId)
      .replace('{entry_id}', entryId);

    const setPopFeedback = (message, variant = 'info') => {
      if (!feedbackEl) {
        return;
      }
      if (!message) {
        feedbackEl.hidden = true;
        return;
      }
      feedbackEl.textContent = message;
      feedbackEl.dataset.variant = variant;
      feedbackEl.hidden = false;
      clearTimeout(setPopFeedback.timer);
      setPopFeedback.timer = setTimeout(() => {
        feedbackEl.hidden = true;
      }, 3200);
    };

    const state = { activities: [] };

    const findActivityById = (activityId) => state.activities.find((item) => String(item.id) === String(activityId));
    const findEntryById = (activityId, entryId) => {
      const activity = findActivityById(activityId);
      if (!activity) {
        return null;
      }
      return (activity.entries || []).find((entry) => String(entry.id) === String(entryId)) || null;
    };

    const updatePreviewMessage = (previewEl, message) => {
      if (!previewEl) {
        return;
      }
      previewEl.innerHTML = `<span>${escapeHtml(message)}</span>`;
    };

    const updatePreviewFromEntry = (previewEl, entry, layoutDual) => {
      if (!previewEl) {
        return;
      }
      if (entry && entry.image_url) {
        previewEl.innerHTML = `<img src="${escapeHtml(entry.image_url)}" alt="Imagem da atividade">`;
      } else {
        updatePreviewMessage(previewEl, layoutDual ? 'Inclua uma imagem para este passo.' : 'Nenhuma imagem adicionada.');
      }
    };

    const updatePreviewWithFile = (previewEl, file) => {
      if (!previewEl || !file) {
        return;
      }
      const reader = new FileReader();
      reader.onload = () => {
        previewEl.innerHTML = `<img src="${reader.result}" alt="Imagem da atividade">`;
      };
      reader.readAsDataURL(file);
    };

    const enableClipboardPaste = (target, fileInput, previewEl) => {
      if (!target) {
        return;
      }
      target.addEventListener('paste', (event) => {
        const clipboard = event.clipboardData || window.clipboardData;
        if (!clipboard || !clipboard.items) {
          return;
        }
        for (const item of clipboard.items) {
          if (item.type && item.type.startsWith('image/')) {
            const blob = item.getAsFile();
            if (!blob) {
              continue;
            }
            const typeParts = blob.type.split('/');
            const extension = (typeParts[1] || 'png').split(';')[0];
            const file = new File([blob], `clipboard-${Date.now()}.${extension}`, { type: blob.type });
            if (typeof DataTransfer !== 'undefined' && fileInput) {
              const dataTransfer = new DataTransfer();
              dataTransfer.items.add(file);
              fileInput.files = dataTransfer.files;
            }
            updatePreviewWithFile(previewEl, file);
            const removeInput = fileInput ? fileInput.closest('form')?.querySelector('input[name="remove_image"]') : null;
            if (removeInput) {
              removeInput.value = '';
            }
            event.preventDefault();
            break;
          }
        }
      });
    };

    const setupEntryForm = (form, activity, entry) => {
      if (!form) {
        return;
      }
      const layout = activity.layout || 'single';
      const previewEl = form.querySelector('[data-image-preview]');
      const fileInput = form.querySelector('input[type="file"][name="image"]');
      const textInput = form.querySelector('textarea[name="text_content"]');
      const removeInput = form.querySelector('input[name="remove_image"]');
      const removeButton = form.querySelector('button[data-action="remove-image"]');

      if (entry) {
        if (textInput) {
          textInput.value = entry.text_content || '';
        }
        updatePreviewFromEntry(previewEl, entry, layout === 'dual');
        if (removeButton) {
          removeButton.disabled = !(entry && entry.image_url);
        }
        if (removeInput) {
          removeInput.value = '';
        }
        if (fileInput) {
          fileInput.value = '';
        }
        form.hidden = true;
      } else {
        updatePreviewMessage(previewEl, layout === 'dual' ? 'Adicione uma imagem para ilustrar o passo.' : 'Descreva a atividade com o máximo de detalhes.');
      }

      if (fileInput) {
        fileInput.addEventListener('change', () => {
          const file = fileInput.files && fileInput.files[0];
          if (!file) {
            return;
          }
          updatePreviewWithFile(previewEl, file);
          if (removeInput) {
            removeInput.value = '';
          }
          if (removeButton) {
            removeButton.disabled = false;
          }
        });
      }

      if (textInput) {
        enableClipboardPaste(textInput, fileInput, previewEl);
      }
    };

    const enterEditMode = (entryContainer) => {
      const form = entryContainer.querySelector('[data-entry-form]');
      const view = entryContainer.querySelector('[data-entry-view]');
      if (!form || !view) {
        return;
      }
      form.hidden = false;
      view.hidden = true;
      entryContainer.dataset.mode = 'edit';
    };

    const exitEditMode = (entryContainer, activityId, entryId) => {
      const form = entryContainer.querySelector('[data-entry-form]');
      const view = entryContainer.querySelector('[data-entry-view]');
      if (!form || !view) {
        return;
      }
      const activity = findActivityById(activityId);
      const entry = findEntryById(activityId, entryId);
      setupEntryForm(form, activity, entry);
      form.hidden = true;
      view.hidden = false;
      entryContainer.dataset.mode = 'view';
    };

    const buildEntryMarkup = (activity, entry) => {
      const layout = activity.layout || 'single';
      const hasImage = Boolean(entry.image_url);
      const imageSection = layout === 'dual'
        ? `<div class="entry-image-view">${hasImage ? `<img src="${escapeHtml(entry.image_url)}" alt="Imagem da atividade">` : '<span>Sem imagem</span>'}</div>`
        : (hasImage ? `<div class="entry-image-view">${`<img src="${escapeHtml(entry.image_url)}" alt="Imagem da atividade">`}</div>` : '');
      return `
        <article class="activity-entry" data-entry data-activity-id="${activity.id}" data-entry-id="${entry.id}" data-mode="view">
          <div class="activity-entry-view" data-entry-view>
            <div class="entry-body" data-layout="${layout}">
              ${imageSection}
              <div class="entry-text-view">${convertTextToHtml(entry.text_content || '')}</div>
            </div>
            <div class="activity-entry-controls">
              <button type="button" data-action="edit-entry">Editar</button>
              <button type="button" data-action="delete-entry">Excluir</button>
            </div>
          </div>
          <form class="activity-entry-form" data-entry-form data-activity-id="${activity.id}" data-entry-id="${entry.id}" hidden>
            <div class="${layout === 'dual' ? 'entry-preview dual' : 'entry-preview'}">
              <div class="entry-image-preview" data-image-preview></div>
              <div class="entry-text">
                <textarea name="text_content" placeholder="Detalhamento do passo">${escapeHtml(entry.text_content || '')}</textarea>
              </div>
            </div>
            <div class="entry-controls">
              <label>
                <span>Enviar imagem</span>
                <input type="file" name="image" accept="image/*" hidden />
              </label>
              <button type="button" data-action="remove-image" ${hasImage ? '' : 'disabled'}>Remover imagem</button>
              <button type="submit">Salvar</button>
              <button type="button" data-action="cancel-edit">Cancelar</button>
            </div>
            <input type="hidden" name="remove_image" value="" />
            <input type="hidden" name="order_index" value="${entry.order_index || ''}" />
            <small>Atualize o texto ou substitua a imagem conforme necessário.</small>
          </form>
        </article>`;
    };
...
