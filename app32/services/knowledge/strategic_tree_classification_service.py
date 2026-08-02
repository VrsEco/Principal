from __future__ import annotations

import re
import unicodedata


class StrategicTreeClassificationService:
    BRANCH_RULES = (
        ("Identidade e Direcionamento", ("missao", "visao", "valores", "mvv", "organograma", "identidade")),
        ("Mercado e Público", ("mercado", "cliente", "publico", "concorrente", "tendencia", "segmento")),
        ("Produtos e Serviços", ("produto", "servico", "oferta", "mercadoria", "margem", "escalabilidade")),
        ("Prospecção e Venda", ("prospeccao", "pre-atendimento", "venda", "comercial", "atendimento")),
        ("Execução e Entrega", ("execucao", "entrega", "producao", "logistica", "beneficiamento", "extracao")),
        ("Comunicação de Valor e Continuidade", ("valor agregado", "comunicacao de valor", "pos-venda", "recompra", "continuidade")),
        ("Arquitetura de Processos", ("macroprocesso", "processo", "arquitetura", "indicador", "incentivo")),
    )

    @staticmethod
    def normalize(content: str) -> str:
        value = unicodedata.normalize("NFD", str(content or ""))
        value = "".join(char for char in value if unicodedata.category(char) != "Mn")
        return re.sub(r"\s+", " ", value.lower()).strip()

    @classmethod
    def classify(cls, content: str) -> dict:
        normalized = cls.normalize(content)
        best_title = "Caixa de entrada"
        best_hits: list[str] = []
        for title, keywords in cls.BRANCH_RULES:
            hits = [keyword for keyword in keywords if keyword in normalized]
            if len(hits) > len(best_hits):
                best_title = title
                best_hits = hits
        return {
            "suggested_branch_title": best_title,
            "suggested_contribution_type": "human_statement",
            "matched_terms": best_hits,
            "confidence": 0.82 if len(best_hits) >= 2 else (0.68 if best_hits else 0.25),
            "ambiguity": not bool(best_hits),
            "classifier": "strategic-tree-rules-v1",
        }
