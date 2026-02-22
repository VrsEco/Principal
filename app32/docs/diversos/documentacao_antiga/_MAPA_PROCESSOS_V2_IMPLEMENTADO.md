# Mapa de Processos - Versão 2 (MP-2) Implementado

## 📋 Resumo

Foi implementado com sucesso um segundo modelo de relatório do Mapa de Processos (MP-2) mantendo o modelo original intacto. Agora existem duas opções de visualização e exportação do mapa de processos organizacionais.

---

## ✅ O Que Foi Implementado

### 1. Novo Template HTML - Layout Profissional em Tabela
**Arquivo:** `templates/pdf/grv_process_map_v2.html`

**Características do MP-2:**
- ✨ **Formato Paisagem (Landscape)**: Otimizado para aproveitamento de espaço horizontal
- 📊 **Layout em Tabela**: Apresentação estruturada com colunas organizadas
- 🎨 **Design Corporativo**: Cabeçalho profissional com título, subtítulo e metadados
- 📈 **Cards de Resumo**: Totalizadores visuais (Áreas, Macroprocessos, Processos)
- 🏷️ **Status com Badges**: Indicadores coloridos para Estruturação e Desempenho
- 📝 **Legendas**: Explicação dos status ao final do documento
- 🎯 **Hierarquia Visual**: Separação clara entre Áreas → Macroprocessos → Processos

**Colunas da Tabela:**
1. Macroprocesso (18%)
2. Código (12%)
3. Processo (22%)
4. Responsável (14%)
5. Estruturação (14%)
6. Desempenho (14%)

### 2. Nova Rota de Geração de PDF
**Rota:** `/grv/company/<company_id>/process/map/pdf2`
**Função:** `grv_process_map_pdf2()`
**Arquivo:** `modules/grv/__init__.py` (linhas 499-671)

**Características Técnicas:**
- Usa Playwright para geração do PDF
- Formato A4 Landscape
- Margens: 12mm (top), 15mm (bottom), 10mm (left/right)
- Header e Footer personalizados
- Print color adjustment para cores exatas
- Nome do arquivo: `mapa-processos-v2-{nome-empresa}.pdf`

### 3. Interface com Novos Botões
**Arquivo:** `templates/grv_process_map.html` (linhas 79-85)

**Botões Adicionados:**
- 👁️ **Visualizar MP-2**: Abre o PDF em nova aba
- 📄 **Exportar PDF MP-2**: Faz download direto do PDF

**Estilo dos Botões:**
- Botão "Visualizar MP-2" com destaque verde (#10b981)
- Separador visual entre modelos MP-1 e MP-2
- Layout responsivo com flex-wrap

### 4. JavaScript para Funcionalidades
**Arquivo:** `static/js/grv-process-map.js` (linhas 760-761, 945-985)

**Funcionalidades:**
- Event listener para visualização em nova aba
- Event listener para download com fetch API
- Mensagens de sucesso/erro
- Tratamento de bloqueadores de pop-up

---

## 🔄 Diferenças entre MP-1 e MP-2

| Característica | MP-1 (Original) | MP-2 (Novo) |
|----------------|-----------------|-------------|
| **Orientação** | Retrato (Portrait) | Paisagem (Landscape) |
| **Layout** | Cards em Grid horizontal | **Layout Hierárquico Visual** |
| **Áreas** | Cabeçalho horizontal | **Barra lateral vertical rotacionada** |
| **Macroprocessos** | Lista sequencial | **Grid 3 por linha (retângulos verticais)** |
| **Processos** | Cards grandes individuais | **Grid 2 por linha dentro de cada macro** |
| **Badges** | Integrados nos cards | **Quadrados coloridos na lateral esquerda** |
| **Estilo** | Moderno, espaçado | Compacto, hierárquico visual |
| **Densidade** | Baixa (1-2 macros/página) | **Alta (3-6 macros/página)** |
| **Fonte Principal** | Segoe UI, Inter | Calibri, Segoe UI |
| **Legenda** | Não possui | Possui ao final |
| **Melhor Para** | Apresentações visuais | **Visão geral executiva, relatórios compactos** |

---

## 🎯 Como Usar

### Acessando o Mapa de Processos
1. Navegue até: `http://127.0.0.1:5002/grv/company/5/process/map`
2. Na aba "Visualizar Mapa", você verá 4 botões:

**Modelo Original (MP-1):**
- 👁️ Visualizar
- 📝 Exportar PDF

**Modelo Novo (MP-2):**
- 👁️ Visualizar MP-2
- 📄 Exportar PDF MP-2

### Visualizando o MP-2
- Clique em **"👁️ Visualizar MP-2"**
- O PDF será aberto em nova aba
- Formato paisagem, ideal para impressão

### Exportando o MP-2
- Clique em **"📄 Exportar PDF MP-2"**
- O arquivo será baixado automaticamente
- Nome do arquivo: `mapa-processos-v2-{timestamp}.pdf`

---

## 📁 Arquivos Criados/Modificados

### ✨ Novos Arquivos
1. `templates/pdf/grv_process_map_v2.html` - Template do MP-2
2. `_MAPA_PROCESSOS_V2_IMPLEMENTADO.md` - Esta documentação

### 📝 Arquivos Modificados
1. `modules/grv/__init__.py` - Nova rota `grv_process_map_pdf2()`
2. `templates/grv_process_map.html` - Adicionados botões MP-2
3. `static/js/grv-process-map.js` - Event listeners para MP-2

---

## 🎨 Paleta de Cores do MP-2

**Cores Primárias:**
- Azul Corporativo: `#1e40af` (títulos, bordas)
- Cinza Escuro: `#1e293b` (texto principal)
- Cinza Médio: `#475569` (texto secundário)
- Cinza Claro: `#64748b` (metadados)

**Status - Estruturação:**
- 🟢 Estabilizado: `#d1fae5` (fundo) / `#065f46` (texto)
- 🟡 Em Andamento: `#fef3c7` (fundo) / `#92400e` (texto)
- ⚪ Fora de Escopo: `#f1f5f9` (fundo) / `#475569` (texto)

**Status - Desempenho:**
- 🟢 Satisfatório: `#d1fae5` (fundo) / `#065f46` (texto)
- 🟡 Abaixo: `#fef3c7` (fundo) / `#92400e` (texto)
- 🔴 Crítico: `#fee2e2` (fundo) / `#991b1b` (texto)
- ⚪ Fora de Escopo: `#f1f5f9` (fundo) / `#475569` (texto)

---

## 🔧 Requisitos Técnicos

- Python 3.x
- Flask
- Playwright (`pip install playwright`)
- Chromium instalado (`playwright install chromium`)

---

## 📊 Estrutura do Template MP-2 (Layout Hierárquico Visual)

```
┌──────────┬──────────────────────────────────────────────────────────┐
│          │ [CABEÇALHO: Mapa de Processos Organizacionais]           │
│          │ [RESUMO: Cards com totais]                               │
│          ├──────────────────────────────────────────────────────────┤
│          │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│          │  │ AB.C.1.1     │  │ AB.C.1.2     │  │ AB.C.1.3     │  │
│  AB.C.1  │  │ Planejamento │  │ Gestão Fin.  │  │ Marketing    │  │
│          │  │              │  │              │  │              │  │
│ GEREN-   │  │ ┌──┐  ┌──┐  │  │ ┌──┐  ┌──┐  │  │ ┌──┐  ┌──┐  │  │
│ CIAIS    │  │ │🔴│P1││🟢│P2│  │ │🟡│P1││🟢│P2│  │ │🔴│P1││🟡│P2│  │
│          │  │ │🟡│  ││🟢│  │  │ │🔴│  ││🟢│  │  │ │🟢│  ││🟡│  │  │
│          │  │ └──┘  └──┘  │  │ └──┘  └──┘  │  │ └──┘  └──┘  │  │
│ (VERTICAL│  │              │  │              │  │              │  │
│  ROTAC.) │  │ Dono: João   │  │ Dono: Maria  │  │ Dono: Pedro  │  │
│          │  └──────────────┘  └──────────────┘  └──────────────┘  │
├──────────┼──────────────────────────────────────────────────────────┤
│          │  ┌──────────────┐  ┌──────────────┐                    │
│  AB.C.2  │  │ AB.C.2.1     │  │ AB.C.2.2     │                    │
│          │  │ Atendimento  │  │ Logística    │                    │
│ OPERA-   │  │              │  │              │                    │
│ ÇÕES     │  │ ┌──┐  ┌──┐  │  │ ┌──┐         │                    │
│          │  │ │🟢│P1││🟢│P2│  │ │🟡│P1│       │                    │
│          │  │ │🟢│  ││🔴│  │  │ │🟢│  │       │                    │
│          │  │ └──┘  └──┘  │  │ └──┘         │                    │
│ (VERTICAL│  │              │  │              │                    │
│  ROTAC.) │  │ Dono: Ana    │  │ Dono: Carlos │                    │
│          │  └──────────────┘  └──────────────┘                    │
└──────────┴──────────────────────────────────────────────────────────┘
[LEGENDA: Cores de Estruturação e Desempenho]
```

**Hierarquia Visual:**
1. **Áreas**: Barra lateral vertical (texto rotacionado) - 1 por linha
2. **Macroprocessos**: Retângulos verticais - **3 por linha**
   - Nome + Código no topo
   - Dono do Processo no rodapé
3. **Processos**: Cards menores - **2 por linha dentro de cada macro**
   - Nome + Código centralizados
   - 2 badges coloridos à esquerda (🔴🟡🟢)

---

## ✅ Status da Implementação

- ✅ Template HTML MP-2 criado
- ✅ Rota de geração PDF implementada
- ✅ Botões adicionados na interface
- ✅ JavaScript configurado
- ✅ Modelo original (MP-1) mantido intacto
- ✅ Documentação criada

---

## 🎯 Próximos Passos (Opcional)

1. **Personalização**: Ajustar cores/layout conforme PDF de referência específico
2. **Filtros**: Adicionar opções de filtro por área/status
3. **Exportação**: Adicionar formatos Excel/Word
4. **Comparação**: Página para comparar MP-1 vs MP-2 lado a lado
5. **Histórico**: Versionamento de mapas de processos

---

## 📞 Suporte

Para ajustes no template MP-2, edite:
- `templates/pdf/grv_process_map_v2.html` - Layout e estilos
- `modules/grv/__init__.py` - Lógica de geração
- `static/js/grv-process-map.js` - Comportamento dos botões

---

**Implementado em:** 13/10/2025  
**Status:** ✅ Completo e Funcional

