#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MÃ³dulo de GeraÃ§Ã£o de RelatÃ³rios Profissionais
Sistema PEVAPP22
Usando ReportLab + Plotly (compatÃ­vel com Windows)
"""

import logging
import os
from database.postgres_helper import connect as pg_connect
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
    PageBreak,
    Image,
    KeepTogether,
)
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

logger = logging.getLogger(__name__)
from reportlab.pdfgen import canvas
import plotly.graph_objects as go
from plotly.subplots import make_subplots


class GeradorRelatoriosProfissionais:
    """
    Classe para gerar relatÃ³rios profissionais em PDF
    Integrado ao sistema PEVAPP22
    Usando ReportLab (compatÃ­vel com Windows)
    """

    def __init__(self, db_path=None):
        """
        Inicializa o gerador de relatÃ³rios

        Args:
            db_path: Caminho para o banco de dados SQLite (opcional)
        """
        self.db_path = db_path or "pevapp22.db"
        self.temp_dir = "temp_relatorios"
        self.output_dir = "relatorios"

        # Cria diretÃ³rios se nÃ£o existirem
        os.makedirs(self.temp_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)

        # ConfiguraÃ§Ã£o de estilos
        self.styles = getSampleStyleSheet()
        self._criar_estilos_personalizados()

    def _get_connection(self):
        """Cria uma conexÃ£o com o banco de dados"""
        from database.postgres_helper import connect as pg_connect

        conn = pg_connect()
        # PostgreSQL retorna Row objects por padrÃ£o
        return conn

    def _criar_estilos_personalizados(self):
        """Cria estilos personalizados para o documento"""

        # TÃ­tulo principal
        self.styles.add(
            ParagraphStyle(
                name="TituloPrincipal",
                parent=self.styles["Heading1"],
                fontSize=24,
                textColor=colors.HexColor("#1a76ff"),
                spaceAfter=20,
                alignment=TA_CENTER,
            )
        )

        # SubtÃ­tulo
        self.styles.add(
            ParagraphStyle(
                name="Subtitulo",
                parent=self.styles["Normal"],
                fontSize=12,
                textColor=colors.HexColor("#666666"),
                spaceAfter=30,
                alignment=TA_CENTER,
            )
        )

        # TÃ­tulo de seÃ§Ã£o
        self.styles.add(
            ParagraphStyle(
                name="TituloSecao",
                parent=self.styles["Heading2"],
                fontSize=14,
                textColor=colors.HexColor("#1a76ff"),
                spaceBefore=15,
                spaceAfter=10,
            )
        )

        # MÃ©trica
        self.styles.add(
            ParagraphStyle(
                name="MetricaValor",
                parent=self.styles["Normal"],
                fontSize=20,
                textColor=colors.HexColor("#1a76ff"),
                fontName="Helvetica-Bold",
                alignment=TA_CENTER,
            )
        )

        self.styles.add(
            ParagraphStyle(
                name="MetricaLabel",
                parent=self.styles["Normal"],
                fontSize=9,
                textColor=colors.HexColor("#666666"),
                alignment=TA_CENTER,
            )
        )

    # ========================================
    # MÃ‰TODOS DE BUSCA DE DADOS
    # ========================================

    def buscar_empresa(self, empresa_id):
        """Busca dados da empresa"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, name, legal_name, industry, size, description
            FROM companies
            WHERE id = ?
        """,
            (empresa_id,),
        )

        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                "id": row[0],
                "nome": row[1] or row[2] or "Empresa",
                "legal_name": row[2] or "",
                "industry": row[3] or "",
                "size": row[4] or "",
                "description": row[5] or "",
            }
        return None

    def buscar_projetos(self, empresa_id, status=None):
        """Busca projetos da empresa"""
        conn = self._get_connection()
        cursor = conn.cursor()

        query = """
            SELECT 
                id, title, description, status, 
                start_date, end_date, priority, owner
            FROM company_projects
            WHERE company_id = ?
        """
        params = [empresa_id]

        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY start_date DESC"

        cursor.execute(query, params)

        projetos = []
        for row in cursor.fetchall():
            projetos.append(
                {
                    "codigo": f"PRJ-{row[0]:03d}",
                    "nome": row[1] or "Projeto sem tÃ­tulo",
                    "descricao": row[2] or "",
                    "status": row[3] or "Planejamento",
                    "data_inicio": row[4],
                    "data_fim": row[5],
                    "investimento": 0.0,  # NÃ£o existe no banco, deixar zerado
                    "responsavel": row[7] or "",
                    "prioridade": row[6] or "",
                }
            )

        conn.close()
        return projetos

    def calcular_metricas_empresa(self, empresa_id):
        """Calcula mÃ©tricas gerais da empresa"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Total de projetos
        cursor.execute(
            """
            SELECT COUNT(*) FROM company_projects WHERE company_id = ?
        """,
            (empresa_id,),
        )
        total_projetos = cursor.fetchone()[0]

        # Projetos concluÃ­dos
        cursor.execute(
            """
            SELECT COUNT(*) FROM company_projects 
            WHERE company_id = ? AND status IN ('completed', 'ConcluÃ­do')
        """,
            (empresa_id,),
        )
        projetos_concluidos = cursor.fetchone()[0]

        # Projetos em andamento
        cursor.execute(
            """
            SELECT COUNT(*) FROM company_projects 
            WHERE company_id = ? AND status IN ('in_progress', 'Em Andamento')
        """,
            (empresa_id,),
        )
        projetos_em_andamento = cursor.fetchone()[0]

        conn.close()

        # Calcula eficiÃªncia
        eficiencia = (
            (projetos_concluidos / total_projetos * 100) if total_projetos > 0 else 0
        )

        return {
            "total_projetos": total_projetos,
            "projetos_concluidos": projetos_concluidos,
            "projetos_em_andamento": projetos_em_andamento,
            "investimento_total": 0.0,  # NÃ£o hÃ¡ no banco
            "eficiencia": round(eficiencia, 1),
        }

    # ========================================
    # MÃ‰TODOS DE GERAÃ‡ÃƒO DE GRÃFICOS
    # ========================================

    def gerar_grafico_projetos_status(self, empresa_id):
        """Gera grÃ¡fico de pizza com status dos projetos"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT status, COUNT(*) as total
            FROM company_projects
            WHERE company_id = ?
            GROUP BY status
        """,
            (empresa_id,),
        )

        dados = cursor.fetchall()
        conn.close()

        if not dados:
            return None

        labels = [row[0] for row in dados]
        values = [row[1] for row in dados]

        # Cores personalizadas
        cores = {
            "Planejamento": "#ffc107",
            "Em Andamento": "#1a76ff",
            "ConcluÃ­do": "#28a745",
            "Pausado": "#dc3545",
            "Cancelado": "#6c757d",
        }

        colors_list = [cores.get(label, "#666666") for label in labels]

        fig = go.Figure(
            data=[
                go.Pie(
                    labels=labels,
                    values=values,
                    hole=0.4,
                    marker=dict(colors=colors_list),
                    textposition="auto",
                    textinfo="label+percent",
                )
            ]
        )

        fig.update_layout(
            title={
                "text": "DistribuiÃ§Ã£o de Projetos por Status",
                "x": 0.5,
                "xanchor": "center",
                "font": {"size": 16},
            },
            template="plotly_white",
            font=dict(family="Arial", size=11),
            height=350,
            margin=dict(l=20, r=20, t=50, b=20),
            showlegend=True,
        )

        path = os.path.join(self.temp_dir, f"grafico_status_{empresa_id}.png")
        fig.write_image(path, width=700, height=350, scale=2)
        return os.path.abspath(path)

    def gerar_grafico_investimentos(self, empresa_id):
        """Gera grÃ¡fico de barras com investimentos por projeto"""
        projetos = self.buscar_projetos(empresa_id)

        if not projetos:
            return None

        # Pega top 10 projetos por investimento
        projetos_sorted = sorted(
            projetos, key=lambda x: x["investimento"], reverse=True
        )[:10]

        if not projetos_sorted:
            return None

        nomes = [
            p["nome"][:30] + "..." if len(p["nome"]) > 30 else p["nome"]
            for p in projetos_sorted
        ]
        valores = [p["investimento"] for p in projetos_sorted]

        fig = go.Figure(
            data=[
                go.Bar(
                    y=nomes,
                    x=valores,
                    orientation="h",
                    marker_color="#1a76ff",
                    text=[f"R$ {v:,.0f}" for v in valores],
                    textposition="auto",
                )
            ]
        )

        fig.update_layout(
            title={
                "text": "Top 10 Projetos por Investimento",
                "x": 0.5,
                "xanchor": "center",
                "font": {"size": 16},
            },
            xaxis_title="Investimento (R$)",
            yaxis_title="",
            template="plotly_white",
            font=dict(family="Arial", size=10),
            height=400,
            margin=dict(l=150, r=20, t=50, b=50),
        )

        path = os.path.join(self.temp_dir, f"grafico_investimentos_{empresa_id}.png")
        fig.write_image(path, width=800, height=400, scale=2)
        return os.path.abspath(path)

    # ========================================
    # MÃ‰TODOS AUXILIARES
    # ========================================

    @staticmethod
    def format_currency(valor):
        """Formata valor como moeda brasileira"""
        if valor is None:
            return "R$ 0,00"
        return (
            f"R$ {float(valor):,.2f}".replace(",", "_")
            .replace(".", ",")
            .replace("_", ".")
        )

    @staticmethod
    def format_date(data_str):
        """Formata data para padrÃ£o brasileiro"""
        if not data_str:
            return "-"
        try:
            if isinstance(data_str, str):
                data = datetime.strptime(data_str, "%Y-%m-%d")
            else:
                data = data_str
            return data.strftime("%d/%m/%Y")
        except Exception as exc:
            return data_str

    def limpar_temp(self):
        """Remove arquivos temporÃ¡rios"""
        try:
            for arquivo in os.listdir(self.temp_dir):
                file_path = os.path.join(self.temp_dir, arquivo)
                if os.path.isfile(file_path):
                    os.remove(file_path)
        except Exception as e:
            logger.exception("Erro ao limpar arquivos temporÃ¡rios")

    # ========================================
    # MÃ‰TODO PRINCIPAL DE GERAÃ‡ÃƒO
    # ========================================

    def gerar_relatorio_projetos(self, empresa_id):
        """
        Gera relatÃ³rio completo de projetos da empresa

        Args:
            empresa_id: ID da empresa

        Returns:
            str: Caminho do arquivo PDF gerado
        """

        # 1. Busca dados
        empresa = self.buscar_empresa(empresa_id)
        if not empresa:
            raise ValueError(f"Empresa {empresa_id} nÃ£o encontrada")

        projetos = self.buscar_projetos(empresa_id)
        metricas = self.calcular_metricas_empresa(empresa_id)

        # 2. Gera grÃ¡ficos
        grafico_status = None
        grafico_investimentos = None

        if len(projetos) > 0:
            try:
                grafico_status = self.gerar_grafico_projetos_status(empresa_id)
            except Exception as e:
                logger.warning("Erro ao gerar grÃ¡fico de status: %s", e)

            try:
                grafico_investimentos = self.gerar_grafico_investimentos(empresa_id)
            except Exception as e:
                logger.warning("Erro ao gerar grÃ¡fico de investimentos: %s", e)

        # 3. Configura PDF
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"relatorio_projetos_empresa_{empresa_id}_{timestamp}.pdf"
        output_path = os.path.join(self.output_dir, output_filename)

        # Cria documento em paisagem
        doc = SimpleDocTemplate(
            output_path,
            pagesize=landscape(A4),
            rightMargin=2 * cm,
            leftMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
        )

        # 4. Cria elementos do PDF
        story = []

        # CabeÃ§alho
        story.append(
            Paragraph("RelatÃ³rio de Projetos", self.styles["TituloPrincipal"])
        )
        story.append(
            Paragraph(
                f"{empresa['nome']}<br/>Gerado em: {datetime.now().strftime('%d/%m/%Y Ã s %H:%M')}",
                self.styles["Subtitulo"],
            )
        )
        story.append(Spacer(1, 1 * cm))

        # Cards de MÃ©tricas
        metricas_data = [
            [
                Paragraph(
                    "<br/>".join(
                        [
                            '<font size="20" color="#1a76ff"><b>'
                            + str(metricas["total_projetos"])
                            + "</b></font>",
                            '<font size="9" color="#666666">TOTAL DE PROJETOS</font>',
                        ]
                    ),
                    self.styles["Normal"],
                ),
                Paragraph(
                    "<br/>".join(
                        [
                            '<font size="20" color="#1a76ff"><b>'
                            + str(metricas["projetos_concluidos"])
                            + "</b></font>",
                            '<font size="9" color="#666666">CONCLUÃDOS</font>',
                        ]
                    ),
                    self.styles["Normal"],
                ),
                Paragraph(
                    "<br/>".join(
                        [
                            '<font size="20" color="#1a76ff"><b>'
                            + str(metricas["projetos_em_andamento"])
                            + "</b></font>",
                            '<font size="9" color="#666666">EM ANDAMENTO</font>',
                        ]
                    ),
                    self.styles["Normal"],
                ),
                Paragraph(
                    "<br/>".join(
                        [
                            '<font size="20" color="#1a76ff"><b>'
                            + str(metricas["eficiencia"])
                            + "%</b></font>",
                            '<font size="9" color="#666666">TAXA DE CONCLUSÃƒO</font>',
                        ]
                    ),
                    self.styles["Normal"],
                ),
            ]
        ]

        metricas_table = Table(
            metricas_data, colWidths=[6 * cm, 6 * cm, 6 * cm, 6 * cm]
        )
        metricas_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8f9fa")),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                    ("TOPPADDING", (0, 0), (-1, -1), 15),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 15),
                    ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#e0e0e0")),
                ]
            )
        )

        story.append(metricas_table)
        story.append(Spacer(1, 1 * cm))

        # GrÃ¡fico de Status
        if grafico_status and os.path.exists(grafico_status):
            story.append(
                Paragraph("ðŸ“Š DistribuiÃ§Ã£o por Status", self.styles["TituloSecao"])
            )
            try:
                img = Image(grafico_status, width=18 * cm, height=9 * cm)
                story.append(img)
                story.append(Spacer(1, 0.5 * cm))
            except Exception as e:
                logger.exception("Erro ao adicionar grÃ¡fico de status")

        # Tabela de Projetos
        if projetos:
            story.append(
                Paragraph("ðŸ“‹ Lista de Projetos", self.styles["TituloSecao"])
            )
            story.append(Spacer(1, 0.3 * cm))

            # Prepara dados da tabela
            tabela_data = [
                ["CÃ³digo", "Projeto", "Status", "InÃ­cio", "Fim", "Investimento"]
            ]

            for projeto in projetos:
                tabela_data.append(
                    [
                        projeto["codigo"],
                        projeto["nome"][:40] + "..."
                        if len(projeto["nome"]) > 40
                        else projeto["nome"],
                        projeto["status"],
                        self.format_date(projeto["data_inicio"]),
                        self.format_date(projeto["data_fim"]),
                        self.format_currency(projeto["investimento"]),
                    ]
                )

            # Linha de total
            tabela_data.append(
                [
                    "",
                    "",
                    "",
                    "",
                    "TOTAL INVESTIDO:",
                    self.format_currency(metricas["investimento_total"]),
                ]
            )

            # Cria tabela
            tabela_projetos = Table(
                tabela_data,
                colWidths=[3 * cm, 9 * cm, 3.5 * cm, 3 * cm, 3 * cm, 3.5 * cm],
            )
            tabela_projetos.setStyle(
                TableStyle(
                    [
                        # CabeÃ§alho
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a76ff")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 10),
                        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                        ("VALIGN", (0, 0), (-1, 0), "MIDDLE"),
                        ("TOPPADDING", (0, 0), (-1, 0), 8),
                        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                        # Dados
                        ("FONTNAME", (0, 1), (-1, -2), "Helvetica"),
                        ("FONTSIZE", (0, 1), (-1, -2), 9),
                        ("ALIGN", (5, 1), (5, -2), "RIGHT"),
                        ("VALIGN", (0, 1), (-1, -2), "MIDDLE"),
                        ("TOPPADDING", (0, 1), (-1, -2), 6),
                        ("BOTTOMPADDING", (0, 1), (-1, -2), 6),
                        (
                            "ROWBACKGROUNDS",
                            (0, 1),
                            (-1, -2),
                            [colors.white, colors.HexColor("#f8f9fa")],
                        ),
                        # Total
                        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#e8f4ff")),
                        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                        ("ALIGN", (5, -1), (5, -1), "RIGHT"),
                        # Bordas
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e0e0e0")),
                        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#1a76ff")),
                    ]
                )
            )

            story.append(tabela_projetos)
            story.append(Spacer(1, 1 * cm))
        else:
            story.append(
                Paragraph("âš ï¸ Nenhum projeto cadastrado", self.styles["Normal"])
            )
            story.append(Spacer(1, 0.5 * cm))

        # GrÃ¡fico de Investimentos
        if grafico_investimentos and os.path.exists(grafico_investimentos):
            story.append(PageBreak())
            story.append(
                Paragraph("ðŸ’° Investimentos por Projeto", self.styles["TituloSecao"])
            )
            try:
                img = Image(grafico_investimentos, width=20 * cm, height=10 * cm)
                story.append(img)
            except Exception as e:
                logger.exception("Erro ao adicionar grÃ¡fico de investimentos")

        # RodapÃ©
        story.append(Spacer(1, 1 * cm))
        rodape_text = f"""
        <para align="center">
        <font size="10"><b>PEVAPP22 - Sistema de GestÃ£o Empresarial</b></font><br/>
        <font size="9" color="#666666">Documento gerado automaticamente em {datetime.now().strftime('%d/%m/%Y Ã s %H:%M:%S')}</font>
        </para>
        """
        story.append(Paragraph(rodape_text, self.styles["Normal"]))

        # 5. Gera PDF
        doc.build(story)

        # 6. Limpa arquivos temporÃ¡rios
        self.limpar_temp()

        return output_path


# ========================================
# FUNÃ‡Ã•ES DE CONVENIÃŠNCIA
# ========================================


def gerar_relatorio_empresa(empresa_id):
    """
    FunÃ§Ã£o de conveniÃªncia para gerar relatÃ³rio de projetos

    Args:
        empresa_id: ID da empresa

    Returns:
        str: Caminho do arquivo PDF gerado
    """
    gerador = GeradorRelatoriosProfissionais()
    return gerador.gerar_relatorio_projetos(empresa_id)


if __name__ == "__main__":
    # Teste rÃ¡pido
    logger.info("Teste do Gerador de RelatÃ³rios Profissionais")
    logger.info("Para integrar ao Flask, use:")
    logger.info(
        "  from modules.gerador_relatorios_reportlab import gerar_relatorio_empresa"
    )
    logger.info("  pdf_path = gerar_relatorio_empresa(empresa_id)")
