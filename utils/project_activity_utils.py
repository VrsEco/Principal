from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


def _extract_sequence_from_code(
    code: Optional[str], project_code: Optional[str]
) -> Optional[int]:
    """Return numeric sequence found at the end of an activity code."""
    if not code:
        return None

    text = str(code).strip()
    if not text:
        return None

    suffix = text
    if project_code:
        prefix = f"{project_code}."
        if text.startswith(prefix):
            suffix = text[len(prefix) :]
        else:
            parts = text.split(".")
            if len(parts) > 1:
                suffix = parts[-1]
    else:
        parts = text.split(".")
        if len(parts) > 1:
            suffix = parts[-1]

    digits = "".join(ch for ch in suffix if ch.isdigit())
    if not digits:
        return None

    try:
        return int(digits)
    except ValueError:
        return None


def normalize_project_activities(
    activities: Any,
    project_code: Optional[str],
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

    # Default stage and status
    for item in normalized:
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

    # Ensure sequential codes when project code exists
    max_sequence = 0
    assigned_sequences: set[int] = set()

    if project_code:
        for item in normalized:
            sequence = _extract_sequence_from_code(item.get("code"), project_code)
            if sequence:
                assigned_sequences.add(sequence)
                if sequence > max_sequence:
                    max_sequence = sequence

        next_sequence = max_sequence + 1
        for item in normalized:
            code = str(item.get("code") or "").strip()
            if code:
                continue

            while next_sequence in assigned_sequences:
                next_sequence += 1

            item["code"] = f"{project_code}.{next_sequence:02d}"
            assigned_sequences.add(next_sequence)
            if next_sequence > max_sequence:
                max_sequence = next_sequence
            next_sequence += 1
            changed = True

    return normalized, changed, max_sequence
