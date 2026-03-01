import json
import math
from datetime import timedelta
from typing import List, Tuple

import httpx
from pydantic import BaseModel, Field

from constants import BOM_MINS_PER_UNIT, MINS_PER_DAY, TODAY
from environment import GEMINI_API_KEY, GEMINI_API_URL
from models import ProductionOrder

# ---------------------------------------------------------------------------
# Pydantic models for Gemini response parsing
# ---------------------------------------------------------------------------


class ConflictPair(BaseModel):
    displaced_order_id: str  # internal_id of the order that loses its slot
    jumping_order_id: str  # internal_id of the order that jumped due to priority
    explanation: str  # human-readable explanation of why this is a conflict
    resolution: str  # what EDF does to resolve it


class ConflictReport(BaseModel):
    conflict_detected: bool
    pairs: list[ConflictPair] = Field(default_factory=list)
    operator_message: str  # full plain-text message to send via Telegram


class ScheduleOperation(BaseModel):
    action: str  # "move_after" | "move_before" | "move_to_front" | "move_to_back" | "swap"
    order_id: str  # internal_id of the order to move
    reference_order_id: str | None = None  # used by move_after / move_before / swap
    explanation: str  # why this operation satisfies the instruction


class ModifyReport(BaseModel):
    operations: list[ScheduleOperation]
    operator_message: str  # summary of changes made, to echo back via Telegram


# ---------------------------------------------------------------------------
# LLMExecutor
# ---------------------------------------------------------------------------


class LLMExecutor:
    def __init__(self, timeout: int = 30) -> None:
        self._client = httpx.Client(timeout=timeout)
        self._headers = {
            "Content-Type": "application/json",
            "X-goog-api-key": GEMINI_API_KEY,
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect_and_explain_and_resolve_conflict(
        self,
        production_orders: List[ProductionOrder],
    ) -> Tuple[List[ProductionOrder], str]:
        """
        1. Detect any priority-vs-deadline conflicts in the EDF schedule.
        2. Ask Gemini to explain each conflict and confirm EDF resolution.
        3. Return (unchanged EDF schedule, operator_message).

        EDF ordering is already correct — the schedule is NOT reordered here.
        Gemini's role is purely explanation and validation, not replanning.
        """
        schedule_json = _serialize_schedule(production_orders)
        prompt = _conflict_detection_prompt(schedule_json)

        raw = self._call_gemini(prompt, response_schema=ConflictReport.model_json_schema())
        report = ConflictReport.model_validate(raw)

        # Log detected pairs
        if report.conflict_detected:
            for pair in report.pairs:
                print(
                    f"[conflict] {pair.displaced_order_id} displaced by {pair.jumping_order_id}: "
                    f"{pair.explanation}"
                )
        else:
            print("[conflict] No conflicts detected.")

        return production_orders, report.operator_message

    def modify_production_orders(
        self,
        instruction: str,
        production_orders: List[ProductionOrder],
    ) -> List[ProductionOrder]:
        """
        Parse a natural-language operator instruction (e.g. from Telegram),
        derive a sequence of schedule operations, apply them to the ordered list,
        and recompute starts_at / ends_at for all orders.
        """
        schedule_json = _serialize_schedule(production_orders)
        prompt = _modify_prompt(instruction, schedule_json)

        raw = self._call_gemini(prompt, response_schema=ModifyReport.model_json_schema())
        report = ModifyReport.model_validate(raw)

        print(f"[modify] Applying {len(report.operations)} operation(s):")
        for op in report.operations:
            print(
                f"  {op.action} {op.order_id}"
                + (f" -> {op.reference_order_id}" if op.reference_order_id else "")
                + f": {op.explanation}"
            )

        updated = _apply_operations(report.operations, production_orders)
        updated = _recompute_schedule(updated)

        print(f"[modify] {report.operator_message}")
        return updated

    def __enter__(self) -> "LLMExecutor":
        return self

    def __exit__(self, *args) -> None:
        self._client.close()

    # ------------------------------------------------------------------
    # Internal: Gemini call
    # ------------------------------------------------------------------

    def _call_gemini(self, prompt: str, response_schema: dict) -> dict:
        """
        POST to Gemini generateContent with JSON response mode.
        Returns parsed dict ready for Pydantic validation.
        """
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0,
                "responseMimeType": "application/json",
                "responseSchema": response_schema,
            },
        }

        resp = self._client.post(GEMINI_API_URL, headers=self._headers, json=body)
        resp.raise_for_status()

        # Gemini wraps the response in candidates[0].content.parts[0].text
        text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        return json.loads(text)


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------


def _conflict_detection_prompt(schedule_json: str) -> str:
    return f"""
You are a production planning assistant at a PCB contract manufacturer.

The factory has ONE assembly line. Orders run sequentially. The schedule below
is already sorted by Earliest Deadline First (EDF): nearest deadline first,
ties broken by priority (lower number = higher urgency).

A CONFLICT exists when:
  - An order has a high priority (low number, e.g. P1) but a LATER deadline than
    the order scheduled after it.
  - If the schedule were sorted by priority instead of deadline, the high-priority
    order would jump ahead and cause the displaced order to MISS its deadline.

Your tasks:
1. Identify all such conflict pairs.
2. For each pair, confirm that EDF resolves it correctly (both deadlines met).
3. Write a clear, concise operator_message (plain text, suitable for Telegram)
   that explains any conflicts found and confirms all deadlines are met.
   If no conflicts exist, say so briefly.

Current EDF schedule (JSON):
{schedule_json}

Respond strictly according to the provided JSON schema.
""".strip()


def _modify_prompt(instruction: str, schedule_json: str) -> str:
    return f"""
You are a production planning assistant at a PCB contract manufacturer.

The factory has ONE assembly line. Orders run sequentially.
The operator has sent a modification instruction via Telegram.

Your task:
1. Parse the instruction into one or more schedule operations.
2. Each operation must reference orders by their internal_id (e.g. "SO-003").
3. Use only these actions:
   - move_after:   place order_id immediately after reference_order_id
   - move_before:  place order_id immediately before reference_order_id
   - move_to_front: place order_id first in the queue
   - move_to_back:  place order_id last in the queue
   - swap:         swap positions of order_id and reference_order_id
4. Write a brief operator_message confirming what changes will be made.

Current schedule (JSON):
{schedule_json}

Operator instruction:
"{instruction}"

Respond strictly according to the provided JSON schema.
""".strip()


# ---------------------------------------------------------------------------
# Schedule serialization
# ---------------------------------------------------------------------------


def _serialize_schedule(production_orders: list[ProductionOrder]) -> str:
    rows = []
    for i, po in enumerate(production_orders):
        so = po.sales_order
        rows.append(
            {
                "position": i + 1,
                "internal_id": so.internal_id,
                "customer": so.customer_name,
                "product": so.product_name,
                "quantity": so.quantity,
                "priority": so.priority,
                "deadline": so.deadline.date().isoformat(),
                "starts_at": po.starts_at.date().isoformat(),
                "ends_at": po.ends_at.date().isoformat(),
                "on_time": po.on_time,
            }
        )
    return json.dumps(rows, indent=2)


# ---------------------------------------------------------------------------
# Operation application + schedule recomputation
# ---------------------------------------------------------------------------


def _apply_operations(
    operations: list[ScheduleOperation],
    production_orders: list[ProductionOrder],
) -> list[ProductionOrder]:
    """Apply each operation sequentially to the ordered list."""
    orders = list(production_orders)

    for op in operations:
        idx = _find_index(orders, op.order_id)
        if idx is None:
            print(f"  [warning] order '{op.order_id}' not found — skipping operation")
            continue

        item = orders.pop(idx)

        if op.action == "move_to_front":
            orders.insert(0, item)

        elif op.action == "move_to_back":
            orders.append(item)

        elif op.action in ("move_after", "move_before"):
            ref_idx = _find_index(orders, op.reference_order_id)
            if ref_idx is None:
                print(f"  [warning] reference '{op.reference_order_id}' not found — skipping")
                orders.insert(idx, item)  # restore original position
                continue
            insert_at = ref_idx + 1 if op.action == "move_after" else ref_idx
            orders.insert(insert_at, item)

        elif op.action == "swap":
            ref_idx = _find_index(orders, op.reference_order_id)
            if ref_idx is None:
                print(f"  [warning] reference '{op.reference_order_id}' not found — skipping")
                orders.insert(idx, item)
                continue
            ref_item = orders.pop(ref_idx)
            # re-insert both at each other's original positions
            # idx may have shifted if ref_idx < idx
            actual_idx = idx if ref_idx >= idx else idx - 1
            orders.insert(ref_idx if ref_idx < actual_idx else actual_idx, item)
            orders.insert(actual_idx if ref_idx < actual_idx else ref_idx, ref_item)

        else:
            print(f"  [warning] unknown action '{op.action}' — skipping")
            orders.insert(idx, item)

    return orders


def _find_index(orders: list[ProductionOrder], internal_id: str | None) -> int | None:
    if internal_id is None:
        return None
    for i, po in enumerate(orders):
        if po.sales_order.internal_id.lower() == internal_id.lower():
            return i
    return None


def _recompute_schedule(production_orders: list[ProductionOrder]) -> list[ProductionOrder]:
    """
    Recompute starts_at / ends_at for every order based on current list order.
    Uses the same formula as compute_schedule() in scheduler.py:
      total_mins = BOM_MINS_PER_UNIT[product_code] * quantity
      days       = ceil(total_mins / MINS_PER_DAY)
    """

    updated = []
    cursor = TODAY
    for po in production_orders:
        so = po.sales_order
        mins_per_unit = BOM_MINS_PER_UNIT.get(so.product_code, 60)
        total_mins = mins_per_unit * so.quantity
        days_needed = math.ceil(total_mins / MINS_PER_DAY)

        starts_at = cursor
        ends_at = cursor + timedelta(days=days_needed)
        cursor = ends_at

        updated.append(
            po.model_copy(
                update={
                    "starts_at": starts_at,
                    "ends_at": ends_at,
                }
            )
        )

    return updated
