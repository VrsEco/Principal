// =====================================
// REPORT SETTINGS - JavaScript Completo
// =====================================

console.log('✅ report_settings.js carregado');

// =====================================
// PREVIEW DO CANVAS
// =====================================

let drawPreview;

(function initPreview() {
  const canvas = document.getElementById('pagePreview');
  if (!canvas) {
    console.warn('Canvas não encontrado');
    return;
  }
  
  const ctx = canvas.getContext('2d');

  function mmToPx(mm) {
    return (mm / 25.4) * 96;
  }

  const PAPER_SIZES = {
    A4: { width: 210, height: 297 },
    Carta: { width: 216, height: 279 },
    "Ofício": { width: 216, height: 356 }
  };

  const GRID_COLORS = [
    "#bfdbfe", "#bbf7d0", "#fef08a", "#fbcfe8",
    "#c4b5fd", "#fed7aa", "#bae6fd", "#e9d5ff"
  ];

  function getPaperSize() {
    const size = document.getElementById('paper_size')?.value || 'A4';
    return PAPER_SIZES[size] || PAPER_SIZES.A4;
  }

  function isLandscape() {
    return document.getElementById('orientation')?.value === 'Paisagem';
  }

  drawPreview = function() {
    const paper = getPaperSize();
    const landscape = isLandscape();
    const pageWidth = landscape ? paper.height : paper.width;
    const pageHeight = landscape ? paper.width : paper.height;

    const maxHeightMm = 150;
    const maxHeightPx = mmToPx(maxHeightMm);
    const aspectRatio = pageWidth / pageHeight;
    
    const canvasHeight = maxHeightPx;
    const canvasWidth = canvasHeight * aspectRatio;

    canvas.width = canvasWidth;
    canvas.height = canvasHeight;
    canvas.style.width = canvasWidth + 'px';
    canvas.style.height = canvasHeight + 'px';
    
    const scale = maxHeightPx / mmToPx(pageHeight);
    
    ctx.clearRect(0, 0, canvasWidth, canvasHeight);

    const margins = {
      top: Number(document.getElementById('margin_top')?.value || 0),
      right: Number(document.getElementById('margin_right')?.value || 0),
      bottom: Number(document.getElementById('margin_bottom')?.value || 0),
      left: Number(document.getElementById('margin_left')?.value || 0),
    };
    
    const headerHeight = Number(document.getElementById('header_height')?.value || 0);
    const footerHeight = Number(document.getElementById('footer_height')?.value || 0);
    const headerRows = Math.max(Number(document.getElementById('header_rows')?.value || 1), 1);
    const headerCols = Math.max(Number(document.getElementById('header_columns')?.value || 1), 1);
    const footerRows = Math.max(Number(document.getElementById('footer_rows')?.value || 1), 1);
    const footerCols = Math.max(Number(document.getElementById('footer_columns')?.value || 1), 1);

    // Fundo
    ctx.fillStyle = '#f8fafc';
    ctx.fillRect(0, 0, canvasWidth, canvasHeight);

    // Borda das margens
    ctx.strokeStyle = '#94a3b8';
    ctx.lineWidth = 1.2;
    ctx.strokeRect(
      mmToPx(margins.left) * scale,
      mmToPx(margins.top) * scale,
      canvasWidth - mmToPx(margins.left + margins.right) * scale,
      canvasHeight - mmToPx(margins.top + margins.bottom) * scale
    );

    // Cabeçalho com células
    if (headerHeight > 0) {
      const headerLeft = mmToPx(margins.left) * scale;
      const headerTop = mmToPx(margins.top) * scale;
      const headerWidthPx = canvasWidth - mmToPx(margins.left + margins.right) * scale;
      const headerHeightPx = mmToPx(headerHeight) * scale;
      
      // Desenha células do header
      const cellWidth = headerWidthPx / headerCols;
      const cellHeight = headerHeightPx / headerRows;
      
      for (let r = 0; r < headerRows; r++) {
        for (let c = 0; c < headerCols; c++) {
          const colorIndex = (r + c) % GRID_COLORS.length;
          ctx.fillStyle = GRID_COLORS[colorIndex];
          ctx.globalAlpha = 0.35;
          ctx.fillRect(
            headerLeft + c * cellWidth,
            headerTop + r * cellHeight,
            cellWidth,
            cellHeight
          );
          ctx.globalAlpha = 1;
          
          // Borda da célula
          ctx.strokeStyle = 'rgba(15, 23, 42, 0.25)';
          ctx.lineWidth = 1;
          ctx.strokeRect(
            headerLeft + c * cellWidth,
            headerTop + r * cellHeight,
            cellWidth,
            cellHeight
          );
          
          // Texto da célula
          ctx.fillStyle = '#0f172a';
          ctx.font = '11px Arial';
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.fillText(
            `H${r + 1}•C${c + 1}`,
            headerLeft + c * cellWidth + cellWidth / 2,
            headerTop + r * cellHeight + cellHeight / 2
          );
        }
      }
    }

    // Rodapé com células
    if (footerHeight > 0) {
      const footerLeft = mmToPx(margins.left) * scale;
      const footerBottom = canvasHeight - mmToPx(margins.bottom) * scale;
      const footerWidthPx = canvasWidth - mmToPx(margins.left + margins.right) * scale;
      const footerHeightPx = mmToPx(footerHeight) * scale;
      const footerTop = footerBottom - footerHeightPx;
      
      // Desenha células do footer
      const cellWidth = footerWidthPx / footerCols;
      const cellHeight = footerHeightPx / footerRows;
      
      for (let r = 0; r < footerRows; r++) {
        for (let c = 0; c < footerCols; c++) {
          const colorIndex = (r + c) % GRID_COLORS.length;
          ctx.fillStyle = GRID_COLORS[(colorIndex + 2) % GRID_COLORS.length];
          ctx.globalAlpha = 0.35;
          ctx.fillRect(
            footerLeft + c * cellWidth,
            footerTop + r * cellHeight,
            cellWidth,
            cellHeight
          );
          ctx.globalAlpha = 1;
          
          // Borda da célula
          ctx.strokeStyle = 'rgba(15, 23, 42, 0.25)';
          ctx.lineWidth = 1;
          ctx.strokeRect(
            footerLeft + c * cellWidth,
            footerTop + r * cellHeight,
            cellWidth,
            cellHeight
          );
          
          // Texto da célula
          ctx.fillStyle = '#0f172a';
          ctx.font = '11px Arial';
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.fillText(
            `R${r + 1}•C${c + 1}`,
            footerLeft + c * cellWidth + cellWidth / 2,
            footerTop + r * cellHeight + cellHeight / 2
          );
        }
      }
    }
  };

  // Event listeners para todos os campos que afetam o preview
  ['margin_top', 'margin_right', 'margin_bottom', 'margin_left', 
   'header_height', 'footer_height',
   'header_rows', 'header_columns', 
   'footer_rows', 'footer_columns'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.addEventListener('input', drawPreview);
  });
  
  ['paper_size', 'orientation'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.addEventListener('change', drawPreview);
  });

  drawPreview();
  console.log('✅ Preview inicializado');
})();

// =====================================
// SALVAR MODELO
// =====================================

async function saveModel() {
  const saveBtn = document.getElementById('save-model-btn-top');
  const editingId = saveBtn?.dataset.editingId;
  const isEditing = !!editingId;
  
  const name = document.getElementById('preset_name_inline')?.value;
  const description = document.getElementById('preset_description_inline')?.value;
  
  if (!name || name.trim() === '') {
    alert('Por favor, informe o nome do modelo');
    return;
  }
  
  const modelData = {
    name: name.trim(),
    description: description?.trim() || '',
    paper_size: document.getElementById('paper_size').value,
    orientation: document.getElementById('orientation').value,
    margin_top: parseInt(document.getElementById('margin_top').value),
    margin_right: parseInt(document.getElementById('margin_right').value),
    margin_bottom: parseInt(document.getElementById('margin_bottom').value),
    margin_left: parseInt(document.getElementById('margin_left').value),
    header_height: parseInt(document.getElementById('header_height').value),
    header_rows: parseInt(document.getElementById('header_rows').value),
    header_columns: parseInt(document.getElementById('header_columns').value),
    header_content: document.getElementById('header_content').value,
    footer_height: parseInt(document.getElementById('footer_height').value),
    footer_rows: parseInt(document.getElementById('footer_rows').value),
    footer_columns: parseInt(document.getElementById('footer_columns').value),
    footer_content: document.getElementById('footer_content').value
  };
  
  try {
    const url = isEditing ? `/api/reports/models/${editingId}` : '/api/reports/models';
    const method = isEditing ? 'PUT' : 'POST';
    
    console.log(`${method} ${url}`, modelData);
    
    const response = await fetch(url, {
      method: method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(modelData)
    });
    
    const data = await response.json();
    
    if (data.success) {
      if (isEditing) {
        alert(`Modelo atualizado com sucesso!`);
      } else {
        alert(`Modelo salvo com sucesso! ID: ${data.model_id}`);
      }
      location.reload();
    } else {
      alert('Erro: ' + (data.error || 'Desconhecido'));
    }
  } catch (error) {
    console.error('Erro:', error);
    alert('Erro ao conectar: ' + error.message);
  }
}

// =====================================
// LIMPAR CAMPOS
// =====================================

function clearFields() {
  if (!confirm('Deseja realmente limpar todos os campos?')) return;
  
  document.getElementById('preset_name_inline').value = '';
  document.getElementById('preset_description_inline').value = '';
  document.getElementById('preset_code').value = '';
  
  document.getElementById('paper_size').value = 'A4';
  document.getElementById('orientation').value = 'Retrato';
  document.getElementById('margin_top').value = '5';
  document.getElementById('margin_right').value = '5';
  document.getElementById('margin_bottom').value = '5';
  document.getElementById('margin_left').value = '5';
  document.getElementById('header_height').value = '25';
  document.getElementById('header_rows').value = '1';
  document.getElementById('header_columns').value = '3';
  document.getElementById('header_content').value = '';
  document.getElementById('footer_height').value = '15';
  document.getElementById('footer_rows').value = '1';
  document.getElementById('footer_columns').value = '3';
  document.getElementById('footer_content').value = '';
  
  const saveBtn = document.getElementById('save-model-btn-top');
  if (saveBtn) {
    saveBtn.textContent = '💾 Salvar modelo';
    delete saveBtn.dataset.editingId;
  }
  
  if (typeof drawPreview === 'function') drawPreview();
}

// =====================================
// APLICAR MODELO
// =====================================

async function applyModel(modelId) {
  console.log('Aplicando modelo:', modelId);
  
  try {
    const response = await fetch(`/api/reports/models/${modelId}`);
    const data = await response.json();
    
    if (data.success && data.model) {
      const model = data.model;
      
      document.getElementById('paper_size').value = model.paper_size;
      document.getElementById('orientation').value = model.orientation;
      document.getElementById('margin_top').value = model.margins.top;
      document.getElementById('margin_right').value = model.margins.right;
      document.getElementById('margin_bottom').value = model.margins.bottom;
      document.getElementById('margin_left').value = model.margins.left;
      document.getElementById('header_height').value = model.header.height;
      document.getElementById('header_rows').value = model.header.rows;
      document.getElementById('header_columns').value = model.header.columns;
      document.getElementById('header_content').value = model.header.content || '';
      document.getElementById('footer_height').value = model.footer.height;
      document.getElementById('footer_rows').value = model.footer.rows;
      document.getElementById('footer_columns').value = model.footer.columns;
      document.getElementById('footer_content').value = model.footer.content || '';
      
      if (typeof drawPreview === 'function') drawPreview();
      
      window.scrollTo({ top: 0, behavior: 'smooth' });
      alert(`Modelo "${model.name}" aplicado com sucesso!`);
    }
  } catch (error) {
    console.error('Erro:', error);
    alert('Erro: ' + error.message);
  }
}

// =====================================
// EDITAR MODELO
// =====================================

async function editModel(modelId) {
  console.log('Editando modelo:', modelId);
  
  try {
    const response = await fetch(`/api/reports/models/${modelId}`);
    
    if (!response.ok) {
      alert(`Erro ${response.status}: ${response.statusText}`);
      return;
    }
    
    const data = await response.json();
    console.log('Dados recebidos:', data);
    
    if (data.success && data.model) {
      const model = data.model;
      
      // Preencher campos
      document.getElementById('preset_name_inline').value = model.name;
      document.getElementById('preset_description_inline').value = model.description || '';
      document.getElementById('preset_code').value = `MODEL_${model.id}`;
      
      document.getElementById('paper_size').value = model.paper_size;
      document.getElementById('orientation').value = model.orientation;
      document.getElementById('margin_top').value = model.margins.top;
      document.getElementById('margin_right').value = model.margins.right;
      document.getElementById('margin_bottom').value = model.margins.bottom;
      document.getElementById('margin_left').value = model.margins.left;
      document.getElementById('header_height').value = model.header.height;
      document.getElementById('header_rows').value = model.header.rows;
      document.getElementById('header_columns').value = model.header.columns;
      document.getElementById('header_content').value = model.header.content || '';
      document.getElementById('footer_height').value = model.footer.height;
      document.getElementById('footer_rows').value = model.footer.rows;
      document.getElementById('footer_columns').value = model.footer.columns;
      document.getElementById('footer_content').value = model.footer.content || '';
      
      // Atualizar preview
      if (typeof drawPreview === 'function') drawPreview();
      
      // Mudar botão para modo edição
      const saveBtn = document.getElementById('save-model-btn-top');
      if (saveBtn) {
        saveBtn.textContent = '✏️ Atualizar modelo';
        saveBtn.dataset.editingId = modelId;
      }
      
      // Scroll para topo
      window.scrollTo({ top: 0, behavior: 'smooth' });
      
      alert(`Modelo "${model.name}" carregado para edição!`);
    }
  } catch (error) {
    console.error('Erro:', error);
    alert('Erro: ' + error.message);
  }
}

// =====================================
// EXCLUIR MODELO
// =====================================

async function deleteModel(modelId) {
  if (!confirm('Deseja realmente excluir este modelo?\nEsta ação não pode ser desfeita.')) {
    return;
  }
  
  console.log('Excluindo modelo:', modelId);
  
  try {
    const response = await fetch(`/api/reports/models/${modelId}`, {
      method: 'DELETE'
    });
    
    const data = await response.json();
    
    if (data.success) {
      alert('Modelo excluído com sucesso!');
      location.reload();
    } else {
      if (data.conflicts && data.conflicts.has_conflicts) {
        alert(`Não é possível excluir.\nEste modelo tem ${data.conflicts.instance_count} relatório(s) associado(s).`);
      } else {
        alert('Erro ao excluir: ' + (data.error || 'Desconhecido'));
      }
    }
  } catch (error) {
    console.error('Erro:', error);
    alert('Erro: ' + error.message);
  }
}

// =====================================
// INICIALIZAÇÃO
// =====================================

document.addEventListener('DOMContentLoaded', function() {
  console.log('🔧 Inicializando report_settings.js...');
  
  // Conectar botões do topo
  document.getElementById('save-model-btn-top')?.addEventListener('click', saveModel);
  document.getElementById('clear-fields-btn-top')?.addEventListener('click', clearFields);
  
  // Conectar botões dos modelos
  document.querySelectorAll('.apply-model-btn').forEach(btn => {
    btn.addEventListener('click', function(e) {
      e.preventDefault();
      applyModel(this.dataset.modelId);
    });
  });
  
  document.querySelectorAll('.edit-model-btn').forEach(btn => {
    btn.addEventListener('click', function(e) {
      e.preventDefault();
      editModel(this.dataset.modelId);
    });
  });
  
  document.querySelectorAll('.delete-model-btn').forEach(btn => {
    btn.addEventListener('click', function(e) {
      e.preventDefault();
      deleteModel(this.dataset.modelId);
    });
  });
  
  console.log('✅ Todos os botões conectados!');
  console.log(`   - Aplicar: ${document.querySelectorAll('.apply-model-btn').length}`);
  console.log(`   - Editar: ${document.querySelectorAll('.edit-model-btn').length}`);
  console.log(`   - Excluir: ${document.querySelectorAll('.delete-model-btn').length}`);
});

