from __future__ import annotations

import argparse
import os
import sys


BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Habilita o módulo multi-tenant de Leilões Imobiliários para uma empresa do APP32."
    )
    selector = parser.add_mutually_exclusive_group(required=True)
    selector.add_argument("--company-id", type=int, help="ID da empresa/tenant.")
    selector.add_argument("--client-code", help="Código do cliente, ex.: GND.")
    selector.add_argument("--name-contains", help="Trecho do nome da empresa, ex.: GanduInvest.")
    parser.add_argument("--display-name", default="Leilões Imobiliários", help="Nome exibido no APP32.")
    parser.add_argument("--code-prefix", default=None, help="Prefixo sugerido para imóveis, ex.: GND.")
    parser.add_argument("--disable", action="store_true", help="Desabilita o módulo em vez de habilitar.")
    return parser.parse_args()


def main() -> int:
    from app import create_app
    from models import Company
    from services.real_estate_auction_service import RealEstateAuctionService

    args = _parse_args()
    app = create_app(os.environ.get("FLASK_CONFIG", "default"))

    with app.app_context():
        query = Company.query
        if args.company_id:
            company = query.filter_by(id=args.company_id).first()
        elif args.client_code:
            company = query.filter_by(client_code=args.client_code).first()
        else:
            company = query.filter(Company.name.ilike(f"%{args.name_contains}%")).order_by(Company.id.asc()).first()

        if company is None:
            print("Empresa não encontrada para o seletor informado.", file=sys.stderr)
            return 2

        payload = {
            "module_enabled": not args.disable,
            "display_name": args.display_name,
            "code_prefix": args.code_prefix or company.client_code,
        }
        settings = RealEstateAuctionService.upsert_tenant_settings(company.id, payload)
        state = "habilitado" if settings["module_enabled"] else "desabilitado"
        print(
            f"Módulo Leilões Imobiliários {state}: "
            f"company_id={company.id}, empresa={company.name}, prefixo={settings.get('code_prefix') or '-'}"
        )
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
