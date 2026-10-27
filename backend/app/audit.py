"""
Audit trail for sensitive edits: who changed what, and when.

Separate from activity_logs (the general "what's happening" feed shown to
all staff) — this keeps before/after values for money- and identity-
sensitive fields and is only ever shown to management
(see PERMISSIONS["audit.view"] in security.py).
"""
import json


def record(conn, user: dict, action: str, target_type: str, target_id, target_label: str, changes: dict | None = None):
    conn.execute("""
        INSERT INTO audit_log (org_id, actor_id, actor_name, actor_role, action, target_type, target_id, target_label, changes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user["org"], user["id"], user["name"], user["role"],
        action, target_type, target_id, target_label,
        json.dumps(changes, ensure_ascii=False) if changes else None,
    ))


def diff(old: dict, new: dict) -> dict:
    """Returns only the fields that actually changed, as {field: {old, new}}."""
    changed = {}
    for field, new_value in new.items():
        old_value = old.get(field)
        if old_value != new_value:
            changed[field] = {"old": old_value, "new": new_value}
    return changed
