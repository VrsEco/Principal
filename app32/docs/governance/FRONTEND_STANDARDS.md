# 🎨 Padrões Frontend (v2.0)

**Última Atualização:** 17/02/2026  
**Versão:** 2.0  
**Status:** ✅ Obrigatório

---

## 🎯 Stack Frontend v2.0
*   **TailwindCSS:** Para utilitários de design e responsividade.
*   **Jinja2:** Para renderização server-side.
*   **Vanilla JS:** Para interações ricas.
*   **Jinja2 + JS:** Cuidado extremo ao injetar variáveis Jinja em scripts JS. Sempre verifique o fechamento correto das chaves `}}`. Ex: `var id = {{ obj.id }}`.


## 📐 Regras Visuais (Preservadas)
1.  **Z-Index de Modais:** Fixado em **25.000**.
2.  **Micro-animações:** Hover em botões deve ser sutil (escala 1.02 ou leve mudança de contraste).
3.  **CSS de Impressão:** Relatórios devem manter o `@media print` configurado para ocultar sidebars e menus.

## 🏗️ Estrutura de Componentes
Ao criar novos layouts com Tailwind:
*   Não use cores saturadas de fundo (vermelhos/azuis puros).
*   Use a paleta institucional: Slate/Gray para textos e fundos.
*   **Modais:** Veja `MODAL_STANDARDS.md`.

---

**Nota:** A migração para Tailwind não autoriza o abandono dos scripts de auxílio em `static/js/`.
