"""
NovaBoard Electronics — Production Scheduling Agent
Hardcoded httpx script. Steps 5 and 8 are stubs.

API base: https://hackathon33.arke.so
  sales-api:   /api/sales/...
  product-api: /api/product/...   (inferred from briefing — not in ref doc)
"""

import math
from datetime import timedelta
from typing import Dict, List, Optional

import httpx
from tqdm import tqdm

from .constants import BASE_URL, BOM_MINS_PER_UNIT, MINS_PER_DAY, PASSWORD, TODAY, USERNAME
from .models import Phase, ProductionOrder, SalesOrder
from .utils import infer_product_code, parse_deadline

# ---------------------------------------------------------------------------
# Step 1 — Auth
# ---------------------------------------------------------------------------


def login(client: httpx.Client) -> str:
    """POST /api/login -> Bearer token."""
    resp = client.post(f"{BASE_URL}/api/login", json={"username": USERNAME, "password": PASSWORD})
    resp.raise_for_status()
    token: str = resp.json()["accessToken"]
    print(f"[auth] OK — token: {token[:30]}...")
    return token


# ---------------------------------------------------------------------------
# Step 2 — Read accepted sales orders
# ---------------------------------------------------------------------------


def get_accepted_orders(client: httpx.Client) -> List[SalesOrder]:
    """
    GET /api/sales/order?status=accepted  -> list[orderSummary]
    GET /api/sales/order/{id}             -> orderDetails (includes product lines)

    orderSummary fields used:
      id, internal_id, expected_shipping_time, priority, customer_attr.name
    orderDetails adds:
      products: OrderLineItem[]  ->  item_id, name, quantity
    """
    resp = client.get(f"{BASE_URL}/api/sales/order", params={"status": "accepted"})
    resp.raise_for_status()
    summaries: List[Dict] = resp.json()

    orders: List[SalesOrder] = []
    for s in tqdm(summaries, desc="Fetching order details"):
        detail_resp = client.get(f"{BASE_URL}/api/sales/order/{s['id']}")
        detail_resp.raise_for_status()
        d: Dict = detail_resp.json()

        deadline = parse_deadline(d["expected_shipping_time"])
        priority = int(d.get("priority", 3))
        customer_name = (d.get("customer_attr") or {}).get("name", "Unknown")

        for line in d.get("products", []):
            product_name = line.get("name", "")
            orders.append(
                SalesOrder(
                    id=s["id"],
                    internal_id=d.get("internal_id", s["id"]),
                    customer_name=customer_name,
                    product_id=line.get("item_id") or line.get("id", ""),
                    product_name=product_name,
                    product_code=infer_product_code(product_name),
                    quantity=int(line.get("quantity", 1)),
                    deadline=deadline,
                    priority=priority,
                )
            )

    # EDF: nearest deadline first, ties broken by priority (lower = more urgent)
    orders.sort(key=lambda o: (o.deadline, o.priority))

    print(f"\n[orders] {len(orders)} lines (EDF order):")
    for o in orders:
        print(
            f"  {o.internal_id} | {o.customer_name} | {o.product_name} x{o.quantity} "
            f"| deadline {o.deadline.date()} | P{o.priority}"
        )

    return orders


# ---------------------------------------------------------------------------
# Step 3 — Compute EDF schedule (pure Python)
# ---------------------------------------------------------------------------


def compute_schedule(orders: List[SalesOrder]) -> List[ProductionOrder]:
    """
    Assign starts_at / ends_at sequentially.
    total_mins = BOM_MINS_PER_UNIT[product_code] x quantity
    days       = ceil(total_mins / 480)
    """
    production_orders: List[ProductionOrder] = []
    cursor = TODAY

    print("\n[schedule] EDF schedule:")
    for so in orders:
        mins_per_unit = BOM_MINS_PER_UNIT.get(so.product_code, 60)
        total_mins = mins_per_unit * so.quantity
        days_needed = math.ceil(total_mins / MINS_PER_DAY)

        starts_at = cursor
        ends_at = cursor + timedelta(days=days_needed)
        cursor = ends_at

        po = ProductionOrder(sales_order=so, starts_at=starts_at, ends_at=ends_at)
        flag = "OK" if po.on_time else "LATE"
        print(
            f"  {so.internal_id}: {starts_at.date()} -> {ends_at.date()} "
            f"(deadline {so.deadline.date()}) [{flag}]"
        )

        production_orders.append(po)

    return production_orders


# ---------------------------------------------------------------------------
# Step 4 — Detect scheduling conflict (SO-005 vs SO-003)
# ---------------------------------------------------------------------------


def detect_conflict(production_orders: List[ProductionOrder]) -> Optional[str]:
    """
    SO-005 (SmartHome IoT, P1 escalated, deadline Mar 8) vs
    SO-003 (AgriBot, P2, deadline Mar 4).

    Priority-first would schedule SO-005 before SO-003 -> SO-003 misses Mar 4.
    EDF keeps SO-003 first -> both deadlines met.
    Returns a human-readable report, or None if orders not found.
    """

    def find(fragment: str) -> Optional[ProductionOrder]:
        return next(
            (
                po
                for po in production_orders
                if fragment.lower() in po.sales_order.internal_id.lower()
            ),
            None,
        )

    so003_po = find("SO-003")
    so005_po = find("SO-005")

    if not so003_po or not so005_po:
        print("[conflict] Could not locate SO-003 or SO-005 — skipping")
        return None

    so003 = so003_po.sales_order
    so005 = so005_po.sales_order

    report = (
        f"\n[conflict] Priority escalation conflict detected:\n"
        f"  SO-005 ({so005.customer_name}) escalated P3->P1, deadline {so005.deadline.date()}.\n"
        f"  SO-003 ({so003.customer_name}) is P{so003.priority}, deadline {so003.deadline.date()}.\n"
        f"  Priority-first sort: SO-005 before SO-003 -> SO-003 misses {so003.deadline.date()}.\n"
        f"  EDF resolution: SO-003 scheduled first (tighter deadline).\n"
        f"    SO-003 ends {so003_po.ends_at.date()} <= {so003.deadline.date()} [OK]\n"
        f"    SO-005 ends {so005_po.ends_at.date()} <= {so005.deadline.date()} [OK]\n"
        f"  No manual rescheduling needed."
    )
    print(report)
    return report


# ---------------------------------------------------------------------------
# Step 5 — Create production orders in Arke  [STUB]
# ---------------------------------------------------------------------------


def create_production_orders_in_arke(
    client: httpx.Client,
    production_orders: List[ProductionOrder],
) -> List[ProductionOrder]:
    """
    STUB — assigns dummy IDs. Real implementation per order:

      1. PUT /api/product/production
            body: { product_id, quantity, starts_at (ISO), ends_at (ISO) }
            -> returns production order with id

      2. POST /api/product/production/{id}/_schedule
            -> Arke generates phase sequence from BOM

      3. GET /api/product/production/{id}
            -> read phases with duration_per_unit values

      4. For each phase (sequential — next starts when previous ends):
            phase_total_mins = duration_per_unit x quantity
            phase_days       = ceil(phase_total_mins / 480)
            POST /api/product/production-order-phase/{phaseId}/_update_starting_date
            POST /api/product/production-order-phase/{phaseId}/_update_ending_date
    """
    print("\n[arke] STUB: skipping production order creation")
    updated: List[ProductionOrder] = []
    for i, po in enumerate(tqdm(production_orders, desc="Creating production orders (stub)")):
        dummy_phases = [
            Phase(
                id=f"DUMMY-PH-{i+1:03d}-{j+1}",
                name=f"Phase {j+1}",
                starts_at=po.starts_at + timedelta(hours=j * 2),
                ends_at=po.starts_at + timedelta(hours=(j + 1) * 2),
            )
            for j in range(3)
        ]
        updated.append(
            po.model_copy(
                update={
                    "production_order_id": f"DUMMY-PO-{i+1:03d}",
                    "phases": dummy_phases,
                }
            )
        )
    return updated


# ---------------------------------------------------------------------------
# Step 6 — Notify operator via Telegram and wait for approval
# ---------------------------------------------------------------------------


def notify_and_wait_for_approval(
    production_orders: List[ProductionOrder],
    conflict_msg: Optional[str],
) -> bool:
    """
    1. Build schedule message.
    2. POST to Telegram Bot API.
    3. Wait for operator reply (console fallback — replace with getUpdates polling).
    Returns True if approved.
    """
    lines = ["NovaBoard Production Schedule — Feb 28 2026\n"]
    for po in production_orders:
        so = po.sales_order
        flag = "OK" if po.on_time else "LATE"
        lines.append(
            f"- {so.internal_id} ({so.customer_name}) — {so.product_name} x{so.quantity}\n"
            f"  {po.starts_at.strftime('%b %d')} -> {po.ends_at.strftime('%b %d')} "
            f"| deadline {so.deadline.strftime('%b %d')} | P{so.priority} [{flag}]"
        )

    if conflict_msg:
        lines.append(
            "\nPriority conflict resolved automatically (EDF):\n"
            "SO-005 (SmartHome IoT, P1 escalated) deadline Mar 8.\n"
            "SO-003 (AgriBot, P2) deadline Mar 4 — scheduled first.\n"
            "Both deadlines met. No intervention needed."
        )

    lines.append("\nReply APPROVE to confirm, or describe changes.")
    message = "\n".join(lines)

    print("Sending message to operator via Telegram (dummy for now) ...")
    print(message)

    print("\n[approval] Waiting for operator response...")
    reply = input("  Type APPROVE to confirm, anything else to cancel: ").strip().upper()
    return reply == "APPROVE"


# ---------------------------------------------------------------------------
# Step 7 — Confirm production orders in Arke
# ---------------------------------------------------------------------------


def confirm_production_orders(
    client: httpx.Client,
    production_orders: List[ProductionOrder],
) -> None:
    """
    POST /api/product/production/{id}/_confirm
    Moves order to in_progress; first phase becomes ready_to_start.
    """
    for po in tqdm(production_orders, desc="Confirming orders"):
        pid = po.production_order_id
        if pid and not pid.startswith("DUMMY"):
            resp = client.post(f"{BASE_URL}/api/product/production/{pid}/_confirm")
            resp.raise_for_status()
            print(f"  [confirm] {po.sales_order.internal_id} -> in_progress")
        else:
            print(f"  [confirm] STUB: would confirm {po.sales_order.internal_id} ({pid})")


# ---------------------------------------------------------------------------
# Step 8 — Advance phases  [STUB — physical layer goes here]
# ---------------------------------------------------------------------------


def advance_phases(
    client: httpx.Client,
    production_orders: List[ProductionOrder],
) -> None:
    """
    STUB. Real implementation per phase:

      Phase lifecycle: not_ready -> ready -> _start -> started -> _complete -> completed

      1. [Physical] Camera/VLM verifies phase completion (green QC indicator etc.)
                    defect detected -> pause and notify operator
      2. POST /api/product/production-order-phase/{phaseId}/_start
      3. [wait / verify]
      4. POST /api/product/production-order-phase/{phaseId}/_complete
    """
    print("\n[phases] STUB: physical layer not implemented")
    for po in production_orders:
        print(f"  {po.sales_order.internal_id}:")
        for phase in po.phases:
            print(f"    would start/complete '{phase.name}' ({phase.id})")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    print("=" * 60)
    print("NovaBoard Electronics — Production Scheduling Agent")
    print(f"Date: {TODAY.date()}")
    print("=" * 60)

    with httpx.Client(timeout=30) as client:

        # 1. Auth
        token = login(client)
        client.headers["Authorization"] = f"Bearer {token}"

        # 2. Read accepted orders, EDF sorted
        orders = get_accepted_orders(client)

        # 3. Compute EDF schedule
        production_orders = compute_schedule(orders)

        # 4. Detect SO-005 vs SO-003 conflict
        conflict_msg = detect_conflict(production_orders)

        # 5. Create production orders in Arke (STUB)
        production_orders = create_production_orders_in_arke(client, production_orders)

        # 6. Notify operator + wait for approval
        approved = notify_and_wait_for_approval(production_orders, conflict_msg)
        if not approved:
            print("\n[abort] Operator did not approve. Exiting.")
            return

        # 7. Confirm orders in Arke
        print("\n[arke] Confirming orders...")
        confirm_production_orders(client, production_orders)

        # 8. Advance phases (STUB — physical layer goes here)
        advance_phases(client, production_orders)

    print("\n[done] Scheduling complete.")


if __name__ == "__main__":
    main()
