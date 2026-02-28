from typing import Any, Dict, List, Optional, Set, Tuple, Sequence
import json

def safe_int(value: Any) -> Optional[int]:
    try:
        if value is None:
            return None
        return int(float(value)) if isinstance(value, (str, float, int)) else None
    except (ValueError, TypeError):
        return None

def normalize_identity_value(value: Any) -> Optional[str]:
    """Normalize textual identifiers (names/emails) for comparisons."""
    if value in (None, "", False):
        return None
    text = str(value).strip().lower()
    if not text:
        return None
    normalized = " ".join(text.split())
    return normalized or None

def match_employee_from_lookup(value: Any, lookup: Dict[str, Set[int]]) -> Optional[int]:
    """Find a single employee ID from a normalized name/email lookup."""
    key = normalize_identity_value(value)
    if not key:
        return None
    matches = lookup.get(key)
    if matches and len(matches) == 1:
        return list(matches)[0]
    return None

def parse_activities_payload(raw: Any) -> List[Dict[str, Any]]:
    """Converts varied payloads into a list of dicts."""
    if not raw:
        return []
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, dict)]
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8", errors="ignore")
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return [item for item in parsed if isinstance(item, dict)]
        except Exception:
            return []
    return []

def extract_activity_employee_ids(activity: Dict[str, Any]) -> Set[int]:
    """Returns set of employee_ids referenced in the activity."""
    ids: Set[int] = set()

    def _collect(value: Any):
        candidate = safe_int(value)
        if candidate:
            ids.add(candidate)

    for key in ("responsible_id", "executor_id", "owner_id", "employee_id"):
        _collect(activity.get(key))

    collaborators = activity.get("collaborators") or activity.get("assigned_collaborators")
    if isinstance(collaborators, list):
        for entry in collaborators:
            if isinstance(entry, dict):
                _collect(entry.get("employee_id") or entry.get("id"))
            else:
                _collect(entry)

    return ids

def enrich_activity_assignments(activity: Dict[str, Any], employee_lookup: Dict[str, Set[int]], employee_directory: Dict[int, Dict[str, Any]]):
    """Enriches activity with employee IDs based on names/emails using lookup."""
    
    def _assign(field: str, sources: List[str]):
        if safe_int(activity.get(field)):
            return
        for source in sources:
            match = match_employee_from_lookup(activity.get(source), employee_lookup)
            if match:
                activity[field] = match
                if source.endswith("_name") and not activity.get(source):
                    activity[source] = employee_directory.get(match, {}).get("name")
                return

    _assign("responsible_id", ["responsible_name", "responsible", "who"])
    _assign("executor_id", ["executor_name", "executor"])
    _assign("owner_id", ["owner_name", "owner"])

    collaborators = activity.get("collaborators") or activity.get("assigned_collaborators")
    if isinstance(collaborators, list):
        for entry in collaborators:
            if not isinstance(entry, dict):
                continue
            if safe_int(entry.get("employee_id") or entry.get("id")):
                continue
            match = match_employee_from_lookup(entry.get("name") or entry.get("email"), employee_lookup)
            if match:
                entry["employee_id"] = match
                entry.setdefault("id", match)
