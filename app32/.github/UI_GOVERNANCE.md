# Governança de Interface de Usuário (UI)

Padrões obrigatórios para o sistema de referência de UI (versão 2).

## Sistema de Referência

- **Formato:** `XXX-XXX` (Página-Elemento), apenas numérico.
- **Páginas (`XXX`):** códigos únicos, sequenciais (001, 002, ...), registrados em `ui_pages_v2`.
- **Elementos (`XXX`):** sequenciais dentro da página (001, 002, ...), armazenados em `ui_elements_v2`.
- `data-ref` no HTML é normalizado para 3 dígitos na UI (ex.: `data-ref="5"` → `005`).

## Como Registrar

1) **Página**  
```python
from services.ui_reference_service_v2 import UIReferenceServiceV2
UIReferenceServiceV2.register_page(
    page_name="Minha Página",
    template_file="minha_pagina.html",
    page_route="/minha/pagina"
)
```

2) **Elementos**  
- Marque os elementos interativos com `data-ref="NNN"`.
- Para sincronizar com o banco (opcional): `python scripts/catalog_ui_elements.py --verbose`

## Ferramentas
- **Overlay de códigos:** `Ctrl + Shift + Y`
- **Cópia rápida:** `Ctrl + click` copia `XXX-XXX`

## Checklist de PR (UI)
- [ ] Novos templates registrados em `ui_pages_v2` (código numérico).
- [ ] Elementos interativos têm `data-ref` e foram sincronizados em `ui_elements_v2`.
- [ ] Formato `XXX-XXX` respeitado (sem alfanuméricos).
- [ ] `Ctrl+Click` testado nos novos elementos.
