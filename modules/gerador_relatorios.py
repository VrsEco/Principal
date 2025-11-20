#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MÃ³dulo de GeraÃ§Ã£o de RelatÃ³rios Profissionais
Sistema PEVAPP22
Usando WeasyPrint + Plotly
"""

import logging
import os
from contextlib import contextmanager
from datetime import datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from decimal import Decimal
from config_database import get_db

logger = logging.getLogger(__name__)

try:
    from weasyprint import HTML  # type: ignore

    _WEASYPRINT_AVAILABLE = True
    _WEASYPRINT_IMPORT_ERROR = None
except Exception as _weasy_exc:  # pragma: no cover - defensive import
    HTML = None
    _WEASYPRINT_AVAILABLE = False
    _WEASYPRINT_IMPORT_ERROR = _weasy_exc


class GeradorRelatoriosProfissionais:
    """
    Classe para gerar relatÃ³rios profissionais em PDF
    Integrado ao sistema PEVAPP22
    """

    def __init__(self, db_connection=None):
        """
        Inicializa o gerador de relatÃ³rios

        Args:
            db_connection: ConexÃ£o com banco de dados (opcional)
        """
        self.db = db_connection or get_db()
        self.temp_dir = "temp_relatorios"
        self.output_dir = "relatorios"

        # Cria diretÃ³rios se nÃ£o existirem
        os.makedirs(self.temp_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)

    @contextmanager
    def _cursor(self):
        """Retorna um cursor independente do backend configurado."""
        conn = None
        cursor = None
        close_conn = False
        try:
            if hasattr(self.db, "_get_connection"):
                conn = self.db._get_connection()
                close_conn = True
            else:
                conn = self.db
            cursor = conn.cursor()
            yield cursor
        finally:
            if cursor is not None:
                try:
                    cursor.close()
                except Exception:
                    pass
            if close_conn and conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass

    def _ensure_weasyprint(self):
        """Garante que a dependÃªncia principal esteja instalada."""
        if not _WEASYPRINT_AVAILABLE or HTML is None:
            raise RuntimeError(
                "WeasyPrint nÃ£o estÃ¡ disponÃ­vel. Instale as dependÃªncias de relatÃ³rio."
            ) from _WEASYPRINT_IMPORT_ERROR

    def _safe_write_image(self, fig, path, **kwargs):
        """Exporta o grÃ¡fico tratando ausÃªncia do motor de imagens."""
        try:
            fig.write_image(path, **kwargs)
            return os.path.abspath(path)
        except Exception as exc:
            logger.warning("[relatorios] NÃ£o foi possÃ­vel exportar grÃ¡fico: %s", exc)
            return None

    # ========================================
    # MÃ‰TODOS DE BUSCA DE DADOS
    # ========================================

    def buscar_empresa(self, empresa_id):
        """Busca dados da empresa utilizando o adaptador atual."""
        company = self.db.get_company(empresa_id)
        if not company:
            return None
        return {
            "id": company.get("id"),
            "nome": company.get("name") or company.get("legal_name") or "Empresa",
            "cnpj": company.get("cnpj") or "",
            "endereco": company.get("address") or "",
            "telefone": company.get("phone") or "",
            "email": company.get("email") or "",
            "logo": company.get("logo_path") or "",
        }

    def buscar_projetos(self, empresa_id, status=None):
        """Busca projetos da empresa"""
        projetos_brutos = self.db.get_company_projects(empresa_id)
        projetos = []
        for projeto in projetos_brutos:
            if status and (projeto.get("status") or "").lower() != status.lower():
                continue
            codigo = projeto.get("code")
            if not codigo:
                codigo = f"PRJ-{projeto.get('id', 0):04d}"
            projetos.append(
                {
                    "codigo": codigo,
                    "nome": projeto.get("title") or "Projeto",
                    "descricao": projeto.get("description") or "",
                    "status": projeto.get("status") or "planned",
                    "data_inicio": projeto.get("start_date"),
                    "data_fim": projeto.get("end_date"),
                    "investimento": float(projeto.get("budget") or 0),
                    "responsavel": projeto.get("owner") or "",
                }
            )
        return sorted(
            projetos,
            key=lambda item: item.get("data_inicio") or datetime.utcnow(),
            reverse=True,
        )

    def calcular_metricas_empresa(
        self, empresa_id, periodo_inicio=None, periodo_fim=None
    ):
        """Calcula m?tricas gerais da empresa"""
        projetos = self.db.get_company_projects(empresa_id)
        total_projetos = len(projetos)
        projetos_concluidos = sum(
            1
            for projeto in projetos
            if (projeto.get("status") or "").lower()
            in {"concluÃ­do", "concluido", "completed", "done"}
        )
        investimento_total = sum(
            float(projeto.get("budget") or 0) for projeto in projetos
        )

        eficiencia = (
            (projetos_concluidos / total_projetos * 100) if total_projetos > 0 else 0
        )

        return {
            "total_projetos": total_projetos,
            "projetos_concluidos": projetos_concluidos,
            "projetos_em_andamento": total_projetos - projetos_concluidos,
            "investimento_total": investimento_total,
            "eficiencia": round(eficiencia, 1),
        }

    # ========================================
    # MÃ‰TODOS DE GERAÃ‡ÃƒO DE GRÃFICOS
    # ========================================

    def gerar_grafico_projetos_status(self, empresa_id):
        """Gera grÃ¡fico de pizza com status dos projetos"""
        with self._cursor() as cursor:
            cursor.execute(
                """
                SELECT status, COUNT(*) as total
                FROM company_projects
                WHERE company_id = %s
                GROUP BY status
            """,
                (empresa_id,),
            )
            dados = cursor.fetchall()

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

        colors = [cores.get(label, "#666666") for label in labels]

        fig = go.Figure(
            data=[
                go.Pie(
                    labels=labels,
                    values=values,
                    hole=0.4,
                    marker=dict(colors=colors),
                    textposition="auto",
                    textinfo="label+percent",
                )
            ]
        )

        fig.update_layout(
            title="DistribuiÃ§Ã£o de Projetos por Status",
            template="plotly_white",
            font=dict(family="Arial", size=12),
            height=400,
        )

        path = os.path.join(self.temp_dir, f"grafico_status_{empresa_id}.png")
        return self._safe_write_image(fig, path, width=800, height=400, scale=2)

    def gerar_grafico_investimentos(self, empresa_id):
        """Gera grÃ¡fico de barras com investimentos por projeto"""
        projetos = self.buscar_projetos(empresa_id)

        if not projetos:
            return None

        # Pega top 10 projetos por investimento
        projetos_sorted = sorted(
            projetos, key=lambda x: x["investimento"], reverse=True
        )[:10]

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
            title="Top 10 Projetos por Investimento",
            xaxis_title="Investimento (R$)",
            yaxis_title="Projeto",
            template="plotly_white",
            font=dict(family="Arial", size=11),
            height=500,
            margin=dict(l=200),
        )

        path = os.path.join(self.temp_dir, f"grafico_investimentos_{empresa_id}.png")
        return self._safe_write_image(fig, path, width=1000, height=500, scale=2)

    def gerar_grafico_timeline(self, empresa_id):
        """Gera grÃ¡fico de timeline dos projetos"""
        projetos = self.buscar_projetos(empresa_id)

        if not projetos:
            return None

        # Filtra projetos com datas vÃ¡lidas
        projetos_validos = [p for p in projetos if p["data_inicio"] and p["data_fim"]][
            :15
        ]  # Top 15

        if not projetos_validos:
            return None

        fig = go.Figure()

        for i, projeto in enumerate(projetos_validos):
            cor = {
                "Planejamento": "#ffc107",
                "Em Andamento": "#1a76ff",
                "ConcluÃ­do": "#28a745",
                "Pausado": "#dc3545",
            }.get(projeto["status"], "#666666")

            fig.add_trace(
                go.Scatter(
                    x=[projeto["data_inicio"], projeto["data_fim"]],
                    y=[i, i],
                    mode="lines+markers",
                    name=projeto["nome"][:30],
                    line=dict(color=cor, width=10),
                    marker=dict(size=8),
                    hovertemplate=f"<b>{projeto['nome']}</b><br>"
                    + f"InÃ­cio: {projeto['data_inicio']}<br>"
                    + f"Fim: {projeto['data_fim']}<br>"
                    + f"Status: {projeto['status']}<extra></extra>",
                )
            )

        fig.update_layout(
            title="Timeline de Projetos",
            xaxis_title="Data",
            yaxis=dict(
                tickmode="array",
                tickvals=list(range(len(projetos_validos))),
                ticktext=[p["codigo"] for p in projetos_validos],
            ),
            template="plotly_white",
            height=max(400, len(projetos_validos) * 30),
            showlegend=False,
            font=dict(family="Arial", size=10),
        )

        path = os.path.join(self.temp_dir, f"grafico_timeline_{empresa_id}.png")
        return self._safe_write_image(
            fig,
            path,
            width=1000,
            height=max(400, len(projetos_validos) * 30),
            scale=2,
        )

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
    # MÃ‰TODOS PRINCIPAIS DE GERAÃ‡ÃƒO
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
        grafico_status = self.gerar_grafico_projetos_status(empresa_id)
        grafico_investimentos = self.gerar_grafico_investimentos(empresa_id)
        grafico_timeline = self.gerar_grafico_timeline(empresa_id)

        # 3. Prepara dados para o template
        contexto = {
            "empresa": empresa,
            "projetos": projetos,
            "metricas": metricas,
            "total_investimento": self.format_currency(metricas["investimento_total"]),
            "grafico_status_path": grafico_status,
            "grafico_investimentos_path": grafico_investimentos,
            "grafico_timeline_path": grafico_timeline,
            "data_geracao": datetime.now().strftime("%d/%m/%Y Ã s %H:%M:%S"),
            "format_currency": self.format_currency,
            "format_date": self.format_date,
        }

        # 4. Gera HTML
        html_content = self._gerar_html_relatorio_projetos(contexto)

        # 5. Converte para PDF
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"relatorio_projetos_empresa_{empresa_id}_{timestamp}.pdf"
        output_path = os.path.join(self.output_dir, output_filename)

        self._ensure_weasyprint()
        HTML(string=html_content).write_pdf(output_path)

        # 6. Limpa arquivos temporÃ¡rios
        self.limpar_temp()

        return output_path

    def _gerar_html_relatorio_projetos(self, contexto):
        """Gera HTML do relatÃ³rio de projetos"""

        # Gera tabela de projetos
        tabela_projetos = ""
        for projeto in contexto["projetos"]:
            cor_status = {
                "Planejamento": "orange",
                "Em Andamento": "blue",
                "ConcluÃ­do": "green",
                "Pausado": "red",
                "Cancelado": "gray",
            }.get(projeto["status"], "black")

            tabela_projetos += f"""
            <tr>
                <td><strong>{projeto['codigo']}</strong></td>
                <td>{projeto['nome']}</td>
                <td><span style="color: {cor_status};">â— {projeto['status']}</span></td>
                <td>{self.format_date(projeto['data_inicio'])}</td>
                <td>{self.format_date(projeto['data_fim'])}</td>
                <td style="text-align: right;">{self.format_currency(projeto['investimento'])}</td>
            </tr>
            """

        # Template HTML
        html = f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>RelatÃ³rio de Projetos - {contexto['empresa']['nome']}</title>
    <style>
        @page {{
            size: A4 landscape;
            margin: 1.5cm;
            @top-center {{
                content: "{contexto['empresa']['nome']} - RelatÃ³rio de Projetos";
                font-size: 10pt;
                color: #666;
            }}
            @bottom-right {{
                content: "PÃ¡gina " counter(page);
                font-size: 9pt;
                color: #666;
            }}
        }}
        
        body {{
            font-family: 'Segoe UI', Arial, sans-serif;
            color: #333;
            line-height: 1.5;
        }}
        
        .header {{
            border-bottom: 3px solid #1a76ff;
            padding-bottom: 15px;
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        h1 {{
            color: #1a76ff;
            font-size: 24pt;
            margin: 0;
        }}
        
        .metrics {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 15px;
            margin: 20px 0;
        }}
        
        .metric-card {{
            background: #f8f9fa;
            border-left: 4px solid #1a76ff;
            padding: 15px;
        }}
        
        .metric-value {{
            font-size: 24pt;
            font-weight: bold;
            color: #1a76ff;
        }}
        
        .metric-label {{
            font-size: 10pt;
            color: #666;
            text-transform: uppercase;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
            font-size: 10pt;
        }}
        
        th {{
            background: #1a76ff;
            color: white;
            padding: 10px;
            text-align: left;
            font-weight: 600;
        }}
        
        td {{
            padding: 8px 10px;
            border-bottom: 1px solid #e0e0e0;
        }}
        
        tr:nth-child(even) {{
            background: #f8f9fa;
        }}
        
        .chart {{
            margin: 20px 0;
            page-break-inside: avoid;
        }}
        
        .section {{
            margin-bottom: 30px;
            page-break-inside: avoid;
        }}
        
        .footer {{
            margin-top: 30px;
            padding-top: 15px;
            border-top: 2px solid #e0e0e0;
            font-size: 9pt;
            color: #666;
            text-align: center;
        }}
    </style>
</head>
<body>
    <!-- CabeÃ§alho -->
    <div class="header">
        <div>
            <h1>RelatÃ³rio de Projetos</h1>
            <p style="color: #666; font-size: 12pt;">{contexto['empresa']['nome']}</p>
        </div>
        <div style="text-align: right;">
            <p style="font-size: 10pt; margin: 0;">Gerado em:</p>
            <p style="font-size: 11pt; margin: 0; font-weight: bold;">{contexto['data_geracao']}</p>
        </div>
    </div>
    
    <!-- MÃ©tricas -->
    <div class="metrics">
        <div class="metric-card">
            <div class="metric-value">{contexto['metricas']['total_projetos']}</div>
            <div class="metric-label">Total de Projetos</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{contexto['metricas']['projetos_concluidos']}</div>
            <div class="metric-label">Projetos ConcluÃ­dos</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{contexto['metricas']['projetos_em_andamento']}</div>
            <div class="metric-label">Em Andamento</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{contexto['metricas']['eficiencia']}%</div>
            <div class="metric-label">Taxa de ConclusÃ£o</div>
        </div>
    </div>
    
    <!-- GrÃ¡fico de Status -->
    {f'<div class="section"><h2>ðŸ“Š DistribuiÃ§Ã£o por Status</h2><div class="chart"><img src="file:///{contexto["grafico_status_path"]}" style="width: 100%;"></div></div>' if contexto['grafico_status_path'] else ''}
    
    <!-- Tabela de Projetos -->
    <div class="section">
        <h2>ðŸ“‹ Lista de Projetos</h2>
        <table>
            <thead>
                <tr>
                    <th>CÃ³digo</th>
                    <th>Projeto</th>
                    <th>Status</th>
                    <th>Data InÃ­cio</th>
                    <th>Data Fim</th>
                    <th style="text-align: right;">Investimento</th>
                </tr>
            </thead>
            <tbody>
                {tabela_projetos}
            </tbody>
            <tfoot>
                <tr style="background: #e8f4ff; font-weight: bold;">
                    <td colspan="5" style="text-align: right;">TOTAL INVESTIDO:</td>
                    <td style="text-align: right;">{contexto['total_investimento']}</td>
                </tr>
            </tfoot>
        </table>
    </div>
    
    <!-- GrÃ¡fico de Investimentos -->
    {f'<div class="section"><h2>ðŸ’° Investimentos por Projeto</h2><div class="chart"><img src="file:///{contexto["grafico_investimentos_path"]}" style="width: 100%;"></div></div>' if contexto['grafico_investimentos_path'] else ''}
    
    <!-- Timeline -->
    {f'<div class="section"><h2>ðŸ“… Timeline de Projetos</h2><div class="chart"><img src="file:///{contexto["grafico_timeline_path"]}" style="width: 100%;"></div></div>' if contexto['grafico_timeline_path'] else ''}
    
    <!-- RodapÃ© -->
    <div class="footer">
        <p><strong>PEVAPP22 - Sistema de GestÃ£o Empresarial</strong></p>
        <p>Documento gerado automaticamente | {contexto['data_geracao']}</p>
    </div>
</body>
</html>
        """

        return html


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
    logger.info("  from modules.gerador_relatorios import gerar_relatorio_empresa")
    logger.info("  pdf_path = gerar_relatorio_empresa(empresa_id)")
