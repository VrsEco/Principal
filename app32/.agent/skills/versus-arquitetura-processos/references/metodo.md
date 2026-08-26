# Método Versus de Arquitetura de Processos

## 1. Pergunta central

> O que a empresa precisa fazer continuamente para cumprir sua identidade, entregar valor aos seus clientes e alcançar seus objetivos?

## 2. Cadeia de derivação

```text
Identidade
→ resultados empresariais necessários
→ áreas/cadeias
→ macroprocessos (geração de valor → grandes entregas)
→ processos (entregas)
→ atividades (microentregas)
→ clientes ou processos recebedores
```

### Identidade

Compreender propósito, missão, visão, valores, posicionamento, clientes, mercados, produtos, serviços, objetivos, restrições e diferenciais. Não inferir definição ausente como fato.

### Resultados empresariais necessários

Traduzir a identidade em resultados que a empresa precisa produzir continuamente: direção, aquisição de clientes, entrega principal, receita, sustentação, conformidade, pessoas, recursos e aprendizado.

### Áreas ou cadeias

Agrupar grandes famílias de geração de valor. Usar Gestão, Finalísticos e Apoio apenas quando forem adequados; não torná-los obrigatórios.

### Macroprocessos — grandes entregas

Representar grandes entregas ou capacidades empresariais permanentes. Um macroprocesso deve ter finalidade, fronteira, recebedor e conjunto coerente de processos. Deve sobreviver a mudanças razoáveis de organograma.

### Processos — entregas

Representar transformações recorrentes e gerenciáveis. Exigir gatilho, entradas, transformação, saída, cliente/recebedor, responsável possível e indicador possível.

### Atividades — microentregas

Representar ações executáveis que produzem avanço verificável no processo. Associar controles, responsáveis, checklists, formulários, POPs e indicadores quando aplicável.

### Clientes ou processos recebedores

Fechar a cadeia explicitando quem recebe cada entrega. Validar se a saída de um processo é entrada útil de outro ou resultado percebido pelo cliente.

## 3. Fatoração

Para cada item, perguntar:

1. É permanente ou temporário?
2. É uma grande entrega, uma entrega ou uma microentrega?
3. Possui início e fim próprios?
4. Produz saída reconhecível?
5. Tem cliente ou processo recebedor?
6. Pode ter responsável e indicador?
7. Está no mesmo nível de granularidade dos irmãos?
8. Continua fazendo sentido se o organograma mudar?

Dividir quando houver resultados, recebedores, owners ou ciclos claramente distintos. Agrupar quando os itens forem apenas etapas inseparáveis da mesma entrega.

### Nomenclatura direta e fronteiras

O nome do processo deve comunicar rapidamente o trabalho realizado e a entrega que encerra sua fronteira. Usar verbos concretos e objetos reconhecíveis pela equipe, evitando títulos abstratos ou descrições que tentem conter toda a jornada ponta a ponta.

Verbos podem permanecer no mesmo nome quando convergem para uma única entrega e mantêm recebedor, responsável e ciclo de gestão coerentes. Separar em processos distintos quando surgir nova entrega principal, novo recebedor, handoff relevante, novo responsável, decisão autônoma ou ciclo de acompanhamento próprio.

Exemplo de refatoração preferida:

```text
Evitar:
AA.C.2.2.2 - Desenhar, precificar, propor, negociar e contratar soluções

Preferir:
AA.C.2.2.2 - Desenhar, precificar, confeccionar e enviar proposta
AA.C.2.2.3 - Fazer follow-up, negociar e fechar contratos
AA.C.2.2.4 - Formalizar contrato e realizar onboarding financeiro e operacional
```

No exemplo, o envio da proposta encerra uma entrega reconhecível. O acompanhamento, a negociação e o fechamento possuem outro momento de controle e outra entrega final; por isso formam um processo próprio. Após o fechamento, a formalização e o onboarding iniciam a relação contratada e preparam a operação e o fluxo financeiro, caracterizando uma terceira fronteira gerenciável.

## 4. Encadeamento

Validar dois eixos:

- `vertical`: identidade → grande entrega → entrega → microentrega;
- `horizontal`: saída → recebedor/entrada seguinte → nova transformação.

Localizar órfãos, lacunas, duplicidades, sobreposições e saltos de nível.

## 5. Relação com capacidades e projetos

- Processo declara as capacidades habilitadoras de que necessita.
- Dimensão apenas classifica capacidades: ativos; pessoas; tecnologia/dados; documentos/conhecimento; materiais/serviços.
- Projeto cria, corrige ou melhora processo/capacidade; não deve ser incorporado como processo permanente.
- Agente Gestor de Projetos recebe gaps aprovados; o Arquiteto de Processos não cria projeto automaticamente.

## 6. Gates de qualidade

Uma proposta só pode ser apresentada para validação quando:

- deriva de identidade/evidências explícitas;
- cobre geração de valor, gestão e sustentação necessárias;
- mantém níveis coerentes;
- usa nomes diretos e fronteiras perceptíveis, sem condensar entregas distintas no mesmo processo;
- fecha entregas em clientes ou recebedores;
- separa organização, processos, projetos, ativos e atividades;
- registra dúvidas e hipóteses sem mascará-las como decisão;
- explica por que dividiu, agrupou, incluiu ou removeu elementos.
