from __future__ import annotations

from pathlib import Path
from urllib.parse import unquote, urlparse

import psycopg2
from psycopg2.extras import execute_values

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT.parent / ".env" if (ROOT.parent / ".env").exists() else ROOT / ".env"
CLIENT_CODE = "M1"
COMPANY_NAME = "Empresa Teste Versus"

AREAS = [
    {
        "code": "GER",
        "name": "Gerenciais",
        "description": "Processos de direção, inovação e decisões estratégicas da indústria de autopeças.",
        "color": "#2563eb",
        "macros": [
            {
                "code": "GER.01",
                "name": "Planejamento Estratégico",
                "owner": "Diretoria Executiva",
                "description": "Define posicionamento, metas e prioridades comerciais, industriais e digitais.",
                "processes": [
                    ("GER.01.01", "Analisar mercado de reposição automotiva", "Consolida inteligência de mercado por região, categoria de peça e canal digital.", "Estratégia"),
                    ("GER.01.02", "Definir metas e portfólio prioritário", "Desdobra metas por linhas de produto, margem, giro e nível de serviço.", "Diretoria"),
                    ("GER.01.03", "Acompanhar indicadores estratégicos", "Monitora crescimento, rentabilidade, satisfação do lojista e eficiência produtiva.", "Controladoria Estratégica"),
                ],
            },
            {
                "code": "GER.02",
                "name": "Pesquisa e Desenvolvimento",
                "owner": "Engenharia de Produto",
                "description": "Evolui produtos, embalagens e aplicações para o mercado de reposição.",
                "processes": [
                    ("GER.02.01", "Capturar necessidades de lojistas e aplicadores", "Coleta demandas, reclamações e oportunidades vindas do pós-venda e canais digitais.", "P&D"),
                    ("GER.02.02", "Desenvolver novos componentes", "Projeta, prototipa e valida autopeças para novas aplicações e veículos.", "Engenharia"),
                    ("GER.02.03", "Homologar alterações técnicas", "Valida especificações, testes e documentação antes da liberação comercial.", "Qualidade Técnica"),
                ],
            },
        ],
    },
    {
        "code": "FIN",
        "name": "Finalísticos",
        "description": "Processos que criam, vendem, produzem e entregam valor ao pequeno lojista.",
        "color": "#16a34a",
        "macros": [
            {
                "code": "FIN.01",
                "name": "Propaganda e Publicidade",
                "owner": "Marketing Digital",
                "description": "Atrai lojistas em todo o Brasil por campanhas digitais e conteúdo técnico.",
                "processes": [
                    ("FIN.01.01", "Planejar campanhas digitais", "Define calendário, verba e públicos por região, linha de autopeças e sazonalidade.", "Marketing"),
                    ("FIN.01.02", "Produzir conteúdo técnico-comercial", "Cria vídeos, comparativos, posts e materiais para ajudar o lojista a vender melhor.", "Conteúdo"),
                    ("FIN.01.03", "Medir conversão de mídia em vendas", "Acompanha leads, tráfego, pedidos e ROI por campanha.", "Growth"),
                ],
            },
            {
                "code": "FIN.02",
                "name": "Vendas / Pós-Venda",
                "owner": "Comercial B2B Digital",
                "description": "Converte, atende e fideliza pequenos lojistas via e-commerce, WhatsApp e equipe interna.",
                "processes": [
                    ("FIN.02.01", "Cadastrar e qualificar lojistas", "Valida dados comerciais, região, perfil de compra e condições de atendimento.", "Inside Sales"),
                    ("FIN.02.02", "Atender pedidos digitais", "Apoia cotações, disponibilidade, prazos e condições de venda para lojistas.", "Vendas Digitais"),
                    ("FIN.02.03", "Gerir relacionamento pós-venda", "Acompanha entregas, devoluções, garantias e recompra.", "Sucesso do Cliente"),
                    ("FIN.02.04", "Resolver garantias e trocas", "Recebe evidências, classifica causas e conduz tratativas comerciais e técnicas.", "Pós-Venda Técnico"),
                ],
            },
            {
                "code": "FIN.03",
                "name": "Produção / Entrega",
                "owner": "Operações Industriais",
                "description": "Planeja, fabrica, embala, expede e entrega pedidos nacionais de autopeças.",
                "processes": [
                    ("FIN.03.01", "Planejar produção por demanda digital", "Converte pedidos e previsão de vendas em ordens de produção e prioridades de estoque.", "PCP"),
                    ("FIN.03.02", "Fabricar e controlar qualidade das autopeças", "Executa produção, inspeções e liberação técnica por lote.", "Produção"),
                    ("FIN.03.03", "Separar, embalar e faturar pedidos", "Realiza picking, embalagem, conferência fiscal e preparação para transporte.", "Expedição"),
                    ("FIN.03.04", "Despachar e acompanhar entregas nacionais", "Integra transportadoras, rastreia ocorrências e confirma entrega ao lojista.", "Logística"),
                ],
            },
        ],
    },
    {
        "code": "APO",
        "name": "Apoio",
        "description": "Processos que sustentam pessoas, finanças, compliance, estoques e ativos da operação.",
        "color": "#f97316",
        "macros": [
            {
                "code": "APO.01",
                "name": "Gerir Pessoas",
                "owner": "RH",
                "description": "Garante capacidade humana, segurança e desenvolvimento das equipes.",
                "processes": [
                    ("APO.01.01", "Recrutar e integrar colaboradores", "Seleciona, contrata e integra profissionais para operação, comercial e suporte.", "RH"),
                    ("APO.01.02", "Treinar equipes operacionais e comerciais", "Capacita times em produto, qualidade, segurança e atendimento B2B.", "Treinamento"),
                    ("APO.01.03", "Gerir saúde, segurança e desempenho", "Monitora requisitos trabalhistas, segurança industrial e performance individual.", "RH / SESMT"),
                ],
            },
            {
                "code": "APO.02",
                "name": "Gerir Recursos Financeiros",
                "owner": "Financeiro",
                "description": "Administra caixa, crédito, cobrança, pagamentos e rentabilidade.",
                "processes": [
                    ("APO.02.01", "Gerir contas a receber B2B", "Controla faturamento, boletos, PIX, cartão e inadimplência de lojistas.", "Financeiro"),
                    ("APO.02.02", "Gerir contas a pagar e fornecedores", "Planeja pagamentos de matéria-prima, serviços, fretes e despesas operacionais.", "Contas a Pagar"),
                    ("APO.02.03", "Projetar fluxo de caixa e margens", "Acompanha capital de giro, margem por SKU e necessidade de financiamento.", "Controladoria"),
                ],
            },
            {
                "code": "APO.03",
                "name": "Gerir Tributos e Fisco",
                "owner": "Fiscal / Contábil",
                "description": "Assegura apuração tributária, documentos fiscais e obrigações acessórias.",
                "processes": [
                    ("APO.03.01", "Classificar produtos e regras fiscais", "Mantém NCM, CST/CSOSN, CFOP, origem e regras por UF.", "Fiscal"),
                    ("APO.03.02", "Emitir e escriturar documentos fiscais", "Garante emissão, validação e escrituração de notas de venda, devolução e frete.", "Faturamento Fiscal"),
                    ("APO.03.03", "Apurar tributos e obrigações acessórias", "Consolida impostos, declarações e evidências para fiscalização.", "Contabilidade"),
                ],
            },
            {
                "code": "APO.04",
                "name": "Gerir Estoques",
                "owner": "Suprimentos e Almoxarifado",
                "description": "Controla matéria-prima, componentes, produtos acabados e níveis de reposição.",
                "processes": [
                    ("APO.04.01", "Planejar reposição de materiais", "Define necessidades de compra por demanda, lead time e estoque mínimo.", "Suprimentos"),
                    ("APO.04.02", "Receber e armazenar materiais", "Conferência, endereçamento e controle de lotes de insumos e componentes.", "Almoxarifado"),
                    ("APO.04.03", "Inventariar produtos e componentes", "Realiza contagens cíclicas, ajustes e análise de divergências.", "Estoque"),
                ],
            },
            {
                "code": "APO.05",
                "name": "Gerir Ativos",
                "owner": "Manutenção / Patrimônio",
                "description": "Mantém máquinas, ferramentas, infraestrutura e ativos digitais operacionais.",
                "processes": [
                    ("APO.05.01", "Cadastrar e controlar ativos industriais", "Registra máquinas, moldes, ferramentas, equipamentos e vida útil.", "Patrimônio"),
                    ("APO.05.02", "Executar manutenção preventiva", "Planeja e executa manutenções para reduzir paradas e perdas de produção.", "Manutenção"),
                    ("APO.05.03", "Gerir infraestrutura de tecnologia", "Mantém e-commerce, integrações, coletores, rede e sistemas de apoio.", "TI"),
                ],
            },
        ],
    },
]

SIPOC = {
    "macro_code": "FIN.03",
    "title": "SIPOC — Produção / Entrega",
    "objective": "Enquadrar a cadeia ponta a ponta que transforma demanda digital de lojistas em autopeças produzidas, faturadas e entregues em todo o Brasil.",
    "start_boundary": "Pedido confirmado no canal digital ou necessidade de reposição aprovada pelo PCP.",
    "end_boundary": "Entrega confirmada ao lojista, documentação fiscal concluída e ocorrência logística encerrada.",
    "trigger_event": "Entrada de pedidos B2B no e-commerce/WhatsApp ou sinal de estoque abaixo do ponto de reposição.",
    "customer_requirements": "Prazo confiável, peça correta, embalagem íntegra, nota fiscal sem divergência, rastreio ativo e suporte rápido em ocorrência.",
    "constraints_notes": "Capacidade produtiva, disponibilidade de matéria-prima, regras fiscais por UF, janela de coleta das transportadoras e SLA prometido no canal digital.",
    "measures_notes": "OTIF, lead time pedido-entrega, taxa de retrabalho, ruptura de estoque, acuracidade de picking, devoluções por erro e custo de frete por pedido.",
    "risks_notes": "Ruptura de insumos, falha de qualidade por lote, erro fiscal interestadual, avaria no transporte, promessa comercial incompatível com capacidade e atraso de transportadora.",
    "notes": "Material demonstrativo para portfólio Versus; indústria fictícia de autopeças com venda B2B digital para pequenos lojistas.",
    "items": [
        ("supplier", "Lojistas compradores", "Pedidos confirmados, prioridades comerciais e feedback de mercado.", 1, True),
        ("supplier", "Fornecedores de matéria-prima e componentes", "Insumos, componentes, embalagens e certificados técnicos.", 2, True),
        ("supplier", "Marketing e Vendas Digitais", "Previsão de demanda, campanhas ativas e condições prometidas ao cliente.", 3, False),
        ("supplier", "Transportadoras parceiras", "Janelas de coleta, tabelas de frete e cobertura nacional.", 4, True),
        ("input", "Pedido B2B aprovado", "Itens, quantidades, endereço, condição comercial e prazo prometido.", 1, True),
        ("input", "Plano de produção e estoque", "Ordens, prioridades, disponibilidade de produto acabado e necessidade de fabricação.", 2, True),
        ("input", "Materiais e especificações técnicas", "Componentes, matéria-prima, embalagem, ficha técnica e parâmetros de qualidade.", 3, True),
        ("input", "Regras fiscais e logísticas", "NCM, CFOP, tributação por UF, etiqueta, romaneio e regras de transporte.", 4, True),
        ("process", "Planejar produção e separação", "PCP prioriza ordens e reservas conforme demanda digital e estoque disponível.", 1, True),
        ("process", "Fabricar e inspecionar autopeças", "Produção executa etapas industriais, registra lote e qualidade libera conformidade.", 2, True),
        ("process", "Separar, embalar e faturar", "Expedição realiza picking, conferência, embalagem, emissão fiscal e documentação de envio.", 3, True),
        ("process", "Despachar e monitorar entrega", "Logística aciona transportadora, envia rastreio e trata ocorrências até a confirmação.", 4, True),
        ("output", "Autopeças conformes e embaladas", "Itens corretos, rastreáveis por lote e protegidos para transporte nacional.", 1, True),
        ("output", "Pedido faturado e documentado", "Nota fiscal, romaneio, etiqueta e informações fiscais consistentes.", 2, True),
        ("output", "Entrega rastreável", "Código de rastreio, status logístico e confirmação de recebimento.", 3, True),
        ("output", "Dados de desempenho operacional", "Indicadores de prazo, qualidade, custo, devoluções e ocorrências.", 4, False),
        ("customer", "Pequenos lojistas de autopeças", "Recebem os produtos para revenda com prazo e confiabilidade.", 1, True),
        ("customer", "Equipe de Vendas / Pós-Venda", "Recebe status, evidências e insumos para comunicação com o cliente.", 2, False),
        ("customer", "Financeiro e Fiscal", "Recebem faturamento, comprovantes e eventos para conciliação e obrigações.", 3, False),
        ("customer", "Diretoria de Operações", "Recebe indicadores para decisões de capacidade, estoque e logística.", 4, False),
    ],
}


def database_url() -> str:
    for line in ENV_PATH.read_text(encoding="utf-8", errors="ignore").splitlines():
        if line.startswith("DATABASE_URL="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError(f"DATABASE_URL não encontrado em {ENV_PATH}")


def connect():
    parsed = urlparse(database_url())
    return psycopg2.connect(
        host=parsed.hostname,
        port=parsed.port or 5432,
        user=unquote(parsed.username or ""),
        password=unquote(parsed.password or ""),
        dbname=(parsed.path or "").lstrip("/"),
    )


def main() -> None:
    conn = connect()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("select id, name from companies where client_code = %s order by id", (CLIENT_CODE,))
                row = cur.fetchone()
                if not row:
                    raise RuntimeError(f"Empresa com client_code={CLIENT_CODE!r} não encontrada")
                company_id = row[0]

                cur.execute(
                    """
                    update companies
                       set name=%s,
                           legal_name=%s,
                           description=%s,
                           industry=%s,
                           size=%s,
                           city=%s,
                           state=%s,
                           coverage_online=%s,
                           mvv_mission=%s,
                           mvv_vision=%s,
                           mvv_values=%s,
                           updated_at=now()
                     where id=%s
                    """,
                    (
                        COMPANY_NAME,
                        "M1 Autopeças Digitais Ltda. (fictícia)",
                        "Indústria fictícia de autopeças para demonstrações do portfólio Versus, com venda B2B digital para pequenos lojistas em todo o Brasil.",
                        "Indústria de autopeças",
                        "PME industrial",
                        "Feira de Santana",
                        "BA",
                        "Brasil inteiro via internet",
                        "Produzir e entregar autopeças confiáveis que ajudem pequenos lojistas a vender mais com agilidade e segurança.",
                        "Ser referência nacional em distribuição digital B2B de autopeças para o varejo independente.",
                        "Qualidade técnica; simplicidade comercial; compromisso com prazo; dados para decisão; parceria com lojistas.",
                        company_id,
                    ),
                )

                # Limpeza tenant-safe do mapa de processos e SIPOC do tenant M1.
                cur.execute("delete from process_sipoc_regulatory_items where company_id=%s", (company_id,))
                cur.execute("delete from process_sipoc_items where company_id=%s", (company_id,))
                cur.execute("delete from process_sipoc_snapshots where company_id=%s", (company_id,))
                cur.execute("delete from macro_process_sipoc_regulatory_items where company_id=%s", (company_id,))
                cur.execute("delete from macro_process_sipoc_items where company_id=%s", (company_id,))
                cur.execute("delete from macro_process_sipoc_snapshots where company_id=%s", (company_id,))
                cur.execute("delete from process_routines where company_id=%s", (company_id,))
                cur.execute("delete from processes where company_id=%s", (company_id,))
                cur.execute("delete from macro_processes where company_id=%s", (company_id,))
                cur.execute("delete from process_areas where company_id=%s", (company_id,))

                macro_ids: dict[str, int] = {}
                process_count = 0
                for area_index, area in enumerate(AREAS, start=1):
                    cur.execute(
                        """
                        insert into process_areas (company_id, code, name, description, order_index, color, created_at, updated_at)
                        values (%s,%s,%s,%s,%s,%s,now(),now()) returning id
                        """,
                        (company_id, area["code"], area["name"], area["description"], area_index, area["color"]),
                    )
                    area_id = cur.fetchone()[0]
                    for macro_index, macro in enumerate(area["macros"], start=1):
                        cur.execute(
                            """
                            insert into macro_processes (company_id, area_id, code, name, owner, description, order_index, created_at, updated_at)
                            values (%s,%s,%s,%s,%s,%s,%s,now(),now()) returning id
                            """,
                            (company_id, area_id, macro["code"], macro["name"], macro["owner"], macro["description"], macro_index),
                        )
                        macro_id = cur.fetchone()[0]
                        macro_ids[macro["code"]] = macro_id
                        process_rows = [
                            (
                                company_id,
                                macro_id,
                                code,
                                name,
                                desc,
                                responsible,
                                "stable",
                                "defined",
                                "managed",
                                idx,
                                True,
                            )
                            for idx, (code, name, desc, responsible) in enumerate(macro["processes"], start=1)
                        ]
                        execute_values(
                            cur,
                            """
                            insert into processes
                                (company_id, macro_id, code, name, description, responsible, kanban_stage,
                                 structuring_level, performance_level, order_index, is_active, created_at)
                            values %s
                            """,
                            process_rows,
                            template="(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,now())",
                        )
                        process_count += len(process_rows)

                prod_macro_id = macro_ids[SIPOC["macro_code"]]
                cur.execute(
                    """
                    insert into macro_process_sipoc_snapshots
                        (company_id, macro_process_id, version, status, title, objective, start_boundary, end_boundary,
                         trigger_event, customer_requirements, constraints_notes, measures_notes, risks_notes, notes,
                         published_at, created_at, updated_at)
                    values (%s,%s,1,'published',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,now(),now(),now()) returning id
                    """,
                    (
                        company_id,
                        prod_macro_id,
                        SIPOC["title"],
                        SIPOC["objective"],
                        SIPOC["start_boundary"],
                        SIPOC["end_boundary"],
                        SIPOC["trigger_event"],
                        SIPOC["customer_requirements"],
                        SIPOC["constraints_notes"],
                        SIPOC["measures_notes"],
                        SIPOC["risks_notes"],
                        SIPOC["notes"],
                    ),
                )
                sipoc_id = cur.fetchone()[0]
                execute_values(
                    cur,
                    """
                    insert into macro_process_sipoc_items
                        (company_id, sipoc_snapshot_id, lane, title, description, order_index, source_type, source_ref, is_critical, created_at, updated_at)
                    values %s
                    """,
                    [
                        (company_id, sipoc_id, lane, title, desc, order_idx, "manual", None, critical)
                        for lane, title, desc, order_idx, critical in SIPOC["items"]
                    ],
                    template="(%s,%s,%s,%s,%s,%s,%s,%s,%s,now(),now())",
                )

                cur.execute("select count(*) from process_areas where company_id=%s", (company_id,))
                areas_count = cur.fetchone()[0]
                cur.execute("select count(*) from macro_processes where company_id=%s", (company_id,))
                macros_count = cur.fetchone()[0]
                cur.execute("select count(*) from processes where company_id=%s", (company_id,))
                processes_count = cur.fetchone()[0]
                cur.execute("select count(*) from macro_process_sipoc_items where company_id=%s and sipoc_snapshot_id=%s", (company_id, sipoc_id))
                sipoc_items_count = cur.fetchone()[0]

        print({
            "ok": True,
            "company_id": company_id,
            "company": COMPANY_NAME,
            "areas": areas_count,
            "macro_processes": macros_count,
            "processes": processes_count,
            "sipoc_macro": "Produção / Entrega",
            "sipoc_snapshot_id": sipoc_id,
            "sipoc_items": sipoc_items_count,
        })
    finally:
        conn.close()


if __name__ == "__main__":
    main()

