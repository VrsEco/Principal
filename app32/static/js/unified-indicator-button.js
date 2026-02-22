/**
 * Unified Indicator Button Component
 * 
 * This component creates a unified button for creating indicators
 * that automatically captures context (plan_id, okr_id, project_id) 
 * based on the current page location.
 */

class UnifiedIndicatorButton {
    constructor(options = {}) {
        this.options = {
            buttonText: options.buttonText || '📊 Criar Indicador',
            buttonClass: options.buttonClass || 'button button-primary unified-indicator-btn',
            containerId: options.containerId || null,
            debug: options.debug || false,
            ...options
        };
        
        this.context = {
            company_id: null,
            plan_id: null,
            okr_id: null,
            okr_level: null,
            project_id: null,
            page_type: null
        };
        
        this.init();
    }
    
    init() {
        this.detectContext();
        this.createButton();
        this.log('UnifiedIndicatorButton initialized', this.context);
    }
    
    detectContext() {
        // Extract context from current URL and page
        const url = window.location.pathname;
        const urlParts = url.split('/');
        
        // Extract plan_id from URL patterns like /plans/<plan_id>/...
        const planIndex = urlParts.indexOf('plans');
        if (planIndex !== -1 && urlParts[planIndex + 1]) {
            this.context.plan_id = urlParts[planIndex + 1];
        }
        
        // Extract company_id from URL patterns like /companies/<company_id>/...
        const companyIndex = urlParts.indexOf('companies');
        if (companyIndex !== -1 && urlParts[companyIndex + 1]) {
            this.context.company_id = urlParts[companyIndex + 1];
        }
        
        // Detect page type and additional context
        if (url.includes('/okr-global')) {
            this.context.page_type = 'okr-global';
            this.context.okr_level = 'global';
            this.detectOKRContext();
        } else if (url.includes('/okr-area')) {
            this.context.page_type = 'okr-area';
            this.context.okr_level = 'area';
            this.detectOKRContext();
        } else if (url.includes('/projects')) {
            this.context.page_type = 'projects';
            this.detectProjectContext();
        }
        
        // Try to get company_id from global variables if not found in URL
        if (!this.context.company_id) {
            if (typeof window.companyId !== 'undefined') {
                this.context.company_id = window.companyId;
            } else if (typeof window.company !== 'undefined' && window.company.id) {
                this.context.company_id = window.company.id;
            }
        }
        
        this.log('Context detected:', this.context);
    }
    
    detectOKRContext() {
        // Try to detect which OKR is currently being viewed/edited
        // This could be enhanced based on the specific page structure
        
        // Look for data attributes or form fields that might contain OKR IDs
        const okrForms = document.querySelectorAll('form[data-okr-id]');
        if (okrForms.length > 0) {
            this.context.okr_id = okrForms[0].getAttribute('data-okr-id');
        }
        
        // Look for selected OKR in any visible selects
        const okrSelects = document.querySelectorAll('select[name*="okr"]');
        for (const select of okrSelects) {
            if (select.value) {
                this.context.okr_id = select.value;
                break;
            }
        }
    }
    
    detectProjectContext() {
        // Try to detect which project is currently being viewed
        
        // Look for data attributes or form fields that might contain project IDs
        const projectForms = document.querySelectorAll('form[data-project-id]');
        if (projectForms.length > 0) {
            this.context.project_id = projectForms[0].getAttribute('data-project-id');
        }
        
        // Look for project ID in URL
        const url = window.location.pathname;
        const projectMatch = url.match(/\/projects\/(\d+)/);
        if (projectMatch) {
            this.context.project_id = projectMatch[1];
        }
    }
    
    createButton() {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = this.options.buttonClass;
        button.innerHTML = this.options.buttonText;
        button.onclick = () => this.openIndicatorForm();
        
        // Add the button to the specified container or auto-detect a good location
        const container = this.findContainer();
        if (container) {
            container.appendChild(button);
            this.log('Button added to container:', container);
        } else {
            this.log('Warning: No suitable container found for button');
        }
    }
    
    findContainer() {
        // If a specific container is specified, use it
        if (this.options.containerId) {
            return document.getElementById(this.options.containerId);
        }
        
        // Auto-detect good locations based on page type
        const selectors = [
            '.card-header .card-actions',
            '.interview-actions',
            '.section-status-controls',
            '.form-actions',
            '.button-group',
            '.actions',
            '.toolbar',
            '.header-actions'
        ];
        
        for (const selector of selectors) {
            const element = document.querySelector(selector);
            if (element) {
                return element;
            }
        }
        
        // Fallback: try to find any action container
        const fallbackSelectors = [
            '[class*="action"]',
            '[class*="button"]',
            '[class*="toolbar"]'
        ];
        
        for (const selector of fallbackSelectors) {
            const element = document.querySelector(selector);
            if (element && element.tagName !== 'BUTTON') {
                return element;
            }
        }
        
        // Last resort: create a container
        const body = document.querySelector('body');
        if (body) {
            const container = document.createElement('div');
            container.className = 'unified-indicator-container';
            container.style.cssText = 'position: fixed; top: 20px; right: 20px; z-index: 1000;';
            body.appendChild(container);
            return container;
        }
        
        return null;
    }
    
    openIndicatorForm() {
        this.log('Opening indicator form with context:', this.context);
        
        if (!this.context.company_id) {
            alert('Erro: Não foi possível identificar a empresa. Verifique se você está na página correta.');
            return;
        }
        
        // Build URL for the indicator form
        let formUrl = `/grv/company/${this.context.company_id}/indicators/form`;
        
        // Add query parameters for pre-filling
        const params = new URLSearchParams();
        
        if (this.context.plan_id) {
            params.set('plan_id', this.context.plan_id);
        }
        
        if (this.context.okr_id) {
            params.set('okr_id', this.context.okr_id);
        }
        
        if (this.context.okr_level) {
            params.set('okr_level', this.context.okr_level);
        }
        
        if (this.context.project_id) {
            params.set('project_id', this.context.project_id);
        }
        
        if (this.context.page_type) {
            params.set('page_type', this.context.page_type);
        }
        
        if (params.toString()) {
            formUrl += '?' + params.toString();
        }
        
        this.log('Opening form URL:', formUrl);
        
        // Open the form in a popup window
        const popup = window.open(
            formUrl,
            'indicatorForm',
            'width=800,height=900,scrollbars=yes,resizable=yes'
        );
        
        if (popup) {
            popup.focus();
        } else {
            // Fallback: navigate to the form in the same window
            window.location.href = formUrl;
        }
    }
    
    log(...args) {
        if (this.options.debug) {
            console.log('[UnifiedIndicatorButton]', ...args);
        }
    }
}

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Only initialize on pages that need the indicator button
    const shouldInitialize = 
        window.location.pathname.includes('/okr-global') ||
        window.location.pathname.includes('/okr-area') ||
        window.location.pathname.includes('/projects');
    
    if (shouldInitialize) {
        // Initialize with debug mode based on environment
        const debug = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
        
        window.unifiedIndicatorButton = new UnifiedIndicatorButton({
            debug: debug
        });
    }
});

// Export for manual initialization if needed
if (typeof module !== 'undefined' && module.exports) {
    module.exports = UnifiedIndicatorButton;
} else {
    window.UnifiedIndicatorButton = UnifiedIndicatorButton;
}
