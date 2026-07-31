from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from services.knowledge.contracts import SourceChunkDocument, SourceDocument


@dataclass(frozen=True)
class ManualNavigationEntry:
    title: str
    navigation_target: str
    route_key: str
    module_key: str
    module_label: str


class ManualCatalogCompiler:
    """Compila todas as entradas navegáveis do menu em ajuda mínima e rastreável."""

    adapter_version = "v1"
    parser_version = "sidebar-navigation-v1"
    chunking_policy = "manual-navigation-v1"
    URL_FOR_TARGETS = {
        "plans.plans_list": "/plans",
        "processes.process_map": "/process-map",
        "processes.processes_list": "/processes",
        "processes.process_portal_redirect": "/process-portal",
        "processes.process_routines_redirect": "/process-routines",
        "processes.bpms_analysis_redirect": "/bpms-analysis",
        "processes.process_instances_redirect": "/process-instances",
        "portfolios.portfolios_page_redirect": "/project-portfolios",
        "projects.projects_list": "/projects",
        "projects.project_analysis": "/projects/analysis",
        "meetings.meetings_manage_root": "/meetings",
        "processes.process_occurrences_redirect": "/process-occurrences",
        "work_journey.work_journey_redirect": "/work-journey",
        "processes.process_routines_analysis_page": "/process-routines/analysis",
        "main.efficiency_analysis_company": "/efficiency-analysis",
        "main.efficiency_analysis": "/efficiency-analysis",
    }
    MODULES = (
        (("/financial",), "finance", "Gestão Financeira"),
        (("/contracts",), "commercial", "Gestão Comercial"),
        (("/indicators", "/incentives", "/plans", "/process-portal/strategic-management"), "strategy", "Gestão Estratégica"),
        (("/process", "/bpms", "/routines"), "processes", "Gestão de Processos"),
        (("/project",), "projects", "Gestão de Projetos"),
        (("/meetings",), "meetings", "Gestão de Reuniões"),
        (("/calendar", "/work-journey", "/my-work", "/efficiency-analysis"), "routine", "Gestão da Rotina"),
        (("/internal-audit",), "internal_audit", "Auditoria Interna"),
        (("/consultive", "/structuring-journey"), "consultive", "Consultivo"),
        (("/real-estate-auctions",), "real_estate_auctions", "Leilões Imobiliários"),
        (("/sapiens",), "knowledge", "Sapiens"),
        (("/ai", "/api-mcp", "/tools", "/workflow", "/channels", "/qa", "/companies"), "system", "Sistema"),
        (("/portal",), "portal", "Portal"),
    )

    def __init__(self, app_root: str | Path | None = None):
        self.app_root = Path(app_root or Path(__file__).resolve().parents[2])
        self.sidebar_files = (
            self.app_root / "templates" / "partials" / "sidebar_standard.html",
            self.app_root / "templates" / "partials" / "sidebar" / "_routine_management.html",
        )

    def discover_entries(self) -> tuple[ManualNavigationEntry, ...]:
        entries: dict[str, ManualNavigationEntry] = {}
        for path in self.sidebar_files:
            if not path.exists():
                continue
            content = path.read_text(encoding="utf-8-sig")
            for match in re.finditer(
                r"<a\s+(?P<attrs>[^>]*?)>(?P<body>.*?)</a>",
                content,
                flags=re.I | re.S,
            ):
                href_match = re.search(r'href="(?P<href>.*?)"', match.group("attrs"), flags=re.S)
                if not href_match:
                    continue
                href = self._resolve_href(href_match.group("href"))
                title = self._clean_label(match.group("body"))
                if not href or not title:
                    continue
                module_key, module_label = self._module_for(href)
                route_key = self._route_key(href_match.group("href"), href)
                entries[href] = ManualNavigationEntry(
                    title=title,
                    navigation_target=href,
                    route_key=route_key,
                    module_key=module_key,
                    module_label=module_label,
                )
        return tuple(entries[target] for target in sorted(entries))

    def compile_documents(
        self,
        *,
        excluded_targets: set[str] | None = None,
    ) -> tuple[SourceDocument, ...]:
        excluded_paths = {
            urlsplit(target).path for target in (excluded_targets or set()) if target
        }
        documents = []
        for entry in self.discover_entries():
            if urlsplit(entry.navigation_target).path in excluded_paths:
                continue
            content = self._content(entry)
            checksum = self._checksum(content)
            source_ref = f"manual.navigation.{self._slugify(entry.navigation_target)}"
            documents.append(
                SourceDocument(
                    knowledge_scope="product",
                    source_type="product_help",
                    source_ref=source_ref,
                    knowledge_kind="product_help",
                    title=f"Acessar {entry.title}",
                    canonical_uri=f"app-versus://help/navigation/{self._slugify(entry.navigation_target)}",
                    status="published",
                    authority_level="official",
                    version="v1",
                    product_version="3.2",
                    locale="pt-BR",
                    route_key=entry.route_key,
                    module_key=entry.module_key,
                    audience=("administrator", "client", "collaborator"),
                    help_kind="navigation",
                    navigation_target=entry.navigation_target,
                    content_checksum=checksum,
                    chunks=(
                        SourceChunkDocument(
                            section_key="como-acessar",
                            content=content,
                            chunk_order=0,
                            content_checksum=checksum,
                            token_count=len(content.split()),
                            source_span="Como acessar",
                            metadata={"compiled_from": "sidebar"},
                            adapter_version=self.adapter_version,
                            parser_version=self.parser_version,
                            chunking_policy=self.chunking_policy,
                        ),
                    ),
                    metadata={
                        "compiled_from": "sidebar",
                        "module_label": entry.module_label,
                        "suggested_questions": [
                            f"Como acessar {entry.title}?",
                            f"Onde encontro {entry.title}?",
                            f"Como faço para ver {entry.title}?",
                        ],
                    },
                )
            )
        return tuple(documents)

    def audit_documents(self, documents: tuple[SourceDocument, ...]) -> dict[str, object]:
        expected_paths = {
            urlsplit(entry.navigation_target).path for entry in self.discover_entries()
        }
        raw_targets = [
            document.navigation_target
            for document in documents
            if document.navigation_target
        ]
        targets = [urlsplit(target).path for target in raw_targets]
        target_set = set(targets)
        missing = sorted(expected_paths - target_set)
        duplicates = sorted(
            target for target in set(raw_targets) if raw_targets.count(target) > 1
        )
        return {
            "ok": not missing and not duplicates,
            "expected_navigation_entries": len(expected_paths),
            "documented_navigation_entries": len(expected_paths & target_set),
            "coverage_percent": round(
                (len(expected_paths & target_set) / len(expected_paths) * 100)
                if expected_paths
                else 100.0,
                2,
            ),
            "missing_targets": missing,
            "duplicate_targets": duplicates,
        }

    @staticmethod
    def _content(entry: ManualNavigationEntry) -> str:
        return (
            f"Como acessar {entry.title}\n\n"
            f"A área **{entry.title}** está disponível no APP Versus, em "
            f"**{entry.module_label}**.\n\n"
            "1. Confirme a empresa ativa no cabeçalho do sistema.\n"
            f"2. Abra **{entry.module_label}** no menu lateral.\n"
            f"3. Selecione **{entry.title}**.\n"
            "4. Use os filtros da própria tela para localizar o registro desejado.\n\n"
            f"Perguntas equivalentes: onde encontro {entry.title}; como faço para ver "
            f"{entry.title}; abrir {entry.title}.\n\n"
            "A disponibilidade da área e dos dados depende das permissões do usuário e "
            "da empresa ativa."
        )

    def _resolve_href(self, raw_href: str) -> str | None:
        raw_href = raw_href.strip()
        if raw_href.startswith("/") and "{{" not in raw_href:
            return raw_href
        endpoints = re.findall(r"url_for\(['\"]([^'\"]+)['\"]", raw_href)
        for endpoint in endpoints:
            target = self.URL_FOR_TARGETS.get(endpoint)
            if target:
                return target
        return None

    @staticmethod
    def _clean_label(body: str) -> str:
        cleaned = re.sub(r"{[{%].*?[%}]}", " ", body, flags=re.S)
        cleaned = re.sub(r"<span\s+class=['\"]nav-pill[^>]*>.*?</span>", " ", cleaned, flags=re.I | re.S)
        cleaned = re.sub(r"<[^>]+>", " ", cleaned)
        return " ".join(cleaned.split())

    @classmethod
    def _module_for(cls, target: str) -> tuple[str, str]:
        path = urlsplit(target).path
        for prefixes, module_key, module_label in cls.MODULES:
            if any(path.startswith(prefix) for prefix in prefixes):
                return module_key, module_label
        return "system", "Sistema"

    @classmethod
    def _route_key(cls, raw_href: str, target: str) -> str:
        endpoint = re.search(r"url_for\(['\"]([^'\"]+)['\"]", raw_href)
        return endpoint.group(1) if endpoint else f"navigation.{cls._slugify(urlsplit(target).path)}"

    @staticmethod
    def _checksum(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    @staticmethod
    def _slugify(value: str) -> str:
        normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
        return normalized or "inicio"
