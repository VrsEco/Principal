/** @jsxRuntime automatic */
/** @jsxImportSource @oai/artifact-tool/presentation-jsx */
import {
  Presentation,
  PresentationFile,
  row,
  column,
  grid,
  layers,
  panel,
  text,
  shape,
  rule,
  fill,
  hug,
  fixed,
  wrap,
  fr,
  auto,
  drawSlideToCtx,
} from '@oai/artifact-tool';
import { Canvas } from 'file:///C:/Users/mff20/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/node_modules/skia-canvas/lib/index.mjs';
import fs from 'node:fs';
import path from 'node:path';

const WORKSPACE = 'C:/GestaoVersus/app32/tmp/presentations/investidores-recarga';
const OUT_PPTX = 'C:/GestaoVersus/app32/output/investidores/Pitch_Investimento_Recarga_Eletrica_em_revisao.pptx';
const SCRATCH = path.join(WORKSPACE, 'scratch_run3');
fs.mkdirSync(SCRATCH, { recursive: true });
fs.mkdirSync(path.dirname(OUT_PPTX), { recursive: true });

const W = 1920;
const H = 1080;
const presentation = Presentation.create({ slideSize: { width: W, height: H } });

const C = {
  navy: '#0B1324',
  navy2: '#1E2A44',
  teal: '#14B8A6',
  blue: '#2563EB',
  green: '#059669',
  amber: '#D97706',
  red: '#DC2626',
  text: '#0F172A',
  sub: '#475569',
  soft: '#F8FAFC',
  line: '#CBD5E1',
  softBlue: '#E0F2FE',
  softTeal: '#CCFBF1',
  softGold: '#FEF3C7',
  softGray: '#EEF2F7',
  softGreen: '#ECFDF5',
};

const annualRevenue = 364800000;
const annualResult = 94933188;
const annualInvestor = 23733297;
const fixedMonthly = 311500;
const monthlyRevenue = 30400000;
const monthlyContribution = 12868800;
const monthlyTax = 4646201;
const monthlyNetResult = 7911099;
const monthlyInvestor = 1977774.75;
const fixedAnnual = fixedMonthly * 12;
const annualContribution = 154425600;
const cmRatio = annualContribution / annualRevenue;

const structure = [
  { area: 'Comercial', setup: 340000, fixedMonth: 110000 },
  { area: 'Operacional', setup: 331000, fixedMonth: 109000 },
  { area: 'Adm/Fin', setup: 102500, fixedMonth: 92500 },
];

const products = [
  { name: 'Kit / equipamento principal', status: 'Ativado', revenue: 24000000, cmPct: 33.4, cmRs: 26736, volume: 300 },
  { name: 'Implantação / instalação', status: 'Modelado sem rampa', revenue: 0, cmPct: 35.3, cmRs: 14120, volume: 0 },
  { name: 'Software de gestão', status: 'Ativado', revenue: 6400000, cmPct: 75.8, cmRs: 1212, volume: 4000 },
  { name: 'Estudo de viabilidade / assessoria', status: 'A ativar', revenue: 0, cmPct: 0, cmRs: 0, volume: 0 },
  { name: 'Peças e upgrades', status: 'A ativar', revenue: 0, cmPct: 0, cmRs: 0, volume: 0 },
  { name: 'Manutenção especializada', status: 'A ativar', revenue: 0, cmPct: 0, cmRs: 0, volume: 0 },
];

const scenarios = [0.2, 0.5, 1.0].map((p) => {
  const revenue = monthlyRevenue * p;
  const contribution = monthlyContribution * p;
  const operating = contribution - fixedMonthly;
  const taxes = Math.max(operating, 0) * 0.37;
  const result = operating - taxes;
  return { p, revenue, contribution, taxes, result };
});

const market = {
  currentFleet: 411869,
  currentChargers: 21061,
  ratioCurrent: 19.6,
  deficitCurrent: 20126,
  projections: [
    { year: 2026, fleet: 639869, needed: 63987, deficit: 42926, incremental: 22800 },
    { year: 2027, fleet: 1004869, needed: 100487, deficit: 79426, incremental: 36500 },
    { year: 2028, fleet: 1588869, needed: 158887, deficit: 137826, incremental: 58400 },
    { year: 2029, fleet: 2523869, needed: 252387, deficit: 231326, incremental: 93500 },
    { year: 2030, fleet: 4023869, needed: 402387, deficit: 381326, incremental: 150000 },
  ],
};

function brl(v) {
  return 'R$ ' + Number(v).toLocaleString('pt-BR', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
}
function brl1(v) {
  return 'R$ ' + Number(v).toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
}
function pct(v) {
  return Number(v).toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + '%';
}
function baseFrame() {
  return { frame: { left: 0, top: 0, width: W, height: H }, baseUnit: 8 };
}
function T(value, size, opts = {}) {
  return text(value, {
    width: opts.width ?? fill,
    height: opts.height ?? hug,
    ...opts,
    style: {
      fontSize: size,
      color: opts.color ?? C.text,
      bold: opts.bold ?? false,
      align: opts.align,
      ...opts.style,
    },
  });
}
function section(title, subtitle) {
  return column({ width: fill, height: hug, gap: 8 }, [
    T(title, 40, { bold: true, color: C.navy }),
    rule({ width: fixed(160), stroke: C.teal, weight: 5 }),
    T(subtitle, 22, { width: wrap(1500), color: C.sub }),
  ]);
}
function bullets(items, size = 24) {
  return column({ width: fill, height: hug, gap: 10 }, items.map((item) => T(`• ${item}`, size, { color: C.sub })));
}
function card(label, value, fillColor) {
  return panel({ width: fill, height: fill, fill: fillColor, borderRadius: 22, padding: 22 }, column({ width: fill, gap: 10 }, [
    T(label, 21, { bold: true, color: C.sub }),
    T(value, 36, { bold: true, color: C.navy }),
  ]));
}
function tableCell(content, fillColor = '#FFFFFF') {
  return panel({ width: fill, height: fill, fill: fillColor, borderRadius: 14, padding: { x: 14, y: 12 } }, content);
}
function headerCell(label) {
  return panel({ width: fill, height: fill, fill: C.navy, borderRadius: 14, padding: { x: 14, y: 12 } }, T(label, 20, { bold: true, color: '#FFFFFF' }));
}

// 1 cover
{
  const s = presentation.slides.add();
  s.compose(layers({ width: fill, height: fill }, [
    shape({ width: fill, height: fill, fill: C.navy }),
    shape({ width: fixed(560), height: fixed(560), fill: '#17355E', borderRadius: 280 }),
    column({ width: fill, height: fill, padding: { x: 92, y: 82 }, gap: 22 }, [
      T('PIT DE INVESTIMENTO', 22, { color: C.teal, bold: true }),
      T('Infraestrutura de recarga elétrica para investidores', 62, { color: '#FFFFFF', bold: true, width: wrap(1200) }),
            panel({ width: wrap(1200), fill: '#162748', borderRadius: 22, padding: { x: 24, y: 20 } },
        T('A operação foi desenhada com 06 produtos, mas a modelagem atual considera apenas 02. Isso torna a tese financeira conservadora e preserva upside relevante.', 30, { color: '#FFFFFF', bold: true, width: wrap(1120) })
      ),
      row({ width: fill, gap: 18 }, [
        panel({ width: fixed(420), fill: '#0F766E', borderRadius: 16, padding: 16 }, T('Ramp-up até ago/2027', 24, { color: '#FFFFFF', bold: true, align: 'center' })),
        panel({ width: fixed(380), fill: '#1D4ED8', borderRadius: 16, padding: 16 }, T('Aporte: R$ 11,5 mi', 24, { color: '#FFFFFF', bold: true, align: 'center' })),
        panel({ width: fixed(420), fill: '#B45309', borderRadius: 16, padding: 16 }, T('Payback: 36m conservador | ~12m otimista', 24, { color: '#FFFFFF', bold: true, align: 'center' })),
      ]),
          ]),
  ]), baseFrame());
}

// 2 company
{
  const s = presentation.slides.add();
  s.compose(column({ width: fill, height: fill, padding: { x: 88, y: 68 }, gap: 26 }, [
    section('1. A empresa', 'Síntese da governança, valores e objetivos financeiros presentes no relatório.'),
    row({ width: fill, height: fixed(230), gap: 22 }, [
      card('Gestão e Governança', 'Previsão de conselho de administração, diretoria e gerências (coml, operacional, adm-fin)', C.softBlue),
      card('Liderança', 'César Lisboa na condução estratégica', C.softTeal),
      card('Capital', '100% próprio na largada', C.softGold),
    ]),
    row({ width: fill, height: fill, gap: 24 }, [
      panel({ width: fill, height: fill, fill: C.soft, borderRadius: 22, padding: 24 }, column({ width: fill, gap: 14 }, [
        T('Valores e diretrizes', 28, { bold: true, color: C.navy }),
        bullets([
          'Respeito aos valores do negócio e dos sócios.',
          'Segurança do investimento e da operação.',
          'Prioridade ao longo prazo e à execução por etapas.',
          'Valorização e respeito da cadeia produtiva: colaboradores, fornecedores e clientes.',
        ], 25),
      ])),
      panel({ width: fill, height: fill, fill: C.soft, borderRadius: 22, padding: 24 }, column({ width: fill, gap: 14 }, [
        T('Objetivos financeiros-base', 28, { bold: true, color: C.navy }),
        bullets([
          'Payback conservador de 36 meses, com leitura otimista próxima de 12 meses no fluxo projetado.',
          'Investimentos acionados conforme evolução de vendas, embora o plano consolide tudo em jul/2026.',
          'Formação de base recorrente e monetização da infraestrutura instalada.',
        ], 25),
      ])),
    ]),
  ]), baseFrame());
}

// 3 products activated detailed
{
  const activeProducts = [
    { name: 'Kit / equipamento principal', status: 'Ativado', qty: 300, unitPrice: 80000, mcPct: 33.4, mcUnit: 26736, mcTotal: 300 * 26736 },
    { name: 'Software de gestão', status: 'Ativado', qty: 4000, unitPrice: 1600, mcPct: 75.8, mcUnit: 1212, mcTotal: 4000 * 1212 },
  ];
  const rows = [
    headerCell('Produto'), headerCell('Status'), headerCell('Qtd. vendida pós-ramp-up'), headerCell('Valor unitário'), headerCell('MC %'), headerCell('MC unitária'), headerCell('MC total'),
    ...activeProducts.flatMap((p, i) => {
      const bg = i % 2 === 0 ? '#F8FAFC' : '#EEF2F7';
      return [
        tableCell(T(p.name, 18, { color: C.text }), bg),
        tableCell(T(p.status, 18, { bold: true, color: p.status === 'Ativado' ? C.green : C.amber }), bg),
        tableCell(T(String(p.qty), 18, { bold: true, color: C.text }), bg),
        tableCell(T(brl(p.unitPrice), 18, { color: C.text }), bg),
        tableCell(T(pct(p.mcPct), 18, { color: C.text }), bg),
        tableCell(T(brl(p.mcUnit), 18, { color: C.text }), bg),
        tableCell(T(brl(p.mcTotal), 18, { bold: true, color: C.navy }), bg),
      ];
    }),
  ];
  const s = presentation.slides.add();
  s.compose(column({ width: fill, height: fill, padding: { x: 62, y: 54 }, gap: 18 }, [
    section('2. Produtos ativados: visão detalhada', 'Detalhamento dos produtos hoje modelados, com quantidade vendida pós-ramp-up, valor unitário e margem de contribuição.'),
    grid({ width: fill, height: fixed(420), columns: [fr(1.45), fr(0.62), fr(0.82), fr(0.76), fr(0.42), fr(0.72), fr(0.8)], rows: [auto, auto, auto, auto], columnGap: 10, rowGap: 10 }, rows),
    row({ width: fill, height: fill, gap: 18 }, [
      card('Faturamento mensal pós-ramp-up', brl(monthlyRevenue), C.softBlue),
      card('MC mensal do plano revisado', brl(monthlyContribution), C.softTeal),
      card('Produtos com rampa efetiva', '02', C.softGold),
    ]),
    panel({ width: fill, fill: C.softGreen, borderRadius: 18, padding: 16 }, T('Os 2 produtos acima sustentam a receita, a margem e o resultado pós-ramp-up do plano atual.', 22, { color: '#065F46', bold: true })),
  ]), baseFrame());
}

// 3b products to activate
{
  const futureRows = [
    headerCell('Produto'), headerCell('Status'), headerCell('Qtd. vendida pós-ramp-up'), headerCell('Valor unitário'), headerCell('MC %'), headerCell('MC unitária'), headerCell('MC total'),
    ...[
      'Implantação / instalação',
      'Estudo de viabilidade / assessoria',
      'Peças e upgrades',
      'Manutenção especializada',
    ].flatMap((name, i) => {
      const bg = i % 2 === 0 ? '#F8FAFC' : '#EEF2F7';
      return [
        tableCell(T(name, 18, { color: C.text }), bg),
        tableCell(T('A ativar', 18, { bold: true, color: C.amber }), bg),
        tableCell(T('A estruturar', 18, { color: C.sub }), bg),
        tableCell(T('A estruturar', 18, { color: C.sub }), bg),
        tableCell(T('-', 18, { color: C.sub }), bg),
        tableCell(T('-', 18, { color: C.sub }), bg),
        tableCell(T('-', 18, { color: C.sub }), bg),
      ];
    }),
  ];
  const s = presentation.slides.add();
  s.compose(column({ width: fill, height: fill, padding: { x: 62, y: 54 }, gap: 18 }, [
    section('3. Produtos a ativar: espaço de upside', 'Há 4 frentes adicionais passíveis de ativação ao longo da execução, sem depender delas para a tese-base fechar.'),
    grid({ width: fill, height: fixed(420), columns: [fr(1.45), fr(0.62), fr(0.82), fr(0.76), fr(0.42), fr(0.72), fr(0.8)], rows: [auto, auto, auto, auto, auto], columnGap: 10, rowGap: 10 }, futureRows),
    row({ width: fill, height: fill, gap: 18 }, [
      panel({ width: fill, height: fill, fill: C.soft, borderRadius: 20, padding: 20 }, column({ width: fill, gap: 12 }, [
        T('O que esses produtos podem adicionar', 24, { bold: true, color: C.navy }),
        bullets([
          'Mais recorrência e maior captura de valor por cliente.',
          'Elevação de ticket médio e extensão do ciclo de monetização.',
          'Redução de dependência exclusiva do hardware e implantação.',
        ], 21),
      ])),
      panel({ width: fill, height: fill, fill: C.soft, borderRadius: 20, padding: 20 }, column({ width: fill, gap: 12 }, [
        T('Mensagem para investidores', 24, { bold: true, color: C.navy }),
        bullets([
          'A operação já fecha com 2 produtos contribuindo para o resultado.',
          'Ainda há 4 frentes adicionais passíveis de ativação.',
          'Portanto, o resultado atual é conservador.',
          'O upside está na ativação organizada desse segundo bloco do portfólio.',
        ], 21),
      ])),
    ]),
  ]), baseFrame());
}

// 4 market demand
{
  const s = presentation.slides.add();
  s.compose(column({ width: fill, height: fill, padding: { x: 88, y: 68 }, gap: 24 }, [
    section('4. Demanda do mercado / déficit de infraestrutura', 'Base observada: 411,9 mil veículos plug-in e 21,1 mil pontos públicos/semi-públicos. Cenário-base de demanda calibrado para 2026-2030.'),
    row({ width: fill, height: fixed(220), gap: 22 }, [
      card('Frota plug-in atual', market.currentFleet.toLocaleString('pt-BR'), C.softBlue),
      card('Pontos atuais de recarga', market.currentChargers.toLocaleString('pt-BR'), C.softTeal),
      card('Relação atual', `${String(market.ratioCurrent).replace('.', ',')}:1`, C.softGold),
      card('Déficit atual p/ 10:1', market.deficitCurrent.toLocaleString('pt-BR'), '#FCE7F3'),
    ]),
    grid({ width: fill, height: fixed(420), columns: [fr(0.52), fr(0.9), fr(0.9), fr(0.95), fr(0.95)], rows: [auto, auto, auto, auto, auto, auto], columnGap: 12, rowGap: 10 }, [
      headerCell('Ano'), headerCell('Frota projetada'), headerCell('Pontos necessários (10:1)'), headerCell('Déficit acumulado'), headerCell('Demanda incremental no ano'),
      ...market.projections.flatMap((m, i) => {
        const bg = i % 2 === 0 ? C.soft : C.softGray;
        return [
          tableCell(T(String(m.year), 20, { bold: true }), bg),
          tableCell(T(m.fleet.toLocaleString('pt-BR'), 20), bg),
          tableCell(T(m.needed.toLocaleString('pt-BR'), 20), bg),
          tableCell(T(m.deficit.toLocaleString('pt-BR'), 20, { bold: true, color: C.amber }), bg),
          tableCell(T(m.incremental.toLocaleString('pt-BR'), 20, { bold: true, color: C.green }), bg),
        ];
      }),
    ]),
    T('Nota: relação ideal de 10 veículos por ponto; 2027-2030 projetados em cenário-base de planejamento, alinhado à tendência setorial de expansão da frota.', 18, { color: C.sub }),
  ]), baseFrame());
}

// 5 structure
{
  const s = presentation.slides.add();
  const rows = [headerCell('Estrutura'), headerCell('Custo de setup'), headerCell('Custo fixo mensal'), headerCell('Leitura resumida')];
  structure.forEach((a, i) => {
    const bg = i % 2 === 0 ? C.soft : C.softGray;
    rows.push(
      tableCell(T(a.area, 21, { bold: true }), bg),
      tableCell(T(brl(a.setup), 21), bg),
      tableCell(T(brl(a.fixedMonth), 21), bg),
      tableCell(T(a.area === 'Comercial' ? 'Prospecção, vendas e ativação de receita' : a.area === 'Operacional' ? 'Implantação, suporte técnico e entrega' : 'Backoffice, gestão financeira e administração', 20, { color: C.sub }), bg),
    );
  });
  s.compose(column({ width: fill, height: fill, padding: { x: 88, y: 68 }, gap: 24 }, [
    section('5. Estrutura: Comercial, Operacional e Adm-Fin', 'Custos de estrutura resumidos a partir das frentes planejadas e do total mensal de custos/despesas fixas do PDF 03.'),
    row({ width: fill, height: fixed(210), gap: 20 }, [
      card('Setup total das frentes', brl(773500), C.softBlue),
      card('Custo fixo mensal total', brl(fixedMonthly), C.softTeal),
      card('Custo fixo anual', brl(fixedAnnual), C.softGold),
    ]),
    grid({ width: fill, height: fixed(350), columns: [fr(0.75), fr(0.65), fr(0.75), fr(1.35)], rows: [auto, auto, auto, auto], columnGap: 14, rowGap: 10 }, rows),
  ]), baseFrame());
}

// 6 result scenarios
{
  const s = presentation.slides.add();
  const rows = [headerCell('Cenário'), headerCell('Receita mensal'), headerCell('Margem de contribuição'), headerCell('Custo fixo mensal'), headerCell('Impostos'), headerCell('Resultado líquido mensal')];
  scenarios.forEach((sc, i) => {
    const bg = i % 2 === 0 ? C.soft : C.softGray;
    rows.push(
      tableCell(T(`${sc.p * 100}% das vendas`, 20, { bold: true }), bg),
      tableCell(T(brl(sc.revenue), 20), bg),
      tableCell(T(brl(sc.contribution), 20), bg),
      tableCell(T(brl(fixedMonthly), 20), bg),
      tableCell(T(brl(sc.taxes), 20), bg),
      tableCell(T(brl(sc.result), 20, { bold: true, color: sc.result > 0 ? C.green : C.red }), bg),
    );
  });
  s.compose(column({ width: fill, height: fill, padding: { x: 78, y: 58 }, gap: 22 }, [
    section('6. Resultado líquido: 20%, 50% e 100% das vendas', 'Cenários mensais pós-ramp-up, mantendo a mesma base de custo fixo e a mesma estrutura de margem/tributação do planejamento revisado.'),
    grid({ width: fill, height: fixed(360), columns: [fr(0.7), fr(0.82), fr(0.95), fr(0.8), fr(0.75), fr(0.95)], rows: [auto, auto, auto, auto], columnGap: 12, rowGap: 10 }, rows),
    row({ width: fill, height: fill, gap: 22 }, [
      panel({ width: fill, height: fill, fill: C.soft, borderRadius: 22, padding: 22 }, column({ width: fill, gap: 14 }, [
        T('Interpretação', 26, { bold: true, color: C.navy }),
        bullets([
          'O negócio permanece positivo mesmo em 20% do volume de vendas do plano revisado.',
          'Em 50% das vendas, o resultado líquido mensal já supera R$ 3,86 milhões.',
          'Em 100%, o resultado líquido mensal alcança R$ 7,91 milhões.',
        ], 23),
      ])),
      panel({ width: fill, height: fill, fill: C.soft, borderRadius: 22, padding: 22 }, column({ width: fill, gap: 14 }, [
        T('Premissas do cálculo', 26, { bold: true, color: C.navy }),
        bullets([
          'Receita mensal pós-ramp-up de R$ 30,4 milhões no cenário de 100%.',
          'Custo fixo mensal de R$ 311,5 mil.',
          'Mesma relação de margem e mesma carga tributária efetiva observada no PDF 03.',
        ], 23),
      ])),
    ]),
  ]), baseFrame());
}

// 7 investment
{
  const s = presentation.slides.add();
  s.compose(column({ width: fill, height: fill, padding: { x: 88, y: 68 }, gap: 24 }, [
    section('7. Investimento necessário', 'Composição do investimento segundo o PDF 03 e leitura prática para o investidor.'),
    row({ width: fill, height: fixed(220), gap: 20 }, [
      card('Caixa', brl(1900000), C.softBlue),
      card('Estoques', brl(8820000), C.softTeal),
      card('Investimentos fixos', brl(462000), C.softGold),
      card('Total investimento', brl(11500000), '#FCE7F3'),
    ]),
    row({ width: fill, height: fill, gap: 22 }, [
      panel({ width: fill, height: fill, fill: C.soft, borderRadius: 22, padding: 24 }, column({ width: fill, gap: 14 }, [
        T('Detalhamento do investimento', 28, { bold: true, color: C.navy }),
        bullets([
          '6 meses de custos e despesas fixas: R$ 1,9 milhão.',
          '1 container de 36 unidades: R$ 1,764 milhão.',
          '3 containers de 36 unidades: R$ 5,292 milhões.',
          '1 container adicional de 36 unidades: R$ 1,764 milhão.',
          'Investimentos fixos mapeados no plano: aproximadamente R$ 462 mil.',
          'Taxa de dólar considerada no modelo: R$ 5,00.',
        ], 23),
      ])),
      panel({ width: fill, height: fill, fill: C.soft, borderRadius: 22, padding: 24 }, column({ width: fill, gap: 14 }, [
        T('Leitura executiva', 28, { bold: true, color: C.navy }),
        bullets([
          'O investimento é majoritariamente direcionado a estoque e capacidade de entrega.',
          'O capital de giro reduz risco de execução no ramp-up.',
          'O plano nasce sem dependência de alavancagem financeira externa na largada.',
        ], 23),
      ])),
    ]),
  ]), baseFrame());
}

// 8 investor premises
{
  const s = presentation.slides.add();
  s.compose(column({ width: fill, height: fill, padding: { x: 88, y: 68 }, gap: 24 }, [
    section('8. Premissas financeiras do investidor', 'Premissas do PDF 03 combinadas com o fluxo mensal revisado do investidor, a partir de nov/2026.'),
    grid({ width: fill, height: fixed(240), columns: [fr(1), fr(1), fr(1), fr(1), fr(1)], columnGap: 18 }, [
      card('Distribuição ao investidor', '25%', C.softBlue),
      card('Custo de oportunidade', '12% a.a.', C.softTeal),
      card('TIR estimada*', '142,2% a.a.', C.softGold),
      card('VPL estimado*', brl(10797483), '#FCE7F3'),
      card('Payback do investidor*', '~10,2 meses', '#EDE9FE'),
    ]),
    row({ width: fill, height: fill, gap: 22 }, [
      panel({ width: fill, height: fill, fill: C.soft, borderRadius: 22, padding: 24 }, column({ width: fill, gap: 14 }, [
        T('Leitura das premissas', 28, { bold: true, color: C.navy }),
        bullets([
          'O PDF 03 explicita distribuição de 25% a partir de nov/2026; nesta versão, a métrica foi recalculada com o fluxo mensal do próprio plano.',
          'O investidor participa do upside sem depender da ativação das outras 4 frentes de produto.',
          'O retorno calculado não depende de aumento de preço ou redução de custo fixo.',
        ], 23),
      ])),
      panel({ width: fill, height: fill, fill: C.soft, borderRadius: 22, padding: 24 }, column({ width: fill, gap: 14 }, [
        T('Notas metodológicas', 28, { bold: true, color: C.navy }),
        bullets([
          'TIR anualizada a partir da TIR mensal do fluxo jul/2026 a dez/2027.',
          'VPL calculado com custo de oportunidade de 12% a.a., convertido para taxa mensal.',
          'Taxa de dólar considerada no modelo: R$ 5,00.',
          'Os indicadores não incorporam upside dos produtos ainda não ativados.',
        ], 23),
      ])),
    ]),
  ]), baseFrame());
}

// 9 business cash flow
{
  const monthRevenue = monthlyRevenue;
  const monthContribution = monthlyContribution;
  const monthResult = monthlyNetResult;
  const s = presentation.slides.add();
  s.compose(column({ width: fill, height: fill, padding: { x: 88, y: 68 }, gap: 24 }, [
    section('9. Fluxo de caixa do negócio (resumido)', 'Set/2027 foi tratado como o primeiro mês cheio após o ramp-up; 2028 representa sua equivalência anualizada em 12 meses estáveis.'),
    row({ width: fill, height: fixed(280), gap: 22 }, [
      panel({ width: fill, height: fill, fill: C.softBlue, borderRadius: 24, padding: 24 }, column({ width: fill, gap: 12 }, [
        T('Set/2027 (1 mês após o ramp-up)', 26, { bold: true, color: C.navy }),
        T(`Receita: ${brl1(monthRevenue)}`, 24, { color: C.text }),
        T(`Margem de contribuição: ${brl1(monthContribution)}`, 24, { color: C.text }),
        T(`Custo fixo: ${brl(fixedMonthly)}`, 24, { color: C.text }),
        T(`Resultado líquido estimado: ${brl1(monthResult)}`, 24, { color: C.green, bold: true }),
      ])),
      panel({ width: fill, height: fill, fill: C.softTeal, borderRadius: 24, padding: 24 }, column({ width: fill, gap: 12 }, [
        T('Ano cheio 2028 (jan-dez)', 26, { bold: true, color: C.navy }),
        T(`Receita anual: ${brl(annualRevenue)}`, 24, { color: C.text }),
        T(`Margem de contribuição anualizada: ${brl(annualContribution)}`, 24, { color: C.text }),
        T(`Custo fixo anual: ${brl(fixedAnnual)}`, 24, { color: C.text }),
        T(`Resultado líquido anualizado: ${brl(annualResult)}`, 24, { color: C.green, bold: true }),
      ])),
    ]),
    panel({ width: fill, height: fill, fill: C.soft, borderRadius: 22, padding: 24 }, column({ width: fill, gap: 14 }, [
      T('Leitura complementar', 28, { bold: true, color: C.navy }),
      bullets([
        'No planejamento revisado, o mês pós-ramp-up entrega cerca de R$ 7,91 milhões de resultado líquido.',
        'A equivalência anualizada desse mesmo patamar leva o resultado para R$ 94,93 milhões.',
        'Isso reforça a leitura de forte alavancagem após a fase de implantação e ativação comercial.',
      ], 23),
    ])),
  ]), baseFrame());
}

// 10 investor cash flow
{
  const monthInvestor = monthlyInvestor;
  const s = presentation.slides.add();
  s.compose(column({ width: fill, height: fill, padding: { x: 88, y: 68 }, gap: 24 }, [
    section('10. Fluxo de caixa do investidor (resumido)', 'Distribuição do investidor em um mês após o ramp-up e na equivalência anualizada, mantendo 25% de participação sobre o resultado líquido revisado.'),
    row({ width: fill, height: fixed(260), gap: 22 }, [
      panel({ width: fill, height: fill, fill: C.softGold, borderRadius: 24, padding: 24 }, column({ width: fill, gap: 12 }, [
        T('Aporte inicial', 26, { bold: true, color: C.navy }),
        T(brl(11500000), 42, { bold: true, color: C.red }),
        T('Momento-base: jul/2026', 22, { color: C.sub }),
      ])),
      panel({ width: fill, height: fill, fill: C.softBlue, borderRadius: 24, padding: 24 }, column({ width: fill, gap: 12 }, [
        T('Set/2027', 26, { bold: true, color: C.navy }),
        T(`Distribuição mensal estimada: ${brl1(monthInvestor)}`, 28, { bold: true, color: C.green }),
        T('1 mês após o fim do ramp-up', 22, { color: C.sub }),
      ])),
      panel({ width: fill, height: fill, fill: C.softTeal, borderRadius: 24, padding: 24 }, column({ width: fill, gap: 12 }, [
        T('Ano cheio 2028', 26, { bold: true, color: C.navy }),
        T(`Distribuição anualizada: ${brl(annualInvestor)}`, 28, { bold: true, color: C.green }),
        T(`Média mensal: ${brl1(monthInvestor)}`, 22, { color: C.sub }),
      ])),
    ]),
    panel({ width: fill, height: fill, fill: C.soft, borderRadius: 22, padding: 24 }, column({ width: fill, gap: 14 }, [
        T('Interpretação', 28, { bold: true, color: C.navy }),
        bullets([
          'A remuneração do investidor acontece com base em um fluxo já viável com 2 produtos contribuindo para o resultado.',
          'A ativação das outras 4 frentes funciona como upside opcional, não como condição para a tese-base fechar.',
          'Esse desenho melhora a assimetria risco-retorno da oportunidade.',
        ], 23),
      ])),
  ]), baseFrame());
}

// 11 closing
{
  const s = presentation.slides.add();
  s.compose(layers({ width: fill, height: fill }, [
    shape({ width: fill, height: fill, fill: C.navy2 }),
    column({ width: fill, height: fill, padding: { x: 96, y: 88 }, gap: 24 }, [
      T('11. Fechamento', 24, { color: C.teal, bold: true }),
      T('A tese fecha com 2 produtos contribuindo para o resultado atual e pode ganhar potência adicional com a ativação de mais 4 frentes do portfólio.', 58, { color: '#FFFFFF', bold: true, width: wrap(1500) }),
      panel({ width: wrap(1520), fill: '#24365B', borderRadius: 24, padding: { x: 28, y: 24 } }, T('O investidor entra em uma operação desenhada para 6 produtos, mas com apenas 2 sustentando a rampa financeira hoje. Isso preserva uma leitura conservadora e mantém upside concreto de receita, margem e recorrência.', 30, { color: '#E2E8F0', width: wrap(1450) })),
      row({ width: fill, gap: 18 }, [
        panel({ width: fixed(390), fill: '#0F766E', borderRadius: 16, padding: 16 }, T('Mercado com tendência estrutural', 24, { color: '#FFFFFF', bold: true, align: 'center' })),
        panel({ width: fixed(420), fill: '#1D4ED8', borderRadius: 16, padding: 16 }, T('Modelo com recorrência e margem', 24, { color: '#FFFFFF', bold: true, align: 'center' })),
        panel({ width: fixed(500), fill: '#B45309', borderRadius: 16, padding: 16 }, T('Upside fora da conta atual', 24, { color: '#FFFFFF', bold: true, align: 'center' })),
      ]),
      column({ width: fill, gap: 10 }, [
        T('• Base conservadora, não teto de resultado.', 24, { color: '#CBD5E1' }),
        T('• Execução bem-sucedida pode ativar novas avenidas de faturamento.', 24, { color: '#CBD5E1' }),
        T('• Case atrativo para investidor que busca retorno com assimetria positiva.', 24, { color: '#CBD5E1' }),
      ]),
          ]),
  ]), baseFrame());
}

const blob = await PresentationFile.exportPptx(presentation);
await blob.save(OUT_PPTX);
await blob.save(path.join(WORKSPACE, 'output', 'output.pptx'));
for (let i = 0; i < presentation.slides.items.length; i += 1) {
  const slide = presentation.slides.items[i];
  const canvas = new Canvas(W, H);
  const ctx = canvas.getContext('2d');
  await drawSlideToCtx(slide, presentation, ctx);
  await canvas.toFile(path.join(SCRATCH, `slide-${String(i + 1).padStart(2, '0')}.png`));
}
console.log(JSON.stringify({ pptx: OUT_PPTX, slides: presentation.slides.items.length }, null, 2));

