import { pathToFileURL } from 'node:url';
import fs from 'node:fs/promises';
import path from 'node:path';

const artifact = await import(pathToFileURL('C:/Users/mff20/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs').href);
const { PresentationFile, FileBlob } = artifact;

const outDir = 'C:/GestaoVersus/app32/Propostas/Revisadas';
await fs.mkdir(outDir, { recursive: true });

function normalize(s) { return String(s ?? '').replace(/\r\n/g, '\n').trim(); }

function textElements(slide) {
  return slide.elements.items
    .filter(e => normalize(e.toSnapshot?.().text).length > 0)
    .map(e => ({ e, snap: e.toSnapshot() }));
}

function editSlide(slide, edits, options = {}) {
  const byId = new Map(slide.elements.items.map(e => [String(e.toSnapshot?.().id), e]));
  const edited = new Set();
  for (const [id, text] of Object.entries(edits)) {
    const el = byId.get(String(id));
    if (!el) {
      console.warn(`WARN: slide ${slide.index} missing shape id ${id}`);
      continue;
    }
    el.text = normalize(text);
    edited.add(String(id));
  }
  if (options.clearOtherText) {
    for (const { e, snap } of textElements(slide)) {
      const id = String(snap.id);
      if (!edited.has(id)) e.text = '';
    }
  }
}

async function exportDeck({ source, output, slides }) {
  const presentation = await PresentationFile.importPptx(await FileBlob.load(source));
  for (const [idx, edits] of Object.entries(slides)) {
    const slide = presentation.slides.items[Number(idx) - 1];
    if (!slide) {
      console.warn(`WARN: missing slide ${idx} for ${output}`);
      continue;
    }
    editSlide(slide, edits, { clearOtherText: true });
  }
  const pptx = await PresentationFile.exportPptx(presentation);
  const outPath = path.join(outDir, output);
  await pptx.save(outPath);
  console.log(`OK ${outPath}`);
}

const phub = {
  source: 'C:/GestaoVersus/app32/Propostas/Proposta Comercial - Versus Performance Hub.pptx',
  output: 'Proposta_Comercial_Versus_Performance_Hub_Revisada.pptx',
  slides: {
    1: {
      8: 'ESTRUTURAÇÃO EMPRESARIAL ASSISTIDA POR MÉTODO, TECNOLOGIA E GOVERNANÇA',
      9: 'Performance Hub\nProposta Comercial',
      10: 'Para: [cliente]\nAtt.: [decisor]',
      11: 'Maio de 2026'
    },
    2: {
      13: '1 — O DESAFIO',
      4: 'Sua empresa trabalha cada vez mais, mas nem sempre transforma esforço em resultado proporcional.',
      14: 'Gestores sobrecarregados, processos desorganizados, projetos sem ritmo e decisões baseadas em suposições.',
      15: 'O custo aparece em retrabalho, baixa produtividade, margem imprevisível, caixa pressionado e dependência de pessoas-chave.'
    },
    3: {
      20: '2 — A SOLUÇÃO: PERFORMANCE HUB',
      19: 'Um sistema operacional de gestão para PME: método consultivo, APP32, Sapiens, squads e cadência de governança.',
      21: 'Reunimos:\n→ Forma de Trabalho — método, ritos e responsabilidades\n→ Ferramenta — APP32 como núcleo de projetos, processos, indicadores e evidências\n→ Agentes — Sapiens, Squad Versus e Squad Cliente como apoio assistido\n→ Orquestração — follow-ups, aprovações, handoffs e decisões rastreáveis'
    },
    4: {
      81: 'Performance Hub',
      48: 'Sistema integrado de gestão',
      3: 'Forma de\nTrabalho',
      16: 'Ferramenta\nAPP32',
      17: 'Agentes e\nSquads',
      51: 'Orquestração e Governança',
      24: 'Ritos e\nresponsabilidades',
      27: 'Projetos, processos\ne indicadores',
      30: 'Sapiens, evidências\ne trilhas',
      37: 'Follow-up, handoffs\ne auditoria'
    },
    5: {
      4: '3 — O QUE SUA EMPRESA GANHA',
      9: 'Indicadores confiáveis, acessíveis e acompanhados',
      14: 'Decisões baseadas em fatos, não em suposições',
      20: 'Planejamento estratégico claro, aplicável e desdobrado em ação',
      25: 'Processos com donos, padrões, metas e evidências',
      30: 'Projetos priorizados, acompanhados e conectados à rotina',
      46: 'Desempenho e carga de trabalho com mais visibilidade',
      35: 'Sua organização caminha para se tornar a melhor versão de si mesma.'
    },
    6: {
      13: '4 — COMO IREMOS TRABALHAR',
      23: 'Serão 20 horas mensais de consultoria remota ou presencial. Nesse período, aplicamos metodologia desenvolvida em mais de 15 anos de experiência, apoiada por tecnologia própria para dar ritmo, disciplina e consistência à gestão.',
      22: 'Reunião mensal estratégica\nDiretoria: resultados, decisões, prioridades e rumos.',
      15: 'Reuniões semanais táticas\nGerências: entregas, gargalos, planos de ação e cobranças.',
      12: 'Assessoria assistida\nApoio à execução, follow-up, evidências e organização da rotina.'
    },
    7: {
      7: '5 — INVESTIMENTO',
      6: 'Nossa proposta permite que empresas menores acessem uma estrutura de gestão antes restrita a grandes organizações.\n\nInvestimento:\n• Parcela fixa mensal: R$ [valor]\n• Parcela variável por metas/resultados: R$ [critério]\n\nSem fidelidade obrigatória e sem multa rescisória, quando aplicável. O investimento deve ser comparado ao custo de operar com retrabalho, baixa previsibilidade e decisões sem evidência.'
    },
    8: {
      7: '5 — INVESTIMENTO',
      8: 'Condição de entrada com risco reduzido\n\nProposta válida até [data].\n\nA continuidade do trabalho é revisada com base em utilidade percebida, aderência da cadência e evolução real da gestão.'
    },
    9: {
      18: 'Histórias de',
      19: 'SUCESSO',
      20: 'Mais de 15 anos de experiência aplicados à gestão empresarial.',
      21: 'Nossas parcerias de longo prazo refletem compromisso com excelência, geração de valor e evolução real dos clientes. Cases e evidências específicos devem ser usados quando houver autorização.',
      22: 'Clientes e evidências autorizadas:'
    },
    10: {
      3: 'PRÓXIMO PASSO',
      4: 'Vamos iniciar este ciclo de gestão, controle e crescimento?\n\nPara avançar, envie CNPJ e e-mail da empresa para prepararmos o contrato e agendarmos o kickoff.\n\nNo início, alinharemos agenda, responsáveis, acessos e prioridades dos primeiros 30 dias.',
      6: 'Fabiano Ferreira\nfabiano@gestaoversus.com.br',
      7: '(71) 9 9642-6565',
      8: '@gestaoversus',
      9: 'gestaoversusoficial',
      10: 'facebook.com/VersusConsultoria',
      11: 'www.gestaoversus.com.br'
    }
  }
};

const brazilian = {
  source: 'C:/GestaoVersus/app32/Propostas/Proposta Versus - Serviços Pontuais - Brazilian Nickel.pptx',
  output: 'Proposta_Brazilian_Nickel_Servicos_Pontuais_Revisada.pptx',
  slides: {
    1: { 8: 'ESTRUTURAÇÃO INICIAL DE PROCESSOS COM VISIBILIDADE, GOVERNANÇA E PRÓXIMOS PASSOS', 9: 'Proposta Comercial\nServiços Pontuais', 10: 'Para: Brazilian Nickel\nAtt. Elton Souza', 11: 'Abril de 2026' },
    2: { 13: 'Empreender é uma evolução constante.', 14: 'Nesta etapa, propomos transformar a demanda inicial de processos em clareza executiva e entregáveis práticos.', 15: 'Operação\norganizada', 16: 'Decisão\nmais segura', 17: 'Rotinas\nvisíveis e auditáveis' },
    3: { 29: 'COMO FAREMOS', 31: 'Combinaremos expertises de forma coordenada e pragmática para estruturar o escopo solicitado e preparar a empresa para evoluir a gestão por processos.', 27: 'Gestão de Processos de Negócio (BPM)', 24: 'Gestão financeira e orçamentária', 25: 'Custos e precificação', 26: 'Consultoria fiscal e contábil', 28: 'Auditoria interna' },
    4: { 6: 'ESCOPO', 3: 'Solicitação do cliente\n\nEm reunião com o Sr. Elton Souza, definimos como prioridade inicial a estruturação de processos.\n\nEscopo proposto:\n→ concepção ou atualização da arquitetura de processos;\n→ visibilidade dos macroprocessos e processos por área;\n→ identificação dos donos de processos;\n→ modelagem parcial para enxergar atividades, encadeamento, fornecedores, clientes, insumos e produtos gerados.' },
    5: { 6: 'ENTREGÁVEIS', 3: 'Ao final desta etapa, a Brazilian Nickel receberá:\n\n→ Mapa de Processos;\n→ Fluxo dos Macroprocessos;\n→ SIPOC dos Macroprocessos;\n→ síntese executiva dos achados;\n→ recomendação de continuidade e priorização da estruturação.\n\nEsses entregáveis criam a base para POPs, indicadores, rotinas, implantação e estabilização.' },
    6: { 6: 'EVOLUÇÃO', 3: 'Após finalizar o escopo solicitado, o trabalho poderá evoluir para:\n\n→ finalização da modelagem;\n→ POPs — Procedimentos Operacionais Padrão;\n→ indicadores;\n→ rotinas;\n→ assistência na implantação e treinamento;\n→ assistência na estabilização da execução.\n\nA primeira etapa organiza a visão. A continuidade transforma visão em gestão.' },
    7: { 6: 'EVOLUÇÃO', 3: 'Implantação da Gestão por Processos\n\nApós a estruturação inicial, a Versus poderá apoiar:\n→ acompanhamento da execução da rotina;\n→ acompanhamento dos indicadores;\n→ PDCA com os donos de processos;\n→ priorização de melhorias;\n→ criação de ritmo e governança operacional.' },
    8: { 29: 'GANHOS', 31: 'Processos claros tornam as demais disciplinas de gestão mais objetivas, comparáveis e auditáveis.', 45: 'Gestão operacional', 27: 'Gestão financeira e orçamentária', 24: 'Gestão de custos', 25: 'Planejamento e gestão estratégica', 26: 'Gestão contábil, fiscal e tributária', 28: 'Auditoria interna e externa' },
    9: { 6: 'COMO TRABALHAMOS', 3: 'Cada frente de trabalho será estruturada como projeto, com:\n\na) alinhamento de expectativas;\nb) início do projeto;\nc) levantamento e entrevistas;\nd) acompanhamento da execução;\ne) validações intermediárias;\nf) entrega conforme alinhamento inicial;\ng) recomendação executiva de próximos passos.' },
    10: { 18: 'Histórias de', 19: 'SUCESSO', 20: 'Mais de 15 anos de experiência e parcerias de longo prazo.', 21: 'Nossa atuação busca gerar clareza, governança e evolução real para os clientes. Cases específicos devem ser usados quando houver autorização de divulgação.', 22: 'Clientes e evidências autorizadas:' },
    11: { 5: 'Como trabalhamos:', 4: 'Atendimento híbrido\nRemoto e presencial', 6: 'Combinamos disponibilidade e agilidade do trabalho remoto com presença física quando necessária para compreender a dinâmica da organização. Essa combinação reduz fricção sem perder profundidade consultiva.' },
    12: { 7: 'INVESTIMENTO', 6: 'Modelo proposto:\n\n→ R$ 350,00 por hora técnica, remota ou presencial;\n→ faturamento mínimo de 30 horas mensais;\n→ estimativa inicial aproximada de 90 horas para o escopo apresentado.\n\nPara trabalhos presenciais fora da RM de Salvador/BA:\n→ mínimo de 3 dias, equivalente a 24 horas úteis;\n→ cada hora de deslocamento entre cidades será considerada como 0,5 hora útil;\n→ despesas de deslocamento, alimentação, deslocamento local e hospedagem serão de responsabilidade do contratante;\n→ agendamento sujeito à disponibilidade.' },
    13: { 7: 'REDUÇÃO DE RISCO', 6: 'A estimativa poderá variar conforme engajamento, disponibilidade das pessoas-chave e agilidade de resposta da organização.\n\nPara reduzir o risco de entrada:\n→ contrato sem fidelidade;\n→ sem prazo mínimo obrigatório;\n→ encerramento a qualquer momento, sem multa;\n→ evolução para novas etapas apresentada separadamente.' },
    14: { 4: 'Ficamos à disposição para esclarecimentos adicionais.\n\nCaso a proposta esteja aderente, pedimos a gentileza de responder com o CNPJ e o e-mail da empresa para prepararmos o contrato e agendarmos o kickoff.\n\nTambém indicaremos as pessoas-chave e documentos iniciais necessários para começar.', 6: 'Fabiano Ferreira\nfabiano@gestaoversus.com.br', 7: '(71) 9 9642-6565', 8: '@gestaoversus', 9: 'gestaoversusoficial', 10: 'facebook.com/VersusConsultoria', 11: 'www.gestaoversus.com.br', 12: 'Obrigado!' }
  }
};

const britos = {
  source: 'C:/GestaoVersus/app32/Propostas/Proposta Versus Desktop - Serviços Pontuais Vrs. 02.pptx',
  output: 'Proposta_Britos_Mag_Servicos_Pontuais_Revisada.pptx',
  slides: {
    1: { 8: 'ESTRUTURAÇÃO LEGAL E TRIBUTÁRIA INICIAL COM CLAREZA PARA DECISÃO', 9: 'Proposta Comercial\nServiços Pontuais', 10: 'Para: Britos Mag Energia Solar\nAtt. Wilson Caldas e Priscila', 11: 'Janeiro de 2026' },
    2: { 13: 'Empreender é uma evolução constante.', 14: 'Propomos organizar a estrutura inicial do negócio para reduzir insegurança decisória e preparar próximos passos.', 15: 'Estrutura\nmais clara', 16: 'Decisão\nmais segura', 17: 'Rotinas\nmais auditáveis', 18: 'A seguir, apresentamos como faremos isso na prática.' },
    3: { 6: 'ESCOPO', 3: 'Inicialmente atenderemos às necessidades apresentadas em reunião com o Sr. Wilson Caldas e Priscila.\n\nEscopo proposto:\n→ definição e estruturação legal do negócio;\n→ análise das atividades: intermediação, monitoramento, instalação, recebimento de valores de terceiros, patrimônio e indústria de energia;\n→ enquadramento e planejamento tributário considerando alternativas disponíveis na legislação atual.\n\nO objetivo é reduzir insegurança decisória e organizar a base da operação.' },
    4: { 29: 'COMO FAREMOS', 31: 'Criaremos uma solução coordenada, prática e personalizada para a realidade da Britos Mag, integrando leitura legal, tributária, financeira, fiscal, operacional e de controle.', 27: 'Gestão de Processos de Negócio (BPM)', 24: 'Gestão financeira e orçamentária', 25: 'Custos e precificação', 26: 'Consultoria fiscal e contábil', 28: 'Auditoria interna' },
    5: { 6: 'COMO TRABALHAMOS', 3: 'Cada frente será estruturada como projeto, com:\n\na) alinhamento de expectativas;\nb) levantamento de informações;\nc) análise técnica e consultiva;\nd) validações intermediárias;\ne) entrega do relatório final;\nf) orientação executiva sobre próximos passos.\n\nA efetividade depende da disponibilidade das informações e da participação dos responsáveis.' },
    6: { 18: 'Histórias de', 19: 'SUCESSO', 20: 'Mais de 15 anos de experiência e parcerias de longo prazo.', 21: 'Nossa atuação busca gerar clareza, governança e evolução real para os clientes. Cases específicos devem ser usados quando houver autorização de divulgação.', 22: 'Clientes e evidências autorizadas:' },
    7: { 7: 'INVESTIMENTO', 6: 'O investimento para esta etapa será de:\n\nR$ 6.500,00\n(seis mil e quinhentos reais)\n\nForma de pagamento:\n→ 50% no início dos trabalhos;\n→ 50% na entrega do relatório final.\n\nO valor considera volume de trabalho, conhecimento necessário, técnicas aplicadas e impacto esperado na qualidade da decisão.' },
    8: { 5: 'Como trabalhamos:', 4: 'Atendimento híbrido\nRemoto e presencial', 6: 'Trabalharemos de forma híbrida, combinando agilidade remota, presença física quando necessária e entendimento consultivo da realidade da empresa. Essa combinação permite eficiência sem perder profundidade.' },
    9: { 9: 'Após esta primeira fase, poderemos avançar para estruturação financeira, custos e precificação, gestão de processos, controles internos, rotina gerencial e Performance Hub.', 8: 'A MELHOR VERSÃO DE SI MESMA!', 10: 'Saiba mais em:\nphub.gestaoversus.com.br' },
    10: { 4: 'Qualquer dúvida adicional estamos à disposição.\n\nCaso a proposta esteja aderente, responda com o CNPJ e e-mail da empresa para prepararmos o contrato e agendarmos o kickoff.\n\nTambém indicaremos documentos e informações iniciais necessários para começar.', 6: 'Fabiano Ferreira\nfabiano@gestaoversus.com.br', 7: '(71) 9 9642-6565', 8: '@gestaoversus', 9: 'gestaoversusoficial', 10: 'facebook.com/VersusConsultoria', 11: 'www.gestaoversus.com.br', 12: 'Obrigado!' }
  }
};

await exportDeck(phub);
await exportDeck(brazilian);
await exportDeck(britos);
