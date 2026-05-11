"""
Payment Tracker Engine — 供应商付款管理引擎

职责：
  - JSON 文件读写（data/payments.json）
  - 供应商/费用项自动补全（来自 data/products/services/mashes/*.csv）
  - 付款条目 CRUD
  - 状态流转控制（pending → paid → archived）
  - 多条件筛选与看板统计

遵循项目 Engine 模式：纯函数，无类，Path-based 文件操作。
"""

from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
PAYMENTS_JSON = ROOT / "data" / "payments.json"
MASHES_DIR = ROOT / "data" / "products" / "services" / "mashes"

# Valid status transitions
VALID_TRANSITIONS = {
    "pending": ["paid", "archived"],
    "paid": ["archived"],
    "archived": [],
}


# ── JSON Storage I/O ──────────────────────────────────────────────


def load_payments() -> List[Dict[str, Any]]:
    if not PAYMENTS_JSON.exists():
        return []
    with open(PAYMENTS_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


def save_payments(payments: List[Dict[str, Any]]) -> None:
    PAYMENTS_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(PAYMENTS_JSON, "w", encoding="utf-8") as f:
        json.dump(payments, f, ensure_ascii=False, indent=2)


# ── ID Generation ─────────────────────────────────────────────────


def generate_payment_id(payments: List[Dict[str, Any]]) -> str:
    max_num = 0
    for p in payments:
        pid = p.get("payment_id", "")
        if pid.startswith("PAY-"):
            try:
                max_num = max(max_num, int(pid.split("-")[1]))
            except (ValueError, IndexError):
                pass
    return f"PAY-{max_num + 1:03d}"


# ── Mashes Data Lookup ────────────────────────────────────────────


def load_suppliers_from_mashes() -> List[str]:
    suppliers: set = set()
    if not MASHES_DIR.exists():
        return []
    for csv_file in sorted(MASHES_DIR.glob("*_merged.csv")):
        try:
            with open(csv_file, newline="", encoding="utf-8-sig") as f:
                for row in csv.DictReader(f):
                    name = (row.get("项目名称") or "").strip()
                    if name:
                        suppliers.add(name)
        except Exception:
            continue
    return sorted(suppliers)


def load_cost_items_from_mashes() -> List[Dict[str, str]]:
    items: List[Dict[str, str]] = []
    seen: set = set()
    if not MASHES_DIR.exists():
        return items
    for csv_file in sorted(MASHES_DIR.glob("*_merged.csv")):
        try:
            with open(csv_file, newline="", encoding="utf-8-sig") as f:
                for row in csv.DictReader(f):
                    code = (row.get("项目编号") or "").strip()
                    name = (row.get("项目名称") or "").strip()
                    if code and code not in seen:
                        seen.add(code)
                        items.append({"code": code, "name": name})
        except Exception:
            continue
    return items


# ── CRUD ──────────────────────────────────────────────────────────


def create_payment(request: Dict[str, Any]) -> Dict[str, Any]:
    payments = load_payments()
    now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    payment = {
        "payment_id": generate_payment_id(payments),
        "booking_id": request.get("booking_id"),
        "supplier_name": request.get("supplier_name", ""),
        "related_customer_order": request.get("related_customer_order"),
        "status": "pending",
        "cost_items": request.get("cost_items", []),
        "total_amount": request.get("total_amount", 0),
        "due_date": request.get("due_date"),
        "actual_payment_date": None,
        "receipt_link": request.get("receipt_link"),
        "notes": request.get("notes"),
        "created_at": now,
        "updated_at": now,
    }
    payments.append(payment)
    save_payments(payments)
    return payment


def get_payment(payment_id: str) -> Optional[Dict[str, Any]]:
    for p in load_payments():
        if p.get("payment_id") == payment_id:
            return p
    return None


def update_payment(payment_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    payments = load_payments()
    for i, p in enumerate(payments):
        if p.get("payment_id") == payment_id:
            for key, value in updates.items():
                if value is not None and key not in ("payment_id", "status", "created_at"):
                    p[key] = value
            p["updated_at"] = datetime.utcnow().isoformat(timespec="seconds") + "Z"
            payments[i] = p
            save_payments(payments)
            return p
    return None


def update_payment_status(payment_id: str, new_status: str) -> Optional[Dict[str, Any]]:
    payments = load_payments()
    for i, p in enumerate(payments):
        if p.get("payment_id") == payment_id:
            current = p.get("status", "pending")
            allowed = VALID_TRANSITIONS.get(current, [])
            if new_status not in allowed:
                raise ValueError(f"不允许从 '{current}' 变更到 '{new_status}'")
            p["status"] = new_status
            if new_status == "paid" and not p.get("actual_payment_date"):
                p["actual_payment_date"] = datetime.utcnow().strftime("%Y-%m-%d")
            p["updated_at"] = datetime.utcnow().isoformat(timespec="seconds") + "Z"
            payments[i] = p
            save_payments(payments)
            return p
    return None


def delete_payment(payment_id: str) -> bool:
    payments = load_payments()
    filtered = [p for p in payments if p.get("payment_id") != payment_id]
    if len(filtered) == len(payments):
        return False
    save_payments(filtered)
    return True


# ── Filtering & Stats ─────────────────────────────────────────────


def list_payments(
    supplier: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> List[Dict[str, Any]]:
    results = load_payments()

    if supplier:
        sl = supplier.lower()
        results = [p for p in results if sl in p.get("supplier_name", "").lower()]
    if status:
        results = [p for p in results if p.get("status") == status]
    if search:
        sl = search.lower()
        results = [
            p
            for p in results
            if sl in (p.get("booking_id") or "").lower()
            or sl in (p.get("related_customer_order") or "").lower()
            or sl in (p.get("supplier_name") or "").lower()
            or sl in (p.get("payment_id") or "").lower()
        ]
    if date_from:
        results = [p for p in results if p.get("due_date", "") >= date_from]
    if date_to:
        results = [p for p in results if p.get("due_date", "") <= date_to]

    return results


def get_kanban_stats() -> Dict[str, Any]:
    payments = load_payments()
    stats = {
        "total_count": len(payments),
        "pending_count": 0,
        "pending_amount": 0.0,
        "paid_count": 0,
        "paid_amount": 0.0,
        "archived_count": 0,
        "archived_amount": 0.0,
        "total_pending_amount": 0.0,
        "overdue_count": 0,
        "overdue_amount": 0.0,
    }
    today = datetime.utcnow().strftime("%Y-%m-%d")
    for p in payments:
        s = p.get("status", "pending")
        amt = float(p.get("total_amount", 0))
        stats[f"{s}_count"] = stats.get(f"{s}_count", 0) + 1
        stats[f"{s}_amount"] = stats.get(f"{s}_amount", 0.0) + amt
        if s == "pending":
            due = p.get("due_date", "")
            if due and due < today:
                stats["overdue_count"] += 1
                stats["overdue_amount"] += amt
    stats["total_pending_amount"] = stats["pending_amount"]
    return stats
