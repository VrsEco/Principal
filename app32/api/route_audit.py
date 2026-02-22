"""
Route Audit API endpoints
Provides endpoints for auditing and managing route logging
"""

from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
from services.route_audit_service import route_audit_service
from middleware.auto_log_decorator import (
    enable_auto_logging_for_entity,
    disable_auto_logging_for_entity,
    get_auto_logging_config,
)

route_audit_bp = Blueprint("route_audit", __name__, url_prefix="/route-audit")


@login_required
@route_audit_bp.route("/", methods=["GET"])
def audit_dashboard():
    """Dashboard de auditoria de rotas"""
    # Apenas administradores podem acessar
    if (
        not current_user
        or not current_user.is_authenticated
        or getattr(current_user, "role", None) != "admin"
    ):
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Acesso negado. Apenas administradores podem acessar.",
                }
            ),
            403,
        )

    return render_template("route_audit/dashboard.html")


@login_required
@route_audit_bp.route("/api/summary", methods=["GET"])
def get_audit_summary():
    """Retorna resumo da auditoria de rotas"""
    try:
        # Apenas administradores podem acessar
        if (
            not current_user
            or not current_user.is_authenticated
            or getattr(current_user, "role", None) != "admin"
        ):
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Acesso negado. Apenas administradores podem acessar.",
                    }
                ),
                403,
            )

        summary = route_audit_service.get_audit_summary()

        return jsonify({"success": True, "summary": summary})

    except Exception as e:
        return (
            jsonify({"success": False, "message": f"Erro ao obter resumo: {str(e)}"}),
            500,
        )


@route_audit_bp.route("/api/routes", methods=["GET"])
@login_required
def get_all_routes():
    """Lista todas as rotas da aplicação"""
    try:
        # Apenas administradores podem acessar
        if (
            not current_user
            or not current_user.is_authenticated
            or getattr(current_user, "role", None) != "admin"
        ):
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Acesso negado. Apenas administradores podem acessar.",
                    }
                ),
                403,
            )

        # Obter parâmetros de filtro
        filter_type = request.args.get(
            "filter", "all"
        )  # all, with_logging, without_logging, crud

        routes = route_audit_service.discover_all_routes()

        # Aplicar filtros
        if filter_type == "with_logging":
            routes = [r for r in routes if r["has_auto_log"] or r["has_manual_log"]]
        elif filter_type == "without_logging":
            routes = [
                r
                for r in routes
                if r["needs_logging"]
                and not r["has_auto_log"]
                and not r["has_manual_log"]
            ]
        elif filter_type == "crud":
            routes = [r for r in routes if r["is_crud"]]

        # Remover objetos função que não são serializáveis
        for route in routes:
            if "function" in route:
                del route["function"]

        return jsonify({"success": True, "routes": routes, "total": len(routes)})

    except Exception as e:
        return (
            jsonify({"success": False, "message": f"Erro ao obter rotas: {str(e)}"}),
            500,
        )


@route_audit_bp.route("/api/routes/without-logging", methods=["GET"])
@login_required
def get_routes_without_logging():
    """Lista rotas sem logging configurado"""
    try:
        # Apenas administradores podem acessar
        if (
            not current_user
            or not current_user.is_authenticated
            or getattr(current_user, "role", None) != "admin"
        ):
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Acesso negado. Apenas administradores podem acessar.",
                    }
                ),
                403,
            )

        routes = route_audit_service.get_routes_without_logging()

        # Remover objetos função que não são serializáveis
        for route in routes:
            if "function" in route:
                del route["function"]

        return jsonify({"success": True, "routes": routes, "total": len(routes)})

    except Exception as e:
        return (
            jsonify(
                {
                    "success": False,
                    "message": f"Erro ao obter rotas sem logging: {str(e)}",
                }
            ),
            500,
        )


@route_audit_bp.route("/api/routes/<path:endpoint>/details", methods=["GET"])
@login_required
def get_route_details(endpoint):
    """Obtém detalhes de uma rota específica"""
    try:
        # Apenas administradores podem acessar
        if (
            not current_user
            or not current_user.is_authenticated
            or getattr(current_user, "role", None) != "admin"
        ):
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Acesso negado. Apenas administradores podem acessar.",
                    }
                ),
                403,
            )

        route = route_audit_service.get_route_details(endpoint)

        if not route:
            return jsonify({"success": False, "message": "Rota não encontrada"}), 404

        # Remover objeto função
        if "function" in route:
            del route["function"]

        # Adicionar guia de implementação
        implementation_guide = route_audit_service.get_implementation_guide(route)

        return jsonify(
            {
                "success": True,
                "route": route,
                "implementation_guide": implementation_guide,
            }
        )

    except Exception as e:
        return (
            jsonify(
                {
                    "success": False,
                    "message": f"Erro ao obter detalhes da rota: {str(e)}",
                }
            ),
            500,
        )


@route_audit_bp.route("/api/config", methods=["GET"])
@login_required
def get_logging_config():
    """Obtém configuração atual de logging automático"""
    try:
        # Apenas administradores podem acessar
        if (
            not current_user
            or not current_user.is_authenticated
            or getattr(current_user, "role", None) != "admin"
        ):
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Acesso negado. Apenas administradores podem acessar.",
                    }
                ),
                403,
            )

        config = get_auto_logging_config()

        return jsonify({"success": True, "config": config})

    except Exception as e:
        return (
            jsonify(
                {"success": False, "message": f"Erro ao obter configuração: {str(e)}"}
            ),
            500,
        )


@login_required
@route_audit_bp.route("/api/entity/<entity_type>/enable", methods=["POST"])
def enable_entity_logging(entity_type):
    """Habilita logging automático para um tipo de entidade"""
    try:
        # Apenas administradores podem modificar
        if current_user.role != "admin":
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Acesso negado. Apenas administradores podem modificar configurações.",
                    }
                ),
                403,
            )

        enable_auto_logging_for_entity(entity_type)

        return jsonify(
            {
                "success": True,
                "message": f"Logging automático habilitado para {entity_type}",
                "entity_type": entity_type,
            }
        )

    except Exception as e:
        return (
            jsonify(
                {"success": False, "message": f"Erro ao habilitar logging: {str(e)}"}
            ),
            500,
        )


@login_required
@route_audit_bp.route("/api/entity/<entity_type>/disable", methods=["POST"])
def disable_entity_logging(entity_type):
    """Desabilita logging automático para um tipo de entidade"""
    try:
        # Apenas administradores podem modificar
        if current_user.role != "admin":
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Acesso negado. Apenas administradores podem modificar configurações.",
                    }
                ),
                403,
            )

        disable_auto_logging_for_entity(entity_type)

        return jsonify(
            {
                "success": True,
                "message": f"Logging automático desabilitado para {entity_type}",
                "entity_type": entity_type,
            }
        )

    except Exception as e:
        return (
            jsonify(
                {"success": False, "message": f"Erro ao desabilitar logging: {str(e)}"}
            ),
            500,
        )


@route_audit_bp.route("/api/export-report", methods=["GET"])
@login_required
def export_audit_report():
    """Exporta relatório de auditoria em formato CSV"""
    try:
        # Apenas administradores podem exportar
        if current_user.role != "admin":
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Acesso negado. Apenas administradores podem exportar.",
                    }
                ),
                403,
            )

        import csv
        import io
        from datetime import datetime

        routes = route_audit_service.discover_all_routes()

        output = io.StringIO()
        writer = csv.writer(output)

        # Cabeçalho
        writer.writerow(
            [
                "Endpoint",
                "Path",
                "Métodos",
                "Blueprint",
                "Tipo de Entidade",
                "É CRUD",
                "Tem Auto-Log",
                "Tem Log Manual",
                "Precisa de Log",
                "Status",
            ]
        )

        # Dados
        for route in routes:
            has_logging = route["has_auto_log"] or route["has_manual_log"]
            needs_logging = route["needs_logging"]

            status = "OK"
            if needs_logging and not has_logging:
                status = "SEM LOG"
            elif has_logging:
                status = "COM LOG"
            elif not needs_logging:
                status = "NÃO NECESSÁRIO"

            writer.writerow(
                [
                    route["endpoint"],
                    route["path"],
                    ", ".join(route["methods"]),
                    route["blueprint"] or "",
                    route["entity_type"] or "",
                    "Sim" if route["is_crud"] else "Não",
                    "Sim" if route["has_auto_log"] else "Não",
                    "Sim" if route["has_manual_log"] else "Não",
                    "Sim" if needs_logging else "Não",
                    status,
                ]
            )

        output.seek(0)
        csv_content = output.getvalue()
        output.close()

        return jsonify(
            {
                "success": True,
                "csv_content": csv_content,
                "filename": f'route_audit_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
            }
        )

    except Exception as e:
        return (
            jsonify(
                {"success": False, "message": f"Erro ao exportar relatório: {str(e)}"}
            ),
            500,
        )
