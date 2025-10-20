(function(){
  const companyId = parseInt(document.querySelector('[data-company-id]')?.getAttribute('data-company-id') || window.location.pathname.match(/\/company\/(\d+)/)?.[1], 10);
  
  // Tab management
  document.querySelectorAll('[data-tab]').forEach(btn => {
    btn.addEventListener('click', () => {
      const tab = btn.getAttribute('data-tab');
      document.querySelectorAll('[data-panel]').forEach(p => p.style.display = p.getAttribute('data-panel') === tab ? 'block' : 'none');
      document.querySelectorAll('[data-tab]').forEach(b => b.className = b === btn ? 'button' : 'button button-ghost');
    });
  });

  // Areas CRUD
  const areaForm = document.getElementById('areaForm');
  const areasList = document.getElementById('areasList');
  
  async function loadAreas(){
    const res = await fetch(`/api/companies/${companyId}/process-areas`);
    const json = await res.json();
    if(!(json && json.success)) return;
    
    areasList.innerHTML = '';
    const list = json.data || [];
    
    if(!list.length){
      areasList.innerHTML = '<div class="surface-card" style="padding:24px;text-align:center;"><p class="text-muted" style="margin:0;">Nenhuma área cadastrada. Use o formulário acima para criar a primeira área.</p></div>';
      return;
    }
    
    list.forEach(a => {
      const div = document.createElement('div');
      div.style.cssText = 'padding:12px 16px;border:1px solid rgba(148,163,184,.2);border-radius:8px;margin-bottom:8px;display:flex;justify-content:space-between;align-items:center;background:#ffffff;';
      
      const colorDot = a.color ? `<span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:${a.color};margin-right:8px;vertical-align:middle;"></span>` : '';
      
      // Formato padrão: CÓDIGO - NOME
      const displayText = a.code ? `${a.code} - ${a.name.toUpperCase()}` : a.name;
      
      div.innerHTML = `
        <div style="flex:1;">
          <div style="display:flex;align-items:center;margin-bottom:4px;">
            ${colorDot}<strong style="color:#000000;font-size:15px;">${displayText}</strong>
          </div>
          ${a.description ? `<div style="color:var(--color-muted);font-size:12px;margin-left:20px;">${a.description}</div>` : ''}
        </div>
        <div style="display:flex;gap:6px;">
          <button data-edit-area="${a.id}" class="button button-ghost" style="font-size:12px;padding:6px 12px;">✏️ Editar</button>
          <button data-del-area="${a.id}" class="button button-ghost" style="font-size:12px;padding:6px 12px;color:var(--color-danger);">🗑️ Excluir</button>
        </div>
      `;
      areasList.appendChild(div);
    });
    
    // Populate area selects (in macro form)
    const macroAreaSelect = document.getElementById('macroAreaSelect');
    if(macroAreaSelect){
      const currentValue = macroAreaSelect.value;
      // Formato padrão: CÓDIGO - NOME
      macroAreaSelect.innerHTML = '<option value="">Selecione uma área</option>' + list.map(a => {
        const displayText = a.code ? `${a.code} - ${a.name.toUpperCase()}` : a.name;
        return `<option value="${a.id}">${displayText}</option>`;
      }).join('');
      if(currentValue){
        macroAreaSelect.value = currentValue;
      }
    }
  }
  
  if(areaForm){
    areaForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const code = areaForm.code.value.trim();
      const name = areaForm.name.value.trim();
      
      if(!code || Number(code) < 1){
        window.showMessage('Informe um código válido (número maior que 0)','error');
        return;
      }
      if(!name){
        window.showMessage('Informe o nome da área','error');
        return;
      }
      
      const payload = { 
        code: code, 
        name: name, 
        description: areaForm.description.value.trim(), 
        color: areaForm.color.value, 
        order_index: Number(code) || 0 
      };
      
      const id = areaForm.id.value;
      const url = id ? `/api/companies/${companyId}/process-areas/${id}` : `/api/companies/${companyId}/process-areas`;
      const method = id ? 'PUT' : 'POST';
      
      console.log('Salvando área:', { id, url, method, payload });
      
      const res = await fetch(url, { method, headers: {'Content-Type':'application/json'}, body: JSON.stringify(payload) });
      const json = await res.json();
      
      console.log('Resposta da API:', json);
      
      if(json && json.success){ 
        window.showMessage('Área salva com sucesso','success'); 
        areaForm.reset(); 
        areaForm.color.value = '#a78bfa'; // Reset color to default
        loadAreas(); 
        
        // Reload macros to update area names in dropdowns
        if(window.loadMacros) window.loadMacros();
        
        // Reload process map visual
        if(window.renderProcessMap) window.renderProcessMap();
      }
      else { 
        console.error('Erro ao salvar:', json);
        window.showMessage(json?.error || 'Falha ao salvar área','error'); 
      }
    });
  }
  
  if(areasList){
    areasList.addEventListener('click', async (e) => {
      const editBtn = e.target.closest('[data-edit-area]');
      const delBtn = e.target.closest('[data-del-area]');
      if(editBtn){
        const id = editBtn.getAttribute('data-edit-area');
        const res = await fetch(`/api/companies/${companyId}/process-areas`);
        const json = await res.json();
        const a = (json.data||[]).find(x => x.id == id);
        if(a){
          areaForm.id.value = a.id;
          
          // Extrair apenas a sequência do código completo (ex: "AO.C.1" -> "1")
          let sequenceNumber = '';
          if(a.code){
            const parts = a.code.split('.');
            sequenceNumber = parts[parts.length - 1] || ''; // Pega a última parte
          }
          areaForm.code.value = sequenceNumber;
          
          areaForm.name.value = a.name||'';
          areaForm.description.value = a.description||'';
          areaForm.color.value = a.color||'#a78bfa';
          
          // Scroll to form
          areaForm.scrollIntoView({ behavior: 'smooth', block: 'start' });
          areaForm.code.focus();
        }
      } else if(delBtn){
        if(!confirm('Tem certeza que deseja excluir esta área? Esta ação não pode ser desfeita.\n\nATENÇÃO: Todos os macroprocessos vinculados a esta área serão afetados.')) return;
        const id = delBtn.getAttribute('data-del-area');
        const res = await fetch(`/api/companies/${companyId}/process-areas/${id}`, {method:'DELETE'});
        const json = await res.json();
        if(json && json.success){ 
          window.showMessage('Área excluída com sucesso','success'); 
          loadAreas();
          
          // Reload macros and map
          if(window.loadMacros) window.loadMacros();
          if(window.renderProcessMap) window.renderProcessMap();
        }
        else { window.showMessage(json?.error || 'Falha ao excluir área','error'); }
      }
    });
  }

  // Load Employees (Collaborators)
  const processResponsibleSelect = document.getElementById('processResponsibleSelect');
  
  async function loadEmployees(){
    if(!processResponsibleSelect) return;
    
    try {
      const res = await fetch(`/api/companies/${companyId}/employees`);
      const json = await res.json();
      
      if(json && json.success){
        const employees = json.employees || [];
        const currentValue = processResponsibleSelect.value;
        
        // Build options: empty option + all employees
        let options = '<option value="">Selecione um colaborador</option>';
        employees.forEach(emp => {
          if(emp.status === 'active' || emp.status === null || emp.status === undefined){
            options += `<option value="${escapeHtml(emp.name)}">${escapeHtml(emp.name)}</option>`;
          }
        });
        
        processResponsibleSelect.innerHTML = options;
        
        // Restore previous value if exists
        if(currentValue){
          processResponsibleSelect.value = currentValue;
        }
      }
    } catch(err){
      console.error('Erro ao carregar colaboradores:', err);
    }
  }

// Macros CRUD
  const macroForm = document.getElementById('macroForm');
  const macrosContainer = document.getElementById('macrosContainer');
  const macroAreaSelect = document.getElementById('macroAreaSelect');
  const processMacroSelect = document.getElementById('processMacroSelect');
  
  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }
  
  async function loadMacros(){
    const res = await fetch(`/api/companies/${companyId}/macro-processes`);
    const json = await res.json();
    if(!(json && json.success)) return;

    const list = json.data || [];
    
    // Update macrosContainer (inline list)
    if(macrosContainer){
      if(!list.length){
        macrosContainer.innerHTML = '<div class="surface-card" style="padding:24px;text-align:center;"><p class="text-muted" style="margin:0;">Nenhum macroprocesso cadastrado. Use o formulário acima para criar o primeiro macroprocesso.</p></div>';
      } else {
        macrosContainer.innerHTML = '';
        list.forEach(m => {
          const div = document.createElement('div');
          div.style.cssText = 'padding:12px 16px;border:1px solid rgba(148,163,184,.2);border-radius:8px;margin-bottom:8px;display:flex;justify-content:space-between;align-items:flex-start;background:#ffffff;';
          
          const areaColor = m.area_color || '#a78bfa';
          const areaTag = m.area_name ? `<span style="display:inline-block;padding:2px 8px;background:${areaColor}15;color:${areaColor};border:1px solid ${areaColor}40;border-radius:6px;font-size:10px;font-weight:600;margin-right:8px;">${escapeHtml(m.area_name.toUpperCase())}</span>` : '';
          
          // Formato padrão: CÓDIGO - NOME
          const displayText = m.code ? `${escapeHtml(m.code)} - ${escapeHtml(m.name.toUpperCase())}` : escapeHtml(m.name);
          
          const owner = m.owner ? `<div style="color:#1e3a8a;font-size:12px;margin-top:4px;">👤 Dono: <span style=\"color:#1e3a8a;font-weight:600;\">${escapeHtml(m.owner)}</span></div>` : '';
          const description = m.description ? `<div style="color:var(--color-muted);font-size:12px;margin-top:4px;">${escapeHtml(m.description)}</div>` : '';
          
          div.innerHTML = `
            <div style="flex:1;">
              <div style="display:flex;align-items:center;margin-bottom:4px;">
                ${areaTag}<strong style="color:#000000;font-size:15px;">${displayText}</strong>
              </div>
              ${owner}${description}
            </div>
            <div style="display:flex;gap:6px;">
              <button data-edit-macro="${m.id}" class="button button-ghost" style="font-size:12px;padding:6px 12px;">✏️ Editar</button>
              <button data-del-macro="${m.id}" class="button button-ghost" style="font-size:12px;padding:6px 12px;color:var(--color-danger);">🗑️ Excluir</button>
            </div>
          `;
          macrosContainer.appendChild(div);
        });
        
        // Mostrar indicador de scroll se houver muitos itens
        const scrollIndicator = document.getElementById('scrollIndicator');
        if(scrollIndicator && list.length > 3){
          scrollIndicator.style.display = 'block';
        } else if(scrollIndicator){
          scrollIndicator.style.display = 'none';
        }
      }
    }
    
    // Update processMacroSelect (process form)
    if(processMacroSelect){
      const currentValue = processMacroSelect.value;
      // Formato padrão: CÓDIGO - NOME
      processMacroSelect.innerHTML = '<option value="">Selecione</option>' + list.map(m => {
        const displayText = m.code ? `${m.code} - ${m.name.toUpperCase()}` : m.name;
        return `<option value="${m.id}">${displayText}</option>`;
      }).join('');
      if(currentValue){
        processMacroSelect.value = currentValue;
      }
    }
  }
  
  if(macroForm){
    macroForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const areaId = macroForm.area_id.value.trim();
      const name = macroForm.name.value.trim();
      const owner = macroForm.owner.value.trim();
      const orderIndex = macroForm.order_index.value.trim();
      const description = macroForm.description.value.trim();
      
      if(!areaId){
        window.showMessage('Selecione uma área','error');
        return;
      }
      if(!name){
        window.showMessage('Informe o nome do macroprocesso','error');
        return;
      }
      if(!owner){
        window.showMessage('Informe o dono do processo','error');
        return;
      }
      if(!orderIndex || Number(orderIndex) < 1){
        window.showMessage('Informe uma sequência válida (número maior que 0)','error');
        return;
      }
      
      const payload = { 
        area_id: Number(areaId),
        name: name,
        owner: owner,
        description: description,
        order_index: Number(orderIndex)
      };
      
      const id = macroForm.id.value;
      const url = id ? `/api/companies/${companyId}/macro-processes/${id}` : `/api/companies/${companyId}/macro-processes`;
      const method = id ? 'PUT' : 'POST';
      const res = await fetch(url, { method, headers: {'Content-Type':'application/json'}, body: JSON.stringify(payload) });
      const json = await res.json();
      if(json && json.success){ 
        window.showMessage('Macroprocesso salvo com sucesso','success'); 
        macroForm.reset(); 
        loadMacros();
        
        // Reload process map visual
        if(window.renderProcessMap) window.renderProcessMap();
      }
      else { window.showMessage(json?.error || 'Falha ao salvar macroprocesso','error'); }
    });
  }
  
  if(macrosContainer){
    macrosContainer.addEventListener('click', async (e) => {
      const editBtn = e.target.closest('[data-edit-macro]');
      const delBtn = e.target.closest('[data-del-macro]');
      if(editBtn){
        const id = editBtn.getAttribute('data-edit-macro');
        const res = await fetch(`/api/companies/${companyId}/macro-processes`);
        const json = await res.json();
        const m = (json.data||[]).find(x => x.id == id);
        if(m){
          macroForm.id.value = m.id;
          macroForm.area_id.value = m.area_id||'';
          macroForm.name.value = m.name||'';
          macroForm.owner.value = m.owner||'';
          macroForm.order_index.value = m.order_index||'';
          macroForm.description.value = m.description||'';
          
          // Scroll to form
          macroForm.scrollIntoView({ behavior: 'smooth', block: 'start' });
          macroForm.area_id.focus();
        }
      } else if(delBtn){
        if(!confirm('Tem certeza que deseja excluir este macroprocesso? Esta ação não pode ser desfeita.\n\nATENÇÃO: Todos os processos vinculados a este macroprocesso serão afetados.')) return;
        const id = delBtn.getAttribute('data-del-macro');
        const res = await fetch(`/api/companies/${companyId}/macro-processes/${id}`, {method:'DELETE'});
        const json = await res.json();
        if(json && json.success){ 
          window.showMessage('Macroprocesso excluído com sucesso','success'); 
          loadMacros();
          
          // Reload process map visual
          if(window.renderProcessMap) window.renderProcessMap();
        }
        else { window.showMessage(json?.error || 'Falha ao excluir macroprocesso','error'); }
      }
    });
  }

  // Processes CRUD
  const processForm = document.getElementById('processForm');
  const processesList = document.getElementById('processesList');
  const processCodePreview = document.getElementById('processCodePreview');
  const filterProcessQuery = document.getElementById('filterProcessQuery');
  const filterProcessMacro = document.getElementById('filterProcessMacro');
  const filterProcessResponsible = document.getElementById('filterProcessResponsible');
  const filterProcessPerformance = document.getElementById('filterProcessPerformance');
  const btnClearProcessFilters = document.getElementById('btnClearProcessFilters');
  const toggleProcessFilters = document.getElementById('toggleProcessFilters');
  const processFiltersSection = document.getElementById('processFilters');
  const FILTER_STORAGE_KEY = `grv:processFilters:${companyId}`;
  const FILTER_COLLAPSE_KEY = `grv:processFilters:collapsed:${companyId}`;
  const LAST_MACRO_USED_KEY = `grv:lastMacroUsed:${companyId}`;
  let allProcessesCache = [];
  let macroById = {};
  
  // Atualizar preview do código quando selecionar macroprocesso
  if(processMacroSelect && processCodePreview){
    processMacroSelect.addEventListener('change', () => {
      const selectedOption = processMacroSelect.options[processMacroSelect.selectedIndex];
      if(selectedOption && selectedOption.value){
        const macroText = selectedOption.textContent;
        // Extrair código do macro (ex: "AO.C.1.1 - PLANEJAMENTO" -> "AO.C.1.1")
        const macroCode = macroText.split(' - ')[0];
        processCodePreview.textContent = `${macroCode}.? (ex: ${macroCode}.1)`;
      } else {
        processCodePreview.textContent = 'Selecione um macroprocesso';
      }
    });
  }
  
  function loadSavedProcessFilters(){
    try {
      const saved = JSON.parse(localStorage.getItem(FILTER_STORAGE_KEY) || '{}');
      if(filterProcessQuery) filterProcessQuery.value = saved.query || '';
      if(filterProcessMacro) filterProcessMacro.value = saved.macro_id || '';
      if(filterProcessResponsible) filterProcessResponsible.value = saved.responsible || '';
      if(filterProcessPerformance) filterProcessPerformance.value = saved.performance || '';
    } catch(_e) {}
  }

  function saveProcessFilters(){
    const payload = {
      query: filterProcessQuery ? filterProcessQuery.value.trim() : '',
      macro_id: filterProcessMacro ? filterProcessMacro.value : '',
      responsible: filterProcessResponsible ? filterProcessResponsible.value : '',
      performance: filterProcessPerformance ? filterProcessPerformance.value : ''
    };
    try { localStorage.setItem(FILTER_STORAGE_KEY, JSON.stringify(payload)); } catch(_e) {}
  }

  function applyProcessFilters(){
    let list = allProcessesCache.slice(0);
    const q = (filterProcessQuery ? filterProcessQuery.value.trim().toLowerCase() : '');
    const macroId = filterProcessMacro ? filterProcessMacro.value : '';
    const responsible = filterProcessResponsible ? filterProcessResponsible.value : '';
    const performance = filterProcessPerformance ? filterProcessPerformance.value : '';

    if(q){
      list = list.filter(p => (p.code||'').toLowerCase().includes(q) || (p.name||'').toLowerCase().includes(q));
    }
    if(macroId){
      list = list.filter(p => String(p.macro_id||'') === String(macroId));
    }
    if(responsible){
      list = list.filter(p => (p.responsible||'') === responsible);
    }
    if(performance){
      list = list.filter(p => (p.performance_level||'') === performance);
    }

    // Garantir ordenação por código (fallback caso backend mude)
    list.sort((a,b) => String(a.code||'').localeCompare(String(b.code||'')) || (a.order_index||0) - (b.order_index||0) || String(a.name||'').localeCompare(String(b.name||'')));

    // Render
    if(!list.length){
      processesList.innerHTML = '<div class="surface-card" style="padding:24px;text-align:center;"><p class="text-muted" style="margin:0;">Nenhum processo encontrado com os filtros aplicados.</p></div>';
      return;
    }

    processesList.innerHTML = '';
    list.forEach(p => {
      const div = document.createElement('div');
      div.style.cssText = 'padding:12px 16px;border:1px solid rgba(148,163,184,.2);border-radius:8px;margin-bottom:8px;display:flex;justify-content:space-between;align-items:flex-start;background:#ffffff;color:#1e3a8a;';
      const displayText = p.code ? `${escapeHtml(p.code)} - ${escapeHtml(p.name.toUpperCase())}` : escapeHtml(p.name);
      let macroTag = '';
      const macro = p.macro_id ? macroById[p.macro_id] : null;
      if(macro){
        const areaColor = macro.area_color || '#a78bfa';
        const macroDisplay = macro.code ? `${escapeHtml(macro.code)} - ${escapeHtml((macro.name||'').toUpperCase())}` : escapeHtml(macro.name||'');
        macroTag = `<span style="display:inline-block;padding:2px 8px;background:${areaColor}15;color:${areaColor};border:1px solid ${areaColor}40;border-radius:6px;font-size:10px;font-weight:600;margin-right:8px;">${macroDisplay}</span>`;
      }
      const responsibleHtml = p.responsible ? `<div style="color:#1e3a8a;font-size:12px;margin-top:4px;">👤 Responsável: <span style=\"color:#1e3a8a;font-weight:600;\">${escapeHtml(p.responsible)}</span></div>` : '';
      const description = p.description ? `<div style="color:#1e3a8a;font-size:12px;margin-top:4px;">${escapeHtml(p.description)}</div>` : '';
      div.innerHTML = `
        <div style="flex:1;">
          <div style="display:flex;align-items:center;margin-bottom:4px;">
            ${macroTag}<strong style="color:#000000;font-size:15px;">${displayText}</strong>
          </div>
          ${responsibleHtml}
          ${description}
        </div>
        <div style="display:flex;gap:6px;">
          <button data-edit-proc="${p.id}" class="button button-ghost" style="font-size:12px;padding:6px 12px;">✏️ Editar</button>
          <button data-del-proc="${p.id}" class="button button-ghost" style="font-size:12px;padding:6px 12px;color:var(--color-danger);">🗑️ Excluir</button>
        </div>
      `;
      processesList.appendChild(div);
    });
  }

  async function populateFilterSources(){
    try {
      // Macros para o select de filtro
      const resMacros = await fetch(`/api/companies/${companyId}/macro-processes`);
      const jsonMacros = await resMacros.json();
      if(jsonMacros && jsonMacros.success){
        (jsonMacros.data || []).forEach(m => { macroById[m.id] = m; });
        if(filterProcessMacro){
          const current = filterProcessMacro.value;
          const options = ['<option value="">Todos</option>'].concat((jsonMacros.data||[]).map(m => {
            const displayText = m.code ? `${m.code} - ${m.name.toUpperCase()}` : m.name;
            return `<option value="${m.id}">${displayText}</option>`;
          }));
          filterProcessMacro.innerHTML = options.join('');
          if(current) filterProcessMacro.value = current;
        }
      }

      // Responsáveis a partir dos colaboradores
      const resEmp = await fetch(`/api/companies/${companyId}/employees`);
      const jsonEmp = await resEmp.json();
      if(jsonEmp && jsonEmp.success && filterProcessResponsible){
        const employees = (jsonEmp.employees||[]).filter(emp => (emp.status === 'active' || emp.status == null));
        const names = Array.from(new Set(employees.map(e => e.name).filter(Boolean)));
        const current = filterProcessResponsible.value;
        const options = ['<option value="">Todos</option>'].concat(names.map(n => `<option value="${escapeHtml(n)}">${escapeHtml(n)}</option>`));
        filterProcessResponsible.innerHTML = options.join('');
        if(current) filterProcessResponsible.value = current;
      }
    } catch(_e) {}
  }

  async function loadProcesses(){
    const res = await fetch(`/api/companies/${companyId}/processes`);
    const json = await res.json();
    if(!(json && json.success)) return;
    allProcessesCache = json.data || [];

    if(!allProcessesCache.length){
      processesList.innerHTML = '<div class="surface-card" style="padding:24px;text-align:center;"><p class="text-muted" style="margin:0;">Nenhum processo cadastrado. Use o formulário acima para criar o primeiro processo.</p></div>';
      return;
    }

    // Garantir selects de filtros preenchidos e estado restaurado antes de aplicar filtros
    await populateFilterSources();
    loadSavedProcessFilters();
    applyProcessFilters();
  }
  
  if(processForm){
    processForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const macroId = processForm.macro_id.value.trim();
      const name = processForm.name.value.trim();
      const orderIndex = processForm.order_index.value.trim();
      
      if(!macroId){
        window.showMessage('Selecione um macroprocesso','error');
        return;
      }
      if(!name){
        window.showMessage('Informe o nome do processo','error');
        return;
      }
      if(!orderIndex || Number(orderIndex) < 1){
        window.showMessage('Informe uma sequência válida (número maior que 0)','error');
        return;
      }
      
      const payload = { 
        macro_id: Number(macroId),
        name: name,
        performance_level: processForm.performance_level.value, 
        responsible: processForm.responsible.value.trim(),
        description: processForm.description.value.trim(),
        order_index: Number(orderIndex)
      };
      
      const id = processForm.id.value;
      const url = id ? `/api/companies/${companyId}/processes/${id}` : `/api/companies/${companyId}/processes`;
      const method = id ? 'PUT' : 'POST';
      
      console.log('Salvando processo:', { id, url, method, payload });
      
      const res = await fetch(url, { method, headers: {'Content-Type':'application/json'}, body: JSON.stringify(payload) });
      const json = await res.json();
      
      console.log('Resposta da API:', json);
      
      if(json && json.success){ 
        window.showMessage('Processo salvo com sucesso','success'); 
        processForm.reset();
        if(processCodePreview) processCodePreview.textContent = 'Selecione um macroprocesso';
        // Memorizar último macroprocesso usado
        try { localStorage.setItem(LAST_MACRO_USED_KEY, String(macroId)); } catch(_e) {}
        
        // Restaurar o último macro usado imediatamente após o reset
        setTimeout(() => {
          try {
            const saved = localStorage.getItem(LAST_MACRO_USED_KEY);
            if(saved && processMacroSelect){
              processMacroSelect.value = saved;
              const selectedOption = processMacroSelect.options[processMacroSelect.selectedIndex];
              if(selectedOption && selectedOption.value){
                const macroText = selectedOption.textContent;
                const macroCode = macroText.split(' - ')[0];
                if(processCodePreview) processCodePreview.textContent = `${macroCode}.? (ex: ${macroCode}.1)`;
              }
            }
          } catch(_e) {}
        }, 0);
        
        loadProcesses();
        
        // Reload process map visual
        if(window.renderProcessMap) window.renderProcessMap();
      }
      else { 
        console.error('Erro ao salvar:', json);
        window.showMessage(json?.error || 'Falha ao salvar processo','error'); 
      }
    });
  }

  // Restaura último macroprocesso usado ao focar no formulário/novo cadastro
  if(processForm && processMacroSelect){
    const restoreLastMacro = () => {
      try {
        const saved = localStorage.getItem(LAST_MACRO_USED_KEY);
        if(saved && !processForm.id.value){
          // Verificar se o valor salvo ainda existe nas opções
          const optionExists = Array.from(processMacroSelect.options).some(opt => opt.value === saved);
          if(optionExists){
            processMacroSelect.value = saved;
            const selectedOption = processMacroSelect.options[processMacroSelect.selectedIndex];
            if(selectedOption && selectedOption.value){
              const macroText = selectedOption.textContent;
              const macroCode = macroText.split(' - ')[0];
              if(processCodePreview) processCodePreview.textContent = `${macroCode}.? (ex: ${macroCode}.1)`;
            }
          }
        }
      } catch(_e) {}
    };
    // Ao abrir a página
    restoreLastMacro();
    // Ao clicar no botão Limpar
    const resetBtn = processForm.querySelector('button[type="reset"]');
    if(resetBtn){
      resetBtn.addEventListener('click', () => {
        setTimeout(restoreLastMacro, 0);
      });
    }
  }
  
  if(processesList){
    processesList.addEventListener('click', async (e) => {
      const editBtn = e.target.closest('[data-edit-proc]');
      const delBtn = e.target.closest('[data-del-proc]');
      if(editBtn){
        const id = editBtn.getAttribute('data-edit-proc');
        const res = await fetch(`/api/companies/${companyId}/processes`);
        const json = await res.json();
        const p = (json.data||[]).find(x => x.id == id);
        if(p){
          processForm.id.value = p.id;
          processForm.macro_id.value = p.macro_id||'';
          
          // Extrair apenas a sequência do código completo (ex: "AO.C.1.1.1" -> "1")
          let sequenceNumber = '';
          if(p.code){
            const parts = p.code.split('.');
            sequenceNumber = parts[parts.length - 1] || '';
          }
          processForm.order_index.value = sequenceNumber || p.order_index || '';
          
          processForm.name.value = p.name||'';
          processForm.performance_level.value = p.performance_level||'';
          processForm.responsible.value = p.responsible||'';
          processForm.description.value = p.description||'';
          
          // Atualizar preview do código
          if(processMacroSelect && processCodePreview && p.macro_id){
            const selectedOption = Array.from(processMacroSelect.options).find(opt => opt.value == p.macro_id);
            if(selectedOption){
              const macroText = selectedOption.textContent;
              const macroCode = macroText.split(' - ')[0];
              processCodePreview.textContent = `${macroCode}.? (ex: ${macroCode}.1)`;
            }
          }
          
          // Scroll to form
          processForm.scrollIntoView({ behavior: 'smooth', block: 'start' });
          processForm.macro_id.focus();
        }
      } else if(delBtn){
        if(!confirm('Tem certeza que deseja excluir este processo? Esta ação não pode ser desfeita.')) return;
        const id = delBtn.getAttribute('data-del-proc');
        const res = await fetch(`/api/companies/${companyId}/processes/${id}`, {method:'DELETE'});
        const json = await res.json();
        if(json && json.success){ 
          window.showMessage('Processo excluído com sucesso','success'); 
          loadProcesses();
          
          // Reload process map visual
          if(window.renderProcessMap) window.renderProcessMap();
        }
        else { window.showMessage(json?.error || 'Falha ao excluir processo','error'); }
      }
    });
  }

  // Eventos de filtros
  if(filterProcessQuery){
    filterProcessQuery.addEventListener('input', () => { saveProcessFilters(); applyProcessFilters(); });
  }
  if(filterProcessMacro){
    filterProcessMacro.addEventListener('change', () => { saveProcessFilters(); applyProcessFilters(); });
  }
  if(filterProcessResponsible){
    filterProcessResponsible.addEventListener('change', () => { saveProcessFilters(); applyProcessFilters(); });
  }
  if(filterProcessPerformance){
    filterProcessPerformance.addEventListener('change', () => { saveProcessFilters(); applyProcessFilters(); });
  }
  if(btnClearProcessFilters){
    btnClearProcessFilters.addEventListener('click', () => {
      if(filterProcessQuery) filterProcessQuery.value = '';
      if(filterProcessMacro) filterProcessMacro.value = '';
      if(filterProcessResponsible) filterProcessResponsible.value = '';
      if(filterProcessPerformance) filterProcessPerformance.value = '';
      saveProcessFilters();
      applyProcessFilters();
    });
  }

  // Colapsar/expandir filtros com persistência
  function updateFilterCollapseUI(){
    const collapsed = localStorage.getItem(FILTER_COLLAPSE_KEY) === '1';
    if(processFiltersSection){
      processFiltersSection.style.display = collapsed ? 'none' : '';
    }
    if(toggleProcessFilters){
      toggleProcessFilters.textContent = collapsed ? 'Mostrar filtros' : 'Ocultar filtros';
    }
  }
  if(toggleProcessFilters){
    toggleProcessFilters.addEventListener('click', () => {
      const collapsed = localStorage.getItem(FILTER_COLLAPSE_KEY) === '1';
      localStorage.setItem(FILTER_COLLAPSE_KEY, collapsed ? '0' : '1');
      updateFilterCollapseUI();
    });
    updateFilterCollapseUI();
  }

  // Render Process Map Visual
  async function renderProcessMap(){
    const container = document.getElementById('processMapContainer');
    if(!container) return;
    
    const res = await fetch(`/api/companies/${companyId}/process-map`);
    const json = await res.json();
    if(!(json && json.success)){ container.innerHTML = '<p class="text-muted">Falha ao carregar mapa.</p>'; return; }
    
    const data = json.data;
    const areas = data.areas || [];
    
    if(!areas.length){
      container.innerHTML = '<div style="padding:40px;text-align:center;"><p class="text-muted">Nenhuma área cadastrada. Adicione áreas, macroprocessos e processos para visualizar o mapa.</p></div>';
      return;
    }
    
    // Mapeamento de níveis
    const structuringMap = {
      '': { label: 'Fora de Escopo', color: '#6b7280', icon: '⚪' },
      'in_progress': { label: 'Map|Impl|Estabn', color: '#f59e0b', icon: '🟡' },
      'stabilized': { label: 'Estabilizado', color: '#10b981', icon: '🟢' },
      'initiated': { label: 'Map|Impl|Estabn', color: '#f59e0b', icon: '🟡' },
      'structured': { label: 'Estabilizado', color: '#10b981', icon: '🟢' }
    };
    
    const performanceMap = {
      '': { label: 'Fora de Escopo', color: '#6b7280', icon: '⚪' },
      'critical': { label: 'Crítico', color: '#ef4444', icon: '🔴' },
      'below': { label: 'Abaixo', color: '#f59e0b', icon: '🟡' },
      'satisfactory': { label: 'Satisfatório', color: '#10b981', icon: '🟢' },
      'initiated': { label: 'Abaixo', color: '#f59e0b', icon: '🟡' },
      'structured': { label: 'Satisfatório', color: '#10b981', icon: '🟢' }
    };
    
    // Calcular totais
    let totalMacros = 0;
    let totalProcessos = 0;
    areas.forEach(area => {
      const macros = area.macros || [];
      totalMacros += macros.length;
      macros.forEach(macro => {
        totalProcessos += (macro.processes || []).length;
      });
    });
    
    let html = '<div style="display:flex;flex-direction:column;gap:24px;color:#0f172a;">';
    
    // Seção de Resumo (Summary Cards)
    html += `<section class="summary-section" style="display:flex;flex-wrap:wrap;gap:12px;margin-bottom:8px;">`;
    html += `<div class="summary-card" style="border:1px solid rgba(148,163,184,0.35);border-radius:8px;padding:12px 16px;min-width:140px;background:#f8fafc;">`;
    html += `<div style="font-size:10px;letter-spacing:0.04em;text-transform:uppercase;color:#64748b;margin-bottom:4px;">Áreas</div>`;
    html += `<div style="font-weight:600;font-size:16px;color:#0f172a;">${areas.length}</div>`;
    html += `</div>`;
    html += `<div class="summary-card" style="border:1px solid rgba(148,163,184,0.35);border-radius:8px;padding:12px 16px;min-width:140px;background:#f8fafc;">`;
    html += `<div style="font-size:10px;letter-spacing:0.04em;text-transform:uppercase;color:#64748b;margin-bottom:4px;">Macroprocessos</div>`;
    html += `<div style="font-weight:600;font-size:16px;color:#0f172a;">${totalMacros}</div>`;
    html += `</div>`;
    html += `<div class="summary-card" style="border:1px solid rgba(148,163,184,0.35);border-radius:8px;padding:12px 16px;min-width:140px;background:#f8fafc;">`;
    html += `<div style="font-size:10px;letter-spacing:0.04em;text-transform:uppercase;color:#64748b;margin-bottom:4px;">Processos</div>`;
    html += `<div style="font-weight:600;font-size:16px;color:#0f172a;">${totalProcessos}</div>`;
    html += `</div>`;
    html += `</section>`;
    
    areas.forEach((area, areaIdx) => {
      const areaColor = area.color || '#a78bfa';
      const areaDisplay = area.code ? `${area.code} - ${area.name.toUpperCase()}` : area.name.toUpperCase();
      
      // Função auxiliar para criar cor suave da área (mix com branco)
      const mixAreaColor = (hexColor, factor = 0.82) => {
        const hex = hexColor.replace('#', '');
        const r = parseInt(hex.substr(0, 2), 16);
        const g = parseInt(hex.substr(2, 2), 16);
        const b = parseInt(hex.substr(4, 2), 16);
        const blend = (c) => Math.round(c + (255 - c) * factor);
        return `rgb(${blend(r)}, ${blend(g)}, ${blend(b)})`;
      };
      
      const areaColorSoft = mixAreaColor(areaColor);
      
      html += `<div class="print-area-block" style="--print-area-color:${areaColor};margin:16px 0 20px 0;background:#ffffff !important;">`;
      
      // Cabeçalho da Área - Usando gradiente suave como no PDF
      html += `<div class="print-page-header print-area-header" style="--print-area-color:${areaColor};background:linear-gradient(135deg, ${areaColorSoft}, rgba(255,255,255,0.92));border:1px solid ${areaColorSoft};border-radius:10px;padding:14px 18px;display:flex;justify-content:space-between;align-items:center;">`;
      html += `<div style="font-weight:600;font-size:15px;color:#000000;text-transform:uppercase;margin:0;">${areaDisplay}</div>`;
      html += `<div style="font-size:10px;color:#1e3a8a;">${(area.macros||[]).length} macroprocesso(s) • ${(area.macros||[]).reduce((sum, m) => sum + (m.processes||[]).length, 0)} processo(s)</div>`;
      html += `</div>`;
      
      const macros = area.macros || [];
      
      if(!macros.length){
        html += `<div style="padding:20px;text-align:center;color:#6b7280;">Nenhum macroprocesso cadastrado nesta área</div>`;
      } else {
        html += `<div style="padding:16px;">`;
        
        macros.forEach((macro, macroIdx) => {
          const macroDisplay = macro.code ? `${macro.code} - ${macro.name.toUpperCase()}` : macro.name;
          
          // Usar div simples para macroprocesso (mais parecido com o PDF)
          html += `<div class="print-macro-block" style="margin-top:16px;margin-bottom:${macroIdx < macros.length - 1 ? '20px' : '0'};page-break-inside:avoid;break-inside:avoid;background:#ffffff;">`;
          
          // Cabeçalho do Macroprocesso
          html += `<div class="macro-title" style="font-weight:600;font-size:13px;color:#000000;margin:0 0 2px 0;">${macroDisplay}</div>`;
          if (macro.owner) {
            html += `<div class="macro-owner" style="margin:2px 0 10px;font-size:10px;color:#1e3a8a;">Responsável: ${macro.owner}</div>`;
          }
          
          // Processos do Macroprocesso
          const processes = macro.processes || [];
          
          if(!processes.length){
            html += `<div style="padding:12px 0;color:#6b7280;font-size:12px;">Nenhum processo cadastrado neste macroprocesso.</div>`;
          } else {
            html += `<div class="process-grid" style="display:grid;grid-template-columns:repeat(auto-fit, minmax(210px, 1fr));gap:12px;margin-top:8px;">`;
            
            processes.forEach(proc => {
              const sLevel = structuringMap[proc.structuring_level] || structuringMap[''];
              const pLevel = performanceMap[proc.performance_level] || performanceMap[''];
              const procDisplay = proc.code ? `${proc.code} - ${proc.name.toUpperCase()}` : proc.name;
              
              // Função auxiliar para misturar cor com branco (criar background suave)
              const mixWithWhite = (hexColor, factor = 0.88) => {
                const hex = hexColor.replace('#', '');
                const r = parseInt(hex.substr(0, 2), 16);
                const g = parseInt(hex.substr(2, 2), 16);
                const b = parseInt(hex.substr(4, 2), 16);
                const blend = (c) => Math.round(c + (255 - c) * factor);
                return `rgb(${blend(r)}, ${blend(g)}, ${blend(b)})`;
              };
              
              const sLevelBg = mixWithWhite(sLevel.color);
              const pLevelBg = mixWithWhite(pLevel.color);
              
              html += `<div class="print-process-card" style="background:#ffffff;border:1px solid rgba(148,163,184,0.4);border-radius:10px;padding:12px;display:flex;flex-direction:column;gap:8px;">`;
              html += `<div class="process-title" style="font-weight:600;font-size:12px;color:#000000;margin:0;line-height:1.3;">${procDisplay}</div>`;
              
              if(proc.responsible){
                html += `<div class="process-meta" style="font-size:10px;color:#1e3a8a;">Responsável: ${proc.responsible}</div>`;
              }
              
              html += `<div class="badge-group" style="display:flex;flex-direction:column;gap:4px;">`;
              const darkYellow = '#b45309';
              const sTextColor = (sLevel.color === '#f59e0b') ? darkYellow : sLevel.color;
              const pTextColor = (pLevel.color === '#f59e0b') ? darkYellow : pLevel.color;

              html += `<div class="badge" style="display:inline-flex;align-items:center;gap:6px;border-radius:6px;padding:4px 6px;font-size:9.5px;font-weight:600;background:${sLevelBg};color:${sTextColor};line-height:1.1;">`;
              html += `<span class="badge-label" style="text-transform:uppercase;font-weight:500;color:#475569;letter-spacing:0.03em;">Estruturação</span>`;
              html += `<span class="badge-value" style="font-weight:600;">${sLevel.label}</span>`;
              html += `</div>`;
              html += `<div class="badge" style="display:inline-flex;align-items:center;gap:6px;border-radius:6px;padding:4px 6px;font-size:9.5px;font-weight:600;background:${pLevelBg};color:${pTextColor};line-height:1.1;">`;
              html += `<span class="badge-label" style="text-transform:uppercase;font-weight:500;color:#475569;letter-spacing:0.03em;">Desempenho</span>`;
              html += `<span class="badge-value" style="font-weight:600;">${pLevel.label}</span>`;
              html += `</div>`;
              html += `</div>`;
              
              if(proc.description){
                html += `<div class="process-description" style="font-size:9.8px;color:#334155;line-height:1.4;margin-top:4px;word-break:break-word;">${proc.description}</div>`;
              }
              
              html += `</div>`;
            });
            
            html += `</div>`;
          }
          
          html += `</div>`;
        });
        
        html += `</div>`;
      }
      
      html += `</div>`;
    });
    
    html += '</div>';
    container.innerHTML = html;
    
    // Atualizar timestamp após renderizar
    updateMapTimestamp();
  }

  // Atualizar data de "Atualizado em" quando renderizar o mapa
  function updateMapTimestamp(){
    const mapLastUpdate = document.getElementById('mapLastUpdate');
    if(mapLastUpdate){
      const today = new Date();
      const dateStr = today.toLocaleDateString('pt-BR');
      mapLastUpdate.textContent = dateStr;
    }
  }
  
  // Visualizador de Impressão
  const mapViewerModal = document.getElementById('mapViewerModal');
  const mapViewerInner = document.getElementById('mapViewerInner');
  const btnViewMap = document.getElementById('btnViewMap');
  const btnExportPdf = document.getElementById('btnExportPdf');
  const btnViewMapV2 = document.getElementById('btnViewMapV2');
  const btnExportPdfV2 = document.getElementById('btnExportPdfV2');
  const btnCloseViewer = document.getElementById('btnCloseViewer');
  const btnZoomIn = document.getElementById('btnZoomIn');
  const btnZoomOut = document.getElementById('btnZoomOut');
  const btnZoomReset = document.getElementById('btnZoomReset');
  const btnZoomFit = document.getElementById('btnZoomFit');
  const btnPrintFromViewer = document.getElementById('btnPrintFromViewer');
  const zoomLevelDisplay = document.getElementById('zoomLevel');
  
  let currentZoom = 1.0;
  let currentOrientation = 'portrait';
  
  function updateZoomDisplay(){
    if(zoomLevelDisplay){
      zoomLevelDisplay.textContent = Math.round(currentZoom * 100) + '%';
    }
    if(mapViewerInner){
      // Remover todas as classes de zoom anteriores
      for(let i = 3; i <= 20; i++){
        mapViewerInner.classList.remove(`zoom-level-${i*10}`);
      }
      
      // Adicionar classe do zoom atual (arredondado para níveis de 10%)
      const zoomPercent = Math.round(currentZoom * 100);
      const zoomLevel = Math.round(zoomPercent / 10) * 10; // Arredondar para 10, 20, 30, etc.
      mapViewerInner.classList.add(`zoom-level-${zoomLevel}`);
      
      // Atualizar classes de zoom para controlar colunas
      mapViewerInner.classList.remove('zoom-small', 'zoom-medium', 'zoom-large');
      
      if(currentZoom < 0.7){
        mapViewerInner.classList.add('zoom-small'); // 4 colunas
      } else if(currentZoom >= 0.7 && currentZoom <= 1.3){
        mapViewerInner.classList.add('zoom-medium'); // 3 colunas (padrão)
      } else {
        mapViewerInner.classList.add('zoom-large'); // 2 colunas
      }
      
      // Aplicar orientação
      mapViewerInner.classList.remove('orientation-portrait', 'orientation-landscape');
      mapViewerInner.classList.add(`orientation-${currentOrientation}`);
    }
  }
  
  function openViewer(){
    if(!mapViewerModal || !mapViewerInner) return;

    // Clonar conteudo do mapa  
    const mapContainer = document.getElementById('processMapContainer');
    if(mapContainer){
      // Buscar informacoes do cabecalho
      const companyName = document.querySelector('.card-header h3')?.textContent || 'Empresa';

      // Buscar metadados individuais
      const versaoEl = document.querySelector('.card-header strong');
      const criadoEl = document.querySelectorAll('.card-header > div > div > div')[1];
      const atualizadoEl = document.getElementById('mapLastUpdate');
      const impressoEl = document.getElementById('printDate');

      const versao = versaoEl ? '1.0' : '1.0';
      const criado = criadoEl ? criadoEl.textContent.replace('Criado em: ', '') : 'N/A';
      const atualizado = atualizadoEl ? atualizadoEl.textContent : 'N/A';
      const impresso = impressoEl ? impressoEl.textContent : '';

      const buildHeader = (dateTargetId) => `
        <div class='print-header-content'>
          <div class='print-header-title-row'>
            <h2 class='print-header-title'>${companyName}</h2>
            <span class='print-page-counter' aria-hidden='true'></span>
          </div>
          <div class='print-header-meta'>
            <div><strong>Versao:</strong> ${versao}</div>
            <div><strong>Criado em:</strong> ${criado}</div>
            <div><strong>Atualizado em:</strong> ${atualizado}</div>
            <div><strong>Impresso em:</strong> <span id='${dateTargetId}'>${impresso}</span></div>
          </div>
        </div>
      `;

      const runningHeader = `<div class='print-page-header-global'>${buildHeader('viewerPrintDatePrint')}</div>`;
      const visibleHeader = `<div class='print-page-header-visible'>${buildHeader('viewerPrintDate')}</div>`;

      mapViewerInner.innerHTML = `${runningHeader}${visibleHeader}${mapContainer.innerHTML}`;
    }

    // Resetar zoom para 100% e 3 colunas (padrao)
    currentZoom = 1.0;
    currentOrientation = 'portrait';
    updateZoomDisplay();

    // Atualizar select de orientacao
    const orientationSelect = document.getElementById('orientationSelect');
    if(orientationSelect){
      orientationSelect.value = 'portrait';
    }

    // Mostrar modal
    mapViewerModal.style.display = 'flex';
    document.body.style.overflow = 'hidden';

    // Calcular paginacao aproximada
    setTimeout(calculatePages, 500);
  }

  
  function closeViewer(){
    if(mapViewerModal){
      mapViewerModal.style.display = 'none';
      document.body.style.overflow = '';
    }
  }
  
  function zoomIn(){
    currentZoom = Math.min(currentZoom + 0.1, 3.0); // Max 300%
    updateZoomDisplay();
    setTimeout(calculatePages, 300);
  }
  
  function zoomOut(){
    currentZoom = Math.max(currentZoom - 0.1, 0.3); // Min 30%
    updateZoomDisplay();
    setTimeout(calculatePages, 300);
  }
  
  function zoomReset(){
    currentZoom = 1.0;
    updateZoomDisplay();
    setTimeout(calculatePages, 300);
  }
  
  function calculatePages(){
    // Cálculo aproximado de páginas baseado na altura do conteúdo
    if(!mapViewerInner) return;
    
    const A4_HEIGHT_MM = 297;
    const MARGIN_MM = 40; // 2cm top + 2cm bottom
    const USABLE_HEIGHT_MM = A4_HEIGHT_MM - MARGIN_MM;
    
    // Converter altura do conteúdo para mm (aproximado)
    const contentHeightPx = mapViewerInner.scrollHeight;
    const pxToMm = 0.2645833333; // Conversão aproximada 96dpi
    const contentHeightMm = contentHeightPx * pxToMm;
    
    const estimatedPages = Math.max(1, Math.ceil(contentHeightMm / USABLE_HEIGHT_MM));
    
    const pageInfo = document.getElementById('pageInfo');
    if(pageInfo){
      pageInfo.textContent = `Aprox. ${estimatedPages} página${estimatedPages !== 1 ? 's' : ''}`;
    }
  }
  
  function zoomFit(){
    if(!mapViewerInner) return;
    const content = document.querySelector('.map-viewer-content');
    if(!content) return;
    
    const contentWidth = content.clientWidth - 40; // Padding
    const contentHeight = content.clientHeight - 40;
    const innerWidth = mapViewerInner.scrollWidth;
    const innerHeight = mapViewerInner.scrollHeight;
    
    const scaleX = contentWidth / innerWidth;
    const scaleY = contentHeight / innerHeight;
    
    currentZoom = Math.min(scaleX, scaleY, 1.0); // Não aumentar, só diminuir
    updateZoomDisplay();
  }
  
  // Event listeners
  if(btnViewMap){
    btnViewMap.addEventListener('click', openViewer);
  }

  if(btnExportPdf){
    btnExportPdf.addEventListener('click', () => {
      if(Number.isNaN(companyId)) return;
      const url = `/grv/company/${companyId}/process/map/pdf`;
      const opened = window.open(url, '_blank', 'noopener');
      if(!opened && window.showMessage){
        window.showMessage('Não foi possível abrir o PDF. Verifique o bloqueador de pop-ups.', 'error');
      }
    });
  }

  // MP-2 Buttons
  if(btnViewMapV2){
    btnViewMapV2.addEventListener('click', () => {
      if(Number.isNaN(companyId)) return;
      const url = `/grv/company/${companyId}/process/map/pdf2`;
      const opened = window.open(url, '_blank', 'noopener');
      if(!opened && window.showMessage){
        window.showMessage('Não foi possível abrir o PDF MP-2. Verifique o bloqueador de pop-ups.', 'error');
      }
    });
  }

  if(btnExportPdfV2){
    btnExportPdfV2.addEventListener('click', () => {
      if(Number.isNaN(companyId)) return;
      const url = `/grv/company/${companyId}/process/map/pdf2`;
      // Força download em vez de visualização
      fetch(url)
        .then(response => response.blob())
        .then(blob => {
          const url = window.URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.style.display = 'none';
          a.href = url;
          a.download = `mapa-processos-v2-${Date.now()}.pdf`;
          document.body.appendChild(a);
          a.click();
          window.URL.revokeObjectURL(url);
          document.body.removeChild(a);
          if(window.showMessage){
            window.showMessage('PDF MP-2 exportado com sucesso!', 'success');
          }
        })
        .catch(err => {
          console.error('Erro ao exportar PDF MP-2:', err);
          if(window.showMessage){
            window.showMessage('Erro ao exportar PDF MP-2. Tente novamente.', 'error');
          }
        });
    });
  }
  
  if(btnCloseViewer){
    btnCloseViewer.addEventListener('click', closeViewer);
  }
  
  if(btnZoomIn){
    btnZoomIn.addEventListener('click', zoomIn);
  }
  
  if(btnZoomOut){
    btnZoomOut.addEventListener('click', zoomOut);
  }
  
  if(btnZoomReset){
    btnZoomReset.addEventListener('click', zoomReset);
  }
  
  if(btnZoomFit){
    btnZoomFit.addEventListener('click', () => {
      zoomFit();
      setTimeout(calculatePages, 300);
    });
  }
  
  // Controle de orientação
  const orientationSelect = document.getElementById('orientationSelect');
  if(orientationSelect){
    orientationSelect.addEventListener('change', (e) => {
      currentOrientation = e.target.value;
      updateZoomDisplay();
      setTimeout(calculatePages, 300);
    });
  }
  
  if(btnPrintFromViewer){
    btnPrintFromViewer.addEventListener('click', () => {
      // Atualizar data de impressão
      const now = new Date();
      const dateStr = now.toLocaleDateString('pt-BR');
      const timeStr = now.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
      const impressaoTexto = `${dateStr} às ${timeStr}`;
      
      // Atualizar no cabeçalho original
      const printDate = document.getElementById('printDate');
      if(printDate){
        printDate.textContent = impressaoTexto;
      }
      
      // Atualizar no viewer
      const viewerPrintDate = document.getElementById('viewerPrintDate');
      if(viewerPrintDate){
        viewerPrintDate.textContent = impressaoTexto;
      }
      
      const viewerPrintDatePrint = document.getElementById('viewerPrintDatePrint');
      if(viewerPrintDatePrint){
        viewerPrintDatePrint.textContent = impressaoTexto;
      }
      
      // Imprimir
      setTimeout(() => window.print(), 100);
    });
  }
  
  // Fechar com ESC
  document.addEventListener('keydown', (e) => {
    if(e.key === 'Escape' && mapViewerModal && mapViewerModal.style.display === 'flex'){
      closeViewer();
    }
  });
  
  // Fechar clicando no overlay
  const overlay = document.querySelector('.map-viewer-overlay');
  if(overlay){
    overlay.addEventListener('click', closeViewer);
  }
  
  // Botão Imprimir direto (sem visualizador)
  const btnPrintMap = document.getElementById('btnPrintMap');
  if(btnPrintMap){
    btnPrintMap.addEventListener('click', () => {
      // Atualizar data de impressao antes de imprimir
      const now = new Date();
      const dateStr = now.toLocaleDateString('pt-BR');
      const timeStr = now.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });

      const printDate = document.getElementById('printDate');
      if(printDate){
        printDate.textContent = `${dateStr} às ${timeStr}`;
      }

      const viewerPrintDatePrint = document.getElementById('viewerPrintDatePrint');
      if(viewerPrintDatePrint){
        viewerPrintDatePrint.textContent = `${dateStr} às ${timeStr}`;
      }

      // Imprimir
      setTimeout(() => window.print(), 100);
    });
  }
  
  // Expose functions globally
  window.renderProcessMap = renderProcessMap;
  window.loadMacros = loadMacros;
  window.loadAreas = loadAreas;
  window.loadProcesses = loadProcesses;
  window.loadEmployees = loadEmployees;

  // Init
  loadAreas();
  loadMacros();
  loadProcesses();
  loadEmployees();
  renderProcessMap();
})();

