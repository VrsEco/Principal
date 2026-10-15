"""Reprocessa títulos do contas a receber que sobraram de faturamentos cancelados.

Modos:
  (padrão)  DRY-RUN, somente leitura: gera CSV/JSON com a ação proposta por título.
  --execute aplica o cancelamento apenas nos títulos com ação "cancelar" presentes no
            dry-run aprovado (--approved-dry-run) e que continuam elegíveis na hora.

Exemplos:
  python scripts/reprocess_cancelled_billing_titles.py --company-id 1
  python scripts/reprocess_cancelled_billing_titles.py --all-companies
  python scripts/reprocess_cancelled_billing_titles.py --company-id 1 --execute \
      --approved-dry-run out/dry_run_company1_20261015.json --user-id 14

Antes de alterar, grava snapshot completo (títulos, baixas e rateios) para reversão e, ao
final, o relatório pós-execução com contagem e totais antes/depois.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

os.environ.setdefault("APP_BOOTSTRAP_RUNTIME_SERVICES", "0")
os.environ.setdefault("APP_BOOTSTRAP_DB_SCHEMA", "0")

from app import create_app  # noqa: E402
from models import Company, db  # noqa: E402
from services.contract_billing_orphan_titles_service import (  # noqa: E402
    ACTION_CANCEL,
    OrphanBillingTitlesService,
)


def _stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _dry_run(company_id: int, output_dir: Path) -> dict:
    groups = OrphanBillingTitlesService.scan(company_id=company_id)
    rows = OrphanBillingTitlesService.build_rows(groups)
    summary = OrphanBillingTitlesService.summarize(rows)
    metrics = OrphanBillingTitlesService.ledger_metrics(company_id=company_id)
    files = OrphanBillingTitlesService.write_report(
        rows=rows,
        summary=summary,
        directory=output_dir,
        stem=f"dry_run_company{company_id}_{_stamp()}",
        meta={"company_id": company_id, "gerado_em": datetime.now().isoformat(), "modo": "dry-run", "metricas_atuais": metrics},
    )
    db.session.rollback()
    return {"company_id": company_id, "rows": len(rows), "totais": summary, "metricas": metrics, "arquivos": files}


def _execute(company_id: int, user_id: int, approved_file: Path, output_dir: Path) -> dict:
    approved = json.loads(approved_file.read_text(encoding="utf-8"))
    if int(approved.get("meta", {}).get("company_id", 0)) != company_id:
        raise SystemExit("O dry-run aprovado pertence a outra empresa.")
    approved_entry_ids = {int(row["entry_id"]) for row in approved.get("titulos", []) if row.get("acao") == ACTION_CANCEL}
    if not approved_entry_ids:
        raise SystemExit("Nenhum título com ação 'cancelar' no dry-run aprovado.")

    stamp = _stamp()
    before = OrphanBillingTitlesService.ledger_metrics(company_id=company_id)
    groups = [
        group
        for group in OrphanBillingTitlesService.scan(company_id=company_id)
        if group["action"] == ACTION_CANCEL and approved_entry_ids.intersection(item["entry"].id for item in group["analyses"])
    ]
    entries = [item["entry"] for group in groups for item in group["analyses"]]
    snapshot_path = output_dir / f"snapshot_antes_company{company_id}_{stamp}.json"
    output_dir.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text(
        json.dumps(
            {"company_id": company_id, "gerado_em": datetime.now().isoformat(), "titulos": OrphanBillingTitlesService.ledger_snapshot(company_id=company_id, entries=entries)},
            ensure_ascii=False,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )
    print(f"Snapshot gravado em {snapshot_path}")

    results = OrphanBillingTitlesService.execute(company_id=company_id, user_id=user_id, approved_entry_ids=approved_entry_ids)
    after = OrphanBillingTitlesService.ledger_metrics(company_id=company_id)
    report = {
        "company_id": company_id,
        "executado_em": datetime.now().isoformat(),
        "user_id": user_id,
        "dry_run_aprovado": str(approved_file),
        "snapshot": str(snapshot_path),
        "faturamentos_cancelados": sum(1 for item in results if item["resultado"] == "cancelado"),
        "faturamentos_ignorados": [item for item in results if item["resultado"].startswith("ignorado")],
        "faturamentos_com_erro": [item for item in results if item["resultado"] == "erro"],
        "antes": before,
        "depois": after,
        "variacao_receber_aberto": {
            "titulos": after["receber_aberto"]["titulos"] - before["receber_aberto"]["titulos"],
            "saldo_aberto": round(after["receber_aberto"]["saldo_aberto"] - before["receber_aberto"]["saldo_aberto"], 2),
        },
        "faturamentos_ativos_intactos": before["faturamentos_ativos"] == after["faturamentos_ativos"],
        "resultados": results,
    }
    report_path = output_dir / f"pos_execucao_company{company_id}_{stamp}.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Relatório pós-execução em {report_path}")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--company-id", type=int, help="Empresa a processar.")
    parser.add_argument("--all-companies", action="store_true", help="Varredura read-only de todas as empresas (apenas dry-run).")
    parser.add_argument("--output-dir", default="out/reprocess_cancelled_billing_titles")
    parser.add_argument("--execute", action="store_true", help="Aplica o cancelamento (exige --approved-dry-run e --user-id).")
    parser.add_argument("--approved-dry-run", help="JSON do dry-run aprovado por um humano.")
    parser.add_argument("--user-id", type=int, help="Usuário registrado na auditoria da execução.")
    args = parser.parse_args()

    if args.execute and args.all_companies:
        parser.error("--execute não pode ser combinado com --all-companies.")
    if not args.company_id and not args.all_companies:
        parser.error("Informe --company-id ou --all-companies.")
    if args.execute and not (args.approved_dry_run and args.user_id):
        parser.error("--execute exige --approved-dry-run e --user-id.")

    output_dir = Path(args.output_dir)
    app = create_app()
    with app.app_context():
        if args.execute:
            report = _execute(args.company_id, args.user_id, Path(args.approved_dry_run), output_dir)
            print(json.dumps({k: report[k] for k in ("faturamentos_cancelados", "variacao_receber_aberto", "faturamentos_ativos_intactos")}, ensure_ascii=False, indent=2))
            return 1 if report["faturamentos_com_erro"] else 0

        company_ids = [args.company_id] if args.company_id else [item.id for item in Company.query.order_by(Company.id).all()]
        sweep = [_dry_run(company_id, output_dir) for company_id in company_ids]
        for item in sweep:
            cancelar = item["totais"]["por_acao_receber"]["cancelar"]
            print(
                f"empresa {item['company_id']}: {item['rows']} títulos órfãos; a receber 'cancelar' = "
                f"{cancelar['titulos']} títulos / saldo R$ {cancelar['saldo_aberto']:.2f}; arquivos: {item['arquivos']['csv']}"
            )
        if len(sweep) > 1:
            (output_dir / f"varredura_{_stamp()}.json").write_text(json.dumps(sweep, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
