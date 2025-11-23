# Governança de Interface de Usuário (UI)

Este documento define os padrões e processos obrigatórios para o desenvolvimento e manutenção da interface de usuário do sistema Gestão Versus.

## Sistema de Referência de UI (UI Reference System)

Implementamos um sistema de endereçamento único para todas as páginas e elementos interativos do sistema. O objetivo é facilitar a comunicação entre usuários, suporte e desenvolvimento, além de permitir testes automatizados mais robustos.

### Formato dos Códigos

O sistema utiliza um formato de dois blocos de dois caracteres alfanuméricos:

**`XX-XX`** (Página-Elemento)

Exemplos:
- `01-01`: Página 01 (Login), Elemento 01 (Botão Entrar)
- `A5-B2`: Página A5 (PEV Projetos), Elemento B2 (Tabela de Projetos)

#### Regras de Numeração

1. **Páginas (Primeiro par `XX`)**:
   - Sequencial: `01` a `99`, depois `A0` a `ZZ`.
   - Único em todo o sistema.
   - Gerado automaticamente pelo banco de dados/serviço.

2. **Elementos (Segundo par `XX`)**:
   - Sequencial dentro da página: `01` a `99`, depois `A0` a `ZZ`.
   - Único dentro da página.

### Processo de Desenvolvimento

#### 1. Criando Nova Página

Ao criar uma nova página HTML (`.html`):

1. **Registrar no Banco**: Use o script ou serviço para criar a página e obter o próximo código disponível.
   ```python
   # Exemplo via shell
   from services.ui_reference_service import create_page
   code = create_page(page_code=get_next_page_code(), page_name="Nova Página", template_file="nova_pagina.html")
   print(code) # Ex: 'A9'
   ```

2. **Adicionar ao Template**: O `base.html` já injeta o código automaticamente se passado pelo backend. No seu controller/rota, certifique-se de passar `page_code` para o template.
   ```python
   return render_template('nova_pagina.html', page_code='A9', ...)
   ```

#### 2. Adicionando Elementos

Ao adicionar botões, campos, tabelas ou cards importantes:

1. **Obter Código**: Use o serviço para reservar o código.
2. **Adicionar Atributo**: Adicione `data-ref="XX"` ao elemento HTML.
   ```html
   <button class="btn btn-primary" data-ref="01">Salvar</button>
   ```

### Ferramentas de Apoio

#### Modo Debug (Visualização)
- Pressione `Ctrl + Shift + R` em qualquer página para ativar o modo de visualização dos códigos.
- Todos os elementos com `data-ref` serão destacados.

#### Cópia Rápida
- Segure `Ctrl` e clique em qualquer elemento com referência para copiar o código completo (ex: `A9-01`) para a área de transferência.

### Manutenção

- **Script de Catalogação**: `scripts/catalog_ui_elements.py` pode ser rodado periodicamente para detectar novos elementos e páginas que não foram registrados (embora o ideal seja registrar na criação).
- **Auditoria**: Todas as alterações nas tabelas `ui_pages` e `ui_elements` são logadas na tabela `ui_audit_log`.

---

## Checklist para Pull Requests (UI)

Todo PR que envolve alterações de interface deve conter:

- [ ] Novos arquivos `.html` foram registrados na tabela `ui_pages`.
- [ ] Novos elementos interativos (botões, inputs) possuem atributo `data-ref`.
- [ ] Códigos de referência foram gerados sequencialmente e não conflitam.
- [ ] Funcionalidade de `Ctrl+Click` testada nos novos elementos.
