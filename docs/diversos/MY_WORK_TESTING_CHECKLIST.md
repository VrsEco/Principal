# ✅ Checklist de Testes - My Work

## 🎯 Guia Completo de Testes da Interface

---

## 🚀 **PASSO 1: Iniciar a Aplicação**

### Reiniciar Docker (Recomendado)
```bash
# Execute este arquivo:
REINICIAR_DOCKER_MY_WORK.bat
```

**OU** manualmente:
```bash
docker-compose -f docker-compose.dev.yml down
docker-compose -f docker-compose.dev.yml up -d --build
```

### Acessar Aplicação
```
http://127.0.0.1:5003/my-work-demo
```

⚠️ **IMPORTANTE:** Você precisa estar **LOGADO** primeiro!

---

## ✅ **PASSO 2: Testar Navegação das Abas**

### **Aba "👤 Minhas Atividades"**
- [ ] Aba está ativa por padrão (azul)
- [ ] Título mostra: "Minhas Atividades"
- [ ] Subtítulo: "Gerencie sua rotina e acompanhe seu desempenho"
- [ ] Contador mostra: "17" (ou outro número)
- [ ] Team Overview está **ESCONDIDO**

### **Aba "👥 Minha Equipe"**
- [ ] Clicar na aba "Minha Equipe"
- [ ] Aba fica ativa (azul)
- [ ] Título muda para: "Atividades da Equipe"
- [ ] Subtítulo muda para: "Acompanhe o desempenho e progresso da sua equipe"
- [ ] Contador mostra: "45" (ou outro número)
- [ ] **Team Overview APARECE** com 3 cards:
  - [ ] 📊 Distribuição de Carga (3 membros)
  - [ ] ⚠️ Alertas (3 alertas)
  - [ ] 📈 Performance da Equipe

### **Aba "🏢 Empresa"**
- [ ] Clicar na aba "Empresa"
- [ ] Aba fica ativa (azul)
- [ ] Título muda para: "Atividades da Empresa"
- [ ] Subtítulo muda para: "Visão estratégica de todas as atividades organizacionais"
- [ ] Contador mostra: "180" (ou outro número)
- [ ] Team Overview está **ESCONDIDO**

---

## ✅ **PASSO 3: Testar Dashboard Cards**

- [ ] 4 cards aparecem:
  - [ ] 🟡 Pendentes (12)
  - [ ] 🔵 Em Andamento (3)
  - [ ] 🔴 Atrasadas (2)
  - [ ] 🟢 Concluídas (45)
- [ ] Cards têm hover effect (levantam ao passar mouse)
- [ ] Ícones estão visíveis
- [ ] Cores corretas
- [ ] Tendências aparecem (↑ ↓ →)

---

## ✅ **PASSO 4: Testar Filtros**

### **Abas de Filtro:**
- [ ] Clicar em "Todas" → Fica azul
- [ ] Clicar em "Hoje" → Fica azul, outras ficam cinza
- [ ] Clicar em "Esta Semana" → Fica azul
- [ ] Clicar em "Atrasadas" → Fica azul
- [ ] Contadores nas abas estão visíveis

### **Busca:**
- [ ] Digitar "proposta" na busca
- [ ] Lista filtra em tempo real
- [ ] Limpar busca → Lista volta ao normal

### **Ordenação:**
- [ ] Mudar dropdown para "Por Prioridade"
- [ ] Lista reordena
- [ ] Mudar para "Por Status"
- [ ] Lista reordena

---

## ✅ **PASSO 5: Testar Botões das Atividades**

### **Botão "⏱️ + Horas":**
- [ ] Clicar no botão azul "⏱️ + Horas"
- [ ] Modal abre com título "⏱️ Adicionar Horas Trabalhadas"
- [ ] Info da atividade aparece no topo
- [ ] Data está preenchida com hoje
- [ ] Digitar "2.5" em horas
- [ ] Resumo calcula: "Total após adição: 2.5h"
- [ ] Clicar em "Registrar Horas"
- [ ] Modal fecha
- [ ] Mensagem de sucesso aparece: "✅ 2.5h registradas com sucesso!"

### **Botão "💬 Comentar":**
- [ ] Clicar no botão amarelo "💬 Comentar"
- [ ] Modal abre com título "💬 Adicionar Comentário / Anotação"
- [ ] Info da atividade aparece
- [ ] Dropdown de tipo de comentário funciona
- [ ] Digitar comentário
- [ ] Marcar "Comentário privado"
- [ ] Clicar em "Adicionar Comentário"
- [ ] Modal fecha
- [ ] Mensagem de sucesso: "✅ Comentário adicionado com sucesso!"

### **Botão "✅ Finalizar":**
- [ ] Clicar no botão verde "✅ Finalizar"
- [ ] Modal abre com alerta verde
- [ ] Título: "✅ Finalizar Atividade"
- [ ] Mostra ícone de check grande
- [ ] Texto: "Você está prestes a finalizar esta atividade"
- [ ] Campo de comentário final (opcional)
- [ ] Resumo mostra mudança de status
- [ ] Clicar em "Confirmar Finalização"
- [ ] Modal fecha
- [ ] Mensagem: "✅ Atividade finalizada com sucesso!"
- [ ] **Atividade some da lista com animação**

### **Fechar Modal:**
- [ ] Clicar no X (canto superior direito)
- [ ] Modal fecha
- [ ] Clicar fora do modal (no overlay escuro)
- [ ] Modal fecha

---

## ✅ **PASSO 6: Testar Sidebar de Horas**

### **Aba "Hoje":**
- [ ] Aba "Hoje" está ativa por padrão
- [ ] 3 cards de resumo aparecem:
  - [ ] Capacidade: 8h
  - [ ] Previsto: 6h 30min (azul)
  - [ ] Realizado: 4h 15min (verde)
- [ ] Barra de progresso mostra 53% verde + azul
- [ ] Legenda: Realizado | Previsto | Livre
- [ ] Detalhamento mostra:
  - [ ] 📁 Atividades de Projetos (4h previsto, 2h 45min realizado)
  - [ ] ⚙️ Instâncias de Processos (2h 30min previsto, 1h 30min realizado)
  - [ ] 📋 Outros / Disponível (1h 30min)

### **Aba "Semana":**
- [ ] Clicar na aba "Semana"
- [ ] Aba fica ativa (azul)
- [ ] Visão do dia **ESCONDE**
- [ ] Visão da semana **APARECE**
- [ ] 3 cards de resumo:
  - [ ] Capacidade: 40h
  - [ ] Previsto: 32h
  - [ ] Realizado: 18h 30min
- [ ] **Gráfico de barras por dia** aparece:
  - [ ] 5 barras (S T Q Q S)
  - [ ] Barras empilhadas (verde + azul)
  - [ ] Dia atual (Sexta) tem badge "HOJE" e borda azul
  - [ ] Valores aparecem ao passar mouse
- [ ] Detalhamento semanal mostra:
  - [ ] 📁 Projetos: 20h previsto, 12h realizado
  - [ ] ⚙️ Processos: 12h previsto, 6h 30min realizado
  - [ ] 📋 Outros: 8h disponível

---

## ✅ **PASSO 7: Testar Team Overview** (Aba "Minha Equipe")

### **Card: Distribuição de Carga**
- [ ] Trocar para aba "👥 Minha Equipe"
- [ ] Card "📊 Distribuição de Carga" aparece
- [ ] 3 membros listados:
  - [ ] João Silva (80%)
  - [ ] Maria Santos (95% - amarelo ⚠️)
  - [ ] Pedro Costa (60%)
- [ ] Barras de progresso coloridas
- [ ] Horas aparecem (ex: 32h / 40h)
- [ ] Hover effect ao passar mouse

### **Card: Alertas**
- [ ] Card "⚠️ Alertas" aparece
- [ ] 3 alertas com cores diferentes:
  - [ ] ⚠️ Amarelo - Sobrecarga
  - [ ] 🔴 Vermelho - Atrasadas
  - [ ] ✅ Verde - Disponível

### **Card: Performance da Equipe**
- [ ] Card "📈 Performance da Equipe" aparece
- [ ] 3 métricas:
  - [ ] Score Médio: 78 pontos
  - [ ] Taxa de Conclusão: 85%
  - [ ] Capacidade Utilizada: 75%

---

## ✅ **PASSO 8: Testar Responsividade**

### **Redimensionar Navegador:**
- [ ] Tela grande (> 1200px) → Layout 2 colunas
- [ ] Tela média (1024px) → Sidebar vai para baixo
- [ ] Tela pequena (768px) → Tudo empilhado
- [ ] Mobile (< 480px) → Abas verticais

### **Mobile Específico:**
- [ ] Abas de visão ficam verticais
- [ ] Cards de estatísticas em 2 colunas
- [ ] Botões de ação ficam full-width
- [ ] Team Overview cards empilhados

---

## ✅ **PASSO 9: Testar Performance Score**

- [ ] Círculo animado está visível
- [ ] Número "85" aparece no centro
- [ ] Gradiente roxo no círculo
- [ ] Badges aparecem:
  - [ ] 🔥 7 dias
  - [ ] 🏆 10/semana
- [ ] Status: "Excelente desempenho!"

---

## ✅ **PASSO 10: Testar Relatórios Rápidos**

- [ ] Scroll até o final da página
- [ ] 3 cards de relatórios aparecem:
  - [ ] Produtividade Semanal (gráfico de barras)
  - [ ] Tempo Médio (2.5 dias)
  - [ ] Taxa de Conclusão (donut 80%)
- [ ] Gráficos estão visíveis e estilizados

---

## ✅ **PASSO 11: Testar Atalhos de Teclado**

- [ ] Pressionar `Ctrl + F` (ou `Cmd + F` no Mac)
- [ ] Campo de busca é focado
- [ ] Digitar algo
- [ ] Pressionar `Esc`
- [ ] Busca é limpa

---

## ✅ **PASSO 12: Verificar Animações**

- [ ] Reload da página → Fade in suave
- [ ] Scroll para baixo → Cards aparecem gradualmente
- [ ] Hover nos cards → Levantam levemente
- [ ] Clicar em botões → Feedback visual
- [ ] Trocar de aba → Transição suave
- [ ] Abrir modal → Slide up animation
- [ ] Fechar modal → Fade out

---

## 🐛 **PASSO 13: Verificar Erros no Console**

### **Abrir DevTools (F12):**
- [ ] Console está limpo (sem erros vermelhos)
- [ ] Mensagem aparece: "✅ My Work page initialized"
- [ ] CSS carregou (verificar na aba Network)
- [ ] JavaScript carregou (verificar na aba Network)

---

## 📊 **Checklist de Qualidade Visual**

### **Cores e Estilos:**
- [ ] Gradiente roxo no header
- [ ] Azul nos botões primários
- [ ] Verde nos botões de sucesso
- [ ] Amarelo nos alertas
- [ ] Vermelho nos itens atrasados
- [ ] Fonte Poppins carregada

### **Espaçamentos:**
- [ ] Elementos não estão "colados"
- [ ] Margins e paddings consistentes
- [ ] Cards alinhados
- [ ] Texto legível

### **Interatividade:**
- [ ] Todos os botões têm hover effect
- [ ] Cursor muda para pointer nos clicáveis
- [ ] Feedback visual ao clicar
- [ ] Animações suaves

---

## 🎯 **CHECKLIST FINAL - Tudo Funcionando?**

### **✅ Componentes Principais:**
- [ ] Header com gradiente roxo
- [ ] Performance Score (círculo 85 pts)
- [ ] 3 Abas de visão (Minhas, Equipe, Empresa)
- [ ] 4 Cards de estatísticas
- [ ] Team Overview (aparece só na aba Equipe)
- [ ] Filtros (Todas, Hoje, Semana, Atrasadas)
- [ ] Busca em tempo real
- [ ] 3 Atividades de exemplo
- [ ] Sidebar de controle de horas
- [ ] Relatórios rápidos

### **✅ Modals:**
- [ ] Modal de Adicionar Horas
- [ ] Modal de Adicionar Comentário
- [ ] Modal de Finalizar

### **✅ Interações:**
- [ ] Troca de abas funciona
- [ ] Filtros funcionam
- [ ] Busca funciona
- [ ] Ordenação funciona
- [ ] Botões abrem modals
- [ ] Formulários funcionam
- [ ] Mensagens de sucesso aparecem

### **✅ Responsividade:**
- [ ] Desktop: Layout 2 colunas
- [ ] Tablet: Sidebar embaixo
- [ ] Mobile: Tudo empilhado

---

## 🎉 **Se Tudo Funcionou:**

```
┌────────────────────────────────────┐
│  ✅ FRONTEND APROVADO!             │
│                                    │
│  Próximo passo:                    │
│  Implementar Backend (APIs)        │
└────────────────────────────────────┘
```

**Siga para:** `docs/MY_WORK_INTEGRATION_GUIDE.md`

---

## 🐛 **Se Algo Não Funcionou:**

### **Problema: Página não carrega**
```bash
# Verificar se container está rodando:
docker ps

# Ver logs:
docker-compose -f docker-compose.dev.yml logs -f app_dev
```

### **Problema: CSS não aplicado**
- Limpar cache: `Ctrl + Shift + R`
- Verificar arquivo existe: `static/css/my-work.css`
- Abrir DevTools → Network → Verificar se my-work.css foi carregado

### **Problema: Modals não abrem**
- Abrir DevTools → Console
- Verificar se há erros JavaScript
- Verificar se my-work.js foi carregado

### **Problema: Abas não trocam**
- Abrir Console
- Clicar na aba
- Ver se aparece: "Switched to view: team"

---

## 📸 **Screenshots Esperados**

### **1. Aba "Minhas Atividades"**
```
- Header roxo com "Minhas Atividades"
- Performance Score 85 pts
- 4 cards de stats
- NO Team Overview
- Lista de atividades
- Sidebar de horas (Hoje ativo)
```

### **2. Aba "Minha Equipe"**
```
- Header roxo com "Atividades da Equipe"
- Performance Score da equipe
- 4 cards de stats (valores maiores)
- SIM Team Overview (3 cards)
- Lista de atividades da equipe
- Sidebar de horas da equipe
```

### **3. Modal de Horas Aberto**
```
- Overlay escuro com blur
- Modal centralizado
- Título: "⏱️ Adicionar Horas Trabalhadas"
- Info da atividade
- Formulário com data e horas
- Resumo automático
- Botões: Cancelar | Registrar Horas
```

---

## 📝 **Notas de Teste**

### **Dados Mockados:**
- Atividades: 3 exemplos fixos
- Team members: 3 membros fixos
- Horas: Valores de exemplo
- Performance: 85 pts fixo

### **Backend Pendente:**
- APIs não implementadas ainda
- Dados virão do backend no futuro
- Por enquanto, tudo é frontend mockado

---

## ✨ **O Que Esperar**

### **✅ Deve Funcionar:**
- Navegação entre abas
- Filtros e busca
- Ordenação
- Abrir modals
- Preencher formulários
- Fechar modals
- Animações
- Responsividade

### **⏳ Ainda Não Funciona (Backend Pendente):**
- Salvar horas no banco
- Salvar comentários no banco
- Finalizar atividade de verdade
- Carregar dados reais
- Permissões baseadas em role
- Equipes dinâmicas

---

## 🎯 **Critérios de Aprovação**

Para aprovar o frontend, verifique se:

✅ **Visual está bonito e moderno?**  
✅ **Abas trocam corretamente?**  
✅ **Modals abrem e fecham?**  
✅ **Responsivo funciona?**  
✅ **Nenhum erro no console?**  
✅ **Experiência é fluida?**

---

## 🚀 **Após Aprovação:**

1. ✅ Criar models no backend
2. ✅ Criar migrations de banco
3. ✅ Implementar APIs
4. ✅ Conectar frontend com backend
5. ✅ Testar integração completa

---

**Boa sorte nos testes!** 🎉

Qualquer problema, consulte:
- `docs/MY_WORK_COMPLETE_SUMMARY.md`
- `docs/MY_WORK_MULTI_VIEW.md`
- `docs/MY_WORK_INTEGRATION_GUIDE.md`

