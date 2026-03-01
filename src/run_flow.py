"""
NovaBoard Electronics — Production Scheduling Agent
6-Step Production Workflow

API base: https://hackathon33.arke.so
  sales-api:   /api/sales/...
  product-api: /api/product/...
"""

import math
from datetime import timedelta
from typing import Dict, List

import httpx
from tqdm import tqdm

from camera_verify import validate_phase_completion_visually
from llm_executor import LLMExecutor
from telegram_bot import send_message, send_message_and_wait_for_approval

from constants import BOM_MINS_PER_UNIT, MINS_PER_DAY, TODAY
from environment import ARKE_PASSWORD, ARKE_TENANT, ARKE_USERNAME
from models import Phase, ProductionOrder, SalesOrder
from utils import format_utc_datetime, infer_product_code, parse_deadline

# -------------------------------------------------------------------------
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

        # Build product mapping
        product_mapping = build_product_mapping(client)

        # Cache product details (including process_lines with durations)
        product_details_cache = build_product_details_cache(client, product_mapping)

        # Step 1: Read open orders — show what needs to be produced
        sales_orders = step1_read_open_orders(client, product_mapping)

        # Step 2: Choose a planning policy (pure reasoning, no API calls)
        production_plan = step2_choose_planning_policy(sales_orders)

        # Step 3: Create production orders in Arke
        production_orders = step3_create_production_orders(client, production_plan)

        # Step 4: Schedule phases with concrete start/end dates
        production_orders = step4_schedule_phases(client, production_orders, product_details_cache)

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
    resp = client.post(
        f"{ARKE_TENANT}/api/login", json={"username": ARKE_USERNAME, "password": ARKE_PASSWORD}
    )
    resp.raise_for_status()
    token: str = resp.json()["accessToken"]
    print(f"[auth] OK — token: {token[:30]}...")
    return token


# ---------------------------------------------------------------------------
# Product Mapping
# ---------------------------------------------------------------------------


def build_product_mapping(client: httpx.Client) -> Dict[str, str]:
    """
    Fetch all products and build a mapping from name/internal_id to product_id.

    GET /api/product/product

    Returns: Dict with both name and internal_id as keys pointing to product_id
    """
    print("\n[Setup] Building product mapping...")
    resp = client.get(f"{ARKE_TENANT}/api/product/product")
    resp.raise_for_status()
    products = resp.json()

    mapping = {}
    for p in products:
        try:
            product_id = p["id"]
            try:
                name = p["name"]
                mapping[name] = product_id
            except KeyError:
                print(f"⚠️ Warning: Product {product_id} missing 'name' field")

            try:
                internal_id = p["internal_id"]
                mapping[internal_id] = product_id
            except KeyError:
                print(f"⚠️ Warning: Product {product_id} missing 'internal_id' field")
        except KeyError:
            print(f"⚠️ Warning: Product entry missing 'id' field: {p}")
            continue

    print(f"[Setup] Mapped {len(products)} products to {len(mapping)} lookup keys")
    return mapping


# ---------------------------------------------------------------------------
# Step 1 — Read open orders
# ---------------------------------------------------------------------------


def step1_read_open_orders(
    client: httpx.Client, product_mapping: Dict[str, str]
) -> List[SalesOrder]:
    """
    Step 1: Read open orders — show what needs to be produced

    Retrieve all accepted sales orders. For each one extract:
    product, quantity, deadline (expected_shipping_time), priority (1=highest), customer.
    Display a summary sorted by urgency (EDF + priority).

    GET /api/sales/order?status=accepted
    GET /api/sales/order/{id}
    """
    resp = client.get(
        f"{ARKE_TENANT}/api/sales/order", params={"status": "accepted", "limit": 1000}
    )
    resp.raise_for_status()
    summaries: List[Dict] = resp.json()

    orders: List[SalesOrder] = []
    for s in tqdm(summaries, desc="[Step 1] Fetching order details"):
        detail_resp = client.get(f"{ARKE_TENANT}/api/sales/order/{s['id']}")
        detail_resp.raise_for_status()
        d: Dict = detail_resp.json()

        try:
            deadline = parse_deadline(d["expected_shipping_time"])
        except KeyError:
            print(f"⚠️ Warning: Order {s['id']} missing 'expected_shipping_time', skipping")
            continue

        try:
            priority = int(d["priority"])
        except KeyError:
            print(f"⚠️ Warning: Order {s['id']} missing 'priority', defaulting to 3")
            priority = 3

        try:
            customer_name = d["customer_attr"]["name"]
        except KeyError:
            print(f"⚠️ Warning: Order {s['id']} missing customer name, using 'Unknown'")
            customer_name = "Unknown"

        try:
            products_list = d["products"]
        except KeyError:
            print(f"⚠️ Warning: Order {s['id']} missing 'products' field, skipping")
            continue

        for line in products_list:
            try:
                product_name = line["name"]
            except KeyError:
                print(f"⚠️ Warning: Product line in order {s['id']} missing 'name', skipping")
                continue

            # Try to resolve product_id from mapping
            product_id = None
            try:
                extra_id = line["extra_id"]
                product_id = product_mapping.get(extra_id)
            except KeyError:
                pass

            if not product_id:
                product_id = product_mapping.get(product_name)

            if not product_id:
                try:
                    product_id = line["extra_id"]
                except KeyError:
                    print(f"⚠️ Warning: Could not resolve product_id for '{product_name}'")
                    product_id = None

            try:
                quantity = int(line["quantity"])
            except KeyError:
                print(
                    f"⚠️ Warning: Product line '{product_name}' missing 'quantity', defaulting to 1"
                )
                quantity = 1

            try:
                internal_id = d["internal_id"]
            except KeyError:
                internal_id = s["id"]

            orders.append(
                SalesOrder(
                    id=s["id"],
                    internal_id=internal_id,
                    customer_name=customer_name,
                    product_id=product_id,
                    product_name=product_name,
                    product_code=infer_product_code(product_name),
                    quantity=quantity,
                    deadline=deadline,
                    priority=priority,
                )
            )
            if not orders[-1].product_id or orders[-1].product_id not in product_mapping.values():
                print(
                    f"⚠️ Warning: Could not resolve product_id for '{product_name}' (got: {product_id})"
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
            f"  {so.internal_id}; {so.product_id}: {po.starts_at.date()} -> {po.ends_at.date()} "
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
        body = {
            "product_id": po.sales_order.product_id,
            "quantity": po.sales_order.quantity,
            "starts_at": format_utc_datetime(po.starts_at),
            "ends_at": format_utc_datetime(po.ends_at),
        }
        resp = client.put(
            f"{ARKE_TENANT}/api/product/production",
            json=body,
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
    product_details_cache: Dict[str, Dict],
) -> List[ProductionOrder]:
    """
    Step 4: Schedule phases with concrete start/end dates

    1. Call _schedule on each production order → Arke generates phase sequence from BOM
    2. GET /api/product/production/{id} to read phases with phase names
    3. Look up duration from product's process_lines
    4. Assign concrete start/end dates to each phase (sequential)
    5. Update each phase with start/end dates

    Phase duration: total_minutes = duration × quantity
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
        resp = client.post(
            f"{ARKE_TENANT}/api/product/production/{po.production_order_id}/_schedule"
        )
        resp.raise_for_status()

        # 2. Get phases with phase names
        resp = client.get(f"{ARKE_TENANT}/api/product/production/{po.production_order_id}")
        resp.raise_for_status()
        prod_data = resp.json()

        try:
            phases_data = prod_data["phases"]
        except KeyError:
            print(
                f"⚠️ Warning: Production order {po.production_order_id} missing 'phases', skipping"
            )
            continue

        # Get product details for duration lookup
        try:
            product_details = product_details_cache[po.sales_order.product_id]
        except KeyError:
            print(f"⚠️ Warning: No cached details for product {po.sales_order.product_id}")
            product_details = {"process_lines": []}

        try:
            process_lines = product_details["process_lines"]
        except KeyError:
            print(f"⚠️ Warning: Product {po.sales_order.product_id} missing 'process_lines'")
            process_lines = []

        # Build phase name -> duration mapping
        phase_durations = {}
        for line in process_lines:
            try:
                name = line["name"]
                try:
                    duration = int(line["duration"])
                except KeyError:
                    print(f"⚠️ Warning: Process line '{name}' missing 'duration', using 60")
                    duration = 60
                phase_durations[name] = duration
            except KeyError:
                print(f"⚠️ Warning: Process line missing 'name' field, skipping")
                continue

        # 3. Compute and set start/end for each phase (sequential)
        phase_cursor = po.starts_at
        phases: List[Phase] = []

        for phase_data in phases_data:
            try:
                phase_id = phase_data["id"]
            except KeyError:
                print(f"⚠️ Warning: Phase data missing 'id', skipping")
                continue

            # Parse actual phase name from nested structure
            try:
                phase_name = phase_data["phase"]["name"]
            except KeyError:
                print(f"⚠️ Warning: Phase {phase_id} missing nested name, using 'Unknown Phase'")
                phase_name = "Unknown Phase"

            # Look up duration from product's process_lines
            duration_per_unit = phase_durations.get(phase_name, 60)

            total_mins = duration_per_unit * po.sales_order.quantity
            phase_days = math.ceil(total_mins / MINS_PER_DAY)

            phase_start = phase_cursor
            phase_end = phase_cursor + timedelta(days=phase_days)
            phase_cursor = phase_end

            # Update end date
            try:
                body = {"ends_at": format_utc_datetime(phase_end)}
                response = client.post(
                    f"{ARKE_TENANT}/api/product/production-order-phase/{phase_id}/_update_ending_date",
                    json=body,
                )
                response.raise_for_status()
            except:
                print(f"⚠️ Warning: Failed to update ending date for phase {phase_id}")
                print(
                    f"      Response status: {response.status_code}, request {body}, response: {response.text}"
                )

            # Update start date
            try:
                body = {"starts_at": format_utc_datetime(phase_start)}
                response = client.post(
                    f"{ARKE_TENANT}/api/product/production-order-phase/{phase_id}/_update_starting_date",
                    json=body,
                )
                response.raise_for_status()
            except:
                print(f"⚠️ Warning: Failed to update starting date for phase {phase_id}")
                print(
                    f"      Response status: {response.status_code}, request {body}, response {response.text}"
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

    lines.append("\n✉️ Reply /approve to confirm, or /disapprove to defer.")
    message = "\n".join(lines)

    # Send via Telegram/Slack/Discord
    print("\n[Telegram] Sending message to operator...")
    print("-" * 60)
    print(message)
    print("-" * 60)

    # Wait for operator response
    print("\n[Step 5] Waiting for operator approval...")

    approved = send_message_and_wait_for_approval(message)

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

    POST /api/product/production/{id}/_start

    Moves order from scheduled to in_progress; first phase becomes ready_to_start.
    """
    print("\n[Arke] Starting production orders...")
    for po in tqdm(production_orders, desc="Starting orders"):
        resp = client.post(f"{ARKE_TENANT}/api/product/production/{po.production_order_id}/_start")
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
    print("  Camera started...verifying phase completion...")

    for po in production_orders:
        print(f"\n  {po.sales_order.internal_id} (PO: {po.production_order_id}):")
        for phase in po.phases:
            print(f"    • {phase.name} ({phase.id})")

            # Start the phase
            resp = client.post(
                f"{ARKE_TENANT}/api/product/production-order-phase/{phase.id}/_start"
            )
            resp.raise_for_status()
            print(f"      ✅ Phase started")

            # TODO: Physical monitoring loop
            # - Camera/VLM verification
            # - Defect detection
            # - Operator notification if needed

            visually_valid = validate_phase_completion_visually()

            if not visually_valid:
                print(f"      ❌ Phase failed visual verification!")
                print("      Please investigate and resolve manually.")
                send_message(
                    f"Phase '{phase.name}' for sales order {po.sales_order.internal_id} failed visual verification. Please investigate and resolve."
                )
                break

            # Complete the phase
            try:
                # Fetch phase details to check if it's the final phase
                phase_resp = client.get(
                    f"{ARKE_TENANT}/api/product/production-order-phase/{phase.id}"
                )
                phase_resp.raise_for_status()
                phase_data = phase_resp.json()

                try:
                    is_final = phase_data["is_final"]
                except KeyError:
                    print(f"      ⚠️ Warning: Phase {phase.id} missing 'is_final', assuming False")
                    is_final = False

                # Build completion request body
                completion_body = {
                    "raw_material_inventory": [],
                    "skip_consumption": False,
                }

                # If final phase, include completed quantity
                if is_final:
                    completion_body["completed"] = po.sales_order.quantity
                    print(
                        f"      ℹ️  Final phase - including completed quantity: {po.sales_order.quantity}"
                    )

                resp = client.post(
                    f"{ARKE_TENANT}/api/product/production-order-phase/{phase.id}/_complete",
                    json=completion_body,
                )
                resp.raise_for_status()
                print(f"      ✅ Phase completed")
            except httpx.HTTPStatusError as e:
                print(f"      ❌ Error completing phase: {e}")
                print("      Please investigate and resolve manually.")
                send_message(
                    f"Something went wrong with sales order {po.sales_order.internal_id} during phase '{phase.name}'. Error code {e.response.status_code}; message {e.response.text}. Please investigate."
                )
                break

    send_message("\nAll phases have been advanced (started and completed) 🎉")


# ---------------------------------------------------------------------------
# Product Details Cache
# ---------------------------------------------------------------------------


def build_product_details_cache(
    client: httpx.Client, product_mapping: Dict[str, str]
) -> Dict[str, Dict]:
    """
    Fetch product details for all products to cache process_lines (phase durations).

    GET /api/product/product/{product_id}

    Returns: Dict mapping product_id to product details
    """
    print("\n[Setup] Caching product details with process_lines...")
    cache = {}
    unique_product_ids = set(product_mapping.values())

    for product_id in tqdm(unique_product_ids, desc="Fetching product details"):
        try:
            resp = client.get(f"{ARKE_TENANT}/api/product/product/{product_id}")
            resp.raise_for_status()
            cache[product_id] = resp.json()
        except Exception as e:
            print(f"⚠️ Warning: Could not fetch details for product {product_id}: {e}")
            cache[product_id] = {"process_lines": []}

    print(f"[Setup] Cached details for {len(cache)} products")
    return cache


if __name__ == "__main__":
    main()
