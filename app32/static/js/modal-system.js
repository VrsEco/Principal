/**
 * Sistema Centralizado de Modais - GestaoVersus
 * 
 * PADRÃO DE Z-INDEX DO PROJETO:
 * - Conteúdo normal: 1-99
 * - Dropdowns/tooltips: 100-999
 * - Sidebars/overlays: 1000-9999
 * - Botões flutuantes: 10000-19999
 * - Modais do sistema: 20000-29999
 * - Modais críticos/alerts: 30000-39999
 * - Debug/desenvolvimento: 40000+
 * 
 * USO:
 * const modal = new Modal('meuModalId');
 * modal.open();
 * modal.close();
 */

class Modal {
  constructor(modalId, options = {}) {
    this.modalId = modalId;
    this.modalElement = document.getElementById(modalId);
    
    // Configurações padrão
    this.config = {
      zIndex: 25000, // Z-index padrão para modais do sistema
      backdrop: true,
      closeOnBackdrop: true,
      closeOnEscape: true,
      animation: true,
      ...options
    };
    
    if (!this.modalElement) {
      console.error(`[Modal System] Modal com id "${modalId}" não encontrado!`);
      return;
    }
    
    this.init();
  }
  
  init() {
    // Garantir estilos base do modal
    this.applyBaseStyles();
    
    // Adicionar eventos
    this.setupEvents();
    
    console.log(`[Modal System] Modal "${this.modalId}" inicializado com z-index: ${this.config.zIndex}`);
  }
  
  applyBaseStyles() {
    const modal = this.modalElement;
    
    // Aplicar estilos inline que sempre funcionam
    modal.style.display = 'none';
    modal.style.position = 'fixed';
    modal.style.top = '0';
    modal.style.left = '0';
    modal.style.width = '100%';
    modal.style.height = '100%';
    modal.style.zIndex = this.config.zIndex.toString();
    modal.style.alignItems = 'center';
    modal.style.justifyContent = 'center';
    
    if (this.config.backdrop) {
      modal.style.backgroundColor = 'rgba(0, 0, 0, 0.6)';
      modal.style.backdropFilter = 'blur(4px)';
    }
  }
  
  setupEvents() {
    // Fechar ao clicar no backdrop
    if (this.config.closeOnBackdrop) {
      this.modalElement.addEventListener('click', (e) => {
        if (e.target === this.modalElement) {
          this.close();
        }
      });
    }
    
    // Fechar com ESC
    if (this.config.closeOnEscape) {
      this.escapeHandler = (e) => {
        if (e.key === 'Escape' && this.isOpen()) {
          this.close();
        }
      };
      document.addEventListener('keydown', this.escapeHandler);
    }
    
    // Botões de fechar internos
    const closeButtons = this.modalElement.querySelectorAll('[data-modal-close]');
    closeButtons.forEach(btn => {
      btn.addEventListener('click', () => this.close());
    });
  }
  
  open() {
    console.log(`[Modal System] Abrindo modal "${this.modalId}"`);
    
    const modal = this.modalElement;
    
    // Forçar display flex
    modal.style.display = 'flex';
    
    // Adicionar classe para animação se configurado
    if (this.config.animation) {
      modal.classList.add('modal-opening');
      setTimeout(() => {
        modal.classList.remove('modal-opening');
        modal.classList.add('modal-open');
      }, 10);
    } else {
      modal.classList.add('modal-open');
    }
    
    // Prevenir scroll do body
    document.body.style.overflow = 'hidden';
    
    // Emitir evento customizado
    modal.dispatchEvent(new CustomEvent('modalOpened', { detail: { modalId: this.modalId } }));
    
    console.log(`[Modal System] Modal "${this.modalId}" aberto com sucesso`);
  }
  
  close() {
    console.log(`[Modal System] Fechando modal "${this.modalId}"`);
    
    const modal = this.modalElement;
    
    // Animação de fechamento
    if (this.config.animation) {
      modal.classList.add('modal-closing');
      setTimeout(() => {
        modal.style.display = 'none';
        modal.classList.remove('modal-closing', 'modal-open');
        document.body.style.overflow = '';
      }, 300);
    } else {
      modal.style.display = 'none';
      modal.classList.remove('modal-open');
      document.body.style.overflow = '';
    }
    
    // Emitir evento customizado
    modal.dispatchEvent(new CustomEvent('modalClosed', { detail: { modalId: this.modalId } }));
    
    console.log(`[Modal System] Modal "${this.modalId}" fechado`);
  }
  
  isOpen() {
    return this.modalElement.style.display === 'flex' || 
           this.modalElement.classList.contains('modal-open');
  }
  
  destroy() {
    // Remover event listeners
    if (this.escapeHandler) {
      document.removeEventListener('keydown', this.escapeHandler);
    }
    
    console.log(`[Modal System] Modal "${this.modalId}" destruído`);
  }
}

/**
 * Helper para criar modais rapidamente
 */
function createModal(id, content, options = {}) {
  // Criar elemento do modal se não existir
  let modalElement = document.getElementById(id);
  
  if (!modalElement) {
    modalElement = document.createElement('div');
    modalElement.id = id;
    modalElement.className = 'modal-system';
    modalElement.innerHTML = `
      <div class="modal-content-system">
        <button class="modal-close-system" data-modal-close>&times;</button>
        <div class="modal-body-system">
          ${content}
        </div>
      </div>
    `;
    document.body.appendChild(modalElement);
  }
  
  return new Modal(id, options);
}

/**
 * Exportar para uso global
 */
if (typeof window !== 'undefined') {
  window.Modal = Modal;
  window.createModal = createModal;
  
  console.log('[Modal System] Sistema de modais carregado e pronto para uso');
}

