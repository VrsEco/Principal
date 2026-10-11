"""Conector administrativo curado do mcp-versus (``/mcp/pilot/admin``, escopo OAuth ``mcp:admin``).

O conector comum (``/mcp/pilot``) nunca recebe ``mcp:admin``. Estas ferramentas pertencem à surface ``admin``:
ficavam inalcançáveis pelos clientes OAuth (violação M7 do contrato de mutações). A lista é fechada e revisada:
só exclusões e aprovações que já têm aprovação humana persistida (regra D6) e permissão por empresa.

Ficam FORA, de propósito: diagnósticos do sistema, cadastro de usuários, status de empresa, implantação de agentes
e WhatsApp Status. Cada uma pede revisão e autorização próprias antes de entrar aqui.
"""

from __future__ import annotations

ADMIN_CONNECTOR_TOOL_NAMES: tuple[str, ...] = (
    "approve_work_journey_absence_request_tool",
    "approve_work_journey_transfer_request_tool",
    "delete_commercial_contract",
    "delete_indicator_line_of_sight_tool",
    "delete_process_strategy_alignment_link_tool",
    "delete_work_journey_block_tool",
    "delete_work_journey_manual_task_tool",
    "delete_work_journey_rule_tool",
)
