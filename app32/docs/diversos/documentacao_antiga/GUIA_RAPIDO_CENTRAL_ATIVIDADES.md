# Guia Rápido - Central de Gestão de Atividades

## 🎯 O que é?

Uma visualização **unificada** de todas as suas atividades:
- ✅ Atividades dos Projetos
- ✅ Instâncias dos Processos

Tudo em um só lugar! Com filtros poderosos e visualização em lista ou calendário.

---

## 📍 Como Acessar

**GRV** → **Gestão da Rotina** → **Gestão de Atividades / Calendário**

URL: `http://127.0.0.1:5002/grv/company/5/routine/activities`

---

## 📊 Entendendo a Tela

### Topo: Estatísticas
5 cards com métricas em tempo real:
- **Total de Atividades**: Quantidade consolidada
- **Projetos**: Atividades de projetos
- **Processos**: Instâncias de processos
- **Em Andamento**: Ativas no momento
- **Vencendo Hoje**: Com prazo para hoje

### Abas de Visualização

**📋 Lista**: Cards com informações detalhadas  
**📅 Calendário**: Visualização temporal com cores

---

## 🔍 Usando os Filtros

### Filtros Disponíveis:

1. **Tipo**
   - Todos
   - Atividades de Projetos
   - Instâncias de Processos

2. **Status/Estágio**
   - Pendente
   - Em Andamento
   - Executando
   - Aguardando
   - Concluído

3. **Pessoa**
   - Filtra por **responsável** (nível estratégico)
   - OU por **executor** (nível operacional)

4. **Projeto**
   - Vê somente atividades de um projeto específico

5. **Processo**
   - Vê somente instâncias de um processo específico

6. **Buscar**
   - Campo de texto livre no título

### Dicas:
- ✅ Combine filtros para busca precisa
- ✅ Filtros atualizam lista E calendário
- ✅ Estatísticas recalculam automaticamente
- ✅ Limpe filtros clicando em "Todos" / "Todas"

---

## 📋 Visualização em Lista

### Layout em Duas Colunas

A lista é dividida em **duas colunas lado a lado**:

**📋 Esquerda: Instâncias de Processos (ROTINA)**
- Mostra quantidade de itens no topo
- Representa o peso operacional/rotina
- Cards amarelos de processos
- Foco: executores e horas

**🎯 Direita: Atividades de Projetos (ESTRATÉGIA)**
- Mostra quantidade de itens no topo
- Representa o peso estratégico/projetos
- Cards azuis de projetos
- Foco: responsáveis e prazos

### Como Usar:

1. **Veja o balanceamento**
   - Compare quantidade esquerda vs direita
   - Identifique se rotina está sobrecarregada
   - Ou se projetos precisam de mais atenção

2. **Navegue pelas colunas**
   - Role independentemente em cada coluna
   - Cards mostram informações específicas

3. **Veja informações rápidas**
   - **Processos**: Código, prazo, executores, horas (previsto/realizado)
   - **Projetos**: Código, prazo, responsável, estágio

4. **Clique para gerenciar**
   - Processo → Abre gerenciamento da instância
   - Projeto → Abre Kanban do projeto
   - Mantém seus filtros para quando voltar

---

## 📅 Visualização em Calendário

### Como Usar:

1. **Clique na aba "📅 Calendário"**

2. **Navegue pelo calendário**
   - Botões: ◀ Anterior | Hoje | Próximo ▶
   - Título mostra mês/semana/dia atual

3. **Mude a visualização**
   - **Mês**: Visão geral mensal
   - **Semana**: Detalhes da semana
   - **Dia**: Foco no dia
   - **Lista**: Eventos em lista temporal

4. **Identifique por cor**
   - **Azul**: Atividades de projetos
   - **Laranja**: Instâncias de processos

5. **Clique em um evento**
   - Abre gerenciamento da atividade
   - Ao voltar, calendário permanece

---

## 🔄 Navegação Contextual

### O que é?

Quando você clica em uma atividade e depois volta, o sistema:
- ✅ Restaura a aba que você estava (Lista ou Calendário)
- ✅ Restaura todos os filtros
- ✅ Mantém seu termo de busca
- ✅ Você continua de onde parou!

### Como funciona?

**Automático!** Você não precisa fazer nada. O sistema:
1. Salva seu estado ao clicar
2. Abre a página de edição
3. Ao voltar (botão "← Voltar"), restaura tudo

---

## 💡 Exemplos Práticos

### Exemplo 1: Gestor de Projetos

**Objetivo**: Ver todas as atividades do Projeto "Modernização"

**Passos**:
1. Filtra **Projeto**: Modernização
2. Vê 15 atividades do projeto
3. Clica em uma para editar
4. Volta → Continua vendo as 15 atividades filtradas

### Exemplo 2: Colaborador

**Objetivo**: Ver o que tenho para fazer esta semana

**Passos**:
1. Filtra **Pessoa**: Meu Nome
2. Clica em **📅 Calendário**
3. Muda para visualização **Semana**
4. Vê eventos azuis (projetos) e laranjas (processos)
5. Organiza prioridades

### Exemplo 3: Gerente de Processos

**Objetivo**: Acompanhar processos em andamento

**Passos**:
1. Filtra **Tipo**: Instâncias de Processos
2. Filtra **Status**: Em Andamento
3. Vê 8 processos ativos
4. Clica em um para ver detalhes
5. Registra horas
6. Volta → Continua vendo os 8 processos

### Exemplo 4: Dashboard Executivo

**Objetivo**: Ver tudo vencendo hoje

**Passos**:
1. Olha estatística **"Vencendo Hoje": 3**
2. Não aplica filtro (vê tudo)
3. Aba **Lista**: Busca visualmente por ⏱️
4. Ou aba **Calendário**: Eventos de hoje destacados
5. Prioriza ações

---

## 🎨 Identificação Visual

### Tipos de Atividade:
| Tipo | Badge | Cor |
|------|-------|-----|
| Atividade de Projeto | PROJETO | Azul claro |
| Instância de Processo | PROCESSO | Amarelo claro |

### Status/Estágios:
| Status | Cor |
|--------|-----|
| Pendente / Caixa de Entrada | Cinza |
| Em Andamento / Executando | Azul |
| Aguardando | Amarelo |
| Concluído | Verde |
| Cancelado / Suspenso | Vermelho |

### No Calendário:
| Tipo | Cor do Evento |
|------|---------------|
| Projeto | Azul forte |
| Processo | Laranja forte |

---

## ⚡ Atalhos e Dicas

1. **Filtrar rapidamente**: Clique nos selects, não precisa rolar muito
2. **Limpar filtros**: Selecione "Todos" em cada filtro
3. **Trocar de aba**: Clique nas abas no topo
4. **Voltar de atividade**: Sempre use o botão "← Voltar" para manter contexto
5. **Ver vencimentos**: Use aba Calendário na visualização Semana
6. **Buscar rápido**: Digite parte do título no campo Buscar

---

## ❓ Perguntas Frequentes

**P: Como vejo só minhas atividades?**  
R: Filtre **Pessoa** e selecione seu nome.

**P: Posso combinar filtros?**  
R: Sim! Todos os filtros podem ser combinados.

**P: Por que algumas atividades não têm responsável?**  
R: Instâncias de processo não têm responsável único, só executores.

**P: Posso editar direto da lista?**  
R: Não. Clique na atividade para abrir a página de gerenciamento completa.

**P: O calendário mostra atividades sem prazo?**  
R: Não. Apenas atividades com `due_date` aparecem no calendário.

**P: Como sei se é projeto ou processo?**  
R: Veja o badge colorido (azul = projeto, amarelo = processo)

**P: Posso exportar os dados?**  
R: Ainda não. Funcionalidade futura.

---

## 🚀 Fluxo de Uso Recomendado

### Rotina Diária:
```
1. Acessar Central de Atividades
2. Filtrar por: Pessoa = Você
3. Ver estatística "Vencendo Hoje"
4. Abrir aba Calendário (visualização Dia)
5. Clicar nas atividades para gerenciar
6. Voltar e filtros permanecem
```

### Reunião Semanal de Status:
```
1. Acessar Central de Atividades
2. Filtrar por: Status = Em Andamento
3. Aba Calendário (visualização Semana)
4. Discutir cada evento colorido
5. Clicar para ver detalhes
6. Voltar mantém contexto da reunião
```

### Planejamento Mensal:
```
1. Acessar Central de Atividades
2. Aba Calendário (visualização Mês)
3. Ver distribuição de atividades
4. Identificar gargalos (dias cheios)
5. Reorganizar prioridades
```

---

## ✅ Sistema Pronto!

A **Central de Gestão de Atividades** está 100% funcional e integrada com:
- ✅ Projetos GRV
- ✅ Processos GRV
- ✅ Sistema de colaboradores
- ✅ Navegação do sistema

**Acesse agora**: `http://127.0.0.1:5002/grv/company/5/routine/activities`

**Aproveite** a visão consolidada e produtiva! 🎉

