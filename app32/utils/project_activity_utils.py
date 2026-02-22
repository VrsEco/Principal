from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


def _extract_sequence_from_code(
    code: Optional[str], project_code: Optional[str]
) -> Optional[int]:
    """Return numeric sequence found at the end of an activity code.
    
    Supports formats:
    - {company_code}.J.{project_num}.{activity_num} -> returns activity_num
    - {project_code}.{activity_num} -> returns activity_num
    - ATV-{activity_num} -> returns activity_num
    """
    if not code:
        return None

    text = str(code).strip()
    if not text:
        return None

    # Check for format: {company_code}.J.{project_num}.{activity_num}
    parts = text.split(".")
    if len(parts) >= 4 and parts[1] == "J":
        # Format: {company_code}.J.{project_num}.{activity_num}
        try:
            return int(parts[-1])
        except (ValueError, IndexError):
            pass
    
    # Check for format: {project_code}.{activity_num}
    if project_code:
        prefix = f"{project_code}."
        if text.startswith(prefix):
            suffix = text[len(prefix) :]
            digits = "".join(ch for ch in suffix if ch.isdigit())
            if digits:
                try:
                    return int(digits)
                except ValueError:
                    pass
    
    # Fallback: extract last numeric part
    if len(parts) > 1:
        suffix = parts[-1]
    else:
        suffix = text
    
    digits = "".join(ch for ch in suffix if ch.isdigit())
    if not digits:
        return None

    try:
        return int(digits)
    except ValueError:
        return None


def _normalize_score_weight(value: Any) -> float:
    """Ensure score weight is a positive float with two decimal precision."""
    default = Decimal("1")

    if value in (None, "", "null"):
        return float(default)

    try:
        if isinstance(value, Decimal):
            weight = value
        elif isinstance(value, (int, float)):
            weight = Decimal(str(value))
        else:
            text = str(value).strip().replace(",", ".")
            if not text:
                return float(default)
            weight = Decimal(text)
    except (InvalidOperation, ValueError, TypeError):
        return float(default)

    if weight <= 0:
        return float(default)

    normalized = weight.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return float(normalized)


def normalize_project_activities(
    activities: Any,
    project_code: Optional[str],
    company_code: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], bool, int]:
    """Normalize project activities ensuring ids, stage, status and sequential codes.

    Returns a tuple with the normalized list, a flag indicating whether any change was made,
    and the highest numeric sequence found in the activity codes.
    """
    changed = False

    if not isinstance(activities, list):
        return [], activities is not None, 0

    normalized: List[Dict[str, Any]] = []
    for activity in activities:
        if isinstance(activity, dict):
            normalized.append(dict(activity))
        else:
            changed = True

    if not normalized:
        return normalized, changed, 0

    # Ensure unique positive IDs
    seen_ids: set[int] = set()
    next_id = 1
    for item in normalized:
        raw_id = item.get("id")
        try:
            parsed_id = int(raw_id)
        except (TypeError, ValueError):
            parsed_id = None

        if parsed_id is None or parsed_id <= 0 or parsed_id in seen_ids:
            while next_id in seen_ids:
                next_id += 1
            item["id"] = next_id
            seen_ids.add(next_id)
            next_id += 1
            changed = True
        else:
            item["id"] = parsed_id
            seen_ids.add(parsed_id)
            if parsed_id >= next_id:
                next_id = parsed_id + 1

    # Default stage, status and score weight
    for item in normalized:
        weight_raw = item.get("score_weight")
        normalized_weight = _normalize_score_weight(weight_raw)
        weight_changed = False
        if weight_raw is None:
            weight_changed = True
        else:
            try:
                weight_float = float(str(weight_raw).strip().replace(",", "."))
            except (ValueError, TypeError):
                weight_float = None
            if weight_float is None or round(weight_float, 2) != round(normalized_weight, 2):
                weight_changed = True
        if weight_changed:
            changed = True
        item["score_weight"] = normalized_weight

        stage = str(item.get("stage") or "").strip()
        status = str(item.get("status") or "").strip()

        if not stage:
            item["stage"] = "inbox"
            stage = "inbox"
            changed = True

        if not status:
            # Fall back to stage when possible
            item["status"] = stage if stage != "inbox" else "pending"
            changed = True

    # Ensure sequential codes - always generate codes
    max_sequence = 0
    assigned_sequences: set[int] = set()

    # Extract existing sequences from activities
    for item in normalized:
        code = str(item.get("code") or "").strip()
        if code:
            sequence = _extract_sequence_from_code(code, project_code)
            if sequence:
                assigned_sequences.add(sequence)
                if sequence > max_sequence:
                    max_sequence = sequence

    # Generate codes for activities without codes
    next_sequence = max_sequence + 1
    for item in normalized:
        code = str(item.get("code") or "").strip()
        if code:
            continue

        # Find next available sequence
        while next_sequence in assigned_sequences:
            next_sequence += 1

        # Generate code based on project code format
        # Format: {company_code}.J.{project_number}.{activity_number}
        if project_code and company_code:
            # Extract project number from project_code (format: {company_code}.J.{number})
            project_num = None
            if project_code.startswith(f"{company_code}.J."):
                try:
                    project_num = int(project_code.split(".")[-1])
                except (ValueError, IndexError):
                    pass
            
            if project_num is not None:
                item["code"] = f"{company_code}.J.{project_num}.{next_sequence:02d}"
            else:
                # Fallback: use project_code as is
                item["code"] = f"{project_code}.{next_sequence:02d}"
        elif project_code:
            item["code"] = f"{project_code}.{next_sequence:02d}"
        else:
            item["code"] = f"ATV-{next_sequence:02d}"

        assigned_sequences.add(next_sequence)
        if next_sequence > max_sequence:
            max_sequence = next_sequence
        next_sequence += 1
        changed = True

    return normalized, changed, max_sequence
