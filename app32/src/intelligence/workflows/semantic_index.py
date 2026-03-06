from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence

from .contracts import WorkflowDefinition
from .normalization import normalize_text, root_set, tokenize_text


def build_token_bigrams(tokens: Sequence[str]) -> set[str]:
    if len(tokens) < 2:
        return set()
    return {
        f"{tokens[idx]} {tokens[idx + 1]}"
        for idx in range(len(tokens) - 1)
    }


@dataclass(frozen=True)
class WorkflowSemanticProfile:
    workflow: WorkflowDefinition
    fragments: tuple[str, ...]
    normalized_fragments: tuple[str, ...]
    token_set: frozenset[str]
    root_set: frozenset[str]
    bigrams: frozenset[str]


class WorkflowSemanticIndex:
    def __init__(self, workflows: Iterable[WorkflowDefinition]):
        self._profiles: List[WorkflowSemanticProfile] = [
            self._build_profile(workflow)
            for workflow in workflows
        ]
        self._by_code: Dict[str, WorkflowSemanticProfile] = {
            profile.workflow.code: profile
            for profile in self._profiles
        }

    def list(self) -> List[WorkflowSemanticProfile]:
        return list(self._profiles)

    def get(self, workflow_code: str) -> WorkflowSemanticProfile | None:
        return self._by_code.get(str(workflow_code or "").strip())

    def __iter__(self):
        return iter(self._profiles)

    @classmethod
    def _build_profile(cls, workflow: WorkflowDefinition) -> WorkflowSemanticProfile:
        fragments = cls._build_fragments(workflow)
        normalized_fragments = tuple(
            normalize_text(fragment)
            for fragment in fragments
            if normalize_text(fragment)
        )
        token_values: set[str] = set()
        root_values: set[str] = set()
        bigram_values: set[str] = set()

        for fragment in fragments:
            tokens = tokenize_text(fragment)
            token_values.update(tokens)
            root_values.update(root_set(fragment))
            bigram_values.update(build_token_bigrams(tokens))

        return WorkflowSemanticProfile(
            workflow=workflow,
            fragments=tuple(fragments),
            normalized_fragments=normalized_fragments,
            token_set=frozenset(token_values),
            root_set=frozenset(root_values),
            bigrams=frozenset(bigram_values),
        )

    @staticmethod
    def _build_fragments(workflow: WorkflowDefinition) -> List[str]:
        fragments: List[str] = []
        seen: set[str] = set()

        def _add(raw_value: str | None) -> None:
            normalized = normalize_text(raw_value or "")
            if not normalized or normalized in seen:
                return
            seen.add(normalized)
            fragments.append(str(raw_value or "").strip())

        _add(workflow.title)
        _add(workflow.description)
        _add(workflow.action_key.replace(".", " ").replace("_", " "))

        for keyword in workflow.keywords:
            _add(keyword)
        for example in workflow.intent_examples:
            _add(example)
        for field in workflow.required_fields:
            _add(field.label)
            _add(field.key.replace("_", " "))
        _add(workflow.confirmation_template)
        _add(workflow.execution_template)

        return fragments
