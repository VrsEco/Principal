from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from services.knowledge.contracts import SourceChunkDocument, SourceDocument
from services.mcp_feature_catalog_service import MCPFeatureCatalogService


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
        (("/sapiens",), "knowledge", "Sapiens"),
        (("/ai", "/api-mcp", "/tools", "/workflow", "/channels", "/qa", "/companies"), "system", "Sistema"),
        (("/portal",), "portal", "Portal"),
    )

    CURATED_CUTOFF_HEADING = "## Uso por IA / MCP"

    def __init__(
        self,
        app_root: str | Path | None = None,
        *,
        feature_catalog_service: MCPFeatureCatalogService | None = None,
    ):
        self.app_root = Path(app_root or Path(__file__).resolve().parents[2])
        # O menu é o sidebar padrão mais os parciais incluídos por ele (Planejamento, Gestão Estratégica,
        # Rotina...): ler só parte deles deixa telas inteiras sem artigo de navegação.
        self.sidebar_files = (
            self.app_root / "templates" / "partials" / "sidebar_standard.html",
            *sorted((self.app_root / "templates" / "partials" / "sidebar").glob("*.html")),
        )
        self.feature_catalog_service = feature_catalog_service or MCPFeatureCatalogService()

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
        entries = self.discover_entries()
        sibling_titles = self._sibling_titles_by_target(entries)
        for entry in entries:
            if urlsplit(entry.navigation_target).path in excluded_paths:
                continue
            content = self._curated_content_for(
                entry, sibling_titles=sibling_titles.get(entry.navigation_target, ())
            )
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

    USER_SECTIONS = ("Objetivo", "Quando usar", "Como orientar o usuário")
    _TECHNICAL_MARKERS = re.compile(r"\b(surface|surfaces|mcp|api|tool|tools|ia)\b")

    def _feature_for(self, entry: ManualNavigationEntry) -> dict | None:
        try:
            return self.feature_catalog_service.find_feature_by_route(urlsplit(entry.navigation_target).path)
        except Exception:
            return None

    def _sibling_titles_by_target(
        self, entries: tuple[ManualNavigationEntry, ...]
    ) -> dict[str, tuple[str, ...]]:
        """Para cada tela, os títulos das OUTRAS telas que compartilham o mesmo guia de feature."""

        members: dict[str, list[ManualNavigationEntry]] = {}
        for entry in entries:
            feature = self._feature_for(entry)
            if feature and feature.get("id"):
                members.setdefault(str(feature["id"]), []).append(entry)
        siblings: dict[str, tuple[str, ...]] = {}
        for group in members.values():
            for entry in group:
                siblings[entry.navigation_target] = tuple(
                    other.title for other in group if self._words(other.title) != self._words(entry.title)
                )
        return siblings

    def _curated_content_for(
        self, entry: ManualNavigationEntry, *, sibling_titles: tuple[str, ...] = ()
    ) -> str:
        """Conteúdo da tela, preferindo o guia curado da feature MCP (`rotas_app`).

        Usa só as seções escritas para pessoas (Objetivo, Quando usar, Como orientar o usuário):
        metadados, entradas/saídas e "Uso por IA / MCP" são técnicos e ficam de fora, assim como
        trechos que citam surface/MCP/API/IA. Quando várias telas compartilham o mesmo guia
        (`sibling_titles`), cada uma recebe só os itens que falam dela, e não os das irmãs; senão as
        telas teriam texto (e embedding) idêntico e a busca não as distinguiria. O nome da tela e o
        caminho no menu abrem o texto. Sem feature, sem guia ou sem essas seções: comportamento
        anterior (genérico, ou guia cortado antes de "Uso por IA / MCP").
        """
        feature = self._feature_for(entry)
        if not feature:
            return self._content(entry)

        guide_ref = str(feature.get("guia_ref") or "").strip()
        if not guide_ref:
            return self._content(entry)

        guide_path = (self.feature_catalog_service.guides_root.parent / guide_ref).resolve()
        if not guide_path.exists():
            return self._content(entry)

        markdown = guide_path.read_text(encoding="utf-8")
        sections = self._user_sections(markdown)
        if not sections:
            return self._cut_before_heading(markdown, self.CURATED_CUTOFF_HEADING)

        def keep(name: str, line: str) -> bool:
            if not sibling_titles or name == "Objetivo":  # o objetivo resume a feature: vale para todas
                return True
            return self._line_owner(line, entry.title, sibling_titles) != "sibling"

        cleaned = {
            name: [line for line in (self._strip_technical(raw) for raw in lines) if line and keep(name, line)]
            for name, lines in sections.items()
        }
        parts = [f"Como acessar {entry.title}", f"Onde fica: {self._menu_path(entry, feature)}."]
        if sibling_titles:
            own = [
                self._plain(line)
                for line in cleaned.get("Como orientar o usuário", [])
                if self._line_owner(line, entry.title, sibling_titles) == "own"
                and not self._plain(line).lower().startswith("acessar")
            ]
            if own:
                parts.append("\n".join(own[:2]))
        if cleaned.get("Objetivo"):
            parts.append("\n".join(cleaned["Objetivo"]))
        if cleaned.get("Quando usar"):
            parts.append("Serve para:\n" + "\n".join(self._as_use_case(line) for line in cleaned["Quando usar"]))
        if cleaned.get("Como orientar o usuário"):
            parts.append("Como usar:\n" + "\n".join(self._renumber(cleaned["Como orientar o usuário"])))
        return "\n\n".join(parts) + "\n"

    @classmethod
    def _user_sections(cls, markdown: str) -> dict[str, list[str]]:
        sections: dict[str, list[str]] = {}
        current: str | None = None
        for line in markdown.splitlines():
            if line.startswith("## "):
                heading = line[3:].strip()
                current = heading if heading in cls.USER_SECTIONS else None
                if current:
                    sections.setdefault(current, [])
                continue
            if current and line.strip():
                sections[current].append(line.rstrip())
        return {name: lines for name, lines in sections.items() if lines}

    @classmethod
    def _strip_technical(cls, line: str) -> str:
        """Tira o trecho técnico (surface/MCP/API/IA); se a linha começa técnica, ela some."""
        segments = line.split(" — ")
        kept: list[str] = []
        for segment in segments:
            if cls._TECHNICAL_MARKERS.search(cls._fold(segment)):
                break
            kept.append(segment)
        if not kept:
            return ""
        text = " — ".join(kept).rstrip(" ;,:")
        if len(kept) < len(segments) and not text.endswith("."):
            text += "."
        return text

    @classmethod
    def _line_owner(cls, line: str, title: str, sibling_titles: tuple[str, ...]) -> str:
        """`own`, `sibling` ou `shared`: de qual tela a linha fala (o título mais específico vence)."""
        lead = re.match(r"^\s*(?:[-*]|\d+\.)\s+\*\*([^*]+)\*\*", line)
        words = cls._words(lead.group(1) if lead else line)
        found = [t for t in (title, *sibling_titles) if cls._contains(words, cls._words(t))]
        if lead and found:
            # item de lista "**Tela**: descrição": o dono é o nome em negrito que mais casa
            longest = max(len(cls._words(t)) for t in found)
            owners = {cls._words(t) for t in found if len(cls._words(t)) == longest}
            if len(owners) == 1:
                return "own" if cls._words(title) in owners else "sibling"
        maximal = [
            t
            for t in found
            if not any(
                len(cls._words(other)) > len(cls._words(t)) and cls._contains(cls._words(other), cls._words(t))
                for other in found
            )
        ]
        distinct = {cls._words(t) for t in maximal}
        if len(distinct) != 1:
            return "shared"  # nenhuma tela, ou uma enumeração de várias: vale para todas
        return "own" if cls._words(title) in distinct else "sibling"

    def _menu_path(self, entry: ManualNavigationEntry, feature: dict) -> str:
        base = str(feature.get("caminho_menu") or entry.module_label).strip()
        title_words = self._words(entry.title)
        if title_words and self._words(base)[-len(title_words):] == title_words:
            return base
        return f"{base} > {entry.title}"

    @staticmethod
    def _plain(line: str) -> str:
        text = re.sub(r"^\s*(?:[-*]|\d+\.)\s+", "", line)
        return text.replace("**", "").strip()

    @classmethod
    def _as_use_case(cls, line: str) -> str:
        # "explicar como cadastrar X" (instrução para a IA) -> "Como cadastrar X" (texto para a pessoa)
        text = re.sub(r"^(explicar|orientar)\s+", "", cls._plain(line), flags=re.I)
        return f"- {text[:1].upper()}{text[1:]}"

    @staticmethod
    def _renumber(lines: list[str]) -> list[str]:
        counter = 0
        out = []
        for line in lines:
            match = re.match(r"^\d+\.\s", line)
            if match:
                counter += 1
                line = f"{counter}. " + line[match.end():]
            out.append(line)
        return out

    @staticmethod
    def _fold(text: str) -> str:
        return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()

    @classmethod
    def _words(cls, text: str) -> tuple[str, ...]:
        """Palavras sem acento/caixa e sem plural simples (`contas` -> `conta`), para casar títulos."""
        return tuple(
            w[:-1] if len(w) > 3 and w.endswith("s") else w for w in re.findall(r"[a-z0-9]+", cls._fold(text))
        )

    @staticmethod
    def _contains(haystack: tuple[str, ...], needle: tuple[str, ...]) -> bool:
        n = len(needle)
        return bool(n) and any(haystack[i : i + n] == needle for i in range(len(haystack) - n + 1))

    @staticmethod
    def _cut_before_heading(markdown: str, heading: str) -> str:
        """Corta `markdown` antes do heading exato (linha própria); sem o heading, retorna tudo."""
        lines = markdown.splitlines()
        for index, line in enumerate(lines):
            if line.strip() == heading.strip():
                return "\n".join(lines[:index]).rstrip() + "\n"
        return markdown

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
