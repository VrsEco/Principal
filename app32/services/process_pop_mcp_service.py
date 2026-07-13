from __future__ import annotations
import base64
import binascii
from io import BytesIO
from typing import Any
from werkzeug.datastructures import FileStorage
from sqlalchemy import func
from models import db, Process, ProcessRoutine, ProcessStep
from services.process_bpmn_pop_binding_service import open_or_create_pop_activity_for_bpmn, serialize_pop_binding
from utils.storage import delete_file, save_file

def create_pop_step_for_bpmn(*, company_id: int, process_id: int, bpmn_element_id: str, name: str, description: str | None = None, expected_result: str | None = None, bpmn_element_name: str | None = None, bpmn_element_type: str | None = None, order_index: int | None = None) -> dict[str, Any]:
    process = Process.query.filter_by(id=process_id, company_id=company_id).first()
    if not process: raise ValueError("Processo não encontrado para a empresa informada.")
    if not str(bpmn_element_id or "").strip() or not str(name or "").strip(): raise ValueError("bpmn_element_id e name são obrigatórios.")
    routine, routine_created = open_or_create_pop_activity_for_bpmn(process=process, payload={"bpmn_element_id": bpmn_element_id, "bpmn_element_name": bpmn_element_name, "bpmn_element_type": bpmn_element_type})
    if order_index is None: order_index = (db.session.query(func.coalesce(func.max(ProcessStep.order_index), 0)).filter(ProcessStep.routine_id == routine.id).scalar() or 0) + 1
    step = ProcessStep(routine_id=routine.id, name=str(name).strip(), description=description, expected_result=expected_result, order_index=order_index)
    db.session.add(step); db.session.commit()
    return {"created": True, "binding": serialize_pop_binding(routine, created=routine_created), "step": _step(step)}

def attach_static_image_to_pop_step(*, company_id: int, step_id: int, image_base64: str, filename: str = "pop-step.png", content_type: str | None = None) -> dict[str, Any]:
    step = ProcessStep.query.join(ProcessRoutine, ProcessRoutine.id == ProcessStep.routine_id).filter(ProcessStep.id == step_id, ProcessRoutine.company_id == company_id).first()
    if not step: raise ValueError("Passo POP não encontrado para a empresa informada.")
    if content_type and content_type.lower() not in {"image/jpeg", "image/png"}: raise ValueError("content_type deve ser image/jpeg ou image/png.")
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if extension not in {"jpg", "jpeg", "png"}: raise ValueError("filename deve ter extensão JPG, JPEG ou PNG.")
    try: raw = base64.b64decode(image_base64, validate=True)
    except (ValueError, binascii.Error) as exc: raise ValueError("image_base64 inválido.") from exc
    if not raw: raise ValueError("A imagem não pode estar vazia.")
    if len(raw) > 10 * 1024 * 1024: raise ValueError("A imagem excede o limite de 10 MB.")
    if step.image_path: delete_file(step.image_path)
    step.image_path = save_file(FileStorage(stream=BytesIO(raw), filename=filename, content_type=content_type), subfolder="pop")
    db.session.commit()
    return {"updated": True, "step": _step(step)}

def _step(step: ProcessStep) -> dict[str, Any]:
    return {"id": step.id, "routine_id": step.routine_id, "name": step.name, "description": step.description, "expected_result": step.expected_result, "order_index": step.order_index, "image_path": step.image_path, "video_path": step.video_path}
