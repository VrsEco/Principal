# 📐 Padrão de Modais (v2.0)

**Última Atualização:** 17/02/2026  
**Versão:** 2.0  
**Status:** ✅ Obrigatório

---

## 🎯 Objetivo
Manter a integridade visual do Gestão Versus durante a evolução para tecnologias modernas.

## 📐 Hierarquia de Z-Index (PRESERVADA)
Para evitar que elementos de IA ou popups fiquam escondidos:

| Camada | Z-Index |
|--------|---------|
| Conteúdo | 1-99 |
| Dropdowns | 100-999 |
| Overlays / Sidebars | 1.000-9.999 |
| **Modais Padrão** | **25.000** |
| Alerts Críticos | 30.000 |

## 🛠️ Implementação Técnica
Com a adoção do **TailwindCSS**, a estrutura base deve ser:

```html
<div class="fixed inset-0 z-[25000] flex items-center justify-center bg-black/60">
    <div class="bg-white p-8 rounded-2xl shadow-2xl max-w-lg w-full">
        <!-- Conteúdo via Jinja2 -->
    </div>
</div>
```

### Regras de Ouro:
1.  **Z-index 25.000** é absoluto para modais.
2.  **Micro-animações:** Use transições suaves (`transition-opacity`, `duration-300`) para a entrada do modal.
3.  **Acessibilidade:** ESC deve sempre fechar o modal (implementado via `modal-system.js`).

---

**Relacionado:** `FRONTEND_STANDARDS.md`
