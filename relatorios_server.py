#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Servidor simples para testar as rotas de relatórios
"""

from flask import Flask, render_template, jsonify, request
import sys
import os

# Adiciona o diretório atual ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

app = Flask(__name__)


@app.route("/")
def home():
    return """
    <h1>Sistema de Relatórios Estruturado</h1>
    <p>Servidor funcionando!</p>
    <ul>
        <li><a href="/report-templates">Gerenciador de Templates</a></li>
        <li><a href="/api/report-templates">API Templates</a></li>
        <li><a href="/api/reports/models">API Configurações</a></li>
    </ul>
    """


@app.route("/report-templates")
def report_templates():
    """Página de gerenciamento de templates de relatórios"""
    try:
        return render_template("report_templates_manager.html")
    except Exception as e:
        return f"Erro ao carregar template: {e}", 500


@app.route("/api/report-templates", methods=["GET"])
def api_get_report_templates():
    """Lista todos os templates de relatórios"""
    try:
        from modules.report_templates import ReportTemplatesManager

        manager = ReportTemplatesManager()
        templates = manager.get_all_templates()

        return jsonify(templates)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/report-templates", methods=["POST"])
def api_create_report_template():
    """Cria um novo template de relatório"""
    try:
        from modules.report_templates import ReportTemplatesManager

        data = request.get_json()
        if not data:
            return jsonify({"error": "Dados não fornecidos"}), 400

        manager = ReportTemplatesManager()
        template_id = manager.save_template(data)

        return jsonify({"success": True, "template_id": template_id})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/reports/models", methods=["GET"])
def api_get_report_models():
    """Lista todas as configurações de página"""
    try:
        from modules.report_models import ReportModelsManager

        manager = ReportModelsManager()
        models = manager.get_all_models()

        return jsonify(models)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    print("🚀 Iniciando servidor de relatórios na porta 5002...")
    print("📊 Acesse: http://127.0.0.1:5002/report-templates")
    app.run(host="127.0.0.1", port=5002, debug=True)
