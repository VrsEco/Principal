# SPEC — Governança de Cards por Entrega

## Decisão

Execuções técnicas com três ou mais etapas devem possuir **um único card por entrega**. As etapas são registradas como checklist e evidências no próprio card; não devem gerar cards independentes.

## Motivo

O modelo anterior, de um card por passo, levou o projeto `AA.J.1` a 3.084 cards. Em 13/08/2026, 2.721 cards correspondiam a passos e 417 dos 466 cards abertos eram apenas etapas intermediárias.

## Contrato operacional

- título: `[<nome da entrega>]`;
- notas: objetivo, checklist numerado e evidências por etapa;
- somente uma entrega independente justifica um novo card;
- o card permanece aberto durante toda a execução;
- cada etapa concluída atualiza o checklist e acrescenta sua evidência;
- o card é concluído somente após a última etapa e a validação final;
- materialização deve ser idempotente por `project_id + título normalizado`;
- duplicidade detectada deve ser reportada, nunca recriada silenciosamente.

## Transição AA.J.1 → AA.J.2

- `AA.J.1` será preservado como histórico e arquivado;
- somente backlog ainda válido será levado ao `AA.J.2`;
- séries abertas no padrão `Passo X de N` serão consolidadas em uma entrega;
- evidências e referências aos códigos originais serão preservadas nas notas;
- nenhuma leitura ou escrita pode atravessar o `company_id=9`.

## Contrato de desempenho do quadro

- concluídos não são carregados por padrão;
- listagem de cards é paginada e filtrada no servidor;
- payload de lista é resumido; detalhe completo é obtido sob demanda;
- mutações atualizam apenas o card afetado;
- contagens são agregadas no banco, sem depender da materialização integral do quadro;
- o frontend não deve criar milhares de nós DOM de uma só vez.

