from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import uuid4


from backend.app.core.paths import ROOT
LOG_DIR = ROOT / "logs"
WORKFLOW_TRACE_LOG = LOG_DIR / "workflow_trace.jsonl"


def append_workflow_event(
    *,
    workflow_id: str,
    step: str,
    status: str,
    lead_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    LOG_DIR.mkdir(exist_ok=True)
    record = {
        "event_id": f"evt_{uuid4().hex[:10]}",
        "workflow_id": workflow_id,
        "step": step,
        "status": status,
        "lead_id": lead_id,
        "details": details or {},
        "created_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
    }
    with WORKFLOW_TRACE_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
