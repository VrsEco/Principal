from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from models import ProcessRoutine, ProcessStep
from services.process_pop_media_service import POP_VIDEO_MAX_DURATION_SECONDS


class POPStepDescriptionDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(default="")
    suggested_description: str = Field(default="")
    suggested_expected_result: str = Field(default="")
    warnings: list[str] = Field(default_factory=list)
    source: str = Field(default="heuristic")


def build_process_pop_step_media_context(*, company_id: int, step_id: int) -> dict[str, Any]:
    step = (
        ProcessStep.query.join(ProcessRoutine, ProcessRoutine.id == ProcessStep.routine_id)
        .filter(ProcessStep.id == step_id, ProcessRoutine.company_id == company_id)
        .first()
    )
    if not step:
        raise ValueError("Passo POP não encontrado para a empresa informada.")

    routine = (
        ProcessRoutine.query
        .filter(ProcessRoutine.id == step.routine_id, ProcessRoutine.company_id == company_id)
        .first()
    )
    if not routine:
        raise ValueError("Atividade POP não encontrada para a empresa informada.")

    has_video = bool(getattr(step, "video_path", None))
    has_image = bool(getattr(step, "image_path", None))
    has_description = bool(str(getattr(step, "description", "") or "").strip())

    recommended_actions: list[str] = []
    if not has_video:
        recommended_actions.append("upload_short_video")
    if has_video and not has_image:
        recommended_actions.append("capture_key_frame")
    if not has_description:
        recommended_actions.append("draft_step_description")
    if has_video and has_image and has_description:
        recommended_actions.append("ready_for_human_review")

    return {
        "step": {
            "id": int(step.id),
            "routine_id": int(step.routine_id),
            "name": step.name,
            "description": step.description,
            "expected_result": step.expected_result,
            "layout": step.layout,
            "image_path": step.image_path,
            "video_path": getattr(step, "video_path", None),
            "video_duration_seconds": getattr(step, "video_duration_seconds", None),
            "video_narration": getattr(step, "video_narration", None),
        },
        "routine": {
            "id": int(routine.id),
            "process_id": int(routine.process_id),
            "code": routine.code,
            "name": routine.name,
            "bpmn_element_id": getattr(routine, "bpmn_element_id", None),
        },
        "capture_guidelines": {
            "video_max_duration_seconds": POP_VIDEO_MAX_DURATION_SECONDS,
            "recommended_resolution": "480p",
            "recommended_usage": "1 vídeo curto por passo, não por POP completo",
        },
        "coverage": {
            "has_video": has_video,
            "has_image": has_image,
            "has_description": has_description,
        },
        "recommended_actions": recommended_actions,
    }


def suggest_process_pop_step_description(*, company_id: int, step_id: int) -> dict[str, Any]:
    context = build_process_pop_step_media_context(company_id=company_id, step_id=step_id)
    heuristic = _build_description_heuristic(context)
    try:
        from src.intelligence.llm import llm_expert

        llm = llm_expert.with_structured_output(POPStepDescriptionDraft)
        response = llm.invoke(_build_description_messages(context, heuristic))
        draft = response.model_dump() if isinstance(response, BaseModel) else dict(response or {})
        merged = {
            "title": draft.get("title") or heuristic["title"],
            "suggested_description": draft.get("suggested_description") or heuristic["suggested_description"],
            "suggested_expected_result": draft.get("suggested_expected_result") or heuristic["suggested_expected_result"],
            "warnings": list(dict.fromkeys([*(heuristic.get("warnings") or []), *(draft.get("warnings") or [])])),
            "source": "llm",
        }
    except Exception:
        merged = heuristic

    return {
        "context": context,
        "draft": merged,
    }


def _build_description_heuristic(context: dict[str, Any]) -> dict[str, Any]:
    step = context.get("step") or {}
    routine = context.get("routine") or {}
    coverage = context.get("coverage") or {}

    step_name = str(step.get("name") or "Passo do POP").strip()
    routine_name = str(routine.get("name") or "").strip()
    narration = _clean_text(step.get("video_narration"))
    expected_result = _clean_text(step.get("expected_result"))

    fragments: list[str] = []
    if routine_name:
        fragments.append(f"No contexto da atividade \"{routine_name}\", execute o passo \"{step_name}\".")
    else:
        fragments.append(f"Execute o passo \"{step_name}\" conforme a sequência operacional esperada.")

    if narration:
        fragments.append(narration)
    elif coverage.get("has_video"):
        fragments.append("Use o vídeo curto anexado como referência visual da execução correta deste passo.")
    else:
        fragments.append("Descreva objetivamente a ação principal, os campos ou botões envolvidos e o resultado esperado.")

    if expected_result:
        fragments.append(f"Ao final, confirme que {expected_result.rstrip('.')}.")

    warnings: list[str] = []
    if not coverage.get("has_video"):
        warnings.append("Sem vídeo anexado: o rascunho foi gerado sem referência visual.")
    if not coverage.get("has_image"):
        warnings.append("Considere capturar um frame do vídeo para reforçar o print do passo.")
    if not narration:
        warnings.append("Considere adicionar narração/contexto do operador para melhorar o rascunho.")

    return {
        "title": step_name,
        "suggested_description": " ".join(fragment for fragment in fragments if fragment).strip(),
        "suggested_expected_result": expected_result or "O passo é concluído sem erros e a tela apresenta o estado esperado.",
        "warnings": warnings,
        "source": "heuristic",
    }


def _build_description_messages(context: dict[str, Any], heuristic: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "Você é o Sapiens especialista em POP operacional do APP32. "
                "Gere um rascunho curto, claro e objetivo para um único passo de POP. "
                "Não invente telas, campos ou botões que não estejam no contexto. "
                "Retorne apenas o objeto estruturado solicitado."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "context": context,
                    "heuristic": heuristic,
                    "instructions": {
                        "tone": "operacional, direto, claro",
                        "goal": "descrever um único passo do POP",
                    },
                },
                ensure_ascii=False,
            ),
        },
    ]


def _clean_text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())
