from __future__ import annotations

from dataclasses import dataclass, field

from ..models import TaxSummary


@dataclass
class Workspace:
    session_id: str
    report: TaxSummary | None = None
    traces: list[dict] = field(default_factory=list)


_SESSIONS: dict[str, Workspace] = {}


def get_workspace(session_id: str) -> Workspace:
    key = (session_id or "").strip() or "default"
    if key not in _SESSIONS:
        _SESSIONS[key] = Workspace(session_id=key)
    return _SESSIONS[key]


def save_report(session_id: str, report: TaxSummary) -> Workspace:
    workspace = get_workspace(session_id)
    workspace.report = report
    return workspace
