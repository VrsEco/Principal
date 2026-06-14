# Paper — Malha Analítica Estratégica via MCP/Sapiens

**Classificação:** Paper  
**Status:** Em amadurecimento conceitual  
**Data:** 2026-06-14  
**Domínio principal:** `analytics`  
**Superfícies MCP-alvo:** `mcp_analytics` e `sapiens`  

## 1. Tese

A Malha Analítica Estratégica conecta estratégia, processos, projetos, indicadores, rotinas, pessoas, recursos, capacidade, governança e evidências para responder uma pergunta executiva central:

> A empresa tem capacidade real, econômica e operacional para executar a estratégia que declarou?

A proposta não é criar apenas um dashboard visual. O objetivo é formar um **motor de diagnóstico estruturado da executabilidade da estratégia**, expondo snapshots tenant-safe via MCP/Sapiens para que IAs externas possam analisar gaps, gargalos e oportunidades com evidências.

## 2. Camadas da Malha

### 2.1 Estratégia

- objetivos estratégicos;
- temas estratégicos;
- OKRs;
- key results;
- indicadores;
- metas;
- medições;
- iniciativas estratégicas;
- riscos e premissas.

### 2.2 Operação

- macroprocessos;
- processos;
- subprocessos;
- atividades;
- rotinas;
- POPs/procedimentos;
- entregas;
- controles;
- riscos operacionais.

### 2.3 Capacidade e recursos

Recursos devem ser tratados como entidades analíticas de primeira classe.

Grupos de recursos:

- Pessoas;
- Insumos;
- Imóveis / Instalações;
- TI / Digital;
- Equipamentos / Ferramentas;
- Outros.

Para cada recurso, a Malha deve capturar:

- disponibilidade;
- capacidade operacional;
- custo fixo;
- custo variável;
- restrição;
- criticidade;
- substituibilidade;
- risco associado;
- competência ou especificação requerida;
- vínculo com processo, rotina, projeto ou indicador.

### 2.4 Governança

- dono do objetivo;
- dono do processo;
- sponsor do projeto;
- responsável pela meta;
- responsável pela medição;
- fóruns/comitês;
- cadência de decisão;
- decisões pendentes;
- regras de escalonamento.

### 2.5 Evidências e snapshots

Toda análise deve ser baseada em snapshot versionado, com:

- `company_id`;
- período;
- fontes de dados;
- data de geração;
- frescor dos dados;
- score de qualidade;
- limitações;
- evidências por finding/recomendação.

## 3. Nova dimensão — Benchmarking de Capacidade Operacional e Eficiência Econômica

Além de comparar estado atual versus estado desejado interno, a Malha deve comparar a capacidade atual da empresa com o que o mercado oferece.

Essa dimensão responde:

> Existe tecnologia, equipamento, pessoa, fornecedor, software, método ou automação disponível no mercado que aumente a capacidade, reduza custo unitário, melhore qualidade ou viabilize a estratégia?

### 3.1 Objetivo

Criar uma análise de **capacidade atual vs. capacidade potencial de mercado** por processo.

Exemplos de alternativas pesquisáveis:

- máquinas mais modernas;
- equipamentos com especificações técnicas superiores;
- automações físicas ou digitais;
- softwares especializados;
- fornecedores terceirizados;
- profissionais com competências mais avançadas disponíveis no mercado;
- treinamentos e certificações;
- novos métodos produtivos;
- benchmarks setoriais de produtividade, custo e qualidade.

### 3.2 Exemplo conceitual

Processo atual:

- Processo: Costura;
- Recursos: costureira, máquina de costura e overlock;
- Capacidade: 1.000 peças/mês;
- Custo total estimado: R$ 10,00 por peça.

Benchmark de mercado:

- Máquina automatizada executa costura e overlock;
- colaboradora passa a supervisionar;
- capacidade quadruplica;
- custo fixo dobra;
- custo total estimado cai para R$ 5,00 por peça;
- ponto de equilíbrio aumenta pela elevação do custo fixo.

Relatório esperado:

> Para aumentar a eficiência do processo de Costura, recomenda-se avaliar a máquina Y, com treinamento da colaboradora responsável. Em H meses, a capacidade estimada seria de T peças/mês. O custo fixo subiria para Q, o custo unitário projetado cairia para P, o ponto de equilíbrio passaria para G peças / R$ F, o faturamento potencial subiria para V, a margem de contribuição total possível para O e o lucro potencial para N.

## 4. Modelo analítico do Benchmarking

### 4.1 Estado atual do processo

Campos mínimos:

- processo;
- produto/entrega;
- volume atual;
- capacidade máxima atual;
- tempo de ciclo;
- pessoas alocadas;
- equipamentos usados;
- insumos;
- instalações;
- sistemas;
- custo fixo atual;
- custo variável unitário;
- custo total unitário;
- preço médio;
- margem de contribuição unitária;
- ponto de equilíbrio atual;
- gargalos e restrições.

### 4.2 Pesquisa de mercado

A IA externa pode pesquisar fontes públicas e fornecedores, mas deve retornar dados estruturados com evidência:

- nome da alternativa;
- tipo: equipamento, pessoa, software, fornecedor, treinamento, método ou automação;
- especificações técnicas;
- capacidade prometida;
- custo de aquisição;
- custo operacional;
- custo de manutenção;
- necessidade de treinamento;
- prazo de implantação;
- riscos;
- fontes;
- confiança;
- premissas.

### 4.3 Cenário projetado

Campos mínimos:

- investimento necessário;
- nova capacidade mensal;
- novo custo fixo;
- novo custo variável unitário;
- novo custo total unitário;
- novo ponto de equilíbrio em unidades;
- novo ponto de equilíbrio em receita;
- faturamento potencial;
- margem de contribuição total potencial;
- lucro operacional potencial;
- payback estimado;
- ROI estimado;
- cenário conservador;
- cenário provável;
- cenário otimista.

## 5. Nova dimensão — Fit Executor–Processo e Capacidade Humana Desejável

A Malha também deve analisar a aderência entre o executor atual de cada processo e a capacidade humana desejável para sustentar a operação atual e o planejamento estratégico.

Essa dimensão responde:

> As pessoas que executam os processos hoje possuem capacidade técnica, organizacional, comportamental observável e disponibilidade compatíveis com o que a empresa precisa executar agora e com o que pretende executar no futuro?

### 5.1 Objetivo

Criar uma análise estruturada de **fit entre executor, processo e estratégia**, com foco em desenvolvimento, capacitação, melhor alocação e aumento de desempenho global.

O objetivo não é substituir julgamento humano, nem criar avaliação psicológica automatizada. A IA deve atuar como apoio analítico para:

- identificar gaps técnicos;
- sugerir treinamentos;
- apontar necessidade de mentoria ou supervisão;
- sugerir realocação entre atividades;
- identificar risco de sobrecarga;
- fortalecer sucessão e backup;
- aumentar aderência entre pessoa, processo e estratégia.

### 5.2 Dimensões avaliáveis

Dimensões recomendadas:

- conhecimento técnico requerido pelo processo;
- domínio real do processo;
- qualidade e consistência da execução;
- produtividade;
- cumprimento de prazos;
- organização pessoal;
- aderência a rotinas e POPs;
- autonomia;
- capacidade de aprendizagem;
- comunicação;
- liderança situacional;
- colaboração;
- disponibilidade;
- risco de sobrecarga;
- potencial de evolução;
- aderência ao papel atual;
- aderência a papéis alternativos dentro da empresa.

Dimensões sensíveis devem ser tratadas com cautela. Em vez de “controle emocional” como diagnóstico psicológico, a Malha deve usar linguagem profissional e observável, como:

- estabilidade de execução sob pressão;
- reação a mudanças de prioridade;
- capacidade de seguir rituais e combinados;
- clareza na comunicação em situações críticas;
- necessidade de apoio em contextos de alta complexidade.

### 5.3 Fontes internas possíveis

A análise pode usar, com governança e finalidade explícita:

- currículo cadastrado;
- histórico de experiências;
- treinamentos realizados;
- certificações;
- função/cargo;
- processos executados;
- rotinas atribuídas;
- atrasos recorrentes;
- qualidade das entregas;
- retrabalho;
- evidências de POP/checklist;
- feedbacks registrados;
- autoavaliação;
- avaliação de liderança;
- entrevista estruturada conduzida por IA;
- disponibilidade de agenda/blocos de jornada.

### 5.4 Conversa assistida por IA

A IA pode conduzir uma conversa estruturada com o executor, desde que haja transparência, consentimento quando aplicável e finalidade legítima.

Objetivos da conversa:

- entender domínio técnico;
- confirmar entendimento do processo;
- avaliar organização da execução;
- identificar dificuldades reais;
- mapear necessidades de treinamento;
- identificar barreiras de processo, ferramenta ou comunicação;
- entender aspirações e potenciais realocações;
- produzir um plano de desenvolvimento.

A conversa deve evitar:

- diagnóstico psicológico;
- inferência clínica;
- julgamento moral;
- rótulos pessoais;
- recomendações disciplinares automáticas;
- decisões de desligamento, promoção ou punição.

### 5.5 Estado atual vs. estado desejável

Modelo conceitual:

```text
Processo exige X competências, disponibilidade e maturidade.
Executor atual demonstra Y com base em evidências.
Planejamento estratégico exigirá Z.
Gap = Z - Y.
Recomendação = capacitar, apoiar, automatizar, redistribuir, contratar ou realocar.
```

Exemplo de saída:

> O processo de Atendimento Consultivo exige domínio técnico, organização de follow-up e comunicação clara com clientes. O executor atual possui boa experiência operacional, mas apresenta gaps de organização e cadência de acompanhamento. Recomenda-se treinamento em CRM, rotina semanal de revisão de carteira, mentoria por 60 dias e redistribuição parcial de atividades administrativas para liberar foco comercial.

### 5.6 Métricas sugeridas

- índice de fit executor–processo;
- gap técnico;
- gap de organização;
- gap de disponibilidade;
- risco de sobrecarga;
- dependência de pessoa-chave;
- necessidade de supervisão;
- potencial de capacitação;
- aderência a atividades atuais;
- aderência a atividades alternativas;
- cobertura de backup;
- prioridade de treinamento.

### 5.7 Recomendações possíveis

A IA pode sugerir:

- treinamento técnico;
- treinamento comportamental profissional;
- mentoria;
- shadowing;
- revisão de POP;
- simplificação do processo;
- automação;
- redistribuição de atividades;
- realocação para processo mais aderente;
- contratação complementar;
- criação de backup;
- redução de sobrecarga;
- melhoria de ferramentas.

### 5.8 Guardrails de LGPD, ética e governança humana

Essa dimensão trata dados pessoais e pode influenciar decisões relevantes sobre pessoas. Portanto, deve ter governança reforçada:

- finalidade explícita;
- coleta mínima necessária;
- transparência ao colaborador;
- segurança e controle de acesso;
- trilha de auditoria;
- direito de revisão humana;
- separação entre fato, inferência e recomendação;
- proibição de decisão automatizada sem validação humana;
- não discriminação;
- explicabilidade das recomendações;
- possibilidade de contestação/correção de dados.

Regra de ouro:

> IA recomenda desenvolvimento e alocação. Humano decide, com evidência, contexto e responsabilidade.

### 5.9 Tools MCP futuras sugeridas

- `get_process_executor_fit_snapshot`
- `get_executor_capability_profile`
- `compare_executor_fit_to_process_requirements`
- `prepare_executor_development_interview`
- `register_executor_interview_evidence`
- `generate_executor_development_plan`
- `suggest_executor_activity_reallocation`

No MVP, essas tools devem ser restritas a leitura, análise e recomendação assistida. Mutação de cargo, remuneração, avaliação formal, promoção, punição ou desligamento deve ficar fora da surface de IA.

## 6. Nova dimensão — Motivação, Engajamento e Desenho Neurocomportamental do Trabalho

A Malha também deve avaliar se processos, rotinas, ambiente e rituais de gestão favorecem estados produtivos de motivação, energia, vínculo, foco e bem-estar.

Essa dimensão nasce de uma hipótese útil:

> Processos não são neutros. O desenho do trabalho pode estimular ou inibir motivação, foco, pertencimento, reconhecimento, desafio saudável e energia de execução.

### 6.1 Posicionamento técnico

A Malha não deve medir neurotransmissores diretamente, nem afirmar diagnóstico biológico sobre colaboradores.

Em vez disso, deve usar dopamina, adrenalina, serotonina, ocitocina e noradrenalina como **linguagem conceitual/metafórica** para organizar sinais observáveis de experiência de trabalho.

Tradução segura para o produto:

| Referência neuroquímica | Tradução organizacional observável |
|---|---|
| Dopamina | progresso, desafio adequado, metas claras, feedback rápido, recompensa percebida |
| Adrenalina | energia de ação, urgência saudável, senso de missão, capacidade de resposta |
| Serotonina | reconhecimento, orgulho, status saudável, estabilidade, autoestima profissional |
| Ocitocina | confiança, pertencimento, colaboração, vínculo com liderança/equipe |
| Noradrenalina | foco, atenção, prontidão, clareza de prioridade, concentração sob demanda |

### 6.2 Perguntas analíticas por processo/rotina

A IA deve avaliar:

- a rotina gera sensação clara de progresso?
- o executor recebe feedback rápido e útil?
- há desafio na medida certa ou pressão excessiva?
- o trabalho possui propósito percebido?
- há autonomia suficiente?
- existe reconhecimento proporcional ao esforço?
- a rotina promove colaboração ou isolamento?
- há monotonia improdutiva?
- há alternância saudável entre foco, pausa e interação?
- o ambiente favorece concentração?
- a liderança dá clareza de prioridade?
- o processo gera ansiedade recorrente por ambiguidade ou excesso de urgência?
- há rituais de celebração de avanço?
- há sobrecarga emocional ou cognitiva evitável?

### 6.3 Métricas sugeridas

- índice de motivação da rotina;
- clareza de propósito;
- percepção de progresso;
- velocidade de feedback;
- nível de autonomia;
- nível de reconhecimento;
- colaboração percebida;
- risco de monotonia;
- risco de pressão improdutiva;
- risco de isolamento;
- qualidade do ambiente de foco;
- equilíbrio demanda–recurso;
- aderência da rotina ao perfil do executor;
- risco de desengajamento.

### 6.4 Intervenções possíveis

A IA pode sugerir:

- quebrar entregas longas em marcos menores;
- criar feedbacks rápidos;
- revisar metas para equilibrar desafio e capacidade;
- aumentar autonomia com limites claros;
- criar rituais de reconhecimento;
- alternar tarefas repetitivas com tarefas de maior domínio;
- melhorar clareza de prioridade;
- inserir pausas planejadas;
- reduzir interrupções;
- redesenhar ambiente físico/digital;
- promover colaboração entre pares;
- ajustar jornada/blocos de foco;
- criar momentos de celebração de progresso;
- revisar carga em processos de alta pressão.

### 6.5 Suporte ambiental e nutricional leve

Quando adequado, a Malha pode sugerir **suportes simples de bem-estar no ambiente de trabalho**, como disponibilidade de:

- água;
- café;
- chá;
- frutas;
- castanhas;
- snacks leves;
- opções sem açúcar;
- opções sem cafeína;
- pausas curtas para hidratação e recuperação.

Essas sugestões devem ser tratadas como apoio ambiental, não como prescrição médica ou promessa de “aumentar neurotransmissores”.

Guardrails específicos:

- não recomendar suplemento, medicamento ou dieta clínica;
- respeitar restrições alimentares, alergias, condições de saúde e preferências pessoais;
- oferecer opções, nunca impor consumo;
- evitar estimular excesso de cafeína ou açúcar;
- validar com profissional de saúde/nutrição quando a política envolver recomendações nutricionais estruturadas;
- registrar que o objetivo é conforto, energia percebida e qualidade da pausa, não intervenção biomédica.

Exemplo seguro:

> Em rotinas de alta concentração no período da manhã, recomenda-se disponibilizar água, café/chá e snacks leves opcionais, além de uma pausa curta programada. A hipótese é melhorar conforto, foco percebido e sustentabilidade da rotina, sem caracterizar recomendação médica.

### 6.6 Fontes internas possíveis

- pesquisas pulse de clima/engajamento;
- check-ins de rotina;
- entrevistas estruturadas;
- feedbacks de liderança;
- absenteísmo;
- rotatividade;
- atrasos recorrentes;
- retrabalho;
- interrupções registradas;
- carga de agenda;
- dados de jornada;
- análise de rituais de gestão;
- autoavaliação de energia/foco/motivação.

### 6.7 Tools MCP futuras sugeridas

- `get_process_motivation_design_snapshot`
- `analyze_routine_engagement_factors`
- `generate_work_design_improvement_plan`
- `suggest_process_wellbeing_interventions`
- `prepare_employee_motivation_checkin`
- `register_employee_motivation_evidence`

No MVP, essa dimensão deve funcionar como análise de desenho do trabalho e bem-estar organizacional. Não deve gerar diagnóstico psicológico, fisiológico ou médico.

## 7. Fórmulas de referência

```text
Custo total unitário = custo variável unitário + (custo fixo alocado / volume produzido)

Margem de contribuição unitária = preço unitário - custo variável unitário

Ponto de equilíbrio em unidades = custo fixo total / margem de contribuição unitária

Ponto de equilíbrio em receita = ponto de equilíbrio em unidades * preço unitário

Faturamento potencial = capacidade máxima projetada * preço unitário

Margem de contribuição total potencial = capacidade máxima projetada * margem de contribuição unitária

Lucro operacional potencial = margem de contribuição total potencial - custo fixo total

Payback = investimento / ganho operacional incremental mensal
```

## 8. Tools MCP futuras sugeridas

### 8.1 Leitura interna

- `get_process_operational_capacity_state`
- `get_process_resource_cost_structure`
- `get_process_break_even_snapshot`

### 8.2 Benchmarking externo assistido

- `prepare_process_benchmarking_brief`
- `register_process_market_benchmark_evidence`
- `compare_process_market_alternatives`

### 8.3 Análise econômica

- `simulate_process_capacity_upgrade`
- `analyze_process_efficiency_gap`
- `generate_process_benchmarking_report`

No MVP, essas tools devem ser somente leitura/simulação. Nenhuma compra, contratação, alteração de recurso ou mudança de capacidade deve ser executada automaticamente.

## 9. Guardrails anti-alucinação

A IA pode:

- comparar dados internos com alternativas externas;
- sugerir cenários;
- apontar gaps;
- recomendar estudos, treinamentos e investimentos;
- estimar impacto econômico com premissas explícitas.

A IA não pode:

- afirmar capacidade de máquina sem fonte;
- afirmar preço definitivo sem evidência;
- recomendar compra como decisão final;
- sugerir demissão ou substituição individual sem governança humana;
- ocultar aumento de custo fixo ou ponto de equilíbrio;
- misturar dados entre tenants;
- alterar dados operacionais no MVP.
- decidir sobre pessoas sem validação humana.
- inferir traços psicológicos ou emocionais não observáveis.
- usar conversa com IA como avaliação disciplinar automática.
- afirmar que um processo “gera dopamina/serotonina” no colaborador.
- prescrever dieta, suplemento ou intervenção médica.
- confundir suporte ambiental de bem-estar com tratamento de saúde.

Toda recomendação deve conter:

- gap identificado;
- evidência interna;
- evidência externa;
- premissas;
- cálculo;
- confidence score;
- riscos;
- limitações;
- necessidade de validação humana.

## 10. Relatório analítico esperado

O relatório por processo deve conter:

1. resumo executivo;
2. diagnóstico do processo atual;
3. recursos empregados;
4. capacidade e custo atual;
5. benchmark de mercado;
6. alternativas comparadas;
7. simulação econômica;
8. impacto no ponto de equilíbrio;
9. impacto na capacidade e faturamento potencial;
10. riscos de implantação;
11. recomendação priorizada;
12. evidências e fontes;
13. limitações da análise.
14. plano de capacitação/realocação quando envolver executores.
15. validação humana necessária quando houver impacto em pessoas.
16. análise de motivação/desenho do trabalho quando aplicável.
17. sugestões de suporte ambiental e pausas, quando aplicável.

## 11. Decisão conceitual

Essas dimensões transformam a Malha em uma análise de **executabilidade econômica, operacional, humana e motivacional da estratégia**.

Ela permite sair de:

> “Temos processos mapeados?”

Para:

> “Nossos processos, recursos, tecnologias, executores e rotinas de trabalho são competitivos, saudáveis, motivadores e aderentes ao que a estratégia exige?”

Essa frente deve amadurecer como Paper antes de virar SPEC, pois envolve dados internos, pesquisa externa, simulação financeira, dados pessoais, bem-estar no trabalho, risco de recomendação e governança de decisão.

## 12. Impacto na Jornada de Estruturação / Maturação Estratégica

A Malha Analítica Estratégica deve alimentar a jornada oficial sem criar estado transacional paralelo.

Impactos esperados na jornada:

- a camada **Estrutura/Recursos** passa a ser fase explícita entre arquitetura de processos e modelagem;
- recursos, capacidade, custo e gargalos passam a compor maturidade estratégica, não apenas maturidade operacional;
- fit executor–processo passa a compor a leitura de capacidade estratégica, com foco em desenvolvimento e alocação responsável;
- motivação, engajamento e desenho do trabalho passam a compor a leitura de sustentabilidade da execução;
- o **Painel de Gestão Estratégica** passa a ser a visão executiva de consumo da maturidade, indicadores e ações governadas;
- snapshots MCP/Sapiens passam a evidenciar a qualidade da análise e o frescor dos dados;
- benchmarking externo permanece opcional e assistido até virar SPEC, sempre com fontes, premissas e validação humana.

Referência oficial dependente: `app32/docs/spec/sapiens_strategy_alignment_n1_spec.md`, seção **Jornada de Estruturação / Maturação Estratégica Sapiens**.
