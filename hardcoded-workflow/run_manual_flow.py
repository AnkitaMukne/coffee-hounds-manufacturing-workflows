"""
NovaBoard Electronics — Production Scheduling Agent
6-Step Production Workflow

API base: https://hackathon33.arke.so
  sales-api:   /api/sales/...
  product-api: /api/product/...
"""

import math
from datetime import timedelta
from typing import Dict, List, Optional

import httpx
from tqdm import tqdm

from constants import BASE_URL, BOM_MINS_PER_UNIT, MINS_PER_DAY, PASSWORD, TODAY, USERNAME
from models import Phase, ProductionOrder, SalesOrder
from utils import infer_product_code, parse_deadline

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    print("=" * 60)
    print("NovaBoard Electronics — Production Scheduling Agent")
    print(f"Date: {TODAY.date()}")
    print("=" * 60)

    with httpx.Client(timeout=30) as client:

        # Auth
        token = login(client)
        client.headers["Authorization"] = f"Bearer {token}"

        # Step 1: Read open orders — show what needs to be produced
        sales_orders = step1_read_open_orders(client)

        # Step 2: Choose a planning policy (pure reasoning, no API calls)
        production_plan = step2_choose_planning_policy(sales_orders)

        print("Early exit after Step 2 for testing without state-altering Arke API calls.")
        exit()

        # Step 3: Create production orders in Arke
        production_orders = step3_create_production_orders(client, production_plan)

        # Step 4: Schedule phases with concrete start/end dates
        production_orders = step4_schedule_phases(client, production_orders)

        # Step 5: Human-in-the-loop — present schedule and get approval
        approved = step5_get_human_approval(production_orders)
        if not approved:
            print("\n[abort] Operator did not approve. Exiting.")
            return

        # Confirm orders in Arke (moves to in_progress, first phase ready_to_start)
        confirm_production_orders(client, production_orders)

        # Step 6: Physical integration — advance production with real-time signals
        step6_advance_production(client, production_orders)

    print("\n[done] Scheduling complete.")


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
# Step 1 — Read open orders
# ---------------------------------------------------------------------------


def step1_read_open_orders(client: httpx.Client) -> List[SalesOrder]:
    """
    Step 1: Read open orders — show what needs to be produced

    Retrieve all accepted sales orders. For each one extract:
    product, quantity, deadline (expected_shipping_time), priority (1=highest), customer.
    Display a summary sorted by urgency (EDF + priority).

    GET /api/sales/order?status=accepted
    GET /api/sales/order/{id}
    """
    resp = client.get(f"{BASE_URL}/api/sales/order", params={"status": "accepted"})
    resp.raise_for_status()
    summaries: List[Dict] = resp.json()

    orders: List[SalesOrder] = []
    for s in tqdm(summaries, desc="[Step 1] Fetching order details"):
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

    print(f"\n[Step 1] {len(orders)} sales order lines (sorted by urgency):")
    for o in orders:
        print(
            f"  {o.internal_id} | {o.customer_name} | {o.product_name} x{o.quantity} "
            f"| deadline {o.deadline.date()} | P{o.priority}"
        )

    return orders


# ---------------------------------------------------------------------------
# Step 2 — Choose a planning policy (pure reasoning)
# ---------------------------------------------------------------------------


def step2_choose_planning_policy(sales_orders: List[SalesOrder]) -> List[ProductionOrder]:
    """
    Step 2: Choose a planning policy (no API calls — pure planning reasoning)

    Level 1 (Required): Earliest Deadline First (EDF)
    - One production order per sales order line
    - Sort by expected_shipping_time, nearest first
    - Ties broken by priority (lowest number wins)
    - ends_at = the sales order's shipping date

    Level 2 (Optional — higher score):
    - Group by Product: merge lines with same product
    - Split in Batches: cap batch size (e.g., 10 units)

    Returns: List of ProductionOrder with starts_at/ends_at computed
    """
    print("\n[Step 2] Applying Earliest Deadline First (EDF) policy...")

    production_orders: List[ProductionOrder] = []
    cursor = TODAY

    for so in sales_orders:
        mins_per_unit = BOM_MINS_PER_UNIT.get(so.product_code, 60)
        total_mins = mins_per_unit * so.quantity
        days_needed = math.ceil(total_mins / MINS_PER_DAY)

        starts_at = cursor
        ends_at = cursor + timedelta(days=days_needed)
        cursor = ends_at

        po = ProductionOrder(sales_order=so, starts_at=starts_at, ends_at=ends_at)
        production_orders.append(po)

    print(f"\n[Step 2] EDF schedule computed ({len(production_orders)} production orders):")
    for po in production_orders:
        so = po.sales_order
        flag = "OK" if po.on_time else "LATE"
        print(
            f"  {so.internal_id}: {po.starts_at.date()} -> {po.ends_at.date()} "
            f"(deadline {so.deadline.date()}) [{flag}]"
        )

    return production_orders


# ---------------------------------------------------------------------------
# Step 3 — Create production orders in Arke
# ---------------------------------------------------------------------------


def step3_create_production_orders(
    client: httpx.Client,
    production_plan: List[ProductionOrder],
) -> List[ProductionOrder]:
    """
    Step 3: Create production orders in Arke

    For each item decided in Step 2, create a production order.
    Set starts_at and ends_at from the plan.

    PUT /api/product/production
    {
        "product_id": "<id>",
        "quantity": 20,
        "starts_at": "2026-02-28T08:00:00Z",
        "ends_at": "2026-03-02T17:00:00Z"
    }
    """
    print("\n[Step 3] Creating production orders in Arke...")

    updated: List[ProductionOrder] = []
    for po in tqdm(production_plan, desc="Creating production orders"):
        resp = client.put(
            f"{BASE_URL}/api/product/production",
            json={
                "product_id": po.sales_order.product_id,
                "quantity": po.sales_order.quantity,
                "starts_at": po.starts_at.isoformat(),
                "ends_at": po.ends_at.isoformat(),
            },
        )
        resp.raise_for_status()
        prod_order_data = resp.json()
        production_order_id = prod_order_data["id"]

        updated.append(po.model_copy(update={"production_order_id": production_order_id}))

    print(f"[Step 3] Created {len(updated)} production orders")
    return updated


# ---------------------------------------------------------------------------
# Step 4 — Schedule phases
# ---------------------------------------------------------------------------


def step4_schedule_phases(
    client: httpx.Client,
    production_orders: List[ProductionOrder],
) -> List[ProductionOrder]:
    """
    Step 4: Schedule phases with concrete start/end dates

    1. Call _schedule on each production order → Arke generates phase sequence from BOM
    2. GET /api/product/production/{id} to read phases with duration_per_unit
    3. Assign concrete start/end dates to each phase (sequential)
    4. Update each phase with start/end dates

    Phase duration: total_minutes = duration_per_unit × quantity
    Working day = 480 min (8h)

    POST /api/product/production/{id}/_schedule
    GET /api/product/production/{id}
    POST /api/product/production-order-phase/{phaseId}/_update_starting_date
    POST /api/product/production-order-phase/{phaseId}/_update_ending_date
    """
    print("\n[Step 4] Scheduling phases...")

    updated: List[ProductionOrder] = []
    for po in tqdm(production_orders, desc="Scheduling phases"):
        # 1. Generate phase sequence from BOM
        resp = client.post(f"{BASE_URL}/api/product/production/{po.production_order_id}/_schedule")
        resp.raise_for_status()

        # 2. Get phases with duration_per_unit
        resp = client.get(f"{BASE_URL}/api/product/production/{po.production_order_id}")
        resp.raise_for_status()
        prod_data = resp.json()
        phases_data = prod_data.get("phases", [])

        # 3. Compute and set start/end for each phase (sequential)
        phase_cursor = po.starts_at
        phases: List[Phase] = []

        for phase_data in phases_data:
            phase_id = phase_data["id"]
            phase_name = phase_data.get("name", "Unknown Phase")
            duration_per_unit = phase_data.get("duration_per_unit", 60)
            total_mins = duration_per_unit * po.sales_order.quantity
            phase_days = math.ceil(total_mins / MINS_PER_DAY)

            phase_start = phase_cursor
            phase_end = phase_cursor + timedelta(days=phase_days)
            phase_cursor = phase_end

            client.post(
                f"{BASE_URL}/api/product/production-order-phase/{phase_id}/_update_starting_date",
                json={"starting_date": phase_start.isoformat()},
            )
            client.post(
                f"{BASE_URL}/api/product/production-order-phase/{phase_id}/_update_ending_date",
                json={"ending_date": phase_end.isoformat()},
            )

            phases.append(
                Phase(
                    id=phase_id,
                    name=phase_name,
                    starts_at=phase_start,
                    ends_at=phase_end,
                )
            )

        updated.append(po.model_copy(update={"phases": phases}))

    print(f"[Step 4] Scheduled phases for {len(updated)} production orders")
    return updated


# ---------------------------------------------------------------------------
# Step 5 — Human-in-the-loop approval
# ---------------------------------------------------------------------------


def step5_get_human_approval(production_orders: List[ProductionOrder]) -> bool:
    """
    Step 5: Human-in-the-loop — present schedule to production planner

    Send the proposed production schedule via messaging (Telegram, Slack, Discord).
    The message must include:
    1. Full ordered schedule with start/end dates per production order
    2. EDF reasoning for SO-005: "SO-003 (deadline Mar 4) is scheduled before
       SO-005 (deadline Mar 8) despite SO-005 being P1 — EDF prioritises
       tighter deadlines. All deadlines are met."

    Wait for planner's response. If approved, proceed to confirm orders in Arke.
    If changes requested, adjust dates and re-present.

    Returns: True if approved
    """
    print("\n[Step 5] Preparing schedule for human approval...")

    lines = ["📋 NovaBoard Production Schedule — Feb 28 2026\n"]
    for po in production_orders:
        so = po.sales_order
        flag = "✅ OK" if po.on_time else "⚠️ LATE"
        lines.append(
            f"• {so.internal_id} ({so.customer_name}) — {so.product_name} x{so.quantity}\n"
            f"  📅 {po.starts_at.strftime('%b %d')} → {po.ends_at.strftime('%b %d')} "
            f"| deadline {so.deadline.strftime('%b %d')} | P{so.priority} {flag}"
        )

    lines.append("\n✉️ Reply APPROVE to confirm, or describe changes.")
    message = "\n".join(lines)

    # Send via Telegram/Slack/Discord
    print("\n[Telegram] Sending message to operator...")
    print("-" * 60)
    print(message)
    print("-" * 60)

    # Wait for operator response
    print("\n[Step 5] Waiting for operator approval...")
    reply = input("  Type APPROVE to confirm, anything else to cancel: ").strip().upper()

    approved = reply == "APPROVE"
    if approved:
        print("[Step 5] ✅ Schedule approved by operator")
    else:
        print("[Step 5] ❌ Schedule rejected by operator")

    return approved


# ---------------------------------------------------------------------------
# Confirm production orders (after approval)
# ---------------------------------------------------------------------------


def confirm_production_orders(
    client: httpx.Client,
    production_orders: List[ProductionOrder],
) -> None:
    """
    Confirm production orders in Arke after human approval.

    POST /api/product/production/{id}/_confirm

    Moves order to in_progress; first phase becomes ready_to_start.
    """
    print("\n[Arke] Confirming production orders...")
    for po in tqdm(production_orders, desc="Confirming orders"):
        resp = client.post(f"{BASE_URL}/api/product/production/{po.production_order_id}/_confirm")
        resp.raise_for_status()
        print(f"  ✅ {po.sales_order.internal_id} → in_progress")


# ---------------------------------------------------------------------------
# Step 6 — Physical integration — advance production
# ---------------------------------------------------------------------------


def step6_advance_production(
    client: httpx.Client,
    production_orders: List[ProductionOrder],
) -> None:
    """
    Step 6: Physical integration — advance production with real-time signals

    Drive the production loop with real signals:

    Phase lifecycle:
    not_ready → ready → _start → started → _complete → completed

    Real implementation per phase:
    1. [Physical] Camera/VLM verifies phase completion (green QC indicator, etc.)
                  If defect detected → pause and notify operator
    2. POST /api/product/production-order-phase/{phaseId}/_start
    3. [wait / verify completion]
    4. POST /api/product/production-order-phase/{phaseId}/_complete

    Note: Physical layer integration not yet implemented - phases are started and completed immediately
    """
    print("\n[Step 6] Advancing production phases...")
    print("  Note: Physical layer integration not yet implemented")

    for po in production_orders:
        print(f"\n  {po.sales_order.internal_id} (PO: {po.production_order_id}):")
        for phase in po.phases:
            print(f"    • {phase.name} ({phase.id})")

            # Start the phase
            resp = client.post(f"{BASE_URL}/api/product/production-order-phase/{phase.id}/_start")
            resp.raise_for_status()
            print(f"      ✅ Phase started")

            # TODO: Physical monitoring loop
            # - Camera/VLM verification
            # - Defect detection
            # - Operator notification if needed

            # Complete the phase
            resp = client.post(
                f"{BASE_URL}/api/product/production-order-phase/{phase.id}/_complete"
            )
            resp.raise_for_status()
            print(f"      ✅ Phase completed")


if __name__ == "__main__":
    main()
