from __future__ import annotations

import re
import unicodedata
from typing import Any

from models import Company, Employee, KeyResultArea, OKRArea, OKRGlobal, Project, db


class SectorStrategyStructureError(ValueError):
    """Falha de validação que deve abortar toda a mutação setorial."""


class SectorStrategyStructureService:
    """Cria OKRs setoriais, KRs e iniciativas em uma transação tenant-safe."""

    @staticmethod
    def _normalize(value: str) -> str:
        folded = unicodedata.normalize("NFKD", str(value or ""))
        ascii_value = "".join(char for char in folded if not unicodedata.combining(char))
        return re.sub(r"\s+", " ", ascii_value.casefold()).strip()

    @classmethod
    def _resolve_employee(cls, *, company_id: int, informed_name: str) -> Employee:
        requested = cls._normalize(informed_name)
        if not requested:
            raise SectorStrategyStructureError("Nome de responsável vazio.")
        employees = Employee.query.filter(
            Employee.company_id == company_id,
            Employee.status == "active",
        ).all()
        exact = [item for item in employees if cls._normalize(item.name) == requested]
        if len(exact) == 1:
            return exact[0]
        prefix = [
            item
            for item in employees
            if cls._normalize(item.name).split(" ", 1)[0] == requested
            or cls._normalize(item.name).startswith(f"{requested} ")
        ]
        if len(prefix) == 1:
            return prefix[0]
        if len(exact) > 1 or len(prefix) > 1:
            raise SectorStrategyStructureError(
                f"Identidade ambígua para '{informed_name}' na empresa {company_id}."
            )
        raise SectorStrategyStructureError(
            f"Identidade ativa não encontrada para '{informed_name}' na empresa {company_id}."
        )

    @classmethod
    def execute(
        cls,
        *,
        company_id: int,
        payload: dict[str, Any],
        confirmed_mutation: bool,
        user_id: int | None = None,
    ) -> dict[str, Any]:
        if confirmed_mutation is not True:
            raise PermissionError("Confirmação humana explícita é obrigatória para cadastrar a estrutura setorial.")
        if not isinstance(company_id, int) or isinstance(company_id, bool) or company_id <= 0:
            raise SectorStrategyStructureError("company_id deve ser um inteiro positivo.")
        if Company.query.filter(Company.id == company_id).first() is None:
            raise SectorStrategyStructureError(f"Empresa {company_id} não encontrada.")
        okrs_payload = payload.get("okrs") if isinstance(payload, dict) else None
        if not isinstance(okrs_payload, list) or not okrs_payload:
            raise SectorStrategyStructureError("payload.okrs deve conter ao menos um OKR setorial.")

        names = set()
        for item in okrs_payload:
            if not isinstance(item, dict):
                raise SectorStrategyStructureError("Cada OKR deve ser um objeto.")
            for key in ("owner_name", "internal_client_name"):
                if item.get(key):
                    names.add(str(item[key]).strip())
            for initiative in item.get("initiatives") or []:
                if initiative.get("owner_name"):
                    names.add(str(initiative["owner_name"]).strip())
        identities = {
            informed: cls._resolve_employee(company_id=company_id, informed_name=informed)
            for informed in sorted(names)
        }

        corporate_before = [
            (row.id, row.objective, row.updated_at.isoformat() if row.updated_at else None)
            for row in OKRGlobal.query.filter(OKRGlobal.company_id == company_id).order_by(OKRGlobal.id).all()
        ]
        result: dict[str, Any] = {
            "company_id": company_id,
            "user_id": user_id,
            "created": {"okrs": [], "key_results": [], "projects": []},
            "reused": {"okrs": [], "key_results": [], "projects": []},
            "resolved_identities": [
                {"informed_name": informed, "employee_id": employee.id, "official_name": employee.name}
                for informed, employee in identities.items()
            ],
            "pending": [
                "Vínculos com indicadores corporativos não foram criados: não houve correspondência confirmada.",
                "Colaboradores/projetos órfãos preexistentes não foram conectados sem correspondência confirmada.",
            ],
        }

        try:
            for item in okrs_payload:
                objective = str(item.get("objective") or "").strip()
                department = str(item.get("department") or "").strip() or None
                okr_type = str(item.get("okr_type") or "estruturante").strip()
                if not objective or not department:
                    raise SectorStrategyStructureError("objective e department são obrigatórios em cada OKR.")
                owner = identities[str(item["owner_name"]).strip()].name if item.get("owner_name") else None
                internal_client = (
                    identities[str(item["internal_client_name"]).strip()].name
                    if item.get("internal_client_name")
                    else None
                )
                observations = str(item.get("observations") or "").strip()
                if internal_client:
                    note = f"Cliente interno: {internal_client}. Não é responsável pela execução logística."
                    observations = f"{observations}\n{note}".strip()

                normalized_objective = cls._normalize(objective)
                existing_okrs = OKRArea.query.filter(OKRArea.company_id == company_id).all()
                matches = [row for row in existing_okrs if cls._normalize(row.objective) == normalized_objective]
                if len(matches) > 1:
                    raise SectorStrategyStructureError(f"OKR setorial duplicado preexistente: {objective}")
                if matches:
                    okr = matches[0]
                    if cls._normalize(okr.department or "") != cls._normalize(department or ""):
                        raise SectorStrategyStructureError(f"OKR existente diverge do departamento: {objective}")
                    result["reused"]["okrs"].append(okr.id)
                else:
                    okr = OKRArea(
                        company_id=company_id,
                        objective=objective,
                        type=okr_type,
                        department=department,
                        owner=owner,
                        observations=observations or None,
                        linked_okr_ids=[],
                    )
                    db.session.add(okr)
                    db.session.flush()
                    result["created"]["okrs"].append(okr.id)

                existing_krs = KeyResultArea.query.filter(KeyResultArea.okr_area_id == okr.id).all()
                for kr_data in item.get("key_results") or []:
                    label = str(kr_data.get("label") or "").strip()
                    if not label:
                        raise SectorStrategyStructureError("Todo resultado-chave deve possuir label.")
                    kr_matches = [row for row in existing_krs if cls._normalize(row.label) == cls._normalize(label)]
                    if kr_matches:
                        result["reused"]["key_results"].append(kr_matches[0].id)
                        continue
                    kr = KeyResultArea(
                        okr_area_id=okr.id,
                        label=label,
                        metric=str(kr_data.get("metric") or "proposta").strip() or "proposta",
                        target=str(kr_data.get("target") or "").strip() or None,
                        owner=None,
                    )
                    db.session.add(kr)
                    db.session.flush()
                    existing_krs.append(kr)
                    result["created"]["key_results"].append(kr.id)

                existing_projects = Project.query.filter(
                    Project.company_id == company_id,
                    Project.is_deleted.is_(False),
                ).all()
                for project_data in item.get("initiatives") or []:
                    name = str(project_data.get("name") or "").strip()
                    if not name:
                        raise SectorStrategyStructureError("Toda iniciativa deve possuir name.")
                    project_matches = [row for row in existing_projects if cls._normalize(row.name) == cls._normalize(name)]
                    if project_matches:
                        project = project_matches[0]
                        if okr.id not in (project.okr_links or []):
                            raise SectorStrategyStructureError(
                                f"Projeto existente sem o vínculo esperado; atualização automática bloqueada: {name}"
                            )
                        result["reused"]["projects"].append(project.id)
                        continue
                    project_owner = identities[str(project_data["owner_name"]).strip()].name
                    project = Project(
                        company_id=company_id,
                        name=name,
                        description=str(project_data.get("description") or "").strip() or None,
                        owner=project_owner,
                        status="planned",
                        okr_links=[okr.id],
                    )
                    db.session.add(project)
                    db.session.flush()
                    existing_projects.append(project)
                    result["created"]["projects"].append(project.id)

            corporate_after = [
                (row.id, row.objective, row.updated_at.isoformat() if row.updated_at else None)
                for row in OKRGlobal.query.filter(OKRGlobal.company_id == company_id).order_by(OKRGlobal.id).all()
            ]
            if corporate_after != corporate_before:
                raise SectorStrategyStructureError("A proteção detectou alteração em OKRs corporativos; transação abortada.")
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        result["corporate_okrs_unchanged"] = True
        result["corporate_okr_snapshot"] = [item[0] for item in corporate_before]
        result["human_confirmation_applied"] = True
        return result


__all__ = ["SectorStrategyStructureError", "SectorStrategyStructureService"]
