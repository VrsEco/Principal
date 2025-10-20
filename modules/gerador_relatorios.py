#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo de Geração de Relatórios Profissionais
Sistema PEVAPP22
Usando WeasyPrint + Plotly
"""

import os
from contextlib import contextmanager
from datetime import datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from decimal import Decimal
from config_database import get_db

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
    Classe para gerar relatórios profissionais em PDF
    Integrado ao sistema PEVAPP22
    """
    
    def __init__(self, db_connection=None):
        """
        Inicializa o gerador de relatórios
        
        Args:
            db_connection: Conexão com banco de dados (opcional)
        """
        self.db = db_connection or get_db()
        self.temp_dir = "temp_relatorios"
        self.output_dir = "relatorios"
        
        # Cria diretórios se não existirem
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
        """Garante que a dependência principal esteja instalada."""
        if not _WEASYPRINT_AVAILABLE or HTML is None:
            raise RuntimeError(
                "WeasyPrint não está disponível. Instale as dependências de relatório."
            ) from _WEASYPRINT_IMPORT_ERROR

    def _safe_write_image(self, fig, path, **kwargs):
        """Exporta o gráfico tratando ausência do motor de imagens."""
        try:
            fig.write_image(path, **kwargs)
            return os.path.abspath(path)
        except Exception as exc:
            print(f"[relatorios] Não foi possível exportar gráfico: {exc}")
            return None

    # ========================================
    # MÉTODOS DE BUSCA DE DADOS
    # ========================================
    
    def buscar_empresa(self, empresa_id):
        """Busca dados da empresa"""
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT id, nome, cnpj, endereco, telefone, email, logo_path
                FROM companies
                WHERE id = ?
            """, (empresa_id,))
            row = cursor.fetchone()
        if row:
            return {
                'id': row[0],
                'nome': row[1],
                'cnpj': row[2] or '',
                'endereco': row[3] or '',
                'telefone': row[4] or '',
                'email': row[5] or '',
                'logo': row[6] or ''
            }
        return None
    
    def buscar_projetos(self, empresa_id, status=None):
        """Busca projetos da empresa"""
        query = """
            SELECT 
                codigo, nome, descricao, status, 
                data_inicio, data_fim, investimento,
                responsavel
            FROM company_projects
            WHERE company_id = ?
        """
        params = [empresa_id]
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        query += " ORDER BY data_inicio DESC"
        
        with self._cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()
        
        projetos = []
        for row in rows:
            projetos.append({
                'codigo': row[0],
                'nome': row[1],
                'descricao': row[2] or '',
                'status': row[3],
                'data_inicio': row[4],
                'data_fim': row[5],
                'investimento': float(row[6]) if row[6] else 0.0,
                'responsavel': row[7] or ''
            })
        
        return projetos
    
    def calcular_metricas_empresa(self, empresa_id, periodo_inicio=None, periodo_fim=None):
        """Calcula m?tricas gerais da empresa"""
        with self._cursor() as cursor:
            # Total de projetos
            cursor.execute("""
                SELECT COUNT(*) FROM company_projects WHERE company_id = ?
            """, (empresa_id,))
            total_projetos = cursor.fetchone()[0]
            
            # Projetos conclu?dos
            cursor.execute("""
                SELECT COUNT(*) FROM company_projects 
                WHERE company_id = ? AND status = 'Conclu?do'
            """, (empresa_id,))
            projetos_concluidos = cursor.fetchone()[0]
            
            # Investimento total
            cursor.execute("""
                SELECT COALESCE(SUM(investimento), 0) FROM company_projects 
                WHERE company_id = ?
            """, (empresa_id,))
            investimento_total = float(cursor.fetchone()[0] or 0)

        # Calcula efici?ncia
        eficiencia = (projetos_concluidos / total_projetos * 100) if total_projetos > 0 else 0

        return {
            'total_projetos': total_projetos,
            'projetos_concluidos': projetos_concluidos,
            'projetos_em_andamento': total_projetos - projetos_concluidos,
            'investimento_total': investimento_total,
            'eficiencia': round(eficiencia, 1)
        }
    
    # ========================================
    # MÉTODOS DE GERAÇÃO DE GRÁFICOS
    # ========================================
    
    def gerar_grafico_projetos_status(self, empresa_id):
        """Gera gráfico de pizza com status dos projetos"""
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT status, COUNT(*) as total
                FROM company_projects
                WHERE company_id = ?
                GROUP BY status
            """, (empresa_id,))
            dados = cursor.fetchall()
        
        if not dados:
            return None
        
        labels = [row[0] for row in dados]
        values = [row[1] for row in dados]
        
        # Cores personalizadas
        cores = {
            'Planejamento': '#ffc107',
            'Em Andamento': '#1a76ff',
            'Concluído': '#28a745',
            'Pausado': '#dc3545',
            'Cancelado': '#6c757d'
        }
        
        colors = [cores.get(label, '#666666') for label in labels]
        
        fig = go.Figure(data=[go.Pie(
            labels=labels,
            values=values,
            hole=0.4,
            marker=dict(colors=colors),
            textposition='auto',
            textinfo='label+percent'
        )])
        
        fig.update_layout(
            title='Distribuição de Projetos por Status',
            template='plotly_white',
            font=dict(family="Arial", size=12),
            height=400
        )
        
        path = os.path.join(self.temp_dir, f'grafico_status_{empresa_id}.png')
        return self._safe_write_image(fig, path, width=800, height=400, scale=2)
    
    def gerar_grafico_investimentos(self, empresa_id):
        """Gera gráfico de barras com investimentos por projeto"""
        projetos = self.buscar_projetos(empresa_id)
        
        if not projetos:
            return None
        
        # Pega top 10 projetos por investimento
        projetos_sorted = sorted(projetos, key=lambda x: x['investimento'], reverse=True)[:10]
        
        nomes = [p['nome'][:30] + '...' if len(p['nome']) > 30 else p['nome'] for p in projetos_sorted]
        valores = [p['investimento'] for p in projetos_sorted]
        
        fig = go.Figure(data=[
            go.Bar(
                y=nomes,
                x=valores,
                orientation='h',
                marker_color='#1a76ff',
                text=[f'R$ {v:,.0f}' for v in valores],
                textposition='auto',
            )
        ])
        
        fig.update_layout(
            title='Top 10 Projetos por Investimento',
            xaxis_title='Investimento (R$)',
            yaxis_title='Projeto',
            template='plotly_white',
            font=dict(family="Arial", size=11),
            height=500,
            margin=dict(l=200)
        )
        
        path = os.path.join(self.temp_dir, f'grafico_investimentos_{empresa_id}.png')
        return self._safe_write_image(fig, path, width=1000, height=500, scale=2)
    
    def gerar_grafico_timeline(self, empresa_id):
        """Gera gráfico de timeline dos projetos"""
        projetos = self.buscar_projetos(empresa_id)
        
        if not projetos:
            return None
        
        # Filtra projetos com datas válidas
        projetos_validos = [
            p for p in projetos 
            if p['data_inicio'] and p['data_fim']
        ][:15]  # Top 15
        
        if not projetos_validos:
            return None
        
        fig = go.Figure()
        
        for i, projeto in enumerate(projetos_validos):
            cor = {
                'Planejamento': '#ffc107',
                'Em Andamento': '#1a76ff',
                'Concluído': '#28a745',
                'Pausado': '#dc3545'
            }.get(projeto['status'], '#666666')
            
            fig.add_trace(go.Scatter(
                x=[projeto['data_inicio'], projeto['data_fim']],
                y=[i, i],
                mode='lines+markers',
                name=projeto['nome'][:30],
                line=dict(color=cor, width=10),
                marker=dict(size=8),
                hovertemplate=f"<b>{projeto['nome']}</b><br>" +
                             f"Início: {projeto['data_inicio']}<br>" +
                             f"Fim: {projeto['data_fim']}<br>" +
                             f"Status: {projeto['status']}<extra></extra>"
            ))
        
        fig.update_layout(
            title='Timeline de Projetos',
            xaxis_title='Data',
            yaxis=dict(
                tickmode='array',
                tickvals=list(range(len(projetos_validos))),
                ticktext=[p['codigo'] for p in projetos_validos]
            ),
            template='plotly_white',
            height=max(400, len(projetos_validos) * 30),
            showlegend=False,
            font=dict(family="Arial", size=10)
        )
        
        path = os.path.join(self.temp_dir, f'grafico_timeline_{empresa_id}.png')
        return self._safe_write_image(
            fig,
            path,
            width=1000,
            height=max(400, len(projetos_validos) * 30),
            scale=2,
        )
    
    # ========================================
    # MÉTODOS AUXILIARES
    # ========================================
    
    @staticmethod
    def format_currency(valor):
        """Formata valor como moeda brasileira"""
        if valor is None:
            return "R$ 0,00"
        return f'R$ {float(valor):,.2f}'.replace(',', '_').replace('.', ',').replace('_', '.')
    
    @staticmethod
    def format_date(data_str):
        """Formata data para padrão brasileiro"""
        if not data_str:
            return "-"
        try:
            if isinstance(data_str, str):
                data = datetime.strptime(data_str, '%Y-%m-%d')
            else:
                data = data_str
            return data.strftime('%d/%m/%Y')
        except:
            return data_str
    
    def limpar_temp(self):
        """Remove arquivos temporários"""
        try:
            for arquivo in os.listdir(self.temp_dir):
                file_path = os.path.join(self.temp_dir, arquivo)
                if os.path.isfile(file_path):
                    os.remove(file_path)
        except Exception as e:
            print(f"Erro ao limpar arquivos temporários: {e}")
    
    # ========================================
    # MÉTODOS PRINCIPAIS DE GERAÇÃO
    # ========================================
    
    def gerar_relatorio_projetos(self, empresa_id):
        """
        Gera relatório completo de projetos da empresa
        
        Args:
            empresa_id: ID da empresa
            
        Returns:
            str: Caminho do arquivo PDF gerado
        """
        
        # 1. Busca dados
        empresa = self.buscar_empresa(empresa_id)
        if not empresa:
            raise ValueError(f"Empresa {empresa_id} não encontrada")
        
        projetos = self.buscar_projetos(empresa_id)
        metricas = self.calcular_metricas_empresa(empresa_id)
        
        # 2. Gera gráficos
        grafico_status = self.gerar_grafico_projetos_status(empresa_id)
        grafico_investimentos = self.gerar_grafico_investimentos(empresa_id)
        grafico_timeline = self.gerar_grafico_timeline(empresa_id)
        
        # 3. Prepara dados para o template
        contexto = {
            'empresa': empresa,
            'projetos': projetos,
            'metricas': metricas,
            'total_investimento': self.format_currency(metricas['investimento_total']),
            'grafico_status_path': grafico_status,
            'grafico_investimentos_path': grafico_investimentos,
            'grafico_timeline_path': grafico_timeline,
            'data_geracao': datetime.now().strftime('%d/%m/%Y às %H:%M:%S'),
            'format_currency': self.format_currency,
            'format_date': self.format_date
        }
        
        # 4. Gera HTML
        html_content = self._gerar_html_relatorio_projetos(contexto)
        
        # 5. Converte para PDF
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f'relatorio_projetos_empresa_{empresa_id}_{timestamp}.pdf'
        output_path = os.path.join(self.output_dir, output_filename)
        
        self._ensure_weasyprint()
        HTML(string=html_content).write_pdf(output_path)
        
        # 6. Limpa arquivos temporários
        self.limpar_temp()
        
        return output_path
    
    def _gerar_html_relatorio_projetos(self, contexto):
        """Gera HTML do relatório de projetos"""
        
        # Gera tabela de projetos
        tabela_projetos = ""
        for projeto in contexto['projetos']:
            cor_status = {
                'Planejamento': 'orange',
                'Em Andamento': 'blue',
                'Concluído': 'green',
                'Pausado': 'red',
                'Cancelado': 'gray'
            }.get(projeto['status'], 'black')
            
            tabela_projetos += f"""
            <tr>
                <td><strong>{projeto['codigo']}</strong></td>
                <td>{projeto['nome']}</td>
                <td><span style="color: {cor_status};">● {projeto['status']}</span></td>
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
    <title>Relatório de Projetos - {contexto['empresa']['nome']}</title>
    <style>
        @page {{
            size: A4 landscape;
            margin: 1.5cm;
            @top-center {{
                content: "{contexto['empresa']['nome']} - Relatório de Projetos";
                font-size: 10pt;
                color: #666;
            }}
            @bottom-right {{
                content: "Página " counter(page);
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
    <!-- Cabeçalho -->
    <div class="header">
        <div>
            <h1>Relatório de Projetos</h1>
            <p style="color: #666; font-size: 12pt;">{contexto['empresa']['nome']}</p>
        </div>
        <div style="text-align: right;">
            <p style="font-size: 10pt; margin: 0;">Gerado em:</p>
            <p style="font-size: 11pt; margin: 0; font-weight: bold;">{contexto['data_geracao']}</p>
        </div>
    </div>
    
    <!-- Métricas -->
    <div class="metrics">
        <div class="metric-card">
            <div class="metric-value">{contexto['metricas']['total_projetos']}</div>
            <div class="metric-label">Total de Projetos</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{contexto['metricas']['projetos_concluidos']}</div>
            <div class="metric-label">Projetos Concluídos</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{contexto['metricas']['projetos_em_andamento']}</div>
            <div class="metric-label">Em Andamento</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{contexto['metricas']['eficiencia']}%</div>
            <div class="metric-label">Taxa de Conclusão</div>
        </div>
    </div>
    
    <!-- Gráfico de Status -->
    {f'<div class="section"><h2>📊 Distribuição por Status</h2><div class="chart"><img src="file:///{contexto["grafico_status_path"]}" style="width: 100%;"></div></div>' if contexto['grafico_status_path'] else ''}
    
    <!-- Tabela de Projetos -->
    <div class="section">
        <h2>📋 Lista de Projetos</h2>
        <table>
            <thead>
                <tr>
                    <th>Código</th>
                    <th>Projeto</th>
                    <th>Status</th>
                    <th>Data Início</th>
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
    
    <!-- Gráfico de Investimentos -->
    {f'<div class="section"><h2>💰 Investimentos por Projeto</h2><div class="chart"><img src="file:///{contexto["grafico_investimentos_path"]}" style="width: 100%;"></div></div>' if contexto['grafico_investimentos_path'] else ''}
    
    <!-- Timeline -->
    {f'<div class="section"><h2>📅 Timeline de Projetos</h2><div class="chart"><img src="file:///{contexto["grafico_timeline_path"]}" style="width: 100%;"></div></div>' if contexto['grafico_timeline_path'] else ''}
    
    <!-- Rodapé -->
    <div class="footer">
        <p><strong>PEVAPP22 - Sistema de Gestão Empresarial</strong></p>
        <p>Documento gerado automaticamente | {contexto['data_geracao']}</p>
    </div>
</body>
</html>
        """
        
        return html


# ========================================
# FUNÇÕES DE CONVENIÊNCIA
# ========================================

def gerar_relatorio_empresa(empresa_id):
    """
    Função de conveniência para gerar relatório de projetos
    
    Args:
        empresa_id: ID da empresa
        
    Returns:
        str: Caminho do arquivo PDF gerado
    """
    gerador = GeradorRelatoriosProfissionais()
    return gerador.gerar_relatorio_projetos(empresa_id)


if __name__ == "__main__":
    # Teste rápido
    print("Teste do Gerador de Relatórios Profissionais")
    print("Para integrar ao Flask, use:")
    print("  from modules.gerador_relatorios import gerar_relatorio_empresa")
    print("  pdf_path = gerar_relatorio_empresa(empresa_id)")


